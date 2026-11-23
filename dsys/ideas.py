"""Ideas & interests registry: the user's own ideas plus seeds, with a gentle lifecycle.

Statuses: curiosity, interested, wants_to_try, planned, in_progress, completed,
deferred, dropped, not_interested. Nothing here creates obligations: an idea only
enters a weekly/monthly package when it is scheduled_for that period, and even then
it stays optional.
"""

from __future__ import annotations

import datetime as dt

from .core import (Repo, load_json, period_bounds, period_kind, slugify, write_json)

IDEA_STATUSES = ["curiosity", "interested", "wants_to_try", "planned", "in_progress", "completed",
                 "deferred", "dropped", "not_interested"]
ACTIVE = {"planned", "in_progress"}
CLOSED = {"completed", "dropped", "not_interested"}
# Statuses that express the user's own intent. Seeds and system suggestions may never
# start in these; only an explicit user action (status/schedule command) moves them there.
EXPLICIT_INTENT = {"wants_to_try", "planned", "in_progress"}
EXPLICIT_ACTIONS = {"status", "scheduled", "rescheduled", "continued"}
NON_USER_ORIGINS = {"seed", "system"}


class IdeaError(ValueError):
    pass


class RescheduleLimit(IdeaError):
    pass


def _path(repo: Repo):
    return repo.state_path("ideas")


def load(repo: Repo) -> dict:
    p = _path(repo)
    if not p.exists():
        return {"_doc": "Your ideas and interests. Edit via `python scripts/dsys.py ideas ...`, inbox/ideas.md, or by hand.",
                "ideas": []}
    return load_json(p)


def save(repo: Repo, reg: dict) -> None:
    reg["ideas"].sort(key=lambda i: (i["created"], i["id"]))
    write_json(_path(repo), reg)


def get(reg: dict, idea_id: str) -> dict:
    for i in reg["ideas"]:
        if i["id"] == idea_id:
            return i
    raise IdeaError(f"no idea with id {idea_id!r}")


def _event(idea: dict, day: dt.date, action: str, detail: str | None = None) -> None:
    ev = {"date": day.isoformat(), "action": action}
    if detail:
        ev["detail"] = detail
    idea.setdefault("history", []).append(ev)
    idea["updated"] = day.isoformat()


def _unique_id(reg: dict, title: str) -> str:
    base = "idea-" + slugify(title, 50)
    ids = {i["id"] for i in reg["ideas"]}
    if base not in ids:
        return base
    n = 2
    while f"{base}-{n}" in ids:
        n += 1
    return f"{base}-{n}"


def add(reg: dict, title: str, day: dt.date, *, description: str = "", scope: str = "undecided",
        status: str = "interested", dimensions: list[str] | None = None, origin: str = "user",
        first_step: str | None = None, estimate: str | None = None, tags: list[str] | None = None,
        idea_id: str | None = None) -> dict:
    if status not in IDEA_STATUSES:
        raise IdeaError(f"invalid status {status!r}")
    if scope not in ("weekly", "monthly", "either", "undecided"):
        raise IdeaError(f"invalid scope {scope!r}")
    if origin in NON_USER_ORIGINS and status in EXPLICIT_INTENT:
        raise IdeaError(f"a {origin} idea cannot start as {status!r}; seeds are curiosity or interested until "
                        "the user says otherwise")
    idea = {
        "id": idea_id or _unique_id(reg, title),
        "title": title.strip(),
        "status": status,
        "origin": origin,
        "scope": scope,
        "created": day.isoformat(),
        "updated": day.isoformat(),
        "reschedule_count": 0,
    }
    if any(i["id"] == idea["id"] for i in reg["ideas"]):
        raise IdeaError(f"idea id {idea['id']!r} already exists")
    if description:
        idea["description"] = description
    if dimensions:
        idea["dimensions"] = sorted(set(dimensions))
    if first_step:
        idea["first_step"] = first_step
    if estimate:
        idea["estimate"] = estimate
    if tags:
        idea["tags"] = tags
    _event(idea, day, "added", f"origin={origin}, status={status}, scope={scope}")
    reg["ideas"].append(idea)
    return idea


def set_status(reg: dict, idea_id: str, status: str, day: dt.date, note: str | None = None) -> dict:
    if status not in IDEA_STATUSES:
        raise IdeaError(f"invalid status {status!r}; choose from {', '.join(IDEA_STATUSES)}")
    idea = get(reg, idea_id)
    old = idea["status"]
    idea["status"] = status
    if status in CLOSED or status in ("curiosity", "interested", "wants_to_try"):
        idea.pop("scheduled_for", None)
    if status != "deferred":
        idea.pop("deferred_until", None)
    _event(idea, day, "status", f"{old} -> {status}" + (f": {note}" if note else ""))
    return idea


def schedule(reg: dict, idea_id: str, period: str, day: dt.date, *, limit: int = 2,
             force: bool = False, note: str | None = None) -> dict:
    """Put an idea into a specific week (YYYY-Www) or month (YYYY-MM)."""
    kind = period_kind(period)  # validates format
    period_bounds(period)
    idea = get(reg, idea_id)
    if idea["status"] in CLOSED:
        raise IdeaError(f"idea {idea_id!r} is {idea['status']}; reopen it first (ideas status ... interested)")
    previously = idea.get("scheduled_for")
    is_reschedule = previously is not None and previously != period
    if is_reschedule and idea.get("reschedule_count", 0) >= limit and not force:
        raise RescheduleLimit(
            f"idea {idea_id!r} has already been rescheduled {idea['reschedule_count']} times. "
            "Reconsider it instead: resize, replace, defer, or drop it (or pass --force).")
    if is_reschedule:
        idea["reschedule_count"] = idea.get("reschedule_count", 0) + 1
    idea["scheduled_for"] = period
    if idea["scope"] in ("undecided", "either") or idea["scope"] != kind:
        idea["scope"] = kind
    if idea["status"] != "in_progress":
        idea["status"] = "planned"
    idea.pop("deferred_until", None)
    _event(idea, day, "rescheduled" if is_reschedule else "scheduled",
           f"{previously + ' -> ' if is_reschedule else ''}{period}" + (f": {note}" if note else ""))
    return idea


def unschedule(reg: dict, idea_id: str, day: dt.date, status: str = "interested") -> dict:
    idea = get(reg, idea_id)
    idea.pop("scheduled_for", None)
    idea["status"] = status
    _event(idea, day, "unscheduled", f"status={status}")
    return idea


def defer(reg: dict, idea_id: str, day: dt.date, until: str | None = None, note: str | None = None) -> dict:
    idea = get(reg, idea_id)
    idea["status"] = "deferred"
    idea.pop("scheduled_for", None)
    if until:
        dt.date.fromisoformat(until)
        idea["deferred_until"] = until
    _event(idea, day, "deferred", (f"until {until}" if until else "no date") + (f": {note}" if note else ""))
    return idea


def drop(reg: dict, idea_id: str, day: dt.date, reason: str | None = None, not_interested: bool = False) -> dict:
    return set_status(reg, idea_id, "not_interested" if not_interested else "dropped", day, reason)


def resize(reg: dict, idea_id: str, scope: str, day: dt.date, note: str | None = None) -> dict:
    if scope not in ("weekly", "monthly", "either", "undecided"):
        raise IdeaError(f"invalid scope {scope!r}")
    idea = get(reg, idea_id)
    old = idea["scope"]
    idea["scope"] = scope
    sf = idea.get("scheduled_for")
    if sf and scope in ("weekly", "monthly") and period_kind(sf) != scope:
        idea.pop("scheduled_for")
        if idea["status"] == "planned":
            idea["status"] = "interested"
    if note:
        idea["notes"] = (idea.get("notes", "") + f"\n[{day}] resized: {note}").strip()
    _event(idea, day, "resized", f"{old} -> {scope}" + (f": {note}" if note else ""))
    return idea


def replace(reg: dict, idea_id: str, new_title: str, day: dt.date, **kwargs) -> dict:
    old = get(reg, idea_id)
    kwargs.setdefault("scope", old["scope"])
    kwargs.setdefault("dimensions", old.get("dimensions"))
    new = add(reg, new_title, day, origin=kwargs.pop("origin", old["origin"]), **kwargs)
    old["replaced_by"] = new["id"]
    set_status(reg, idea_id, "dropped", day, f"replaced by {new['id']}")
    return new


def remove(reg: dict, idea_id: str) -> dict:
    idea = get(reg, idea_id)
    reg["ideas"] = [i for i in reg["ideas"] if i["id"] != idea_id]
    for i in reg["ideas"]:
        if i.get("replaced_by") == idea_id:
            i.pop("replaced_by")
    return idea


def note(reg: dict, idea_id: str, text: str, day: dt.date) -> dict:
    idea = get(reg, idea_id)
    idea["notes"] = (idea.get("notes", "") + f"\n[{day}] {text}").strip()
    _event(idea, day, "note", text[:200])
    return idea


def explicit_intent_errors(reg: dict) -> list[str]:
    """Seed/system ideas in an explicit-intent status without a recorded explicit action."""
    out = []
    for i in reg.get("ideas", []):
        if i.get("origin") in NON_USER_ORIGINS and i.get("status") in EXPLICIT_INTENT:
            if not any(e.get("action") in EXPLICIT_ACTIONS for e in i.get("history", [])):
                out.append(f"idea {i['id']!r} ({i['origin']}) is {i['status']!r} without an explicit user action")
    return out


def due_for(reg: dict, period: str) -> dict:
    """What planning for `period` must consider.

    scheduled: ideas explicitly scheduled for this period (must be included, user intent wins)
    resurfacing: deferred ideas whose date has arrived (consider, don't force)
    open: interested / wants_to_try ideas whose scope fits (optional pool)
    """
    kind = period_kind(period)
    start, end = period_bounds(period)
    scheduled, resurfacing, open_pool = [], [], []
    for i in reg["ideas"]:
        if i.get("scheduled_for") == period and i["status"] not in CLOSED:
            scheduled.append(i)
        elif i["status"] == "deferred" and i.get("deferred_until") and \
                dt.date.fromisoformat(i["deferred_until"]) <= end:
            resurfacing.append(i)
        elif i["status"] in ("interested", "wants_to_try", "curiosity") and i["scope"] in (kind, "either", "undecided"):
            open_pool.append(i)
    # wants_to_try (explicit) first, then the user's own ideas, then seeds
    rank = {"wants_to_try": 0, "interested": 1, "curiosity": 2}
    open_pool.sort(key=lambda i: (rank.get(i["status"], 3), i.get("origin") in NON_USER_ORIGINS, i["id"]))
    return {"period": period, "scheduled": scheduled, "resurfacing": resurfacing, "open": open_pool}
