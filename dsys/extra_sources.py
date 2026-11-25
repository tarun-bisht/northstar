"""More candidate sources, fetched by GitHub Actions so scheduled runs only read files.

podcasts  latest episodes of shows in config/sources.json -> podcasts.shows (feed URLs looked up
          with the iTunes Search API), plus episode searches per topic. Each episode keeps its
          audio file (audio_url) so it plays on the page.
updates   research blogs, lab blogs and newsletters (RSS or Atom), Hacker News stories about AI
          (Algolia API) and r/MachineLearning top posts.
hf        Hugging Face trending models, datasets and spaces.

Every parser is defensive: a field that is missing is skipped, never invented.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

from . import net, news

ITUNES_SEARCH = "https://itunes.apple.com/search"
HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
HF_API = "https://huggingface.co/api"


def _json(url: str, timeout: int = 30):
    return json.loads(net.get(url, timeout=timeout, headers={"Accept": "application/json"}))


# --- podcasts ----------------------------------------------------------------------------
def itunes_show(name: str) -> dict | None:
    """The best iTunes match for a show name: its feed URL and Apple Podcasts page."""
    q = urllib.parse.urlencode({"term": name, "media": "podcast", "entity": "podcast", "limit": 5})
    rows = _json(f"{ITUNES_SEARCH}?{q}").get("results", [])
    want = re.sub(r"\W+", " ", name.lower()).strip()
    rows.sort(key=lambda r: re.sub(r"\W+", " ", str(r.get("collectionName", "")).lower()).strip() != want)
    for r in rows:
        if r.get("feedUrl"):
            return {"show": r.get("collectionName", name), "feed_url": r["feedUrl"],
                    "apple_url": r.get("collectionViewUrl"), "artist": r.get("artistName")}
    return None


def parse_podcast_feed(xml_text: str | bytes, show: str) -> list[dict]:
    """Episodes from a podcast RSS feed: title, page link, audio enclosure, date, summary."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out = []
    for item in root.iter("item"):
        enc = item.find("enclosure")
        audio = enc.get("url") if enc is not None and str(enc.get("type", "audio")).startswith("audio") else None
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        if not title or not (audio or link):
            continue
        desc = item.findtext("description") or item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}summary") or ""
        dur = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
        out.append({"show": show, "title": title, "url": link or None, "audio_url": audio,
                    "published": news._date(item.findtext("pubDate") or ""), "summary": news.clean(desc, 500),
                    **({"duration": dur.strip()} if dur else {})})
    return out


def parse_itunes_episodes(data: dict) -> list[dict]:
    out = []
    for r in data.get("results", []):
        if r.get("wrapperType") != "podcastEpisode" and r.get("kind") != "podcast-episode":
            continue
        if not r.get("trackName") or not (r.get("trackViewUrl") or r.get("episodeUrl")):
            continue
        ms = r.get("trackTimeMillis")
        out.append({"show": r.get("collectionName"), "title": " ".join(r["trackName"].split()),
                    "url": r.get("trackViewUrl"), "audio_url": r.get("episodeUrl"),
                    "published": str(r.get("releaseDate", ""))[:19] + "Z" if r.get("releaseDate") else None,
                    "summary": news.clean(r.get("shortDescription") or r.get("description") or "", 500),
                    **({"duration": f"{int(ms) // 60000} min"} if ms else {})})
    return out


def search_episodes(term: str, limit: int = 10) -> list[dict]:
    q = urllib.parse.urlencode({"term": term, "media": "podcast", "entity": "podcastEpisode", "limit": limit})
    return parse_itunes_episodes(_json(f"{ITUNES_SEARCH}?{q}"))


# --- research updates ----------------------------------------------------------------------
def parse_hn(data: dict, min_points: int = 50) -> list[dict]:
    out = []
    for h in data.get("hits", []):
        if not h.get("title") or int(h.get("points") or 0) < min_points:
            continue
        out.append({"source": "Hacker News", "title": h["title"],
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "discussion_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "points": int(h.get("points") or 0), "comments": int(h.get("num_comments") or 0),
                    "published": h.get("created_at")})
    return out


def fetch_hn(query: str, since: dt.datetime, min_points: int = 50) -> list[dict]:
    q = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": 50,
                                "numericFilters": f"created_at_i>{int(since.timestamp())},points>={min_points}"})
    return parse_hn(_json(f"{HN_SEARCH}?{q}"), min_points)


# --- Hugging Face trending -------------------------------------------------------------------
def parse_hf(rows: list, kind: str) -> list[dict]:
    out = []
    for r in rows if isinstance(rows, list) else []:
        rid = r.get("id") or r.get("modelId")
        if not rid:
            continue
        path = {"model": "", "dataset": "datasets/", "space": "spaces/"}[kind]
        out.append({"kind": kind, "id": rid, "url": f"https://huggingface.co/{path}{rid}",
                    **{k: r[k] for k in ("likes", "downloads", "trendingScore", "pipeline_tag", "createdAt") if r.get(k) is not None}})
    return out


def fetch_hf_trending(kind: str, limit: int = 20) -> list[dict]:
    q = urllib.parse.urlencode({"sort": "trendingScore", "direction": -1, "limit": limit})
    return parse_hf(_json(f"{HF_API}/{kind}s?{q}"), kind)
