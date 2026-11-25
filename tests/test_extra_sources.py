"""Podcasts, research updates, Hugging Face trending, long-form video rotation, and the CLI that reads them."""

import datetime as dt
import importlib.util
import json

from conftest import ROOT, D
from dsys import extra_sources as xs
from dsys import history
from dsys.core import load_json, write_json

POD = """<?xml version="1.0"?><rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<item><title>Ep 1: Scaling</title><link>https://show.example/ep1</link><pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate>
<enclosure url="https://cdn.example/ep1.mp3" type="audio/mpeg"/><itunes:duration>01:02:03</itunes:duration>
<description>&lt;p&gt;About scaling.&lt;/p&gt;</description></item>
<item><title></title><link>https://show.example/x</link></item>
</channel></rss>"""


def _fc():
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    return fc


def test_parse_podcast_feed_and_itunes():
    eps = xs.parse_podcast_feed(POD, "Show")
    assert len(eps) == 1 and eps[0]["audio_url"] == "https://cdn.example/ep1.mp3"
    assert eps[0]["summary"] == "About scaling." and eps[0]["duration"] == "01:02:03"
    got = xs.parse_itunes_episodes({"results": [
        {"wrapperType": "podcastEpisode", "trackName": "On  games", "trackViewUrl": "https://podcasts.apple.com/x",
         "episodeUrl": "https://cdn/a.mp3", "releaseDate": "2026-11-20T00:00:00Z", "collectionName": "S", "trackTimeMillis": 3600000},
        {"wrapperType": "track", "trackName": "not an episode"}]})
    assert got == [{"show": "S", "title": "On games", "url": "https://podcasts.apple.com/x", "audio_url": "https://cdn/a.mp3",
                    "published": "2026-11-20T00:00:00Z", "summary": "", "duration": "60 min"}]


def test_parse_hn_and_hf():
    hn = xs.parse_hn({"hits": [{"title": "A", "url": "https://a", "points": 200, "objectID": "1", "num_comments": 5},
                               {"title": "B", "points": 3, "objectID": "2"}]}, 50)
    assert [h["title"] for h in hn] == ["A"] and hn[0]["discussion_url"].endswith("id=1")
    hf = xs.parse_hf([{"id": "org/data", "likes": 5}, {"nope": 1}], "dataset")
    assert hf == [{"kind": "dataset", "id": "org/data", "url": "https://huggingface.co/datasets/org/data", "likes": 5}]


def test_fetch_podcasts(repo, monkeypatch):
    fc = _fc()
    s = load_json(repo.p("config", "sources.json"))
    s["podcasts"].update(shows=[{"name": "Show", "tier": "growth"}, {"name": "Missing"}],
                         episode_searches=[{"term": "games", "tier": "growth"}], pause_seconds=0)
    write_json(repo.p("config", "sources.json"), s)
    monkeypatch.setattr(fc.xs, "itunes_show", lambda n: {"show": n, "feed_url": "https://f", "apple_url": "https://a"} if n == "Show" else None)
    monkeypatch.setattr(fc, "net_get", lambda u: POD.replace("23 Nov 2026", dt.date.today().strftime("%d %b %Y")))
    monkeypatch.setattr(fc.xs, "search_episodes", lambda t, n: [])
    fc.fetch_podcasts(repo, D)
    doc = load_json(repo.p("candidates", "podcasts", f"{D}.json"))
    assert [e["title"] for e in doc["candidates"]] == ["Ep 1: Scaling"] and doc["candidates"][0]["tier"] == "growth"
    assert doc["errors"] == ["Missing: not found on iTunes"]
    assert history.latest_candidates(repo, "podcasts", D + dt.timedelta(days=1))["candidates"]


def test_query_rotation_covers_all():
    fc = _fc()
    qs = [f"q{i}" for i in range(10)]
    seen = set()
    for k in range(5):
        seen |= set(fc.rotate(qs, 4, D + dt.timedelta(days=k)))
    assert seen == set(qs) and fc.rotate(qs, None, D) == qs


def test_cli_interest_search(repo):
    write_json(repo.p("candidates", "arxiv", f"{D}.json"), {"kind": "arxiv", "date": str(D), "candidates": [],
               "interest_search": {"diffusion": [{"arxiv_id": "2301.1", "title": "t"}], "world models": []}})
    res = history.interest_search(repo, D, "diff")
    assert list(res["interest_search"]) == ["diffusion"]


def test_status_and_polls(repo):
    from dsys import status
    st = status.status(repo, D)
    assert "world" in st["missing"] and st["ok"] is False
    status.open_poll(repo, "weekly", "2026-W49", "123.45", [{"key": "1", "topic": "test-time compute"}])
    assert [p["period"] for p in status.list_polls(repo, True)] == ["2026-W49"]
    status.close_poll(repo, "weekly", "2026-W49", ["test-time compute"])
    assert status.list_polls(repo, True) == [] and status.choices_for(repo, "weekly", "2026-W49") == ["test-time compute"]
    ctx = history.context(repo, "weekly", D, "2026-W49")
    assert ctx["poll_choices"] == ["test-time compute"] and "recent_subjects" in ctx


def test_library_page(repo):
    from dsys import site
    html = site.library_html([{"week": "2026-W49", "items": [
        {"id": "a", "title": "Rome", "section": "knowledge", "subject": "history"},
        {"id": "b", "title": "Spring", "section": "questions", "subject": "physics", "category": "question"}]}],
        [{"month": "2026-12", "items": [], "challenges": [{"id": "c", "subject": "maths", "title": "Sum"}]}])
    assert html.index("Mathematics") < html.index("Physics") < html.index("History")
    assert "weekly/2026-W49/knowledge.html#history" in html and "challenge, 2026-12" in html


def test_ensure_dispatches_and_waits(repo):
    from dsys.ensure import ensure
    calls = []

    def run(cmd):
        calls.append(cmd[:2])
        if cmd[0] == "git":  # the workflow's commit lands on the second pull
            if sum(c[0] == "git" for c in calls) == 2:
                write_json(repo.p("candidates", "arxiv", f"{D}.json"), {"candidates": []})

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()
    assert ensure(repo, D, ["arxiv"], wait=300, run=run, sleep=lambda s: None) == 0
    assert calls[0] == ["gh", "api"] and sum(c[0] == "git" for c in calls) == 2
    assert ensure(repo, D, ["arxiv"], run=run, sleep=lambda s: None) == 0 and len(calls) == 3  # already there
