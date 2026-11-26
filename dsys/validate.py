"""Repository validation: syntax, schemas, dates, URLs, ids, duplicates, references."""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from . import arxiv as ax
from . import youtube as yt
from .core import (ALL_STREAMS, DAILY_STREAMS, MONTH_RE, WEEK_RE, Repo, load_json,
                   month_bounds, parse_date, week_bounds)
from .schemas import schema_errors

PODCAST_TYPES = {"podcast"}
VIDEO_TYPES = {"video", "lecture", "documentary", "playlist"}
DATE_KEYS = {"date", "submitted", "published", "created", "updated", "deferred_until", "start_date", "end_date"}
URL_KEYS = {"url", "pdf_url", "embed_url", "thumbnail", "audio_url", "source_url", "solution_url"}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_checked: int = 0

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


def guid_for(stream: str, doc: dict, item: dict | None = None) -> str:
    if stream == "weekly":
        return f"dsys:weekly:{doc['week']}"
    if stream == "monthly":
        return f"dsys:monthly:{doc['month']}"
    if stream == "quarterly":
        return f"dsys:quarterly:{doc['quarter']}"
    return f"dsys:{stream}:{item['id']}"


def url_ok(u: str) -> bool:
    if not isinstance(u, str) or any(c.isspace() for c in u):
        return False
    try:
        p = urllib.parse.urlparse(u)
    except ValueError:
        return False
    host = p.hostname or ""
    return p.scheme in ("http", "https") and "." in host and not host.startswith(".") and not host.endswith(".")


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}/{k}")
            yield path, k, v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}/{i}")


_DIMS: set[str] | None = None
_LANGS: set[str] = set()
_TAGS: set[str] = set()
STYLE_KEYS = {"what_happened", "why_it_matters", "what_to_watch", "context", "analysis", "description",
              "why_recommended", "why", "explanation", "note", "why_it_matches", "objective", "intro", "connection"}


def _semantic_checks(rep: Report, where: str, doc) -> None:
    for path, k, v in _walk(doc):
        if k in STYLE_KEYS and isinstance(v, str) and ("\u2014" in v or ";" in v):
            rep.warn(where, f"{path}/{k}: use plain sentences (no em dashes or semicolons)")
        if k == "dimensions" and isinstance(v, list) and _DIMS is not None:
            for fa in v:
                if fa not in _DIMS:
                    rep.err(where, f"{path}/{k}: unknown dimension {fa!r} (define it in config/interests.json)")
        if k in DATE_KEYS and isinstance(v, str):
            try:
                parse_date(v)
            except ValueError:
                rep.err(where, f"{path}/{k}: invalid date {v!r}")
        if k in URL_KEYS and isinstance(v, str) and not url_ok(v):
            rep.err(where, f"{path}/{k}: invalid URL {v!r}")
        if k in ("generated_at", "verified_at") and isinstance(v, str):
            try:
                dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                rep.err(where, f"{path}/{k}: invalid datetime {v!r}")
        if k in ("scheduled_for", "decision_target", "period") and isinstance(v, str):
            try:
                (week_bounds if WEEK_RE.match(v) else month_bounds)(v)
            except ValueError:
                rep.err(where, f"{path}/{k}: invalid period {v!r}")


TIERS = {"established", "growth", "exploration"}
LEARNING_CATEGORIES = {"research_fundamentals", "ai_study", "paper", "new_knowledge"}


TEACHING_FROM = "2026-11-27"  # news and exploration teach, not just list (from this date on)


def teaching_errors(stream: str, items: list) -> list[str]:
    """Explained news items carry a lesson (the idea behind the story); discovery items say what
    you'll learn or get from them."""
    errs = []
    if stream == "world":
        for it in items:
            if not it.get("lesson"):
                errs.append(f"world item {it.get('id')}: needs a lesson (the concept or history behind the story)")
    if stream == "discovery":
        for it in items:
            if not it.get("what_i_might_get_from_it"):
                errs.append(f"discovery item {it.get('id')}: needs what_i_might_get_from_it (what you'll learn or get)")
    return errs


def discovery_rule_errors(items: list) -> list[str]:
    """Daily rules: at least one podcast, at least one video, and every tier represented. The rest is free."""
    errs = []
    types = {str(it.get("type", "")).lower() for it in items}
    if not types & PODCAST_TYPES:
        errs.append("Daily Discovery needs at least one podcast episode every day")
    if not types & VIDEO_TYPES:
        errs.append("Daily Discovery needs at least one video, lecture or documentary every day")
    missing = TIERS - {it.get("tier") for it in items}
    if missing:
        errs.append(f"Daily Discovery needs at least one item in each tier; missing: {', '.join(sorted(missing))}")
    return errs


def learning_item_errors(it: dict) -> list[str]:
    """Study topics, readings and learning exercises come with a study plan (steps) and real resources."""
    from .render import weekly_section
    sec = weekly_section(it)
    if sec == "knowledge":
        errs = []
        if len(it.get("steps", [])) < 3:
            errs.append(f"item {it.get('id')}: knowledge topics need a study plan of at least 3 steps")
        if len(it.get("resources", [])) < 2:
            errs.append(f"item {it.get('id')}: knowledge topics need at least 2 resources (video, lecture, notes, book chapter, paper)")
        if not it.get("subject"):
            errs.append(f"item {it.get('id')}: knowledge topics need a subject")
        return errs
    if it.get("category") not in LEARNING_CATEGORIES and it.get("mode") != "learn" and sec not in ("research_practice", "research_reading"):
        return []
    errs = []
    if len(it.get("steps", [])) < 2:
        errs.append(f"item {it.get('id')}: learning items need at least 2 concrete steps")
    if not it.get("resources") and not it.get("paper"):
        errs.append(f"item {it.get('id')}: learning items need resources (link, book chapter, video, paper)")
    return errs


WEEKLY_REQUIRED = {  # sections a weekly package must cover, by load (prompts/weekly.md)
    "light": {"research_practice", "questions", "culture"},
    "normal": {"research_practice", "research_reading", "knowledge", "questions", "curiosities", "culture", "people_self"},
    "free": {"research_practice", "research_reading", "knowledge", "questions", "curiosities", "culture", "people_self",
             "curiosity_making"},
}
OTHER_SUBJECTS_MIN = {"light": 0, "normal": 5, "free": 5}  # knowledge topics outside maths and physics
CORE = {"maths", "probability", "physics"}


PILLARS = ["research", "knowledge", "world", "people", "culture", "curiosity"]  # defaults; config dimensions win


def weekly_section_errors(doc: dict, dims: list[str] | None = None) -> list[str]:
    """Sections by load, maths and physics questions, rotating subjects, and every pillar of development."""
    from .render import weekly_section
    items = doc.get("items", [])
    load = doc.get("load", "normal")
    errs = []
    have = {weekly_section(it) for it in items}
    missing = WEEKLY_REQUIRED.get(load, WEEKLY_REQUIRED["normal"]) - have
    if missing:
        errs.append(f"weekly package is missing sections: {', '.join(sorted(missing))} (see prompts/weekly.md)")
    qs = [it for it in items if weekly_section(it) == "questions"]
    need = 1 if load == "light" else 2
    maths = sum(1 for q in qs if q.get("subject") in ("maths", "probability"))
    physics = sum(1 for q in qs if q.get("subject") == "physics")
    if maths < need or physics < need:
        errs.append(f"weekly questions need at least {need} maths or probability and {need} physics "
                    f"(subject field); found {maths} and {physics}")
    others = {it.get("subject") for it in items if weekly_section(it) == "knowledge"} - CORE - {None}
    need_other = OTHER_SUBJECTS_MIN.get(load, 5)
    if len(others) < need_other:
        errs.append(f"weekly knowledge needs topics in at least {need_other} subjects besides maths and physics; "
                    f"found {len(others)} ({', '.join(sorted(others)) or 'none'})")
    if load != "light":
        pillars = [p for p in (dims or PILLARS)]
        covered = {d for it in items for d in it.get("dimensions", [])}
        gap = [p for p in pillars if p not in covered]
        if gap:
            errs.append(f"weekly package must touch every pillar of development; missing: {', '.join(gap)}")
    return errs


MONTHLY_REQUIRED = {"light": {"research"}, "normal": {"research", "fundamentals", "knowledge", "exploration"},
                    "free": {"research", "fundamentals", "knowledge", "exploration"}}


def monthly_section_errors(doc: dict) -> list[str]:
    """Deep dives in every section, and hard challenge problems: maths, physics and rotating subjects."""
    from .render import monthly_section
    load = doc.get("load", "normal")
    errs = []
    have = {monthly_section(pj) for pj in doc.get("items", [])}
    missing = MONTHLY_REQUIRED.get(load, MONTHLY_REQUIRED["normal"]) - have
    if missing:
        errs.append(f"monthly package needs a deep dive in: {', '.join(sorted(missing))} (see prompts/monthly.md)")
    cs = doc.get("challenges", [])
    need = 1 if load == "light" else 2
    maths = sum(1 for c in cs if c.get("subject") in ("maths", "probability"))
    physics = sum(1 for c in cs if c.get("subject") == "physics")
    if maths < need or physics < need:
        errs.append(f"monthly challenges need at least {need} maths or probability and {need} physics problems; "
                    f"found {maths} and {physics}")
    others = {c.get("subject") for c in cs} - CORE
    if load != "light" and len(others) < 4:
        errs.append(f"monthly challenges need problems in at least 4 subjects besides maths and physics; found {len(others)}")
    return errs


def monthly_rotation_warnings(repo: Repo, doc: dict) -> list[str]:
    """The exploration deep dive should rotate through people, culture and curiosity month to month."""
    from .render import monthly_section
    def explore_dims(d):
        return {x for pj in d.get("items", []) if monthly_section(pj) == "exploration" for x in pj.get("dimensions", [])}
    prev = sorted((load_json(f) for f in repo.iter_stream_files("monthly")
                   if load_json(f)["month"] < doc["month"]), key=lambda d: d["month"])[-2:]
    now = explore_dims(doc) & {"people", "culture", "curiosity"}
    recent = set().union(*(explore_dims(d) for d in prev)) if prev else set()
    if prev and now and now <= recent and {"people", "culture", "curiosity"} - recent:
        return [f"monthly exploration repeats {', '.join(sorted(now))} from the last two months; "
                f"rotate to {', '.join(sorted({'people', 'culture', 'curiosity'} - recent))}"]
    return []


def project_errors(pj: dict) -> list[str]:
    errs = []
    if any(not w.get("tasks") for w in pj.get("weeks", [])):
        errs.append(f"project {pj.get('id')}: every week needs concrete tasks (a syllabus, not just a theme)")
    n = len(pj.get("resources", [])) + (1 if pj.get("primary_resource") else 0)
    if n < 2:
        errs.append(f"project {pj.get('id')}: needs a primary resource and further resources (links, chapters, videos)")
    return errs


def _youtube_day_checks(rep: Report, where: str, items: list, repo: Repo) -> None:
    """Variety warnings: creator over-representation and near-duplicate titles within a day."""
    try:
        policy = repo.config("recommendation_policy")
        limit = int(policy.get("dedup_windows_days", {}).get("youtube_creator_soft_limit_per_day", 3))
        langs = set(repo.config("sources").get("youtube", {}).get("languages_accepted", ["en", "hi"]))
    except FileNotFoundError:
        limit, langs = 3, {"en", "hi"}
    per = {}
    for it in items:
        ch = it.get("channel", {}).get("id") or it.get("channel", {}).get("name")
        per[ch] = per.get(ch, 0) + 1
        if it.get("language") and it["language"] not in langs:
            rep.warn(where, f"video {it.get('id')}: language {it['language']!r} not in languages_accepted")
    for ch, n in per.items():
        if n > limit:
            rep.warn(where, f"{n} videos from {ch!r} (soft limit {limit}/day): spread creators across days")
    titles = [(it.get("id"), it.get("title", "")) for it in items]
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            if yt.near_duplicate(titles[i][1], titles[j][1]):
                rep.warn(where, f"near-duplicate titles: {titles[i][0]} and {titles[j][0]}")


def _load(rep: Report, repo: Repo, path: Path):
    rep.files_checked += 1
    rel = path.relative_to(repo.root) if path.is_relative_to(repo.root) else path
    try:
        return load_json(path), str(rel)
    except json.JSONDecodeError as e:
        rep.err(str(rel), f"invalid JSON: {e}")
    except UnicodeDecodeError as e:
        rep.err(str(rel), f"not UTF-8: {e}")
    return None, str(rel)


def validate_repo(repo: Repo, examples: bool = False) -> Report:
    global _DIMS, _LANGS, _TAGS
    rep = Report()
    sp = repo.p("config", "sources.json")
    _TAGS = set(load_json(sp).get("paper_tags", {}).get("tags", [])) if sp.exists() else set()
    lp = repo.p("config", "languages.json")
    _LANGS = {l["id"] for l in load_json(lp).get("learning", [])} if lp.exists() else set()
    if not examples:
        from .config import check as check_config
        cerrs, cwarns = check_config(repo)
        for e in cerrs:
            rep.err("config", e)
        for w in cwarns:
            rep.warn("config", w)
        from .privacy import scan_repo
        perrs, pwarns = scan_repo(repo)
        for e in perrs:
            rep.err("privacy", e)
        for w in pwarns:
            rep.warn("privacy", w)
    schema_dir = repo.p("schemas")
    try:
        _DIMS = set(repo.config("interests").get("dimensions", {})) or None
    except FileNotFoundError:
        _DIMS = None
    state_dir = repo.p("examples", "state") if examples else repo.p("state")

    # ---- ideas registry -----------------------------------------------------
    idea_ids: set[str] = set()
    ideas_file = state_dir / "ideas.json"
    if ideas_file.exists():
        ideas, where = _load(rep, repo, ideas_file)
        if ideas is not None:
            for e in schema_errors(schema_dir, "ideas", ideas):
                rep.err(where, e)
            _semantic_checks(rep, where, ideas)
            for idea in ideas.get("ideas", []) if isinstance(ideas, dict) else []:
                iid = idea.get("id")
                if iid in idea_ids:
                    rep.err(where, f"duplicate idea id {iid!r}")
                idea_ids.add(iid)
            if isinstance(ideas, dict):
                from .ideas import explicit_intent_errors
                for e in explicit_intent_errors(ideas):
                    rep.err(where, e)
            for idea in ideas.get("ideas", []) if isinstance(ideas, dict) else []:
                rb = idea.get("replaced_by")
                if rb and rb not in idea_ids:
                    rep.err(where, f"idea {idea.get('id')!r}: replaced_by {rb!r} does not exist")
                if idea.get("scheduled_for") and idea.get("status") in ("dropped", "not_interested", "completed"):
                    rep.warn(where, f"idea {idea.get('id')!r} is {idea['status']} but still has scheduled_for")

    # ---- other state files: syntax only ------------------------------------
    if state_dir.exists():
        for f in sorted(state_dir.glob("*.json")):
            if f.name != "ideas.json":
                _load(rep, repo, f)

    # ---- content streams ----------------------------------------------------
    guids: dict[str, str] = {}
    reading_weeks: dict[str, int] = {}
    weekly_weeks: list[str] = []
    periodic_items: dict[str, dict[str, str]] = {}  # period -> {item_id: title}
    all_periodic_ids: dict[str, str] = {}
    continues_refs: list[tuple[str, str]] = []

    for stream in ALL_STREAMS:
        seen_ids: dict[str, str] = {}
        seen_papers: dict[str, str] = {}
        seen_videos: dict[str, str] = {}
        for f in repo.iter_stream_files(stream, examples):
            doc, where = _load(rep, repo, f)
            if doc is None:
                continue
            errs = schema_errors(schema_dir, stream, doc)
            for e in errs:
                rep.err(where, e)
            if errs or not isinstance(doc, dict):
                continue
            _semantic_checks(rep, where, doc)
            if examples and not doc.get("example"):
                rep.err(where, "example files must set \"example\": true")
            if not examples and doc.get("example"):
                rep.err(where, "example data must live under examples/, not content/")

            # path consistency
            if stream in DAILY_STREAMS:
                d = doc["date"]
                expected = Path(stream, d[:4], d[5:7], f"{d}.json")
                if not str(f).endswith(str(expected)):
                    rep.err(where, f"path must end with {expected}")
            elif stream == "weekly":
                w = doc["week"]
                try:
                    s, e_ = week_bounds(w)
                    if doc["start_date"] != s.isoformat() or doc["end_date"] != e_.isoformat():
                        rep.err(where, f"start/end must be {s}..{e_} for {w}")
                except ValueError as ex:
                    rep.err(where, str(ex))
                if f.name != f"{w}.json" or f.parent.name != w[:4]:
                    rep.err(where, f"path must be weekly/{w[:4]}/{w}.json")
            elif stream == "monthly":
                m = doc["month"]
                if f.name != f"{m}.json" or f.parent.name != m[:4]:
                    rep.err(where, f"path must be monthly/{m[:4]}/{m}.json")
            elif stream == "quarterly":
                q = doc["quarter"]
                if f.name != f"{q}.json" or f.parent.name != q[:4]:
                    rep.err(where, f"path must be quarterly/{q[:4]}/{q}.json")
                for name, part in doc["parts"].items():
                    if part["topics"] and not part["summary"].strip():
                        rep.err(where, f"parts/{name}: summary is empty: write two to four plain lines")
                    for t in part["topics"]:
                        if not t["about"].strip():
                            rep.err(where, f"parts/{name}: topic {t['title']!r} has no 'about' line")

            if stream == "reading":
                w = doc["week"]
                try:
                    s_, e_ = week_bounds(w)
                    if doc["start_date"] != s_.isoformat() or doc["end_date"] != e_.isoformat():
                        rep.err(where, f"start/end must be {s_}..{e_} for {w}")
                except ValueError as ex:
                    rep.err(where, str(ex))
                if f.name != f"{w}.json" or f.parent.name != w[:4]:
                    rep.err(where, f"path must be reading/{w[:4]}/{w}.json")
                reading_weeks[w] = len(doc["papers"])
                for pp in doc["papers"]:
                    if pp["id"] in seen_ids:
                        rep.err(where, f"duplicate reading-list id {pp['id']!r}")
                    seen_ids[pp["id"]] = where
                    key = pp.get("arxiv_id") or pp["url"]
                    if key in seen_papers:
                        rep.err(where, f"paper {key} is already on the reading list in {seen_papers[key]}")
                    seen_papers[key] = where
                    for t in pp["tags"]:
                        if t not in _TAGS:
                            rep.err(where, f"tag {t!r} is not one of the fixed paper_tags")
                    g = f"dsys:reading:{pp['id']}"
                    guids[g] = where
                continue

            items = doc.get("items", [])
            if stream == "weekly":
                weekly_weeks.append(doc["week"])
            if stream in ("weekly", "monthly"):
                period = doc.get("week") or doc.get("month")
                periodic_items[period] = {}
                g = guid_for(stream, doc)
                if g in guids:
                    rep.err(where, f"duplicate GUID {g} (also in {guids[g]})")
                guids[g] = where
            for it in items:
                iid = it.get("id")
                if iid in seen_ids:
                    rep.err(where, f"duplicate {stream} item id {iid!r} (also in {seen_ids[iid]})")
                seen_ids[iid] = where
                if stream in DAILY_STREAMS:
                    g = guid_for(stream, doc, it)
                    if g in guids and guids[g] != where:
                        rep.err(where, f"duplicate GUID {g}")
                    guids[g] = where
                if stream == "arxiv":
                    for e in ax.url_errors(it):
                        rep.err(where, f"paper {iid}: {e}")
                    for t in it.get("tags", []):
                        if t not in _TAGS:
                            rep.err(where, f"paper {iid}: tag {t!r} is not one of the fixed paper_tags")
                    a = it.get("arxiv_id")
                    if a in seen_papers:
                        rep.err(where, f"duplicate paper {a} (already in {seen_papers[a]})")
                    seen_papers[a] = where
                elif stream == "youtube_shorts":
                    for e in yt.url_errors(it):
                        rep.err(where, f"video {iid}: {e}")
                    v = it.get("video_id")
                    if iid != f"yt-{v}":
                        rep.err(where, f"video item id must be 'yt-{v}'")
                    if v in seen_videos:
                        rep.err(where, f"duplicate video {v} (already in {seen_videos[v]})")
                    seen_videos[v] = where
                    if not examples and it.get("verification", {}).get("method") == "example_unverified":
                        rep.err(where, f"video {iid}: unverified videos are not allowed in content/")
                elif stream in ("weekly", "monthly"):
                    period = doc.get("week") or doc.get("month")
                    if iid in all_periodic_ids:
                        rep.err(where, f"activity id {iid!r} reused (also in {all_periodic_ids[iid]})")
                    all_periodic_ids[iid] = where
                    periodic_items[period][iid] = it.get("title", "")
                    ref = it.get("idea_id")
                    if ref and ref not in idea_ids:
                        rep.err(where, f"item {iid}: idea_id {ref!r} not found in ideas registry")
                    if it.get("origin") == "user_idea" and not ref:
                        rep.warn(where, f"item {iid}: origin=user_idea without idea_id")
                    if it.get("continues"):
                        continues_refs.append((where, it["continues"]))
                    if it.get("category") == "paper" and "paper" not in it:
                        rep.err(where, f"item {iid}: category=paper requires a 'paper' block")
            if stream == "youtube_shorts":
                _youtube_day_checks(rep, where, items, repo)
            if stream == "discovery":
                for e in discovery_rule_errors(items):
                    rep.err(where, e)
            if doc.get("date", "") >= TEACHING_FROM:
                for e in teaching_errors(stream, items):
                    rep.err(where, e)
            if stream == "language":
                for it in items:
                    if it.get("language") not in _LANGS:
                        rep.err(where, f"language {it.get('language')!r} is not in config/languages.json -> learning")
                    if it.get("id") != f"lang-{doc['date']}":
                        rep.err(where, f"language pack id must be 'lang-{doc['date']}'")
            if stream == "weekly":
                for ls in doc.get("language", {}).get("lessons", []):
                    if ls["language"] not in _LANGS:
                        rep.err(where, f"lesson language {ls['language']!r} is not in config/languages.json")
            if stream == "monthly":
                for pl in doc.get("language", {}).get("plans", []):
                    if pl["language"] not in _LANGS:
                        rep.err(where, f"plan language {pl['language']!r} is not in config/languages.json")
            if stream == "youtube_shorts" and items:
                missing = TIERS - {it.get("tier") for it in items}
                if missing:
                    rep.err(where, f"Shorts need at least one video in each tier; missing: {', '.join(sorted(missing))}")
            if stream == "weekly":
                for it in items:
                    for e in learning_item_errors(it):
                        rep.err(where, e)
                for e in weekly_section_errors(doc, sorted(_DIMS) if _DIMS else PILLARS):
                    rep.err(where, e)
            if stream == "monthly":
                if not any(it.get("tier") == "growth" for it in items):
                    rep.err(where, "every monthly package needs at least one growth item (a reading or exercise "
                                   "in science, mathematics, neuroscience or philosophy that broadens research)")
                for it in items:
                    for e in project_errors(it):
                        rep.err(where, e)
                for e in monthly_section_errors(doc):
                    rep.err(where, e)
                for w_ in monthly_rotation_warnings(repo, doc):
                    rep.warn(where, w_)

    if not examples:
        lang_days = {f.stem for f in repo.iter_stream_files("language")}
        for f in repo.iter_stream_files("discovery"):
            if f.stem not in lang_days:
                rep.err(str(f.relative_to(repo.root)), "every day needs its 5-minute language pack "
                        f"(content/language/{f.stem[:4]}/{f.stem[5:7]}/{f.stem}.json)")

    for w in weekly_weeks:
        if not examples and reading_weeks.get(w, 0) < 3:
            rep.err(f"content/weekly/{w[:4]}/{w}.json",
                    f"week {w} needs a reading list with at least 3 papers (content/reading/{w[:4]}/{w}.json)")

    for where, ref in continues_refs:
        if ref not in all_periodic_ids:
            rep.err(where, f"continues {ref!r} does not match any earlier activity")

    # ---- feedback -------------------------------------------------------------
    for f in repo.iter_feedback_files(examples):
        doc, where = _load(rep, repo, f)
        if doc is None:
            continue
        errs = schema_errors(schema_dir, "feedback", doc)
        for e in errs:
            rep.err(where, e)
        if errs:
            continue
        _semantic_checks(rep, where, doc)
        period = doc["period"]
        if f.name != f"{period}.json":
            rep.err(where, f"feedback file must be named {period}.json")
        if period not in periodic_items:
            rep.err(where, f"no weekly/monthly package found for period {period}")
            continue
        for ent in doc["entries"]:
            if ent["item_id"] not in periodic_items[period]:
                rep.err(where, f"item_id {ent['item_id']!r} is not in package {period}")
    return rep
