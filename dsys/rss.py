"""Deterministic RSS 2.0 generation from validated content."""

from __future__ import annotations

import datetime as dt
import email.utils
import re
from pathlib import Path
from xml.sax.saxutils import escape

from . import render
from .core import DAILY_STREAMS, DIGEST_FEEDS, FEEDS, STREAM_META, Repo, load_json, month_bounds, week_bounds
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


_DETAILS_OPEN = re.compile(r"<details[^>]*>\s*<summary>(.*?)</summary>", re.S)


def for_readers(html_body: str) -> str:
    """Make fragments safe for RSS readers: many drop or mangle <details>, so open them up.

    The summary becomes a bold lead-in and the content shows in full.
    """
    html_body = _DETAILS_OPEN.sub(lambda m: f"<p><strong>{m.group(1)}</strong></p>", html_body)
    return html_body.replace("</details>", "")


def _digest_html(site: dict, date: str, streams: dict, part: str) -> str:
    """One compact part of a day: headings per stream and section, short entries that link out."""
    out = [f'<p><a href="{x(site["base_url"])}/daily/{date}/{part}.html" target="_blank" rel="noopener">Open on the site</a></p>']
    for key, label, names in render.DAILY_PARTS:
        if key != part:
            continue
        present = [s for s in names if s in streams and (streams[s].get("papers") or streams[s].get("items"))]
        if not present:
            continue
        for s in present:
            items = streams[s]["papers"] if s == "reading" else streams[s]["items"]
            title = "Reading list this week" if s == "reading" else STREAM_META[s]["title"]
            out.append(f"<h3>{render.esc(title)} ({len(items)})</h3>")
            if s == "arxiv":
                out.append("<ul>" + "".join(
                    f"<li><strong>{render.a(p['url'], p['title'])}</strong><br/>{render.esc(', '.join(p['tags']))}. "
                    f"{render.esc(', '.join(p['authors'][:4]))}{' et al.' if len(p['authors']) > 4 else ''}</li>"
                    for p in items) + "</ul>")
            elif s == "world":
                briefs = streams[s].get("briefs", [])
                for key, sec, its in render.group_world(items, briefs):
                    out.append(f"<h4>{render.esc(sec)}</h4>" + ("<ul>" + "".join(
                        f"<li><strong>{render.a(w['sources'][0]['url'], w['title'])}</strong><br/>{render.esc(w['what_happened'])} "
                        f"<em>Why it matters:</em> {render.esc(w['why_it_matters'])}</li>" for w in its) + "</ul>" if its else "")
                        + render.world_briefs(briefs, key))
            elif s == "research_updates":
                out.append("<ul>" + "".join(
                    f"<li><strong>{render.a(u['source']['url'], u['title'])}</strong><br/>{render.esc(u['what_happened'])}</li>"
                    for u in items) + "</ul>")
            elif s == "discovery":
                for _, sec, its in render.group_discovery(items):
                    out.append(f"<h4>{render.esc(sec)}</h4><ul>" + "".join(
                        f"<li><strong>{render.a(r['url'], r['title']) if r.get('url') else render.esc(r['title'])}</strong>"
                        f"{' by ' + render.esc(r['creator']) if r.get('creator') else ''}<br/>{render.esc(r['description'])}"
                        f"{render.media_embed(r.get('url'), r.get('title', ''), r.get('audio_url'))}</li>"
                        for r in its) + "</ul>")
            elif s == "reading":
                out.append("<ul>" + "".join(
                    f"<li><strong>{render.a(pp['url'], pp['title'])}</strong><br/>{render.esc(', '.join(pp['tags']))}"
                    f"{'. ' + render.esc(pp['note']) if pp.get('note') else ''}</li>" for pp in items) + "</ul>")
            elif s == "language":
                out += [f"<h4>{render.esc(pk['language'].capitalize())}: {render.esc(pk['title'])}</h4>"
                        + for_readers(render.language_pack(pk)) for pk in items]
            elif s == "youtube_shorts":
                out.append("<p>" + " ".join(
                    f'<a href="{render.esc(v["url"])}" target="_blank" rel="noopener noreferrer"><img src="{render.esc(v["thumbnail"])}" alt="{render.esc(v["title"])}" width="120"/></a>'
                    for v in items[:12]) + "</p>")
                out.append(f'<p><a href="{x(site["base_url"])}/daily/{date}/exploration.html#youtube_shorts" target="_blank" rel="noopener">All {len(items)} shorts</a></p>')
    return "".join(out)


def _digest_entries(repo: Repo, site: dict, examples: bool, limit: int | None, part: str) -> list[dict]:
    by_date: dict[str, dict] = {}
    for s in DAILY_STREAMS:
        for f in repo.iter_stream_files(s, examples):
            doc = load_json(f)
            by_date.setdefault(doc["date"], {})[s] = doc
    entries = []
    for date in sorted(by_date, reverse=True)[:limit]:
        streams = dict(by_date[date])
        names = next(ss for k, _, ss in render.DAILY_PARTS if k == part)
        if not any(s in streams and (streams[s].get("items") or streams[s].get("papers") or streams[s].get("briefs")) for s in names):
            continue
        labels = {"arxiv": "papers", "research_updates": "updates", "reading": "on the reading list", "world": "stories",
                  "discovery": "finds", "youtube_shorts": "shorts", "language": "language pack"}
        counts = [f"{len(streams[s].get('papers') or streams[s]['items'])} {labels[s]}"
                  for s in names if s in streams and (streams[s].get("papers") or streams[s].get("items"))]
        day = dt.date.fromisoformat(date)
        heading = next(lbl for k, lbl, _ in render.DAILY_PARTS if k == part)
        entries.append({
            "guid": f"dsys:{part}:{date}", "title": f"{heading}, {day.strftime('%a %-d %b')}: " + ", ".join(counts),
            "link": f"{site['base_url']}/daily/{date}/{part}.html", "description": "; ".join(counts),
            "html": _digest_html(site, date, streams, part), "pub": pub_datetime(day, site, -3600),
            "creator": None, "categories": [part], "media": None,
        })
    return entries


def collect_items(repo: Repo, feed: str, site: dict, examples: bool = False,
                  limit: int | None = None) -> list[dict]:
    """Return feed entries (newest first) as plain dicts, for one feed in FEEDS.

    research / news / exploration: one item per day. reading: one item per paper.
    <layer>-<part> (weekly, monthly, quarterly): one item per week, month or quarter, for that part only.
    File names are ISO dates, weeks or months, so a reverse sort reads the newest file first, and
    reading stops once the feed's window is full.
    """
    if feed in DIGEST_FEEDS:
        return _digest_entries(repo, site, examples, limit, feed)
    stream, _, part = feed.partition("-")
    entries = []
    for f in sorted(repo.iter_stream_files(stream, examples), reverse=True):
        if limit is not None and len(entries) >= limit:
            break
        doc = load_json(f)
        if stream == "reading":
            for i, pp in enumerate(doc["papers"]):
                group = {"trending": "Trending", "lab": pp.get("group") or "Leading group"}.get(pp.get("kind"), "For you")
                entries.append({
                    "guid": f"dsys:reading:{pp['id']}", "title": f"[{group}] {pp['title']}", "link": pp["url"],
                    "description": pp.get("note") or ", ".join(pp["tags"]),
                    "html": render.reading_list({"papers": [pp]}),
                    "pub": pub_datetime(dt.date.fromisoformat(pp["added"]), site, i),
                    "creator": ", ".join(pp.get("authors", [])[:6]) or None, "categories": [group] + pp["tags"], "media": None,
                })
        elif stream == "weekly":
            start, _ = week_bounds(doc["week"])
            its = [it for it in doc["items"] if render.weekly_part(it) == part]
            label = dict(render.WEEKLY_PARTS)[part]
            if part == "languages":
                its = [{"title": f"{ls['language'].capitalize()}: {ls['title']}"} for ls in doc.get("language", {}).get("lessons", [])]
            if its:
                entries.append({
                    "guid": f"{guid_for(stream, doc)}:{part}",
                    "title": f"Week of {start.strftime('%-d %b')}, {label.lower()}: "
                             + ", ".join(it["title"] for it in its[:3]) + ("…" if len(its) > 3 else ""),
                    "link": f"{site['base_url']}/weekly/{doc['week']}/{part}.html",
                    "description": doc["intro"], "html": render.weekly_package(doc, part),
                    "pub": pub_datetime(start, site), "creator": None, "categories": ["weekly", part], "media": None,
                })
        elif stream == "monthly":
            start, _ = month_bounds(doc["month"])
            titles = [pj["title"] for pj in doc["items"] if render.monthly_part(pj) == part]
            if part == "knowledge" and doc.get("challenges"):
                titles.append(f"{len(doc['challenges'])} challenge problems")
            if part == "languages":
                titles = [f"{pl['language'].capitalize()} plan" for pl in doc.get("language", {}).get("plans", [])]
            if titles:
                label = dict(render.MONTHLY_PARTS)[part]
                entries.append({
                    "guid": f"{guid_for(stream, doc)}:{part}",
                    "title": f"{start.strftime('%B %Y')}, {label.lower()}: " + ", ".join(titles),
                    "link": f"{site['base_url']}/monthly/{doc['month']}/{part}.html",
                    "description": doc["intro"], "html": render.monthly_package(doc, part),
                    "pub": pub_datetime(start, site), "creator": None, "categories": ["monthly", part], "media": None,
                })
        elif stream == "quarterly":
            qend = dt.date.fromisoformat(doc["to"])
            pt = doc["parts"][part]
            entries.append({
                "guid": f"{guid_for(stream, doc)}:{part}", "title": f"{doc['quarter']} review, {part}",
                "link": f"{site['base_url']}/quarterly/{doc['quarter']}/{part}.html",
                "description": pt["summary"] or "Nothing in this part this quarter.",
                "html": render.quarterly_review(doc, part) + render.quarterly_stats(doc),
                "pub": pub_datetime(qend + dt.timedelta(days=1), site), "creator": None,
                "categories": ["quarterly", part], "media": None,
            })
    entries.sort(key=lambda e: (e["pub"], e["guid"]), reverse=True)
    return entries[:limit] if limit is not None else entries


def build_feed(repo: Repo, stream: str, examples: bool = False) -> str:
    site = repo.config("site")
    render.configure(repo)
    policy = repo.config("recommendation_policy")
    window = int(policy.get("feeds", {}).get(stream, 100))
    meta = FEEDS[stream]
    entries = collect_items(repo, stream, site, examples, limit=window)
    self_url = f"{site['base_url']}/feeds/{meta['file']}"
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
        out.append(f"<content:encoded>{x(for_readers(e['html']))}</content:encoded>")
        if e["media"]:
            m = e["media"]
            out.append(f'<media:thumbnail url="{x(m["thumbnail"])}"/>')
            out.append(f'<media:content url="{x(m["player"])}" medium="video">'
                       f'<media:player url="{x(m["player"])}"/><media:title>{x(m["title"])}</media:title></media:content>')
        out.append("</item>")
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


def generate_all(repo: Repo, out_dir: Path | None = None, examples: bool = False) -> dict[str, Path]:
    """Write every feed in FEEDS. Returns feed key -> path."""
    out_dir = out_dir or repo.p("feeds")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.xml"):  # feeds that no longer exist must not linger
        if old.name not in {m["file"] for m in FEEDS.values()}:
            old.unlink()
    written = {}
    for feed, meta in FEEDS.items():
        path = out_dir / meta["file"]
        path.write_text(build_feed(repo, feed, examples), encoding="utf-8")
        written[feed] = path
    return written
