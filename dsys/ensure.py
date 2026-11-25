"""Make sure today's candidate files are complete before a run uses them. Never fall back to search.

GitHub's scheduled workflows can start hours late or not at all, so a run never trusts the
schedule. This command:

1. checks today's files for the kinds the run needs (arXiv only on weekdays);
2. if a fetch workflow is already queued or running (a late scheduled run), waits for it to finish;
3. otherwise starts the fetch workflow itself (workflow_dispatch through the gh CLI) for the
   missing kinds, or in retry mode for sources that failed, and waits for that run to finish;
4. pulls the repo and checks again, up to `attempts` rounds.

Missing files are never accepted: if they still can't be fetched when the time runs out, it
exits 1 and the run reports the failure instead of searching. Sources that keep failing
inside a file that exists (one feed out of thirty, say) are retried every round and then
listed, since the rest of the file is still real data.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import time
from pathlib import Path

REPO_SLUG = "tarun-bisht/northstar"
WORKFLOW = "fetch-candidates.yml"
WEEKDAY_ONLY = {"arxiv"}  # the workflow skips arXiv at weekends: there are no new papers


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(_root()), capture_output=True, text=True, timeout=120)


def needed(day: dt.date, kinds: list[str]) -> list[str]:
    return [k for k in kinds if not (k in WEEKDAY_ONLY and day.weekday() >= 5)]


def check(repo, day: dt.date, kinds: list[str]) -> tuple[list[str], dict[str, list]]:
    """(missing kinds, {kind: failed sources}) for today's files."""
    missing, failed = [], {}
    for k in kinds:
        f = repo.p("candidates", k, f"{day.isoformat()}.json")
        if not f.exists():
            missing.append(k)
            continue
        doc = json.loads(f.read_text())
        bad = doc.get("failed_sources") or ([] if doc.get("candidates") or doc.get("models") else doc.get("errors") or [])
        if bad:
            failed[k] = bad
    return missing, failed


def _runs(run, status: str | None = None) -> list[dict]:
    q = f"repos/{REPO_SLUG}/actions/workflows/{WORKFLOW}/runs?per_page=20" + (f"&status={status}" if status else "")
    r = run(["gh", "api", q])
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    return json.loads(r.stdout or "{}").get("workflow_runs", [])


def _active(run) -> list[dict]:
    return _runs(run, "in_progress") + _runs(run, "queued")


def _wait_done(run, run_ids: set, sleep, pause: int, deadline: float, clock) -> None:
    while run_ids and clock() < deadline:
        sleep(pause)
        done = {r["id"] for r in _runs(run) if r["id"] in run_ids and r.get("status") == "completed"}
        run_ids -= done


def ensure(repo, day: dt.date, kinds: list[str], timeout: int = 5400, attempts: int = 4, pause: int = 30,
           run=None, sleep=time.sleep, clock=time.monotonic) -> int:
    run = run or _run
    kinds = needed(day, kinds)
    deadline = clock() + timeout
    log = []
    for attempt in range(1, attempts + 1):
        missing, failed = check(repo, day, kinds)
        if not missing and not failed:
            print(json.dumps({"ok": True, "missing": [], "failed_sources": {}, "log": log}))
            return 0
        if clock() >= deadline:
            break
        try:
            active = _active(run)
            if active:  # a late scheduled run or an earlier dispatch is already fetching: wait for it
                log.append(f"round {attempt}: waiting for running fetch {[r['id'] for r in active]}")
                _wait_done(run, {r["id"] for r in active}, sleep, pause, deadline, clock)
            else:
                retry = not missing  # files exist, only some sources failed: refetch just those
                todo = missing or list(failed)
                started = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)
                r = run(["gh", "api", "-X", "POST", f"repos/{REPO_SLUG}/actions/workflows/{WORKFLOW}/dispatches",
                         "-f", "ref=main", "-f", f"inputs[kinds]={','.join(todo)}",
                         "-f", f"inputs[retry_only]={'true' if retry else 'false'}"])
                if r.returncode != 0:
                    raise RuntimeError((r.stderr or r.stdout)[-300:])
                log.append(f"round {attempt}: started fetch for {','.join(todo)}{' (retry failed sources)' if retry else ''}")
                mine: set = set()
                while not mine and clock() < deadline:  # the new run takes a few seconds to appear
                    sleep(min(pause, 10))
                    mine = {x["id"] for x in _runs(run) if x.get("event") == "workflow_dispatch"
                            and x.get("created_at", "") >= started.strftime("%Y-%m-%dT%H:%M:%SZ")}
                _wait_done(run, mine, sleep, pause, deadline, clock)
        except RuntimeError as e:
            log.append(f"round {attempt}: GitHub API error: {e}")
            sleep(pause)
        run(["git", "pull", "-q", "--rebase", "origin", "main"])
    missing, failed = check(repo, day, kinds)
    ok = not missing
    print(json.dumps({"ok": ok, "missing": missing, "failed_sources": failed, "log": log,
                      "next": ("use the fetched files; list failed_sources in the final message" if ok else
                               "do not search instead: skip the streams that need the missing files, "
                               "post the failure to Slack (prompts/runs/_git.md) and say so in the final message")}))
    return 0 if ok else 1
