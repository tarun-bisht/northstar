import xml.etree.ElementTree as ET

from conftest import activity, daily, example, monthly, paper, video, weekly
from dsys.core import FEEDS
from dsys.rss import build_feed, generate_all
from dsys.site import build_site
from dsys.validate import validate_repo

NS = {"content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}


def test_every_feed_valid_when_empty(repo, tmp_path):
    out = generate_all(repo, tmp_path / "f")
    assert set(p.name for p in out.values()) == {m["file"] for m in FEEDS.values()}
    assert {"research.xml", "news.xml", "exploration.xml", "reading.xml", "weekly-knowledge.xml",
            "monthly-exploration.xml", "quarterly-research.xml"} <= {p.name for p in out.values()}
    assert "arxiv.xml" not in {p.name for p in out.values()}  # no single-stream feeds
    for p in out.values():
        ET.parse(p)


def test_old_feed_files_are_removed(repo, tmp_path):
    (tmp_path / "f").mkdir()
    (tmp_path / "f" / "arxiv.xml").write_text("<rss/>")
    generate_all(repo, tmp_path / "f")
    assert not (tmp_path / "f" / "arxiv.xml").exists()


def test_escaping_and_guids(repo):
    nasty = 'Bias & <script>alert("x")</script> ]]> test'
    daily(repo, "arxiv", "2026-11-24", [paper(title=nasty, abstract="Uses <b>tags</b> & ampersands in an abstract that is long enough.")])
    xml = build_feed(repo, "research")
    root = ET.fromstring(xml)
    item = root.find("channel/item")
    assert item.find("guid").text == "dsys:research:2026-11-24"
    assert item.find("guid").get("isPermaLink") == "false"
    html = item.find("content:encoded", NS).text
    assert "Bias &amp; &lt;script&gt;" in html and "<script>" not in html


def test_deterministic(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(), paper("2611.04321")])
    assert build_feed(repo, "research") == build_feed(repo, "research")


def test_rolling_window(repo):
    policy = repo.config("recommendation_policy")
    policy["feeds"]["research"] = 2
    from dsys.core import write_json
    write_json(repo.p("config", "recommendation_policy.json"), policy)
    for d in ("2026-11-22", "2026-11-23", "2026-11-24"):
        daily(repo, "arxiv", d, [paper(f"2611.0000{d[-1]}")])
    items = ET.fromstring(build_feed(repo, "research")).findall("channel/item")
    assert [i.find("guid").text for i in items] == ["dsys:research:2026-11-24", "dsys:research:2026-11-23"]


def test_shorts_in_their_own_feed(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video(title='Fourier & "waves" <fast>')])
    assert ET.fromstring(build_feed(repo, "exploration")).find("channel/item") is None
    item = ET.fromstring(build_feed(repo, "shorts")).find("channel/item")
    html = item.find("content:encoded", NS).text
    assert "youtube.com/embed/abcDEF12345" in html and "&lt;fast&gt;" in html
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in html and "allowfullscreen" in html
    assert "youtube.com/shorts/abcDEF12345" in html  # the fallback link
    assert item.find("link").text.endswith("/daily/2026-11-24/shorts.html")


def test_weekly_monthly_feeds_and_site(repo, tmp_path):
    weekly(repo, items=[activity("w-1", hints=["h1", "h2"], category="research_fundamentals", steps=["try n=23", "derive"],
                                 resources=[{"title": "A probability book", "type": "book", "chapters": "Ch. 1"}])])
    monthly(repo)
    daily(repo, "world", "2026-11-24", [])
    assert validate_repo(repo).ok
    for part in ("research", "knowledge", "exploration"):
        items = ET.fromstring(build_feed(repo, f"weekly-{part}")).findall("channel/item")
        assert [i.find("guid").text for i in items] == [f"dsys:weekly:2026-W49:{part}"]
        assert items[0].find("link").text.endswith(f"/weekly/2026-W49/{part}.html")
    assert "Hint 2" in build_feed(repo, "weekly-research") and "Hint 2" not in build_feed(repo, "weekly-exploration")
    assert ET.fromstring(build_feed(repo, "monthly-research")).find("channel/item") is not None
    out = build_site(repo, tmp_path / "site")
    assert not (out / "ideas.html").exists()  # ideas stay in the repo, not on the website
    feeds_page = (out / "index.html").read_text()
    for name in ("research", "news", "exploration", "reading", "weekly-research", "weekly-knowledge",
                 "weekly-exploration", "monthly-research", "monthly-knowledge", "monthly-exploration"):
        assert f"feeds/{name}.xml" in feeds_page
    assert "<nav class=\"main\"" not in feeds_page and not (out / "feeds.html").exists()
    for f in ["index.html", "archive.html", "docs.html", "vision.html",
              "weekly/2026-W49.html", "weekly/2026-W49/index.html", "weekly/2026-W49/research.html",
              "weekly/2026-W49/knowledge.html", "weekly/2026-W49/exploration.html",
              "monthly/2026-12/index.html", "monthly/2026-12/research.html", "monthly/2026-12/exploration.html",
              "daily/2026-11-24/index.html", "daily/2026-11-24/news.html", "feeds/weekly-knowledge.xml"]:
        assert (out / f).exists(), f
    assert "Hint 2" in (out / "weekly/2026-W49/research.html").read_text()
    assert "Hint 2" not in (out / "weekly/2026-W49/exploration.html").read_text()


def test_site_uses_configured_focus_names(repo, tmp_path):
    from dsys.core import load_json, write_json
    cfg = load_json(repo.p("config", "interests.json"))
    cfg["dimensions"] = {"craft": {"name": "Craft"}, "health": {"name": "Movement"}}
    write_json(repo.p("config", "interests.json"), cfg)
    out = build_site(repo, tmp_path / "s")
    html = (out / "index.html").read_text()
    assert "Craft" in html and "Movement" in html and "People &amp; self" not in html


def test_feed_reads_only_newest_files(repo, monkeypatch):
    import dsys.rss as rss
    for w in range(30, 50):
        weekly(repo, f"2026-W{w:02d}", with_reading=False)
    site = repo.config("site")
    full = rss.collect_items(repo, "weekly-research", site)
    loaded = []
    real = rss.load_json
    monkeypatch.setattr(rss, "load_json", lambda f: loaded.append(f) or real(f))
    fast = rss.collect_items(repo, "weekly-research", site, limit=5)
    assert len(loaded) == 5
    assert [e["guid"] for e in fast] == [e["guid"] for e in full[:5]]
    assert fast[0]["guid"] == "dsys:weekly:2026-W49:research"


def test_feed_is_rss2_with_cdata_plain_description_and_no_scripts(repo):
    from dsys.rss import cdata, for_readers, plain_text
    w = example("w", "world")
    w["items"][0]["what_happened"] = "Rates rose; see x_{l+1} = x_l + f(x_l) and \\frac{a}{b}. Costs $83 now."
    daily(repo, "world", "2026-11-24", w["items"], briefs=w.get("briefs", []))
    raw = build_feed(repo, "news")
    assert 'xmlns:content="http://purl.org/rss/1.0/modules/content/"' in raw and '<rss version="2.0"' in raw
    assert "<content:encoded><![CDATA[" in raw
    item = ET.fromstring(raw).find("channel/item")
    desc = item.find("description").text
    assert "<" not in desc and "&lt;" not in desc
    html = item.find("content:encoded", NS).text
    assert "x<sub>l+1</sub> = x<sub>l</sub> + f(x<sub>l</sub>)" in html
    assert "<math" in html and "<mfrac>" in html and "$83" in html
    assert "<script" not in for_readers('<p>a</p><script>alert(1)</script><link rel="stylesheet" href="s.css"><style>p{}</style>')
    assert cdata("a]]>b") == "<![CDATA[a]]]]><![CDATA[>b]]>"
    assert ET.fromstring(f"<x>{cdata('a]]>b')}</x>").text == "a]]>b"
    assert plain_text("<p>Hi &amp; <b>bye</b></p>") == "Hi & bye"


def test_youtube_links_become_players_with_fallback():
    from dsys import render
    for url, short in [("https://www.youtube.com/watch?v=abcDEF12345", False), ("https://youtu.be/abcDEF12345", False),
                       ("https://www.youtube.com/shorts/abcDEF12345", True), ("https://m.youtube.com/watch?v=abcDEF12345&t=3", False)]:
        h = render.media_embed(url, "T")
        assert "https://www.youtube.com/embed/abcDEF12345" in h and "allowfullscreen" in h
        assert 'referrerpolicy="strict-origin-when-cross-origin"' in h
        assert ("youtube.com/shorts/abcDEF12345" in h) == short and ("aspect-ratio:9/16" in h) == short
    from dsys.rss import for_readers
    opened = for_readers(render.media_embed("https://youtu.be/abcDEF12345", "T"))
    assert "<details" not in opened and "Play here" not in opened and opened.startswith('<div class="yt">')
