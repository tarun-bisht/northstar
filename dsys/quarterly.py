"""Quarterly review: deterministic stats plus the topics of the quarter's packages.

`draft` writes content/quarterly/<YYYY>/<YYYY-Qn>.json with every number filled in and an
empty `summary` and `about` fields. The quarterly run only writes those few lines, so the
review stays short and cheap. It is public: it holds counts and topics, nothing personal.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

from .core import DAILY_STREAMS, Repo, load_json, write_json
from .synthesis import quarter_bounds, quarter_of


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def path_for(repo: Repo, quarter: str):
    return repo.p("content", "quarterly", quarter[:4], f"{quarter}.json")


def stats(repo: Repo, quarter: str) -> dict:
    start, end = quarter_bounds(quarter)
    s, e = start.isoformat(), end.isoformat()
    counts: Counter = Counter()
    tiers: Counter = Counter()
    tags: Counter = Counter()
    areas: Counter = Counter()
    days = set()
    for stream in DAILY_STREAMS:
        for f in repo.iter_stream_files(stream):
            doc = load_json(f)
            if not s <= doc["date"] <= e:
                continue
            if doc["items"]:
                days.add(doc["date"])
            counts[stream] += len(doc["items"])
            for it in doc["items"]:
                if stream == "discovery" and it.get("tier"):
                    tiers[it["tier"]] += 1
                if stream == "arxiv":
                    tags.update(it.get("tags", []))
                    if it.get("research_area"):
                        areas[it["research_area"].lower()] += 1
    for f in repo.iter_stream_files("reading"):
        doc = load_json(f)
        if s <= doc["start_date"] <= e:
            counts["reading_list_papers"] += len(doc["papers"])
            tags.update(t for pp in doc["papers"] for t in pp.get("tags", []))
    for stream, key in (("weekly", "start_date"), ("monthly", None)):
        for f in repo.iter_stream_files(stream):
            doc = load_json(f)
            when = doc[key] if key else doc["month"] + "-01"
            if s <= when <= e:
                counts[f"{stream}_packages"] += 1
                counts[f"{stream}_items"] += len(doc["items"])
    return {
        "days_with_content": len(days),
        "counts": dict(sorted(counts.items())),
        "discovery_by_tier": {t: tiers.get(t, 0) for t in ("established", "growth", "exploration")},
        "top_paper_tags": [[t, n] for t, n in tags.most_common(10)],
        "top_research_areas": [[a, n] for a, n in areas.most_common(12)],
    }


def topics(repo: Repo, quarter: str, base_url: str = "") -> list[dict]:
    """Every weekly and monthly item of the quarter (research and discovery, never news or shorts)."""
    start, end = quarter_bounds(quarter)
    s, e = start.isoformat(), end.isoformat()
    out = []
    for f in repo.iter_stream_files("monthly"):
        doc = load_json(f)
        if s <= doc["month"] + "-01" <= e:
            out += [{"period": doc["month"], "kind": "monthly", "title": it["title"],
                     "url": f"{base_url}/monthly/{doc['month']}.html", "about": ""} for it in doc["items"]]
    for f in repo.iter_stream_files("weekly"):
        doc = load_json(f)
        if s <= doc["start_date"] <= e:
            out += [{"period": doc["week"], "kind": "weekly", "title": it["title"],
                     "url": f"{base_url}/weekly/{doc['week']}.html", "about": ""} for it in doc["items"]]
    return sorted(out, key=lambda t: (t["period"], t["kind"], t["title"]))


def draft(repo: Repo, quarter: str | None = None, today: dt.date | None = None) -> dict:
    """Write the review file with stats and topics. Existing summary and abouts are kept."""
    q = quarter or quarter_of(today or dt.date.today())
    start, end = quarter_bounds(q)
    base = repo.config("site").get("base_url", "")
    p = path_for(repo, q)
    old = load_json(p) if p.exists() else {}
    old_about = {(t["period"], t["title"]): t.get("about", "") for t in old.get("topics", [])}
    tps = topics(repo, q, base)
    for t in tps:
        t["about"] = old_about.get((t["period"], t["title"]), "")
    doc = {"schema": "quarterly", "quarter": q, "from": start.isoformat(), "to": end.isoformat(),
           "generated_at": now_utc(), "generator": "dsys quarterly draft",
           "stats": stats(repo, q), "summary": old.get("summary", ""), "topics": tps}
    write_json(p, doc)
    return {"path": str(p.relative_to(repo.root)), "quarter": q, "topics_to_describe": len(tps),
            "stats": doc["stats"]}
