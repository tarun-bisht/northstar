"""The staged pipeline: reputation, social sources, page-1 parsing, feed health, compact
readers with 3-day dedupe, stats, alphaXiv links and folded extras."""

import datetime as dt
import json
import urllib.error

from conftest import D
from dsys import feeds as fd
from dsys import net, render, reputation, stages
from dsys.core import load_json, write_json


def test_reputation_matches_people_orgs_and_domains():
    reg = reputation.Registry({"researchers": [{"name": "Yann LeCun"}],
                               "labs": [{"name": "Sakana AI", "aliases": [], "domains": ["sakana.ai"]}],
                               "universities": [{"name": "Indian Institute of Technology Bombay", "aliases": ["IIT Bombay"],
                                                 "domains": ["iitb.ac.in"]},
                                                {"name": "Carnegie Mellon University", "aliases": ["CMU"], "domains": ["cmu.edu"]}]})
    assert reputation.apply(reg, {"authors": ["Yann LeCun"]})["trusted"] == 1
    p = reputation.apply(reg, {"authors": ["A"], "affiliations": ["Dept. of CSE, IIT Bombay"]})
    assert p["trusted"] == 1 and p["trust_matches"] == ["Indian Institute of Technology Bombay"]
    assert reputation.apply(reg, {"authors": ["A"], "email_domains": ["cs.cmu.edu"]})["trusted"] == 1
    assert reputation.apply(reg, {"authors": ["A"], "organizations": ["Sakana AI"]})["trusted"] == 1
    assert reputation.apply(reg, {"authors": ["A"], "affiliations": ["Academy of cmu-like studies"]})["trusted"] == 0
    assert reputation.apply(reg, {"authors": ["A"], "email_domains": ["gmail.com"]})["trusted"] == 0


def test_registry_file_is_well_formed():
    from conftest import ROOT
    d = json.loads((ROOT / "config" / "reputation.json").read_text())
    names = [o["name"] for o in d["labs"]]
    assert {"Sakana AI", "Prior Labs", "Sarvam AI", "Google DeepMind", "Anthropic"} <= set(names)
    assert len(names) == len(set(names))
    assert all(isinstance(o.get("domains", []), list) for o in d["labs"] + d["universities"])
    reputation.Registry(d)  # every name compiles


def test_reputation_log_and_suggestions(repo):
    for k in range(3):
        reputation.log_papers(repo, D, [{"arxiv_id": f"2611.0000{k}", "authors": ["New Person"],
                                         "affiliations": ["Tiny Lab of Wonders"]}], "picked")
    s = reputation.suggestions(repo, 3)
    assert s["authors"][0][0] == "New Person" and s["orgs"][0][0] == "Tiny Lab of Wonders"


def test_arxiv_ids_and_bluesky_parse():
    assert fd.arxiv_ids("see arxiv.org/abs/2511.01234v2 and alphaxiv.org/abs/2510.00042, not 3.14159") == ["2511.01234", "2510.00042"]
    posts = fd.parse_bluesky({"posts": [{"uri": "at://did:plc:x/app.bsky.feed.post/3abc", "author": {"handle": "a.bsky.social"},
                                         "record": {"text": "New paper arxiv.org/abs/2511.01234", "createdAt": "2026-11-25T01:00:00Z"},
                                         "likeCount": 40}]})
    assert posts[0]["url"] == "https://bsky.app/profile/a.bsky.social/post/3abc" and posts[0]["likes"] == 40


def test_page1_parsers():
    html = ('<span class="ltx_contact ltx_role_affiliation">Massachusetts Institute of Technology</span>'
            '<span class="ltx_contact ltx_role_email">jane@csail.mit.edu</span><div class="ltx_abstract">x</div>')
    got = fd.parse_html_front(html)
    assert got["affiliations"] == ["Massachusetts Institute of Technology"] and got["email_domains"] == ["csail.mit.edu"]
    txt = fd.parse_text_front("A Title\nJane Doe\nDepartment of Physics, University of Tokyo\njane@u-tokyo.ac.jp\nAbstract\nWe ...")
    assert "Department of Physics, University of Tokyo" in txt["affiliations"] and txt["email_domains"] == ["u-tokyo.ac.jp"]


def test_feed_health_skips_dead_links_and_retries_weekly(tmp_path):
    h = fd.FeedHealth(tmp_path / "fh.json", D)
    err = urllib.error.HTTPError("https://x", 404, "gone", {}, None)
    h.record("https://x", "X", err)
    assert h.data["https://x"]["dead_since"] == D.isoformat()
    h2 = fd.FeedHealth(tmp_path / "fh.json", D + dt.timedelta(days=1))
    h.save()
    h2 = fd.FeedHealth(tmp_path / "fh.json", D + dt.timedelta(days=1))
    assert h2.skip("https://x") is True
    assert fd.FeedHealth(tmp_path / "fh.json", D + dt.timedelta(days=7)).skip("https://x") is False
    h.record("https://y", "Y", urllib.error.HTTPError("https://y", 403, "blocked", {}, None))
    assert "dead_since" not in h.data["https://y"]  # a 403 is skipped today, not marked dead


def test_net_does_not_retry_permanent_errors(monkeypatch):
    from tests_helpers import real_get
    calls = []

    def fake(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 404, "gone", {}, None)
    monkeypatch.setattr(net.urllib.request, "urlopen", fake)
    try:
        real_get()("https://example.org/x")
    except urllib.error.HTTPError:
        pass
    assert len(calls) == 1 and net.is_permanent(urllib.error.HTTPError("u", 410, "", {}, None))


def test_fetch_many_isolates_failures_and_tries_alternates():
    def fn(u):
        if "bad" in u:
            raise OSError("down")
        return [{"title": u}]
    out = fd.fetch_many([{"name": "a", "url": "https://bad/1", "alternates": ["https://good/1"]},
                         {"name": "b", "url": "https://bad/2"}], fn)
    assert out["a"][0] == [{"title": "https://good/1"}] and out["b"][0] is None


def _arxiv_file(repo, papers):
    write_json(repo.p("candidates", "arxiv", f"{D}.json"), {"kind": "arxiv", "date": str(D), "candidates": papers})


def _paper(aid, title, abstract, cats=("cs.LG",), **kw):
    return {"arxiv_id": aid, "title": title, "abstract": abstract, "authors": ["A B"], "categories": list(cats),
            "primary_category": cats[0], "submitted": str(D), "url": f"https://arxiv.org/abs/{aid}", **kw}


def test_stage1_skips_no_interest_no_signal_then_merge_and_stage2(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(stages, "WORK", tmp_path)
    cfg = load_json(repo.p("config", "sources.json"))
    cfg["arxiv"]["coverage"]["topics"] = [{"interest": "machine unlearning", "categories": ["cs.LG"], "keywords": ["unlearning"]}]
    write_json(repo.p("config", "sources.json"), cfg)
    _arxiv_file(repo, [_paper("2611.00001", "Machine unlearning at scale", "We study unlearning."),
                       _paper("2611.00002", "Crop yields", "Farming data."),
                       _paper("2611.00003", "A hot paper", "Something else.", hf_upvotes=40)])
    s1 = stages.stage1(repo, D)
    assert s1["read_stage1"] == 2 and s1["skipped"] == 1
    b = s1["batches"][0]
    assert b["papers"] == 2 and b["write"].endswith("verdict_01.json")
    rows = [json.loads(line) for line in open(b["read"]).read().splitlines()]
    assert rows[0]["id"] == "2611.00001" and set(rows[0]) == {"id", "t", "a", "i", "s", "tr", "b"}
    v = tmp_path / "v.json"
    v.write_text(json.dumps([{"id": "2611.00001", "lane": "strong"}, {"id": "2611.00003", "lane": "field"}]))
    m = stages.merge_verdicts(repo, D, [str(v)])
    assert m["passed"] == 2 and m["ids"] == "2611.00001,2611.00003"
    write_json(repo.p("candidates", "affil", f"{D}.json"),
               {"papers": {"2611.00001": {"affiliations": ["Carnegie Mellon University"], "email_domains": ["cmu.edu"]}}})
    s2 = stages.stage2(repo, D)
    assert [r["id"] for r in s2] == ["2611.00001", "2611.00003"]
    assert s2[0]["lane"] == "strong" and s2[0]["alphaxiv"] == "https://www.alphaxiv.org/abs/2611.00001"
    st = stages.stats(repo, D)["streams"]["papers"]
    assert st["fetched"] == 3 and st["read_stage1"] == 2 and st["passed_stage1"] == 2 and st["read_stage2"] == 2


def test_compact_updates_drop_recent(repo):
    write_json(repo.p("candidates", "updates", f"{D}.json"), {"candidates": [
        {"title": "Lab releases model X", "url": "https://lab/x", "source": "Lab", "kind": "lab", "summary": "s" * 2000},
        {"title": "Old story", "url": "https://old", "source": "Lab", "kind": "lab"}]})
    prev = repo.daily_path("research_updates", (D - dt.timedelta(days=1)).isoformat())
    write_json(prev, {"schema": "research_updates", "date": str(D - dt.timedelta(days=1)), "items": [
        {"id": "u1", "title": "Old story", "source": {"url": "https://old"}}]})
    rows = stages.compact_updates(repo, D)
    assert [r["t"] for r in rows] == ["Lab releases model X"] and len(rows[0]["x"]) == 1200


def test_alphaxiv_links_and_new_tab():
    assert render.paper_link("https://arxiv.org/abs/2511.01234v3") == "https://www.alphaxiv.org/abs/2511.01234"
    html = render.a("https://arxiv.org/pdf/2511.01234", "paper")
    assert "alphaxiv.org/abs/2511.01234" in html and 'target="_blank"' in html
    assert render.paper_link("https://example.org/x") == "https://example.org/x"


def test_interest_news_queries():
    from dsys import news
    b = news.interest_batches({"established": {"ai_research": ["machine unlearning", "agents", "world models"]}},
                              {"groups": ["established.ai_research"], "batch_size": 5})
    assert b == ['("machine unlearning" OR "world models")']  # single lowercase words are too noisy


def test_reputation_add_appends_with_evidence_and_skips_known(repo):
    from dsys import reputation
    r = reputation.add(repo, "lab", "Tiny Frontier Lab", ["2611.00001", "2611.00002"], aliases=["TFL"], lab_kind="frontier")
    assert r["added"] and r["labs"]["kind"] == "frontier"
    doc = load_json(repo.p("config", "reputation.json"))
    assert doc["added"][-1]["evidence"] == ["2611.00001", "2611.00002"]
    assert reputation.add(repo, "lab", "tiny frontier lab", ["2611.00003"])["added"] is False
    assert reputation.add(repo, "lab", "TFL", ["2611.00003"])["added"] is False


def test_enrich_ids_strong_first_capped(repo):
    import json as _j
    from dsys import stages
    day = D
    write_json(repo.p("candidates", "arxiv", f"{day}.json"),
               {"candidates": [_paper(f"2611.000{i:02d}", f"P{i}", "x", hf_upvotes=i) for i in range(10)]})
    (stages.WORK / day.isoformat()).mkdir(parents=True, exist_ok=True)
    (stages.WORK / day.isoformat() / "stage1_passed.json").write_text(
        _j.dumps({f"2611.000{i:02d}": ("strong" if i < 3 else "field") for i in range(10)}))
    ids = stages.enrich_ids(repo, day, limit=5)
    assert ids[:3] == ["2611.00002", "2611.00001", "2611.00000"] and len(ids) == 5 and ids[3] == "2611.00009"


def test_lean_media_keeps_needed_fields_and_clips_text():
    from dsys.stages import lean_media
    doc = {"candidates": [{"video_id": "abcDEF12345", "title": "T", "url": "u", "embed_url": "e", "thumbnail": "t",
                           "channel": {"name": "C", "id": "UCx"}, "description": "word " * 400, "tags": list("abcdefgh"),
                           "views": 9}]}
    c = lean_media(doc)["candidates"][0]
    assert {"video_id", "url", "embed_url", "thumbnail", "views"} <= set(c) and c["channel"] == {"name": "C"}
    assert len(c["description"]) <= 301 and c["tags"] == list("abcde")
