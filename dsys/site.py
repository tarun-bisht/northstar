"""Northstar: the static site. One stylesheet, no JavaScript framework.

Design: a navigator's chart. The wordmark is the north star; the home-page dial is the sextant used to sight it.
 Pale chart-paper, navy ink, a brass instrument arc on the
home page whose segments are your dimensions (config/interests.json). Each item carries its dimension colour
as a left rule, so colour always means "which part of life this touches".
"""

from __future__ import annotations

import datetime as dt
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from . import ideas as ideas_mod
from . import render
from .core import DAILY_STREAMS, STREAM_META, Repo, iso_week, load_json, today
from .render import DIMENSION_NAMES, TIME_LABEL, a, esc, human
from .rss import generate_all

DIMENSIONS: list[str] = list(DIMENSION_NAMES)  # refreshed from config in build_site
STREAM_DEFAULT_DIMENSION = {"language": "culture", "arxiv": "research", "research_updates": "research", "world": "world",
                         "discovery": "curiosity", "youtube_shorts": "curiosity"}
STREAM_SHORT = {"language": "Language", "arxiv": "Papers", "research_updates": "Research", "world": "World", "discovery": "Discovery",
                "youtube_shorts": "Shorts"}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&'
         'family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&display=swap" rel="stylesheet">')

CSS = """
:root{
  --paper:#edf1f2;--paper-2:#e1e8ea;--ink:#15243a;--ink-2:#4b5a6b;--rule:#c4cfd3;--link:#21507f;--brass:#9a772b;
  --serif:"Literata",Georgia,"Times New Roman",serif;--sans:"Atkinson Hyperlegible",system-ui,-apple-system,"Segoe UI",sans-serif;
  --measure:40rem;
}
@media (prefers-color-scheme:dark){:root{
  --paper:#0f1a26;--paper-2:#16253a;--ink:#e2e8ec;--ink-2:#97a5b3;--rule:#2a3b50;--link:#8fb9e2;--brass:#cfa955;}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:400 1.0625rem/1.65 var(--serif);
  font-optical-sizing:auto;text-rendering:optimizeLegibility}
a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:.18em}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:2px solid var(--brass);outline-offset:3px;border-radius:2px}
.skip{position:absolute;left:-999px}.skip:focus{left:1rem;top:1rem;background:var(--paper);padding:.4rem .7rem;z-index:9}
header.site{border-bottom:1px solid var(--rule)}
.bar{max-width:68rem;margin:0 auto;padding:.85rem 1.25rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap}
.mark{display:flex;align-items:center;gap:.55rem;color:var(--ink);text-decoration:none;font:600 1.3rem/1 var(--serif);letter-spacing:.01em}
.mark svg{width:22px;height:22px}
main{max-width:68rem;margin:0 auto;padding:2.25rem 1.25rem 5rem}
.col{max-width:var(--measure)}
h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.2;letter-spacing:-.005em}
h1{font-size:2.35rem;margin:.1rem 0 .6rem}
h2{font-size:1.45rem;margin:2.8rem 0 .9rem}
h3{font-size:1.15rem;margin:0 0 .3rem}
p{margin:.55rem 0}
.lede{font-size:1.2rem;line-height:1.55;color:var(--ink)}
.meta,.authors,.source,.links,.kind{font:400 .875rem/1.5 var(--sans);color:var(--ink-2)}
.meta{margin:.15rem 0 .5rem}
.why{font-style:italic}
.uncertain strong{color:var(--brass)}
blockquote{margin:.6rem 0;padding:.1rem 0 .1rem 1rem;border-left:2px solid var(--rule);color:var(--ink-2);font-size:.98rem}
details{margin:.45rem 0}
summary{cursor:pointer;font:400 .9rem/1.5 var(--sans);color:var(--link)}
summary:hover{text-decoration:underline}
ul,ol{padding-left:1.3rem;margin:.4rem 0}li{margin:.2rem 0}
.rel{font-weight:700}.rel-must_read{color:var(--link)}
.areas{margin:.6rem 0 0;display:flex;flex-wrap:wrap;gap:.35rem .9rem;font:400 .82rem/1.4 var(--sans);color:var(--ink-2)}
.pl::before{content:"";display:inline-block;width:.55rem;height:.55rem;border-radius:50%;margin-right:.35rem;vertical-align:.04rem;background:var(--c)}
"""
LIGHT = ["#2e5c8a", "#2c7471", "#6a5c99", "#9c5168", "#9a772b", "#557a36", "#8a4f2e", "#3d6b8f"]
DARK = ["#7ea9d6", "#6fbdb6", "#a99ad8", "#d993a8", "#cfa955", "#9cc57a", "#d9a07a", "#8fbbe0"]


def dimension_css() -> str:
    """Colour variables for whatever dimensions the config defines."""
    light = "".join(f"--p-{p}:{LIGHT[i % len(LIGHT)]};" for i, p in enumerate(DIMENSIONS))
    dark = "".join(f"--p-{p}:{DARK[i % len(DARK)]};" for i, p in enumerate(DIMENSIONS))
    cls = "".join(f".pl-{p},.e-{p}{{--c:var(--p-{p})}}" for p in DIMENSIONS)
    return f":root{{{light}}}@media (prefers-color-scheme:dark){{:root{{{dark}}}}}{cls}"


CSS += """
.entry,.activity{position:relative;padding:.15rem 0 .2rem 1.15rem;margin:1.6rem 0;border-left:3px solid var(--c,var(--rule))}
.entry h3 a{color:var(--ink);text-decoration:none}.entry h3 a:hover{text-decoration:underline}
.stream-note{font:400 .9rem/1.5 var(--sans);color:var(--ink-2);margin-top:-.4rem}
.empty{font-style:italic;color:var(--ink-2)}
/* home */
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,25rem);gap:2.5rem;align-items:center;margin-bottom:1rem}
.hero h1{font-size:clamp(2.6rem,6vw,4rem);margin:0;letter-spacing:-.02em}
.hero .lede{max-width:30rem}
.instrument{width:100%;height:auto;color:var(--ink)}
.instrument .seg{fill:none;stroke-width:14}
.instrument .scale{stroke:var(--ink-2);stroke-width:1}
.instrument .lbl{font:400 11.5px var(--sans);fill:var(--ink-2)}
.instrument .tick{stroke-width:2.2;stroke-linecap:round}
.instrument .arm{stroke:var(--brass);stroke-width:2}
.instrument .pivot{fill:var(--brass)}
.buttons{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.2rem 0 .4rem}
.btn{font:700 .92rem/1 var(--sans);padding:.65rem 1.05rem;border:1px solid var(--ink);border-radius:999px;color:var(--ink);text-decoration:none}
.btn:hover{background:var(--ink);color:var(--paper)}
.feeds{list-style:none;padding:0;margin:0}
.feeds li{display:grid;grid-template-columns:11rem minmax(0,1fr) auto;gap:.6rem;align-items:center;padding:.45rem 0;border-top:1px solid var(--rule)}
.fname{font:700 .9rem var(--sans)}
.feeds input{width:100%;font:400 .82rem ui-monospace,Menlo,monospace;color:var(--ink);background:var(--paper-2);border:1px solid var(--rule);border-radius:4px;padding:.4rem .5rem}
.feeds button{font:700 .82rem var(--sans);padding:.42rem .8rem;border:1px solid var(--rule);background:var(--paper);color:var(--ink);border-radius:4px;cursor:pointer}
.feeds button:hover{border-color:var(--ink)}
@media (max-width:640px){.feeds li{grid-template-columns:1fr auto}.fname{grid-column:1/-1}}
@media (prefers-reduced-motion:no-preference){
  .instrument .seg{stroke-dasharray:var(--len);stroke-dashoffset:var(--len);animation:draw 1.1s cubic-bezier(.3,.6,.2,1) forwards;animation-delay:var(--d)}
  .instrument .arm{transform-origin:200px 200px;animation:swing 1.4s cubic-bezier(.3,.6,.2,1) .5s both}
  @keyframes draw{to{stroke-dashoffset:0}}
  @keyframes swing{from{transform:rotate(-90deg)}to{transform:rotate(0)}}
}
.today{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.4rem 2.5rem}
.stream{padding:.9rem 0;border-top:1px solid var(--rule)}
.stream h3{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;font-size:1.05rem}
.stream h3 span{font:400 .85rem var(--sans);color:var(--ink-2)}
.stream a,.plan a{text-decoration:none}.stream a:hover,.plan a:hover{text-decoration:underline}
.stream ul{list-style:none;padding:0;margin:.3rem 0 0;font-size:.95rem}
.stream li{margin:.3rem 0;line-height:1.4}
.plan{display:grid;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr));gap:2.5rem}
.plan ol{list-style:none;padding:0}
.plan li{padding:.45rem 0;border-bottom:1px solid var(--rule)}
.plan li .meta{margin:0}
/* daily */
.daynav{display:flex;justify-content:space-between;gap:1rem;font:400 .9rem var(--sans);margin:.2rem 0 1.4rem}
.toc{display:flex;flex-wrap:wrap;gap:.4rem 1.3rem;font:400 .92rem var(--sans);padding:.7rem 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.toc span{color:var(--ink-2)}
.shorts{display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:1.2rem 1rem;margin-top:1rem}
.short a.thumb{display:block;aspect-ratio:9/14;overflow:hidden;border-radius:6px;background:var(--paper-2)}
.short img{width:100%;height:100%;object-fit:cover;display:block}
.short p{margin:.35rem 0 0;font:400 .85rem/1.35 var(--sans)}
.lang{list-style:none;padding:0}.lang li{margin:.3rem 0}.native{font-size:1.1em}.rom{color:var(--ink-2);font-style:italic}
.qs li{margin:.4rem 0}
.short .ch{color:var(--ink-2);font-size:.8rem}
/* ideas */
.idea{padding:.7rem 0;border-top:1px solid var(--rule)}
.idea h3{font-size:1.02rem;margin:0}
.idea .first{font-size:.95rem}
/* archive / lists */
.months h3{margin-top:1.8rem;font-size:1rem;color:var(--ink-2);font-family:var(--sans);font-weight:700}
.days{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(13rem,1fr));gap:.1rem 1.5rem}
.days li{padding:.3rem 0;border-bottom:1px solid var(--rule);font-size:.95rem}
.days .meta{display:block;margin:0}
.feedlist{list-style:none;padding:0}.feedlist li{padding:.8rem 0;border-top:1px solid var(--rule)}
.feedlist code{display:block;font:400 .82rem/1.4 ui-monospace,Menlo,monospace;color:var(--ink-2);word-break:break-all;margin-top:.2rem}
.doc{max-width:44rem}.doc table{border-collapse:collapse;font-size:.92rem;margin:1rem 0;display:block;overflow-x:auto}
.doc th,.doc td{border-bottom:1px solid var(--rule);padding:.35rem .7rem .35rem 0;text-align:left;vertical-align:top}
.doc pre{background:var(--paper-2);padding:.8rem 1rem;overflow-x:auto;font-size:.82rem;border-radius:4px}
.doc code{font-size:.88em}
.banner{background:var(--paper-2);padding:.7rem 1rem;border-left:3px solid var(--brass);font:400 .92rem/1.5 var(--sans)}
footer.site{border-top:1px solid var(--rule);font:400 .85rem/1.5 var(--sans);color:var(--ink-2)}
footer.site .bar{padding:1.2rem 1.25rem 2rem}
iframe{max-width:100%;border:0}
@media (max-width:760px){
  body{font-size:1rem}.hero{grid-template-columns:1fr;gap:1rem}.hero svg{max-width:22rem;margin:0 auto;display:block}
  h1{font-size:1.9rem}main{padding-top:1.5rem}.plan{gap:0}.plan h2{margin-top:2rem}.bar{gap:.8rem 1.2rem}
}
"""


def mark_svg() -> str:
    return ('<svg viewBox="0 0 30 30" aria-hidden="true"><path d="M15 1 L17.2 12.8 L29 15 L17.2 17.2 L15 29 L12.8 17.2 L1 15 L12.8 12.8 Z" fill="var(--brass)"/>'
            '<circle cx="15" cy="15" r="2.2" fill="var(--paper)"/></svg>')


def page(site: dict, title: str, body: str, depth: int = 0, current: str = "") -> str:
    """One page. No navigation bar: every page links home; the home page links everywhere."""
    up = "../" * depth
    head_title = esc(site["title"]) if title == "Home" else f"{esc(title)} — {esc(site['title'])}"
    alt = "".join(f'<link rel="alternate" type="application/rss+xml" title="{esc(site["title"])}: {esc(m["title"])}" '
                  f'href="{up}feeds/{m["feed"]}">' for m in STREAM_META.values())
    header = ("" if current == "home" else
              f'<header class="site"><div class="bar"><a class="mark" href="{up}index.html">{mark_svg()}'
              f'{esc(site["title"])}</a></div></header>')
    fork = f'<a href="{esc(site["repository"])}">Fork on GitHub</a>' if site.get("repository") else ""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="description" content="{esc(site["description"])}">'
            f'<meta name="color-scheme" content="light dark"><title>{head_title}</title><!--CANONICAL-->'
            f'<link rel="icon" href="data:image/svg+xml,{_favicon()}">{FONTS}<style>{CSS}{dimension_css()}</style>{alt}</head><body>'
            f'<a class="skip" href="#content">Skip to content</a>{header}'
            f'<main id="content">{body}</main>'
            f'<footer class="site"><div class="bar"><span>{esc(site["title"])}</span>{fork}</div></footer>'
            f'{COPY_JS if current == "home" else ""}</body></html>\n')


COPY_JS = ("<script>document.querySelectorAll('button[data-copy]').forEach(function(b){b.addEventListener('click',"
           "function(){var t=b.getAttribute('data-copy');(navigator.clipboard?navigator.clipboard.writeText(t):"
           "Promise.reject()).then(function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy'},1500)})"
           ".catch(function(){var i=b.previousElementSibling;i.select();});});});</script>")


def _favicon() -> str:
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%2315243a'/>"
           "<path d='M16 3 L18.3 13.7 L29 16 L18.3 18.3 L16 29 L13.7 18.3 L3 16 L13.7 13.7 Z' fill='%23cfa955'/></svg>")
    return svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


_CANON = {"root": None, "base": ""}


def _write(path: Path, html: str):
    """Write a page, filling in its absolute canonical URL from config/site.json base_url."""
    if _CANON["root"] is not None and "<!--CANONICAL-->" in html:
        rel = path.relative_to(_CANON["root"]).as_posix()
        rel = "" if rel == "index.html" else rel
        html = html.replace("<!--CANONICAL-->", f'<link rel="canonical" href="{esc(_CANON["base"])}/{esc(rel)}">')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def period_label(period: str | None) -> str | None:
    """2026-W49 -> 'week of 30 Nov'; 2026-12 -> 'December 2026'."""
    if not period:
        return None
    from .core import WEEK_RE, week_bounds
    if WEEK_RE.match(period):
        return "the week of " + week_bounds(period)[0].strftime("%-d %b")
    return dt.date.fromisoformat(period + "-01").strftime("%B %Y")


def long_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.strftime("%A %-d %B %Y")


def item_dimension(stream: str, it: dict) -> str:
    ps = it.get("dimensions") or []
    return ps[0] if ps else STREAM_DEFAULT_DIMENSION.get(stream, DIMENSIONS[0] if DIMENSIONS else "research")


# --- the instrument ------------------------------------------------------------------
def instrument_svg(counts: dict[str, int], quiet: str | None) -> str:
    """A 180-degree arc split into one segment per dimension, a graduated scale,
    ticks for today's items, and an index arm resting on the quietest area."""
    cx, cy, r = 200, 200, 150
    out = ['<svg class="instrument" viewBox="-74 0 568 236" role="img" '
           f'aria-label="Today touches: {esc(", ".join(f"{DIMENSION_NAMES[p]} {counts.get(p, 0)}" for p in DIMENSIONS))}">']

    def pt(deg, rad):
        t = math.radians(deg)
        return cx + rad * math.cos(t), cy - rad * math.sin(t)

    step = 180 / max(len(DIMENSIONS), 1)
    for i, p in enumerate(DIMENSIONS):
        a0, a1 = 180 - i * step - 1.2, 180 - (i + 1) * step + 1.2
        x0, y0 = pt(a0, r)
        x1, y1 = pt(a1, r)
        length = math.radians(a0 - a1) * r
        out.append(f'<path class="seg" d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" '
                   f'style="stroke:var(--p-{p});--len:{length:.0f};--d:{i * 0.09:.2f}s;opacity:.85"/>')
        # label
        mid = 180 - i * step - step / 2
        lx, ly = pt(mid, r + 30)
        anchor = "end" if mid > 100 else ("start" if mid < 80 else "middle")
        out.append(f'<text class="lbl" x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}">{esc(render.DIMENSION_SHORT.get(p) or DIMENSION_NAMES[p])}</text>')
        # today's marks, spread inside the segment
        n = min(counts.get(p, 0), 12)
        for k in range(n):
            deg = 180 - i * step - (k + 1) * step / (n + 1)
            ax, ay = pt(deg, r - 14)
            bx, by = pt(deg, r - 26)
            out.append(f'<line class="tick" x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" style="stroke:var(--p-{p})"/>')
    # graduated scale
    for deg in range(0, 181, 3):
        long = deg % 15 == 0
        ax, ay = pt(deg, r + 9)
        bx, by = pt(deg, r + (16 if long else 12))
        out.append(f'<line class="scale" x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>')
    # index arm
    idx = DIMENSIONS.index(quiet) if quiet in DIMENSIONS else None
    deg = 180 - idx * step - step / 2 if idx is not None else 90
    ex, ey = pt(deg, r - 34)
    out.append(f'<line class="arm" x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}"/>')
    out.append(f'<circle class="pivot" cx="{cx}" cy="{cy}" r="5"/>')
    out.append("</svg>")
    return "".join(out)


def _quiet_dimension(repo: Repo, day: dt.date) -> str | None:
    th = repo.state_path("topic_history")
    if not th.exists():
        return None
    by_month = load_json(th).get("by_month", {})
    recent = Counter()
    for m in (day.strftime("%Y-%m"), (day.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")):
        recent.update(by_month.get(m, {}))
    if not recent:
        return None
    return min(DIMENSIONS, key=lambda p: (recent.get(p, 0), DIMENSIONS.index(p)))


# --- data -----------------------------------------------------------------------------
def _daily_index(repo: Repo, examples: bool):
    by_date: dict[str, dict[str, dict]] = defaultdict(dict)
    for stream in DAILY_STREAMS:
        for f in repo.iter_stream_files(stream, examples):
            doc = load_json(f)
            by_date[doc["date"]][stream] = doc
    return dict(sorted(by_date.items(), reverse=True))


def _entry(stream: str, it: dict) -> str:
    title = a(it["url"], it["title"]) if it.get("url") else esc(it["title"])
    return (f'<article class="entry e-{item_dimension(stream, it)}"><h3>{title}</h3>'
            f'{render.ITEM_RENDERERS[stream](it)}</article>')


def _short(it: dict) -> str:
    return (f'<div class="short"><a class="thumb" href="{esc(it["url"])}"><img src="{esc(it["thumbnail"])}" '
            f'alt="" loading="lazy"></a><p><a href="{esc(it["url"])}">{esc(it["title"])}</a></p>'
            f'<p class="ch">{esc(it["channel"]["name"])}</p></div>')


def _daily_page(site, date, streams, depth, prev=None, nxt=None, title=None) -> str:
    present = [s for s in DAILY_STREAMS if s in streams]
    nav = ('<div class="daynav">'
           + (f'<a href="{prev}.html" rel="prev">Earlier: {render.nice_date(prev)}</a>' if prev else "<span></span>")
           + (f'<a href="{nxt}.html" rel="next">Later: {render.nice_date(nxt)}</a>' if nxt else "<span></span>")
           + "</div>")
    toc = '<p class="toc">' + "".join(
        f'<a href="#{s}">{STREAM_META[s]["title"]}</a> <span>{len(streams[s]["items"])}</span>' for s in present) + "</p>"
    body = [f"<h1>{esc(title or long_date(date))}</h1>", nav, toc]
    for s in present:
        doc = streams[s]
        body.append(f'<section id="{s}"><h2>{esc(STREAM_META[s]["title"])}</h2>')
        if doc.get("notes"):
            body.append(f'<p class="stream-note">{esc(doc["notes"])}</p>')
        if not doc["items"]:
            body.append('<p class="empty">Nothing worth your time here today.</p>')
        elif s == "youtube_shorts":
            body.append('<div class="shorts">' + "".join(_short(it) for it in doc["items"]) + "</div>")
        else:
            body.append('<div class="col">' + "".join(_entry(s, it) for it in doc["items"]) + "</div>")
        body.append("</section>")
    return page(site, title or date, "".join(body), depth, "archive")


# --- build ----------------------------------------------------------------------------
def build_site(repo: Repo, out: Path | None = None) -> Path:
    out = out or repo.p("_site")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    site = repo.config("site")
    _CANON.update(root=out, base=site["base_url"].rstrip("/"))
    render.configure(repo)
    DIMENSIONS[:] = list(DIMENSION_NAMES)

    feeds = generate_all(repo, out / "feeds")
    generate_all(repo, repo.p("feeds"))

    daily = _daily_index(repo, False)
    dates = list(daily)  # newest first
    for i, (date, streams) in enumerate(daily.items()):
        nxt = dates[i - 1] if i > 0 else None
        prev = dates[i + 1] if i + 1 < len(dates) else None
        _write(out / "daily" / f"{date}.html", _daily_page(site, date, streams, 1, prev, nxt))

    weeks = sorted((load_json(f) for f in repo.iter_stream_files("weekly")), key=lambda d: d["week"], reverse=True)
    months = sorted((load_json(f) for f in repo.iter_stream_files("monthly")), key=lambda d: d["month"], reverse=True)
    for w in weeks:
        _write(out / "weekly" / f"{w['week']}.html",
               page(site, f"Week {w['week']}", f"<div class='col'><h1>Week of {render.nice_date(w['start_date'])}</h1>"
                    f"{render.weekly_package(w)}</div>", 1, "weekly"))
    for m in months:
        label = dt.date.fromisoformat(m["month"] + "-01").strftime("%B %Y")
        _write(out / "monthly" / f"{m['month']}.html",
               page(site, label, f"<div class='col'><h1>{label}</h1>{render.monthly_package(m)}</div>", 1, "monthly"))

    def plist(items, href, label_fn):
        if not items:
            return None
        return "<ul class='days'>" + "".join(
            f"<li>{a(href(x), label_fn(x))}<span class='meta'>{len(x['items'])} "
            f"{'things' if len(x['items']) != 1 else 'thing'}</span></li>" for x in items) + "</ul>"

    _write(out / "weekly" / "index.html", page(site, "Weekly", "<div class='col'><h1>Weekly</h1></div>"
           + (plist(weeks, lambda w: f"{w['week']}.html", lambda w: f"Week of {render.nice_date(w['start_date'], True)}")
              or "<p class='empty'>The first package arrives on Saturday morning.</p>"), 1, "weekly"))
    _write(out / "monthly" / "index.html", page(site, "Monthly", "<div class='col'><h1>Monthly</h1></div>"
           + (plist(months, lambda m: f"{m['month']}.html",
                    lambda m: dt.date.fromisoformat(m["month"] + "-01").strftime("%B %Y"))
              or "<p class='empty'>The first package arrives on the 1st.</p>"), 1, "monthly"))

    # archive, grouped by month
    arch = ["<div class='col'><h1>Archive</h1></div>"]
    if not daily:
        arch.append("<p class='empty'>Nothing yet.</p>")
    by_month = defaultdict(list)
    for date in dates:
        by_month[date[:7]].append(date)
    arch.append("<div class='months'>")
    for m, ds in by_month.items():
        arch.append(f"<h3>{dt.date.fromisoformat(m + '-01').strftime('%B %Y')}</h3><ul class='days'>")
        for d in ds:
            counts = ", ".join(f"{STREAM_SHORT[s].lower()} {len(doc['items'])}" for s, doc in daily[d].items())
            arch.append(f"<li>{a('daily/' + d + '.html', dt.date.fromisoformat(d).strftime('%a %-d %b'))}"
                        f"<span class='meta'>{esc(counts)}</span></li>")
        arch.append("</ul>")
    arch.append("</div>")
    _write(out / "archive.html", page(site, "Archive", "".join(arch), 0, "archive"))

    # ideas live in state/ideas.json (the repo), not on the website
    reg = {"ideas": []}

    # docs
    readme = repo.p("README.md")
    text = readme.read_text(encoding="utf-8") if readme.exists() else "README.md not found."
    try:
        import markdown  # type: ignore
        docs_html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        docs_html = f"<pre>{esc(text)}</pre>"
    _write(out / "docs.html", page(site, "How it works", f"<div class='doc'>{docs_html}</div>", 0, "docs"))

    _write(out / "index.html", page(site, "Home", _home(repo, site, daily, weeks, months, feeds), 0, "home"))
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out


def _home(repo, site, daily, weeks, months, feeds) -> str:
    latest = next(iter(daily), None)
    counts: Counter = Counter()
    if latest:
        for s, doc in daily[latest].items():
            for it in doc["items"]:
                for p in (it.get("dimensions") or [STREAM_DEFAULT_DIMENSION.get(s)]):
                    counts[p] += 1
    day = dt.date.fromisoformat(latest) if latest else today()
    quiet = _quiet_dimension(repo, day)
    b = [f'<section class="hero"><div><h1>{esc(site["title"])}</h1><p class="lede">{esc(site["description"])}</p></div>'
         f'<figure style="margin:0">{instrument_svg(counts, quiet)}</figure></section>']
    buttons = [(f"daily/{latest}.html", "Today")] if latest else []
    buttons += [("archive.html", "Archive"), ("weekly/index.html", "Weekly"), ("monthly/index.html", "Monthly"),
                ("docs.html", "How it works")]
    b.append('<nav class="buttons" aria-label="Sections">' + "".join(
        f'<a class="btn" href="{h}">{t}</a>' for h, t in buttons) + "</nav>")

    if latest:
        b.append(f"<h2>{esc(long_date(latest))}</h2><div class='today'>")
        for s in DAILY_STREAMS:
            doc = daily[latest].get(s)
            if not doc:
                continue
            n = len(doc["items"])
            lis = "".join(f"<li>{a(it['url'], it['title']) if it.get('url') else esc(it['title'])}</li>"
                          for it in doc["items"][:3])
            more = f"<li>{a(f'daily/{latest}.html#{s}', f'All {n}')}</li>" if n > 3 else ""
            b.append(f"<div class='stream'><h3>{esc(STREAM_META[s]['title'])} <span>{n}</span></h3><ul>{lis}{more}</ul></div>")
        b.append("</div>")

    plan = []
    if weeks:
        w = weeks[0]
        lis = "".join(f"<li>{a('weekly/' + w['week'] + '.html', it['title'])}"
                      f"{render.meta(TIME_LABEL.get(it['time_estimate']))}</li>" for it in w["items"])
        plan.append(f"<div><h2>Week of {render.nice_date(w['start_date'])}</h2><ol>{lis}</ol></div>")
    if months:
        m = months[0]
        label = dt.date.fromisoformat(m["month"] + "-01").strftime("%B")
        lis = "".join(f"<li>{a('monthly/' + m['month'] + '.html', it['title'])}{render.meta(esc(it['time_estimate']))}</li>"
                      for it in m["items"])
        plan.append(f"<div><h2>{label}</h2><ol>{lis}</ol></div>")
    if plan:
        b.append("<div class='plan'>" + "".join(plan) + "</div>")

    rows = "".join(
        f"<li><span class='fname'>{esc(STREAM_META[stream]['title'])}</span>"
        f"<input readonly value='{esc(site['base_url'])}/feeds/{esc(path.name)}' aria-label='{esc(STREAM_META[stream]['title'])} feed URL' onclick='this.select()'>"
        f"<button type='button' data-copy='{esc(site['base_url'])}/feeds/{esc(path.name)}'>Copy</button></li>"
        for stream, path in feeds.items())
    b.append(f"<h2>RSS feeds</h2><ul class='feeds'>{rows}</ul>")
    return "".join(b)
