"""Trust registry (config/reputation.json): a binary flag for papers from known groups.

A paper is `trusted: 1` when any of these match the registry:
- an author is a listed researcher;
- an organization or affiliation (from arXiv, Hugging Face, alphaXiv, or page 1 of the
  paper) names a listed university or lab, by name or alias;
- an author email domain belongs to a listed university or lab.

It is a hint, not a verdict: with a thousand universities, most academic papers match.
Quality still comes from the abstract and the other signals. The monthly run keeps the
registry current (prompts/runs/monthly.md) from state/reputation_log.json.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from functools import lru_cache

FILE = ("config", "reputation.json")
LOG = ("state", "reputation_log.json")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


class Registry:
    def __init__(self, data: dict):
        self.data = data
        self.people = {norm(r["name"]) for r in data.get("researchers", [])}
        for r in data.get("researchers", []):
            self.people |= {norm(a) for a in r.get("aliases", [])}
        self.orgs: list[tuple[re.Pattern, str]] = []
        self.domains: dict[str, str] = {}
        for group in ("universities", "labs"):
            for o in data.get(group, []):
                for name in [o["name"]] + o.get("aliases", []):
                    pat = _pattern(name)
                    if pat:
                        self.orgs.append((pat, o["name"]))
                for d in o.get("domains", []):
                    self.domains[d.lower().lstrip("@.")] = o["name"]

    def match_people(self, authors: list[str]) -> list[str]:
        return [a for a in authors or [] if norm(a) in self.people]

    def match_text(self, texts: list[str]) -> list[str]:
        hits = []
        for t in texts or []:
            for pat, name in self.orgs:
                if name not in hits and pat.search(t):
                    hits.append(name)
        return hits

    def match_domains(self, domains: list[str]) -> list[str]:
        hits = []
        for d in domains or []:
            d = d.lower()
            parts = d.split(".")
            for i in range(len(parts) - 1):  # cs.stanford.edu -> stanford.edu
                name = self.domains.get(".".join(parts[i:]))
                if name and name not in hits:
                    hits.append(name)
                    break
        return hits


def _pattern(name: str) -> re.Pattern | None:
    name = (name or "").strip()
    if len(name) < 2:
        return None
    if name.isupper() and len(name) <= 6:  # MIT, CMU, KAIST: exact case, whole word
        return re.compile(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])")
    body = r"[\s,\-]+".join(re.escape(t) for t in name.lower().split())
    return re.compile(rf"(?<![a-z]){body}(?![a-z])", re.I)


def load(repo) -> Registry:
    p = repo.p(*FILE)
    return _load(str(p), p.stat().st_mtime if p.exists() else 0)


@lru_cache(maxsize=4)
def _load(path: str, _mtime: float) -> Registry:
    try:
        return Registry(json.loads(open(path, encoding="utf-8").read()))
    except FileNotFoundError:
        return Registry({})


def apply(reg: Registry, paper: dict) -> dict:
    """Set paper['trusted'] (1 or 0) and paper['trust_matches'] from everything we know."""
    hits = reg.match_people(paper.get("authors", []))
    hits += [h for h in reg.match_text(paper.get("organizations", []) + paper.get("affiliations", [])) if h not in hits]
    hits += [h for h in reg.match_domains(paper.get("email_domains", [])) if h not in hits]
    paper["trusted"] = 1 if hits else 0
    if hits:
        paper["trust_matches"] = hits[:6]
    else:
        paper.pop("trust_matches", None)
    return paper


# --- the log the monthly run uses to grow the registry ------------------------------------
def log_papers(repo, day: dt.date, papers: list[dict], kind: str) -> dict:
    """Count authors and affiliations of picked and trending papers that the registry does not
    cover yet. Public data only (names on public papers)."""
    from .core import load_json, write_json
    p = repo.p(*LOG)
    doc = load_json(p) if p.exists() else {"authors": {}, "orgs": {}}
    reg = load(repo)
    for paper in papers:
        aid = paper.get("arxiv_id")
        known = set(paper.get("trust_matches", []))
        for a in paper.get("authors", [])[:12]:
            if norm(a) in reg.people:
                continue
            e = doc["authors"].setdefault(a, {"papers": [], "kinds": {}})
            if aid and aid not in e["papers"]:
                e["papers"] = (e["papers"] + [aid])[-20:]
                e["kinds"][kind] = e["kinds"].get(kind, 0) + 1
                e["last"] = day.isoformat()
        for o in paper.get("organizations", []) + paper.get("affiliations", []):
            if reg.match_text([o]) or o in known:
                continue
            e = doc["orgs"].setdefault(o[:120], {"papers": [], "kinds": {}})
            if aid and aid not in e["papers"]:
                e["papers"] = (e["papers"] + [aid])[-20:]
                e["kinds"][kind] = e["kinds"].get(kind, 0) + 1
                e["last"] = day.isoformat()
    cutoff = (day - dt.timedelta(days=120)).isoformat()  # forget what stopped recurring
    for key in ("authors", "orgs"):
        doc[key] = {k: v for k, v in doc[key].items() if v.get("last", "") >= cutoff}
    write_json(p, doc)
    return doc


def suggestions(repo, min_papers: int = 3) -> dict:
    """Recurring authors and organizations, with their papers, for the monthly review."""
    from .core import load_json
    p = repo.p(*LOG)
    doc = load_json(p) if p.exists() else {"authors": {}, "orgs": {}}
    pick = lambda d: sorted(([k, v] for k, v in d.items() if len(v["papers"]) >= min_papers),
                            key=lambda kv: -len(kv[1]["papers"]))[:40]
    return {"authors": pick(doc["authors"]), "orgs": pick(doc["orgs"])}
