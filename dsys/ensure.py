"""Make sure today's candidate files exist before a run uses them.

GitHub's scheduled workflows can start hours late, so a run cannot trust that the 06:37 IST
fetch has happened. If a file is missing, this starts the fetch workflow itself
(workflow_dispatch through the gh CLI), then pulls until the files arrive or the wait runs out.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import time

REPO_SLUG = "tarun-bisht/northstar"
WORKFLOW = "fetch-candidates.yml"


def _missing(repo, day: dt.date, kinds: list[str]) -> list[str]:
    return [k for k in kinds if not repo.p("candidates", k, f"{day.isoformat()}.json").exists()]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(_root()), capture_output=True, text=True, timeout=120)


def _root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent


def ensure(repo, day: dt.date, kinds: list[str], wait: int = 900, pause: int = 30, run=None, sleep=time.sleep) -> int:
    run = run or _run
    missing = _missing(repo, day, kinds)
    if not missing:
        print(json.dumps({"ok": True, "missing": []}))
        return 0
    r = run(["gh", "api", "-X", "POST", f"repos/{REPO_SLUG}/actions/workflows/{WORKFLOW}/dispatches",
             "-f", "ref=main", "-f", f"inputs[kinds]={','.join(missing)}"])
    if r.returncode != 0:
        print(json.dumps({"ok": False, "missing": missing, "dispatched": False, "error": (r.stderr or r.stdout)[-300:],
                          "next": "use the fallback in the stream prompt and say so in notes"}))
        return 1
    waited = 0
    while waited < wait:
        sleep(pause)
        waited += pause
        run(["git", "pull", "-q", "--rebase", "origin", "main"])
        missing = _missing(repo, day, kinds)
        if not missing:
            print(json.dumps({"ok": True, "missing": [], "dispatched": True, "waited_seconds": waited}))
            return 0
    print(json.dumps({"ok": False, "missing": missing, "dispatched": True, "waited_seconds": waited,
                      "next": "use the fallback in the stream prompt and say so in notes"}))
    return 1
