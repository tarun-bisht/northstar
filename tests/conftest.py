import copy
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "scripts"))  # after ROOT so the dsys package wins over scripts/dsys.py

from dsys.core import Repo, load_json, write_json  # noqa: E402

D = dt.date(2026, 11, 24)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never touch the network: dsys.net.get raises at once and retry pauses are skipped.
    Tests that need a response monkeypatch the fetcher they exercise."""
    from dsys import net

    def _blocked(url, **kw):
        raise OSError(f"network disabled in tests: {url}")
    monkeypatch.setattr(net, "get", _blocked)
    monkeypatch.setattr(net, "_sleep", lambda s: None)


@pytest.fixture
def repo(tmp_path) -> Repo:
    """An empty repository with real schemas and config, plus a copy of examples/."""
    for d in ("schemas", "config", "examples"):
        shutil.copytree(ROOT / d, tmp_path / d)
    (tmp_path / "state").mkdir()
    (tmp_path / "README.md").write_text("# test\n")
    return Repo(tmp_path)


def example(name: str, stream: str) -> dict:
    path = next((ROOT / "examples" / "content" / stream).rglob("*.json"))
    return copy.deepcopy(load_json(path))


def paper(aid="2611.01234", **kw):
    p = {
        "id": f"arxiv-{aid}", "arxiv_id": aid, "title": "A paper", "authors": ["A. Author"],
        "url": f"https://arxiv.org/abs/{aid}", "submitted": "2026-11-23", "categories": ["cs.LG"],
        "abstract": "We study something important and report results that are quite long enough.",
        "research_area": "unlearning", "tags": ["close to your work"],
    }
    p.update(kw)
    return p


def video(vid="abcDEF12345", **kw):
    v = {
        "id": f"yt-{vid}", "video_id": vid, "title": "A short", "channel": {"name": "Chan"},
        "url": f"https://www.youtube.com/shorts/{vid}", "embed_url": f"https://www.youtube.com/embed/{vid}",
        "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "topic": "math", "category": "mathematics",
        "dimensions": ["knowledge"], "why_it_matches": "visual intuition", "discovery_source": "youtube_data_api",
        "format": "short", "format_evidence": "shorts_url_check", "language": "en", "tier": "established",
        "verification": {"method": "youtube_data_api", "verified_at": "2026-11-24T01:00:00Z"},
    }
    v.update(kw)
    return v


def daily(repo: Repo, stream: str, date: str, items: list, **kw):
    doc = {"schema": stream, "date": date, "generated_at": "2026-11-24T01:00:00Z", "items": items, **kw}
    write_json(repo.daily_path(stream, date), doc)
    return doc


def reading(repo: Repo, week="2026-W49", n=3):
    from dsys.core import week_bounds
    s, e = week_bounds(week)
    papers = [{"id": f"rl-{week.lower()}-{i}", "title": f"Paper {i}", "url": f"https://example.org/{week}/{i}",
               "source": "arxiv", "tags": ["worth knowing"], "added": s.isoformat()} for i in range(n)]
    doc = {"schema": "reading", "week": week, "start_date": s.isoformat(), "end_date": e.isoformat(),
           "generated_at": "2026-11-28T01:00:00Z", "papers": papers}
    write_json(repo.reading_path(week), doc)
    return doc


def weekly(repo: Repo, week="2026-W49", items=None, with_reading=True, **kw):
    from dsys.core import week_bounds
    if with_reading:
        reading(repo, week)
    s, e = week_bounds(week)
    items = items if items is not None else [activity(f"w-{week.lower()}-a"), activity(f"w-{week.lower()}-b")]
    items = pad_weekly_sections(week, items, kw.get("load", "normal"))
    doc = {"schema": "weekly", "week": week, "start_date": s.isoformat(), "end_date": e.isoformat(),
           "generated_at": "2026-11-28T01:00:00Z", "load": "normal", "intro": "Optional things.", "items": items,
           "language": {"lessons": [LESSON]}, **kw}
    write_json(repo.weekly_path(week), doc)
    return doc


LESSON = {"language": "japanese", "title": "Greetings", "explanation": "How to greet people politely in Japanese.",
          "examples": [{"text": "こんにちは", "romanization": "konnichiwa", "meaning": "hello"},
                       {"text": "おはよう", "romanization": "ohayō", "meaning": "good morning"},
                       {"text": "こんばんは", "romanization": "konbanwa", "meaning": "good evening"}],
          "questions": [{"question": "Say hello", "answer": "こんにちは"}, {"question": "Say good morning", "answer": "おはよう"},
                        {"question": "Say good evening", "answer": "こんばんは"}],
          "practice": ["Greet three people today"]}
PLAN = {"language": "telugu", "goal": "Basic greetings and small talk",
        "weeks": [{"week": i, "focus": f"week {i}", "tasks": ["practise"]} for i in range(1, 5)],
        "resources": [{"title": "A Telugu course", "type": "course", "chapters": "Units 1-2"}]}


def language_pack(date="2026-11-24", **kw):
    p = {"id": f"lang-{date}", "language": "japanese", "title": "At a café", "theme": "ordering", "minutes": 5,
         "phrases": [{"text": "コーヒーをください", "romanization": "kōhī o kudasai", "meaning": "coffee, please"},
                     {"text": "いくらですか", "romanization": "ikura desu ka", "meaning": "how much is it?"},
                     {"text": "ありがとう", "romanization": "arigatō", "meaning": "thank you"}],
         "dialogue": [{"text": "いらっしゃいませ", "meaning": "welcome"}, {"text": "コーヒーをください", "meaning": "coffee, please"}],
         "practice": [{"question": "Order a coffee", "answer": "コーヒーをください"},
                      {"question": "Ask the price", "answer": "いくらですか"}],
         "tier": "growth", "dimensions": ["culture"]}
    p.update(kw)
    return p


def activity(aid, **kw):
    a = {"id": aid, "title": f"Activity {aid}", "category": "culture", "dimensions": ["knowledge"],
         "description": "Do a thing.", "why": "Because.", "time_estimate": "30-60m", "origin": "system",
         "status": "suggested", "tier": "established", "mode": "practise"}
    a.update(kw)
    return a


def pad_weekly_sections(week, items, load="normal"):
    """A weekly package must cover the required sections; add one filler per missing section."""
    from dsys.render import weekly_section
    from dsys.validate import WEEKLY_REQUIRED
    have = {weekly_section(it) for it in items}
    fill = [activity(f"w-{week.lower()}-fill-{sec.replace('_', '-')}", section=sec, title=f"Filler {sec}")
            for sec in sorted(WEEKLY_REQUIRED.get(load, WEEKLY_REQUIRED["normal"]) - have)]
    return list(items) + fill


def fill_sections(repo: Repo) -> None:
    """Pad weekly and monthly files a test wrote by hand so they meet the section rules."""
    for f in repo.iter_stream_files("weekly"):
        doc = load_json(f)
        doc["items"] = pad_weekly_sections(doc["week"], doc["items"], doc.get("load", "normal"))
        write_json(f, doc)
    from dsys.render import monthly_section
    for f in repo.iter_stream_files("monthly"):
        doc = load_json(f)
        have = {monthly_section(pj) for pj in doc["items"]}
        doc["items"] += [project(f"m-{doc['month']}-fill-{sec}", section=sec, title=f"Filler {sec}", tier="established")
                         for sec in ("research", "knowledge", "exploration") if sec not in have]
        write_json(f, doc)


def monthly(repo: Repo, month="2026-12", items=None):
    items = items if items is not None else [project(f"m-{month}-a")]
    from dsys.render import monthly_section
    have = {monthly_section(pj) for pj in items}
    items = list(items) + [project(f"m-{month}-fill-{sec}", section=sec, title=f"Filler {sec}", tier="established")
                           for sec in ("research", "knowledge", "exploration") if sec not in have]
    doc = {"schema": "monthly", "month": month, "generated_at": "2026-12-01T01:00:00Z", "load": "normal",
           "intro": "Optional depth.", "items": items, "language": {"plans": [PLAN]}}
    write_json(repo.monthly_path(month), doc)
    return doc


def project(pid, **kw):
    p = {"id": pid, "title": "Project", "kind": "ai_deep_dive", "dimensions": ["research"], "why": "w",
         "objective": "o", "weeks": [{"week": 1, "focus": "a", "tasks": ["read ch. 1"]},
                                     {"week": 2, "focus": "b", "tasks": ["do exercises"]}],
         "primary_resource": {"title": "A book", "type": "book", "chapters": "Ch. 1-2"},
         "resources": [{"title": "A lecture", "type": "lecture", "chapters": "Lectures 1-3"}],
         "deliverable": "d", "definition_of_done": "done", "time_estimate": "2 h/week", "origin": "system",
         "status": "suggested", "tier": "growth"}
    p.update(kw)
    return p


def shorts_day(*videos):
    """A Shorts day must cover every tier; pad the given videos with one per missing tier."""
    vids = list(videos)
    have = {v["tier"] for v in vids}
    fillers = {"established": "fillEST0001", "growth": "fillGRW0001", "exploration": "fillEXP0001"}
    for t, vid in fillers.items():
        if t not in have:
            vids.append(video(vid, tier=t, title=f"Filler {t} about {vid}", channel={"name": f"Fill {t}"}))
    return vids
