"""Feed HTML that looks the same, clean and calm, in every RSS reader.

Readers drop stylesheets and scripts, so the look comes from two things only:

* one structure for every entry: section heading, entry title, a quiet meta line, the text, then
  "Why it matters" and the idea behind it where there is one;
* inline styles added at the end by polish(): a system font stack, a type scale, spacing, quiet
  meta lines and soft rules. No text colours are set, so light and dark reader themes both work,
  and a reader that strips styles still shows clean semantic HTML.
"""
from __future__ import annotations

import datetime as dt
import re

from . import render
from .render import a, esc

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'Noto Sans',"
        "'Noto Sans Devanagari','Noto Sans JP',sans-serif")
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
RULE = "rgba(127,127,127,.28)"
ACCENT = "#b08d3c"
QUIET = "font-size:.86em;opacity:.72;margin:0 0 .55em;line-height:1.45"

# (tag, class or None) -> inline style. The first match wins; class-specific rules come first.
STYLES = [
    ("p", "kicker", "font-size:.78em;letter-spacing:.06em;text-transform:uppercase;opacity:.65;margin:0 0 .3em"),
    ("p", "lede", "font-size:1.08em;line-height:1.55;margin:.2em 0 1.1em"),
    ("p", "meta", QUIET), ("p", "authors", QUIET), ("p", "links", QUIET), ("p", "source", QUIET),
    ("p", "tags", QUIET), ("p", "yt-link", "font-size:.8em;opacity:.8;margin:.3em 0 1em"), ("p", "site", QUIET),
    ("p", "why", f"margin:.45em 0 .7em;padding:.05em 0 .05em .8em;border-left:3px solid {RULE}"),
    ("p", "also", "margin:1em 0 .3em;font-size:.9em"),
    ("p", "more", "font-size:.95em;margin:1.2em 0 .4em;font-weight:600"),
    ("div", "lesson", f"margin:.7em 0 .9em;padding:.65em .9em;border-left:3px solid {ACCENT};"
                      "background:rgba(176,141,60,.09);border-radius:0 6px 6px 0"),
    ("div", "yt", "margin:.6em 0 .2em"),
    ("div", "entry", "margin:0 0 1.5em"), ("article", None, "margin:0 0 1.5em"), ("section", None, "margin:0 0 1.5em"),
    ("details", "abs", "margin:.2em 0 .8em"),
    ("summary", None, "cursor:pointer;font-size:.86em;opacity:.8;margin:.1em 0 .3em"),
    ("blockquote", None, f"margin:.5em 0 .8em;padding:.1em 0 .1em .9em;border-left:3px solid {RULE};font-size:.95em"),
    ("ul", "briefs", "margin:.3em 0 1em;padding-left:1.1em;font-size:.95em"),
    ("ul", None, "margin:.35em 0 .9em;padding-left:1.25em"), ("ol", None, "margin:.35em 0 .9em;padding-left:1.4em"),
    ("li", None, "margin:.3em 0;line-height:1.5"),
    ("h1", None, "font-size:1.45em;line-height:1.25;margin:.2em 0 .6em"),
    ("h2", None, f"font-size:1.22em;line-height:1.3;margin:1.7em 0 .7em;padding-bottom:.3em;border-bottom:1px solid {RULE}"),
    ("h3", None, "font-size:1.04em;line-height:1.35;margin:1.25em 0 .3em"),
    ("h4", "sub-h", "font-size:.8em;letter-spacing:.06em;text-transform:uppercase;opacity:.7;margin:1.5em 0 .5em"),
    ("h4", None, "font-size:1em;line-height:1.4;margin:1.2em 0 .3em"),
    ("h5", None, "font-size:1em;margin:1.1em 0 .3em"),
    ("p", None, "margin:0 0 .65em;line-height:1.6"),
    ("hr", None, f"border:0;border-top:1px solid {RULE};margin:1.8em 0"),
    ("img", None, "max-width:100%;height:auto;border-radius:6px"),
    ("code", None, f"font-family:{MONO};font-size:.9em"),
    ("table", None, "border-collapse:collapse;margin:.6em 0 1em;font-size:.95em"),
    ("th", None, f"text-align:left;padding:.3em .6em;border-bottom:1px solid {RULE}"),
    ("td", None, f"padding:.3em .6em;border-bottom:1px solid {RULE}"),
]
_OPEN = re.compile(r"<(?P<tag>[a-zA-Z][a-zA-Z0-9]*)(?P<attrs>(?:\s[^<>]*?)?)(?P<end>/?)>")
_CLASS = re.compile(r"""\sclass=(["'])(.*?)\1""")


def polish(html: str) -> str:
    """Add the inline styles and wrap the body in the font stack. Tags that already carry a style
    (the YouTube player) keep theirs; MathML is left alone."""
    def style(m: re.Match) -> str:
        tag, attrs = m.group("tag").lower(), m.group("attrs") or ""
        if " style=" in attrs or tag in ("math", "a", "iframe", "span", "strong", "em", "br", "sub", "sup"):
            return m.group(0)
        cm = _CLASS.search(attrs)
        classes = set(cm.group(2).split()) if cm else set()
        for t, c, css in STYLES:
            if t == tag and (c is None or c in classes):
                return f'<{m.group("tag")}{attrs} style="{css}"{m.group("end")}>'
        return m.group(0)
    body = _OPEN.sub(style, html)
    return f'<div style="font-family:{FONT};font-size:16px;line-height:1.6;max-width:44em">{body}</div>'


# --- the daily parts ----------------------------------------------------------------------------

def header(site: dict, date: str, part: str, label: str) -> str:
    day = dt.date.fromisoformat(date).strftime("%A %-d %B %Y")
    url = f"{site['base_url']}/daily/{date}/{part}.html"
    return (f"<p class='kicker'>{esc(site['title'])} · {esc(label)}</p>"
            f"<p class='site'>{esc(day)} · {a(url, 'Open on the site')}</p>")


def frame(site: dict, kicker: str, when: str, url: str, body: str) -> str:
    """The same header and footer for weekly, monthly, quarterly and reading entries."""
    return (f"<p class='kicker'>{esc(site['title'])} · {esc(kicker)}</p>"
            f"<p class='site'>{esc(when)} · {a(url, 'Open on the site')}</p>{body}"
            f"<hr/><p class='site'>{a(url, 'Read this on the site')}</p>")


def footer(site: dict, date: str, part: str) -> str:
    return f"<hr/><p class='site'>{a(site['base_url'] + f'/daily/{date}/{part}.html', 'Read this on the site')}</p>"


def _meta(*bits) -> str:
    bits = [b for b in bits if b]
    return f"<p class='meta'>{' · '.join(bits)}</p>" if bits else ""


def _why(label: str, text: str | None) -> str:
    return f"<p><strong>{esc(label)}.</strong> {esc(text)}</p>" if text else ""


def _authors(p: dict, n: int = 4) -> str:
    au = p.get("authors") or []
    return esc(", ".join(au[:n])) + (" et al." if len(au) > n else "")


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def paper(p: dict, full: bool = True) -> str:
    title = f"<h3>{a(p['url'], p['title'])}</h3>"
    aff = esc("; ".join(p["affiliations"][:3])) if p.get("affiliations") else ""
    meta = _meta(_authors(p), aff, esc(", ".join(p.get("tags", []))))
    abstract = f"<blockquote>{esc(p['abstract'])}</blockquote>" if p.get("abstract") else ""
    return f"<div class='entry'>{title}{meta}{abstract}</div>"


def update(u: dict) -> str:
    src = u.get("source") or {}
    return (f"<div class='entry'><h3>{a(src.get('url'), u['title'])}</h3>"
            f"{_meta(esc(src.get('name')), render.human(u.get('kind', '')), render.nice_date(u.get('published', '')))}"
            f"<p>{esc(u['what_happened'])}</p>{_why('Why it matters', u.get('why_it_matters'))}</div>")


def story(w: dict) -> str:
    src = (w.get("sources") or [{}])[0]
    ls = w.get("lesson")
    lesson = (f"<div class='lesson'><p><strong>The idea behind it: {esc(ls['concept'])}.</strong> {esc(ls['explanation'])}"
              + (f" {a(ls['learn_more']['url'], ls['learn_more']['title'])}" if ls.get("learn_more", {}).get("url") else "")
              + "</p></div>") if ls else ""
    return (f"<div class='entry'><h3>{a(src.get('url'), w['title'])}</h3>"
            f"{_meta(esc(src.get('name')), esc(', '.join(w.get('regions', []))))}"
            f"<p>{esc(w['what_happened'])}</p>{_why('Why it matters', w.get('why_it_matters'))}{lesson}</div>")


def find(r: dict) -> str:
    title = a(r["url"], r["title"]) if r.get("url") else esc(r["title"])
    meta = _meta(esc(r.get("creator")), render.human(r.get("type", "")), render.human(r.get("duration") or r.get("time_required") or ""))
    return (f"<div class='entry'><h3>{title}</h3>{meta}<p>{esc(r['description'])}</p>"
            f"{_why('What you will get', r.get('what_i_might_get_from_it'))}"
            f"{render.media_embed(r.get('url'), r.get('title', ''), r.get('audio_url'))}</div>")


def short(v: dict) -> str:
    is_short = v.get("format") == "short" or "/shorts/" in v.get("url", "")
    return (f"<div class='entry'><h3>{esc(v['title'])}</h3>"
            f"{_meta(esc(v.get('channel', {}).get('name')), esc(v.get('topic')))}"
            f"{render.youtube_player(v['video_id'], v['title'], short=is_short)}</div>")


ENTRY = {"arxiv": paper, "research_updates": update, "world": story, "discovery": find, "youtube_shorts": short}


def overview_block(ov: list) -> str:
    if not ov:
        return ""
    return ("<h2>Overview</h2><p class='meta'>The best of today. Everything else follows below.</p>"
            + "".join(ENTRY[s](it) for s, it in ov))


def research(streams: dict, ov: list) -> str:
    out = [overview_block(ov)]
    papers = (streams.get("arxiv") or {}).get("items", [])
    if papers:
        top = [p for p in papers if p.get("priority", "top") != "more"]
        more = [p for p in papers if p.get("priority") == "more"]
        out.append("<h2>Papers</h2>" + "".join(paper(p) for p in top))
        if more:
            out.append(f"<p class='more'>More papers that passed ({len(more)})</p>" + "".join(paper(p, full=False) for p in more))
    ups = (streams.get("research_updates") or {}).get("items", [])
    if ups:
        top = [u for u in ups if u.get("priority", "top") != "more"]
        more = [u for u in ups if u.get("priority") == "more"]
        out.append("<h2>Research updates</h2>" + "".join(update(u) for u in top))
        if more:
            out.append(f"<p class='more'>More updates ({len(more)})</p><ul class='briefs'>" + "".join(
                f"<li>{a((u.get('source') or {}).get('url'), u['title'])}</li>" for u in more) + "</ul>")
    return "".join(out)


def news(streams: dict) -> str:
    doc = streams.get("world") or {}
    briefs = doc.get("briefs", [])
    out = []
    for key, label, its in render.group_world(doc.get("items", []), briefs):
        rows = [b for b in briefs if render.world_section({"section": b["section"]}) == key]
        if not its and not rows:
            continue
        out.append(f"<h2>{esc(label)}</h2>" + "".join(story(w) for w in its))
        if rows:
            out.append("<p class='also'><strong>Also in the news</strong></p><ul class='briefs'>" + "".join(
                f"<li>{a(b['url'], b['title'])} <span>· {esc(b['source'])}</span></li>" for b in rows) + "</ul>")
    return "".join(out)


def exploration(streams: dict, ov: list) -> str:
    out = [overview_block(ov)]
    for _, label, its in render.group_discovery((streams.get("discovery") or {}).get("items", [])):
        if its:
            out.append(f"<h2>{esc(label)}</h2>" + "".join(find(r) for r in its))
    return "".join(out)


def shorts(streams: dict) -> str:
    items = (streams.get("youtube_shorts") or {}).get("items", [])
    return f"<h2>Shorts ({len(items)})</h2>" + "".join(short(v) for v in items) if items else ""


def languages(streams: dict) -> str:
    return "".join(f"<h2>{esc(pk['language'].capitalize())}: {esc(pk['title'])}</h2>{render.language_pack(pk)}"
                   for pk in (streams.get("language") or {}).get("items", []))
