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
    spans = "<span class='sep'> · </span>".join(f'<span class="pl pl-{esc(p)}">{esc(DIMENSION_NAMES.get(p, p))}</span>' for p in ps)
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


# --- daily page structure (shared by the site and the daily RSS digest) ---------------
# --- the parts every page is split into (each part has its own URL) -------------------
# Daily: research / news / exploration. Weekly, monthly, quarterly: research / knowledge / exploration.
DAILY_PARTS = [  # (key, heading, streams). "reading" is this week's reading list, shown every day.
    ("research", "Research", ["arxiv", "research_updates", "reading"]),
    ("news", "News", ["world"]),
    ("exploration", "Exploration", ["discovery", "youtube_shorts", "language"]),
]
DAILY_GROUPS = DAILY_PARTS  # old name
PERIOD_PARTS = [("research", "Research"), ("knowledge", "Knowledge"), ("exploration", "Exploration")]
DISCOVERY_SECTIONS = [  # (key, label, recommendation types)
    ("podcasts", "Podcasts", {"podcast"}),
    ("videos", "Videos and lectures", {"video", "lecture", "documentary", "playlist", "course"}),
    ("reads", "Reads", {"article", "paper", "book", "website"}),
    ("culture", "Watch and listen", {"film", "series", "anime", "album", "music", "artwork"}),
    ("try", "Try, make or go", {"place", "experience", "project", "tool", "idea", "person", "other"}),
]


def group_discovery(items: list[dict]) -> list[tuple[str, str, list[dict]]]:
    out = []
    for key, label, types in DISCOVERY_SECTIONS:
        its = [r for r in items if r.get("type") in types]
        if its:
            out.append((key, label, its))
    known = set().union(*(t for _, _, t in DISCOVERY_SECTIONS))
    rest = [r for r in items if r.get("type") not in known]
    if rest:
        out.append(("other", "More", rest))
    return out


WEEKLY_SECTIONS = [  # (key, label, what belongs, part)
    ("research_practice", "Research practice", "a fundamentals problem, derivation, critique or experiment-design exercise", "research"),
    ("research_reading", "Research reading", "a paper or concept worth studying properly", "research"),
    ("questions", "Questions to think about", "maths, probability, physics or science puzzles with hints", "knowledge"),
    ("things_to_know", "Things to know and talk about", "anything worth knowing and bringing up in conversation", "knowledge"),
    ("world", "Understanding the world", "a place, system or long-running story explained", "knowledge"),
    ("culture", "Culture", "music, art, books, films, anime and the people behind them", "exploration"),
    ("people_self", "People and self", "practice with real people: listening, conversation, courage, leadership", "exploration"),
    ("curiosity_making", "Curiosity and making", "hobbies, experiments, things to build or try", "exploration"),
]
_CATEGORY_SECTION = {"research_fundamentals": "research_practice", "ai_study": "research_reading",
                     "paper": "research_reading", "question": "questions", "talking_point": "things_to_know",
                     "new_knowledge": "things_to_know", "people": "people_self", "teaching": "people_self",
                     "reflection": "people_self", "culture": "culture", "making": "curiosity_making",
                     "random_curiosity": "curiosity_making", "world_understanding": "world"}
_OLD_WEEKLY = {"talking_points": "things_to_know"}
SECTION_PART = {k: part for k, _, _, part in WEEKLY_SECTIONS}


def weekly_section(it: dict) -> str:
    sec = it.get("section")
    if sec:
        return _OLD_WEEKLY.get(sec, sec)
    if it.get("category") == "user_idea":
        return "research_reading" if "research" in (it.get("dimensions") or []) else "curiosity_making"
    return _CATEGORY_SECTION.get(it.get("category"), "curiosity_making")


def weekly_part(it: dict) -> str:
    return SECTION_PART[weekly_section(it)]


MONTHLY_SECTIONS = [
    ("research", "Research deep dive"),
    ("knowledge", "Knowledge deep dive"),
    ("exploration", "Exploration deep dive"),
]
_KIND_SECTION = {"ai_deep_dive": "research", "research_exploration": "research", "non_ai_deep_dive": "knowledge",
                 "exploration_theme": "exploration", "people": "exploration", "teaching": "exploration",
                 "creative_project": "exploration", "hobby_skill": "exploration"}
_OLD_MONTHLY = {"culture_life": "exploration", "people_self": "exploration", "making": "exploration"}


def monthly_section(pj: dict) -> str:
    if pj.get("section"):
        return _OLD_MONTHLY.get(pj["section"], pj["section"])
    if pj.get("kind") == "user_idea":
        return "research" if "research" in (pj.get("dimensions") or []) else "knowledge"
    return _KIND_SECTION.get(pj.get("kind"), "knowledge")
WORLD_SECTIONS = [  # (key, label): news categories, shown in this order
    ("india", "India"),
    ("geopolitics", "Geopolitics and international relations"),
    ("leadership", "Leadership changes"),
    ("conflict_disaster", "Conflicts and disasters"),
    ("economy_markets", "Economy, finance and markets"),
    ("business", "Business and companies"),
    ("technology", "Technology and AI"),
    ("science_space", "Science and space"),
    ("health", "Health"),
    ("climate_energy", "Climate, energy and environment"),
    ("society", "Society, demographics and migration"),
    ("explainers", "Explainers and analysis"),
]
_TOPIC_SECTION = {"economics": "economy_markets", "finance": "economy_markets", "trade": "economy_markets",
                  "business": "business", "technology": "technology",
                  "science": "science_space", "health": "health",
                  "environment": "climate_energy", "climate": "climate_energy", "energy": "climate_energy",
                  "society": "society", "culture": "society", "migration": "society", "demographics": "society",
                  "conflict": "conflict_disaster", "disaster": "conflict_disaster",
                  "geopolitics": "geopolitics", "international_relations": "geopolitics"}
_OLD_SECTION = {"world": "geopolitics", "science_tech": "science_space", "business_tech": "technology",
                "science_health": "science_space"}


def world_section(w: dict) -> str:
    """The item's news category, or one derived from its topic and regions for older items."""
    sec = w.get("section")
    if sec:
        return _OLD_SECTION.get(sec, sec)
    india = any(r.lower() == "india" for r in w.get("regions", []))
    if india and w.get("topic") in ("politics", "society", "other", None):
        return "india"
    return _TOPIC_SECTION.get(w.get("topic"), "india" if india else "geopolitics")


def group_world(items: list[dict], briefs: list[dict] | None = None) -> list[tuple[str, str, list[dict]]]:
    """Explained items by category. With briefs, categories that only have briefs are included too."""
    by: dict[str, list] = {}
    for w in items:
        by.setdefault(world_section(w), []).append(w)
    keys = set(by) | {_OLD_SECTION.get(b["section"], b["section"]) for b in (briefs or [])}
    return [(k, label, by.get(k, [])) for k, label in WORLD_SECTIONS if k in keys]


def world_briefs(briefs: list[dict], section: str) -> str:
    """'Also in the news': one line per headline, linking straight to the article."""
    rows = [b for b in briefs or [] if _OLD_SECTION.get(b["section"], b["section"]) == section]
    if not rows:
        return ""
    return ("<p class='also'><strong>Also in the news</strong></p><ul class='briefs'>" + "".join(
        f"<li>{a(b['url'], b['title'])} <span class='meta'>{esc(b['source'])}</span>"
        + (f"<br/>{esc(b['line'])}" if b.get("line") else "") + "</li>" for b in rows) + "</ul>")


# --- daily items ---------------------------------------------------------------
KIND_LABEL = {"ai_deep_dive": "AI deep dive", "non_ai_deep_dive": "non-AI deep dive", "user_idea": "your idea",
              "ai_study": "AI study", "question": "question", "talking_point": "talking point"}
TIER_LABEL = {"established": "established", "growth": "growth", "exploration": "exploration"}
MODE_LABEL = {"learn": "learn", "practise": "practise", "create": "make something", "experience": "go and experience",
              "reflect": "reflect"}


def tags_line(tags) -> str:
    """Tags as pills on the site; the ' · ' separators keep them readable in RSS readers that drop CSS."""
    if not tags:
        return ""
    return "<p class='tags'>" + "<span class='sep'> · </span>".join(f"<span class='tag'>{esc(t)}</span>" for t in tags) + "</p>"


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


def weekly_package(doc: dict, part: str | None = None) -> str:
    out = [f'<p class="lede">{esc(doc["intro"])}</p>',
           f"<p class='meta'>{nice_date(doc['start_date'])} to {nice_date(doc['end_date'], True)}, "
           f"planned for {LOAD_TEXT.get(doc['load'], doc['load'])}. All optional.</p>"]
    for key, label, _, sec_part in WEEKLY_SECTIONS:
        if part and sec_part != part:
            continue
        its = [it for it in doc["items"] if weekly_section(it) == key]
        if its:
            out.append(f"<h2 id='{key}'>{esc(label)}</h2>")
            out += [f'<section class="activity e-{(it.get("dimensions") or ["research"])[0]}">{activity(it)}</section>'
                    for it in its]
    if doc.get("language") and part in (None, "exploration"):
        out.append(language_lessons(doc["language"]))
    if doc.get("reflection_prompt") and part in (None, "exploration"):
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


def monthly_package(doc: dict, part: str | None = None) -> str:
    out = [f'<p class="lede">{esc(doc["intro"])}</p>',
           f"<p class='meta'>Planned for {LOAD_TEXT.get(doc['load'], doc['load']).replace('week', 'month')}. "
           "Pick one, or none.</p>"]
    for key, label in MONTHLY_SECTIONS:
        if part and key != part:
            continue
        pjs = [pj for pj in doc["items"] if monthly_section(pj) == key]
        if pjs:
            out.append(f"<h2 id='{key}'>{esc(label)}</h2>")
            out += [f'<section class="activity e-{(pj.get("dimensions") or ["research"])[0]}">{project(pj)}</section>'
                    for pj in pjs]
    if doc.get("language") and part in (None, "exploration"):
        out.append(language_plans(doc["language"]))
    if doc.get("reflection_prompts") and part in (None, "exploration"):
        out.append(_list("If you feel like reflecting", doc["reflection_prompts"]))
    return "".join(out)


STAT_LABEL = {"arxiv": "papers on the radar", "reading_list_papers": "reading-list papers",
              "research_updates": "research updates", "discovery": "discoveries", "language": "language packs",
              "world": "news items", "youtube_shorts": "shorts", "weekly_packages": "weekly packages",
              "weekly_items": "weekly items", "monthly_packages": "monthly packages", "monthly_items": "monthly items"}


def quarterly_stats(doc: dict) -> str:
    st = doc["stats"]
    counts = st["counts"]
    order = ["arxiv", "reading_list_papers", "research_updates", "discovery", "weekly_items", "monthly_items",
             "language", "world", "youtube_shorts"]
    rows = "".join(f"<li><strong>{counts[k]}</strong> {esc(STAT_LABEL.get(k, human(k)))}</li>" for k in order if counts.get(k))
    tiers = ", ".join(f"{n} {t}" for t, n in st["discovery_by_tier"].items())
    news = ", ".join(f"{human(k)} ({n})" for k, n in (st.get("news_by_category") or {}).items())
    tags = ", ".join(f"{t} ({n})" for t, n in st["top_paper_tags"])
    areas = ", ".join(f"{t} ({n})" for t, n in st["top_research_areas"])
    return "".join([f"<p class='meta'>{nice_date(doc['from'], True)} to {nice_date(doc['to'], True)}, "
                    f"{st['days_with_content']} days with content</p>",
                    "<h2>In numbers</h2>", f"<ul class='stats'>{rows}</ul>" if rows else "<p class='empty'>No content yet.</p>",
                    _field("Paper tags", tags), _field("Research areas", areas),
                    _field("News by category", news), _field("Discovery by tier", tiers)])


def quarterly_part(doc: dict, part: str) -> str:
    pt = doc["parts"][part]
    out = [f'<p class="lede">{esc(pt["summary"])}</p>' if pt["summary"] else "<p class='empty'>Nothing in this part this quarter.</p>"]
    for kind, label in (("monthly", "Monthly deep dives"), ("weekly", "Weekly topics")):
        group = [t for t in pt["topics"] if t["kind"] == kind]
        if group:
            out.append(f"<h2>{label}</h2><ul class='topics'>" + "".join(
                f"<li><strong>{a(t['url'], t['title']) if t.get('url') else esc(t['title'])}</strong>"
                f" <span class='meta'>({esc(t['period'])})</span><br/>{esc(t['about'])}</li>" for t in group) + "</ul>")
    return "".join(out)


def quarterly_review(doc: dict, part: str | None = None) -> str:
    """One part, or (part=None) the overview: every part's summary plus the numbers."""
    if part:
        return quarterly_part(doc, part)
    out = []
    for key, label in PERIOD_PARTS:
        summ = doc["parts"][key]["summary"]
        if summ:
            out.append(f"<h2>{esc(label)}</h2><p>{esc(summ)}</p>")
    return "".join(out) + quarterly_stats(doc)
