"""Schedule awareness: how much optional time a week or month is likely to have.

Inputs (config/schedules.json, all optional):
  default_load  light | normal | free: what an ordinary period feels like
  recurring     usual free time per weekday, e.g. weekday evenings 0.5h, weekends 2.5h
  periods       dated exceptions: busy ('light') or freer ('free') stretches

Per day: available = recurring hours for that weekday x multiplier of any dated period
covering it. When dated periods overlap on a day, busy ('light') wins, since protecting
real life is the safer error. Over a range, available hours are compared with a usual
range: well below means light, well above means free, otherwise default_load.

Without recurring entries every day counts as one unit, so dated periods still work.
"""

from __future__ import annotations

import datetime as dt

from .core import Repo, period_bounds

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MULTIPLIER = {"light": 0.3, "normal": 1.0, "free": 2.0}
LIGHT_BELOW, FREE_ABOVE = 0.6, 1.4
PRECEDENCE = {"light": 3, "free": 2, "normal": 1}


def _recurring_hours(cfg: dict) -> dict[str, float] | None:
    rules = cfg.get("recurring")
    if not isinstance(rules, list) or not rules:
        return None
    hours = {d: 0.0 for d in DAYS}
    for r in rules:
        for d in r.get("days", []):
            if d in hours:
                hours[d] += float(r.get("hours_per_day", 0))
    return hours


def day_info(cfg: dict, day: dt.date) -> dict:
    hours = _recurring_hours(cfg)
    base = hours[DAYS[day.weekday()]] if hours else 1.0
    covering = [p for p in cfg.get("periods", [])
                if dt.date.fromisoformat(p["start"]) <= day <= dt.date.fromisoformat(p["end"])]
    load = max((p["load"] for p in covering), key=lambda l: PRECEDENCE.get(l, 0), default=None)
    mult = MULTIPLIER.get(load, 1.0) if load else 1.0
    return {"date": day.isoformat(), "base": base, "available": base * mult, "period_load": load,
            "labels": [p.get("label", "") for p in covering]}


def load_for_range(cfg: dict, start: dt.date, end: dt.date) -> dict:
    days = [day_info(cfg, start + dt.timedelta(days=i)) for i in range((end - start).days + 1)]
    base = sum(d["base"] for d in days)
    avail = sum(d["available"] for d in days)
    ratio = (avail / base) if base > 0 else 1.0
    if ratio < LIGHT_BELOW:
        load = "light"
    elif ratio > FREE_ABOVE:
        load = "free"
    else:
        load = cfg.get("default_load", "normal")
    labels = sorted({l for d in days for l in d["labels"] if l})
    periods = []
    for p in cfg.get("periods", []):
        ps, pe = dt.date.fromisoformat(p["start"]), dt.date.fromisoformat(p["end"])
        if ps <= end and pe >= start:
            periods.append({**p, "overlap_days": (min(pe, end) - max(ps, start)).days + 1})
    out = {"load": load, "periods": periods, "labels": labels, "ratio_to_usual": round(ratio, 2)}
    if _recurring_hours(cfg):
        out["available_hours"] = round(avail, 1)
        out["usual_hours"] = round(base, 1)
    return out


def load_for_period(repo: Repo, period: str) -> dict:
    start, end = period_bounds(period)
    p = repo.p("config", "schedules.json")
    cfg = repo.config("schedules") if p.exists() else {}
    return load_for_range(cfg, start, end)
