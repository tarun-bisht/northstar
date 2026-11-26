#!/usr/bin/env python3
"""Fetch raw candidates from official APIs into candidates/<kind>/<date>.json.

Runs in GitHub Actions (which has internet access). No AI calls here: this only
collects real metadata so the Claude generation step selects from verified data
instead of inventing it.

  python scripts/fetch_candidates.py arxiv            # public arXiv API, no key
  python scripts/fetch_candidates.py news             # publisher RSS feeds, no key
  python scripts/fetch_candidates.py youtube          # needs YOUTUBE_API_KEY
  python scripts/fetch_candidates.py arxiv --retry-failed   # only what failed earlier today
  python scripts/fetch_candidates.py prune --keep-days 14
"""
import argparse
import datetime as dt
import os
import sys
import time
import unicodedata
import urllib.parse

import _bootstrap  # noqa: F401
from dsys import arxiv as ax
from dsys.config import arxiv_categories
from dsys import news
from dsys import extra_sources as xs
from dsys import feeds as fd
from dsys import reputation as rep
from dsys import youtube as yt
from dsys.core import load_json, repo_from_env, today, write_json


def write_candidates(path, data) -> None:
    """Candidate files are written compactly (no indentation): they are read by code, not people."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def net_status(e: Exception) -> str:
    from dsys import net
    return net.status_of(e)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _norm_name(n: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower().replace(".", " ").split())


def _merge(by_id: dict, p: dict) -> None:
    """Add a paper, or fold extra signals (upvotes, votes, sources) into the copy we have."""
    old = by_id.get(p["arxiv_id"])
    if old is None:
        by_id[p["arxiv_id"]] = p
        return
    for k in ("hf_upvotes", "alphaxiv_votes", "alphaxiv_visits"):
        if p.get(k):
            old[k] = max(old.get(k, 0), p[k])
    for k in ("reddit_mentions", "bluesky_mentions", "bluesky_likes"):
        if p.get(k):
            old[k] = max(old.get(k, 0), p[k])
    for k in ("alphaxiv_lists", "alphaxiv_interests", "organizations", "affiliations", "social_links"):
        if p.get(k):
            old[k] = sorted(set(old.get(k, [])) | set(p[k]))
    if len(p.get("abstract", "")) > len(old.get("abstract", "")) and old.get("source") != "arxiv_api":
        old["abstract"] = p["abstract"]
    for k in ("categories", "authors", "title", "submitted"):
        if not old.get(k) and p.get(k):
            old[k] = p[k]


def alphaxiv_feeds(axv: dict) -> list[dict]:
    """The alphaXiv lists to read: Hot, Likes, Twitter (X) discussion and GitHub stars by default."""
    return axv.get("feeds") or [{"sort": axv.get("sort", "Hot"), "interval": axv.get("interval", "7 Days"),
                                 "limit": axv.get("limit", 50)}]


def alphaxiv_interest_search(sources: dict, cfg: dict) -> tuple[dict, list]:
    """One alphaXiv search per interest in arxiv.coverage. Returns {interest: [papers]} and the misses."""
    out, misses = {}, []
    limit = int(cfg.get("limit_per_interest", 10))
    pause = float(cfg.get("pause_seconds", 1))
    for t in sources["arxiv"].get("coverage", {}).get("topics", []):
        query = t.get("search") or t["interest"]
        try:
            out[t["interest"]] = ax.search_alphaxiv(query, limit)
        except Exception as e:  # one bad query never costs the rest
            misses.append(f"{t['interest']} ({e})")
        time.sleep(pause)
    return out, misses


def fetch_arxiv(repo, day: dt.date, retry_failed: bool = False) -> int:
    """arXiv API per category (RSS fallback), Hugging Face Daily Papers and alphaXiv trending.

    Each source that fails after its retries is listed in `failed_sources`. A later run with
    --retry-failed fetches only those and merges, so one bad minute never costs a day.
    """
    sources = repo.config("sources")
    cfg = sources["arxiv"]
    lookback = int(cfg.get("lookback_days", 4))
    cutoff = (day - dt.timedelta(days=lookback)).isoformat()
    overrides = cfg.get("max_results_overrides", {})
    path = repo.p("candidates", "arxiv", f"{day.isoformat()}.json")
    prev = load_json(path) if path.exists() else {}
    hf = sources.get("huggingface", {})
    axv = sources.get("alphaxiv", {})

    wanted = [f"arxiv:{c}" for c in arxiv_categories(sources)]
    if hf.get("enabled", True):
        wanted += [f"huggingface:{(day - dt.timedelta(days=k)).isoformat()}" for k in range(lookback + 1)]
    if axv.get("enabled", True):
        wanted += [f"alphaxiv:{f['sort']}" for f in alphaxiv_feeds(axv)]
    if axv.get("search", {}).get("enabled", True):
        wanted.append("alphaxiv_search:interests")
    social = sources.get("paper_social", {})
    if social.get("reddit", {}).get("subreddits"):
        wanted.append("reddit:papers")
    if social.get("bluesky", {}).get("queries"):
        wanted.append("bluesky:papers")
    if retry_failed:
        if not prev:
            print("arxiv --retry-failed: no file for today yet, doing a full fetch")
        else:
            wanted = [s for s in wanted if s in set(prev.get("failed_sources", []))]
            if not wanted:
                print("arxiv --retry-failed: nothing failed today, nothing to do")
                return 0

    by_id: dict[str, dict] = {}
    interest_search: dict[str, list] = dict(prev.get("interest_search", {}))
    errors, failed, notes = [], [], []
    social_hits: dict[str, dict] = {}
    health = fd.FeedHealth(repo.p("state", "feed_health.json"), day)
    for src in wanted:
        kind, arg = src.split(":", 1)
        try:
            if kind == "arxiv":
                try:
                    got = ax.fetch_recent(arg, int(overrides.get(arg, cfg.get("max_results_per_category", 400))))
                    for p in got:
                        p.setdefault("source", "arxiv_api")
                except Exception as e:  # API down or rate limited: fall back to today's RSS list
                    got = ax.fetch_rss(arg)
                    notes.append(f"{arg}: API failed ({e}); used rss.arxiv.org ({len(got)} papers, today's list only)")
                for p in got:
                    if (p.get("submitted") or day.isoformat()) >= cutoff:
                        _merge(by_id, p)
            elif kind == "huggingface":
                for p in ax.fetch_hf_daily(arg, hf.get("daily_papers_api", "https://huggingface.co/api/daily_papers")):
                    _merge(by_id, {**p, "categories": [], "source": "huggingface_daily"})
            elif kind == "alphaxiv":
                f = next(f for f in alphaxiv_feeds(axv) if f["sort"] == arg)
                got, err = None, None
                for sort in [f["sort"]] + f.get("alternates", []):  # the API's name for a list can change
                    try:
                        got = ax.fetch_alphaxiv(int(f.get("limit", 50)), sort, f.get("interval", "7 Days"))
                        break
                    except Exception as e:
                        err = e
                if got is None:
                    raise err
                for p in got:
                    _merge(by_id, {**p, "categories": [], "source": "alphaxiv_trending", "alphaxiv_lists": [f["sort"]]})
            elif kind == "reddit":
                rc = social["reddit"]
                f = {"name": "reddit papers", **fd.reddit_feed(rc["subreddits"], rc.get("sort", "top"), rc.get("t", "day"))}
                (posts, err), = fd.fetch_many([f], fd.fetch_rss, health).values()
                if err:
                    raise err
                for post in posts:
                    for aid in fd.arxiv_ids(" ".join([post["title"], post.get("summary", ""), post["url"]])):
                        social_hits.setdefault(aid, {"reddit_mentions": 0, "social_links": set()})
                        social_hits[aid]["reddit_mentions"] = social_hits[aid].get("reddit_mentions", 0) + 1
                        social_hits[aid]["social_links"].add(post["url"])
            elif kind == "bluesky":
                bc = social["bluesky"]
                since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(bc.get("days", 2)))).strftime("%Y-%m-%dT%H:%M:%SZ")
                ok = 0
                for q in bc["queries"]:
                    try:
                        posts = fd.bluesky_search(q, 100, bc.get("sort", "top"), since)
                        ok += 1
                    except Exception as e:
                        notes.append(f"Bluesky search '{q}' failed ({net_status(e)})")
                        continue
                    for post in posts:
                        for aid in fd.arxiv_ids(" ".join([post["text"]] + post["links"])):
                            h = social_hits.setdefault(aid, {"social_links": set()})
                            h["bluesky_mentions"] = h.get("bluesky_mentions", 0) + 1
                            h["bluesky_likes"] = h.get("bluesky_likes", 0) + post["likes"]
                            h["social_links"].add(post["url"])
                if not ok:
                    raise RuntimeError("every Bluesky search failed")
            elif kind == "alphaxiv_search":
                interest_search, misses = alphaxiv_interest_search(sources, axv.get("search", {}))
                if misses and len(misses) == len(sources["arxiv"].get("coverage", {}).get("topics", [])):
                    raise RuntimeError(f"every alphaXiv search failed ({misses[0]})")
                notes += [f"alphaXiv search failed for: {', '.join(misses)}"] if misses else []
        except Exception as e:  # keep going; record the failure for --retry-failed
            errors.append(f"{src}: {e}")
            failed.append(src)

    # Papers people are talking about on Reddit and Bluesky: fetch the ones we don't have yet.
    missing = [a for a in social_hits if a not in by_id]
    if missing:
        try:
            for p in ax.fetch_ids(missing[:300]):
                _merge(by_id, {**p, "source": "social"})
        except Exception as e:
            notes.append(f"could not fetch {len(missing)} papers found on Reddit or Bluesky ({net_status(e)})")
    for aid, h in social_hits.items():
        if aid in by_id:
            _merge(by_id, {"arxiv_id": aid, **{k: (sorted(v)[:5] if isinstance(v, set) else v) for k, v in h.items()}})
    # Merge with the earlier file of the day: a re-run can only add, never shrink.
    for p in prev.get("candidates", []):
        _merge(by_id, p)
    registry = rep.load(repo)
    hits_by_id: dict[str, set] = {}
    for interest, rows in interest_search.items():
        for r in rows:
            hits_by_id.setdefault(r["arxiv_id"], set()).add(interest)
    notable = {_norm_name(n) for n in sources.get("notable_researchers", {}).get("names", [])}
    for p in by_id.values():
        if p["arxiv_id"] in hits_by_id:
            p["alphaxiv_interests"] = sorted(set(p.get("alphaxiv_interests", [])) | hits_by_id[p["arxiv_id"]])
        hits = [a for a in p.get("authors", []) if _norm_name(a) in notable]
        if hits:
            p["notable_authors"] = hits
        else:
            p.pop("notable_authors", None)
        rep.apply(registry, p)
    still_failed = failed + ([s for s in prev.get("failed_sources", []) if s not in wanted] if prev else [])
    out = {"kind": "arxiv", "date": day.isoformat(), "fetched_at": now_utc(),
           "source": "arXiv API (rss.arxiv.org fallback), Hugging Face Daily Papers, alphaXiv lists and search, Reddit, Bluesky",
           "failed_sources": sorted(set(still_failed)), "errors": errors,
           "notes": (prev.get("notes", []) if retry_failed else []) + notes,
           "candidates": sorted(by_id.values(), key=lambda p: p["arxiv_id"], reverse=True),
           "interest_search": interest_search}
    write_candidates(path, out)
    health.save()
    print(f"arxiv: {len(by_id)} candidates, {len(failed)} sources failed {failed or ''}, {len(notes)} RSS fallbacks")
    return 0 if by_id or not errors else 1


def _hn_front(url: str) -> list[dict]:
    import json as _json
    from dsys import net as _net
    data = _json.loads(_net.get(url, timeout=20, headers={"Accept": "application/json"}))
    return [{"title": h["title"], "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
             "published": h.get("created_at"), "summary": "",
             "points": int(h.get("points") or 0), "comments": int(h.get("num_comments") or 0),
             "discussion_url": f"https://news.ycombinator.com/item?id={h['objectID']}"}
            for h in data.get("hits", []) if h.get("title")]


def _feed_fn(f: dict):
    """How to read a feed: RSS/Atom by default, or a JSON API named in `type`."""
    if f.get("type") == "hn_front":
        return _hn_front
    if f.get("only_url_contains"):
        part = f["only_url_contains"]
        return lambda u: [x for x in fd.fetch_rss(u) if part in x["url"]]
    return fd.fetch_rss


def fetch_news(repo, day: dt.date, retry_failed: bool = False) -> int:
    """Headlines from publisher feeds, Google News (India and US, topics, fixed and interest
    searches), depth sources (The Conversation, Nature, Quanta), Hacker News and Reddit, fetched
    in parallel into candidates/news/<date>.json."""
    cfg = repo.config("sources").get("world", {})
    feeds = cfg.get("feeds", []) + news.google_news_feeds(cfg, repo.config("interests"))
    for r in cfg.get("reddit", []):
        feeds.append({"name": r["name"], "section": r.get("section", "world"), **fd.reddit_feed(r["subreddits"], r.get("sort", "top"), r.get("t", "day"))})
    path = repo.p("candidates", "news", f"{day.isoformat()}.json")
    prev = load_json(path) if path.exists() else {}
    if retry_failed and prev:
        failed_before = set(prev.get("failed_sources", []))
        feeds = [f for f in feeds if f["name"] in failed_before]
        if not feeds:
            print("news --retry-failed: nothing failed today, nothing to do")
            return 0
    now = dt.datetime.now(dt.timezone.utc)
    health = fd.FeedHealth(repo.p("state", "feed_health.json"), day)
    by_url = {c["url"]: c for c in prev.get("candidates", [])}
    errors, failed, counts = [], [], {}
    by_feed = {f["name"]: f for f in feeds}
    results = {}
    for f in feeds:  # feeds with a special reader are fetched one by one, the rest in parallel
        if f.get("type") or f.get("only_url_contains"):
            results.update(fd.fetch_many([f], _feed_fn(f), health))
    results.update(fd.fetch_many([f for f in feeds if not (f.get("type") or f.get("only_url_contains"))], fd.fetch_rss, health))
    for name, (items, err) in results.items():
        f = by_feed[name]
        if err is not None:
            errors.append(f"{name}: {net_status(err)}")
            failed.append(name)
            continue
        got = news.select_recent(items, now, int(f.get("lookback_hours", cfg.get("lookback_hours", 36))))
        got = got[: int(f.get("max_items", cfg.get("max_per_feed", 40)))]
        counts[name] = len(got)
        for x in got:
            row = {**x, "source": x.pop("publisher", None) or f["name"], "feed": name, "section": f.get("section", "world")}
            if f.get("depth"):
                row["depth"] = True
            by_url.setdefault(x["url"], row)
    tried = {f["name"] for f in feeds}
    still_failed = failed + [s for s in prev.get("failed_sources", []) if s not in tried]
    cands = sorted(by_url.values(), key=lambda c: (c.get("published") or "", c["url"]), reverse=True)
    out = {"kind": "news", "date": day.isoformat(), "fetched_at": now_utc(),
           "source": "publisher feeds, Google News (India and US), The Conversation, Nature, Quanta, Hacker News, Reddit",
           "failed_sources": sorted(set(still_failed)), "errors": errors,
           "per_feed": {**prev.get("per_feed", {}), **counts}, "candidates": cands}
    write_candidates(path, out)
    health.save()
    print(f"news: {len(cands)} headlines from {len(counts)} feeds, {len(failed)} feeds failed")
    return 0 if cands or not errors else 1



def _skip_no_key(repo, kind: str, day: dt.date) -> int:
    """Without YOUTUBE_API_KEY, write an empty file so the daily run sees the kind as done
    (instead of starting fetches again) and makes no shorts or videos. Never search instead."""
    print(f"{kind}: YOUTUBE_API_KEY not set, writing an empty file")
    write_candidates(repo.p("candidates", kind, f"{day.isoformat()}.json"),
                     {"kind": kind, "date": day.isoformat(), "fetched_at": now_utc(),
                      "skipped": "YOUTUBE_API_KEY not set", "failed_sources": [], "candidates": []})
    return 0

def fetch_youtube(repo, day: dt.date) -> int:
    if not os.environ.get("YOUTUBE_API_KEY"):
        return _skip_no_key(repo, "youtube", day)
    cfg = repo.config("sources")["youtube"]
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(cfg.get("published_within_days", 60))))
    after_s = after.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ids, origin, errors = [], {}, []
    quota_hit = False
    per_day = cfg.get("queries_per_day")
    for gi, group in enumerate(cfg.get("query_groups", [])):
        lang = group["language"]
        n = None if not per_day else max(1, round(per_day * len(group["queries"]) / sum(len(g["queries"]) for g in cfg["query_groups"])))
        for q in rotate(group["queries"], n, day):
            if quota_hit:
                break
            try:
                for vid in yt.api_search(q, int(cfg.get("max_results_per_query", 25)), after_s,
                                         cfg.get("region_code", "IN"), lang):
                    if vid not in origin:
                        origin[vid] = (q, lang)
                        ids.append(vid)
            except Exception as e:
                errors.append(f"{q}: {e}")
                if "quota" in str(e).lower() or "403" in str(e):
                    quota_hit = True
    vids = []
    try:
        for v in yt.api_videos(ids):
            q, qlang = origin.get(v["video_id"], (None, None))
            v["query"], v["query_language"] = q, qlang
            v["language"] = v.get("language") or qlang
            v["url"] = yt.watch_url(v["video_id"])
            v["embed_url"] = yt.embed_url(v["video_id"])
            v["thumbnail"] = yt.thumbnail_url(v["video_id"])
            vids.append(v)
    except Exception as e:
        errors.append(f"videos.list: {e}")

    # filter: already published, near-duplicate titles, too long, language, per-channel cap
    hist_p = repo.state_path("youtube_history")
    hist = load_json(hist_p) if hist_p.exists() else {"videos": {}}
    recent_titles = [h["title"] for h in hist.get("videos", {}).values()][-2000:]
    kept, dropped = yt.filter_candidates(
        vids, set(hist.get("videos", {})), recent_titles,
        max_duration=int(cfg.get("max_duration_seconds", 180)), per_channel=int(cfg.get("max_candidates_per_channel", 5)),
        languages=tuple(cfg.get("languages_accepted", ["en", "hi"])))

    # classify Shorts with evidence (never by duration alone)
    if cfg.get("shorts_url_check", True):
        for v in kept:
            fmt = yt.shorts_url_check(v["video_id"])
            v["format"] = fmt
            v["format_evidence"] = "shorts_url_check" if fmt != "unknown" else "none"
            if fmt == "short":
                v["url"] = yt.shorts_url(v["video_id"])
            time.sleep(0.2)
    else:
        for v in kept:
            v["format"], v["format_evidence"] = "unknown", "none"

    out = {"kind": "youtube", "date": day.isoformat(), "fetched_at": now_utc(), "source": "YouTube Data API v3",
           "errors": errors, "dropped": dropped, "candidates": sorted(kept, key=lambda v: v["video_id"])}
    write_candidates(repo.p("candidates", "youtube", f"{day.isoformat()}.json"), out)
    print(f"youtube: {len(kept)} candidates kept of {len(vids)} ({dropped}), {len(errors)} errors")
    return 0


def _recent(items: list[dict], now: dt.datetime, days: int) -> list[dict]:
    return news.select_recent(items, now, days * 24)


def fetch_podcasts(repo, day: dt.date) -> int:
    """Latest episodes of the shows in config, plus episode searches per topic, with audio files."""
    cfg = repo.config("sources").get("podcasts", {})
    now = dt.datetime.now(dt.timezone.utc)
    days = int(cfg.get("lookback_days", 14))
    eps, errors = [], []
    for sh in cfg.get("shows", []):
        try:
            info = xs.itunes_show(sh["name"])
            if not info:
                errors.append(f"{sh['name']}: not found on iTunes")
                continue
            got = _recent(xs.parse_podcast_feed(net_get(info["feed_url"]), info["show"]), now, days)
            for e in got[: int(cfg.get("per_show", 3))]:
                eps.append({**e, "tier": sh.get("tier"), "topics": sh.get("topics", []), "apple_show_url": info.get("apple_url"),
                            "url": e.get("url") or info.get("apple_url"), "via": "show feed"})
        except Exception as e:
            errors.append(f"{sh['name']}: {e}")
        time.sleep(float(cfg.get("pause_seconds", 0.5)))
    for f in cfg.get("feeds", []):  # shows whose feed URL we know: no iTunes lookup
        try:
            urls = [f["url"]] + f.get("alternates", [])
            got, last = None, None
            for u in urls:
                try:
                    got = xs.parse_podcast_feed(net_get(u), f["name"])
                    break
                except Exception as e:
                    last = e
            if got is None:
                raise last
            for e in _recent(got, now, days)[: int(cfg.get("per_show", 3))]:
                eps.append({**e, "tier": f.get("tier"), "topics": f.get("topics", []), "via": "show feed"})
        except Exception as e:
            errors.append(f"{f['name']}: {net_status(e)}")
    for t in cfg.get("episode_searches", []):
        try:
            for e in _recent(xs.search_episodes(t["term"], int(cfg.get("per_search", 8))), now, int(t.get("days", 60))):
                eps.append({**e, "tier": t.get("tier"), "topics": [t["term"]], "via": "iTunes episode search"})
        except Exception as e:
            errors.append(f"search {t['term']}: {e}")
        time.sleep(float(cfg.get("pause_seconds", 0.5)))
    seen, out = set(), []
    for e in eps:
        k = (e.get("show"), e["title"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    write_candidates(repo.p("candidates", "podcasts", f"{day.isoformat()}.json"),
               {"kind": "podcasts", "date": day.isoformat(), "fetched_at": now_utc(),
                "source": "show RSS feeds via iTunes Search API, iTunes episode search", "errors": errors, "candidates": out})
    print(f"podcasts: {len(out)} episodes, {len(errors)} errors")
    return 0 if out or not errors else 1


def net_get(url: str) -> bytes:
    from dsys import net
    return net.get(url, timeout=30)


def fetch_updates(repo, day: dt.date) -> int:
    """Research updates: lab and researcher feeds (with the Alan Turing Institute feeds for labs
    without one), Google News bridges (labs without feeds, X and LinkedIn posts), Substacks,
    Hacker News, Reddit and Bluesky, in parallel, into candidates/updates/<date>.json."""
    sources = repo.config("sources")
    cfg = sources.get("research_updates", {})
    now = dt.datetime.now(dt.timezone.utc)
    health = fd.FeedHealth(repo.p("state", "feed_health.json"), day)
    feeds = list(cfg.get("feeds", []))
    ed = urllib.parse.urlencode(cfg.get("google_news_edition", {"hl": "en-US", "gl": "US", "ceid": "US:en"}))
    for q in cfg.get("google_news_bridges", []):
        feeds.append({"name": f"Google News: {q['name']}", "kind": q.get("kind", "news"), "lookback_days": 1,
                      "url": f"https://news.google.com/rss/search?q={urllib.parse.quote(q['q'] + ' when:1d')}&{ed}"})
    for r in cfg.get("reddit", []):
        feeds.append({"name": r["name"], "kind": "discussion", "lookback_days": 2,
                      **fd.reddit_feed(r["subreddits"], r.get("sort", "top"), r.get("t", "day"))})
    items, errors = [], []
    for name, (got, err) in fd.fetch_many(feeds, fd.fetch_rss, health).items():
        f = next(x for x in feeds if x["name"] == name)
        if err is not None:
            errors.append(f"{name}: {net_status(err)}")
            continue
        for x in _recent(got, now, int(f.get("lookback_days", cfg.get("lookback_days", 7))))[:15]:
            items.append({**x, "source": x.pop("publisher", None) or f["name"], "feed": name, "kind": f.get("kind", "blog")})
    bs = cfg.get("bluesky", {})
    since = (now - dt.timedelta(days=int(bs.get("days", 1)))).strftime("%Y-%m-%dT%H:%M:%SZ")
    for q in bs.get("queries", []):
        try:
            for post in fd.bluesky_search(q, 50, "top", since):
                if post["likes"] >= int(bs.get("min_likes", 20)):
                    items.append({"title": post["text"][:300], "summary": post["text"], "url": post["url"], "source": "Bluesky",
                                  "author": post["author"], "links": post["links"][:3], "likes": post["likes"],
                                  "published": post["published"], "kind": "social", "feed": f"Bluesky: {q}"})
        except Exception as e:
            errors.append(f"Bluesky {q}: {net_status(e)}")
    hn = cfg.get("hacker_news", {})
    if hn.get("enabled", True):
        hsince = now - dt.timedelta(days=int(hn.get("lookback_days", 2)))
        for q in hn.get("queries", []):
            try:
                for x in xs.fetch_hn(q, hsince, int(hn.get("min_points", 80))):
                    items.append({**x, "kind": "discussion", "feed": "Hacker News"})
            except Exception as e:
                errors.append(f"Hacker News {q}: {net_status(e)}")
    seen, out_items = set(), []
    for x in items:  # one row per canonical URL and per headline
        key_u, key_t = news.canonical_url(x["url"]), " ".join(news._WORD.findall(x["title"].lower()))[:120]
        if key_u in seen or key_t in seen:
            continue
        seen |= {key_u, key_t}
        out_items.append(x)
    out = {"kind": "updates", "date": day.isoformat(), "fetched_at": now_utc(),
           "source": "lab and researcher feeds, Alan Turing Institute feeds, Google News bridges, Substacks, Hacker News, Reddit, Bluesky",
           "errors": errors, "candidates": out_items}
    write_candidates(repo.p("candidates", "updates", f"{day.isoformat()}.json"), out)
    health.save()
    print(f"updates: {len(out_items)} items, {len(errors)} sources failed")
    return 0 if out_items or not errors else 1


def fetch_enrich(repo, day: dt.date, ids: list[str]) -> int:
    """Page 1 of the given papers (arXiv HTML, else the PDF's first page): affiliations and email
    domains, then the trust flag. One request every 3 seconds, as arXiv asks. No retries."""
    path = repo.p("candidates", "affil", f"{day.isoformat()}.json")
    doc = load_json(path) if path.exists() else {"kind": "affil", "date": day.isoformat(), "papers": {}}
    registry = rep.load(repo)
    done = 0
    for aid in ids:
        if aid in doc["papers"]:
            continue
        info = fd.front_matter(aid)
        paper = {"authors": [], "affiliations": info["affiliations"], "email_domains": info["email_domains"]}
        rep.apply(registry, paper)
        doc["papers"][aid] = {**info, "trusted": paper["trusted"], **({"trust_matches": paper["trust_matches"]} if paper.get("trust_matches") else {})}
        done += 1
        time.sleep(3)
    doc["fetched_at"] = now_utc()
    write_candidates(path, doc)
    found = sum(1 for v in doc["papers"].values() if v["affiliations"] or v["email_domains"])
    print(f"enrich: {done} papers read, {found} of {len(doc['papers'])} with affiliations or emails")
    return 0


def fetch_addpapers(repo, day: dt.date, ids: list[str], tag: str) -> int:
    """Papers a run found on alphaXiv (its Hot and For You feeds through the alphaXiv connector):
    tag the ones we have, fetch the rest from the arXiv API, and merge into today's candidates."""
    path = repo.p("candidates", "arxiv", f"{day.isoformat()}.json")
    doc = load_json(path) if path.exists() else {"kind": "arxiv", "date": day.isoformat(), "candidates": []}
    by_id = {c["arxiv_id"]: c for c in doc["candidates"]}
    missing = [i for i in ids if i not in by_id]
    if missing:
        try:
            for p in ax.fetch_ids(missing):
                _merge(by_id, {**p, "source": "alphaxiv_feed"})
        except Exception as e:
            print(f"addpapers: arXiv API failed ({net_status(e)})")
    registry = rep.load(repo)
    for i in ids:
        if i in by_id:
            _merge(by_id, {"arxiv_id": i, "alphaxiv_lists": [tag]})
            rep.apply(registry, by_id[i])
    doc["candidates"] = sorted(by_id.values(), key=lambda p: p["arxiv_id"], reverse=True)
    doc.setdefault("notes", []).append(f"{len(ids)} papers from {tag} ({len(missing)} new)")
    write_candidates(path, doc)
    print(f"addpapers: {len(ids)} from {tag}, {len(missing)} new")
    return 0


def fetch_fun(repo, day: dt.date) -> int:
    """Today's latest xkcd and one random older one, for the #random channel."""
    import random as _r
    try:
        latest = fd.xkcd()
        old = fd.xkcd(_r.Random(day.toordinal()).randint(1, max(1, latest["num"] - 1)))
    except Exception as e:
        print(f"fun: xkcd failed ({net_status(e)})")
        return 0
    write_candidates(repo.p("candidates", "fun", f"{day.isoformat()}.json"),
                     {"kind": "fun", "date": day.isoformat(), "fetched_at": now_utc(), "xkcd_latest": latest, "xkcd_random": old})
    print(f"fun: xkcd {latest['num']} and {old['num']}")
    return 0


def fetch_hf(repo, day: dt.date) -> int:
    cfg = repo.config("sources").get("huggingface", {}).get("trending", {})
    out, errors = {}, []
    for kind in cfg.get("kinds", ["model", "dataset", "space"]):
        try:
            out[kind + "s"] = xs.fetch_hf_trending(kind, int(cfg.get("limit", 20)))
        except Exception as e:
            errors.append(f"{kind}s: {e}")
    write_candidates(repo.p("candidates", "hf", f"{day.isoformat()}.json"),
               {"kind": "hf", "date": day.isoformat(), "fetched_at": now_utc(), "source": "Hugging Face API (trendingScore)",
                "errors": errors, **out})
    print(f"hf: {sum(len(v) for v in out.values())} trending, {len(errors)} errors")
    return 0 if out else 1


def rotate(queries: list[str], n: int | None, day: dt.date) -> list[str]:
    """A different slice of the queries each day, so all of them come round without spending more quota."""
    if not n or n >= len(queries):
        return list(queries)
    start = (day.toordinal() * n) % len(queries)
    return (queries + queries)[start:start + n]


def _channel_ids(repo, handles: list[str], errors: list) -> dict[str, str]:
    """Handle -> channel id, cached in state/youtube_channels.json (1 quota unit per new handle)."""
    import json as _json
    path = repo.p("state", "youtube_channels.json")
    cache = _json.loads(path.read_text()) if path.exists() else {}
    for h in handles:
        if h in cache:
            continue
        try:
            cid = yt.channel_id_for_handle(h)
            if cid:
                cache[h] = cid
            else:
                errors.append(f"channel {h}: not found")
        except Exception as e:
            errors.append(f"channel {h}: {net_status(e)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(cache, indent=1, sort_keys=True) + "\n")
    return {h: cache[h] for h in handles if h in cache}


def fetch_long_videos(repo, day: dt.date) -> int:
    """Videos for Daily Discovery: new uploads from curated channels (free RSS feeds) plus a
    rotating long-form search. Each video carries views, likes, comments, engagement rates and
    reach against its channel's size, so the run chooses from data without watching."""
    if not os.environ.get("YOUTUBE_API_KEY"):
        return _skip_no_key(repo, "videos", day)
    yc = repo.config("sources")["youtube"]
    cfg = yc.get("long_form", {})
    ch = yc.get("channels", {})
    errors, origin, ids = [], {}, []
    since = (day - dt.timedelta(days=int(ch.get("lookback_days", 7)))).isoformat()
    for h, cid in _channel_ids(repo, ch.get("handles", []), errors).items():
        try:
            for vid, pub in yt.channel_feed_ids(cid):
                if pub >= since and vid not in origin:
                    origin[vid] = f"channel {h}"
                    ids.append(vid)
        except Exception as e:
            errors.append(f"feed {h}: {net_status(e)}")
    if cfg.get("enabled", True):
        after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(cfg.get("published_within_days", 365))))
        after_s = after.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        for q in rotate(cfg.get("queries", []), cfg.get("queries_per_day"), day):
            try:
                for vid in yt.api_search(q, int(cfg.get("max_results_per_query", 10)), after_s, "IN", "en", duration="long"):
                    if vid not in origin:
                        origin[vid] = q
                        ids.append(vid)
            except Exception as e:
                errors.append(f"{q}: {net_status(e)}")
                if "403" in str(e):
                    break
    vids = []
    try:
        raw = yt.api_videos(ids)
        subs = yt.api_channels(sorted({v["channel"]["id"] for v in raw if v["channel"].get("id")}))
        for v in raw:
            if (v.get("duration_seconds") or 0) < int(cfg.get("min_duration_seconds", 240)):
                continue
            s = subs.get(v["channel"].get("id"), {}).get("subscribers")
            v.update(query=origin.get(v["video_id"]), url=yt.watch_url(v["video_id"]), embed_url=yt.embed_url(v["video_id"]),
                     thumbnail=yt.thumbnail_url(v["video_id"]), channel_subscribers=s, **yt.quality(v, s))
            vids.append(v)
    except Exception as e:
        errors.append(f"videos.list: {net_status(e)}")
    write_candidates(repo.p("candidates", "videos", f"{day.isoformat()}.json"),
                     {"kind": "videos", "date": day.isoformat(), "fetched_at": now_utc(),
                      "source": "YouTube channel RSS feeds and Data API v3", "errors": errors, "candidates": vids})
    print(f"videos: {len(vids)} candidates, {len(errors)} errors")
    return 0


def prune(repo, keep_days: int, day: dt.date) -> int:
    cutoff = (day - dt.timedelta(days=keep_days)).isoformat()
    n = 0
    for f in sorted(repo.p("candidates").rglob("*.json")):
        if f.stem < cutoff:
            f.unlink()
            n += 1
    print(f"pruned {n} old candidate files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["arxiv", "news", "youtube", "videos", "podcasts", "updates", "hf", "fun", "enrich", "addpapers", "prune"])
    ap.add_argument("--ids", default="", help="enrich, addpapers: comma-separated arXiv ids")
    ap.add_argument("--tag", default="alphaXiv", help="addpapers: which alphaXiv feed they came from")
    ap.add_argument("--date")
    ap.add_argument("--keep-days", type=int, default=14)
    ap.add_argument("--retry-failed", action="store_true",
                    help="arxiv: refetch only sources that failed earlier today. youtube: fetch only if today's file is missing or empty")
    a = ap.parse_args()
    repo = repo_from_env()
    day = dt.date.fromisoformat(a.date) if a.date else today()
    if a.kind == "arxiv":
        return fetch_arxiv(repo, day, a.retry_failed)
    if a.kind == "news":
        return fetch_news(repo, day, a.retry_failed)
    if a.kind == "youtube":
        f = repo.p("candidates", "youtube", f"{day.isoformat()}.json")
        if a.retry_failed and f.exists() and load_json(f).get("candidates"):
            print("youtube --retry-failed: today's candidates already exist, nothing to do")
            return 0
        return fetch_youtube(repo, day)
    if a.kind == "enrich":
        return fetch_enrich(repo, day, [x.strip() for x in a.ids.split(",") if x.strip()])
    if a.kind == "addpapers":
        return fetch_addpapers(repo, day, [x.strip() for x in a.ids.split(",") if x.strip()], a.tag)
    if a.kind == "fun":
        return fetch_fun(repo, day)
    simple = {"videos": fetch_long_videos, "podcasts": fetch_podcasts, "updates": fetch_updates, "hf": fetch_hf}
    if a.kind in simple:
        f = repo.p("candidates", a.kind, f"{day.isoformat()}.json")
        if a.retry_failed and f.exists() and (load_json(f).get("candidates") or load_json(f).get("models")):
            print(f"{a.kind} --retry-failed: today's file already has candidates, nothing to do")
            return 0
        return simple[a.kind](repo, day)
    return prune(repo, a.keep_days, day)


if __name__ == "__main__":
    sys.exit(main())
