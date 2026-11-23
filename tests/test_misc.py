import datetime as dt
import json

from conftest import D, activity, daily, paper, video, weekly
from dsys import arxiv as ax
from dsys import history, ideas
from dsys import youtube as yt
from dsys.cli import main
from dsys.core import load_json, next_month, next_week, week_bounds, write_json
from dsys.schedule import load_for_range


def test_period_math():
    assert next_week("2026-W52") == "2026-W53"
    assert next_week("2026-W53") == "2027-W01"
    assert next_month("2026-12") == "2027-01"
    assert next_month("2027-01", -1) == "2026-12"
    assert week_bounds("2026-W48") == (dt.date(2026, 11, 23), dt.date(2026, 11, 29))


def test_schedule_load():
    cfg = {"default_load": "normal", "periods": [{"label": "deadline", "start": "2026-12-01", "end": "2026-12-10", "load": "light"}]}
    assert load_for_range(cfg, dt.date(2026, 11, 30), dt.date(2026, 12, 6))["load"] == "light"
    assert load_for_range(cfg, dt.date(2026, 12, 14), dt.date(2026, 12, 20))["load"] == "normal"
    cfg["periods"] = [{"label": "hol", "start": "2026-12-24", "end": "2027-01-01", "load": "free"}]
    assert load_for_range(cfg, dt.date(2026, 12, 21), dt.date(2026, 12, 27))["load"] == "free"
    assert load_for_range(cfg, dt.date(2026, 12, 1), dt.date(2026, 12, 31))["load"] == "normal"


def test_youtube_helpers():
    assert yt.is_valid_id("dQw4w9WgXcQ")
    assert not yt.is_valid_id("dQw4w9WgXc")
    assert yt.extract_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt.extract_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3") == "dQw4w9WgXcQ"
    assert yt.extract_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt.extract_id("https://example.com/watch?v=dQw4w9WgXcQ") is None
    assert yt.parse_iso8601_duration("PT1M5S") == 65
    assert yt.parse_iso8601_duration("PT45S") == 45


def test_arxiv_parse_feed():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
    <entry><id>http://arxiv.org/abs/2611.01234v2</id><published>2026-11-20T10:00:00Z</published>
    <updated>2026-11-21T10:00:00Z</updated><title>A  Title
    here</title><summary> An abstract
     with  spaces. </summary><author><name>A B</name></author><author><name>C D</name></author>
    <arxiv:primary_category term="cs.LG"/><category term="cs.LG"/><category term="cs.CR"/></entry></feed>"""
    [p] = ax.parse_feed(xml)
    assert p["arxiv_id"] == "2611.01234" and p["version"] == "v2"
    assert p["title"] == "A Title here" and p["abstract"] == "An abstract with spaces."
    assert p["authors"] == ["A B", "C D"] and p["categories"] == ["cs.LG", "cs.CR"]
    assert p["url"] == "https://arxiv.org/abs/2611.01234"


def test_history_and_dedup_context(repo):
    daily(repo, "arxiv", "2026-11-23", [paper()])
    daily(repo, "youtube_shorts", "2026-11-23", [video()])
    write_json(repo.p("candidates", "arxiv", "2026-11-24.json"), {"candidates": [
        {"arxiv_id": "2611.01234", "title": "old"}, {"arxiv_id": "2611.05555", "title": "new"},
        {"arxiv_id": "2611.06666", "title": "seen"}]})
    history.rebuild(repo)
    history.mark_papers_seen(repo, ["2611.06666"], D)
    c = history.unseen_arxiv_candidates(repo, D)
    assert [x["arxiv_id"] for x in c["candidates"]] == ["2611.05555"]
    ctx = history.context(repo, "youtube_shorts", D)
    assert "Chan" in ctx["creators_used_last_7_days"]
    # seen survives rebuild
    history.rebuild(repo)
    assert "2611.06666" in load_json(repo.state_path("paper_history"))["seen"]


def test_weekly_context_contains_scheduled_user_ideas(repo):
    r = ideas.load(repo)
    ideas.add(r, "Try pottery", D)
    ideas.schedule(r, "idea-try-pottery", "2026-W49", D)
    ideas.save(repo, r)
    ctx = history.context(repo, "weekly", D, "2026-W49")
    assert [i["id"] for i in ctx["ideas_scheduled_for_this_period"]] == ["idea-try-pottery"]
    assert ctx["schedule"]["load"] in ("light", "normal", "free")


def test_cli_end_to_end(repo, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("DSYS_ROOT", str(repo.root))
    assert main(["ideas", "add", "I want to build a small game", "--scope", "monthly", "--month", "2026-12",
                 "--date", "2026-11-24"]) == 0
    assert main(["ideas", "add", "Try pottery", "--date", "2026-11-24"]) == 0
    assert main(["ideas", "schedule", "idea-try-pottery", "--week", "2026-W49", "--date", "2026-11-24"]) == 0
    assert main(["ideas", "defer", "idea-try-pottery", "--until", "2027-02-01", "--date", "2026-11-24"]) == 0
    items = tmp_path / "items.json"
    items.write_text(json.dumps({"items": [paper()], "notes": "1 selected", "candidates_considered": 10}))
    assert main(["daily", "merge", "arxiv", "--date", "2026-11-24", "--items", str(items)]) == 0
    assert main(["daily", "merge", "arxiv", "--date", "2026-11-24", "--items", str(items)]) == 0  # idempotent
    doc = load_json(repo.daily_path("arxiv", "2026-11-24"))
    assert len(doc["items"]) == 1 and doc["candidates_considered"] == 10
    weekly(repo, "2026-W49", items=[activity("w-x")])
    assert main(["feedback", "record", "--period", "2026-W49", "--item", "w-x", "--status", "completed",
                 "--enjoyed", "fun", "--more", "math,history", "--date", "2026-12-05"]) == 0
    assert main(["feedback", "apply", "--period", "2026-W49", "--date", "2026-12-05"]) == 0
    assert main(["history", "rebuild"]) == 0
    assert main(["validate"]) == 0
    assert main(["inbox", "clear", "ideas"]) == 0
    capsys.readouterr()
    assert main(["inbox", "show", "ideas"]) == 0
    assert "(empty)" in capsys.readouterr().out


def test_parse_hf_daily():
    data = [{"paper": {"id": "2611.01234", "title": "A  paper", "summary": "An  abstract.", "upvotes": 42,
                       "publishedAt": "2026-11-20T10:00:00.000Z", "authors": [{"name": "A B"}]}},
            {"paper": {"id": "not-arxiv", "title": "skip"}}]
    [p] = ax.parse_hf_daily(data)
    assert p == {"arxiv_id": "2611.01234", "title": "A paper", "authors": ["A B"], "abstract": "An abstract.",
                 "submitted": "2026-11-20", "hf_upvotes": 42, "url": "https://arxiv.org/abs/2611.01234"}


def test_fetch_arxiv_merges_hf_signal(repo, monkeypatch):
    import importlib.util
    from conftest import ROOT
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    s = load_json(repo.p("config", "sources.json"))
    s["arxiv"]["categories"] = [{"id": "cs.LG"}]
    write_json(repo.p("config", "sources.json"), s)
    monkeypatch.setattr(fc.ax, "fetch_recent", lambda cat, n: [
        {"arxiv_id": "2611.00001", "title": "On arXiv", "submitted": "2026-11-23", "categories": ["cs.LG"]}])
    monkeypatch.setattr(fc.ax, "fetch_hf_daily", lambda d, api: [
        {"arxiv_id": "2611.00001", "hf_upvotes": 30, "title": "On arXiv", "submitted": "2026-11-23"},
        {"arxiv_id": "2611.00002", "hf_upvotes": 80, "title": "Only on HF", "submitted": "2026-11-23",
         "abstract": "x", "authors": [], "url": "https://arxiv.org/abs/2611.00002"}])
    fc.fetch_arxiv(repo, D)
    c = {p["arxiv_id"]: p for p in load_json(repo.p("candidates", "arxiv", f"{D}.json"))["candidates"]}
    assert c["2611.00001"]["hf_upvotes"] == 30 and c["2611.00002"]["source"] == "huggingface_daily"
