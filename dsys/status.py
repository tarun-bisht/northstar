"""What a run produced today and what went wrong, for the Slack digest; and the topic polls.

state/polls.json holds the polls posted in Slack (prompts/runs/topic_poll.md) and the topics
the user chose (prompts/runs/poll_collect.md). Topics are general, never private details.
"""

from __future__ import annotations

import datetime as dt

from .core import Repo, iso_week, load_json, month_of, next_week, write_json

DAILY_EXPECTED = {  # stream -> which days it should exist
    "arxiv": "weekdays", "research_updates": "every", "world": "every", "discovery": "every",
    "language": "every", "youtube_shorts": "every",
}


def status(repo: Repo, day: dt.date) -> dict:
    from .validate import validate_repo
    out = {"date": day.isoformat(), "present": [], "missing": [], "failed_sources": {}, "validation_errors": []}
    for stream, when in DAILY_EXPECTED.items():
        if when == "weekdays" and day.weekday() >= 5:
            continue
        (out["present"] if repo.daily_path(stream, day.isoformat()).exists() else out["missing"]).append(stream)
    cdir = repo.p("candidates")
    if cdir.exists():
        for f in sorted(cdir.glob(f"*/{day.isoformat()}.json")):
            doc = load_json(f)
            bad = doc.get("failed_sources") or doc.get("errors") or []
            if bad:
                out["failed_sources"][f.parent.name] = bad[:10] + ([f"... and {len(bad) - 10} more"] if len(bad) > 10 else [])
    if day.weekday() == 5:
        wk = next_week(iso_week(day))
        out["next_week"] = {"week": wk, "package": repo.weekly_path(wk).exists(), "papers": repo.reading_path(wk).exists()}
    if day.day == 1:
        m = month_of(day)
        out["this_month"] = {"month": m, "package": repo.monthly_path(m).exists()}
    out["validation_errors"] = validate_repo(repo).errors[:20]
    out["ok"] = not (out["missing"] or out["validation_errors"]
                     or (day.weekday() == 5 and not out["next_week"]["package"])
                     or (day.day == 1 and not out["this_month"]["package"]))
    return out


def _load(repo: Repo) -> dict:
    p = repo.state_path("polls")
    return load_json(p) if p.exists() else {"polls": []}


def open_poll(repo: Repo, kind: str, period: str, ts: str, options: list[dict]) -> dict:
    doc = _load(repo)
    doc["polls"] = [p for p in doc["polls"] if not (p["kind"] == kind and p["period"] == period)]
    poll = {"kind": kind, "period": period, "ts": ts, "options": options, "status": "open", "choices": []}
    doc["polls"].append(poll)
    doc["polls"] = doc["polls"][-24:]  # keep about six months
    write_json(repo.state_path("polls"), doc)
    return poll


def close_poll(repo: Repo, kind: str, period: str, choices: list[str]) -> dict:
    doc = _load(repo)
    for p in doc["polls"]:
        if p["kind"] == kind and p["period"] == period:
            p["status"], p["choices"] = "closed", [str(c) for c in choices]
            write_json(repo.state_path("polls"), doc)
            return p
    raise SystemExit(f"no {kind} poll for {period}")


def list_polls(repo: Repo, only_open: bool = False) -> list[dict]:
    return [p for p in _load(repo)["polls"] if not only_open or p["status"] == "open"]


def choices_for(repo: Repo, kind: str, period: str) -> list[str]:
    """The user's poll picks for a weekly or monthly period (empty if none). Read by context."""
    for p in _load(repo)["polls"]:
        if p["kind"] == kind and p["period"] == period and p["status"] == "closed":
            return p["choices"]
    return []
