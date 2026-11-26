"""Overview: the best few items of the day's Research and Exploration parts, at most five each,
shown first. Items in the overview are left out of the main list, so nothing appears twice.

The daily run chooses them (`dsys.py daily overview`, field `overview: true`). When it hasn't,
for older days or if a run stopped early, they are chosen from what is already marked best:
research takes `priority: top` papers first, then top research updates; exploration takes one
item from each section in turn, so the overview stays varied."""
from __future__ import annotations

import datetime as dt

from .core import Repo, load_json, write_json

MAX = 5
PARTS = {"research": ("arxiv", "research_updates"), "exploration": ("discovery",)}
STREAMS = {s for ss in PARTS.values() for s in ss}


def _items(streams: dict, s: str) -> list:
    return (streams.get(s) or {}).get("items", [])


def chosen(streams: dict, part: str) -> list[tuple[str, dict]]:
    """(stream, item) pairs in the part's overview, in order, at most MAX."""
    names = PARTS.get(part, ())
    marked = [(s, it) for s in names for it in _items(streams, s) if it.get("overview")]
    if marked:
        return marked[:MAX]
    if part == "research":
        top = [(s, it) for s in names for it in _items(streams, s) if it.get("priority", "top") == "top"]
        return top[:MAX]
    if part == "exploration":
        from .render import group_discovery
        groups = [its for _, _, its in group_discovery(_items(streams, "discovery"))]
        out, i = [], 0
        while len(out) < MAX and any(i < len(g) for g in groups):
            out += [("discovery", g[i]) for g in groups if i < len(g)]
            i += 1
        return out[:MAX]
    return []


def split(streams: dict, part: str) -> tuple[list[tuple[str, dict]], dict]:
    """The overview, and the day's streams with those items removed (for the main list)."""
    ov = chosen(streams, part)
    ids = {it["id"] for _, it in ov}
    rest = {s: ({**doc, "items": [it for it in doc.get("items", []) if it["id"] not in ids]}
                if s in PARTS.get(part, ()) else doc) for s, doc in streams.items()}
    return ov, rest


def errors(stream: str, its: list) -> list[str]:
    n = sum(1 for it in its if it.get("overview"))
    if n and stream not in STREAMS:
        return [f"overview is only for {', '.join(sorted(STREAMS))}"]
    if n > MAX:
        return [f"at most {MAX} overview items; found {n}"]
    return []


def set_overview(repo: Repo, day: dt.date, part: str, ids: list[str]) -> dict:
    """Mark these items (in this order) as the part's overview and clear earlier marks."""
    if part not in PARTS:
        raise SystemExit(f"part must be one of {', '.join(PARTS)}")
    if not 1 <= len(ids) <= MAX:
        raise SystemExit(f"give 1 to {MAX} item ids")
    docs, found = {}, set()
    for s in PARTS[part]:
        path = repo.daily_path(s, day.isoformat())
        if path.exists():
            docs[path] = load_json(path)
    for doc in docs.values():
        for it in doc["items"]:
            it.pop("overview", None)
            if it["id"] in ids:
                it["overview"] = True
                found.add(it["id"])
        doc["items"].sort(key=lambda it: (0, ids.index(it["id"])) if it["id"] in ids else (1, 0))
    unknown = [i for i in ids if i not in found]
    if unknown:
        raise SystemExit(f"not in today's {part}: {', '.join(unknown)}")
    for path, doc in docs.items():
        write_json(path, doc)
    return {"date": day.isoformat(), "part": part, "overview": ids}
