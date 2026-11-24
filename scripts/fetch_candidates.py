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

import _bootstrap  # noqa: F401
from dsys import arxiv as ax
from dsys.config import arxiv_categories
from dsys import news
from dsys import youtube as yt
from dsys.core import load_json, repo_from_env, today, write_json


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
    if len(p.get("abstract", "")) > len(old.get("abstract", "")) and old.get("source") != "arxiv_api":
        old["abstract"] = p["abstract"]
    for k in ("categories", "authors", "title", "submitted"):
        if not old.get(k) and p.get(k):
            old[k] = p[k]


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
        wanted.append("alphaxiv:trending")
    if retry_failed:
        if not prev:
            print("arxiv --retry-failed: no file for today yet, doing a full fetch")
        else:
            wanted = [s for s in wanted if s in set(prev.get("failed_sources", []))]
            if not wanted:
                print("arxiv --retry-failed: nothing failed today, nothing to do")
                return 0

    by_id: dict[str, dict] = {}
    errors, failed, notes = [], [], []
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
                for p in ax.fetch_alphaxiv(int(axv.get("limit", 50)), axv.get("sort", "Hot"), axv.get("interval", "7 Days")):
                    _merge(by_id, {**p, "categories": [], "source": "alphaxiv_trending"})
        except Exception as e:  # keep going; record the failure for --retry-failed
            errors.append(f"{src}: {e}")
            failed.append(src)

    # Merge with the earlier file of the day: a re-run can only add, never shrink.
    for p in prev.get("candidates", []):
        _merge(by_id, p)
    notable = {_norm_name(n) for n in sources.get("notable_researchers", {}).get("names", [])}
    for p in by_id.values():
        hits = [a for a in p.get("authors", []) if _norm_name(a) in notable]
        if hits:
            p["notable_authors"] = hits
        else:
            p.pop("notable_authors", None)
    still_failed = failed + ([s for s in prev.get("failed_sources", []) if s not in wanted] if prev else [])
    out = {"kind": "arxiv", "date": day.isoformat(), "fetched_at": now_utc(),
           "source": "export.arxiv.org API (rss.arxiv.org fallback) + Hugging Face Daily Papers + alphaXiv trending",
           "failed_sources": sorted(set(still_failed)), "errors": errors,
           "notes": (prev.get("notes", []) if retry_failed else []) + notes,
           "candidates": sorted(by_id.values(), key=lambda p: p["arxiv_id"], reverse=True)}
    write_json(path, out)
    print(f"arxiv: {len(by_id)} candidates, {len(failed)} sources failed {failed or ''}, {len(notes)} RSS fallbacks")
    return 0 if by_id or not errors else 1


def fetch_news(repo, day: dt.date, retry_failed: bool = False) -> int:
    """Headlines from config/sources.json -> world.feeds into candidates/news/<date>.json."""
    cfg = repo.config("sources").get("world", {})
    feeds = cfg.get("feeds", []) + news.google_news_feeds(cfg)
    path = repo.p("candidates", "news", f"{day.isoformat()}.json")
    prev = load_json(path) if path.exists() else {}
    if retry_failed and prev:
        failed_before = set(prev.get("failed_sources", []))
        feeds = [f for f in feeds if f["name"] in failed_before]
        if not feeds:
            print("news --retry-failed: nothing failed today, nothing to do")
            return 0
    now = dt.datetime.now(dt.timezone.utc)
    by_url = {c["url"]: c for c in prev.get("candidates", [])}
    errors, failed, counts = [], [], {}
    for f in feeds:
        try:
            got = news.select_recent(news.fetch(f["url"]), now, int(f.get("lookback_hours", cfg.get("lookback_hours", 36))))
            got = got[: int(f.get("max_items", cfg.get("max_per_feed", 40)))]
            counts[f["name"]] = len(got)
            for x in got:
                by_url.setdefault(x["url"], {**x, "source": x.pop("publisher", None) or f["name"], "feed": f["name"],
                                             "section": f.get("section", "world")})
        except Exception as e:  # keep going; record the failure for --retry-failed
            errors.append(f"{f['name']}: {e}")
            failed.append(f["name"])
        time.sleep(0.5)
    tried = {f["name"] for f in feeds}
    still_failed = failed + [s for s in prev.get("failed_sources", []) if s not in tried]
    cands = sorted(by_url.values(), key=lambda c: (c.get("published") or "", c["url"]), reverse=True)
    out = {"kind": "news", "date": day.isoformat(), "fetched_at": now_utc(), "source": "publisher RSS/Atom feeds",
           "failed_sources": sorted(set(still_failed)), "errors": errors,
           "per_feed": {**prev.get("per_feed", {}), **counts}, "candidates": cands}
    write_json(path, out)
    print(f"news: {len(cands)} headlines from {len(counts)} feeds, {len(failed)} feeds failed {failed or ''}")
    return 0 if cands or not errors else 1


def fetch_youtube(repo, day: dt.date) -> int:
    if not os.environ.get("YOUTUBE_API_KEY"):
        print("youtube: YOUTUBE_API_KEY not set — skipping (the generator will fall back to web search + oEmbed).")
        return 0
    cfg = repo.config("sources")["youtube"]
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(cfg.get("published_within_days", 60))))
    after_s = after.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ids, origin, errors = [], {}, []
    quota_hit = False
    for group in cfg.get("query_groups", []):
        lang = group["language"]
        for q in group["queries"]:
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
    write_json(repo.p("candidates", "youtube", f"{day.isoformat()}.json"), out)
    print(f"youtube: {len(kept)} candidates kept of {len(vids)} ({dropped}), {len(errors)} errors")
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
    ap.add_argument("kind", choices=["arxiv", "news", "youtube", "prune"])
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
    return prune(repo, a.keep_days, day)


if __name__ == "__main__":
    sys.exit(main())
