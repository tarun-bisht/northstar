"""Staged reading for the daily run: Python narrows and compacts, cheap models read in bulk,
Sonnet decides. Nothing good is thrown away unseen, and tokens go where judgement is needed.

Papers
  stage1   every unseen paper that matches an interest OR has a quality signal (votes,
           discussion, notable author, venue, released code), as compact batches for Haiku:
           id, title, full abstract, matched interests, signals, trust flag, buzz.
  verdicts Haiku returns {id, lane: strong|field|no}. strong = on the user's interests and
           good; field = important for the field even with little overlap.
  enrich   page 1 of the passing papers (affiliations, emails) via the fetch workflow.
  stage2   the passing papers in full, with affiliations, trust and signals, for the final choice (Sonnet).
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
    from .core import locked
    p = repo.p("state", "stats", f"{day.isoformat()}.json")
    with locked(p):
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


BATCH_CHARS = 60_000  # about 15k tokens: well inside one file read


def stage1(repo: Repo, day: dt.date, batch_size: int = 80) -> dict:
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
    # one paper per line; a batch ends at batch_size papers or BATCH_CHARS characters, whichever
    # comes first, so one Read call always sees the whole batch
    groups, cur, size = [], [], 0
    for r in rows:
        line = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
        if cur and (len(cur) >= batch_size or size + len(line) > BATCH_CHARS):
            groups.append(cur)
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        groups.append(cur)
    for n, g in enumerate(groups, 1):
        f = out_dir / f"stage1_{n:02d}.txt"
        f.write_text("\n".join(wrap("\n".join(g))) + "\n", encoding="utf-8")
        batches.append({"read": str(f), "write": str(out_dir / f"verdict_{n:02d}.json"), "papers": len(g)})
    from .usage import add
    add(repo.root, "papers stage1 batches (Haiku)", sum(Path(b["read"]).stat().st_size for b in batches))
    record(repo, day, "papers", fetched=total, unseen=len(_cands(repo, day)), read_stage1=len(rows),
           skipped_no_interest_no_signal=skipped)
    return {"date": day.isoformat(), "fetched": total, "read_stage1": len(rows), "skipped": skipped,
            "batches": batches, "verdict_format": '[{"id": "2611.01234", "lane": "strong|field|no"}]'}


ENRICH_MAX = 200  # page 1 is read at one paper every 3 s: 200 papers take about 10 minutes


def enrich_ids(repo: Repo, day: dt.date, limit: int = ENRICH_MAX) -> list[str]:
    """Papers whose page 1 is worth reading: strong lane first, then by buzz, at most limit."""
    passed = json.loads((WORK / day.isoformat() / "stage1_passed.json").read_text())
    by_id = {p["arxiv_id"]: p for p in _cands(repo, day)}
    order = sorted(passed, key=lambda i: (passed[i] != "strong", -buzz(by_id.get(i, {})), i))
    return order[:limit]


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
    rate = len(verdicts) / max(1, sum(len(json.loads(Path(f).read_text())) for f in files))
    out_doc = {"passed": len(verdicts), "strong": strong, "field": len(verdicts) - strong,
               "pass_rate": round(rate, 2), "ids": ",".join(sorted(verdicts))}
    if rate > 0.5:
        out_doc["warning"] = ("More than half passed the first reading: the batches were judged too generously. "
                              "That is fine for today, but the final choice must hold the quality bar.")
    return out_doc


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
                    "categories": p.get("categories", [])[:3], "comment": p.get("comment"),
                    "submitted": p.get("submitted")})
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


LEAN_TEXT = 300  # characters of a description or summary kept for choosing


def _clip(text, n: int = LEAN_TEXT):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def lean_media(doc: dict) -> dict:
    """Videos, shorts and podcasts as a run reads them to choose: the description or summary cut to
    its first 300 characters (YouTube descriptions are mostly links, timestamps and sponsor text),
    at most 5 tags, no channel ids. Every field a content item needs (url, embed_url, thumbnail,
    audio_url, stats) is kept. `--full` shows everything."""
    out = []
    for c in doc.get("candidates", []):
        c = dict(c)
        for k in ("description", "summary"):
            if k in c:
                c[k] = _clip(c[k])
        if isinstance(c.get("tags"), list):
            c["tags"] = c["tags"][:5]
        if isinstance(c.get("channel"), dict):
            c["channel"] = {k: v for k, v in c["channel"].items() if k != "id"}
        c.pop("apple_show_url", None)
        if c.get("video_id"):
            # built from the id when writing an item (youtube_shorts.md step 8): not needed to choose
            for k in ("url", "embed_url", "thumbnail", "query_language", "made_for_kids"):
                c.pop(k, None)
        out.append(c)
    return {**doc, "candidates": out}


MAX_PAPERS = 40  # a day's papers, best first: enough to cover the field, few enough to read


def pick(repo: Repo, day: dt.date, choices: list[dict]) -> dict:
    """Build full paper items from the final choice. The model writes only its judgement (arxiv_id,
    priority, research_area, tags, dimensions, in order, best first). Title, authors, link, dates,
    categories, the abstract word for word, affiliations, trust, lane and upvotes come from the
    fetched data, so nothing is retyped and nothing can drift from the source."""
    passed = json.loads((WORK / day.isoformat() / "stage1_passed.json").read_text())
    dropped = choices[MAX_PAPERS:]
    choices = choices[:MAX_PAPERS]  # best first: past the limit, the weakest go
    affil_p = repo.p("candidates", "affil", f"{day.isoformat()}.json")
    affil = load_json(affil_p).get("papers", {}) if affil_p.exists() else {}
    reg = reputation.load(repo)
    by_id = {p["arxiv_id"]: p for p in _cands(repo, day)}
    items, missing = [], []
    for c in choices:
        aid = str(c["arxiv_id"]).replace("arxiv-", "")
        p = by_id.get(aid)
        if not p:
            missing.append(aid)
            continue
        a = affil.get(aid, {})
        full = {**p, "affiliations": sorted(set(p.get("affiliations", [])) | set(a.get("affiliations", []))),
                "email_domains": a.get("email_domains", [])}
        reputation.apply(reg, full)
        it = {"id": f"arxiv-{aid}", "arxiv_id": aid, "title": " ".join(p["title"].split()),
              "authors": p.get("authors", []), "url": f"https://arxiv.org/abs/{aid}",
              "submitted": (p.get("submitted") or "")[:10], "categories": p.get("categories", []),
              "abstract": p.get("abstract", ""), "abstract_source": "arxiv_api_candidates",
              "research_area": c["research_area"], "tags": c.get("tags", []),
              "dimensions": c.get("dimensions", ["research"]), "priority": c.get("priority", "more"),
              "lane": passed.get(aid, c.get("lane", "field")), "trusted": full["trusted"]}
        if full["affiliations"]:
            it["affiliations"] = full["affiliations"][:8]
        if p.get("hf_upvotes"):
            it["hf_upvotes"] = p["hf_upvotes"]
        if p.get("version"):
            it["version"] = p["version"]
        items.append(it)
    out = {"items": items, "missing": missing}
    if dropped:
        out["over_limit"] = (f"{len(dropped)} more papers than the limit of {MAX_PAPERS}; kept the first {MAX_PAPERS} "
                             "as ordered. Mark the dropped ones seen.")
        out["dropped"] = [str(c["arxiv_id"]).replace("arxiv-", "") for c in dropped]
    return out


SHORTS_KEEP = 250


def prefilter_shorts(cands: list[dict], per_channel: int = 3, keep: int = SHORTS_KEEP) -> list[dict]:
    """Narrow shorts before any model reads them, using only rules the shorts prompt already sets:
    nothing made for kids, at most 3 per creator, then the best by engagement (likes and comments
    per view, with reach), taken in turn from each search query. Each query comes from an interest,
    so every topic and tier keeps its share."""
    import math
    from collections import defaultdict

    def score(c):
        v = c.get("views") or 0
        if not v:
            return 0.0
        return ((c.get("likes") or 0) / v) * 10 + ((c.get("comments") or 0) / v) * 100 + math.log10(v + 1) * 0.3

    by_ch: dict = defaultdict(int)
    ok = []
    for c in sorted(cands, key=score, reverse=True):
        ch = (c.get("channel") or {}).get("name", "")
        if c.get("made_for_kids") or by_ch[ch] >= per_channel:
            continue
        by_ch[ch] += 1
        ok.append(c)
    queues: dict = defaultdict(list)
    for c in ok:
        queues[c.get("query", "")].append(c)
    out, i = [], 0
    while len(out) < keep and any(i < len(q) for q in queues.values()):
        out += [q[i] for q in queues.values() if i < len(q)]
        i += 1
    return out[:keep]


_NON_LATIN = __import__("re").compile(r"[\u0900-\u0DFF\u0600-\u06FF\u0750-\u077F]")  # Indic scripts, Arabic/Urdu


def is_english(c: dict) -> bool:
    """English only, for every video, podcast and short: a stated non-English language, or a title in
    an Indic or Arabic script, is out. Learning-language lessons are taught in English, so they pass."""
    lang = (c.get("language") or "").split("-")[0].lower()
    if lang and lang != "en":
        return False
    return not _NON_LATIN.search(str(c.get("title", "")))


def english_only(cands: list[dict]) -> list[dict]:
    return [c for c in cands if is_english(c)]
