"""Command-line interface: `python scripts/dsys.py <command> ...`  (run with -h for help)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from . import feedback as fb_mod
from . import history
from . import ideas as ideas_mod
from .core import (DAILY_STREAMS, Repo, dump_json, iso_week, load_json, month_of, next_month, next_week,
                   repo_from_env, today, write_json)
from .schedule import load_for_period
from .validate import validate_repo

INBOX_TEMPLATES = {
    "ideas": """# Ideas inbox

This file is PUBLIC (it lives in a public repo). Write interests and ideas, not private details.
Write anything here, any time (GitHub web/mobile editor works fine). The next scheduled run
reads it, records each idea in `state/ideas.json`, scopes it (weekly vs monthly), and clears this file.

Examples:
- I want to learn photography (maybe a monthly thing)
- try pottery this weekend
- curious about the history of the Mughal empire
- recommend a hobby I can do in 30 minutes a day

---
""",
    "feedback": """# Feedback inbox

This file is PUBLIC (it lives in a public repo, and Git keeps history). Keep it to what you did and
liked. Anything personal, just tell Claude in chat.
Tell the system how the week/month went, in plain words. No forms. Mention item names loosely;
the next weekly/monthly run matches them, records feedback, and clears this file.

Examples:
- Did the probability puzzle, loved it, more like that. Skipped the pottery video, no time.
- The monthly interpretability project is going well, want to continue next month.
- Next two weeks are crunch for a deadline — keep it light.
- Less anime this month, more history.

---
""",
}


def _day(s: str | None) -> dt.date:
    return dt.date.fromisoformat(s) if s else today()


def _print(obj):
    sys.stdout.write(dump_json(obj))


def _parse_list(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def cmd_validate(repo: Repo, args) -> int:
    rc = 0
    targets = [False, True] if args.all else [args.examples]
    for ex in targets:
        rep = validate_repo(repo, examples=ex)
        label = "examples" if ex else "content"
        for w in rep.warnings:
            print(f"WARN  [{label}] {w}")
        for e in rep.errors:
            print(f"ERROR [{label}] {e}")
        print(f"[{label}] {rep.files_checked} files checked: {len(rep.errors)} errors, {len(rep.warnings)} warnings")
        rc |= 0 if rep.ok else 1
    return rc


def cmd_rss(repo: Repo, args) -> int:
    if cmd_validate(repo, argparse.Namespace(all=False, examples=False)):
        print("Refusing to generate RSS from invalid content.")
        return 1
    from .rss import generate_all
    for stream, path in generate_all(repo).items():
        print(f"wrote {path.relative_to(repo.root)}")
    return 0


def cmd_build(repo: Repo, args) -> int:
    if cmd_validate(repo, argparse.Namespace(all=True, examples=False)):
        print("Refusing to build from invalid content.")
        return 1
    from .site import build_site
    out = build_site(repo)
    print(f"site built at {out}")
    return 0


def cmd_history(repo: Repo, args) -> int:
    _print(history.rebuild(repo))
    return 0


def cmd_papers(repo: Repo, args) -> int:
    n = history.mark_papers_seen(repo, args.ids, _day(args.date))
    print(f"marked {n} papers as seen")
    return 0


def cmd_candidates(repo: Repo, args) -> int:
    day = _day(args.date)
    if args.kind == "news":
        _print(history.news_candidates(repo, day, args.category or args.section, args.brief))
        return 0
    data = (history.unseen_arxiv_candidates if args.kind == "arxiv" else history.unseen_youtube_candidates)(repo, day)
    if args.kind == "arxiv" and args.ids:
        want = {i.strip() for i in args.ids.split(",") if i.strip()}
        data["candidates"] = [c for c in data["candidates"] if c["arxiv_id"] in want]
        _print(data)
        return 0
    if args.kind == "arxiv" and args.trending_week:
        _print(history.week_trending(repo, args.trending_week, args.limit or 30))
        return 0
    if args.kind == "arxiv" and args.ranked:
        from . import rank
        sl = rank.shortlist(data["candidates"], repo.config("sources"), args.limit)
        _print({k: v for k, v in data.items() if k != "candidates"} | sl)
        return 0
    if args.limit:
        data["candidates"] = data["candidates"][args.offset:args.offset + args.limit]
    if args.brief and args.kind == "arxiv":
        data["candidates"] = [{"arxiv_id": c["arxiv_id"], "title": c["title"], "categories": c.get("categories", []),
                               **{k: c[k] for k in ("hf_upvotes", "alphaxiv_votes", "notable_authors") if c.get(k)}}
                              for c in data["candidates"]]
    _print(data)
    return 0


def cmd_context(repo: Repo, args) -> int:
    _print(history.context(repo, args.stream, _day(args.date), args.period))
    return 0


def cmd_period(repo: Repo, args) -> int:
    d = _day(args.date)
    w, m = iso_week(d), month_of(d)
    _print({"date": d.isoformat(), "this_week": w, "next_week": next_week(w), "this_month": m,
            "next_month": next_month(m), "load_this_week": load_for_period(repo, w)["load"],
            "load_next_week": load_for_period(repo, next_week(w))["load"],
            "load_next_month": load_for_period(repo, next_month(m))["load"]})
    return 0


def cmd_daily(repo: Repo, args) -> int:
    """Merge items into a day's file (creating it), skipping ids already present."""
    day = _day(args.date)
    path = repo.daily_path(args.stream, day.isoformat())
    doc = load_json(path) if path.exists() else {"schema": args.stream, "date": day.isoformat(), "items": []}
    doc["generated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    doc["generator"] = args.generator or doc.get("generator", "claude-scheduled-task")
    incoming = load_json(args.items) if args.items else []
    if isinstance(incoming, dict):
        if incoming.get("notes"):
            doc["notes"] = incoming["notes"]
        if "candidates_considered" in incoming:
            doc["candidates_considered"] = incoming["candidates_considered"]
        if incoming.get("briefs"):  # world: one-line "also in the news" headlines
            seen = {b["url"] for b in doc.get("briefs", [])}
            doc["briefs"] = doc.get("briefs", []) + [b for b in incoming["briefs"] if b["url"] not in seen]
        incoming = incoming.get("items", [])
    have = {i["id"] for i in doc["items"]}
    added = 0
    for it in incoming:
        if it["id"] not in have:
            doc["items"].append(it)
            have.add(it["id"])
            added += 1
    if args.notes:
        doc["notes"] = args.notes
    write_json(path, doc)
    print(f"{path.relative_to(repo.root)}: +{added} items ({len(doc['items'])} total)")
    return 0


def cmd_ideas(repo: Repo, args) -> int:
    reg = ideas_mod.load(repo)
    day = _day(getattr(args, "date", None))
    limit = int(repo.config("recommendation_policy").get("reschedule_limit", 2))
    a = args.action
    try:
        if a == "list":
            rows = [i for i in reg["ideas"] if not args.status or i["status"] in args.status.split(",")]
            for i in rows:
                print(f"{i['id']:<55} {i['status']:<14} {i['scope']:<10} {i.get('scheduled_for', ''):<9} {i['title']}")
            print(f"({len(rows)} ideas)")
            return 0
        if a == "show":
            _print(ideas_mod.get(reg, args.id))
            return 0
        if a == "due":
            _print(ideas_mod.due_for(reg, args.period))
            return 0
        if a == "add":
            idea = ideas_mod.add(reg, args.title, day, description=args.description or "", scope=args.scope,
                                 status=args.status, dimensions=_parse_list(args.dimensions), origin=args.origin,
                                 first_step=args.first_step, estimate=args.estimate, tags=_parse_list(args.tags))
            if args.week or args.month:
                ideas_mod.schedule(reg, idea["id"], args.week or args.month, day, limit=limit)
        elif a == "status":
            idea = ideas_mod.set_status(reg, args.id, args.status, day, args.note)
        elif a == "schedule":
            target = args.week or args.month
            if args.next_week:
                target = next_week(iso_week(day))
            if args.next_month:
                target = next_month(month_of(day))
            if not target:
                print("give --week YYYY-Www, --month YYYY-MM, --next-week or --next-month")
                return 2
            idea = ideas_mod.schedule(reg, args.id, target, day, limit=limit, force=args.force, note=args.note)
        elif a == "unschedule":
            idea = ideas_mod.unschedule(reg, args.id, day)
        elif a == "defer":
            idea = ideas_mod.defer(reg, args.id, day, args.until, args.note)
        elif a == "drop":
            idea = ideas_mod.drop(reg, args.id, day, args.note, args.not_interested)
        elif a == "resize":
            idea = ideas_mod.resize(reg, args.id, args.scope, day, args.note)
        elif a == "replace":
            idea = ideas_mod.replace(reg, args.id, args.title, day, description=args.description or "")
        elif a == "note":
            idea = ideas_mod.note(reg, args.id, args.text, day)
        elif a == "remove":
            idea = ideas_mod.remove(reg, args.id)
        else:
            raise ideas_mod.IdeaError(f"unknown action {a}")
    except ideas_mod.IdeaError as e:
        print(f"error: {e}")
        return 1
    except ValueError as e:
        print(f"error: {e}")
        return 1
    ideas_mod.save(repo, reg)
    print(f"{a}: {idea['id']} -> status={idea['status']}, scope={idea['scope']}, "
          f"scheduled_for={idea.get('scheduled_for', '-')}")
    return 0


def cmd_feedback(repo: Repo, args) -> int:
    day = _day(args.date)
    try:
        if args.action == "record":
            if args.json:
                data = load_json(args.json)
                entries, general = data.get("entries", []), data.get("general")
            else:
                e = {"item_id": args.item, "status": args.status}
                for k in ("decision", "learned", "enjoyed", "difficult", "skip_reason", "notes", "interest",
                          "difficulty_feedback"):
                    if getattr(args, k, None):
                        e[k] = getattr(args, k)
                if args.target:
                    e["decision_target"] = args.target
                if args.decision_note:
                    e["decision_note"] = args.decision_note
                entries = [e] if args.item else []
                general = {"more_of": _parse_list(args.more) or [], "less_of": _parse_list(args.less) or [],
                           "notes": args.general_notes or ""}
            doc = fb_mod.record(repo, args.period, entries, day, general=general)
            print(f"recorded {len(doc['entries'])} entries for {args.period}")
        elif args.action == "apply":
            for line in fb_mod.apply(repo, args.period, day, force=args.force):
                print(line)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e}")
        return 1
    return 0


def cmd_interests(repo: Repo, args) -> int:
    from . import interests as im
    doc = im.load(repo)
    try:
        if args.action == "list":
            for path, lst in sorted(im.lists(doc).items()):
                print(f"{path:<28} {', '.join(lst)}")
            return 0
        if args.action == "find":
            hits = im.find_everywhere(doc, args.value)
            print("\n".join(hits) if hits else "(not found)")
            return 0
        if args.action == "add":
            changed = im.add(doc, args.path, args.value, create=args.create)
        elif args.action == "remove":
            changed = im.remove(doc, args.path, args.value)
        else:
            changed = im.move(doc, args.src, args.dst, args.value)
    except im.InterestError as e:
        print(f"error: {e}")
        return 1
    if changed:
        im.save(repo, doc)
    print(f"{args.action}: {'done' if changed else 'no change'}")
    return 0


def cmd_reading(repo: Repo, args) -> int:
    """Add papers to a week's reading list (created if missing). Skips papers already on any list."""
    from .core import iso_week, week_bounds
    day = _day(args.date)
    week = args.week or iso_week(day)
    path = repo.reading_path(week)
    s_, e_ = week_bounds(week)
    doc = load_json(path) if path.exists() else {"schema": "reading", "week": week, "start_date": s_.isoformat(),
                                                   "end_date": e_.isoformat(), "papers": []}
    if args.action == "show":
        _print(doc)
        return 0
    known = set()
    for f in repo.iter_stream_files("reading"):
        for pp in load_json(f)["papers"]:
            known |= {k for k in (pp.get("arxiv_id"), pp["url"]) if k}
    incoming = load_json(args.json)
    incoming = incoming.get("papers", incoming) if isinstance(incoming, dict) else incoming
    added = 0
    for pp in incoming:
        if (pp.get("arxiv_id") and pp["arxiv_id"] in known) or pp["url"] in known:
            continue
        pp.setdefault("added", day.isoformat())
        doc["papers"].append(pp)
        known |= {k for k in (pp.get("arxiv_id"), pp["url"]) if k}
        added += 1
    doc["generated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    write_json(path, doc)
    print(f"{path.relative_to(repo.root)}: +{added} papers ({len(doc['papers'])} total)")
    return 0


def cmd_quarterly(repo: Repo, args) -> int:
    from . import quarterly
    q = args.quarter or quarterly.quarter_of(_day(args.date))
    try:
        _print(quarterly.draft(repo, q))
    except ValueError as e:
        print(f"error: {e}")
        return 1
    return 0


def cmd_inbox(repo: Repo, args) -> int:
    path = repo.p("inbox", f"{args.name}.md")
    if args.action == "show":
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        body = text.split("---", 1)[1].strip() if "---" in text else text.strip()
        print(body if body else "(empty)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(INBOX_TEMPLATES[args.name], encoding="utf-8")
        print(f"cleared {path.relative_to(repo.root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dsys", description="Personal development system toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="validate content, state, examples")
    s.add_argument("--examples", action="store_true", help="validate examples/ instead of content/")
    s.add_argument("--all", action="store_true", help="validate content and examples")
    s.set_defaults(fn=cmd_validate)

    sub.add_parser("rss", help="validate then write feeds/*.xml").set_defaults(fn=cmd_rss)
    s = sub.add_parser("build", help="validate, generate RSS and build _site/")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("history", help="rebuild derived history in state/")
    s.add_argument("action", choices=["rebuild"])
    s.set_defaults(fn=cmd_history)

    s = sub.add_parser("papers", help="mark arXiv candidates as seen (reviewed, not selected)")
    s.add_argument("action", choices=["mark-seen"])
    s.add_argument("ids", nargs="+")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_papers)

    s = sub.add_parser("candidates", help="print unseen fetched candidates")
    s.add_argument("kind", choices=["arxiv", "news", "youtube"])
    s.add_argument("--date")
    s.add_argument("--limit", type=int)
    s.add_argument("--offset", type=int, default=0)
    s.add_argument("--category", help="news: only this category (india, geopolitics, conflict_disaster, economy_markets, "
                                      "business_tech, science_health, climate_energy, society, explainers)")
    s.add_argument("--section", help=argparse.SUPPRESS)
    s.add_argument("--brief", action="store_true", help="arxiv: id/title/categories/signals only; news: no summaries")
    s.add_argument("--ranked", action="store_true", help="arxiv: code-ranked shortlist with interests and quality signals")
    s.add_argument("--ids", help="arxiv: comma-separated ids to print in full (abstracts)")
    s.add_argument("--trending-week", help="arxiv: the week's most voted papers (alphaXiv, Hugging Face), e.g. 2026-W48")
    s.set_defaults(fn=cmd_candidates)

    s = sub.add_parser("context", help="planning/dedup context for a generator prompt")
    s.add_argument("stream", choices=DAILY_STREAMS + ["weekly", "monthly"])
    s.add_argument("--date")
    s.add_argument("--period")
    s.set_defaults(fn=cmd_context)

    s = sub.add_parser("period", help="this/next week and month, with schedule load")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_period)

    s = sub.add_parser("daily", help="merge generated items into a day's file")
    s.add_argument("action", choices=["merge"])
    s.add_argument("stream", choices=DAILY_STREAMS)
    s.add_argument("--date")
    s.add_argument("--items", help="JSON file: list of items, or {items, notes, candidates_considered}")
    s.add_argument("--notes")
    s.add_argument("--generator")
    s.set_defaults(fn=cmd_daily)

    s = sub.add_parser("ideas", help="manage ideas & interests")
    isub = s.add_subparsers(dest="action", required=True)
    x = isub.add_parser("list"); x.add_argument("--status")
    x = isub.add_parser("show"); x.add_argument("id")
    x = isub.add_parser("due"); x.add_argument("period")
    x = isub.add_parser("add")
    x.add_argument("title"); x.add_argument("--description"); x.add_argument("--first-step"); x.add_argument("--estimate")
    x.add_argument("--scope", default="undecided", choices=["weekly", "monthly", "either", "undecided"])
    x.add_argument("--status", default="interested", choices=ideas_mod.IDEA_STATUSES)
    x.add_argument("--dimensions", help="comma-separated"); x.add_argument("--tags")
    x.add_argument("--origin", default="user", choices=["user", "system", "seed", "feedback"])
    x.add_argument("--week"); x.add_argument("--month"); x.add_argument("--date")
    x = isub.add_parser("status"); x.add_argument("id"); x.add_argument("status", choices=ideas_mod.IDEA_STATUSES)
    x.add_argument("--note"); x.add_argument("--date")
    x = isub.add_parser("schedule"); x.add_argument("id"); x.add_argument("--week"); x.add_argument("--month")
    x.add_argument("--next-week", action="store_true"); x.add_argument("--next-month", action="store_true")
    x.add_argument("--force", action="store_true"); x.add_argument("--note"); x.add_argument("--date")
    x = isub.add_parser("unschedule"); x.add_argument("id"); x.add_argument("--date")
    x = isub.add_parser("defer"); x.add_argument("id"); x.add_argument("--until"); x.add_argument("--note"); x.add_argument("--date")
    x = isub.add_parser("drop"); x.add_argument("id"); x.add_argument("--note"); x.add_argument("--not-interested", action="store_true"); x.add_argument("--date")
    x = isub.add_parser("resize"); x.add_argument("id"); x.add_argument("scope", choices=["weekly", "monthly", "either", "undecided"])
    x.add_argument("--note"); x.add_argument("--date")
    x = isub.add_parser("replace"); x.add_argument("id"); x.add_argument("title"); x.add_argument("--description"); x.add_argument("--date")
    x = isub.add_parser("note"); x.add_argument("id"); x.add_argument("text"); x.add_argument("--date")
    x = isub.add_parser("remove"); x.add_argument("id")
    s.set_defaults(fn=cmd_ideas)

    s = sub.add_parser("feedback", help="record and apply weekly/monthly feedback")
    fsub = s.add_subparsers(dest="action", required=True)
    x = fsub.add_parser("record")
    x.add_argument("--period", required=True); x.add_argument("--json", help="file with {entries, general} (sanitized; no raw text)")
    x.add_argument("--item"); x.add_argument("--status", choices=["completed", "partially_completed", "not_started",
                                                                   "skipped", "in_progress", "dropped"])
    x.add_argument("--decision", choices=["done", "drop", "reschedule", "reduce_scope", "modify", "split", "replace",
                                          "keep_in_progress", "none"])
    x.add_argument("--target", help="week/month for reschedule-like decisions (default: next period)")
    x.add_argument("--decision-note"); x.add_argument("--learned"); x.add_argument("--enjoyed")
    x.add_argument("--difficult")
    x.add_argument("--skip-reason", choices=["no_time", "too_long", "too_hard", "not_interesting", "other"]); x.add_argument("--notes")
    x.add_argument("--more"); x.add_argument("--less"); x.add_argument("--general-notes")
    x.add_argument("--interest", choices=["more", "same", "less", "not_interested"])
    x.add_argument("--difficulty-feedback", choices=["too_easy", "right", "too_hard"]); x.add_argument("--date")
    x = fsub.add_parser("apply"); x.add_argument("--period", required=True); x.add_argument("--force", action="store_true")
    x.add_argument("--date")
    s.set_defaults(fn=cmd_feedback)

    s = sub.add_parser("interests", help="edit config/interests.json lists (e.g. culture.active)")
    isub2 = s.add_subparsers(dest="action", required=True)
    isub2.add_parser("list")
    x = isub2.add_parser("find"); x.add_argument("value")
    x = isub2.add_parser("add"); x.add_argument("path"); x.add_argument("value")
    x.add_argument("--create", action="store_true", help="create the list inside an existing section")
    x = isub2.add_parser("remove"); x.add_argument("path"); x.add_argument("value")
    x = isub2.add_parser("move"); x.add_argument("src"); x.add_argument("dst"); x.add_argument("value")
    s.set_defaults(fn=cmd_interests)

    s = sub.add_parser("reading", help="weekly paper reading list: show, or add papers from a JSON file")
    s.add_argument("action", choices=["show", "add"])
    s.add_argument("--week", help="YYYY-Www (default: this week)")
    s.add_argument("--json", help="file with a list of papers (or {papers: [...]})")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_reading)


    s = sub.add_parser("quarterly", help="write the public quarterly review file with stats and topics filled in")
    s.add_argument("action", choices=["draft"])
    s.add_argument("--quarter", help="YYYY-Qn (default: current quarter)"); s.add_argument("--date")
    s.set_defaults(fn=cmd_quarterly)

    s = sub.add_parser("inbox", help="show or clear inbox/ideas.md or inbox/feedback.md")
    s.add_argument("action", choices=["show", "clear"])
    s.add_argument("name", choices=["ideas", "feedback"])
    s.set_defaults(fn=cmd_inbox)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(repo_from_env(), args)
