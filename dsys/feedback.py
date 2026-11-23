"""Feedback on weekly/monthly packages: record it, then apply decisions to state.

Principles enforced here:
  * nothing is carried forward unless a decision says so;
  * skipped / not_started with no decision simply expires (not overdue);
  * repeated rescheduling hits a limit and asks for reconsideration;
  * learned preferences are sanitized topic-level signals (state/preference_profile.json),
    never raw feedback text and never scores.
"""

from __future__ import annotations

import datetime as dt

from . import ideas as ideas_mod
from .core import Repo, load_json, next_month, next_week, period_kind, write_json

CONTINUE_DECISIONS = {"reschedule", "reduce_scope", "modify", "split", "keep_in_progress"}


def _package_path(repo: Repo, period: str):
    return repo.weekly_path(period) if period_kind(period) == "weekly" else repo.monthly_path(period)


def _next(period: str) -> str:
    return next_week(period) if period_kind(period) == "weekly" else next_month(period)


def record(repo: Repo, period: str, entries: list[dict], day: dt.date, *, general: dict | None = None) -> dict:
    """Create or merge the feedback file for a period. Later entries for the same item win."""
    pkg_path = _package_path(repo, period)
    if not pkg_path.exists():
        raise ValueError(f"no package for {period} at {pkg_path}")
    pkg_ids = {it["id"] for it in load_json(pkg_path)["items"]}
    for e in entries:
        if e["item_id"] not in pkg_ids:
            raise ValueError(f"{e['item_id']!r} is not an item of {period}")
    path = repo.feedback_path(period)
    doc = load_json(path) if path.exists() else {"schema": "feedback", "period": period, "date": day.isoformat(),
                                                   "entries": []}
    by_id = {e["item_id"]: e for e in doc["entries"]}
    for e in entries:
        by_id[e["item_id"]] = {**by_id.get(e["item_id"], {}), **e}
    doc["entries"] = sorted(by_id.values(), key=lambda e: e["item_id"])
    doc["date"] = day.isoformat()
    if general:
        g = doc.setdefault("general", {})
        for k in ("more_of", "less_of"):
            if general.get(k):
                g[k] = sorted(set(g.get(k, []) + general[k]))
        for k in ("notes",):
            if general.get(k):
                g[k] = (g.get(k, "") + "\n" + general[k]).strip()
    doc["applied"] = False
    write_json(path, doc)
    return doc


def apply(repo: Repo, period: str, day: dt.date, *, force: bool = False) -> list[str]:
    """Apply decisions in feedback/<period>.json to the package statuses and the ideas registry."""
    fpath = repo.feedback_path(period)
    fb = load_json(fpath)
    if fb.get("applied") and not force:
        return [f"{period}: feedback already applied (use --force to re-apply)"]
    policy = repo.config("recommendation_policy")
    limit = int(policy.get("reschedule_limit", 2))
    kind = period_kind(period)
    pkg_path = _package_path(repo, period)
    pkg = load_json(pkg_path)
    items = {it["id"]: it for it in pkg["items"]}
    reg = ideas_mod.load(repo)
    log: list[str] = []

    for e in fb["entries"]:
        it = items[e["item_id"]]
        it["status"] = e["status"]
        decision = e.get("decision") or ("done" if e["status"] == "completed" else "none")
        if e["status"] == "dropped" and decision == "none":
            decision = "drop"
        idea_id = it.get("idea_id")

        if decision in CONTINUE_DECISIONS and not idea_id:
            cand = f"idea-from-{it['id']}"[:120]
            if any(i["id"] == cand for i in reg["ideas"]):
                idea_id = cand
            else:
                ideas_mod.add(reg, it["title"], day, description=it.get("description", "")[:500],
                              scope=kind, status="interested", dimensions=it.get("dimensions"),
                              origin="feedback", idea_id=cand)
                idea_id = cand
                log.append(f"{it['id']}: created idea {idea_id} to hold the continuation")
            it["idea_id"] = idea_id

        if decision == "done":
            if idea_id:
                ideas_mod.set_status(reg, idea_id, "completed", day, f"completed in {period}")
            log.append(f"{it['id']}: done")
        elif decision in ("drop", "replace"):
            if idea_id:
                ideas_mod.set_status(reg, idea_id, "dropped", day,
                                     e.get("decision_note") or f"{decision} after {period}")
            log.append(f"{it['id']}: {decision}" + (" (next package should offer a fresh alternative)"
                                                    if decision == "replace" else ""))
        elif decision in CONTINUE_DECISIONS:
            target = e.get("decision_target") or _next(period)
            note = f"{decision} after {period}" + (f": {e['decision_note']}" if e.get("decision_note") else "")
            idea = ideas_mod.get(reg, idea_id)
            if decision == "keep_in_progress":
                idea["status"] = "in_progress"
                # continuing work in progress is not a reschedule of an untouched item
                prev = idea.get("scheduled_for")
                idea["scheduled_for"] = target
                if period_kind(target) != idea["scope"]:
                    idea["scope"] = period_kind(target)
                ideas_mod._event(idea, day, "continued", f"{prev} -> {target}: {note}")
                log.append(f"{it['id']}: keep in progress -> {target}")
            else:
                if decision in ("reduce_scope", "modify", "split"):
                    ideas_mod.note(reg, idea_id, note, day)
                try:
                    ideas_mod.schedule(reg, idea_id, target, day, limit=limit, note=note)
                    log.append(f"{it['id']}: {decision} -> {target}")
                except ideas_mod.RescheduleLimit:
                    ideas_mod.unschedule(reg, idea_id, day, status="interested")
                    ideas_mod.note(reg, idea_id, "Reschedule limit reached; needs reconsideration "
                                                 "(resize, replace, defer or drop) before planning again.", day)
                    log.append(f"{it['id']}: NOT rescheduled (limit {limit} reached) — flagged for reconsideration")
        else:
            # skipped / not_started / partially_completed without decision: let it go quietly
            if idea_id:
                idea = ideas_mod.get(reg, idea_id)
                if idea.get("scheduled_for") == period:
                    ideas_mod.unschedule(reg, idea_id, day, status="interested")
            log.append(f"{it['id']}: {e['status']}, no decision — not carried forward")

    write_json(pkg_path, pkg)
    ideas_mod.save(repo, reg)
    _learn(repo, fb, items, day)
    fb["applied"] = True
    write_json(fpath, fb)
    return log


def _learn(repo: Repo, fb: dict, items: dict, day: dt.date) -> None:
    """Fold sanitized, topic-level signals into state/preference_profile.json (no raw text, no scores)."""
    from . import profile
    doc = profile.load(repo)
    profile.update_from_feedback(doc, fb, items, day)
    profile.save(repo, doc)
