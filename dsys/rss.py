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
_ABS_FOLD = re.compile(r'<details class="abs">.*?</details>', re.S)
_PLAY_FOLD = re.compile(r"<details class=\"play\">\s*<summary>Play here</summary>(.*?)</details>", re.S)
_UNSAFE = re.compile(r"<script\b.*?</script\s*>|<style\b.*?</style\s*>|<link\b[^>]*>|<script\b[^>]*/?>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")


def for_readers(html_body: str) -> str:
    """Make a fragment render well in RSS readers (Inoreader, FeedFlow, NetNewsWire...) with no
    JavaScript and no stylesheets:

    * <details> folds are opened (many readers drop them): players show directly, other summaries
      become a bold lead-in;
    * <script>, <style> and stylesheet links are removed (readers strip them anyway);
    * LaTeX becomes <sub>/<sup> or native MathML (dsys/mathfmt.py).
    """
    from .mathfmt import convert_html
    html_body = _UNSAFE.sub("", html_body)
    # abstract toggles are opened too: readers handle <details> unevenly and some lose the
    # title above it, so a feed always shows the abstract in full
    html_body = _ABS_FOLD.sub(lambda m: re.sub(r"</?details[^>]*>|<summary>.*?</summary>", "", m.group(0)), html_body)
    html_body = _PLAY_FOLD.sub(lambda m: m.group(1), html_body)
    html_body = _DETAILS_OPEN.sub(lambda m: f"<p><strong>{m.group(1)}</strong></p>", html_body)
    html_body = html_body.replace("</details>", "")
    return convert_html(html_body)


def plain_text(html_body: str, limit: int = 400) -> str:
    """A clean plain-text fallback for <description>: no tags, no entities, one line, cut at a word."""
    import html as _html
    t = " ".join(_html.unescape(_TAGS.sub(" ", html_body)).split())
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def cdata(s: str) -> str:
    """Wrap HTML in CDATA, splitting any ']]>' so the section can't end early."""
    return "<![CDATA[" + _CTRL.sub("", s).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _digest_html(site: dict, date: str, streams: dict, part: str) -> str:
    """One part of a day, on the shared feed template (dsys/feedhtml.py). Research and Exploration
    open with an Overview of at most five items, which the main list then leaves out."""
    from . import feedhtml as fh
    from . import overview
    label = next(lbl for k, lbl, _ in render.DAILY_PARTS if k == part)
    ov, rest = overview.split(streams, part) if part in overview.PARTS else ([], streams)
    body = {"research": lambda: fh.research(rest, ov), "news": lambda: fh.news(rest),
            "exploration": lambda: fh.exploration(rest, ov), "shorts": lambda: fh.shorts(rest),
            "languages": lambda: fh.languages(rest)}[part]()
    return fh.header(site, date, part, label) + body + fh.footer(site, date, part)


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
                    "guid": f"dsys:reading:{pp['id']}", "title": f"[{group}] {pp['title']}", "link": render.paper_link(pp["url"]),
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
        from .feedhtml import frame, polish
        html_in = e["html"]
        if stream not in DIGEST_FEEDS:  # daily parts already carry their header and footer
            html_in = frame(site, meta["title"], e["pub"].strftime("%-d %B %Y"), e["link"], html_in)
        body = polish(for_readers(html_in))
        out.append(f"<description>{x(plain_text(e['description'] or body))}</description>")
        out.append(f"<content:encoded>{cdata(body)}</content:encoded>")
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
