import json

from conftest import ROOT, activity, daily, paper, shorts_day, video, weekly
from dsys.core import Repo, load_json, write_json
from dsys.validate import validate_repo


def errs(repo, examples=False):
    return validate_repo(repo, examples=examples).errors


def test_real_repo_is_valid():
    assert validate_repo(Repo(ROOT)).ok
    assert validate_repo(Repo(ROOT), examples=True).ok


def test_all_schemas_compile(repo):
    from jsonschema import Draft202012Validator
    for f in (repo.root / "schemas").glob("*.json"):
        Draft202012Validator.check_schema(load_json(f))


def test_examples_are_marked_and_valid(repo):
    assert errs(repo, examples=True) == []
    f = next((repo.root / "examples/content/world").rglob("*.json"))
    d = load_json(f)
    d.pop("example")
    write_json(f, d)
    assert any("example" in e for e in errs(repo, examples=True))


def test_empty_day_is_valid(repo):
    daily(repo, "arxiv", "2026-11-24", [], notes="nothing relevant")
    assert errs(repo) == []


def test_invalid_json(repo):
    p = repo.daily_path("world", "2026-11-24")
    p.parent.mkdir(parents=True)
    p.write_text("{not json")
    assert any("invalid JSON" in e for e in errs(repo))


def test_missing_required_field(repo):
    p = paper()
    del p["abstract"]
    daily(repo, "arxiv", "2026-11-24", [p])
    assert any("abstract" in e for e in errs(repo))


def test_invalid_date_and_path_mismatch(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(submitted="2026-02-30")])
    assert any("invalid date" in e for e in errs(repo))
    doc = {"schema": "arxiv", "date": "2026-11-25", "generated_at": "2026-11-24T01:00:00Z", "items": []}
    write_json(repo.daily_path("arxiv", "2026-11-23"), doc)
    assert any("path must end with" in e for e in errs(repo))


def test_invalid_url(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(pdf_url="https://nodot/x")])
    assert any("invalid URL" in e for e in errs(repo))


def test_arxiv_url_and_id_consistency(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(url="https://arxiv.org/abs/2611.99999")])
    assert any("canonical" in e for e in errs(repo))


def test_invalid_arxiv_month(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(aid="2613.01234")])
    assert any("invalid arXiv id" in e for e in errs(repo))


def test_duplicate_paper_across_days(repo):
    daily(repo, "arxiv", "2026-11-23", [paper()])
    daily(repo, "arxiv", "2026-11-24", [paper()])
    e = errs(repo)
    assert any("duplicate paper" in x for x in e)


def test_duplicate_ids_within_day(repo):
    daily(repo, "research_updates", "2026-11-24", [_ru("ru-x"), _ru("ru-x")])
    assert any("duplicate research_updates item id" in e for e in errs(repo))


def _ru(i):
    return {"id": i, "title": "t", "kind": "tool", "what_happened": "a", "why_it_matters": "b", "what_to_watch": "c",
            "source": {"name": "s", "url": "https://example.org/x"}, "published": "2026-11-24"}


def test_youtube_validation(repo):
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(video()))
    assert errs(repo) == []
    daily(repo, "youtube_shorts", "2026-11-24", [video("short")])
    assert any("video_id" in e for e in errs(repo))
    daily(repo, "youtube_shorts", "2026-11-24", [video(embed_url="https://www.youtube.com/embed/zzzzzzzzzzz")])
    assert any("embed_url" in e for e in errs(repo))
    daily(repo, "youtube_shorts", "2026-11-24", [video(url="https://www.youtube.com/watch?v=zzzzzzzzzzz")])
    assert any("does not point" in e for e in errs(repo))


def test_unverified_video_rejected_in_content(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video(verification={"method": "example_unverified"})])
    assert any("unverified" in e for e in errs(repo))


def test_duplicate_video_across_days(repo):
    daily(repo, "youtube_shorts", "2026-11-23", [video()])
    daily(repo, "youtube_shorts", "2026-11-24", [video()])
    assert any("duplicate video" in e for e in errs(repo))


def test_invalid_status(repo):
    weekly(repo, items=[activity("w-1", status="overdue")])
    assert any("overdue" in e for e in errs(repo))


def test_broken_idea_reference(repo):
    weekly(repo, items=[activity("w-1", origin="user_idea", idea_id="idea-missing")])
    assert any("not found in ideas registry" in e for e in errs(repo))


def test_weekly_bounds_checked(repo):
    weekly(repo, start_date="2026-12-01")
    assert any("start/end" in e for e in errs(repo))


def test_feedback_references(repo):
    weekly(repo)
    write_json(repo.feedback_path("2026-W49"), {"schema": "feedback", "period": "2026-W49", "date": "2026-12-06",
                                                 "entries": [{"item_id": "nope", "status": "skipped"}]})
    assert any("not in package" in e for e in errs(repo))
    write_json(repo.feedback_path("2026-W50"), {"schema": "feedback", "period": "2026-W50", "date": "2026-12-06",
                                                 "entries": []})
    assert any("no weekly/monthly package" in e for e in errs(repo))


def test_activity_id_reuse_across_weeks(repo):
    weekly(repo, "2026-W49", items=[activity("w-same")])
    weekly(repo, "2026-W50", items=[activity("w-same")])
    assert any("reused" in e for e in errs(repo))


def test_continues_must_reference_existing(repo):
    weekly(repo, "2026-W50", items=[activity("w-2", origin="continued", continues="w-ghost")])
    assert any("continues" in e for e in errs(repo))


def test_dimensions_come_from_config(repo):
    from dsys.core import write_json
    weekly(repo, items=[activity("w-1", dimensions=["gardening"])])
    assert any("unknown dimension 'gardening'" in e for e in errs(repo))
    cfg = load_json(repo.p("config", "interests.json"))
    cfg["dimensions"]["gardening"] = {"name": "Gardening", "description": "Grow things."}
    write_json(repo.p("config", "interests.json"), cfg)
    assert errs(repo) == []


def test_arxiv_reason_is_optional(repo):
    p = paper()
    del p["selection_reason"]
    daily(repo, "arxiv", "2026-11-24", [p])
    assert errs(repo) == []
