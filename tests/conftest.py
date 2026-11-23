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
        "research_area": "unlearning", "relevance": "must_read", "selection_reason": "Directly on unlearning.",
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


def weekly(repo: Repo, week="2026-W49", items=None, **kw):
    from dsys.core import week_bounds
    s, e = week_bounds(week)
    items = items if items is not None else [activity(f"w-{week.lower()}-a"), activity(f"w-{week.lower()}-b")]
    doc = {"schema": "weekly", "week": week, "start_date": s.isoformat(), "end_date": e.isoformat(),
           "generated_at": "2026-11-28T01:00:00Z", "load": "normal", "intro": "Optional things.", "items": items, **kw}
    write_json(repo.weekly_path(week), doc)
    return doc


def activity(aid, **kw):
    a = {"id": aid, "title": f"Activity {aid}", "category": "culture", "dimensions": ["knowledge"],
         "description": "Do a thing.", "why": "Because.", "time_estimate": "30-60m", "origin": "system",
         "status": "suggested", "tier": "established", "mode": "practise"}
    a.update(kw)
    return a


def monthly(repo: Repo, month="2026-12", items=None):
    items = items if items is not None else [project(f"m-{month}-a")]
    doc = {"schema": "monthly", "month": month, "generated_at": "2026-12-01T01:00:00Z", "load": "normal",
           "intro": "Optional depth.", "items": items}
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
