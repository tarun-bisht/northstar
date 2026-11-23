"""Sanitized preference profile (state/preference_profile.json).

Topic-level signals only, never raw feedback text. Two kinds:

  explicit  what the user said: more / less / not_interested / enjoyed / too_hard / too_easy
  inferred  what we noticed: items left untouched ('ignored'), counted per topic

Schedules, timing and reasons are never stored here (or anywhere).

Rules:
  * explicit beats inferred: saying "more of X" clears X from 'ignored';
  * ignoring is NOT disliking: it may be timing, difficulty or size. Planners get a hint
    to try a different format/size/time, never an instruction to drop the topic;
  * newer explicit signals replace older opposite ones (more <-> less).
"""

from __future__ import annotations

import datetime as dt
import re

from .core import Repo, load_json, write_json

EXPLICIT_KINDS = ["more", "less", "not_interested", "enjoyed", "too_hard", "too_easy"]
OPPOSITES = {"more": ["less", "not_interested"], "less": ["more"], "not_interested": ["more", "enjoyed"],
             "enjoyed": ["not_interested"], "too_hard": ["too_easy"], "too_easy": ["too_hard"]}
IGNORED_HINT_AT = 2


def norm_topic(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())[:80]


def empty() -> dict:
    return {"_doc": "Sanitized, topic-level preferences learned from feedback. No raw feedback text. "
                    "Explicit signals beat inferred ones; 'ignored' never means disliked.",
            "explicit": {k: {} for k in EXPLICIT_KINDS},
            "inferred": {"ignored": {}}}


def load(repo: Repo) -> dict:
    p = repo.state_path("preference_profile")
    doc = load_json(p) if p.exists() else empty()
    for k in EXPLICIT_KINDS:
        doc.setdefault("explicit", {}).setdefault(k, {})
    doc.pop("timing", None)  # schedules and timing are never stored
    doc.setdefault("inferred", {}).setdefault("ignored", {})
    return doc


def save(repo: Repo, doc: dict) -> None:
    for k in EXPLICIT_KINDS:
        doc["explicit"][k] = dict(sorted(doc["explicit"][k].items()))
    doc["inferred"]["ignored"] = dict(sorted(doc["inferred"]["ignored"].items()))
    write_json(repo.state_path("preference_profile"), doc)


def add_explicit(doc: dict, kind: str, topic: str, day: dt.date) -> None:
    t = norm_topic(topic)
    if not t or kind not in EXPLICIT_KINDS:
        return
    for opp in OPPOSITES.get(kind, []):
        doc["explicit"][opp].pop(t, None)
    doc["explicit"][kind][t] = day.isoformat()
    if kind in ("more", "enjoyed"):
        doc["inferred"]["ignored"].pop(t, None)


def item_topic(item: dict) -> str:
    return norm_topic(item.get("topic") or item.get("category") or item.get("kind") or item.get("title", ""))


def update_from_feedback(doc: dict, fb: dict, items: dict, day: dt.date) -> None:
    g = fb.get("general", {})
    for t in g.get("more_of", []):
        add_explicit(doc, "more", t, day)
    for t in g.get("less_of", []):
        add_explicit(doc, "less", t, day)
    for e in fb.get("entries", []):
        it = items.get(e["item_id"], {})
        topic = item_topic(it)
        if e.get("interest") in ("more", "less", "not_interested"):
            add_explicit(doc, e["interest"], topic, day)
        if e.get("enjoyed"):
            add_explicit(doc, "enjoyed", topic, day)
        if e.get("difficulty_feedback") in ("too_hard", "too_easy"):
            add_explicit(doc, e["difficulty_feedback"], topic, day)
        if e["status"] in ("completed", "partially_completed", "in_progress"):
            doc["inferred"]["ignored"].pop(topic, None)  # engaged, so not ignored


def recompute_ignored(doc: dict, ignored_counts: dict[str, int]) -> None:
    """Replace inferred 'ignored' counts, skipping topics with explicit positive signals."""
    positive = set(doc["explicit"]["more"]) | set(doc["explicit"]["enjoyed"])
    doc["inferred"]["ignored"] = {t: n for t, n in ignored_counts.items() if t not in positive}


def planning_view(doc: dict, dropped_titles: list[str] | None = None) -> dict:
    """What planners should see: priorities, things to avoid, gentle hints. No numbers to optimise."""
    ex = doc["explicit"]
    return {
        "want_more": sorted(ex["more"]),
        "enjoyed": sorted(ex["enjoyed"]),
        "avoid": sorted(set(ex["less"]) | set(ex["not_interested"]) | {norm_topic(t) for t in dropped_titles or []}),
        "make_easier": sorted(ex["too_hard"]),
        "make_harder": sorted(ex["too_easy"]),
        "ignored_hint": sorted(t for t, n in doc["inferred"]["ignored"].items() if n >= IGNORED_HINT_AT),
        "_how_to_use": ("Explicit signals win. 'avoid' = do not recommend. 'ignored_hint' topics were left untouched "
                        "several times: that is NOT dislike; try a smaller, different-format or better-timed version, "
                        "or rest the topic for a while."),
    }
