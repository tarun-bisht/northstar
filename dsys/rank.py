"""Rank arXiv candidates in code, from title, abstract and signals, before any AI reads them.

Thousands of papers arrive each weekday. Reading every abstract would use the whole run, so
this module scores each candidate deterministically and the run reads only a shortlist:
the top `ranking.shortlist_size` plus every trending or notable paper.

relevance  coverage keywords from config/sources.json -> arxiv.coverage.topics, matched in
           the title (counts double) and abstract, scaled by each topic's weight
quality    community interest (Hugging Face upvotes, alphaXiv votes), a notable researcher,
           released code, a named venue in the arXiv comment (e.g. "Accepted at ICLR 2027")

The score orders the reading. It never decides on its own: the run judges each shortlisted
abstract against the quality rubric in prompts/arxiv.md.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

CODE_RE = re.compile(r"github\.com|gitlab\.com|huggingface\.co/|code (is|and data are|will be) (publicly )?available|"
                     r"we (open[- ]source|release) (our|the) (code|model|data)", re.I)


@lru_cache(maxsize=4096)
def _kw_re(kw: str) -> re.Pattern:
    """Whole-word match for short keywords (llm, rag, gan), prefix match for longer ones (agent -> agents)."""
    k = re.escape(kw.lower())
    return re.compile(rf"\b{k}\b" if len(kw) <= 4 else rf"\b{k}", re.I)


def _venue_re(venues: tuple[str, ...]) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(re.escape(v) for v in venues) + r")\b", re.I)


def relevance(paper: dict, topics: list[dict]) -> tuple[float, list[str]]:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    cats = set(paper.get("categories") or [])
    score, hits = 0.0, []
    for t in topics:
        if cats and not cats & set(t.get("categories", [])):
            continue  # e.g. a physics paper that says "stability" is not about learning algorithms
        kws = t.get("keywords", [])
        in_title = any(_kw_re(k).search(title) for k in kws)
        in_abs = in_title or any(_kw_re(k).search(abstract) for k in kws)
        if in_abs:
            w = float(t.get("weight", 1))
            score += w * (2 if in_title else 1)
            hits.append((w * (2 if in_title else 1), t["interest"]))
    return score, [i for _, i in sorted(hits, reverse=True)]


def signals(paper: dict, venue_re: re.Pattern | None = None) -> list[str]:
    out = []
    if paper.get("notable_authors"):
        out.append("notable researcher")
    if paper.get("alphaxiv_votes"):
        out.append(f"alphaXiv {paper['alphaxiv_votes']} votes")
    if paper.get("hf_upvotes"):
        out.append(f"HF {paper['hf_upvotes']} upvotes")
    if "Twitter (X)" in (paper.get("alphaxiv_lists") or []):
        out.append("discussed on X")
    if paper.get("alphaxiv_interests"):
        out.append("alphaXiv search: " + ", ".join(paper["alphaxiv_interests"][:2]))
    text = f"{paper.get('abstract', '')} {paper.get('comment', '')}"
    if CODE_RE.search(text):
        out.append("code released")
    m = venue_re.search(paper.get("comment", "") or "") if venue_re else None
    if m:
        out.append(f"venue {m.group(1)}")
    return out


def quality(paper: dict, venue_re: re.Pattern | None = None) -> float:
    q = 1.5 * math.log2(1 + paper.get("hf_upvotes", 0)) + 1.5 * math.log2(1 + paper.get("alphaxiv_votes", 0))
    sig = signals(paper, venue_re)
    q += 3 * bool(paper.get("notable_authors")) + 1.5 * ("code released" in sig) + 2 * any(s.startswith("venue") for s in sig)
    q += 1.5 * ("discussed on X" in sig) + 1.0 * bool(paper.get("alphaxiv_interests"))
    return q


def is_trending(paper: dict, cfg: dict) -> bool:
    return (paper.get("alphaxiv_votes", 0) >= int(cfg.get("trending_alphaxiv_votes", 5))
            or paper.get("hf_upvotes", 0) >= int(cfg.get("trending_hf_upvotes", 10)))


def rank(candidates: list[dict], sources: dict) -> list[dict]:
    """Return brief rows sorted by score, best first. Papers with no relevance and no strong signal are dropped."""
    arx = sources.get("arxiv", {})
    topics = arx.get("coverage", {}).get("topics", [])
    cfg = arx.get("ranking", {})
    vre = _venue_re(tuple(cfg.get("venues", []))) if cfg.get("venues") else None
    rows = []
    for p in candidates:
        rel, interests = relevance(p, topics)
        for i in p.get("alphaxiv_interests") or []:  # alphaXiv's own search agrees it is about this interest
            if i not in interests:
                interests.append(i)
                rel += 1
        trend = is_trending(p, cfg)
        notable = bool(p.get("notable_authors"))
        if rel == 0 and not trend and not notable:
            continue
        q = quality(p, vre)
        score = rel + q if rel > 0 else 0.5 * q
        rows.append({"arxiv_id": p["arxiv_id"], "title": p.get("title", ""), "score": round(score, 2),
                     "interests": interests[:3], "signals": signals(p, vre),
                     **({"trending": True} if trend else {}), **({"notable_authors": p["notable_authors"]} if notable else {})})
    rows.sort(key=lambda r: (-r["score"], r["arxiv_id"]))
    return rows


def shortlist(candidates: list[dict], sources: dict, limit: int | None = None) -> dict:
    """Every interest first, then the best of the rest.

    1. For each coverage topic, the best `per_interest` papers that match it, so no interest is
       crowded out by whichever area is loudest on Hugging Face that day.
    2. Filled up to `shortlist_size` by overall score.
    3. Every trending or notable paper beyond the cut, listed separately.
    """
    cfg = sources.get("arxiv", {}).get("ranking", {})
    n = int(limit or cfg.get("shortlist_size", 80))
    per = int(cfg.get("per_interest", 3))
    rows = rank(candidates, sources)
    chosen: dict[str, dict] = {}
    for t in sources.get("arxiv", {}).get("coverage", {}).get("topics", []):
        for r in [r for r in rows if t["interest"] in r["interests"]][:per]:
            chosen.setdefault(r["arxiv_id"], r)
    for r in rows:
        if len(chosen) >= n:
            break
        chosen.setdefault(r["arxiv_id"], r)
    top = sorted(chosen.values(), key=lambda r: (-r["score"], r["arxiv_id"]))
    extra = [r for r in rows if r["arxiv_id"] not in chosen and (r.get("trending") or r.get("notable_authors"))]
    covered = sorted({i for r in top for i in r["interests"]})
    return {"ranked_total": len(rows), "shortlist": top, "also_trending_or_notable": extra,
            "interests_in_shortlist": len(covered)}
