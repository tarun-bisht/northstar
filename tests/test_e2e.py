"""End-to-end run of the whole workflow on SYNTHETIC data, through the CLI.

This exercises the local pipeline (candidates -> daily streams -> ideas -> weekly/monthly ->
feedback -> synthesis -> history -> validation -> RSS -> site). It does not call
arXiv, YouTube, web search or Claude; those integrations are only tested with mocks.
"""

import json
import xml.etree.ElementTree as ET

from conftest import activity, paper, project, shorts_day, video
from dsys.cli import main
from dsys.core import load_json, write_json
from dsys.site import build_site


def run(*args):
    assert main(list(args)) == 0, args


def test_full_workflow(repo, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DSYS_ROOT", str(repo.root))
    day = "2026-11-24"

    # 1. arXiv: candidates fetched by Actions -> unseen list -> select one, mark the rest seen
    write_json(repo.p("candidates", "arxiv", f"{day}.json"), {"date": day, "candidates": [
        {"arxiv_id": "2611.01234", "title": "Relevant", "categories": ["cs.LG"]},
        {"arxiv_id": "2611.09999", "title": "Not relevant", "categories": ["cs.LG"]}]})
    capsys.readouterr()
    run("candidates", "arxiv", "--date", day, "--brief")
    assert json.loads(capsys.readouterr().out)["unseen"] == 2
    items = tmp_path / "a.json"
    items.write_text(json.dumps({"items": [paper(selection_reason="Closely related to your work.")],
                                 "candidates_considered": 2, "notes": "2 candidates, 1 selected"}))
    run("daily", "merge", "arxiv", "--date", day, "--items", str(items))
    run("papers", "mark-seen", "2611.09999", "--date", day)
    run("history", "rebuild")
    capsys.readouterr()
    run("candidates", "arxiv", "--date", day)
    assert json.loads(capsys.readouterr().out)["unseen"] == 0  # nothing shown twice

    # 2. research updates, world, discovery (with a cross-domain pick), shorts
    ru = {"id": "ru-2026-11-24-tool", "title": "A tool", "kind": "tool", "what_happened": "a", "why_it_matters": "b",
          "what_to_watch": "c", "source": {"name": "Lab", "url": "https://example.org/lab"}, "published": day}
    world = {"id": "world-2026-11-24-x", "title": "An event", "regions": ["India"], "topic": "economics",
             "what_happened": "a", "why_it_matters": "b", "what_to_watch": "c", "confirmed_facts": ["f"],
             "sources": [{"name": "Wire", "url": "https://example.org/w"}], "published": day}
    disc = {"id": "disc-2026-11-24-x", "title": "Cinema and empathy", "type": "film", "category": "cinema",
            "topic": "film editing", "description": "d", "why_recommended": "w", "tier": "exploration", "action": "watch",
            "time_required": "2h", "dimensions": ["culture", "people"],
            "cross_domain": {"fields": ["cinema", "psychology"], "connection": "Editing choices shape empathy."}}
    pod = {**disc, "id": "disc-2026-11-24-pod", "title": "An episode", "type": "podcast", "action": "listen",
           "tier": "established"}
    vid = {**disc, "id": "disc-2026-11-24-vid", "title": "A lecture", "type": "lecture", "action": "watch",
           "tier": "growth"}
    pod.pop("cross_domain"); vid.pop("cross_domain")
    for stream, its in (("research_updates", [ru]), ("world", [world]), ("discovery", [disc, pod, vid]),
                        ("youtube_shorts", shorts_day(video()))):
        f = tmp_path / f"{stream}.json"
        f.write_text(json.dumps({"items": its}))
        run("daily", "merge", stream, "--date", day, "--items", str(f))

    # 3. a user-initiated idea, scheduled for next week; a seed stays unscheduled
    run("ideas", "add", "Learn photography", "--scope", "weekly", "--first-step", "One photo walk",
        "--week", "2026-W49", "--date", day)
    run("ideas", "add", "Seed: tides", "--origin", "seed", "--status", "curiosity", "--date", day)
    capsys.readouterr()
    run("context", "weekly", "--period", "2026-W49", "--date", "2026-11-28")
    ctx = json.loads(capsys.readouterr().out)
    assert [i["id"] for i in ctx["ideas_scheduled_for_this_period"]] == ["idea-learn-photography"]
    assert "idea-seed-tides" in [i["id"] for i in ctx["ideas_open_pool"]]

    # 4. weekly package (as the planner would write it)
    from dsys.core import week_bounds
    s, e = week_bounds("2026-W49")
    write_json(repo.weekly_path("2026-W49"), {
        "schema": "weekly", "week": "2026-W49", "start_date": s.isoformat(), "end_date": e.isoformat(),
        "generated_at": "2026-11-28T01:16:00Z", "load": ctx["schedule"]["load"], "intro": "Optional things.",
        "items": [activity("w-2026-w49-photo", title="Photo walk", category="user_idea", origin="user_idea",
                           idea_id="idea-learn-photography", mode="create", topic="photography",
                           dimensions=["culture", "curiosity"]),
                  activity("w-2026-w49-listen", title="Listen first", category="people", mode="practise",
                           topic="active listening", then="Note one thing you learned.", dimensions=["people"]),
                  activity("w-2026-w49-proof", title="A proof", category="research_fundamentals", mode="learn",
                           topic="probability puzzles", hints=["h1", "h2"], dimensions=["research"],
                           steps=["Try small n by hand", "Prove the bound"],
                           resources=[{"title": "A probability text", "type": "book", "chapters": "Ch. 2"}])]})
    run("validate")

    # 5. feedback: keep going, try again later, let go
    fb = tmp_path / "fb.json"
    fb.write_text(json.dumps({"entries": [
        {"item_id": "w-2026-w49-photo", "status": "completed", "enjoyed": "seeing light", "decision": "keep_in_progress",
         "decision_target": "2026-12", "interest": "more"},
        {"item_id": "w-2026-w49-listen", "status": "not_started", "skip_reason": "no_time", "decision": "reschedule"},
        {"item_id": "w-2026-w49-proof", "status": "skipped", "interest": "less"}],
        "general": {"more_of": ["maps"]}}))
    run("feedback", "record", "--period", "2026-W49", "--json", str(fb), "--date", "2026-12-05")
    run("feedback", "apply", "--period", "2026-W49", "--date", "2026-12-05")
    photo = next(i for i in load_json(repo.state_path("ideas"))["ideas"] if i["id"] == "idea-learn-photography")
    assert photo["status"] == "in_progress" and photo["scheduled_for"] == "2026-12"
    prof = load_json(repo.state_path("preference_profile"))
    assert "photography" in prof["explicit"]["more"] and "probability puzzles" in prof["explicit"]["less"]
    assert "seeing light" not in json.dumps(prof)

    # 6. monthly package includes the continued idea; rescheduling and dropping
    capsys.readouterr()
    run("context", "monthly", "--period", "2026-12", "--date", "2026-12-01")
    mctx = json.loads(capsys.readouterr().out)
    assert "idea-learn-photography" in [i["id"] for i in mctx["ideas_scheduled_for_this_period"]]
    assert "probability puzzles" in mctx["preferences"]["avoid"]
    write_json(repo.monthly_path("2026-12"), {
        "schema": "monthly", "month": "2026-12", "generated_at": "2026-12-01T00:45:00Z", "load": "normal",
        "intro": "Optional depth.", "items": [project("m-2026-12-photo", title="A small photo series", kind="user_idea",
                                                      origin="user_idea", idea_id="idea-learn-photography",
                                                      modes=["learn", "create"], dimensions=["culture"])]})
    run("ideas", "drop", "idea-seed-tides", "--note", "not now", "--date", "2026-12-01")

    # 7. synthesis evidence is qualitative
    capsys.readouterr()
    run("synthesis", "--quarter", "2026-Q4")
    ev = json.loads(capsys.readouterr().out)
    assert "Photo walk" in [e["title"] for e in ev["engaged_with"]] and ev["tiers_engaged"]
    assert "%" not in json.dumps(ev)

    # 8. history, validation, RSS, site
    run("history", "rebuild")
    run("validate", "--all")
    run("rss")
    for f in repo.p("feeds").glob("*.xml"):
        ET.parse(f)
    out = build_site(repo, tmp_path / "site")
    for page in ("index.html", f"daily/{day}.html", "weekly/2026-W49.html", "monthly/2026-12.html"):
        assert (out / page).exists(), page
    assert not (out / "ideas.html").exists()
    assert "Connects cinema and psychology" in (out / f"daily/{day}.html").read_text()
    assert "Then." in (out / "weekly/2026-W49.html").read_text()
