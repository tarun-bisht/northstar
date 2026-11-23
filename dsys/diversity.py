"""Variety signals for planners: tier mix, dimension spread, media mix.

Observations with gentle suggestions, never quotas or scores.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

from .core import Repo, load_json

MEDIA = {"podcast": ("podcast",), "video": ("video", "lecture", "documentary", "playlist", "course")}


def recent_items(repo: Repo, day: dt.date, days: int) -> list[dict]:
    cutoff = (day - dt.timedelta(days=days)).isoformat()
    out = []
    for f in repo.iter_stream_files("discovery"):
        doc = load_json(f)
        if doc["date"] >= cutoff:
            out += [{**it, "_stream": "discovery"} for it in doc["items"]]
    for stream, end_key in (("weekly", "end_date"), ("monthly", None)):
        for f in repo.iter_stream_files(stream):
            doc = load_json(f)
            end = doc[end_key] if end_key else doc["month"] + "-31"
            if end >= cutoff:
                out += [{**it, "_stream": stream} for it in doc["items"]]
    return out


def report(repo: Repo, day: dt.date, days: int = 30) -> dict:
    items = recent_items(repo, day, days)
    try:
        dims_cfg = list(repo.config("interests").get("dimensions", {}))
    except FileNotFoundError:
        dims_cfg = []
    tiers = Counter(it.get("tier") for it in items if it.get("tier"))
    dims = Counter(d for it in items for d in it.get("dimensions", []))
    media = Counter(m for it in items if it.get("_stream") == "discovery"
                    for m, keys in MEDIA.items() if str(it.get("type", "")).lower() in keys)
    cross = sum(1 for it in items if it.get("cross_domain"))
    n = len(items)
    suggestions = []
    if n:
        if not tiers.get("exploration"):
            suggestions.append("No exploration lately: add one genuinely unfamiliar, worthwhile surprise.")
        if not tiers.get("growth"):
            suggestions.append("No growth items lately: add a small step in a growth topic.")
        if tiers.get("established", 0) < n / 3:
            suggestions.append("Established interests are under-served: most items should stay relevant to them.")
        if not cross:
            suggestions.append("No cross-domain picks lately: add one that links two unrelated fields.")
        quiet = [d for d in dims_cfg if not dims.get(d)]
        if quiet:
            suggestions.append(f"Not touched lately: {', '.join(quiet)}.")
    return {"window_days": days, "items": n, "tiers": dict(tiers), "dimensions": dict(dims), "media": dict(media),
            "cross_domain_items": cross, "suggestions": suggestions,
            "_note": "Observations, not quotas. Most time in established, steady growth, always some exploration."}
