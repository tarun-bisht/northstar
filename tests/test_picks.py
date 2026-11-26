"""Start here: at most one paper, story and exploration pick a day, each with one line on why."""
import pytest

from conftest import daily, example, paper
from dsys import picks, render
from dsys.core import load_json

DATE = "2026-11-25"


def _day(repo):
    daily(repo, "arxiv", DATE, [paper("2611.00001"), paper("2611.00002", id="arxiv-2611.00002")])
    w = example("w", "world")
    daily(repo, "world", DATE, w["items"], briefs=w.get("briefs", []))
    d = example("d", "discovery")
    daily(repo, "discovery", DATE, d["items"])
    return w["items"][0]["id"], d["items"][0]["id"]


def _streams(repo):
    return {s: load_json(repo.daily_path(s, DATE)) for s in ("arxiv", "world", "discovery")}


def test_set_picks_marks_one_per_stream_and_replaces_earlier_ones(repo):
    import datetime as dt
    story, find = _day(repo)
    day = dt.date.fromisoformat(DATE)
    picks.set_picks(repo, day, {"arxiv-2611.00001": "The clearest result today.", story: "Why rates moved."})
    picks.set_picks(repo, day, {"arxiv-2611.00002": "Better one.", find: "A calm hour of good science."})
    got = {it["id"]: it["start_here"] for _, it in picks.items(_streams(repo))}
    assert got == {"arxiv-2611.00002": "Better one.", find: "A calm hour of good science."}


def test_set_picks_rejects_unknown_ids_two_in_a_stream_and_long_reasons(repo):
    import datetime as dt
    _day(repo)
    day = dt.date.fromisoformat(DATE)
    with pytest.raises(SystemExit):
        picks.set_picks(repo, day, {"arxiv-9999.00000": "nope"})
    with pytest.raises(SystemExit):
        picks.set_picks(repo, day, {"arxiv-2611.00001": "one", "arxiv-2611.00002": "two"})
    with pytest.raises(SystemExit):
        picks.set_picks(repo, day, {"arxiv-2611.00001": "x" * 200})
    assert picks.items(_streams(repo)) == []  # nothing written on a refused call


def test_start_here_renders_on_pages_and_feed_part(repo):
    import datetime as dt
    story, _ = _day(repo)
    picks.set_picks(repo, dt.date.fromisoformat(DATE), {"arxiv-2611.00001": "Read this first.", story: "The big one."})
    st = _streams(repo)
    html = render.start_here(st, base="")
    assert "Start here" in html and "Read this first." in html and "alphaxiv.org/abs/2611.00001" in html
    assert 'href="research.html"' in html and 'href="news.html"' in html
    only = render.start_here(st, only="news")
    assert "The big one." in only and "Read this first." not in only
    assert render.start_here({}, base="") == ""


def test_validation_rejects_two_picks_in_one_stream(repo):
    from dsys.validate import validate_repo
    _day(repo)
    doc = load_json(repo.daily_path("arxiv", DATE))
    for it in doc["items"]:
        it["start_here"] = "Both picked."
    daily(repo, "arxiv", DATE, doc["items"])
    rep = validate_repo(repo)
    assert any("at most one start_here" in e for e in map(str, rep.errors))
