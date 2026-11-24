#!/usr/bin/env python3
"""Fetch raw candidates from official APIs into candidates/<kind>/<date>.json.

Runs in GitHub Actions (which has internet access). No AI calls here: this only
collects real metadata so the Claude generation step selects from verified data
instead of inventing it.

  python scripts/fetch_candidates.py arxiv            # public arXiv API, no key
  python scripts/fetch_candidates.py youtube          # needs YOUTUBE_API_KEY
  python scripts/fetch_candidates.py prune --keep-days 14
"""
import argparse
import datetime as dt
import os
import sys
import time

import _bootstrap  # noqa: F401
from dsys import arxiv as ax
from dsys.config import arxiv_categories
from dsys import youtube as yt
from dsys.core import load_json, repo_from_env, today, write_json


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_arxiv(repo, day: dt.date) -> int:
    sources = repo.config("sources")
    cfg = sources["arxiv"]
    cutoff = (day - dt.timedelta(days=int(cfg.get("lookback_days", 4)))).isoformat()
    overrides = cfg.get("max_results_overrides", {})
    by_id = {}
    errors = []
    for cat in arxiv_categories(sources):
        try:
            for p in ax.fetch_recent(cat, int(overrides.get(cat, cfg.get("max_results_per_category", 400)))):
                if p["submitted"] >= cutoff:
                    by_id.setdefault(p["arxiv_id"], p)
        except Exception as e:  # keep going; record the failure
            errors.append(f"{cat}: {e}")
    hf = sources.get("huggingface", {})
    if hf.get("enabled", True):
        for k in range(int(cfg.get("lookback_days", 4)) + 1):
            d = (day - dt.timedelta(days=k)).isoformat()
            try:
                for p in ax.fetch_hf_daily(d, hf.get("daily_papers_api", "https://huggingface.co/api/daily_papers")):
                    if p["arxiv_id"] in by_id:
                        by_id[p["arxiv_id"]]["hf_upvotes"] = max(by_id[p["arxiv_id"]].get("hf_upvotes", 0), p["hf_upvotes"])
                    else:
                        by_id[p["arxiv_id"]] = {**p, "categories": [], "source": "huggingface_daily"}
            except Exception as e:
                errors.append(f"huggingface {d}: {e}")
    # A re-run on the same day merges with the earlier file, so a rate-limited
    # re-run can never replace good candidates with a smaller set.
    path = repo.p("candidates", "arxiv", f"{day.isoformat()}.json")
    if path.exists():
        for p in load_json(path).get("candidates", []):
            by_id.setdefault(p["arxiv_id"], p)
    out = {"kind": "arxiv", "date": day.isoformat(), "fetched_at": now_utc(), "source": "export.arxiv.org API + Hugging Face Daily Papers",
           "errors": errors, "candidates": sorted(by_id.values(), key=lambda p: p["arxiv_id"], reverse=True)}
    write_json(path, out)
    print(f"arxiv: {len(by_id)} candidates, {len(errors)} errors")
    return 0 if by_id or not errors else 1


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
    ap.add_argument("kind", choices=["arxiv", "youtube", "prune"])
    ap.add_argument("--date")
    ap.add_argument("--keep-days", type=int, default=14)
    a = ap.parse_args()
    repo = repo_from_env()
    day = dt.date.fromisoformat(a.date) if a.date else today()
    if a.kind == "arxiv":
        return fetch_arxiv(repo, day)
    if a.kind == "youtube":
        return fetch_youtube(repo, day)
    return prune(repo, a.keep_days, day)


if __name__ == "__main__":
    sys.exit(main())
