"""Shared fetching helpers for the GitHub Actions scrapers: parallel feeds, feed health,
social sources (Reddit RSS, Bluesky search), arXiv ids in posts, affiliations from page 1,
and xkcd.

Every source is isolated: one broken feed never stops the rest. Permanent errors (401, 403,
404, 410) are not retried and are logged in state/feed_health.json. A feed that answered 404
or 410 is skipped for a week, then tried again once.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import net, news

ARXIV_ID = re.compile(r"(?<![\d.])(\d{4}\.\d{4,5})(?:v\d+)?(?![\d])")
DEAD_DAYS = 7


# --- feed health -----------------------------------------------------------------------
class FeedHealth:
    """state/feed_health.json: last status per feed URL, and which ones are dead."""

    def __init__(self, path: Path, today: dt.date):
        self.path, self.today = path, today
        self.data = json.loads(path.read_text()) if path.exists() else {}

    def skip(self, url: str) -> bool:
        h = self.data.get(url)
        if not h or not h.get("dead_since"):
            return False
        return (self.today - dt.date.fromisoformat(h["dead_since"])).days % DEAD_DAYS != 0

    def record(self, url: str, name: str, err: Exception | None, count: int = 0) -> None:
        h = self.data.setdefault(url, {"name": name})
        h["name"], h["checked"] = name, self.today.isoformat()
        if err is None:
            h.update(status="ok", items=count, fails=0)
            h.pop("dead_since", None)
            return
        h["status"], h["fails"] = net.status_of(err), int(h.get("fails", 0)) + 1
        if net.is_permanent(err) and h["status"] in ("404", "410"):
            h.setdefault("dead_since", self.today.isoformat())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def fetch_many(feeds: list[dict], fn: Callable[[str], list[dict]], health: FeedHealth | None = None,
               workers: int = 10) -> dict[str, tuple[list[dict] | None, Exception | None]]:
    """Fetch every feed in parallel. A feed may list `alternates` (tried in order when the main
    URL fails). Returns {name: (items, error)}."""
    def one(f: dict):
        urls = [f["url"]] + list(f.get("alternates", []))
        err = None
        for u in urls:
            if health and health.skip(u):
                err = err or RuntimeError("skipped: dead link, retried weekly")
                continue
            try:
                items = fn(u)
                if health:
                    health.record(u, f["name"], None, len(items))
                return f["name"], (items, None)
            except Exception as e:  # isolate every source
                err = e
                if health:
                    health.record(u, f["name"], e)
        return f["name"], (None, err)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(one, feeds))


# --- social sources --------------------------------------------------------------------
def reddit_feed(subs: list[str], sort: str = "top", t: str = "day") -> dict:
    """A multireddit RSS feed, with old.reddit.com as the alternate (Reddit often blocks one host)."""
    path = f"r/{'+'.join(subs)}/{sort}/.rss?t={t}"
    return {"url": f"https://www.reddit.com/{path}", "alternates": [f"https://old.reddit.com/{path}"]}


def arxiv_ids(text: str) -> list[str]:
    """arXiv ids mentioned in a post: arxiv.org/abs/2501.01234, alphaxiv.org/abs/..., hf.co/papers/..."""
    out = []
    for m in ARXIV_ID.finditer(text or ""):
        aid = m.group(1)
        if 1 <= int(aid[2:4]) <= 12 and aid not in out:
            out.append(aid)
    return out


BLUESKY_SEARCH = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def parse_bluesky(data: dict) -> list[dict]:
    out = []
    for p in data.get("posts", []):
        rec = p.get("record") or {}
        text = rec.get("text") or ""
        links = [f.get("uri") for fc in rec.get("facets") or [] for f in fc.get("features") or [] if f.get("uri")]
        ext = ((p.get("embed") or {}).get("external") or {}).get("uri")
        if ext:
            links.append(ext)
        handle = (p.get("author") or {}).get("handle")
        rkey = str(p.get("uri", "")).rsplit("/", 1)[-1]
        if not handle or not rkey:
            continue
        out.append({"source": "Bluesky", "author": handle, "text": " ".join(text.split()), "links": links,
                    "url": f"https://bsky.app/profile/{handle}/post/{rkey}",
                    "likes": int(p.get("likeCount") or 0), "reposts": int(p.get("repostCount") or 0),
                    "published": news._date(rec.get("createdAt") or "")})
    return out


def bluesky_search(q: str, limit: int = 100, sort: str = "top", since: str | None = None) -> list[dict]:
    """Public search (no login, no cursor: Bluesky allows only the first page without one)."""
    params = {"q": q, "limit": limit, "sort": sort, **({"since": since} if since else {})}
    data = json.loads(net.get(f"{BLUESKY_SEARCH}?{urllib.parse.urlencode(params)}", timeout=20,
                              headers={"Accept": "application/json"}))
    return parse_bluesky(data)


def fetch_rss(url: str) -> list[dict]:
    return news.fetch(url)


# --- affiliations from page 1 ----------------------------------------------------------
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
_AFF = re.compile(r'class="[^"]*ltx_role_affiliation[^"]*"[^>]*>(.*?)</span>', re.S)
_EMAILSPAN = re.compile(r'class="[^"]*ltx_role_email[^"]*"[^>]*>(.*?)</span>', re.S)


def parse_html_front(html_text: str) -> dict:
    """Affiliations and email domains from arXiv's HTML version (LaTeXML marks them up)."""
    head = html_text[:200_000]
    affs = [news.clean(a) for a in _AFF.findall(head)]
    affs = [a for a in affs if 3 <= len(a) <= 300]
    emails = " ".join(news.clean(e) for e in _EMAILSPAN.findall(head))
    first = news.clean(head[: head.find("ltx_abstract") if "ltx_abstract" in head else 60_000])
    domains = sorted({d.lower() for d in _EMAIL.findall(emails + " " + first)})
    return {"affiliations": sorted(set(affs)), "email_domains": domains}


def parse_text_front(text: str) -> dict:
    """Affiliations (lines before the abstract) and email domains from page 1 of a PDF."""
    cut = re.split(r"\babstract\b", text, maxsplit=1, flags=re.I)[0] if text else ""
    lines = [" ".join(ln.split()) for ln in cut.splitlines()]
    hint = re.compile(r"universit|institut|college|school|laborator|\blab\b|research|inc\.|ltd|deepmind|google|"
                      r"microsoft|meta|openai|anthropic|nvidia|academy|centre|center|department", re.I)
    affs = sorted({ln for ln in lines if hint.search(ln) and 3 <= len(ln) <= 200})
    return {"affiliations": affs[:20], "email_domains": sorted({d.lower() for d in _EMAIL.findall(cut)})}


def front_matter(aid: str) -> dict:
    """Page 1 of a paper: arXiv HTML first, the PDF's first page if there is no HTML. No retries."""
    try:
        h = net.get(f"https://arxiv.org/html/{aid}", timeout=20, pauses=()).decode("utf-8", "replace")
        got = parse_html_front(h)
        if got["affiliations"] or got["email_domains"]:
            return {**got, "via": "html"}
    except Exception:
        pass
    try:
        import io
        from pypdf import PdfReader  # installed by the workflow only
        pdf = net.get(f"https://arxiv.org/pdf/{aid}", timeout=30, pauses=())
        text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text() or ""
        return {**parse_text_front(text), "via": "pdf"}
    except Exception as e:
        return {"affiliations": [], "email_domains": [], "via": "none", "error": net.status_of(e)}


# --- xkcd for #random --------------------------------------------------------------------
def xkcd(num: int | None = None) -> dict:
    url = f"https://xkcd.com/{num}/info.0.json" if num else "https://xkcd.com/info.0.json"
    d = json.loads(net.get(url, timeout=20))
    return {"num": d["num"], "title": html.unescape(d.get("safe_title") or d.get("title", "")),
            "alt": d.get("alt", ""), "url": f"https://xkcd.com/{d['num']}/", "img": d.get("img"),
            "date": f"{d.get('year')}-{int(d.get('month', 1)):02d}-{int(d.get('day', 1)):02d}"}
