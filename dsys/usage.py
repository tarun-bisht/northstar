"""How long each scheduled run takes and roughly how many tokens it reads.

The account's real token meter is not visible to a run, so this measures what drives it: the text a
run reads. Every `dsys.py` output (candidates, paper stages, context), every paper batch written for
the Haiku helpers, and the runbook and prompts a run follows are counted in characters. Tokens are
estimated at about 4 characters each. Writing and thinking are not counted, so real use is higher;
the numbers are for comparing runs and days and for spotting a run that reads far too much.

Logged to state/usage/<date>.jsonl (one line per event), committed with the run's content.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

CHARS_PER_TOKEN = 4
RUNS = ("daily", "weekly", "monthly", "quarterly")


PARTS = [("papers stage1", "papers, first reading (Haiku)"), ("papers stage2", "papers, final choice"),
         ("candidates arxiv", "papers, other"), ("papers", "papers, other"), ("candidates news", "news"),
         ("candidates updates", "research updates"), ("candidates youtube", "shorts"),
         ("candidates videos", "discovery"), ("candidates podcasts", "discovery"), ("candidates hf", "discovery"),
         ("context", "context"), ("runbook", "runbook and prompts"), ("reading", "papers of the week")]


def part_of(what: str) -> str:
    for prefix, part in PARTS:
        if what.startswith(prefix):
            return part
    return "other"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _log(root: Path, day: str) -> Path:
    return root / "state" / "usage" / f"{day}.jsonl"


def _active(root: Path) -> tuple[str, str] | None:
    """(run, day) of the run in progress on this machine, if any."""
    f = root / ".cache" / "usage_run.json"
    if f.exists():
        d = json.loads(f.read_text())
        return d["run"], d["day"]
    return None


def _write(root: Path, day: str, rec: dict) -> None:
    p = _log(root, day)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def add(root: Path, what: str, chars: int) -> None:
    """Count text a run read. Does nothing outside a run, never fails the caller."""
    try:
        act = _active(root)
        if act and chars:
            _write(root, act[1], {"t": _now().isoformat(timespec="seconds"), "run": act[0], "read": what[:80],
                                  "chars": int(chars)})
    except Exception:  # noqa: BLE001 - counting must never break a run
        pass


def prompt_chars(root: Path, run: str) -> int:
    """Characters of CLAUDE.md, the shared rules and every prompt the runbook leads to."""
    seen: set[Path] = set()
    todo = [root / "prompts" / "runs" / f"{run}.md", root / "CLAUDE.md", root / "prompts" / "_shared.md",
            root / "prompts" / "runs" / "_common.md"]
    if run in ("weekly", "monthly"):
        todo.append(root / "docs" / "vision.md")
    while todo:
        p = todo.pop()
        if p in seen or not p.exists():
            continue
        seen.add(p)
        for m in re.finditer(r"prompts/(?:runs/)?[a-z_]+\.md", p.read_text(encoding="utf-8")):
            todo.append(root / m.group(0))
    return sum(p.stat().st_size for p in seen)


def start(root: Path, run: str, day: str) -> dict:
    if run not in RUNS:
        raise SystemExit(f"run must be one of {', '.join(RUNS)}")
    c = root / ".cache"
    c.mkdir(exist_ok=True)
    (c / "usage_run.json").write_text(json.dumps({"run": run, "day": day}))
    rec = {"t": _now().isoformat(timespec="seconds"), "run": run, "event": "start"}
    _write(root, day, rec)
    add(root, "runbook and prompts", prompt_chars(root, run))
    return rec


def end(root: Path) -> dict:
    act = _active(root)
    if not act:
        raise SystemExit("no run in progress (usage start was not called)")
    run, day = act
    rec = {"t": _now().isoformat(timespec="seconds"), "run": run, "event": "end"}
    _write(root, day, rec)
    (root / ".cache" / "usage_run.json").unlink()
    return summary(root, [day])[0] if summary(root, [day]) else rec


def summary(root: Path, days: list[str]) -> list[dict]:
    rows = []
    for day in days:
        p = _log(root, day)
        if not p.exists():
            continue
        runs: dict[str, dict] = {}
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            x = runs.setdefault(r["run"], {"date": day, "run": r["run"], "start": None, "end": None, "chars": 0, "top": {}})
            if r.get("event") == "start":
                x["start"] = x["start"] or r["t"]
            elif r.get("event") == "end":
                x["end"] = r["t"]
            else:
                x["chars"] += r["chars"]
                key = part_of(r["read"])
                x["top"][key] = x["top"].get(key, 0) + r["chars"]
        for x in runs.values():
            mins = None
            if x["start"] and x["end"]:
                mins = round((dt.datetime.fromisoformat(x["end"]) - dt.datetime.fromisoformat(x["start"])).total_seconds() / 60)
            rows.append({"date": day, "run": x["run"], "minutes": mins, "read_chars": x["chars"],
                         "est_tokens_read": x["chars"] // CHARS_PER_TOKEN,
                         "biggest": sorted(x["top"].items(), key=lambda kv: -kv[1])[:3]})
    return rows


def week_days(week: str) -> list[str]:
    y, w = week.split("-W")
    monday = dt.date.fromisocalendar(int(y), int(w), 1)
    return [(monday + dt.timedelta(days=i)).isoformat() for i in range(7)]


def table(rows: list[dict]) -> str:
    out = ["| Date | Run | Minutes | Read (k tokens, est.) | Biggest reads |", "|---|---|---|---|---|"]
    for r in rows:
        big = ", ".join(f"{k} {v // CHARS_PER_TOKEN // 1000}k" for k, v in r["biggest"])
        out.append(f"| {r['date']} | {r['run']} | {r['minutes'] if r['minutes'] is not None else 'running'} | "
                   f"{r['est_tokens_read'] // 1000} | {big} |")
    tot = sum(r["est_tokens_read"] for r in rows)
    out.append(f"| | **total** | {sum(r['minutes'] or 0 for r in rows)} | **{tot // 1000}** | |")
    return "\n".join(out)
