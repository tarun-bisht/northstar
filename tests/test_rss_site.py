import xml.etree.ElementTree as ET

from conftest import activity, daily, monthly, paper, video, weekly
from dsys.core import STREAM_META
from dsys.rss import build_feed, generate_all
from dsys.site import build_site
from dsys.validate import validate_repo

NS = {"content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}


def test_all_seven_feeds_valid_when_empty(repo, tmp_path):
    out = generate_all(repo, tmp_path / "f")
    assert set(p.name for p in out.values()) == {m["feed"] for m in STREAM_META.values()}
    assert "youtube-shorts.xml" in {p.name for p in out.values()}
    for p in out.values():
        ET.parse(p)


def test_escaping_and_guids(repo):
    nasty = 'Bias & <script>alert("x")</script> ]]> test'
    daily(repo, "arxiv", "2026-11-24", [paper(title=nasty, abstract="Uses <b>tags</b> & ampersands in an abstract that is long enough.")])
    xml = build_feed(repo, "arxiv")
    root = ET.fromstring(xml)
    item = root.find("channel/item")
    assert item.find("title").text.endswith(nasty)
    assert item.find("guid").text == "dsys:arxiv:arxiv-2611.01234"
    assert item.find("guid").get("isPermaLink") == "false"
    html = item.find("content:encoded", NS).text
    assert "Uses &lt;b&gt;tags&lt;/b&gt; &amp; ampersands" in html and "<b>tags" not in html
    assert item.find("title").text.startswith("[close to your work]")
    assert "]]&gt;" in xml or "]]>" not in xml.split("<title>", 2)[2]


def test_deterministic(repo):
    daily(repo, "arxiv", "2026-11-24", [paper(), paper("2611.04321")])
    assert build_feed(repo, "arxiv") == build_feed(repo, "arxiv")


def test_rolling_window(repo):
    policy = repo.config("recommendation_policy")
    policy["feeds"]["arxiv"] = 3
    from dsys.core import write_json
    write_json(repo.p("config", "recommendation_policy.json"), policy)
    daily(repo, "arxiv", "2026-11-23", [paper("2611.00001"), paper("2611.00002")])
    daily(repo, "arxiv", "2026-11-24", [paper("2611.00003"), paper("2611.00004")])
    items = ET.fromstring(build_feed(repo, "arxiv")).findall("channel/item")
    assert len(items) == 3
    assert items[0].find("guid").text.endswith("2611.00003")  # newest day, original order


def test_youtube_feed_embed(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video()])
    root = ET.fromstring(build_feed(repo, "youtube_shorts"))
    item = root.find("channel/item")
    html = item.find("content:encoded", NS).text
    assert 'src="https://www.youtube.com/embed/abcDEF12345"' in html
    assert "Watch on YouTube" in html and "hqdefault.jpg" in html
    assert item.find("media:thumbnail", NS).get("url").endswith("/abcDEF12345/hqdefault.jpg")
    assert item.find("link").text == "https://www.youtube.com/shorts/abcDEF12345"


def test_weekly_monthly_feeds_and_site(repo, tmp_path):
    weekly(repo, items=[activity("w-1", hints=["h1", "h2"], category="research_fundamentals", steps=["try n=23", "derive"],
                                 resources=[{"title": "A probability book", "type": "book", "chapters": "Ch. 1"}])])
    monthly(repo)
    daily(repo, "world", "2026-11-24", [])
    assert validate_repo(repo).ok
    guids = {i.find("guid").text for i in ET.fromstring(build_feed(repo, "weekly")).findall("channel/item")}
    assert {"dsys:weekly:2026-W49:research", "dsys:weekly:2026-W49:exploration"} <= guids
    out = build_site(repo, tmp_path / "site")
    assert not (out / "ideas.html").exists()  # ideas stay in the repo, not on the website
    feeds_page = (out / "index.html").read_text()
    for name in ("research", "news", "exploration", "arxiv", "research-updates", "world", "discovery", "youtube-shorts",
                 "weekly", "monthly", "quarterly"):
        assert f"feeds/{name}.xml" in feeds_page
    assert "<nav class=\"main\"" not in feeds_page and not (out / "feeds.html").exists()
    for f in ["index.html", "archive.html", "docs.html", "vision.html",
              "weekly/2026-W49.html", "weekly/2026-W49/index.html", "weekly/2026-W49/research.html",
              "weekly/2026-W49/knowledge.html", "weekly/2026-W49/exploration.html",
              "monthly/2026-12/index.html", "monthly/2026-12/research.html", "monthly/2026-12/exploration.html",
              "daily/2026-11-24/index.html", "daily/2026-11-24/news.html", "feeds/youtube-shorts.xml"]:
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
    import datetime as dt
    import dsys.rss as rss
    start = dt.date(2026, 1, 1)
    for d in range(60):
        day = (start + dt.timedelta(days=d)).isoformat()
        daily(repo, "arxiv", day, [paper(aid=f"2601.{d:05d}")])
    site = repo.config("site")
    full = rss.collect_items(repo, "arxiv", site)
    loaded = []
    real = rss.load_json
    monkeypatch.setattr(rss, "load_json", lambda f: loaded.append(f) or real(f))
    fast = rss.collect_items(repo, "arxiv", site, limit=5)
    assert len(loaded) == 5
    assert [e["guid"] for e in fast] == [e["guid"] for e in full[:5]]
    assert fast[0]["guid"].endswith("2601.00059")
