import datetime as dt
import importlib.util
import json
import xml.etree.ElementTree as ET

import pytest

from conftest import ROOT, D, activity, daily, language_pack, shorts_day, video, weekly
from dsys import diversity, ideas, profile
from dsys import youtube as yt
from dsys.core import load_json, write_json
from dsys.history import context, ignored_counts, rebuild
from dsys.rss import build_feed
from dsys.validate import validate_repo


def rec(rid, **kw):
    r = {"id": rid, "title": f"Title {rid}", "type": "article", "category": "physics", "topic": "entropy",
         "description": "d", "why_recommended": "w", "tier": "established", "action": "read", "time_required": "30m",
         "dimensions": ["knowledge"]}
    r.update(kw)
    return r


# --- ideas: seeds vs explicit intent ---------------------------------------------------
def test_seed_ideas_cannot_start_as_explicit_intent():
    r = {"ideas": []}
    for st in ("wants_to_try", "planned", "in_progress"):
        with pytest.raises(ideas.IdeaError):
            ideas.add(r, f"seed {st}", D, origin="seed", status=st)
    ideas.add(r, "seed ok", D, origin="seed", status="interested")
    assert ideas.explicit_intent_errors(r) == []


def test_real_seed_ideas_are_curiosity_or_interest():
    reg = load_json(ROOT / "state" / "ideas.json")
    for i in reg["ideas"]:
        if i["origin"] == "seed":
            assert i["status"] in ("curiosity", "interested"), i["id"]
            assert "scheduled_for" not in i


def test_hand_edited_seed_intent_is_caught(repo):
    r = ideas.load(repo)
    ideas.add(r, "A seed", D, origin="seed")
    r["ideas"][0]["status"] = "planned"  # simulate a planner or hand edit
    ideas.save(repo, r)
    assert any("without an explicit user action" in e for e in validate_repo(repo).errors)
    # an explicit status change by the user is fine
    r = ideas.load(repo)
    ideas.set_status(r, "idea-a-seed", "wants_to_try", D, "user asked")
    ideas.save(repo, r)
    assert not any("explicit user action" in e for e in validate_repo(repo).errors)


def test_user_idea_can_be_scheduled_and_curiosity_is_not(repo):
    r = {"ideas": []}
    ideas.add(r, "Try pottery", D)
    ideas.add(r, "Curious about tides", D, status="curiosity")
    ideas.schedule(r, "idea-try-pottery", "2026-W49", D)
    due = ideas.due_for(r, "2026-W49")
    assert [i["id"] for i in due["scheduled"]] == ["idea-try-pottery"]
    assert "scheduled_for" not in ideas.get(r, "idea-curious-about-tides")


def test_open_pool_ranks_user_wishes_before_seeds():
    r = {"ideas": []}
    ideas.add(r, "Seed thing", D, origin="seed", status="interested", scope="weekly")
    ideas.add(r, "My wish", D, status="wants_to_try", scope="weekly")
    pool = ideas.due_for(r, "2026-W49")["open"]
    assert pool[0]["id"] == "idea-my-wish"


def test_dropped_ideas_not_reintroduced(repo):
    r = ideas.load(repo)
    ideas.add(r, "Learn juggling", D)
    ideas.drop(r, "idea-learn-juggling", D, "not for me")
    ideas.save(repo, r)
    ctx = context(repo, "weekly", D, "2026-W49")
    assert all(i["id"] != "idea-learn-juggling" for i in ctx["ideas_open_pool"])
    assert "learn juggling" in ctx["preferences"]["avoid"]


def test_rescheduling_does_not_build_a_backlog():
    r = {"ideas": []}
    ideas.add(r, "x", D)
    ideas.schedule(r, "idea-x", "2026-W49", D)
    ideas.schedule(r, "idea-x", "2026-W50", D, limit=2)
    # the idea is in exactly one period at a time
    assert ideas.due_for(r, "2026-W49")["scheduled"] == []
    assert len(ideas.due_for(r, "2026-W50")["scheduled"]) == 1


# --- preferences ---------------------------------------------------------------------------
def test_feedback_updates_profile_and_explicit_beats_inferred(repo):
    from dsys import feedback as fb
    weekly(repo, "2026-W46", items=[activity("w-a", topic="maps"), activity("w-b", topic="poetry")])
    rebuild(repo)  # both untouched in a finished week -> ignored
    prof = profile.load(repo)
    assert prof["inferred"]["ignored"].get("maps") == 1
    weekly(repo, "2026-W49", items=[activity("w-c", topic="maps"), activity("w-d", topic="sculpture")])
    fb.record(repo, "2026-W49", [{"item_id": "w-c", "status": "completed", "interest": "more"},
                                 {"item_id": "w-d", "status": "skipped", "interest": "not_interested"}], D)
    fb.apply(repo, "2026-W49", D)
    prof = profile.load(repo)
    assert "maps" in prof["explicit"]["more"] and "maps" not in prof["inferred"]["ignored"]
    assert "sculpture" in prof["explicit"]["not_interested"]
    view = profile.planning_view(prof)
    assert "sculpture" in view["avoid"] and "maps" in view["want_more"]


def test_ignored_is_not_disliked(repo):
    weekly(repo, "2026-W40", items=[activity("w-1", topic="theatre")])
    weekly(repo, "2026-W41", items=[activity("w-2", topic="theatre")])
    rebuild(repo)
    view = profile.planning_view(profile.load(repo))
    assert "theatre" in view["ignored_hint"]
    assert "theatre" not in view["avoid"]  # never treated as dislike
    assert "NOT dislike" in view["_how_to_use"]


def test_newer_explicit_signal_replaces_opposite():
    doc = profile.empty()
    profile.add_explicit(doc, "less", "anime", D)
    profile.add_explicit(doc, "more", "anime", D)
    assert "anime" in doc["explicit"]["more"] and "anime" not in doc["explicit"]["less"]


def test_current_period_items_not_counted_as_ignored(repo):
    weekly(repo, "2026-W48", items=[activity("w-now", topic="opera")])  # contains 2026-11-24
    assert "opera" not in ignored_counts(repo, D)


# --- diversity and cross-domain ---------------------------------------------------------------
MEDIA_PAIR = [rec("disc-pod", type="podcast", action="listen", tier="established"),
              rec("disc-vid", type="video", action="watch", tier="growth"),
              rec("disc-exp", tier="exploration", dimensions=["world"])]


def test_cross_domain_is_a_schema_type(repo):
    daily(repo, "discovery", "2026-11-24", [rec("disc-1", cross_domain={"fields": ["cinema", "psychology"],
                                                                          "connection": "How editing shapes empathy."})] + MEDIA_PAIR)
    daily(repo, "language", "2026-11-24", [language_pack()])
    assert validate_repo(repo).ok
    daily(repo, "discovery", "2026-11-24", [rec("disc-1", cross_domain={"fields": ["one"], "connection": "too few fields"})] + MEDIA_PAIR)
    assert not validate_repo(repo).ok


def test_variety_report_flags_tier_gaps(repo):
    items = [rec(f"disc-{i}", tier="established", category="machine learning", dimensions=["research"]) for i in range(4)]
    daily(repo, "discovery", "2026-11-24", items)
    joined = " ".join(diversity.report(repo, D, 30)["suggestions"])
    assert "No exploration" in joined and "No growth" in joined and "cross-domain" in joined and "Not touched" in joined


def test_variety_report_satisfied_by_tiered_mix(repo):
    items = [rec("disc-a", tier="established", dimensions=["research"]),
             rec("disc-b", tier="growth", dimensions=["knowledge"],
                 cross_domain={"fields": ["neuroscience", "AI"], "connection": "Predictive coding meets transformers."}),
             rec("disc-c", tier="exploration", dimensions=["world", "culture"]),
             rec("disc-d", tier="established", dimensions=["people", "curiosity"])]
    daily(repo, "discovery", "2026-11-24", items)
    r = diversity.report(repo, D, 30)
    assert r["suggestions"] == [] and r["tiers"] == {"established": 2, "growth": 1, "exploration": 1}


def test_context_exposes_preferences_variety_and_seed_rule(repo):
    ctx = context(repo, "weekly", D, "2026-W49")
    for k in ("preferences", "variety", "interests_hint", "seed_rule"):
        assert k in ctx
    assert "never mark it planned" in ctx["seed_rule"]
    d = context(repo, "discovery", D)
    assert "variety" in d and "preferences" in d


def test_tiers_and_culture_coverage_in_config():
    c = load_json(ROOT / "config" / "interests.json")
    for t in ("established", "growth", "exploration"):
        assert isinstance(c[t], dict)
    blob = json.dumps(c["exploration"]["culture"] + c["growth"]["humanities_and_culture"]).lower()
    for form in ("literature", "biograph", "poetry", "cinema", "animation", "music", "art history", "design",
                 "folklore", "languages", "anime", "documentar", "theatre", "travel"):
        assert form in blob, form
    assert "popularity" in c["culture_guidance"]
    assert "AI agents: planning, memory, tool use and multi-agent systems" in c["established"]["ai_research"]
    assert {"topology", "analysis", "cognitive science"} <= set(c["growth"]["for_research"])
    assert "Antarctica" in c["world"]["regions"] and "Japan" in c["world"]["regions"]


def test_no_repeated_unwanted_recommendation_in_context(repo):
    from dsys import feedback as fb
    weekly(repo, "2026-W49", items=[activity("w-x", topic="crossword puzzles")])
    fb.record(repo, "2026-W49", [], D, general={"less_of": ["crossword puzzles"]})
    fb.apply(repo, "2026-W49", D)
    assert "crossword puzzles" in context(repo, "discovery", D)["preferences"]["avoid"]


# --- YouTube ---------------------------------------------------------------------------------
def test_short_claim_needs_evidence(repo):
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(video(format_evidence="none")))
    assert any("needs format_evidence" in e for e in validate_repo(repo).errors)
    v = video(format="unknown", format_evidence="none")
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(v))  # /shorts/ URL with unknown format
    assert any("asserts the video is a Short" in e for e in validate_repo(repo).errors)
    v["url"] = yt.watch_url(v["video_id"])
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(v))
    assert validate_repo(repo).ok


def test_shorts_url_check_classification(monkeypatch):
    class R:
        def __init__(self, status): self.status = status

    class C:
        status = 200
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pass
        def getresponse(self): return R(C.status)
        def close(self): pass

    monkeypatch.setattr(yt.http.client, "HTTPSConnection", C)
    assert yt.shorts_url_check("abcDEF12345") == "short"
    C.status = 303
    assert yt.shorts_url_check("abcDEF12345") == "short_form"
    C.status = 404
    assert yt.shorts_url_check("abcDEF12345") == "unknown"
    assert yt.shorts_url_check("bad") == "unknown"


def test_filter_candidates_dedup_language_and_creators():
    mk = lambda vid, title, ch="A", lang="en", dur=50: {"video_id": vid, "title": title, "channel": {"name": ch},
                                                       "language": lang, "duration_seconds": dur}
    cands = [mk("aaaaaaaaaa1", "Why is the sky blue? #shorts"), mk("aaaaaaaaaa2", "why is the sky blue"),
             mk("aaaaaaaaaa3", "Seen before"), mk("aaaaaaaaaa4", "Too long", dur=900),
             mk("aaaaaaaaaa5", "French thing", lang="fr"), mk("aaaaaaaaaa6", "भौतिकी सरल भाषा में", lang="hi"),
             mk("bad", "invalid id")] + [mk(f"bbbbbbbbbb{i}", t, ch="B") for i, t in enumerate(
                 ["Volcanoes of Iceland", "How bees dance", "The Mughal water gardens", "Prime spirals explained",
                  "Why glass is a liquid myth", "Octopus camouflage"])]
    kept, why = yt.filter_candidates(cands, {"aaaaaaaaaa3"}, ["Old title"], per_channel=3)
    ids = [c["video_id"] for c in kept]
    assert "aaaaaaaaaa1" in ids and "aaaaaaaaaa2" not in ids and "aaaaaaaaaa6" in ids
    assert why["already_seen"] == 1 and why["too_long"] == 1 and why["language"] == 1
    assert why["invalid_id"] == 1 and why["near_duplicate_title"] == 1 and why["channel_cap"] == 3


def test_hindi_and_english_discovery_configured():
    yt_cfg = load_json(ROOT / "config" / "sources.json")["youtube"]
    langs = {g["language"] for g in yt_cfg["query_groups"]}
    assert {"en", "hi"} <= langs and set(yt_cfg["languages_accepted"]) >= {"en", "hi"}
    hi = next(g for g in yt_cfg["query_groups"] if g["language"] == "hi")
    assert any(any("ऀ" <= ch <= "ॿ" for ch in q) for q in hi["queries"])


def test_fetch_youtube_pipeline_with_mocked_api(repo, monkeypatch):
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-not-a-key")
    s = load_json(repo.p("config", "sources.json"))
    s["youtube"]["query_groups"] = [{"language": "en", "queries": ["q1"]}, {"language": "hi", "queries": ["q2"]}]
    write_json(repo.p("config", "sources.json"), s)
    monkeypatch.setattr(fc.yt, "api_search", lambda q, *a, **k: ["vid00000001", "vid00000002"] if q == "q1" else ["vid00000003"])
    monkeypatch.setattr(fc.yt, "api_videos", lambda ids: [
        {"video_id": i, "title": {"vid00000001": "Black holes in a minute", "vid00000002": "How ants farm fungus",
                                   "vid00000003": "गणित की रोचक पहेली"}[i], "channel": {"name": f"C{i}"}, "duration_seconds": 40,
         "published": "2026-11-20", "language": None} for i in ids])
    monkeypatch.setattr(fc.yt, "shorts_url_check", lambda vid: {"vid00000001": "short", "vid00000002": "short_form"}.get(vid, "unknown"))
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    fc.fetch_youtube(repo, D)
    out = load_json(repo.p("candidates", "youtube", f"{D.isoformat()}.json"))
    by = {c["video_id"]: c for c in out["candidates"]}
    assert by["vid00000001"]["format"] == "short" and by["vid00000001"]["url"].endswith("/shorts/vid00000001")
    assert by["vid00000002"]["format"] == "short_form" and "watch?v=" in by["vid00000002"]["url"]
    assert by["vid00000003"]["format"] == "unknown" and by["vid00000003"]["format_evidence"] == "none"
    assert by["vid00000003"]["language"] == "hi"


def test_youtube_rss_embed_and_escaping(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video(title='Fourier & "waves" <fast>')])  # feed only, no validation
    xml = build_feed(repo, "youtube_shorts")
    item = ET.fromstring(xml).find("channel/item")
    assert item.find("title").text == 'Fourier & "waves" <fast>'
    html = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text
    assert 'src="https://www.youtube.com/embed/abcDEF12345"' in html and "Watch on YouTube" in html
    assert "&lt;fast&gt;" in html and 'referrerpolicy="strict-origin-when-cross-origin"' in html


def test_creator_diversity_warning(repo):
    titles = ["Volcano lightning", "Why bees dance", "Mughal gardens", "Prime spirals", "Octopus skin"]
    vids = [video(f"abcDEF1234{i}", channel={"name": "Same"}, title=t) for i, t in enumerate(titles)]
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(*vids))
    rep = validate_repo(repo)
    assert rep.ok and any("soft limit" in w for w in rep.warnings)


# --- interests editing and website boundary ------------------------------------------------
def test_interests_cli_add_remove_move(repo, monkeypatch, capsys):
    from dsys.cli import main
    monkeypatch.setenv("DSYS_ROOT", str(repo.root))
    assert main(["interests", "add", "exploration.making_and_curiosity", "Raku glazing"]) == 0
    assert main(["interests", "add", "exploration.making_and_curiosity", "raku GLAZING"]) == 0  # duplicate ignored
    doc = load_json(repo.p("config", "interests.json"))
    assert [x for x in doc["exploration"]["making_and_curiosity"] if x.lower() == "raku glazing"] == ["Raku glazing"]
    assert main(["interests", "add", "exploration.crafts", "x"]) == 1  # list doesn't exist without --create
    assert main(["interests", "move", "exploration.making_and_curiosity", "established.crafts", "raku glazing"]) == 0
    doc = load_json(repo.p("config", "interests.json"))
    assert "Raku glazing" in doc["established"]["crafts"]
    assert "Raku glazing" not in doc["exploration"]["making_and_curiosity"]
    assert main(["interests", "add", "growth.research_skills", "writing"]) == 0
    assert main(["interests", "remove", "established.crafts", "RAKU GLAZING"]) == 0
    assert "Raku glazing" not in load_json(repo.p("config", "interests.json"))["established"]["crafts"]
    # cannot edit dimensions or invent top-level sections through this command
    assert main(["interests", "add", "dimensions.x", "y"]) == 1
    assert main(["interests", "add", "nonsense.list", "y", "--create"]) == 1
    from dsys.validate import validate_repo
    assert validate_repo(repo).ok


def test_interests_never_rendered_on_website(repo, tmp_path):
    from dsys import interests as im
    from dsys.site import build_site
    doc = im.load(repo)
    im.add(doc, "exploration.making_and_curiosity", "Zzyzx pottery wheel")
    im.add(doc, "growth.research_skills", "Qwerty calligraphy")
    im.save(repo, doc)
    out = build_site(repo, tmp_path / "s")
    blob = "".join(p.read_text(errors="ignore") for p in out.rglob("*") if p.is_file())
    assert "Zzyzx" not in blob and "Qwerty" not in blob
    assert not (out / "ideas.html").exists()


def test_media_counted_in_variety(repo):
    daily(repo, "discovery", "2026-11-24", [rec("disc-a", type="podcast", action="listen"),
                                            rec("disc-b", type="lecture", action="watch")])
    assert diversity.report(repo, D, 30)["media"] == {"podcast": 1, "video": 1}


MEDIA_PAIR = [rec("disc-pod", type="podcast", action="listen", tier="established"),
              rec("disc-vid", type="video", action="watch", tier="growth"),
              rec("disc-exp", tier="exploration", dimensions=["world"])]


def test_cross_domain_is_a_schema_type(repo):
    daily(repo, "discovery", "2026-11-24", [rec("disc-1", cross_domain={"fields": ["cinema", "psychology"],
                                                                          "connection": "How editing shapes empathy."})] + MEDIA_PAIR)
    daily(repo, "language", "2026-11-24", [language_pack()])
    assert validate_repo(repo).ok
    daily(repo, "discovery", "2026-11-24", [rec("disc-1", cross_domain={"fields": ["one"], "connection": "too few fields"})] + MEDIA_PAIR)
    assert not validate_repo(repo).ok


def test_variety_report_flags_tier_gaps(repo):
    items = [rec(f"disc-{i}", tier="established", category="machine learning", dimensions=["research"]) for i in range(4)]
    daily(repo, "discovery", "2026-11-24", items)
    joined = " ".join(diversity.report(repo, D, 30)["suggestions"])
    assert "No exploration" in joined and "No growth" in joined and "cross-domain" in joined and "Not touched" in joined


def test_variety_report_satisfied_by_tiered_mix(repo):
    items = [rec("disc-a", tier="established", dimensions=["research"]),
             rec("disc-b", tier="growth", dimensions=["knowledge"],
                 cross_domain={"fields": ["neuroscience", "AI"], "connection": "Predictive coding meets transformers."}),
             rec("disc-c", tier="exploration", dimensions=["world", "culture"]),
             rec("disc-d", tier="established", dimensions=["people", "curiosity"])]
    daily(repo, "discovery", "2026-11-24", items)
    r = diversity.report(repo, D, 30)
    assert r["suggestions"] == [] and r["tiers"] == {"established": 2, "growth": 1, "exploration": 1}


def test_context_exposes_preferences_variety_and_seed_rule(repo):
    ctx = context(repo, "weekly", D, "2026-W49")
    for k in ("preferences", "variety", "interests_hint", "seed_rule"):
        assert k in ctx
    assert "never mark it planned" in ctx["seed_rule"]
    d = context(repo, "discovery", D)
    assert "variety" in d and "preferences" in d


def test_tiers_and_culture_coverage_in_config():
    c = load_json(ROOT / "config" / "interests.json")
    for t in ("established", "growth", "exploration"):
        assert isinstance(c[t], dict)
    blob = json.dumps(c["exploration"]["culture"] + c["growth"]["humanities_and_culture"]).lower()
    for form in ("literature", "biograph", "poetry", "cinema", "animation", "music", "art history", "design",
                 "folklore", "languages", "anime", "documentar", "theatre", "travel"):
        assert form in blob, form
    assert "popularity" in c["culture_guidance"]
    assert "AI agents: planning, memory, tool use and multi-agent systems" in c["established"]["ai_research"]
    assert {"topology", "analysis", "cognitive science"} <= set(c["growth"]["for_research"])
    assert "Antarctica" in c["world"]["regions"] and "Japan" in c["world"]["regions"]


def test_no_repeated_unwanted_recommendation_in_context(repo):
    from dsys import feedback as fb
    weekly(repo, "2026-W49", items=[activity("w-x", topic="crossword puzzles")])
    fb.record(repo, "2026-W49", [], D, general={"less_of": ["crossword puzzles"]})
    fb.apply(repo, "2026-W49", D)
    assert "crossword puzzles" in context(repo, "discovery", D)["preferences"]["avoid"]


# --- YouTube ---------------------------------------------------------------------------------
def test_short_claim_needs_evidence(repo):
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(video(format_evidence="none")))
    assert any("needs format_evidence" in e for e in validate_repo(repo).errors)
    v = video(format="unknown", format_evidence="none")
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(v))  # /shorts/ URL with unknown format
    assert any("asserts the video is a Short" in e for e in validate_repo(repo).errors)
    v["url"] = yt.watch_url(v["video_id"])
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(v))
    assert validate_repo(repo).ok


def test_shorts_url_check_classification(monkeypatch):
    class R:
        def __init__(self, status): self.status = status

    class C:
        status = 200
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pass
        def getresponse(self): return R(C.status)
        def close(self): pass

    monkeypatch.setattr(yt.http.client, "HTTPSConnection", C)
    assert yt.shorts_url_check("abcDEF12345") == "short"
    C.status = 303
    assert yt.shorts_url_check("abcDEF12345") == "short_form"
    C.status = 404
    assert yt.shorts_url_check("abcDEF12345") == "unknown"
    assert yt.shorts_url_check("bad") == "unknown"


def test_filter_candidates_dedup_language_and_creators():
    mk = lambda vid, title, ch="A", lang="en", dur=50: {"video_id": vid, "title": title, "channel": {"name": ch},
                                                       "language": lang, "duration_seconds": dur}
    cands = [mk("aaaaaaaaaa1", "Why is the sky blue? #shorts"), mk("aaaaaaaaaa2", "why is the sky blue"),
             mk("aaaaaaaaaa3", "Seen before"), mk("aaaaaaaaaa4", "Too long", dur=900),
             mk("aaaaaaaaaa5", "French thing", lang="fr"), mk("aaaaaaaaaa6", "भौतिकी सरल भाषा में", lang="hi"),
             mk("bad", "invalid id")] + [mk(f"bbbbbbbbbb{i}", t, ch="B") for i, t in enumerate(
                 ["Volcanoes of Iceland", "How bees dance", "The Mughal water gardens", "Prime spirals explained",
                  "Why glass is a liquid myth", "Octopus camouflage"])]
    kept, why = yt.filter_candidates(cands, {"aaaaaaaaaa3"}, ["Old title"], per_channel=3)
    ids = [c["video_id"] for c in kept]
    assert "aaaaaaaaaa1" in ids and "aaaaaaaaaa2" not in ids and "aaaaaaaaaa6" in ids
    assert why["already_seen"] == 1 and why["too_long"] == 1 and why["language"] == 1
    assert why["invalid_id"] == 1 and why["near_duplicate_title"] == 1 and why["channel_cap"] == 3


def test_hindi_and_english_discovery_configured():
    yt_cfg = load_json(ROOT / "config" / "sources.json")["youtube"]
    langs = {g["language"] for g in yt_cfg["query_groups"]}
    assert {"en", "hi"} <= langs and set(yt_cfg["languages_accepted"]) >= {"en", "hi"}
    hi = next(g for g in yt_cfg["query_groups"] if g["language"] == "hi")
    assert any(any("ऀ" <= ch <= "ॿ" for ch in q) for q in hi["queries"])


def test_fetch_youtube_pipeline_with_mocked_api(repo, monkeypatch):
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-not-a-key")
    s = load_json(repo.p("config", "sources.json"))
    s["youtube"]["query_groups"] = [{"language": "en", "queries": ["q1"]}, {"language": "hi", "queries": ["q2"]}]
    write_json(repo.p("config", "sources.json"), s)
    monkeypatch.setattr(fc.yt, "api_search", lambda q, *a, **k: ["vid00000001", "vid00000002"] if q == "q1" else ["vid00000003"])
    monkeypatch.setattr(fc.yt, "api_videos", lambda ids: [
        {"video_id": i, "title": {"vid00000001": "Black holes in a minute", "vid00000002": "How ants farm fungus",
                                   "vid00000003": "गणित की रोचक पहेली"}[i], "channel": {"name": f"C{i}"}, "duration_seconds": 40,
         "published": "2026-11-20", "language": None} for i in ids])
    monkeypatch.setattr(fc.yt, "shorts_url_check", lambda vid: {"vid00000001": "short", "vid00000002": "short_form"}.get(vid, "unknown"))
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    fc.fetch_youtube(repo, D)
    out = load_json(repo.p("candidates", "youtube", f"{D.isoformat()}.json"))
    by = {c["video_id"]: c for c in out["candidates"]}
    assert by["vid00000001"]["format"] == "short" and by["vid00000001"]["url"].endswith("/shorts/vid00000001")
    assert by["vid00000002"]["format"] == "short_form" and "watch?v=" in by["vid00000002"]["url"]
    assert by["vid00000003"]["format"] == "unknown" and by["vid00000003"]["format_evidence"] == "none"
    assert by["vid00000003"]["language"] == "hi"


def test_youtube_rss_embed_and_escaping(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video(title='Fourier & "waves" <fast>')])  # feed only, no validation
    xml = build_feed(repo, "youtube_shorts")
    item = ET.fromstring(xml).find("channel/item")
    assert item.find("title").text == 'Fourier & "waves" <fast>'
    html = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text
    assert 'src="https://www.youtube.com/embed/abcDEF12345"' in html and "Watch on YouTube" in html
    assert "&lt;fast&gt;" in html and 'referrerpolicy="strict-origin-when-cross-origin"' in html


def test_creator_diversity_warning(repo):
    titles = ["Volcano lightning", "Why bees dance", "Mughal gardens", "Prime spirals", "Octopus skin"]
    vids = [video(f"abcDEF1234{i}", channel={"name": "Same"}, title=t) for i, t in enumerate(titles)]
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(*vids))
    rep = validate_repo(repo)
    assert rep.ok and any("soft limit" in w for w in rep.warnings)


# --- interests editing and website boundary ------------------------------------------------
def test_interests_cli_add_remove_move(repo, monkeypatch, capsys):
    from dsys.cli import main
    monkeypatch.setenv("DSYS_ROOT", str(repo.root))
    assert main(["interests", "add", "exploration.making_and_curiosity", "Raku glazing"]) == 0
    assert main(["interests", "add", "exploration.making_and_curiosity", "raku GLAZING"]) == 0  # duplicate ignored
    doc = load_json(repo.p("config", "interests.json"))
    assert [x for x in doc["exploration"]["making_and_curiosity"] if x.lower() == "raku glazing"] == ["Raku glazing"]
    assert main(["interests", "add", "exploration.crafts", "x"]) == 1  # list doesn't exist without --create
    assert main(["interests", "move", "exploration.making_and_curiosity", "established.crafts", "raku glazing"]) == 0
    doc = load_json(repo.p("config", "interests.json"))
    assert "Raku glazing" in doc["established"]["crafts"]
    assert "Raku glazing" not in doc["exploration"]["making_and_curiosity"]
    assert main(["interests", "add", "growth.research_skills", "writing"]) == 0
    assert main(["interests", "remove", "established.crafts", "RAKU GLAZING"]) == 0
    assert "Raku glazing" not in load_json(repo.p("config", "interests.json"))["established"]["crafts"]
    # cannot edit dimensions or invent top-level sections through this command
    assert main(["interests", "add", "dimensions.x", "y"]) == 1
    assert main(["interests", "add", "nonsense.list", "y", "--create"]) == 1
    from dsys.validate import validate_repo
    assert validate_repo(repo).ok


def test_interests_never_rendered_on_website(repo, tmp_path):
    from dsys import interests as im
    from dsys.site import build_site
    doc = im.load(repo)
    im.add(doc, "exploration.making_and_curiosity", "Zzyzx pottery wheel")
    im.add(doc, "growth.research_skills", "Qwerty calligraphy")
    im.save(repo, doc)
    out = build_site(repo, tmp_path / "s")
    blob = "".join(p.read_text(errors="ignore") for p in out.rglob("*") if p.is_file())
    assert "Zzyzx" not in blob and "Qwerty" not in blob
    assert not (out / "ideas.html").exists()


def test_daily_discovery_rules():
    from dsys.validate import discovery_rule_errors
    errs = " ".join(discovery_rule_errors([rec("disc-1")]))
    assert "podcast" in errs and "video" in errs and "growth" in errs and "exploration" in errs
    # a podcast that isn't established doesn't satisfy the essential-podcast rule
    errs = discovery_rule_errors([rec("p", type="podcast", tier="growth")] + MEDIA_PAIR[1:])
    assert any("established" in e for e in errs)
    assert discovery_rule_errors(MEDIA_PAIR) == []


def test_discovery_rules_enforced_by_validation(repo):
    daily(repo, "discovery", "2026-11-24", [rec("disc-1")])
    assert not validate_repo(repo).ok
    daily(repo, "discovery", "2026-11-24", [rec("disc-1")] + MEDIA_PAIR)
    assert any("language pack" in e for e in validate_repo(repo).errors)  # language is compulsory
    daily(repo, "language", "2026-11-24", [language_pack()])
    assert validate_repo(repo).ok


def test_shorts_need_every_tier(repo):
    daily(repo, "youtube_shorts", "2026-11-24", [video()])
    assert any("each tier" in e for e in validate_repo(repo).errors)
    daily(repo, "youtube_shorts", "2026-11-24", shorts_day(video()))
    assert validate_repo(repo).ok


def test_learning_items_need_steps_and_resources(repo):
    weekly(repo, items=[activity("w-1", category="paper", mode="learn")])
    errs = " ".join(validate_repo(repo).errors)
    assert "steps" in errs and "resources" in errs
    weekly(repo, items=[activity("w-1", category="new_knowledge", mode="learn", steps=["read", "summarise"],
                                 resources=[{"title": "Book", "type": "book", "chapters": "Ch. 2"}])])
    assert validate_repo(repo).ok


def test_monthly_needs_growth_item_and_syllabus(repo):
    from conftest import monthly, project
    monthly(repo, items=[project("m-1", tier="established")])
    assert any("growth item" in e for e in validate_repo(repo).errors)
    monthly(repo, items=[project("m-1", weeks=[{"week": 1, "focus": "a"}, {"week": 2, "focus": "b"}])])
    assert any("concrete tasks" in e for e in validate_repo(repo).errors)
    monthly(repo, items=[project("m-1")])
    assert validate_repo(repo).ok


def test_skip_reason_is_generic_only(repo):
    weekly(repo, "2026-W49", items=[activity("w-1")])
    write_json(repo.feedback_path("2026-W49"), {"schema": "feedback", "period": "2026-W49", "date": "2026-12-06",
               "entries": [{"item_id": "w-1", "status": "skipped", "skip_reason": "travelling to my cousin's wedding"}]})
    assert not validate_repo(repo).ok



# --- languages ---------------------------------------------------------------------------
def test_language_pack_rules(repo):
    daily(repo, "language", "2026-11-24", [language_pack()])
    assert validate_repo(repo).ok
    daily(repo, "language", "2026-11-24", [language_pack(minutes=12)])
    assert not validate_repo(repo).ok  # 5 minutes max
    daily(repo, "language", "2026-11-24", [language_pack(language="klingon")])
    assert any("not in config/languages.json" in e for e in validate_repo(repo).errors)
    daily(repo, "language", "2026-11-24", [language_pack(practice=[{"question": "only one", "answer": "x"}])])
    assert not validate_repo(repo).ok  # needs practice questions


def test_weekly_and_monthly_require_language_section(repo):
    from conftest import monthly
    doc = weekly(repo)
    assert validate_repo(repo).ok
    doc.pop("language")
    write_json(repo.weekly_path("2026-W49"), doc)
    assert any("language" in e for e in validate_repo(repo).errors)
    weekly(repo)
    m = monthly(repo)
    m.pop("language")
    write_json(repo.monthly_path("2026-12"), m)
    assert any("language" in e for e in validate_repo(repo).errors)


def test_languages_config(repo):
    from dsys.config import check
    cfg = load_json(ROOT / "config" / "languages.json")
    assert cfg["current_focus"] == "japanese" and {l["id"] for l in cfg["learning"]} == {"japanese", "telugu"}
    bad = dict(cfg, current_focus="french")
    write_json(repo.p("config", "languages.json"), bad)
    assert any("current_focus" in e for e in check(repo)[0])


def test_language_context_and_rendering(repo, tmp_path):
    from dsys.site import build_site
    daily(repo, "language", "2026-11-24", [language_pack()])
    ctx = context(repo, "language", D)
    assert ctx["languages"]["current_focus"] == "japanese" and ctx["recent_packs"][0]["theme"] == "ordering"
    assert "languages" in context(repo, "weekly", D, "2026-W49")
    weekly(repo)
    out = build_site(repo, tmp_path / "s")
    day = (out / "daily" / "2026-11-24.html").read_text()
    assert "コーヒーをください" in day and "kōhī o kudasai" in day and "<summary>Answer</summary>" in day
    wk = (out / "weekly" / "2026-W49.html").read_text()
    assert "Languages" in wk and "こんにちは" in wk
    xml = build_feed(repo, "language")
    assert "Japanese: At a café" in xml
    assert "language.xml" in (out / "index.html").read_text()


def test_learning_languages_only_as_beginner_lessons():
    yt = load_json(ROOT / "config" / "sources.json")["youtube"]
    langs = load_json(ROOT / "config" / "languages.json")["learning"]
    not_ready = {"japanese": "ja", "telugu": "te"}
    for l in langs:
        if not l.get("native_content_ok"):
            code = not_ready.get(l["id"])
            assert code not in yt["languages_accepted"]
            assert all(g["language"] != code for g in yt["query_groups"])
    learning = [g for g in yt["query_groups"] if g.get("purpose") == "language_learning"]
    qs = " ".join(q for g in learning for q in g["queries"]).lower()
    assert "japanese" in qs and "telugu" in qs and "beginner" in qs
