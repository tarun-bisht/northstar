"""Overview: at most five best items in Research and Exploration, shown first, not repeated below."""
import datetime as dt
import xml.etree.ElementTree as ET

import pytest

from conftest import daily, example, paper
from dsys import overview
from dsys.core import load_json
from dsys.rss import build_feed

D = "2026-11-25"
NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _papers(repo, n=8, top=6):
    ps = [paper(f"2611.000{i:02d}", id=f"arxiv-2611.000{i:02d}", title=f"Paper {i}",
                priority="top" if i < top else "more") for i in range(n)]
    daily(repo, "arxiv", D, ps)
    return ps


def test_fallback_takes_top_papers_capped_at_five_and_split_removes_them(repo):
    _papers(repo)
    streams = {"arxiv": load_json(repo.daily_path("arxiv", D))}
    ov, rest = overview.split(streams, "research")
    assert [it["title"] for _, it in ov] == [f"Paper {i}" for i in range(5)]
    assert [it["title"] for it in rest["arxiv"]["items"]] == ["Paper 5", "Paper 6", "Paper 7"]


def test_set_overview_marks_orders_and_validates(repo):
    _papers(repo)
    day = dt.date.fromisoformat(D)
    overview.set_overview(repo, day, "research", ["arxiv-2611.00007", "arxiv-2611.00002"])
    streams = {"arxiv": load_json(repo.daily_path("arxiv", D))}
    assert [it["id"] for _, it in overview.chosen(streams, "research")] == ["arxiv-2611.00007", "arxiv-2611.00002"]
    with pytest.raises(SystemExit):
        overview.set_overview(repo, day, "research", ["arxiv-9999.99999"])
    with pytest.raises(SystemExit):
        overview.set_overview(repo, day, "research", [f"arxiv-2611.000{i:02d}" for i in range(6)])
    assert overview.errors("arxiv", [{"overview": True}] * 6) and not overview.errors("arxiv", [{"overview": True}])
    assert overview.errors("world", [{"overview": True}])


def test_exploration_fallback_is_varied_and_feed_has_no_duplicates(repo):
    d = example("d", "discovery")
    daily(repo, "discovery", D, d["items"])
    streams = {"discovery": load_json(repo.daily_path("discovery", D))}
    ov = overview.chosen(streams, "exploration")
    assert 1 <= len(ov) <= 5
    html = ET.fromstring(build_feed(repo, "exploration")).find("channel/item").find(NS).text
    assert ">Overview</h2>" in html
    for it in d["items"]:
        assert html.count(f">{it['title']}</a>") + html.count(f">{it['title']}</h3>") <= 1


def test_research_feed_overview_then_rest(repo):
    _papers(repo)
    html = ET.fromstring(build_feed(repo, "research")).find("channel/item").find(NS).text
    assert html.index(">Overview</h2>") < html.index(">Papers</h2>")
    assert all(html.count(f">Paper {i}</a>") == 1 for i in range(8))
    assert "More papers that passed (2)" in html
    assert html.startswith("<div style=\"font-family:") and 'style="font-family:-apple-system' in html


def test_every_paper_has_an_abstract_toggle_in_feed_and_site(repo):
    from dsys import render
    _papers(repo)
    html = ET.fromstring(build_feed(repo, "research")).find("channel/item").find(NS).text
    assert html.count('<details class="abs"') == 8 and "<summary" in html  # top, more and overview alike
    assert "<details open" not in html
    assert render.arxiv_item(paper("2611.00001")).count('<details class="abs">') == 1
