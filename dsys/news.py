"""News candidates from publishers' public RSS/Atom feeds (stdlib only).

The World Radar run selects from these verified headlines instead of relying only on
web search, which gave too few items and missed whole areas such as markets.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import re
import xml.etree.ElementTree as ET

from . import net

ATOM = "{http://www.w3.org/2005/Atom}"
_TAG = re.compile(r"<[^>]+>")


def clean(text: str, limit: int = 400) -> str:
    t = " ".join(html.unescape(_TAG.sub(" ", text or "")).split())
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def _date(s: str) -> str | None:
    """RFC 822 (RSS) or ISO 8601 (Atom) -> ISO UTC timestamp, or None."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse(xml_text: str | bytes) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for it in root.iter("item"):  # RSS 2.0
        link = (it.findtext("link") or "").strip()
        if not link:
            g = it.find("guid")
            link = (g.text or "").strip() if g is not None and (g.text or "").startswith("http") else ""
        out.append({"title": clean(it.findtext("title"), 200), "url": link,
                    "published": _date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
                    "summary": clean(it.findtext("description"))})
    for e in root.iter(f"{ATOM}entry"):  # Atom
        link = ""
        for ln in e.findall(f"{ATOM}link"):
            if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                link = ln.get("href")
                break
        out.append({"title": clean(e.findtext(f"{ATOM}title"), 200), "url": link,
                    "published": _date(e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated")),
                    "summary": clean(e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content"))})
    return [x for x in out if x["title"] and x["url"].startswith("http")]


def fetch(url: str, timeout: int = 30) -> list[dict]:
    return parse(net.get(url, timeout=timeout, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"}))


def select_recent(items: list[dict], now: dt.datetime, hours: int) -> list[dict]:
    """Keep items published within `hours` (undated items are kept: some feeds omit dates)."""
    cutoff = now - dt.timedelta(hours=hours)
    keep = []
    for x in items:
        p = x.get("published")
        if p is None or dt.datetime.fromisoformat(p.replace("Z", "+00:00")) >= cutoff:
            keep.append(x)
    return keep
