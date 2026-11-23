"""Configuration checks: required files, ids, conflicts, schedules, URLs, sources."""

from __future__ import annotations

import datetime as dt
import json
import re

from .core import Repo, load_json

REQUIRED = ["interests", "preferences", "recommendation_policy", "sources", "site", "languages"]
OPTIONAL = ["schedules"]
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
ARXIV_CAT_RE = re.compile(r"^[a-z-]+(\.[A-Za-z-]+)?$")
DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
LOADS = {"light", "normal", "free"}


def arxiv_categories(sources: dict) -> list[str]:
    """Category ids from config/sources.json (accepts plain strings or {id, covers} objects)."""
    out = []
    for c in sources.get("arxiv", {}).get("categories", []):
        out.append(c["id"] if isinstance(c, dict) else c)
    return out


def _find_key(obj, key, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield f"{path}/{k}"
            yield from _find_key(v, key, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _find_key(v, key, f"{path}/{i}")


def check(repo: Repo) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    cfg = {}
    for name in REQUIRED + OPTIONAL:
        p = repo.p("config", f"{name}.json")
        if not p.exists():
            (errors if name in REQUIRED else warnings).append(
                f"config/{name}.json missing" + ("" if name in REQUIRED else " (defaults used)"))
            continue
        try:
            cfg[name] = load_json(p)
        except json.JSONDecodeError as e:
            errors.append(f"config/{name}.json: invalid JSON: {e}")

    i = cfg.get("interests", {})
    dims = i.get("dimensions")
    if i and (not isinstance(dims, dict) or not dims):
        errors.append("config/interests.json: 'dimensions' must be a non-empty object")
    elif isinstance(dims, dict):
        for k, v in dims.items():
            if not ID_RE.match(k):
                errors.append(f"config/interests.json: dimension id {k!r} must be lowercase letters/digits/_")
            if not isinstance(v, dict) or not v.get("name"):
                errors.append(f"config/interests.json: dimension {k!r} needs a 'name'")
    for t in ("established", "growth", "exploration"):
        if i and not isinstance(i.get(t), dict):
            errors.append(f"config/interests.json: missing tier '{t}' (an object of topic lists)")
    for path in _find_key(i, "arxiv_categories"):
        errors.append(f"config/interests.json{path}: arXiv categories belong only in config/sources.json -> arxiv.categories")

    s = cfg.get("sources", {})
    if s:
        cats = arxiv_categories(s)
        if not cats:
            errors.append("config/sources.json: arxiv.categories is empty")
        for c in cats:
            if not ARXIV_CAT_RE.match(c):
                errors.append(f"config/sources.json: invalid arXiv category {c!r}")
        if len(set(cats)) != len(cats):
            errors.append("config/sources.json: duplicate arXiv categories")
        for c in s.get("arxiv", {}).get("max_results_overrides", {}):
            if c not in cats:
                warnings.append(f"config/sources.json: max_results_overrides has {c!r}, which is not in categories")
        groups = s.get("youtube", {}).get("query_groups", [])
        if not groups:
            warnings.append("config/sources.json: youtube.query_groups is empty (YouTube candidates will be empty)")
        for g in groups:
            if not g.get("language") or not g.get("queries"):
                errors.append("config/sources.json: each youtube query group needs 'language' and 'queries'")

    lg = cfg.get("languages", {})
    if lg:
        ids = [l.get("id") for l in lg.get("learning", [])]
        if not ids:
            errors.append("config/languages.json: 'learning' must list at least one language")
        for l in lg.get("learning", []):
            if not ID_RE.match(l.get("id") or "") or not l.get("name"):
                errors.append(f"config/languages.json: each language needs an id (lowercase) and a name: {l}")
        if lg.get("current_focus") not in ids:
            errors.append("config/languages.json: current_focus must be one of the learning ids")

    site = cfg.get("site", {})
    if site:
        b = site.get("base_url", "")
        if not re.match(r"^https://[^\s]+[^/]$", b):
            errors.append("config/site.json: base_url must start with https:// and have no trailing slash")

    sc = cfg.get("schedules", {})
    if sc:
        if sc.get("default_load", "normal") not in LOADS:
            errors.append("config/schedules.json: default_load must be light, normal or free")
        for r in sc.get("recurring", []) or []:
            if not set(r.get("days", [])) <= DAYS:
                errors.append(f"config/schedules.json: recurring {r.get('label')!r} has invalid days")
            try:
                if float(r.get("hours_per_day", 0)) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"config/schedules.json: recurring {r.get('label')!r} hours_per_day must be >= 0")
        for p in sc.get("periods", []):
            try:
                a, b2 = dt.date.fromisoformat(p["start"]), dt.date.fromisoformat(p["end"])
                if a > b2:
                    errors.append(f"config/schedules.json: period {p.get('label')!r} ends before it starts")
            except (KeyError, ValueError):
                errors.append(f"config/schedules.json: period {p.get('label')!r} needs valid start/end dates")
            if p.get("load") not in LOADS:
                errors.append(f"config/schedules.json: period {p.get('label')!r} load must be light, normal or free")

    pol = cfg.get("recommendation_policy", {})
    tiers = pol.get("tiers", {})
    shares = [v.get("share", 0) for k, v in tiers.items() if not k.startswith("_")]
    if shares and abs(sum(shares) - 1) > 0.05:
        warnings.append("config/recommendation_policy.json: tier shares should add up to about 1 (they are guidance)")
    for k, v in pol.get("feeds", {}).items():
        if not isinstance(v, int) or v < 1:
            errors.append(f"config/recommendation_policy.json: feeds.{k} must be a positive integer")
    return errors, warnings
