import json
import datetime as dt

import pytest

from conftest import D, activity, monthly, project, weekly
from dsys import feedback as fb
from dsys import ideas
from dsys.core import load_json
from dsys.validate import validate_repo


def reg_with(*titles, **kw):
    r = {"ideas": []}
    for t in titles:
        ideas.add(r, t, D, **kw)
    return r


def test_add_and_unique_ids():
    r = reg_with("Learn photography", "Learn photography")
    assert [i["id"] for i in r["ideas"]] == ["idea-learn-photography", "idea-learn-photography-2"]
    assert r["ideas"][0]["status"] == "interested"


def test_all_statuses_supported():
    r = reg_with("x")
    for s in ideas.IDEA_STATUSES:
        ideas.set_status(r, "idea-x", s, D)
        assert r["ideas"][0]["status"] == s
    with pytest.raises(ideas.IdeaError):
        ideas.set_status(r, "idea-x", "overdue", D)


def test_user_idea_weekly_or_monthly():
    r = reg_with("Try pottery", "Build a small game", "Explore philosophy")
    ideas.schedule(r, "idea-try-pottery", "2026-W49", D)
    ideas.schedule(r, "idea-build-a-small-game", "2026-12", D)
    a, b, c = r["ideas"]
    assert (a["scope"], a["status"], a["scheduled_for"]) == ("weekly", "planned", "2026-W49")
    assert (b["scope"], b["scheduled_for"]) == ("monthly", "2026-12")
    assert c["scope"] == "undecided" and "scheduled_for" not in c


def test_reschedule_limit():
    r = reg_with("x")
    ideas.schedule(r, "idea-x", "2026-W49", D)
    ideas.schedule(r, "idea-x", "2026-W50", D, limit=2)
    ideas.schedule(r, "idea-x", "2026-W51", D, limit=2)
    with pytest.raises(ideas.RescheduleLimit):
        ideas.schedule(r, "idea-x", "2026-W52", D, limit=2)
    ideas.schedule(r, "idea-x", "2026-W52", D, limit=2, force=True)
    assert r["ideas"][0]["reschedule_count"] == 3


def test_same_period_is_not_a_reschedule():
    r = reg_with("x")
    ideas.schedule(r, "idea-x", "2026-W49", D)
    ideas.schedule(r, "idea-x", "2026-W49", D)
    assert r["ideas"][0]["reschedule_count"] == 0


def test_defer_drop_resize_replace_remove():
    r = reg_with("a", "b")
    ideas.schedule(r, "idea-a", "2026-W49", D)
    ideas.defer(r, "idea-a", D, until="2027-01-15")
    a = ideas.get(r, "idea-a")
    assert a["status"] == "deferred" and "scheduled_for" not in a
    due = ideas.due_for(r, "2027-01")
    assert [i["id"] for i in due["resurfacing"]] == ["idea-a"]

    ideas.schedule(r, "idea-b", "2026-W49", D)
    ideas.resize(r, "idea-b", "monthly", D)
    b = ideas.get(r, "idea-b")
    assert b["scope"] == "monthly" and "scheduled_for" not in b and b["status"] == "interested"

    new = ideas.replace(r, "idea-b", "c", D)
    assert ideas.get(r, "idea-b")["status"] == "dropped"
    assert ideas.get(r, "idea-b")["replaced_by"] == new["id"]

    ideas.drop(r, "idea-a", D, not_interested=True)
    assert ideas.get(r, "idea-a")["status"] == "not_interested"
    with pytest.raises(ideas.IdeaError):
        ideas.schedule(r, "idea-a", "2026-W50", D)

    ideas.remove(r, new["id"])
    assert "replaced_by" not in ideas.get(r, "idea-b")


def test_due_for_includes_scheduled_and_pool():
    r = reg_with("w", "m", "e")
    ideas.schedule(r, "idea-w", "2026-W49", D)
    ideas.resize(r, "idea-m", "monthly", D)
    due = ideas.due_for(r, "2026-W49")
    assert [i["id"] for i in due["scheduled"]] == ["idea-w"]
    assert [i["id"] for i in due["open"]] == ["idea-e"]


# --- feedback ------------------------------------------------------------------
def setup_week(repo):
    r = ideas.load(repo)
    ideas.add(r, "Learn photography", D)
    ideas.schedule(r, "idea-learn-photography", "2026-W49", D)
    ideas.save(repo, r)
    weekly(repo, "2026-W49", items=[
        activity("w-done"), activity("w-skip"), activity("w-more"), activity("w-drop"),
        activity("w-photo", origin="user_idea", idea_id="idea-learn-photography", category="user_idea"),
    ])


def test_feedback_apply_decisions(repo):
    setup_week(repo)
    entries = [
        {"item_id": "w-done", "status": "completed", "enjoyed": "loved it"},
        {"item_id": "w-skip", "status": "skipped", "skip_reason": "no_time"},
        {"item_id": "w-more", "status": "partially_completed", "decision": "reschedule"},
        {"item_id": "w-drop", "status": "dropped"},
        {"item_id": "w-photo", "status": "completed", "decision": "keep_in_progress", "decision_target": "2027-01"},
    ]
    fb.record(repo, "2026-W49", entries, D, general={"more_of": ["puzzles"]})
    log = fb.apply(repo, "2026-W49", D)
    pkg = load_json(repo.weekly_path("2026-W49"))
    st = {i["id"]: i["status"] for i in pkg["items"] if "-fill-" not in i["id"]}
    assert st == {"w-done": "completed", "w-skip": "skipped", "w-more": "partially_completed",
                  "w-drop": "dropped", "w-photo": "completed"}
    r = ideas.load(repo)
    ids = {i["id"]: i for i in r["ideas"]}
    # skipped item is NOT carried forward
    assert "idea-from-w-skip" not in ids
    # rescheduled item becomes an idea in next week
    assert ids["idea-from-w-more"]["scheduled_for"] == "2026-W50"
    # photography continues as monthly project
    p = ids["idea-learn-photography"]
    assert (p["status"], p["scheduled_for"], p["scope"]) == ("in_progress", "2027-01", "monthly")
    # learned prefs are qualitative notes
    prof = load_json(repo.state_path("preference_profile"))
    assert "puzzles" in prof["explicit"]["more"]
    assert "culture" in prof["explicit"]["enjoyed"]  # w-done was enjoyed; topic falls back to category
    assert "timing" not in prof  # schedules and reasons are never stored
    assert "loved it" not in json.dumps(prof)  # no raw feedback text in the profile
    assert validate_repo(repo).ok, validate_repo(repo).errors
    # idempotent
    assert "already applied" in fb.apply(repo, "2026-W49", D)[0]


def test_feedback_reschedule_limit_flags_reconsideration(repo):
    setup_week(repo)
    r = ideas.load(repo)
    i = ideas.get(r, "idea-learn-photography")
    i["reschedule_count"] = 2
    ideas.save(repo, r)
    fb.record(repo, "2026-W49", [{"item_id": "w-photo", "status": "not_started", "decision": "reschedule"}], D)
    log = fb.apply(repo, "2026-W49", D)
    assert any("NOT rescheduled" in l for l in log)
    p = ideas.get(ideas.load(repo), "idea-learn-photography")
    assert "scheduled_for" not in p and "reconsideration" in p["notes"]


def test_feedback_without_decision_unschedules_user_idea(repo):
    setup_week(repo)
    fb.record(repo, "2026-W49", [{"item_id": "w-photo", "status": "skipped"}], D)
    fb.apply(repo, "2026-W49", D)
    p = ideas.get(ideas.load(repo), "idea-learn-photography")
    assert p["status"] == "interested" and "scheduled_for" not in p


def test_feedback_record_rejects_unknown_item(repo):
    setup_week(repo)
    with pytest.raises(ValueError):
        fb.record(repo, "2026-W49", [{"item_id": "nope", "status": "skipped"}], D)


def test_monthly_feedback_split(repo):
    monthly(repo, "2026-12", items=[project("m-big")])
    fb.record(repo, "2026-12", [{"item_id": "m-big", "status": "partially_completed", "decision": "split",
                                 "decision_note": "first milestone only"}], D)
    fb.apply(repo, "2026-12", D)
    idea = ideas.get(ideas.load(repo), "idea-from-m-big")
    assert idea["scheduled_for"] == "2027-01" and "first milestone" in idea["notes"]
    assert validate_repo(repo).ok
