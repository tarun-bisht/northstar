"""Shared helpers: repository layout, JSON IO, dates."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

DAILY_STREAMS = ["arxiv", "research_updates", "world", "discovery", "youtube_shorts", "language"]
PERIODIC_STREAMS = ["weekly", "monthly", "reading"]
ALL_STREAMS = DAILY_STREAMS + PERIODIC_STREAMS

STREAM_META = {
    "arxiv": {"title": "arXiv Paper Radar", "feed": "arxiv.xml",
              "description": "Weekday paper triage: only genuinely relevant new arXiv papers, with original abstracts."},
    "research_updates": {"title": "Research Updates", "feed": "research-updates.xml",
                         "description": "Filtered research developments beyond arXiv: lab posts, methods, results, debates."},
    "world": {"title": "World Radar", "feed": "world.xml",
              "description": "What happened, why it matters, what to watch, at home and around the world."},
    "discovery": {"title": "Daily Discovery", "feed": "discovery.xml",
                  "description": "A few worthwhile things to read, watch, try or think about."},
    "youtube_shorts": {"title": "YouTube Shorts Radar", "feed": "youtube-shorts.xml",
                       "description": "Short videos across all your dimensions. Inline playback depends on your RSS reader."},
    "language": {"title": "Language", "feed": "language.xml",
                 "description": "A 5-minute daily practice in your current focus language."},
    "reading": {"title": "Reading list", "feed": "reading.xml",
                "description": "Papers worth definitely reading this week."},
    "weekly": {"title": "Weekly", "feed": "weekly.xml",
               "description": "Small optional things to learn, practise or experience this week."},
    "monthly": {"title": "Monthly", "feed": "monthly.xml",
                "description": "Optional one-month deep dives, projects and experiences."},
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True)
class Repo:
    root: Path = DEFAULT_ROOT

    def p(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    # --- layout -----------------------------------------------------------
    def content_dir(self, stream: str, examples: bool = False) -> Path:
        base = self.p("examples", "content") if examples else self.p("content")
        return base / stream

    def daily_path(self, stream: str, date: str) -> Path:
        y, m, _ = date.split("-")
        return self.p("content", stream, y, m, f"{date}.json")

    def weekly_path(self, week: str) -> Path:
        return self.p("content", "weekly", week[:4], f"{week}.json")

    def reading_path(self, week: str) -> Path:
        return self.p("content", "reading", week[:4], f"{week}.json")

    def monthly_path(self, month: str) -> Path:
        return self.p("content", "monthly", month[:4], f"{month}.json")

    def feedback_path(self, period: str) -> Path:
        return self.p("feedback", period[:4], f"{period}.json")

    def iter_stream_files(self, stream: str, examples: bool = False) -> Iterator[Path]:
        d = self.content_dir(stream, examples)
        if d.exists():
            yield from sorted(d.rglob("*.json"))

    def iter_feedback_files(self, examples: bool = False) -> Iterator[Path]:
        d = self.p("examples", "feedback") if examples else self.p("feedback")
        if d.exists():
            yield from sorted(d.rglob("*.json"))

    def config(self, name: str) -> dict:
        return load_json(self.p("config", f"{name}.json"))

    def state_path(self, name: str) -> Path:
        return self.p("state", f"{name}.json")


def repo_from_env() -> Repo:
    root = os.environ.get("DSYS_ROOT")
    return Repo(Path(root).resolve()) if root else Repo()


# --- JSON -------------------------------------------------------------------
def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dump_json(data), encoding="utf-8")
    tmp.replace(path)


# --- dates ------------------------------------------------------------------
def parse_date(s: str) -> dt.date:
    if not isinstance(s, str) or not DATE_RE.match(s):
        raise ValueError(f"not a YYYY-MM-DD date: {s!r}")
    return dt.date.fromisoformat(s)


def today(tz_offset: str = "+05:30") -> dt.date:
    sign = 1 if tz_offset[0] == "+" else -1
    h, m = int(tz_offset[1:3]), int(tz_offset[4:6])
    tz = dt.timezone(sign * dt.timedelta(hours=h, minutes=m))
    return dt.datetime.now(tz).date()


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_bounds(week: str) -> tuple[dt.date, dt.date]:
    m = WEEK_RE.match(week)
    if not m:
        raise ValueError(f"not an ISO week (YYYY-Www): {week!r}")
    start = dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    return start, start + dt.timedelta(days=6)


def next_week(week: str, n: int = 1) -> str:
    start, _ = week_bounds(week)
    return iso_week(start + dt.timedelta(weeks=n))


def month_of(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def month_bounds(month: str) -> tuple[dt.date, dt.date]:
    m = MONTH_RE.match(month)
    if not m:
        raise ValueError(f"not a month (YYYY-MM): {month!r}")
    y, mo = int(m.group(1)), int(m.group(2))
    if not 1 <= mo <= 12:
        raise ValueError(f"invalid month: {month!r}")
    start = dt.date(y, mo, 1)
    end = dt.date(y + (mo == 12), (mo % 12) + 1, 1) - dt.timedelta(days=1)
    return start, end


def next_month(month: str, n: int = 1) -> str:
    start, _ = month_bounds(month)
    idx = start.year * 12 + (start.month - 1) + n
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def period_kind(period: str) -> str:
    if WEEK_RE.match(period):
        return "weekly"
    if MONTH_RE.match(period):
        return "monthly"
    raise ValueError(f"not a week or month: {period!r}")


def period_bounds(period: str) -> tuple[dt.date, dt.date]:
    return week_bounds(period) if period_kind(period) == "weekly" else month_bounds(period)


def slugify(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "item"
