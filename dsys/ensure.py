"""Make sure today's candidate files are complete before a run uses them. Never fall back to search.

GitHub's scheduled workflows can start hours late or not at all, so a run never trusts the
schedule. This command:

1. checks today's files for the kinds the run needs;
2. if a fetch workflow is already queued or running (a late scheduled run), waits for it to finish;
3. otherwise starts the fetch workflow itself (workflow_dispatch through the gh CLI) for the
   missing kinds, or in retry mode for sources that failed, and waits for that run to finish;
4. pulls the repo and checks again, up to `attempts` rounds.

One call waits about 9 minutes at most (a run's shell commands time out at 10), checking every
60 seconds. Waiting costs nothing: the check is a free GitHub API call and no model works while
the command sleeps. If files are still missing, the run calls it again, up to 10 times.

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

REPO_SLUG = "tarun-bisht/northstar"  # default; forks use their own origin (repo_slug)
WORKFLOW = "fetch-candidates.yml"
WEEKDAY_ONLY: set = set()  # papers are fetched every day (arXiv plus other sources)


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(_root()), capture_output=True, text=True, timeout=120)


def repo_slug(run=None) -> str:
    """owner/repo of this clone's origin, so a fork dispatches its own workflow."""
    import re
    r = (run or _run)(["git", "remote", "get-url", "origin"])
    m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", (r.stdout or "").strip())
    return m.group(1) if r.returncode == 0 and m else REPO_SLUG


def pull(run) -> str | None:
    """Pull main, keeping the run's uncommitted work (--autostash). Returns an error or None."""
    r = run(["git", "pull", "-q", "--rebase", "--autostash", "origin", "main"])
    return None if r.returncode == 0 else (r.stderr or r.stdout or "git pull failed")[-300:]


def _dispatch(run, inputs: dict, sleep, pause: int, deadline: float, clock) -> set:
    """Start the fetch workflow and return the id of the run it created, waiting the few
    seconds GitHub takes to show it. Raises RuntimeError if GitHub refuses."""
    started = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmd = ["gh", "api", "-X", "POST", f"repos/{repo_slug(run)}/actions/workflows/{WORKFLOW}/dispatches", "-f", "ref=main"]
    for k, v in inputs.items():
        cmd += ["-f", f"inputs[{k}]={v}"]
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    mine: set = set()
    while not mine and clock() < deadline:
        sleep(min(pause, 10))
        mine = {x["id"] for x in _runs(run) if x.get("event") == "workflow_dispatch"
                and x.get("created_at", "") >= started}
    return mine


def _retried_marker(repo, day: dt.date) -> Path:
    return repo.p(".cache", f"retried-{day.isoformat()}")  # gitignored, local to this run


def _all_retried(repo, day: dt.date, failed: dict) -> bool:
    """True when every kind with failed sources already had its retry today (the 07:53 run)."""
    for k in failed:
        f = repo.p("candidates", k, f"{day.isoformat()}.json")
        if not (f.exists() and json.loads(f.read_text()).get("retried_at")):
            return False
    return True


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
    q = f"repos/{repo_slug(run)}/actions/workflows/{WORKFLOW}/runs?per_page=20" + (f"&status={status}" if status else "")
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


def ensure(repo, day: dt.date, kinds: list[str], timeout: int = 540, attempts: int = 4, pause: int = 60,
           run=None, sleep=time.sleep, clock=time.monotonic) -> int:
    run = run or _run
    kinds = needed(day, kinds)
    deadline = clock() + timeout
    log = []
    for attempt in range(1, attempts + 1):
        missing, failed = check(repo, day, kinds)
        if not missing and (not failed or _retried_marker(repo, day).exists() or _all_retried(repo, day, failed)):
            # failed sources get one retry per run; after that the fetched data is used as it is
            print(json.dumps({"ok": True, "missing": [], "failed_sources": failed, "log": log,
                              "next": "use the fetched files; list failed_sources in the final message"}))
            return 0
        if clock() >= deadline:
            break
        try:
            active = _active(run)
            if active:  # a late scheduled run or an earlier dispatch is already fetching: wait for it
                log.append(f"round {attempt}: waiting for running fetch {[r['id'] for r in active]}")
                _wait_done(run, {r["id"] for r in active}, sleep, pause, deadline, clock)
            else:
                retry = not missing  # files exist, only some sources failed: refetch just those, once
                todo = missing or list(failed)
                if retry:
                    _retried_marker(repo, day).parent.mkdir(parents=True, exist_ok=True)
                    _retried_marker(repo, day).touch()
                mine = _dispatch(run, {"kinds": ",".join(todo), "retry_only": "true" if retry else "false"},
                                 sleep, pause, deadline, clock)
                log.append(f"round {attempt}: started fetch for {','.join(todo)}{' (retry failed sources)' if retry else ''}")
                _wait_done(run, mine, sleep, pause, deadline, clock)
        except RuntimeError as e:
            log.append(f"round {attempt}: GitHub API error: {e}")
            sleep(pause)
        err = pull(run)
        if err:
            log.append(f"round {attempt}: git pull failed: {err}")
    missing, failed = check(repo, day, kinds)
    ok = not missing
    print(json.dumps({"ok": ok, "missing": missing, "failed_sources": failed, "log": log,
                      "next": ("use the fetched files; list failed_sources in the final message" if ok else
                               "run the same command again (each call waits about 9 minutes; up to 10 calls). "
                               "Never search instead. After 10 calls, skip the streams that need the missing files "
                               "and name them in the final message. Don't post about it: the daily Slack message lists missing parts")}))
    return 0 if ok else 1


def add_papers(repo, day: dt.date, ids: list[str], tag: str, timeout: int = 540, pause: int = 60, run=None,
               sleep=time.sleep, clock=time.monotonic) -> int:
    """Start the fetch workflow in addpapers mode (alphaXiv feed papers) and wait for it to finish."""
    run = run or _run
    deadline = clock() + timeout
    try:
        _wait_done(run, {x["id"] for x in _active(run)}, sleep, pause, deadline, clock)  # one fetch at a time
        mine = _dispatch(run, {"kinds": "addpapers", "ids": ",".join(ids), "tag": tag}, sleep, pause, deadline, clock)
    except RuntimeError as e:
        print(json.dumps({"ok": False, "error": str(e), "next": "go on without them"}))
        return 1
    _wait_done(run, mine, sleep, pause, deadline, clock)
    err = pull(run)
    print(json.dumps({"ok": not err, "added": len(ids), "tag": tag, **({"error": err} if err else {})}))
    return 0 if not err else 1


def enrich(repo, day: dt.date, ids: list[str], timeout: int = 540, pause: int = 60, run=None, sleep=time.sleep,
           clock=time.monotonic) -> int:
    """Start the fetch workflow in enrich mode for these papers and wait for it to finish (page 1:
    affiliations and emails). Call again if it says so; papers it could not read are skipped."""
    run = run or _run
    path = repo.p("candidates", "affil", f"{day.isoformat()}.json")
    have = set(json.loads(path.read_text()).get("papers", {})) if path.exists() else set()
    todo = [i for i in ids if i not in have]
    if not todo:
        print(json.dumps({"ok": True, "enriched": len(ids), "missing": 0}))
        return 0
    deadline = clock() + timeout
    try:
        active = {x["id"] for x in _active(run)}
        # a still-running enrich from the last call is waited for, not started twice
        mine = active or _dispatch(run, {"kinds": "enrich", "ids": ",".join(todo)}, sleep, pause, deadline, clock)
    except RuntimeError as e:
        print(json.dumps({"ok": False, "error": str(e),
                          "next": "go on without affiliations; the trust flag then comes from names only"}))
        return 1
    _wait_done(run, mine, sleep, pause, deadline, clock)
    pull(run)
    have = set(json.loads(path.read_text()).get("papers", {})) if path.exists() else set()
    left = [i for i in ids if i not in have]
    print(json.dumps({"ok": not left, "enriched": len(ids) - len(left), "missing": len(left),
                      "next": "use candidates papers --stage2" if not left else
                              "run the same command again (up to 3 calls), then go on with what is there"}))
    return 0 if not left else 1
