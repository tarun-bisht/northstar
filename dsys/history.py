"""History derived from content (single source of truth) + planning context for prompts.

`rebuild` regenerates state/*_history.json from content files so history can never
drift from what was actually published. Only `paper_history.seen` (candidates that
were looked at but not selected) is not derivable and is preserved.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from . import diversity, profile
from . import ideas as ideas_mod
from .core import (DAILY_STREAMS, Repo, iso_week, load_json, month_of, next_month, next_week, today,
                   period_bounds, period_kind, write_json)
from .schedule import load_for_period


def _iter_daily(repo: Repo, stream: str):
    for f in repo.iter_stream_files(stream):
        doc = load_json(f)
        for it in doc["items"]:
            yield doc["date"], it


def rebuild(repo: Repo) -> dict[str, int]:
    counts = {}
    # papers
    ph_path = repo.state_path("paper_history")
    old = load_json(ph_path) if ph_path.exists() else {}
    selected = {it["arxiv_id"]: {"date": d, "title": it["title"], "relevance": it["relevance"]}
                for d, it in _iter_daily(repo, "arxiv")}
    seen = {k: v for k, v in sorted(old.get("seen", {}).items()) if k not in selected}
    write_json(ph_path, {"_doc": "Derived by `dsys history rebuild`. 'seen' = candidates reviewed but not selected.",
                         "selected": dict(sorted(selected.items())), "seen": seen})
    counts["papers_selected"], counts["papers_seen"] = len(selected), len(seen)

    # youtube
    videos, creators = {}, defaultdict(lambda: {"count": 0, "last": ""})
    for d, it in _iter_daily(repo, "youtube_shorts"):
        videos[it["video_id"]] = {"date": d, "channel": it["channel"]["name"], "title": it["title"],
                                  "category": it["category"]}
        c = creators[it["channel"]["name"]]
        c["count"] += 1
        c["last"] = max(c["last"], d)
    write_json(repo.state_path("youtube_history"),
               {"_doc": "Derived. Used to avoid repeating videos and over-using creators.",
                "videos": dict(sorted(videos.items())), "creators": dict(sorted(creators.items()))})
    counts["videos"] = len(videos)

    # recommendations (discovery + weekly + monthly + research/world titles for dedup)
    recs = {}
    for d, it in _iter_daily(repo, "discovery"):
        recs[f"discovery:{it['id']}"] = {"date": d, "title": it["title"], "url": it.get("url"),
                                         "category": it["category"], "type": it["type"], "dimensions": it["dimensions"]}
    for f in repo.iter_stream_files("weekly"):
        doc = load_json(f)
        for it in doc["items"]:
            recs[f"weekly:{it['id']}"] = {"date": doc["start_date"], "title": it["title"], "category": it["category"],
                                          "dimensions": it["dimensions"], "status": it["status"],
                                          "url": (it.get("paper") or {}).get("url")}
    for f in repo.iter_stream_files("monthly"):
        doc = load_json(f)
        for it in doc["items"]:
            recs[f"monthly:{it['id']}"] = {"date": doc["month"] + "-01", "title": it["title"], "category": it["kind"],
                                           "dimensions": it["dimensions"], "status": it["status"]}
    write_json(repo.state_path("recommendation_history"),
               {"_doc": "Derived. Everything recommended in discovery/weekly/monthly.",
                "items": dict(sorted(recs.items()))})
    counts["recommendations"] = len(recs)

    # topic exposure (qualitative balance signal, not a score)
    exposure = defaultdict(Counter)
    for key, r in recs.items():
        month = r["date"][:7]
        for p in r.get("dimensions", []):
            exposure[month][p] += 1
    prof = profile.load(repo)
    profile.recompute_ignored(prof, ignored_counts(repo, today()))
    profile.save(repo, prof)
    write_json(repo.state_path("topic_history"),
               {"_doc": "Derived. How often each dimension appeared per month. A variety signal, never a target.",
                "by_month": {m: dict(sorted(c.items())) for m, c in sorted(exposure.items())}})
    return counts


def mark_papers_seen(repo: Repo, ids: list[str], day: dt.date) -> int:
    path = repo.state_path("paper_history")
    doc = load_json(path) if path.exists() else {"selected": {}, "seen": {}}
    n = 0
    for i in ids:
        if i not in doc.get("selected", {}) and i not in doc.setdefault("seen", {}):
            doc["seen"][i] = day.isoformat()
            n += 1
    doc["seen"] = dict(sorted(doc["seen"].items()))
    write_json(path, doc)
    return n


def unseen_arxiv_candidates(repo: Repo, day: dt.date) -> dict:
    path = repo.p("candidates", "arxiv", f"{day.isoformat()}.json")
    if not path.exists():
        return {"date": day.isoformat(), "available": False, "candidates": []}
    cand = load_json(path)
    ph_path = repo.state_path("paper_history")
    ph = load_json(ph_path) if ph_path.exists() else {}
    known = set(ph.get("selected", {})) | set(ph.get("seen", {}))
    fresh = [c for c in cand.get("candidates", []) if c["arxiv_id"] not in known]
    return {"date": day.isoformat(), "available": True, "fetched_at": cand.get("fetched_at"),
            "total": len(cand.get("candidates", [])), "unseen": len(fresh), "candidates": fresh}


def unseen_youtube_candidates(repo: Repo, day: dt.date) -> dict:
    path = repo.p("candidates", "youtube", f"{day.isoformat()}.json")
    if not path.exists():
        return {"date": day.isoformat(), "available": False, "candidates": []}
    cand = load_json(path)
    yh_path = repo.state_path("youtube_history")
    known = set(load_json(yh_path).get("videos", {})) if yh_path.exists() else set()
    fresh = [c for c in cand.get("candidates", []) if c["video_id"] not in known]
    return {"date": day.isoformat(), "available": True, "fetched_at": cand.get("fetched_at"),
            "total": len(cand.get("candidates", [])), "unseen": len(fresh), "candidates": fresh}


def _recent(repo: Repo, stream: str, day: dt.date, days: int, fields: tuple[str, ...]):
    cutoff = (day - dt.timedelta(days=days)).isoformat()
    out = []
    for d, it in _iter_daily(repo, stream):
        if d >= cutoff:
            out.append({"date": d, **{k: it.get(k) for k in fields if it.get(k) is not None}})
    return out


def _planning_prefs(repo: Repo) -> dict:
    reg = ideas_mod.load(repo)
    dropped = [i["title"] for i in reg["ideas"] if i["status"] in ("dropped", "not_interested")]
    return profile.planning_view(profile.load(repo), dropped)


def _languages(repo: Repo) -> dict:
    p = repo.p("config", "languages.json")
    return load_json(p) if p.exists() else {}


def _interest_hint(repo: Repo) -> dict:
    i = repo.config("interests")
    tiers = {t: {k: v for k, v in (i.get(t) or {}).items() if not k.startswith("_")}
             for t in ("established", "growth", "exploration")}
    return {**tiers, "policy": repo.config("recommendation_policy").get("tiers", {})}


def ignored_counts(repo: Repo, day: dt.date) -> dict[str, int]:
    """Topics of past weekly/monthly items that were left untouched (no feedback, still 'suggested')."""
    counts: Counter = Counter()
    for stream in ("weekly", "monthly"):
        for f in repo.iter_stream_files(stream):
            doc = load_json(f)
            end = doc.get("end_date") or period_bounds(doc["month"])[1].isoformat()
            if end >= day.isoformat():
                continue  # period not over yet
            for it in doc["items"]:
                if it.get("status") == "suggested":
                    counts[profile.item_topic(it)] += 1
    return dict(counts)


def context(repo: Repo, stream: str, day: dt.date, period: str | None = None) -> dict:
    """Compact JSON a generator prompt reads before producing content."""
    policy = repo.config("recommendation_policy")
    win = policy.get("dedup_windows_days", {})
    ctx: dict = {"stream": stream, "date": day.isoformat(), "weekday": day.strftime("%A")}
    if stream == "arxiv":
        ctx["is_weekday"] = day.weekday() < 5
        ctx["candidates"] = {k: v for k, v in unseen_arxiv_candidates(repo, day).items() if k != "candidates"}
        ctx["recent_selected"] = _recent(repo, "arxiv", day, 30, ("arxiv_id", "title"))
    elif stream in ("research_updates", "world"):
        ctx["recent_items"] = _recent(repo, stream, day, int(win.get(stream, 14)),
                                      ("id", "title", "published", "follows_up"))
    elif stream == "discovery":
        ctx["recent_items"] = _recent(repo, "discovery", day, int(win.get("discovery", 365)),
                                      ("id", "title", "url", "category", "tier"))
        ctx["preferences"] = _planning_prefs(repo)
        ctx["variety"] = diversity.report(repo, day, 30)
        ctx["interests_hint"] = _interest_hint(repo)
    elif stream == "language":
        ctx["languages"] = _languages(repo)
        ctx["recent_packs"] = _recent(repo, "language", day, 60, ("language", "theme", "title"))
    elif stream == "youtube_shorts":
        ctx["candidates"] = {k: v for k, v in unseen_youtube_candidates(repo, day).items() if k != "candidates"}
        yh = repo.state_path("youtube_history")
        hist = load_json(yh) if yh.exists() else {"videos": {}, "creators": {}}
        ctx["known_video_count"] = len(hist["videos"])
        cutoff = (day - dt.timedelta(days=7)).isoformat()
        ctx["creators_used_last_7_days"] = {k: v for k, v in hist["creators"].items() if v["last"] >= cutoff}
        ctx["creator_soft_limit_per_day"] = win.get("youtube_creator_soft_limit_per_day", 3)
    elif stream in ("weekly", "monthly"):
        period = period or (iso_week(day) if stream == "weekly" else month_of(day))
        if period_kind(period) != stream:
            raise ValueError(f"period {period} does not match {stream}")
        start, end = period_bounds(period)
        ctx["period"] = period
        ctx["start"], ctx["end"] = start.isoformat(), end.isoformat()
        ctx["schedule"] = load_for_period(repo, period)
        reg = ideas_mod.load(repo)
        due = ideas_mod.due_for(reg, period)
        slim = lambda i: {k: i.get(k) for k in ("id", "title", "description", "status", "origin", "scope", "first_step",
                                                 "estimate", "notes", "reschedule_count", "dimensions") if i.get(k)}
        ctx["ideas_scheduled_for_this_period"] = [slim(i) for i in due["scheduled"]]
        ctx["ideas_resurfacing"] = [slim(i) for i in due["resurfacing"]]
        ctx["ideas_open_pool"] = [slim(i) for i in due["open"]]
        prev = next_week(period, -1) if stream == "weekly" else next_month(period, -1)
        prev_path = repo.weekly_path(prev) if stream == "weekly" else repo.monthly_path(prev)
        ctx["previous_period"] = prev
        if prev_path.exists():
            pdoc = load_json(prev_path)
            ctx["previous_items"] = [{"id": i["id"], "title": i["title"], "status": i["status"],
                                      "category": i.get("category") or i.get("kind")} for i in pdoc["items"]]
        fb = repo.feedback_path(prev)
        ctx["previous_feedback"] = load_json(fb) if fb.exists() else None
        ctx["preferences"] = _planning_prefs(repo)
        ctx["variety"] = diversity.report(repo, day, 60 if stream == "monthly" else 30)
        ctx["interests_hint"] = _interest_hint(repo)
        ctx["languages"] = _languages(repo)
        ctx["recent_language_themes"] = _recent(repo, "language", day, 60, ("language", "theme"))
        ctx["seed_rule"] = ("ideas_open_pool may include seeds (origin seed): they are suggestions, not intentions. "
                            "You may offer one as an optional item, but never mark it planned or schedule it. "
                            "Only ideas_scheduled_for_this_period reflect the user's explicit wish.")
        rh = repo.state_path("recommendation_history")
        if rh.exists():
            items = load_json(rh)["items"]
            ctx["already_recommended_titles"] = sorted({v["title"] for k, v in items.items()
                                                        if k.startswith(("weekly:", "monthly:", "discovery:"))})
        ctx["existing_item_ids"] = sorted(k.split(":", 1)[1] for k in (load_json(rh)["items"] if rh.exists() else {})
                                          if k.startswith(("weekly:", "monthly:")))
    return ctx
