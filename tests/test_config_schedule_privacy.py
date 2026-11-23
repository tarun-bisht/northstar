import datetime as dt
import json
import re
import subprocess

from conftest import ROOT, daily, paper
from dsys.config import arxiv_categories, check
from dsys.core import Repo, load_json, write_json
from dsys.schedule import load_for_range
from dsys.validate import validate_repo

D = dt.date


def cfg(repo, name):
    return load_json(repo.p("config", f"{name}.json"))


def put(repo, name, doc):
    write_json(repo.p("config", f"{name}.json"), doc)


# --- configuration ------------------------------------------------------------------
def test_real_config_is_valid():
    errors, _ = check(Repo(ROOT))
    assert errors == []


def test_missing_optional_config_uses_defaults(repo):
    repo.p("config", "schedules.json").unlink()
    errors, warnings = check(repo)
    assert errors == [] and any("schedules.json missing" in w for w in warnings)
    from dsys.schedule import load_for_period
    assert load_for_period(repo, "2026-W49")["load"] == "normal"


def test_missing_required_config_is_an_error(repo):
    repo.p("config", "sources.json").unlink()
    errors, _ = check(repo)
    assert any("sources.json missing" in e for e in errors)


def test_conflicting_arxiv_categories_rejected(repo):
    i = cfg(repo, "interests")
    i["established"]["arxiv_categories"] = ["cs.LG"]
    put(repo, "interests", i)
    errors, _ = check(repo)
    assert any("belong only in config/sources.json" in e for e in errors)


def test_arxiv_categories_single_source_and_coverage():
    s = load_json(ROOT / "config" / "sources.json")
    cats = arxiv_categories(s)
    for needed in ("cs.LG", "cs.AI", "cs.CL", "cs.CV", "cs.CR", "cs.MA", "cs.DC", "stat.ML", "math.OC"):
        assert needed in cats
    assert len(cats) == len(set(cats))
    assert "arxiv_categories" not in json.dumps(load_json(ROOT / "config" / "interests.json"))
    # the fetcher reads the same helper (no second list)
    src = (ROOT / "scripts" / "fetch_candidates.py").read_text()
    assert "arxiv_categories(sources)" in src


def test_changing_categories_changes_fetch(repo, monkeypatch):
    import importlib.util
    s = cfg(repo, "sources")
    s["arxiv"]["categories"] = [{"id": "q-bio.NC", "covers": "neuroscience"}]
    put(repo, "sources", s)
    calls = []
    spec = importlib.util.spec_from_file_location("fc", ROOT / "scripts" / "fetch_candidates.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    monkeypatch.setattr(fc.ax, "fetch_recent", lambda cat, n: calls.append((cat, n)) or [])
    fc.fetch_arxiv(repo, D(2026, 11, 24))
    assert calls == [("q-bio.NC", 400)]


def test_invalid_schedule_and_dimension_ids(repo):
    sc = cfg(repo, "schedules")
    sc["recurring"].append({"label": "x", "days": ["funday"], "hours_per_day": 1})
    sc["periods"].append({"label": "bad", "start": "2026-12-10", "end": "2026-12-01", "load": "light"})
    put(repo, "schedules", sc)
    i = cfg(repo, "interests")
    i["dimensions"]["Bad Id"] = {"name": "x"}
    put(repo, "interests", i)
    errors, _ = check(repo)
    assert any("invalid days" in e for e in errors)
    assert any("ends before it starts" in e for e in errors)
    assert any("Bad Id" in e for e in errors)


def test_fork_with_modified_interests(repo, tmp_path):
    i = cfg(repo, "interests")
    i["dimensions"] = {"craft": {"name": "Craft"}, "health": {"name": "Movement", "short": "Move"}}
    put(repo, "interests", i)
    assert check(repo)[0] == []
    from dsys.site import build_site
    out = build_site(repo, tmp_path / "s")
    html = (out / "index.html").read_text()
    assert "Move" in html and "Craft" in html and "Researcher" not in html


def test_canonical_url_consistency(repo, tmp_path):
    base = cfg(repo, "site")["base_url"]
    assert base == "https://tarunbisht.com/northstar"
    daily(repo, "arxiv", "2026-11-24", [paper()])
    from dsys.site import build_site
    out = build_site(repo, tmp_path / "s")
    for f in out.rglob("*.html"):
        t = f.read_text()
        assert "github.io" not in t, f
        for m in re.findall(r'rel="canonical" href="([^"]+)"', t):
            assert m.startswith(base + "/")
    for f in (out / "feeds").glob("*.xml"):
        t = f.read_text()
        assert f'href="{base}/feeds/{f.name}" rel="self"' in t
        assert "github.io" not in t
    home = (out / "index.html").read_text()
    for feed in ("arxiv", "research-updates", "world", "discovery", "youtube-shorts", "weekly", "monthly"):
        assert f"{base}/feeds/{feed}.xml" in home  # copyable on the home page
    readme = (ROOT / "README.md").read_text()
    assert "github.io" not in readme and "tarunbisht.com/northstar" in readme


def test_no_dimension_count_in_public_text():
    for p in [ROOT / "README.md", ROOT / "prompts" / "_shared.md", ROOT / "config" / "interests.json"]:
        assert not re.search(r"\bsix\b|\b6 (dimensions|pillars)\b|pillar", p.read_text(), re.I), p


# --- scheduling -----------------------------------------------------------------------
BASE = {"default_load": "normal",
        "recurring": [{"label": "weekdays", "days": ["mon", "tue", "wed", "thu", "fri"], "hours_per_day": 0.5},
                      {"label": "weekends", "days": ["sat", "sun"], "hours_per_day": 3}]}


def test_recurring_availability_reported():
    r = load_for_range(BASE, D(2026, 11, 30), D(2026, 12, 6))
    assert r["load"] == "normal" and r["usual_hours"] == 8.5 and r["available_hours"] == 8.5


def test_dated_busy_period_makes_lighter():
    c = {**BASE, "periods": [{"label": "busy", "start": "2026-11-30", "end": "2026-12-06", "load": "light"}]}
    r = load_for_range(c, D(2026, 11, 30), D(2026, 12, 6))
    assert r["load"] == "light" and r["available_hours"] < r["usual_hours"]


def test_weekend_only_busy_matters_more_with_recurring():
    # busy on the weekend removes most of the free time even though it's only 2 of 7 days
    c = {**BASE, "periods": [{"label": "trip", "start": "2026-12-05", "end": "2026-12-06", "load": "light"}]}
    assert load_for_range(c, D(2026, 11, 30), D(2026, 12, 6))["load"] == "light"


def test_overlapping_periods_busy_wins():
    c = {**BASE, "periods": [{"label": "holiday", "start": "2026-12-01", "end": "2026-12-10", "load": "free"},
                             {"label": "deadline", "start": "2026-11-28", "end": "2026-12-06", "load": "light"}]}
    r = load_for_range(c, D(2026, 11, 30), D(2026, 12, 6))
    assert r["load"] == "light" and {"holiday", "deadline"} <= set(r["labels"])


def test_free_period_and_default_load():
    c = {**BASE, "periods": [{"label": "holiday", "start": "2026-12-21", "end": "2026-12-27", "load": "free"}]}
    assert load_for_range(c, D(2026, 12, 21), D(2026, 12, 27))["load"] == "free"
    assert load_for_range({**BASE, "default_load": "light"}, D(2026, 12, 14), D(2026, 12, 20))["load"] == "light"
    assert load_for_range({}, D(2026, 12, 14), D(2026, 12, 20))["load"] == "normal"


def test_planner_context_carries_schedule(repo):
    from dsys.history import context
    sc = cfg(repo, "schedules")
    sc["periods"] = [{"label": "busy", "start": "2026-11-30", "end": "2026-12-06", "load": "light"}]
    put(repo, "schedules", sc)
    ctx = context(repo, "weekly", D(2026, 11, 28), "2026-W49")
    assert ctx["schedule"]["load"] == "light" and "available_hours" in ctx["schedule"]


# --- privacy ----------------------------------------------------------------------------
def _fake(prefix, n):  # build secret-shaped strings at runtime so this file never contains one
    return prefix + "A1b2C3d4E5" * (n // 10 + 1)


def test_credentials_detected(repo):
    write_json(repo.p("state", "leak.json"), {"note": _fake("ghp_", 40)[:40]})
    rep = validate_repo(repo)
    assert any("GitHub token" in e for e in rep.errors)


def test_google_key_and_private_key_detected(repo):
    (repo.p("config", "notes.md")).write_text("key " + "AIza" + "B" * 35 + "\n-----BEGIN " + "PRIVATE KEY-----\n")
    errs = validate_repo(repo).errors
    assert any("Google API key" in e for e in errs) and any("private key block" in e for e in errs)


def test_contact_details_in_personal_files(repo):
    write_json(repo.p("state", "x.json"), {"who": "someone@example.org"})
    assert any("email address" in e for e in validate_repo(repo).errors)


def test_raw_feedback_rejected(repo):
    from conftest import weekly
    weekly(repo)
    write_json(repo.feedback_path("2026-W49"), {"schema": "feedback", "period": "2026-W49", "date": "2026-12-06",
                                                 "raw": "my private diary text", "entries": []})
    errs = validate_repo(repo).errors
    assert any("raw" in e for e in errs)


def test_feedback_record_never_stores_raw(repo):
    import datetime
    from conftest import weekly
    from dsys import feedback as fb
    weekly(repo)
    doc = fb.record(repo, "2026-W49", [], datetime.date(2026, 12, 6), general={"more_of": ["maps"]})
    assert "raw" not in doc


def test_private_dir_is_gitignored_and_tracked_files_flagged(tmp_path):
    gi = (ROOT / ".gitignore").read_text()
    assert "private/*" in gi and "!private/README.md" in gi
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "diary.md").write_text("personal")
    subprocess.run(["git", "add", "-f", "private/diary.md"], cwd=tmp_path, check=True)
    from dsys.privacy import tracked_private_files
    assert tracked_private_files(tmp_path)


def test_repo_has_no_reflections_dir_and_inbox_warns():
    assert not (ROOT / "reflections").exists()
    for f in ("ideas.md", "feedback.md"):
        assert "PUBLIC" in (ROOT / "inbox" / f).read_text()
