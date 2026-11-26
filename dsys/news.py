"""News candidates from publishers' public RSS/Atom feeds (stdlib only).

The World Radar run selects from these verified headlines instead of relying only on
web search, which gave too few items and missed whole areas such as markets.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import functools
import re
import urllib.parse
import xml.etree.ElementTree as ET

from . import net

ATOM = "{http://www.w3.org/2005/Atom}"
_TAG = re.compile(r"<[^>]+>")


_UTM = re.compile(r"([?&])(utm_[a-z]+|fbclid|gclid|mc_cid|mc_eid)=[^&#]*&?", re.I)


def clean(text: str, limit: int | None = None) -> str:
    """Strip tags and squeeze whitespace. Real text is kept whole unless a limit is asked for."""
    t = " ".join(html.unescape(_TAG.sub(" ", text or "")).split())
    if limit is None or len(t) <= limit:
        return t
    return t[:limit].rsplit(" ", 1)[0] + "…"


def canonical_url(url: str) -> str:
    """Drop tracking parameters (utm_*, fbclid, gclid) and a trailing ? or &."""
    u = _UTM.sub(lambda m: m.group(1), url or "").rstrip("?&")
    return u.replace("?&", "?")


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
        title = clean(it.findtext("title"))
        publisher = (it.findtext("source") or "").strip()  # Google News names the outlet here
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3].rstrip()
        summary = clean(it.findtext("description"))
        if publisher and summary.startswith(title):  # Google News repeats the headline as the summary
            summary = ""
        row = {"title": title, "url": canonical_url(link),
               "published": _date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
               "summary": summary}
        if publisher:
            row["publisher"] = publisher
        out.append(row)
    for e in root.iter(f"{ATOM}entry"):  # Atom
        link = ""
        for ln in e.findall(f"{ATOM}link"):
            if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                link = ln.get("href")
                break
        out.append({"title": clean(e.findtext(f"{ATOM}title")), "url": canonical_url(link),
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


# --- categorizing and merging duplicates (applied when the run reads candidates) -----------
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "as", "at", "by", "with", "is", "are", "after",
         "from", "over", "says", "say", "new", "its", "his", "her", "their", "be", "will", "has", "have", "amid"}


@functools.lru_cache(maxsize=2048)
def _kw(k: str) -> re.Pattern:
    return re.compile(rf"(?<![a-z0-9]){re.escape(k.lower().strip())}(?![a-z0-9])")


def categorize(item: dict, cfg: dict) -> str:
    """Pick the news category for a headline (see config/sources.json -> world.categories)."""
    cats = cfg.get("categories", {})
    feed_cat = cats.get("feed_default", {}).get(item.get("section", "world"), "geopolitics")
    if feed_cat == "explainers":
        return "explainers"
    title = (item.get("title") or "").lower()
    summary = (item.get("summary") or "").lower()
    # Local and minor signals (school boards, councils, sport) always win: they never make the radar.
    if any(_kw(k).search(title) for k in cats.get("keywords", {}).get("other", [])):
        return "other"
    order = cats.get("order", [])
    best, best_score = None, 0
    for cat in order:
        if cat == "explainers":
            continue
        score = 0
        for k in cats.get("keywords", {}).get(cat, []):
            pat = _kw(k)
            score += 2 * bool(pat.search(title)) + bool(pat.search(summary))
        score *= float(cats.get("weights", {}).get(cat, 1))
        if score > best_score:
            best, best_score = cat, score
    return best or feed_cat


def _tokens(title: str) -> set[str]:
    return {w for w in _WORD.findall(title.lower()) if w not in _STOP and len(w) > 2}


def merge_duplicates(items: list[dict], threshold: float = 0.34, min_shared: int = 3) -> list[dict]:
    """Headlines about the same event become one entry, with the other outlets in `also_in`."""
    out: list[dict] = []
    toks: list[set] = []
    for it in items:
        t = _tokens(it.get("title", ""))
        for i, other in enumerate(toks):
            shared = len(t & other)
            if t and other and shared >= min_shared and shared / len(t | other) >= threshold:
                out[i].setdefault("also_in", [])
                if len(out[i]["also_in"]) < 5:
                    out[i]["also_in"].append({"source": it.get("source"), "url": it.get("url")})
                break
        else:
            out.append(dict(it))
            toks.append(t)
    return out


def google_news_feeds(cfg: dict, interests: dict | None = None) -> list[dict]:
    """Expand config world.google_news into feed entries: topic sections for every edition
    (India and US by default), fixed searches, and searches built from config/interests.json."""
    g = cfg.get("google_news", {})
    if not g.get("enabled"):
        return []
    editions = g.get("editions") or [g.get("edition", {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"})]
    feeds = []
    for i, ed in enumerate(editions):
        tail = urllib.parse.urlencode(ed)
        tag = "" if i == 0 else f" ({ed.get('gl', '')})"
        feeds += [{"name": f"Google News {t['id'].title()}{tag}", "section": t["section"],
                   "url": f"https://news.google.com/rss/headlines/section/topic/{t['id']}?{tail}"}
                  for t in g.get("topics", [])]
        for q in g.get("queries", []):
            if i == 0 or q.get("all_editions"):
                feeds.append({"name": f"Google News: {q['q']}{tag}", "section": q["section"],
                              "url": f"https://news.google.com/rss/search?{urllib.parse.urlencode({'q': q['q'] + ' when:1d', **ed})}"})
        for j, batch in enumerate(interest_batches(interests or {}, g.get("interest_query", {}))):
            feeds.append({"name": f"Google News: interests {j + 1}{tag}", "section": "interest",
                          "url": f"https://news.google.com/rss/search?{urllib.parse.urlencode({'q': batch + ' when:1d', **ed})}"})
    for f in feeds:
        f["max_items"] = int(g.get("max_per_feed", 30))
    return feeds


def interest_batches(interests: dict, cfg: dict) -> list[str]:
    """('a' OR 'b' OR ...) searches from short interest phrases, a few per query."""
    groups = cfg.get("groups", ["established.ai_research", "growth.for_research", "exploration.subjects", "world.topics"])
    size, max_words = int(cfg.get("batch_size", 5)), int(cfg.get("max_words", 4))
    phrases = []
    for g in groups:
        node = interests
        for k in g.split("."):
            node = node.get(k, {}) if isinstance(node, dict) else {}
        for ph in node if isinstance(node, list) else []:
            ph = re.sub(r"\(.*?\)", "", ph).strip()
            single_generic = len(ph.split()) == 1 and ph.islower()  # "agents", "privacy": too noisy alone
            if ph and not single_generic and len(ph.split()) <= max_words and ph.lower() not in {p.lower() for p in phrases}:
                phrases.append(ph)
    return ["(" + " OR ".join(f'"{p}"' for p in phrases[i:i + size]) + ")" for i in range(0, len(phrases), size)]
