"""Start here: at most one paper, one news story and one exploration pick a day, each with one line
on why. A short way into a full day, so a busy reader can stop there and still get the best.
Nothing is tracked: it is an editorial pick, shown on the day's overview, the home page, the top of
each part's feed entry and the Slack message."""
from __future__ import annotations

import datetime as dt

from .core import Repo, load_json, write_json

STREAMS = ("arxiv", "world", "discovery")
LABELS = {"arxiv": "Paper", "world": "Story", "discovery": "Explore"}
PART = {"arxiv": "research", "world": "news", "discovery": "exploration"}


def link(stream: str, it: dict) -> str | None:
    if stream == "world":
        return (it.get("sources") or [{}])[0].get("url")
    return it.get("url")


def items(streams: dict) -> list[tuple[str, dict]]:
    """(stream, item) for the day's picks, in part order."""
    return [(s, it) for s in STREAMS for it in (streams.get(s) or {}).get("items", []) if it.get("start_here")]


def errors(stream: str, its: list) -> list[str]:
    picked = [it.get("id") for it in its if it.get("start_here")]
    if picked and stream not in STREAMS:
        return [f"start_here is only for {', '.join(STREAMS)}"]
    if len(picked) > 1:
        return [f"at most one start_here item per stream a day; found {', '.join(picked)}"]
    return []


def set_picks(repo: Repo, day: dt.date, picks: dict[str, str]) -> dict:
    """Mark these item ids (id -> one line why) as today's picks and clear any earlier ones."""
    found: dict[str, str] = {}
    docs = {}
    for s in STREAMS:
        path = repo.daily_path(s, day.isoformat())
        if not path.exists():
            continue
        doc = load_json(path)
        for it in doc["items"]:
            it.pop("start_here", None)
            if it["id"] in picks:
                if s in found.values():
                    raise SystemExit(f"two picks in {s}: choose one")
                why = " ".join(picks[it["id"]].split())
                if not 3 <= len(why) <= 160:
                    raise SystemExit(f"{it['id']}: the reason must be 3 to 160 characters")
                it["start_here"] = why
                found[it["id"]] = s
        docs[path] = doc
    unknown = sorted(set(picks) - set(found))
    if unknown:
        raise SystemExit(f"not in today's papers, news or exploration: {', '.join(unknown)}")
    for path, doc in docs.items():
        write_json(path, doc)
    return {"date": day.isoformat(), "picks": found}
