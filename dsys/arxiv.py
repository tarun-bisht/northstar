"""arXiv helpers: ID checks and a small client for the official export API.

The API (https://export.arxiv.org/api/query) is public; arXiv asks for at most one
request every 3 seconds. All calls go through dsys.net, which retries transient failures.
rss.arxiv.org is the fallback when the API fails; alphaXiv adds community trending. Used by scripts/fetch_candidates.py in GitHub Actions.
"""

from __future__ import annotations

import email.utils
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

from . import net

ID_RE = re.compile(r"^(\d{4})\.(\d{4,5})$")
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def is_valid_id(arxiv_id: str) -> bool:
    m = ID_RE.match(arxiv_id or "")
    if not m:
        return False
    yymm = m.group(1)
    mm = int(yymm[2:])
    return 1 <= mm <= 12


def abs_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


def url_errors(paper: dict) -> list[str]:
    aid = paper.get("arxiv_id", "")
    if not is_valid_id(aid):
        return [f"invalid arXiv id {aid!r}"]
    errs = []
    url = paper.get("url", "")
    if not re.match(rf"^https://arxiv\.org/abs/{re.escape(aid)}(v\d+)?$", url):
        errs.append(f"url must be canonical https://arxiv.org/abs/{aid}")
    if paper.get("id") != f"arxiv-{aid}":
        errs.append(f"id must be 'arxiv-{aid}'")
    return errs


def split_id(raw: str) -> tuple[str, str | None]:
    """'http://arxiv.org/abs/2501.01234v2' -> ('2501.01234', 'v2')"""
    tail = raw.rstrip("/").split("/")[-1]
    m = re.match(r"^(\d{4}\.\d{4,5})(v\d+)?$", tail)
    if not m:
        return tail, None
    return m.group(1), m.group(2)


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        aid, ver = split_id(e.findtext(f"{ATOM}id", ""))
        if not is_valid_id(aid):
            continue
        cats = [c.get("term") for c in e.findall(f"{ATOM}category") if c.get("term")]
        out.append({
            "arxiv_id": aid,
            "version": ver,
            "title": " ".join((e.findtext(f"{ATOM}title") or "").split()),
            "authors": [" ".join((a.findtext(f"{ATOM}name") or "").split()) for a in e.findall(f"{ATOM}author")],
            "abstract": " ".join((e.findtext(f"{ATOM}summary") or "").split()),
            "submitted": (e.findtext(f"{ATOM}published") or "")[:10],
            "updated": (e.findtext(f"{ATOM}updated") or "")[:10],
            "categories": cats,
            "primary_category": (e.find(f"{ARXIV}primary_category").get("term")
                                 if e.find(f"{ARXIV}primary_category") is not None else (cats[0] if cats else None)),
            "url": abs_url(aid),
        })
    return out


class RateExceeded(Exception):
    """arXiv sometimes answers 200 with the text 'Rate exceeded.' instead of a 429."""


def fetch_recent(category: str, max_results: int = 150, timeout: int = 90) -> list[dict]:
    """Newest papers in a category from the export API, with retries (see dsys.net)."""
    q = urllib.parse.urlencode({
        "search_query": f"cat:{category}", "sortBy": "submittedDate", "sortOrder": "descending",
        "start": 0, "max_results": max_results,
    })
    url = "https://export.arxiv.org/api/query?" + q
    for attempt in range(3):
        text = net.get(url, timeout=timeout).decode("utf-8", "replace")
        net._sleep(3)  # arXiv asks for at most one request every 3 seconds
        if not text.lstrip().lower().startswith("rate exceeded"):
            return parse_feed(text)
        net._sleep(30 * (attempt + 1))
    raise RateExceeded(f"{category}: arXiv answered 'Rate exceeded' three times")


def parse_rss(xml_text: str, category: str) -> list[dict]:
    """Parse rss.arxiv.org/rss/<cat>: today's announcement list, used when the API fails.

    Each item's description reads 'arXiv:<id>v1 Announce Type: new Abstract: <text>'.
    Replacements (already announced papers) are skipped.
    """
    root = ET.fromstring(xml_text)
    out = []
    for it in root.iter("item"):
        desc = " ".join((it.findtext("description") or "").split())
        m = re.match(r"^arXiv:(\d{4}\.\d{4,5})(v\d+)?\s+Announce Type:\s*(\S+)\s+Abstract:\s*(.*)$", desc)
        if not m or m.group(3).startswith("replace") or not is_valid_id(m.group(1)):
            continue
        aid = m.group(1)
        creators = it.findtext("{http://purl.org/dc/elements/1.1/}creator") or ""
        cats = [c.text for c in it.findall("category") if c.text] or [category]
        pub = it.findtext("pubDate") or ""
        try:
            submitted = email.utils.parsedate_to_datetime(pub).date().isoformat()
        except (TypeError, ValueError):
            submitted = ""
        out.append({
            "arxiv_id": aid, "version": m.group(2),
            "title": " ".join((it.findtext("title") or "").split()),
            "authors": [a.strip() for a in creators.split(",") if a.strip()],
            "abstract": m.group(4).strip(),
            "submitted": submitted, "categories": cats, "primary_category": cats[0],
            "url": abs_url(aid), "source": "arxiv_rss",
        })
    return out


def fetch_rss(category: str, timeout: int = 60) -> list[dict]:
    text = net.get(f"https://rss.arxiv.org/rss/{category}", timeout=timeout).decode("utf-8", "replace")
    net._sleep(3)
    return parse_rss(text, category)


def parse_hf_daily(data: list) -> list[dict]:
    """Normalise Hugging Face /api/daily_papers JSON into candidate dicts (arXiv papers only)."""
    out = []
    for row in data or []:
        p = row.get("paper", row)
        aid = str(p.get("id", ""))
        if not is_valid_id(aid):
            continue
        out.append({
            "arxiv_id": aid,
            "title": " ".join((p.get("title") or row.get("title") or "").split()),
            "authors": [a.get("name", "") for a in p.get("authors", []) if a.get("name")],
            "abstract": " ".join((p.get("summary") or row.get("summary") or "").split()),
            "submitted": (p.get("publishedAt") or row.get("publishedAt") or "")[:10],
            "hf_upvotes": int(p.get("upvotes") or 0),
            "url": abs_url(aid),
        })
    return out


def fetch_hf_daily(date: str, api: str = "https://huggingface.co/api/daily_papers", timeout: int = 30) -> list[dict]:
    return parse_hf_daily(json.loads(net.get(f"{api}?date={date}", timeout=timeout)))


# --- alphaXiv trending ---------------------------------------------------------------
ALPHAXIV_FEED = "https://api.alphaxiv.org/papers/v3/feed"


def _first(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def parse_alphaxiv(data) -> list[dict]:
    """Normalise alphaXiv feed JSON. The endpoint is undocumented, so read it defensively:
    accept several field names and skip anything without a valid arXiv id."""
    rows = data if isinstance(data, list) else (_first(data or {}, "papers", "data", "results") or [])
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        p = row.get("paper") if isinstance(row.get("paper"), dict) else row
        raw = str(_first(p, "universal_paper_id", "universalId", "arxivId", "arxiv_id", "upid", "paperId") or "")
        aid, _ = split_id(raw)
        if not is_valid_id(aid):
            continue
        authors = _first(p, "authors", "authorNames") or []
        names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors] if isinstance(authors, list) else []
        metrics = p.get("metrics") if isinstance(p.get("metrics"), dict) else {}
        votes = _first(metrics, "public_total_votes", "total_votes", "upvotes", "votes") or \
            _first(p, "public_total_votes", "total_votes", "upvotes", "votes") or 0
        visits = metrics.get("visits_count") if isinstance(metrics.get("visits_count"), dict) else {}
        when = str(_first(p, "first_publication_date", "firstPublicationDate", "publication_date",
                          "submittedDate", "publishedDate") or "")[:10]
        try:
            votes = int(votes)
        except (TypeError, ValueError):
            votes = 0
        out.append({
            "arxiv_id": aid,
            "title": " ".join(str(_first(p, "title", "name") or "").split()),
            "authors": [n for n in names if n],
            "abstract": " ".join(str(_first(p, "abstract", "paper_summary", "summary") or "").split()),
            "submitted": when,
            "alphaxiv_votes": votes,
            **({"alphaxiv_visits": int(visits["all"])} if str(visits.get("all", "")).isdigit() else {}),
            "url": abs_url(aid),
        })
    return out


def fetch_alphaxiv(limit: int = 50, sort: str = "Hot", interval: str = "7 Days", timeout: int = 30) -> list[dict]:
    q = urllib.parse.urlencode({"pageNum": 1, "pageSize": limit, "sort": sort, "interval": interval})
    return parse_alphaxiv(json.loads(net.get(f"{ALPHAXIV_FEED}?{q}", timeout=timeout,
                                             headers={"Accept": "application/json"})))
