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
.entry :is(h3,h4,h5) a{color:var(--ink);text-decoration:none}.entry :is(h3,h4,h5) a:hover{text-decoration:underline}
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
.stats{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(12rem,1fr));gap:.3rem 1rem}
.stats strong{font:700 1.3rem var(--serif);margin-right:.3rem}.topics li{margin:.5rem 0}
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
.plain{list-style:none;padding:0}.plain li{padding:.45rem 0;border-bottom:1px solid var(--rule)}
/* daily */
.daynav{display:flex;justify-content:space-between;gap:1rem;font:400 .9rem var(--sans);margin:.2rem 0 1.4rem}
.toc{font:400 .92rem/1.5 var(--sans);padding:.6rem 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.toc p{margin:.25rem 0;display:flex;flex-wrap:wrap;gap:.2rem .9rem;align-items:baseline}
.toc strong{min-width:6rem}
.tabs{display:flex;flex-wrap:wrap;gap:.4rem;margin:.4rem 0 1.2rem;font:600 .92rem var(--sans)}
.tab{padding:.45rem .9rem;border:1px solid var(--rule);border-radius:999px;text-decoration:none;color:var(--ink)}
.tab span{font-weight:400;color:var(--ink-2)}.tab.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.tab.on span{color:var(--paper)}a.tab:hover{border-color:var(--ink)}
h1 .sub{display:block;font:400 1rem var(--sans);color:var(--ink-2);margin-top:.4rem}.toc span{color:var(--ink-2)}.toc a.minor{color:var(--ink-2)}
.group{margin-top:2.2rem}.group>h2{margin:0 0 .4rem;padding-bottom:.35rem;border-bottom:2px solid var(--ink)}
.stream-block{margin:1.4rem 0 0}
.stream-h,.sub-h{font-family:var(--sans);font-weight:700;letter-spacing:.02em;display:flex;gap:.6rem;align-items:baseline}
.stream-h{font-size:1rem;text-transform:uppercase;color:var(--ink);margin:0 0 .6rem}
.sub-h{font-size:.95rem;color:var(--ink-2);margin:1.2rem 0 .4rem;padding-top:.6rem;border-top:1px solid var(--rule)}
.stream-h span,.sub-h span{font-weight:400;color:var(--ink-2)}
.entry h4,.entry h5{font-family:var(--serif);font-size:1.12rem;margin:0 0 .3rem;font-weight:600;line-height:1.25}
.tags .sep,.areas .sep{display:none}
.shorts{display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:1.2rem 1rem;margin-top:1rem}
.short a.thumb{display:block;aspect-ratio:9/14;overflow:hidden;border-radius:6px;background:var(--paper-2)}
.short img{width:100%;height:100%;object-fit:cover;display:block}
.short p{margin:.35rem 0 0;font:400 .85rem/1.35 var(--sans)}
.tags{margin:.2rem 0 .4rem;display:flex;flex-wrap:wrap;gap:.35rem}
.tag{font:700 .75rem/1 var(--sans);padding:.3rem .55rem;border-radius:999px;background:var(--paper-2);color:var(--ink);border:1px solid var(--rule)}
.abstract{font-size:.95rem;line-height:1.55}
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
    head_title = esc(site["title"]) if title == "Home" else f"{esc(title)} | {esc(site['title'])}"
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


def _entry(stream: str, it: dict, heading: str = "h3") -> str:
    title = a(it["url"], it["title"]) if it.get("url") else esc(it["title"])
    return (f'<article class="entry e-{item_dimension(stream, it)}"><{heading}>{title}</{heading}>'
            f'{render.ITEM_RENDERERS[stream](it)}</article>')


def _short(it: dict) -> str:
    return (f'<div class="short"><a class="thumb" href="{esc(it["url"])}"><img src="{esc(it["thumbnail"])}" '
            f'alt="" loading="lazy"></a><p><a href="{esc(it["url"])}">{esc(it["title"])}</a></p>'
            f'<p class="ch">{esc(it["channel"]["name"])}</p></div>')


def _stream_title(s: str) -> str:
    return "Reading list this week" if s == "reading" else STREAM_META[s]["title"]


def _sub(anchor: str, label: str, n: int, inner: str) -> str:
    return (f'<div class="subsec" id="{anchor}"><h4 class="sub-h">{esc(label)} <span>{n}</span></h4>'
            f'<div class="col">{inner}</div></div>')


def _stream_block(s: str, doc: dict, date: str | None = None) -> str:
    items = doc.get("papers") if s == "reading" else doc["items"]
    out = [f'<section id="{s}" class="stream-block"><h3 class="stream-h">{esc(_stream_title(s))}'
           f' <span>{len(items)}</span></h3>']
    if s == "reading":
        new = [p for p in items if p.get("added") == date]
        out.append(f'<p class="stream-note">Papers worth definitely reading this week ({esc(doc["week"])}).'
                   + (f" {len(new)} added today." if new else "") + "</p>")
        out.append(f'<div class="col">{render.reading_list({"papers": items})}</div>')
    elif doc.get("notes"):
        out.append(f'<p class="stream-note">{esc(doc["notes"])}</p>')
    if s == "reading":
        pass  # rendered above
    elif not items:
        out.append('<p class="empty">Nothing worth your time here today.</p>')
    elif s == "youtube_shorts":
        out.append('<div class="shorts">' + "".join(_short(it) for it in items) + "</div>")
    elif s == "world":
        out += [_sub(f"news-{k}", label, len(its), "".join(_entry(s, it, "h5") for it in its))
                for k, label, its in render.group_world(items)]
    elif s == "discovery":
        out += [_sub(f"discover-{k}", label, len(its), "".join(_entry(s, it, "h5") for it in its))
                for k, label, its in render.group_discovery(items)]
    else:
        out.append('<div class="col">' + "".join(_entry(s, it, "h4") for it in items) + "</div>")
    out.append("</section>")
    return "".join(out)


def _part_tabs(parts: list[tuple[str, str, int]], current: str | None, prefix: str) -> str:
    """Tabs linking the overview and each part page. prefix is the path from this page to the part pages."""
    over = "<span class='tab on'>Overview</span>" if current is None else f"<a class='tab' href='{prefix}index.html'>Overview</a>"
    tabs = [over] + [f"<span class='tab on'>{esc(label)} <span>{n}</span></span>" if key == current else
                     f"<a class='tab' href='{prefix}{key}.html'>{esc(label)} <span>{n}</span></a>"
                     for key, label, n in parts]
    return "<nav class='tabs'>" + "".join(tabs) + "</nav>"


def _with_reading(streams: dict, reading: dict | None) -> dict:
    streams = dict(streams)
    if reading and reading.get("papers"):
        streams["reading"] = reading
    return streams


def _count(streams: dict, s: str) -> int:
    return len(streams[s]["papers"] if s == "reading" else streams[s]["items"])


def _daily_parts(streams: dict) -> list[tuple[str, str, int]]:
    return [(k, label, sum(_count(streams, s) for s in ss if s in streams))
            for k, label, ss in render.DAILY_PARTS if any(s in streams for s in ss)]


def _daynav(prev, nxt, suffix: str = ".html", up: str = "") -> str:
    return ('<div class="daynav">'
            + (f'<a href="{up}{prev}{suffix}" rel="prev">Earlier: {render.nice_date(prev)}</a>' if prev else "<span></span>")
            + (f'<a href="{up}{nxt}{suffix}" rel="next">Later: {render.nice_date(nxt)}</a>' if nxt else "<span></span>")
            + "</div>")


def _daily_part_page(site, date, streams, part, prev=None, nxt=None) -> str:
    """daily/<date>/<part>.html: one part of the day (research, news or exploration)."""
    key, label, names = next(x for x in render.DAILY_PARTS if x[0] == part)
    present = [s for s in names if s in streams]
    toc = []
    for s in present:
        if s == "world":
            toc += [f'<a href="#news-{k}">{esc(lab)}</a> <span>{len(its)}</span>' for k, lab, its in render.group_world(streams[s]["items"])]
        elif s == "discovery":
            toc += [f'<a href="#discover-{k}">{esc(lab)}</a> <span>{len(its)}</span>' for k, lab, its in render.group_discovery(streams[s]["items"])]
        else:
            short = {"arxiv": "Papers", "research_updates": "Research updates", "reading": "Reading list",
                     "youtube_shorts": "Shorts", "language": "Language"}.get(s, _stream_title(s))
            toc.append(f'<a href="#{s}">{esc(short)}</a> <span>{_count(streams, s)}</span>')
    body = [f"<h1>{esc(label)}<span class='sub'>{esc(long_date(date))}</span></h1>",
            _part_tabs(_daily_parts(streams), part, ""),
            '<nav class="toc"><p>' + " ".join(toc) + "</p></nav>" if toc else ""]
    body += [_stream_block(s, streams[s], date) for s in present]
    body.append(_daynav(prev, nxt, f"/{part}.html", "../"))
    return page(site, f"{label}, {date}", "".join(body), 2, "archive")


def _daily_overview(site, date, streams, prev=None, nxt=None) -> str:
    """daily/<date>/index.html: the three parts with their first few items."""
    body = [f"<h1>{esc(long_date(date))}</h1>", _part_tabs(_daily_parts(streams), None, "")]
    cards = []
    for key, label, names in render.DAILY_PARTS:
        lis = []
        for s in names:
            if s not in streams:
                continue
            items = streams[s]["papers"] if s == "reading" else streams[s]["items"]
            title = {"reading": "Reading list"}.get(s, STREAM_META.get(s, {}).get("title", s))
            first = "".join(f"<li>{a(it['url'], it['title']) if it.get('url') else esc(it['title'])}</li>" for it in items[:3])
            lis.append(f"<h4 class='sub-h'>{esc(title)} <span>{len(items)}</span></h4><ul>{first}</ul>")
        if lis:
            cards.append(f"<div class='stream'><h3><a href='{key}.html'>{esc(label)}</a></h3>{''.join(lis)}"
                         f"<p><a href='{key}.html'>Open {esc(label.lower())}</a></p></div>")
    body.append("<div class='today'>" + "".join(cards) + "</div>")
    body.append(_daynav(prev, nxt, "/index.html", "../"))
    return page(site, date, "".join(body), 2, "archive")


def _period_pages(out: Path, site: dict, kind: str, key: str, title: str, overview_html: str,
                  part_html: dict[str, str], counts: dict[str, int]) -> None:
    """<kind>/<key>/index.html plus one page per part, all sharing the same tabs."""
    parts = [(k, label, counts.get(k, 0)) for k, label in render.PERIOD_PARTS]
    _write(out / kind / key / "index.html",
           page(site, title, f"<div class='col'><h1>{esc(title)}</h1>{_part_tabs(parts, None, '')}{overview_html}</div>", 2, kind))
    for k, label in render.PERIOD_PARTS:
        _write(out / kind / key / f"{k}.html",
               page(site, f"{label}, {title}", f"<div class='col'><h1>{esc(label)}<span class='sub'>{esc(title)}</span></h1>"
                    f"{_part_tabs(parts, k, '')}{part_html.get(k) or '<p class=empty>Nothing in this part.</p>'}</div>", 2, kind))
    # old flat URL keeps working
    _write(out / kind / f"{key}.html", f'<!doctype html><meta http-equiv="refresh" content="0; url={key}/index.html">'
           f'<link rel="canonical" href="{key}/index.html"><a href="{key}/index.html">{esc(title)}</a>')


def _weekly_overview(w: dict) -> str:
    out = [f'<p class="lede">{esc(w["intro"])}</p>']
    for k, label in render.PERIOD_PARTS:
        its = [it for it in w["items"] if render.weekly_part(it) == k]
        if its:
            out.append(f"<h2><a href='{k}.html'>{esc(label)}</a></h2><ul>" + "".join(
                f"<li><a href='{k}.html#{render.weekly_section(it)}'>{esc(it['title'])}</a></li>" for it in its) + "</ul>")
    return "".join(out)


def _monthly_overview(m: dict) -> str:
    out = [f'<p class="lede">{esc(m["intro"])}</p>']
    for k, label in render.PERIOD_PARTS:
        pjs = [pj for pj in m["items"] if render.monthly_section(pj) == k]
        if pjs:
            out.append(f"<h2><a href='{k}.html'>{esc(label)}</a></h2><ul>" + "".join(
                f"<li><a href='{k}.html'>{esc(pj['title'])}</a></li>" for pj in pjs) + "</ul>")
    return "".join(out)


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
    readings = sorted((load_json(f) for f in repo.iter_stream_files("reading")), key=lambda d: d["week"], reverse=True)
    reading_by_week = {r["week"]: r for r in readings}
    for i, (date, streams) in enumerate(daily.items()):
        nxt = dates[i - 1] if i > 0 else None
        prev = dates[i + 1] if i + 1 < len(dates) else None
        st = _with_reading(streams, reading_by_week.get(iso_week(dt.date.fromisoformat(date))))
        _write(out / "daily" / date / "index.html", _daily_overview(site, date, st, prev, nxt))
        for key, _, _ in _daily_parts(st):
            _write(out / "daily" / date / f"{key}.html", _daily_part_page(site, date, st, key, prev, nxt))
        _write(out / "daily" / f"{date}.html", f'<!doctype html><meta http-equiv="refresh" content="0; url={date}/index.html">'
               f'<a href="{date}/index.html">{date}</a>')

    for r in readings:
        _write(out / "reading" / f"{r['week']}.html",
               page(site, f"Reading list {r['week']}", f"<div class='col'><h1>Reading list, week of "
                    f"{render.nice_date(r['start_date'])}</h1>{render.reading_list(r)}</div>", 1, "reading"))
    _write(out / "reading" / "index.html", page(site, "Reading lists", "<div class='col'><h1>Reading lists</h1></div>" + (
        "<ul class='days'>" + "".join(f"<li>{a(r['week'] + '.html', 'Week of ' + render.nice_date(r['start_date'], True))}"
                                      f"<span class='meta'>{len(r['papers'])} papers</span></li>" for r in readings) + "</ul>"
        if readings else "<p class='empty'>Nothing yet.</p>"), 1, "reading"))
    weeks = sorted((load_json(f) for f in repo.iter_stream_files("weekly")), key=lambda d: d["week"], reverse=True)
    months = sorted((load_json(f) for f in repo.iter_stream_files("monthly")), key=lambda d: d["month"], reverse=True)
    for w in weeks:
        counts = {k: sum(1 for it in w["items"] if render.weekly_part(it) == k) for k, _ in render.PERIOD_PARTS}
        _period_pages(out, site, "weekly", w["week"], f"Week of {render.nice_date(w['start_date'], True)}",
                      _weekly_overview(w), {k: render.weekly_package(w, k) for k, _ in render.PERIOD_PARTS}, counts)
    for m in months:
        label = dt.date.fromisoformat(m["month"] + "-01").strftime("%B %Y")
        counts = {k: sum(1 for pj in m["items"] if render.monthly_section(pj) == k) for k, _ in render.PERIOD_PARTS}
        _period_pages(out, site, "monthly", m["month"], label, _monthly_overview(m),
                      {k: render.monthly_package(m, k) for k, _ in render.PERIOD_PARTS}, counts)

    def plist(items, href, label_fn):
        if not items:
            return None
        return "<ul class='days'>" + "".join(
            f"<li>{a(href(x), label_fn(x))}<span class='meta'>{len(x['items'])} "
            f"{'things' if len(x['items']) != 1 else 'thing'}</span></li>" for x in items) + "</ul>"

    _write(out / "weekly" / "index.html", page(site, "Weekly", "<div class='col'><h1>Weekly</h1></div>"
           + (plist(weeks, lambda w: f"{w['week']}/index.html", lambda w: f"Week of {render.nice_date(w['start_date'], True)}")
              or "<p class='empty'>The first package arrives on Saturday morning.</p>"), 1, "weekly"))
    _write(out / "monthly" / "index.html", page(site, "Monthly", "<div class='col'><h1>Monthly</h1></div>"
           + (plist(months, lambda m: f"{m['month']}/index.html",
                    lambda m: dt.date.fromisoformat(m["month"] + "-01").strftime("%B %Y"))
              or "<p class='empty'>The first package arrives on the 1st.</p>"), 1, "monthly"))

    quarters = sorted((load_json(f) for f in repo.iter_stream_files("quarterly")), key=lambda d: d["quarter"], reverse=True)
    for q in quarters:
        counts = {k: len(q["parts"][k]["topics"]) for k, _ in render.PERIOD_PARTS}
        _period_pages(out, site, "quarterly", q["quarter"], f"{q['quarter']} review", render.quarterly_review(q),
                      {k: render.quarterly_review(q, k) for k, _ in render.PERIOD_PARTS}, counts)
    _write(out / "quarterly" / "index.html", page(site, "Quarterly", "<div class='col'><h1>Quarterly reviews</h1></div>"
           + ("<ul class='days'>" + "".join(f"<li>{a(q['quarter'] + '/index.html', q['quarter'] + ' review')}"
                                             f"<span class='meta'>{sum(len(p['topics']) for p in q['parts'].values())} topics</span></li>" for q in quarters) + "</ul>"
              if quarters else "<p class='empty'>The first review arrives on 1 January.</p>"), 1, "quarterly"))

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
            arch.append(f"<li>{a('daily/' + d + '/index.html', dt.date.fromisoformat(d).strftime('%a %-d %b'))}"
                        f"<span class='meta'>{esc(counts)}</span></li>")
        arch.append("</ul>")
    arch.append("</div>")
    _write(out / "archive.html", page(site, "Archive", "".join(arch), 0, "archive"))

    # docs: the vision and the system map, straight from docs/
    try:
        import markdown  # type: ignore
        md = lambda t: markdown.markdown(t, extensions=["tables", "fenced_code"])  # noqa: E731
    except ImportError:
        md = lambda t: f"<pre>{esc(t)}</pre>"  # noqa: E731
    for src, dest, title in (("docs/how_it_works.md", "docs.html", "How it works"), ("docs/vision.md", "vision.html", "Vision")):
        f = repo.p(*src.split("/"))
        text = f.read_text(encoding="utf-8") if f.exists() else f"{src} not found."
        _write(out / dest, page(site, title, f"<div class='doc'>{md(text)}</div>", 0, "docs"))

    _write(out / "index.html", page(site, "Home", _home(repo, site, daily, weeks, months, feeds, readings), 0, "home"))
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out


def _home(repo, site, daily, weeks, months, feeds, readings) -> str:
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
    buttons = [(f"daily/{latest}/{k}.html", label) for k, label, _ in render.DAILY_PARTS] if latest else []
    buttons += [("weekly/index.html", "Weekly"), ("monthly/index.html", "Monthly"), ("quarterly/index.html", "Quarterly"),
                ("archive.html", "Archive"), ("vision.html", "Vision"), ("docs.html", "How it works")]
    b.append('<nav class="buttons" aria-label="Sections">' + "".join(
        f'<a class="btn" href="{h}">{t}</a>' for h, t in buttons) + "</nav>")

    if latest:
        rl = next((r for r in readings if r["week"] == iso_week(day)), None)
        st = _with_reading(daily[latest], rl)
        b.append(f"<h2>{a(f'daily/{latest}/index.html', long_date(latest))}</h2><div class='today'>")
        for key, label, names in render.DAILY_PARTS:
            blocks = []
            for s in names:
                if s not in st:
                    continue
                items = st[s]["papers"] if s == "reading" else st[s]["items"]
                title = "Reading list" if s == "reading" else STREAM_META[s]["title"]
                lis = "".join(f"<li>{a(it['url'], it['title']) if it.get('url') else esc(it['title'])}</li>" for it in items[:3])
                blocks.append(f"<h4 class='sub-h'>{esc(title)} <span>{len(items)}</span></h4><ul>{lis}</ul>")
            if blocks:
                b.append(f"<div class='stream'><h3>{a(f'daily/{latest}/{key}.html', label)}</h3>{''.join(blocks)}</div>")
        b.append("</div>")

    plan = []
    for kind, docs, label_fn, part_fn in (
            ("weekly", weeks, lambda d: f"Week of {render.nice_date(d['start_date'])}", render.weekly_part),
            ("monthly", months, lambda d: dt.date.fromisoformat(d["month"] + "-01").strftime("%B"), render.monthly_section)):
        if not docs:
            continue
        d = docs[0]
        key = d.get("week") or d["month"]
        lis = "".join(f"<li><strong>{a(f'{kind}/{key}/{k}.html', lab)}</strong>: "
                      + esc(", ".join(it["title"] for it in d["items"] if part_fn(it) == k) or "nothing this time") + "</li>"
                      for k, lab in render.PERIOD_PARTS)
        plan.append(f"<div><h2>{a(f'{kind}/{key}/index.html', label_fn(d))}</h2><ul class='plain'>{lis}</ul></div>")
    if plan:
        b.append("<div class='plan'>" + "".join(plan) + "</div>")

    def frow(stream, path):
        url = f"{site['base_url']}/feeds/{path.name}"
        return (f"<li><span class='fname'>{esc(STREAM_META[stream]['title'])}</span>"
                f"<input readonly value='{esc(url)}' aria-label='{esc(STREAM_META[stream]['title'])} feed URL' onclick='this.select()'>"
                f"<button type='button' data-copy='{esc(url)}'>Copy</button></li>")
    from .core import DIGEST_FEEDS, PERIODIC_STREAMS
    main = [s for s in DIGEST_FEEDS + PERIODIC_STREAMS if s in feeds and s != "reading"]
    rest = [s for s in feeds if s not in main]
    b.append("<h2>RSS feeds</h2><ul class='feeds'>" + "".join(frow(s, feeds[s]) for s in main) + "</ul>")
    b.append("<h3>Single streams</h3><ul class='feeds'>" + "".join(frow(s, feeds[s]) for s in rest) + "</ul>")
    return "".join(b)
