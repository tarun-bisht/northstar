"""arXiv helpers: ID checks and a small client for the official export API.

The API (http://export.arxiv.org/api/query) is public; arXiv asks for at most one
request every 3 seconds. Used by scripts/fetch_candidates.py in GitHub Actions.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

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


def fetch_recent(category: str, max_results: int = 150, timeout: int = 30) -> list[dict]:
    q = urllib.parse.urlencode({
        "search_query": f"cat:{category}", "sortBy": "submittedDate", "sortOrder": "descending",
        "start": 0, "max_results": max_results,
    })
    req = urllib.request.Request("http://export.arxiv.org/api/query?" + q,
                                 headers={"User-Agent": "northstar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8")
    time.sleep(3)  # arXiv API etiquette
    return parse_feed(text)


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
    import json
    req = urllib.request.Request(f"{api}?date={date}", headers={"User-Agent": "northstar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse_hf_daily(json.load(r))
