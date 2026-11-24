"""Quarterly synthesis: gather qualitative evidence of exploration and growth.

Output is lists of things (explored, practised, created, emerged, faded, quiet areas),
never percentages or rankings. The written synthesis is personal: it is delivered to the
user (chat / run summary), never committed.
"""

from __future__ import annotations

import datetime as dt
import re

from . import ideas as ideas_mod
from . import profile
from .core import Repo, load_json

Q_RE = re.compile(r"^(\d{4})-Q([1-4])$")


def quarter_bounds(q: str) -> tuple[dt.date, dt.date]:
    m = Q_RE.match(q)
    if not m:
        raise ValueError(f"not a quarter (YYYY-Qn): {q!r}")
    y, n = int(m.group(1)), int(m.group(2))
    start = dt.date(y, 3 * (n - 1) + 1, 1)
    end = dt.date(y + (n == 4), (3 * n) % 12 + 1, 1) - dt.timedelta(days=1)
    return start, end


def quarter_of(d: dt.date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def evidence(repo: Repo, quarter: str) -> dict:
    start, end = quarter_bounds(quarter)
    s, e = start.isoformat(), end.isoformat()
    try:
        dims = {k: v.get("name", k) for k, v in repo.config("interests").get("dimensions", {}).items()}
    except FileNotFoundError:
        dims = {}
    explored = {d: [] for d in dims}
    cross = []
    engaged = []
    for stream in ("weekly", "monthly"):
        for f in repo.iter_stream_files(stream):
            doc = load_json(f)
            when = doc.get("start_date") or doc["month"] + "-01"
            if not s <= when <= e:
                continue
            for it in doc["items"]:
                if it.get("status") in ("completed", "partially_completed", "in_progress"):
                    engaged.append({"title": it["title"], "status": it["status"], "tier": it.get("tier"),
                                    "mode": it.get("mode"), "dimensions": it.get("dimensions", [])})
                    for d in it.get("dimensions", []):
                        explored.setdefault(d, []).append(it["title"])
                if it.get("cross_domain"):
                    cross.append({"title": it["title"], "fields": it["cross_domain"]["fields"]})
    for f in repo.iter_stream_files("discovery"):
        doc = load_json(f)
        if s <= doc["date"] <= e:
            cross += [{"title": it["title"], "fields": it["cross_domain"]["fields"]}
                      for it in doc["items"] if it.get("cross_domain")]
    reg = ideas_mod.load(repo)

    def touched(i, action_prefix=None):
        return any(s <= ev["date"] <= e and (action_prefix is None or ev["action"].startswith(action_prefix))
                   for ev in i.get("history", []))

    ideas_added = [i["title"] for i in reg["ideas"] if s <= i["created"] <= e and i["origin"] == "user"]
    ideas_completed = [i["title"] for i in reg["ideas"] if i["status"] == "completed" and touched(i)]
    ideas_dropped = [i["title"] for i in reg["ideas"] if i["status"] in ("dropped", "not_interested") and touched(i)]
    prof = profile.load(repo)
    signals = {k: sorted(t for t, d in v.items() if s <= d <= e) for k, v in prof["explicit"].items()}
    return {
        "quarter": quarter, "from": s, "to": e,
        "dimensions": dims,
        "engaged_with": engaged,
        "explored_by_dimension": {dims.get(k, k): v for k, v in explored.items()},
        "quiet_dimensions": [dims.get(k, k) for k, v in explored.items() if not v],
        "tiers_engaged": sorted({it.get("tier") for it in engaged if it.get("tier")}),
        "cross_domain_connections": cross,
        "new_user_ideas": ideas_added, "ideas_completed": ideas_completed, "ideas_let_go": ideas_dropped,
        "interest_signals": signals,
        "_how_to_use": ("Qualitative evidence only. Do not compute percentages or rank dimensions. "
                        "Answer the questions in prompts/quarterly.md and suggest what Northstar should do differently."),
    }
