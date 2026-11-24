"""Retries and fallbacks, alphaXiv and news candidates, the daily digest feed and the quarterly review."""

import importlib.util
import io
import json
import urllib.error
import xml.etree.ElementTree as ET

import pytest

from conftest import ROOT, D, daily, paper
from dsys import arxiv as ax
from dsys import net, news, quarterly, render
from dsys.core import load_json
from dsys.rss import build_feed, for_readers
from dsys.validate import validate_repo


def _fc():
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    return fc


# --- dsys.net ------------------------------------------------------------------------
class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _real_get():
    import importlib
    return importlib.reload(net).get  # undo the conftest stub for these tests


def test_net_retries_429_then_succeeds(monkeypatch):
    get = _real_get()
    monkeypatch.setattr(net, "_sleep", lambda s: waits.append(s))
    waits, calls = [], []

    def fake(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {"Retry-After": "7"}, None)
        return _Resp(b"ok")
    monkeypatch.setattr(net.urllib.request, "urlopen", fake)
    assert get("https://example.org/x") == b"ok"
    assert len(calls) == 3 and waits == [7.0, 7.0]


def test_net_does_not_retry_403(monkeypatch):
    get = _real_get()
    monkeypatch.setattr(net, "_sleep", lambda s: None)
    calls = []

    def fake(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 403, "quota", {}, None)
    monkeypatch.setattr(net.urllib.request, "urlopen", fake)
    with pytest.raises(urllib.error.HTTPError):
        get("https://example.org/x")
    assert len(calls) == 1


def test_net_gives_up_after_all_pauses(monkeypatch):
    get = _real_get()
    monkeypatch.setattr(net, "_sleep", lambda s: None)
    calls = []

    def fake(req, timeout):
        calls.append(1)
        raise urllib.error.URLError("timed out")
    monkeypatch.setattr(net.urllib.request, "urlopen", fake)
    with pytest.raises(urllib.error.URLError):
        get("https://example.org/x", pauses=(1, 1))
    assert len(calls) == 3


# --- arXiv RSS fallback and alphaXiv ---------------------------------------------------
RSS = """<?xml version="1.0"?><rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel>
<item><title>A Good Paper</title><link>https://arxiv.org/abs/2611.11111</link>
<description>arXiv:2611.11111v1 Announce Type: new
Abstract: We study things carefully and report results that matter.</description>
<category>cs.LG</category><category>stat.ML</category>
<pubDate>Tue, 24 Nov 2026 00:00:00 -0500</pubDate><dc:creator>Ada Lovelace, Alan Turing</dc:creator></item>
<item><title>Old Paper</title><link>https://arxiv.org/abs/2601.22222</link>
<description>arXiv:2601.22222v3 Announce Type: replace
Abstract: Replaced.</description></item>
</channel></rss>"""


def test_parse_rss_keeps_new_skips_replacements():
    [p] = ax.parse_rss(RSS, "cs.LG")
    assert p["arxiv_id"] == "2611.11111" and p["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert p["abstract"].startswith("We study") and p["categories"] == ["cs.LG", "stat.ML"]
    assert p["submitted"] == "2026-11-24" and p["source"] == "arxiv_rss"


def test_parse_alphaxiv_is_defensive():
    data = {"papers": [
        {"universal_paper_id": "2611.33333", "title": "Trending  One", "abstract": "Abs.",
         "authors": ["A B", "C D"], "metrics": {"public_total_votes": 42, "visits_count": {"all": 900}},
         "first_publication_date": "2026-11-20T00:00:00Z"},
        {"paper": {"arxivId": "2611.44444v2", "title": "Two", "authorNames": [{"name": "E F"}], "upvotes": "7"}},
        {"title": "no id"}, "junk",
    ]}
    a, b = ax.parse_alphaxiv(data)
    assert a["arxiv_id"] == "2611.33333" and a["alphaxiv_votes"] == 42 and a["alphaxiv_visits"] == 900
    assert a["title"] == "Trending One" and a["submitted"] == "2026-11-20"
    assert b["arxiv_id"] == "2611.44444" and b["authors"] == ["E F"] and b["alphaxiv_votes"] == 7
    assert ax.parse_alphaxiv({"weird": 1}) == [] and ax.parse_alphaxiv(None) == []


def _paper(aid, **kw):
    return {"arxiv_id": aid, "title": "T " + aid, "authors": kw.pop("authors", ["X Y"]), "abstract": "a" * 50,
            "submitted": "2026-11-23", "categories": ["cs.LG"], "url": ax.abs_url(aid), **kw}


def test_fetch_arxiv_rss_fallback_failed_sources_and_retry(repo, monkeypatch):
    fc = _fc()
    cfg = load_json(repo.p("config", "sources.json"))
    cfg["arxiv"]["categories"] = [{"id": "cs.LG"}, {"id": "cs.CL"}]
    cfg["notable_researchers"]["names"] = ["Yoshua Bengio"]
    (repo.p("config", "sources.json")).write_text(json.dumps(cfg))

    def api(cat, n):
        if cat == "cs.CL":
            raise OSError("rate exceeded")
        return [_paper("2611.00001", authors=["Yoshua Bengio", "Z"])]
    monkeypatch.setattr(fc.ax, "fetch_recent", api)
    monkeypatch.setattr(fc.ax, "fetch_rss", lambda cat: [_paper("2611.00002", source="arxiv_rss")])
    monkeypatch.setattr(fc.ax, "fetch_hf_daily", lambda d, api: [])

    def axv_down(*a):
        raise OSError("alphaxiv down")
    monkeypatch.setattr(fc.ax, "fetch_alphaxiv", axv_down)
    fc.fetch_arxiv(repo, D)
    doc = load_json(repo.p("candidates", "arxiv", f"{D}.json"))
    ids = {c["arxiv_id"] for c in doc["candidates"]}
    assert ids == {"2611.00001", "2611.00002"}  # cs.CL came from RSS
    assert doc["failed_sources"] == ["alphaxiv:trending"]
    assert any("cs.CL" in n for n in doc["notes"])
    assert next(c for c in doc["candidates"] if c["arxiv_id"] == "2611.00001")["notable_authors"] == ["Yoshua Bengio"]

    # retry: only alphaXiv is fetched again, and nothing is lost
    calls = []
    monkeypatch.setattr(fc.ax, "fetch_recent", lambda cat, n: calls.append(cat) or [])
    monkeypatch.setattr(fc.ax, "fetch_alphaxiv", lambda *a: [{**_paper("2611.00003"), "alphaxiv_votes": 5}])
    fc.fetch_arxiv(repo, D, retry_failed=True)
    doc = load_json(repo.p("candidates", "arxiv", f"{D}.json"))
    assert calls == [] and doc["failed_sources"] == []
    assert {c["arxiv_id"] for c in doc["candidates"]} == {"2611.00001", "2611.00002", "2611.00003"}


# --- news ------------------------------------------------------------------------------
ATOM_FEED = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Why rupee fell</title><link rel="alternate" href="https://theconversation.com/x-1"/>
<published>2026-11-24T02:00:00Z</published><summary>&lt;p&gt;An expert &lt;b&gt;explains&lt;/b&gt;.&lt;/p&gt;</summary></entry>
<entry><title>Old</title><link href="https://theconversation.com/old"/><published>2026-11-01T00:00:00Z</published></entry>
</feed>"""
RSS_NEWS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Sensex rises</title><link>https://example.in/markets/1</link><pubDate>Tue, 24 Nov 2026 10:00:00 +0530</pubDate>
<description>Markets up.</description></item></channel></rss>"""


def test_news_parse_and_recent():
    import datetime as dt
    items = news.parse(ATOM_FEED) + news.parse(RSS_NEWS)
    assert [i["title"] for i in items] == ["Why rupee fell", "Old", "Sensex rises"]
    assert items[0]["summary"] == "An expert explains ." and items[2]["published"] == "2026-11-24T04:30:00Z"
    now = dt.datetime(2026, 11, 24, 12, tzinfo=dt.timezone.utc)
    assert [i["title"] for i in news.select_recent(items, now, 36)] == ["Why rupee fell", "Sensex rises"]


def test_fetch_news_failed_feed_then_retry(repo, monkeypatch):
    fc = _fc()
    cfg = load_json(repo.p("config", "sources.json"))
    cfg["world"]["feeds"] = [{"name": "Conv", "url": "https://a.org/f", "section": "explainers"},
                             {"name": "Mkts", "url": "https://b.org/f", "section": "economy_markets"}]
    (repo.p("config", "sources.json")).write_text(json.dumps(cfg))
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    monkeypatch.setattr(fc.news, "select_recent", lambda items, now, h: items)

    def fetch(url):
        if "b.org" in url:
            raise OSError("down")
        return news.parse(ATOM_FEED)
    monkeypatch.setattr(fc.news, "fetch", fetch)
    fc.fetch_news(repo, D)
    doc = load_json(repo.p("candidates", "news", f"{D}.json"))
    assert doc["failed_sources"] == ["Mkts"] and len(doc["candidates"]) == 2
    monkeypatch.setattr(fc.news, "fetch", lambda url: news.parse(RSS_NEWS))
    fc.fetch_news(repo, D, retry_failed=True)
    doc = load_json(repo.p("candidates", "news", f"{D}.json"))
    assert doc["failed_sources"] == [] and len(doc["candidates"]) == 3
    assert {c["section"] for c in doc["candidates"]} == {"explainers", "economy_markets"}


# --- rendering, digest feed, quarterly ---------------------------------------------------
def test_for_readers_opens_details_and_tags_have_separators():
    h = for_readers("<details><summary>Answer</summary><p>42</p></details>")
    assert "<details" not in h and "<strong>Answer</strong>" in h and "<p>42</p>" in h
    assert " · " in render.tags_line(["a", "b"])


def test_world_sections_derived():
    assert render.world_section({"topic": "finance", "regions": ["India"]}) == "economy_markets"
    assert render.world_section({"topic": "politics", "regions": ["India"]}) == "india"
    assert render.world_section({"topic": "conflict", "regions": ["Europe"]}) == "world"
    assert render.world_section({"section": "explainers", "topic": "science", "regions": []}) == "explainers"


def test_daily_digest_feed(repo):
    daily(repo, "arxiv", "2026-11-24", [paper()])
    root = ET.fromstring(build_feed(repo, "daily"))
    item = root.find("channel/item")
    assert item.find("guid").text == "dsys:daily:2026-11-24"
    assert item.find("title").text.startswith("Tue 24 Nov: 1 papers")
    html = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text
    assert "<h2>Research</h2>" in html and "arXiv Paper Radar (1)" in html


def test_quarterly_draft_validate_and_feed(repo):
    daily(repo, "arxiv", "2026-11-24", [paper()])
    out = quarterly.draft(repo, "2026-Q4")
    p = repo.p(out["path"])
    doc = load_json(p)
    assert doc["stats"]["counts"]["arxiv"] == 1 and doc["summary"] == ""
    rep = validate_repo(repo)
    assert any("2026-Q4" in e and "summary" in e for e in rep.errors)
    doc["summary"] = "Papers this quarter were mostly about unlearning evaluation."
    p.write_text(json.dumps(doc))
    rep = validate_repo(repo)
    assert not [e for e in rep.errors if "quarterly" in e], rep.errors
    root = ET.fromstring(build_feed(repo, "quarterly"))
    assert root.find("channel/item/guid").text == "dsys:quarterly:2026-Q4"
    # a re-draft keeps the summary
    quarterly.draft(repo, "2026-Q4")
    assert load_json(p)["summary"].startswith("Papers this quarter")
