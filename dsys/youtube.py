"""YouTube helpers: ID validation, canonical URLs, optional Data API v3 client.

Legitimate access only:
  * YouTube Data API v3 (needs YOUTUBE_API_KEY; quota 10,000 units/day by default;
    search.list = 100 units, videos.list = 1 unit per call of up to 50 ids).
  * oEmbed (https://www.youtube.com/oembed) to confirm a video exists, no key needed.
No HTML scraping.
"""

from __future__ import annotations

import difflib
import http.client
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

from . import net

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
API = "https://www.googleapis.com/youtube/v3/"


def is_valid_id(video_id: str) -> bool:
    return isinstance(video_id, str) and bool(VIDEO_ID_RE.match(video_id))


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def shorts_url(video_id: str) -> str:
    return f"https://www.youtube.com/shorts/{video_id}"


def embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}"


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def oembed_url(video_id: str) -> str:
    return "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch_url(video_id), safe="")


def extract_id(url: str) -> str | None:
    """Pull an 11-char id from common YouTube URL shapes."""
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower()
    cand = None
    if host in ("youtu.be",):
        cand = u.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if u.path == "/watch":
            cand = urllib.parse.parse_qs(u.query).get("v", [None])[0]
        else:
            parts = [p for p in u.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                cand = parts[1]
    return cand if cand and is_valid_id(cand) else None


def url_errors(video: dict) -> list[str]:
    """Check that url / embed_url / thumbnail agree with video_id, and that the format claim has evidence."""
    vid = video.get("video_id", "")
    errs = []
    if not is_valid_id(vid):
        return [f"invalid YouTube video_id {vid!r}"]
    if extract_id(video.get("url", "")) != vid:
        errs.append(f"url {video.get('url')!r} does not point to video {vid}")
    fmt = video.get("format")
    if fmt == "short" and video.get("format_evidence") != "shorts_url_check":
        errs.append("format 'short' needs format_evidence 'shorts_url_check'; otherwise use 'short_form' or 'unknown'")
    if "/shorts/" in video.get("url", "") and fmt != "short":
        errs.append("a /shorts/ URL asserts the video is a Short; use the watch URL unless format is 'short'")
    if video.get("embed_url") != embed_url(vid):
        errs.append(f"embed_url must be {embed_url(vid)}")
    thumb = video.get("thumbnail", "")
    if "ytimg.com" in thumb and f"/vi/{vid}/" not in thumb:
        errs.append("thumbnail does not match video_id")
    return errs


def parse_iso8601_duration(s: str) -> int | None:
    m = re.match(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s or "")
    if not m:
        return None
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


# --- Data API (only used where network + key are available, e.g. GitHub Actions) ---
def _get(endpoint: str, params: dict, timeout: int = 20) -> dict:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY is not set")
    q = urllib.parse.urlencode({**params, "key": key})
    return json.loads(net.get(API + endpoint + "?" + q, timeout=timeout))  # 403 quota errors are not retried


def api_search(query: str, max_results: int, published_after: str, region: str, lang: str,
               duration: str = "short") -> list[str]:
    """search.list (100 quota units). relevanceLanguage biases, it does not filter."""
    data = _get("search", {
        "part": "id", "q": query, "type": "video", "videoDuration": duration,
        "maxResults": min(max_results, 50), "publishedAfter": published_after,
        "regionCode": region, "relevanceLanguage": lang, "safeSearch": "moderate",
        "order": "relevance",
    })
    return [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]


def api_videos(ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        data = _get("videos", {"part": "snippet,contentDetails,status", "id": ",".join(ids[i:i + 50])})
        for it in data.get("items", []):
            sn, cd = it.get("snippet", {}), it.get("contentDetails", {})
            if it.get("status", {}).get("embeddable") is False:
                continue
            out.append({
                "video_id": it["id"],
                "title": sn.get("title", ""),
                "channel": {"name": sn.get("channelTitle", ""), "id": sn.get("channelId", "")},
                "published": (sn.get("publishedAt") or "")[:10],
                "description": (sn.get("description") or "")[:600],
                "duration_seconds": parse_iso8601_duration(cd.get("duration", "")),
                "tags": sn.get("tags", [])[:10],
                "language": (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "").split("-")[0] or None,
                "made_for_kids": it.get("status", {}).get("madeForKids"),
            })
    return out


# --- Shorts classification ------------------------------------------------------------
def shorts_url_check(video_id: str, timeout: int = 10) -> str:
    """Classify via the public /shorts/<id> URL WITHOUT following redirects or reading the page.

    YouTube serves /shorts/<id> directly (200) for Shorts and redirects (3xx) other videos to
    /watch. This is undocumented behaviour, so any other outcome returns 'unknown' rather than
    guessing. Duration alone is never treated as proof.
    Returns 'short' | 'short_form' | 'unknown'.
    """
    if not is_valid_id(video_id):
        return "unknown"
    try:
        conn = http.client.HTTPSConnection("www.youtube.com", timeout=timeout)
        conn.request("HEAD", f"/shorts/{video_id}", headers={"User-Agent": "northstar/1.0"})
        status = conn.getresponse().status
        conn.close()
    except (OSError, http.client.HTTPException):
        return "unknown"
    if status == 200:
        return "short"
    if status in (301, 302, 303, 307, 308):
        return "short_form"
    return "unknown"


# --- Candidate filtering ----------------------------------------------------------------
def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"#\w+", " ", t)  # hashtags
    # strip punctuation/symbols only; keep letters AND combining marks (Devanagari matras etc.)
    t = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in t)
    return re.sub(r"\s+", " ", t).strip()


def near_duplicate(a: str, b: str, threshold: float = 0.9) -> bool:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return False
    return na == nb or difflib.SequenceMatcher(None, na, nb).ratio() >= threshold


def filter_candidates(cands: list[dict], known_ids: set[str], recent_titles: list[str], *,
                      max_duration: int = 180, per_channel: int = 5,
                      languages: tuple[str, ...] = ("en", "hi")) -> tuple[list[dict], dict]:
    """Drop invalid, already-seen, too-long, near-duplicate and over-represented candidates.

    Returns (kept, reasons) where reasons counts why items were dropped. Order is preserved.
    """
    kept, reasons, per_ch, titles = [], {}, {}, list(recent_titles)

    def drop(why):
        reasons[why] = reasons.get(why, 0) + 1

    for c in cands:
        vid = c.get("video_id", "")
        if not is_valid_id(vid):
            drop("invalid_id"); continue
        if vid in known_ids:
            drop("already_seen"); continue
        d = c.get("duration_seconds")
        if d and d > max_duration:
            drop("too_long"); continue
        lang = (c.get("language") or "").split("-")[0]
        if lang and lang not in languages:
            drop("language"); continue
        if any(near_duplicate(c.get("title", ""), t) for t in titles):
            drop("near_duplicate_title"); continue
        ch = (c.get("channel") or {}).get("id") or (c.get("channel") or {}).get("name", "")
        if per_ch.get(ch, 0) >= per_channel:
            drop("channel_cap"); continue
        per_ch[ch] = per_ch.get(ch, 0) + 1
        titles.append(c.get("title", ""))
        known_ids = known_ids | {vid}
        kept.append(c)
    return kept, reasons
