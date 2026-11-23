"""HTML fragments for items and packages, shared by RSS (content:encoded) and the site.

Fragments use plain semantic HTML so they read well in RSS readers that strip CSS.
Class names are hooks for the site's stylesheet only.
"""

from __future__ import annotations

import datetime as dt
import html
import re

from . import youtube as yt

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

DIMENSION_NAMES = {  # defaults; replaced from config/interests.json -> dimensions by configure()
    "research": "Research",
    "knowledge": "Knowledge",
    "world": "World",
    "people": "People & self",
    "culture": "Culture & life",
    "curiosity": "Curiosity",
}



DIMENSION_SHORT: dict[str, str] = {}  # compact labels (e.g. for the dial); falls back to the full name


def configure(repo) -> None:
    """Load dimension display names from config so forks can rename or add areas."""
    try:
        areas = repo.config("interests").get("dimensions", {})
    except FileNotFoundError:
        return
    if areas:
        DIMENSION_NAMES.clear()
        DIMENSION_SHORT.clear()
        for k, v in areas.items():
            DIMENSION_NAMES[k] = v.get("name", k) if isinstance(v, dict) else k.replace("_", " ").capitalize()
            DIMENSION_SHORT[k] = (v.get("short") if isinstance(v, dict) else None) or DIMENSION_NAMES[k]


TIME_LABEL = {"10-30m": "10 to 30 min", "30-60m": "30 to 60 min", "1-2h": "1 to 2 hours", "few_hours": "a few hours",
              "real_world_practice": "real-world practice"}


def esc(s) -> str:
    return html.escape(_CTRL.sub("", str(s if s is not None else "")), quote=True)


def a(url: str, text: str | None = None) -> str:
    return f'<a href="{esc(url)}">{esc(text or url)}</a>'


def human(s) -> str:
    return esc(str(s).replace("_", " "))


def nice_date(iso: str, with_year: bool = False) -> str:
    try:
        d = dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return esc(iso)
    return d.strftime(f"%-d %b{' %Y' if with_year else ''}")


def meta(*parts) -> str:
    """A one-line description of an item, written as a phrase rather than a tag soup."""
    bits = [p for p in parts if p]
    return f'<p class="meta">{", ".join(bits)}</p>' if bits else ""


def _field(label: str, value, cls: str = "") -> str:
    if not value:
        return ""
    c = f' class="{cls}"' if cls else ""
    return f"<p{c}><strong>{esc(label)}.</strong> {esc(value)}</p>"


def _list(label: str, values, cls: str = "") -> str:
    if not values:
        return ""
    c = f' class="{cls}"' if cls else ""
    return f"<p{c}><strong>{esc(label)}</strong></p><ul>" + "".join(f"<li>{esc(v)}</li>" for v in values) + "</ul>"


def dimension_line(item) -> str:
    ps = item.get("dimensions") or []
    if not ps:
        return ""
    spans = "".join(f'<span class="pl pl-{esc(p)}">{esc(DIMENSION_NAMES.get(p, p))}</span>' for p in ps)
    return f'<p class="areas">{spans}</p>'


def _source(s: dict) -> str:
    if not s:
        return ""
    when = f" ({nice_date(s['published'])})" if s.get("published") else ""
    return f"{a(s['url'], s['name'])}{when}"


def _resources(label: str, res) -> str:
    if not res:
        return ""
    lis = []
    for r in res:
        title = a(r["url"], r["title"]) if r.get("url") else esc(r["title"])
        by = ", ".join(esc(x) for x in (r.get("creator"), r.get("year"), r.get("chapters")) if x)
        note = f". {esc(r['note'])}" if r.get("note") else ""
        lis.append(f"<li>{title}{', ' + by if by else ''} <span class='kind'>({human(r['type'])})</span>{note}</li>")
    return f"<p><strong>{esc(label)}</strong></p><ul class='resources'>{''.join(lis)}</ul>"


def cross_domain_line(item) -> str:
    cd = item.get("cross_domain")
    if not cd:
        return ""
    return (f'<p class="cross"><strong>Connects {esc(" and ".join(cd["fields"]))}.</strong> '
            f'{esc(cd["connection"])}</p>')


# --- daily items ---------------------------------------------------------------
KIND_LABEL = {"ai_deep_dive": "AI deep dive", "non_ai_deep_dive": "non-AI deep dive", "user_idea": "your idea",
              "ai_study": "AI study"}
TIER_LABEL = {"established": "established", "growth": "growth", "exploration": "exploration"}
MODE_LABEL = {"learn": "learn", "practise": "practise", "create": "make something", "experience": "go and experience",
              "reflect": "reflect"}


def tags_line(tags) -> str:
    return "<p class='tags'>" + "".join(f"<span class='tag'>{esc(t)}</span>" for t in tags) + "</p>" if tags else ""


def arxiv_item(p: dict) -> str:
    links = a(p["url"], f"arXiv:{p['arxiv_id']}") + (f", {a(p['pdf_url'], 'PDF')}" if p.get("pdf_url") else "")
    hf = f", {p['hf_upvotes']} upvotes on Hugging Face" if p.get("hf_upvotes") else ""
    return "".join([
        tags_line(p["tags"]),
        f'<p class="authors">{esc(", ".join(p["authors"][:8]))}{" et al." if len(p["authors"]) > 8 else ""}</p>',
        f'<blockquote class="abstract">{esc(p["abstract"])}</blockquote>',
        f'<p class="links">{links}. {esc(p["research_area"])}, {esc(" ".join(p["categories"]))}, '
        f'submitted {nice_date(p["submitted"])}{hf}</p>',
    ])


def reading_list(doc: dict) -> str:
    out = []
    for pp in doc["papers"]:
        by = f"<p class='authors'>{esc(', '.join(pp['authors'][:6]))}</p>" if pp.get("authors") else ""
        note = f"<p>{esc(pp['note'])}</p>" if pp.get("note") else ""
        out.append(f"<article class='entry'><h3>{a(pp['url'], pp['title'])}</h3>{tags_line(pp['tags'])}{by}{note}"
                   f"<p class='links'>{esc(pp['source'].replace('_', ' '))}, added {nice_date(pp['added'])}</p></article>")
    return "".join(out) or "<p class='empty'>No papers yet.</p>"


def update_item(u: dict) -> str:
    srcs = [u["source"]] + u.get("additional_sources", [])
    return "".join([
        meta(human(u["kind"]), esc(u.get("research_area")), nice_date(u["published"])),
        f"<p>{esc(u['what_happened'])}</p>",
        _field("Why it matters", u["why_it_matters"]),
        _field("What to watch", u["what_to_watch"]),
        _field("Uncertain", u.get("uncertainty"), "uncertain"),
        f'<p class="source">Source: {"; ".join(_source(s) for s in srcs)}</p>',
    ])


def world_item(w: dict) -> str:
    deeper = "".join([
        _list("Confirmed", w["confirmed_facts"]),
        _field("Context", w.get("context")),
        _field("Analysis (interpretation, not fact)", w.get("analysis")),
    ])
    return "".join([
        meta(human(w["topic"]), esc(", ".join(w["regions"])), nice_date(w["published"])),
        f"<p>{esc(w['what_happened'])}</p>",
        _field("Why it matters", w["why_it_matters"]),
        _field("What to watch", w["what_to_watch"]),
        _field("Uncertain", w.get("uncertainty"), "uncertain"),
        f'<details><summary>Facts, context and analysis</summary>{deeper}</details>' if deeper else "",
        f'<p class="source">Sources: {"; ".join(_source(s) for s in w["sources"])}</p>',
    ])


def recommendation_item(r: dict) -> str:
    return "".join([
        meta(esc(r.get("creator")), human(r["type"]), esc(r["category"]),
             esc(r.get("duration") or r.get("time_required")), TIER_LABEL.get(r.get("tier"))),
        f"<p>{esc(r['description'])}</p>",
        f'<p class="why">{esc(r["why_recommended"])}</p>',
        cross_domain_line(r) or _field("Connects", r.get("connection_to_interests")),
        _field("You might get", r.get("what_i_might_get_from_it")),
        f'<p class="links">{a(r["url"], "Open")}</p>' if r.get("url") else "",
        dimension_line(r),
    ])


def video_item(v: dict, embed: bool = True) -> str:
    vid = v["video_id"]
    watch = v["url"]
    thumb = v.get("thumbnail") or yt.thumbnail_url(vid)
    parts = []
    if embed:
        parts.append(
            f'<p><iframe width="315" height="560" src="{esc(yt.embed_url(vid))}" title="{esc(v["title"])}" '
            f'frameborder="0" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" '
            f'referrerpolicy="strict-origin-when-cross-origin" '
            f'allowfullscreen="allowfullscreen" loading="lazy"></iframe></p>')
    parts.append(f'<p><a href="{esc(watch)}"><img src="{esc(thumb)}" alt="{esc(v["title"])}" width="320" loading="lazy"/></a></p>')
    dur = f", {v['duration_seconds']} s" if v.get("duration_seconds") else ""
    kind = {"short": "Short", "short_form": "short video", "unknown": "short video"}.get(v.get("format"), "video")
    parts.append(f"<p>{a(watch, 'Watch on YouTube')}. {esc(v['channel']['name'])}, {kind}{dur}</p>")
    parts.append(f'<p class="why">{esc(v["why_it_matches"])}</p>')
    if v.get("description"):
        parts.append(f"<p>{esc(v['description'])}</p>")
    parts.append(meta(esc(v["category"]), esc(v["topic"])))
    return "".join(parts)


def _line(l: dict) -> str:
    rom = f' <span class="rom">{esc(l["romanization"])}</span>' if l.get("romanization") else ""
    note = f' <span class="meta">({esc(l["note"])})</span>' if l.get("note") else ""
    return f'<li><span class="native">{esc(l["text"])}</span>{rom}: {esc(l["meaning"])}{note}</li>'


def _questions(qs: list) -> str:
    out = []
    for i, q in enumerate(qs, 1):
        hint = f"<p class='meta'>Hint: {esc(q['hint'])}</p>" if q.get("hint") else ""
        out.append(f"<li>{esc(q['question'])}{hint}<details><summary>Answer</summary><p>{esc(q['answer'])}</p></details></li>")
    return "<ol class='qs'>" + "".join(out) + "</ol>"


def language_pack(p: dict) -> str:
    res = _resources("Listen", [p["resource"]]) if p.get("resource") else ""
    return "".join([
        meta(esc(p["language"].capitalize()), esc(p["theme"]), f"{p['minutes']} min"),
        "<p><strong>Phrases</strong></p><ul class='lang'>" + "".join(_line(l) for l in p["phrases"]) + "</ul>",
        "<p><strong>Dialogue</strong></p><ul class='lang'>" + "".join(_line(l) for l in p["dialogue"]) + "</ul>",
        "<p><strong>Practice</strong></p>" + _questions(p["practice"]),
        _field("Say it aloud today", p.get("say_aloud")),
        res,
    ])


def language_lessons(block: dict) -> str:
    out = ["<h2>Languages</h2>"]
    for ls in block.get("lessons", []):
        out.append(f"<section class='activity'><h3>{esc(ls['language'].capitalize())}: {esc(ls['title'])}</h3>"
                   f"<p>{esc(ls['explanation'])}</p>"
                   "<p><strong>Examples</strong></p><ul class='lang'>" + "".join(_line(l) for l in ls["examples"]) + "</ul>"
                   "<p><strong>Questions</strong></p>" + _questions(ls["questions"])
                   + _list("Practice", ls["practice"]) + _resources("Resources", ls.get("resources")) + "</section>")
    return "".join(out)


def language_plans(block: dict) -> str:
    out = ["<h2>Languages this month</h2>"]
    for pl in block.get("plans", []):
        weeks = "".join(f"<li><strong>Week {w['week']}: {esc(w['focus'])}</strong>"
                        + ("<ul>" + "".join(f"<li>{esc(t)}</li>" for t in w.get("tasks", [])) + "</ul>" if w.get("tasks") else "")
                        + "</li>" for w in pl["weeks"])
        out.append(f"<section class='activity'><h3>{esc(pl['language'].capitalize())}</h3>"
                   f"{_field('Goal', pl['goal'])}<ol class='weeks'>{weeks}</ol>{_resources('Resources', pl['resources'])}</section>")
    return "".join(out)


ITEM_RENDERERS = {
    "arxiv": arxiv_item,
    "research_updates": update_item,
    "world": world_item,
    "discovery": recommendation_item,
    "youtube_shorts": video_item,
    "language": language_pack,
}


# --- packages --------------------------------------------------------------------
def activity(it: dict, heading: str = "h3") -> str:
    origin = {"user_idea": "your idea", "continued": "continued from before"}.get(it["origin"])
    out = [f"<{heading}>{esc(it['title'])}</{heading}>",
           meta((KIND_LABEL.get(it["category"]) or human(it["category"])) if it["category"] != "user_idea" else None,
                TIER_LABEL.get(it.get("tier")), MODE_LABEL.get(it.get("mode")), TIME_LABEL.get(it["time_estimate"], esc(it["time_estimate"])),
                esc(it.get("difficulty")), origin),
           f"<p>{esc(it['description'])}</p>",
           f'<p class="why">{esc(it["why"])}</p>',
           cross_domain_line(it),
           _field("Then", it.get("then"), "then")]
    ex = it.get("explain")
    if ex:
        inner = "".join(_field(k.replace("_", " ").capitalize(), ex.get(k))
                        for k in ("what", "why", "how", "limitations", "research_relevance"))
        inner += _list("Components", ex.get("components"))
        out.append(f"<details><summary>What, why, how</summary>{inner}</details>")
    pp = it.get("paper")
    if pp:
        out.append(f"<p><strong>Paper.</strong> {a(pp['url'], pp['title'])}, {esc(', '.join(pp['authors']))}, {pp['year']}</p>")
        out.append(_field("Notice", pp.get("what_to_notice")))
        out.append(_field("Reading time", pp.get("reading_time")))
    if it.get("steps"):
        out.append("<ol class='steps'>" + "".join(f"<li>{esc(s)}</li>" for s in it["steps"]) + "</ol>")
    hints = it.get("hints")
    if hints:
        hs = "".join(f"<details class='hint'><summary>Hint {i}</summary><p>{esc(h)}</p></details>"
                     for i, h in enumerate(hints, 1))
        out.append(f"<div class='hints'><p class='meta'>Stuck? Open one hint at a time.</p>{hs}</div>")
    out.append(_resources("Resources", it.get("resources")))
    out.append(dimension_line(it))
    return "".join(out)


LOAD_TEXT = {"light": "a busy stretch, so it's kept light", "normal": "an ordinary week",
             "free": "some free time, so there's room to go deeper"}


def weekly_package(doc: dict) -> str:
    out = [f'<p class="lede">{esc(doc["intro"])}</p>',
           f"<p class='meta'>{nice_date(doc['start_date'])} to {nice_date(doc['end_date'], True)}, "
           f"planned for {LOAD_TEXT.get(doc['load'], doc['load'])}. All optional.</p>"]
    out += [f'<section class="activity e-{(it.get("dimensions") or ["research"])[0]}">{activity(it)}</section>'
            for it in doc["items"]]
    if doc.get("language"):
        out.append(language_lessons(doc["language"]))
    if doc.get("reflection_prompt"):
        out.append(f"<h3>If you feel like reflecting</h3><p>{esc(doc['reflection_prompt'])}</p>")
    return "".join(out)


def project(pj: dict, heading: str = "h3") -> str:
    out = [f"<{heading}>{esc(pj['title'])}</{heading}>",
           meta(KIND_LABEL.get(pj["kind"]) or human(pj["kind"]), TIER_LABEL.get(pj.get("tier")), esc(pj["time_estimate"])),
           f'<p class="why">{esc(pj["why"])}</p>',
           _field("Goal", pj["objective"]),
           _field("Before you start", ", ".join(pj.get("prerequisites", [])))]
    if pj.get("primary_resource"):
        out.append(_resources("Main resource", [pj["primary_resource"]]))
    weeks = "".join(
        f"<li><strong>Week {w['week']}: {esc(w['focus'])}</strong>"
        + ("<ul>" + "".join(f"<li>{esc(t)}</li>" for t in w.get("tasks", [])) + "</ul>" if w.get("tasks") else "")
        + "</li>" for w in pj["weeks"])
    out.append(f"<ol class='weeks'>{weeks}</ol>")
    out += [_resources("Resources", pj.get("resources")), _list("Exercises", pj.get("exercises")),
            _field("Make", pj["deliverable"]), _field("Done when", pj["definition_of_done"]),
            _field("Pull it together", pj.get("final_synthesis")),
            _field("If the month gets busy", pj.get("light_version"), "light"),
            _field("Possible next step (not scheduled)", pj.get("continuation")), dimension_line(pj)]
    return "".join(out)


def monthly_package(doc: dict) -> str:
    out = [f'<p class="lede">{esc(doc["intro"])}</p>',
           f"<p class='meta'>Planned for {LOAD_TEXT.get(doc['load'], doc['load']).replace('week', 'month')}. "
           "Pick one, or none.</p>"]
    out += [f'<section class="activity e-{(pj.get("dimensions") or ["research"])[0]}">{project(pj)}</section>'
            for pj in doc["items"]]
    if doc.get("language"):
        out.append(language_plans(doc["language"]))
    if doc.get("reflection_prompts"):
        out.append(_list("If you feel like reflecting", doc["reflection_prompts"]))
    return "".join(out)
