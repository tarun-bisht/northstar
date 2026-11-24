"""Quarterly review: deterministic stats plus the quarter's topics, split into three parts.

`draft` writes content/quarterly/<YYYY>/<YYYY-Qn>.json with every number and topic filled
in and empty `summary`/`about` fields. The quarterly run only writes those few lines, so
the review stays short and cheap. It is public: counts and topics, nothing personal.

Parts: research (research practice, research reading, research deep dives), knowledge
(questions, things to know, knowledge deep dives), exploration (culture, people, making,
exploration deep dives). Papers, news and shorts appear only as counts.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from . import render
from .core import DAILY_STREAMS, Repo, load_json, write_json

Q_RE = re.compile(r"^(\d{4})-Q([1-4])$")
PARTS = ["research", "knowledge", "exploration"]


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
    news: Counter = Counter()
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
                if stream == "world":
                    news[render.world_section(it)] += 1
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
        "news_by_category": dict(news.most_common()),
        "top_paper_tags": [[t, n] for t, n in tags.most_common(10)],
        "top_research_areas": [[a, n] for a, n in areas.most_common(12)],
    }


def topics(repo: Repo, quarter: str, base_url: str = "") -> dict[str, list[dict]]:
    """Every weekly and monthly item of the quarter, by part (never news or shorts)."""
    start, end = quarter_bounds(quarter)
    s, e = start.isoformat(), end.isoformat()
    out: dict[str, list[dict]] = {p: [] for p in PARTS}
    for f in repo.iter_stream_files("monthly"):
        doc = load_json(f)
        if s <= doc["month"] + "-01" <= e:
            for it in doc["items"]:
                part = render.monthly_section(it)
                out[part].append({"period": doc["month"], "kind": "monthly", "title": it["title"],
                                  "url": f"{base_url}/monthly/{doc['month']}/{part}.html", "about": ""})
    for f in repo.iter_stream_files("weekly"):
        doc = load_json(f)
        if s <= doc["start_date"] <= e:
            for it in doc["items"]:
                part = render.weekly_part(it)
                out[part].append({"period": doc["week"], "kind": "weekly", "title": it["title"],
                                  "url": f"{base_url}/weekly/{doc['week']}/{part}.html", "about": ""})
    return {p: sorted(v, key=lambda t: (t["period"], t["kind"], t["title"])) for p, v in out.items()}


def draft(repo: Repo, quarter: str | None = None, today: dt.date | None = None) -> dict:
    """Write the review file with stats and topics. Existing summaries and abouts are kept."""
    q = quarter or quarter_of(today or dt.date.today())
    start, end = quarter_bounds(q)
    base = repo.config("site").get("base_url", "")
    p = path_for(repo, q)
    old = load_json(p) if p.exists() else {}
    old_parts = old.get("parts", {})
    old_about = {(t["period"], t["title"]): t.get("about", "")
                 for part in old_parts.values() for t in part.get("topics", [])}
    parts = {}
    for name, tps in topics(repo, q, base).items():
        for t in tps:
            t["about"] = old_about.get((t["period"], t["title"]), "")
        parts[name] = {"summary": old_parts.get(name, {}).get("summary", ""), "topics": tps}
    doc = {"schema": "quarterly", "quarter": q, "from": start.isoformat(), "to": end.isoformat(),
           "generated_at": now_utc(), "generator": "dsys quarterly draft", "stats": stats(repo, q), "parts": parts}
    write_json(p, doc)
    return {"path": str(p.relative_to(repo.root)), "quarter": q,
            "topics_to_describe": {k: len(v["topics"]) for k, v in parts.items()}, "stats": doc["stats"]}
