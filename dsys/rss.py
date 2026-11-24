"""Deterministic RSS 2.0 generation from validated content."""

from __future__ import annotations

import datetime as dt
import email.utils
import re
from pathlib import Path
from xml.sax.saxutils import escape

from . import render
from .core import DAILY_STREAMS, STREAM_META, Repo, load_json, month_bounds, week_bounds
from .validate import guid_for

NS = ('xmlns:atom="http://www.w3.org/2005/Atom" '
      'xmlns:content="http://purl.org/rss/1.0/modules/content/" '
      'xmlns:dc="http://purl.org/dc/elements/1.1/" '
      'xmlns:media="http://search.yahoo.com/mrss/"')

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def x(s) -> str:
    """Escape text for XML element content / attributes."""
    return escape(_CTRL.sub("", str(s)), {'"': "&quot;"})


def _tz(offset: str) -> dt.timezone:
    sign = 1 if offset[0] == "+" else -1
    return dt.timezone(sign * dt.timedelta(hours=int(offset[1:3]), minutes=int(offset[4:6])))


def pub_datetime(date: dt.date, site: dict, order: int = 0) -> dt.datetime:
    """Stable timestamp: publish hour on that date, minus `order` seconds so items keep their order."""
    base = dt.datetime(date.year, date.month, date.day, int(site.get("publish_hour_local", 6)), 0, 0,
                       tzinfo=_tz(site.get("timezone_offset", "+00:00")))
    return base - dt.timedelta(seconds=order)


def rfc822(d: dt.datetime) -> str:
    return email.utils.format_datetime(d)


def collect_items(repo: Repo, stream: str, site: dict, examples: bool = False,
                  limit: int | None = None) -> list[dict]:
    """Return feed entries (newest first) as plain dicts.

    File names are ISO dates, weeks or months, so a reverse sort reads the newest file first.
    With a limit, reading stops once enough entries are collected, so feed builds stay fast
    however long the history grows.
    """
    entries = []
    for f in sorted(repo.iter_stream_files(stream, examples), reverse=True):
        if limit is not None and len(entries) >= limit:
            break
        doc = load_json(f)
        if stream in DAILY_STREAMS:
            day = dt.date.fromisoformat(doc["date"])
            for i, it in enumerate(doc["items"]):
                entries.append(_daily_entry(stream, doc, it, day, i, site))
        elif stream == "weekly":
            start, end = week_bounds(doc["week"])
            entries.append({
                "guid": guid_for(stream, doc), "title": f"Week {doc['week']}: optional exploration",
                "link": f"{site['base_url']}/weekly/{doc['week']}.html",
                "description": doc["intro"], "html": render.weekly_package(doc),
                "pub": pub_datetime(start, site), "creator": None, "categories": ["weekly"], "media": None,
            })
        elif stream == "reading":
            for i, pp in enumerate(doc["papers"]):
                entries.append({
                    "guid": f"dsys:reading:{pp['id']}", "title": f"[{pp['tags'][0]}] {pp['title']}", "link": pp["url"],
                    "description": pp.get("note") or ", ".join(pp["tags"]),
                    "html": render.reading_list({"papers": [pp]}),
                    "pub": pub_datetime(dt.date.fromisoformat(pp["added"]), site, i),
                    "creator": ", ".join(pp.get("authors", [])[:6]) or None, "categories": pp["tags"], "media": None,
                })
        elif stream == "monthly":
            start, _ = month_bounds(doc["month"])
            entries.append({
                "guid": guid_for(stream, doc), "title": f"{doc['month']}: optional monthly depth",
                "link": f"{site['base_url']}/monthly/{doc['month']}.html",
                "description": doc["intro"], "html": render.monthly_package(doc),
                "pub": pub_datetime(start, site), "creator": None, "categories": ["monthly"], "media": None,
            })
    entries.sort(key=lambda e: (e["pub"], e["guid"]), reverse=True)
    return entries[:limit] if limit is not None else entries


def _daily_entry(stream, doc, it, day, order, site):
    html_body = render.ITEM_RENDERERS[stream](it)
    link = it.get("url") or (it.get("source") or {}).get("url") or (it.get("sources") or [{}])[0].get("url") \
        or f"{site['base_url']}/daily/{doc['date']}.html"
    title = it["title"]
    creator = None
    cats = []
    media = None
    desc = ""
    if stream == "arxiv":
        title = f"[{it['tags'][0]}] {it['title']}"
        creator = ", ".join(it["authors"][:8]) + (" et al." if len(it["authors"]) > 8 else "")
        cats = it["categories"]
        desc = ", ".join(it["tags"])
    elif stream == "research_updates":
        desc = it["what_happened"]
        cats = [it["kind"]]
    elif stream == "world":
        desc = it["what_happened"]
        cats = [it["topic"]] + it["regions"]
    elif stream == "discovery":
        creator = it.get("creator")
        desc = it["description"]
        cats = [it["category"], it["tier"]]
    elif stream == "language":
        title = f"{it['language'].capitalize()}: {it['title']}"
        desc = it["theme"]
        cats = [it["language"]]
        link = f"{site['base_url']}/daily/{doc['date']}.html#language"
    elif stream == "youtube_shorts":
        creator = it["channel"]["name"]
        desc = it["why_it_matches"]
        cats = [it["category"], it["tier"]]
        media = {"thumbnail": it["thumbnail"], "player": it["embed_url"], "title": it["title"]}
    return {"guid": guid_for(stream, doc, it), "title": title, "link": link, "description": desc,
            "html": html_body, "pub": pub_datetime(day, site, order), "creator": creator,
            "categories": cats, "media": media}


def build_feed(repo: Repo, stream: str, examples: bool = False) -> str:
    site = repo.config("site")
    render.configure(repo)
    policy = repo.config("recommendation_policy")
    window = int(policy.get("feeds", {}).get(stream, 100))
    meta = STREAM_META[stream]
    entries = collect_items(repo, stream, site, examples, limit=window)
    self_url = f"{site['base_url']}/feeds/{meta['feed']}"
    last = rfc822(entries[0]["pub"]) if entries else rfc822(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<rss version="2.0" {NS}>', "<channel>",
           f"<title>{x(site['title'] + ' — ' + meta['title'])}</title>",
           f"<link>{x(site['base_url'] + '/')}</link>",
           f"<description>{x(meta['description'])}</description>",
           "<language>en</language>",
           f'<atom:link href="{x(self_url)}" rel="self" type="application/rss+xml"/>',
           f"<lastBuildDate>{last}</lastBuildDate>",
           "<generator>dsys</generator>",
           "<ttl>180</ttl>"]
    for e in entries:
        out.append("<item>")
        out.append(f"<title>{x(e['title'])}</title>")
        out.append(f"<link>{x(e['link'])}</link>")
        out.append(f'<guid isPermaLink="false">{x(e["guid"])}</guid>')
        out.append(f"<pubDate>{rfc822(e['pub'])}</pubDate>")
        if e["creator"]:
            out.append(f"<dc:creator>{x(e['creator'])}</dc:creator>")
        for c in e["categories"]:
            out.append(f"<category>{x(c)}</category>")
        out.append(f"<description>{x(e['description'])}</description>")
        out.append(f"<content:encoded>{x(e['html'])}</content:encoded>")
        if e["media"]:
            m = e["media"]
            out.append(f'<media:thumbnail url="{x(m["thumbnail"])}"/>')
            out.append(f'<media:content url="{x(m["player"])}" medium="video">'
                       f'<media:player url="{x(m["player"])}"/><media:title>{x(m["title"])}</media:title></media:content>')
        out.append("</item>")
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


def generate_all(repo: Repo, out_dir: Path | None = None, examples: bool = False) -> dict[str, Path]:
    from .core import ALL_STREAMS
    out_dir = out_dir or repo.p("feeds")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for stream in ALL_STREAMS:
        path = out_dir / STREAM_META[stream]["feed"]
        path.write_text(build_feed(repo, stream, examples), encoding="utf-8")
        written[stream] = path
    return written
