"""Staged reading for the daily run: Python narrows and compacts, cheap models read in bulk,
Opus decides. Nothing good is thrown away unseen, and tokens go where judgement is needed.

Papers
  stage1   every unseen paper that matches an interest OR has a quality signal (votes,
           discussion, notable author, venue, released code), as compact batches for Haiku:
           id, title, full abstract, matched interests, signals, trust flag, buzz.
  verdicts Haiku returns {id, lane: strong|field|no}. strong = on the user's interests and
           good; field = important for the field even with little overlap.
  enrich   page 1 of the passing papers (affiliations, emails) via the fetch workflow.
  stage2   the passing papers in full, with affiliations, trust and signals, for Opus.
News and research updates are compacted the same way, and anything published in the last
three days is dropped (exact URL or the same headline).
Every stage records its counts in state/stats/<date>.json for the Slack message.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from . import rank, reputation
from .core import Repo, load_json, write_json

ALPHAXIV = "https://www.alphaxiv.org/abs/{}"
WORK = Path("/tmp/northstar")


def alphaxiv_url(arxiv_id: str) -> str:
    return ALPHAXIV.format(arxiv_id)


def buzz(p: dict) -> int:
    """One number for how much people are paying attention (votes, upvotes, posts, likes)."""
    return int((p.get("hf_upvotes") or 0) + (p.get("alphaxiv_votes") or 0) + 5 * (p.get("reddit_mentions") or 0)
               + 3 * (p.get("bluesky_mentions") or 0) + (p.get("bluesky_likes") or 0) // 10)


# --- stats ---------------------------------------------------------------------------------
def record(repo: Repo, day: dt.date, stream: str, **counts) -> dict:
    p = repo.p("state", "stats", f"{day.isoformat()}.json")
    doc = load_json(p) if p.exists() else {"date": day.isoformat(), "streams": {}}
    doc["streams"].setdefault(stream, {}).update({k: v for k, v in counts.items() if v is not None})
    write_json(p, doc)
    return doc


def stats(repo: Repo, day: dt.date) -> dict:
    p = repo.p("state", "stats", f"{day.isoformat()}.json")
    return load_json(p) if p.exists() else {"date": day.isoformat(), "streams": {}}


# --- papers ----------------------------------------------------------------------------------
def _cands(repo: Repo, day: dt.date) -> list[dict]:
    from .history import unseen_arxiv_candidates
    return unseen_arxiv_candidates(repo, day).get("candidates", [])


def stage1(repo: Repo, day: dt.date, batch_size: int = 40) -> dict:
    """Write compact batches for the cheap first reading and return their paths and counts."""
    cfg = repo.config("sources")
    topics = cfg["arxiv"].get("coverage", {}).get("topics", [])
    path = repo.p("candidates", "arxiv", f"{day.isoformat()}.json")
    total = len(load_json(path).get("candidates", [])) if path.exists() else 0
    rows, skipped = [], 0
    for p in _cands(repo, day):
        rel, interests = rank.relevance(p, topics)
        for i in p.get("alphaxiv_interests") or []:
            if i not in interests:
                interests.append(i)
        sig = rank.signals(p)
        if not interests and not sig:
            skipped += 1
            continue
        rows.append({"id": p["arxiv_id"], "t": p["title"], "a": p.get("abstract", ""), "i": interests[:4], "s": sig,
                     "tr": int(p.get("trusted") or 0), "b": buzz(p)})
    rows.sort(key=lambda r: (-(len(r["i"]) > 0), -r["b"], r["id"]))
    out_dir = WORK / day.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    from .readable import wrap
    for old in list(out_dir.glob("stage1_*")) + list(out_dir.glob("verdict_*")):
        old.unlink()
    batches = []
    for n, k in enumerate(range(0, len(rows), batch_size), 1):
        # one paper per line, long lines wrapped, so one Read call sees the whole batch
        f = out_dir / f"stage1_{n:02d}.txt"
        f.write_text("\n".join(wrap("\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"))
                                                for r in rows[k:k + batch_size]))) + "\n", encoding="utf-8")
        batches.append({"read": str(f), "write": str(out_dir / f"verdict_{n:02d}.json"),
                        "papers": len(rows[k:k + batch_size])})
    record(repo, day, "papers", fetched=total, unseen=len(_cands(repo, day)), read_stage1=len(rows),
           skipped_no_interest_no_signal=skipped)
    return {"date": day.isoformat(), "fetched": total, "read_stage1": len(rows), "skipped": skipped,
            "batches": batches, "verdict_format": '[{"id": "2611.01234", "lane": "strong|field|no"}]'}


def merge_verdicts(repo: Repo, day: dt.date, files: list[str]) -> dict:
    verdicts: dict[str, str] = {}
    for f in files:
        for v in json.loads(Path(f).read_text()):
            lane = str(v.get("lane", "no")).lower()
            if lane in ("strong", "field"):
                verdicts[str(v["id"])] = lane if verdicts.get(str(v["id"])) != "strong" else "strong"
    out = WORK / day.isoformat() / "stage1_passed.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(verdicts))
    strong = sum(1 for v in verdicts.values() if v == "strong")
    record(repo, day, "papers", passed_stage1=len(verdicts), strong=strong, field=len(verdicts) - strong)
    return {"passed": len(verdicts), "strong": strong, "field": len(verdicts) - strong, "ids": ",".join(sorted(verdicts))}


def stage2(repo: Repo, day: dt.date) -> list[dict]:
    """The passing papers in full for the final decision, with page-1 affiliations and trust."""
    passed = json.loads((WORK / day.isoformat() / "stage1_passed.json").read_text())
    affil_p = repo.p("candidates", "affil", f"{day.isoformat()}.json")
    affil = load_json(affil_p).get("papers", {}) if affil_p.exists() else {}
    reg = reputation.load(repo)
    topics = repo.config("sources")["arxiv"].get("coverage", {}).get("topics", [])
    out = []
    for p in _cands(repo, day):
        lane = passed.get(p["arxiv_id"])
        if not lane:
            continue
        a = affil.get(p["arxiv_id"], {})
        full = {**p, "affiliations": sorted(set(p.get("affiliations", [])) | set(a.get("affiliations", []))),
                "email_domains": a.get("email_domains", [])}
        reputation.apply(reg, full)
        _, interests = rank.relevance(p, topics)
        out.append({"id": p["arxiv_id"], "lane": lane, "title": p["title"], "authors": p.get("authors", [])[:12],
                    "abstract": p.get("abstract", ""), "affiliations": full["affiliations"][:8],
                    "trusted": full["trusted"], "trust_matches": full.get("trust_matches", []),
                    "interests": interests[:4], "signals": rank.signals(p), "buzz": buzz(p),
                    "categories": p.get("categories", []), "comment": p.get("comment"),
                    "submitted": p.get("submitted"), "alphaxiv": alphaxiv_url(p["arxiv_id"])})
    out.sort(key=lambda r: (r["lane"] != "strong", -r["trusted"], -r["buzz"]))
    hot = [{"arxiv_id": r["id"], "authors": r["authors"], "affiliations": r["affiliations"]} for r in out if r["buzz"] >= 20]
    if hot:
        reputation.log_papers(repo, day, hot, "trending")
    record(repo, day, "papers", read_stage2=len(out), enriched=sum(1 for v in affil.values() if v.get("affiliations")))
    return out


# --- news and updates ------------------------------------------------------------------------
_W = re.compile(r"[a-z0-9]+")


def headline_key(t: str) -> str:
    return " ".join(_W.findall((t or "").lower()))[:100]


def recent_published(repo: Repo, stream: str, day: dt.date, days: int = 3) -> tuple[set, set]:
    """URLs and headline keys published in a stream over the last `days` days (not today)."""
    urls, heads = set(), set()
    for k in range(1, days + 1):
        p = repo.daily_path(stream, (day - dt.timedelta(days=k)).isoformat())
        if not p.exists():
            continue
        doc = load_json(p)
        for it in doc.get("items", []) + doc.get("briefs", []):
            for u in (it.get("url"), (it.get("source") or {}).get("url") if isinstance(it.get("source"), dict) else None):
                if u:
                    urls.add(u)
            heads.add(headline_key(it.get("title") or it.get("headline") or ""))
    return urls, heads - {""}


def compact_updates(repo: Repo, day: dt.date) -> list[dict]:
    from .history import latest_candidates
    doc = latest_candidates(repo, "updates", day)
    urls, heads = recent_published(repo, "research_updates", day)
    out, dropped = [], 0
    for i, x in enumerate(doc.get("candidates", [])):
        if x.get("url") in urls or headline_key(x.get("title")) in heads:
            dropped += 1
            continue
        out.append({"n": i, "t": x.get("title"), "s": x.get("source"), "k": x.get("kind"), "u": x.get("url"),
                    "d": (x.get("published") or "")[:10], "x": (x.get("summary") or "")[:1200],
                    **({"pts": x["points"]} if x.get("points") else {}), **({"likes": x["likes"]} if x.get("likes") else {})})
    record(repo, day, "research_updates", fetched=len(doc.get("candidates", [])), dropped_recent=dropped, read=len(out))
    return out
