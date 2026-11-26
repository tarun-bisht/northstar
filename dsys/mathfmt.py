"""Maths in HTML that renders in RSS readers and browsers without JavaScript.

Content holds LaTeX written by Claude, sometimes in `$...$`, `$$...$$`, `\\(...\\)` or `\\[...\\]`,
often bare (`x_{l+1} = x_l + f(x_l)`, `a^2 + b^2`, `\\frac{1}{n}`). This turns it into:

* `<sub>` and `<sup>` for simple subscripts and superscripts (`x_{l+1}`, `x_l`, `a^2`, `10^30`):
  they work everywhere;
* MathML (`<math>`, via latex2mathml) for anything with a LaTeX command, fraction, sum, integral,
  matrix or Greek letter: rendered natively by today's browsers and mobile web views.

It is careful with prose: `$83` and `$1.6 billion` are money, not maths; snake_case words, URLs,
code and existing markup are left alone.
"""
from __future__ import annotations

import html
import re

try:
    from latex2mathml.converter import convert as _to_mathml
except ImportError:  # pragma: no cover - only without the package
    _to_mathml = None

# Text inside these elements is never touched.
_SKIP = {"code", "pre", "math", "script", "style", "iframe", "textarea", "kbd", "samp", "svg", "title"}
_TAG = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
_TAG_NAME = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)")
_URL = re.compile(r"(?:https?://|www\.)\S+")

# Delimited maths. $...$ follows pandoc: no space just inside the dollars, and the opening $ is not
# followed by a digit (so "$83 ... $200" stays money). A span counts only if it holds LaTeX.
_DISPLAY = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)
_INLINE = re.compile(r"\\\((.+?)\\\)|(?<![\\$\w])\$(?![\s\d$])([^$\n]+?)(?<!\s)\$(?![\w$])")
_LATEXY = re.compile(r"\\[A-Za-z]+|[_^{}]")

# Bare LaTeX commands that mean maths. A run of maths around one becomes a single <math>.
_CMDS = ("frac|dfrac|tfrac|sqrt|sum|prod|int|iint|oint|lim|limsup|liminf|infty|partial|nabla|cdot|cdots|ldots|"
         "times|div|pm|mp|leq|geq|neq|approx|sim|simeq|equiv|propto|le|ge|ll|gg|in|notin|subset|subseteq|cup|cap|"
         "forall|exists|to|rightarrow|leftarrow|Rightarrow|iff|mapsto|log|ln|exp|sin|cos|tan|max|min|arg|argmax|"
         "argmin|det|mathbb|mathcal|mathbf|mathrm|operatorname|hat|bar|tilde|vec|dot|overline|underline|binom|"
         "begin|end|left|right|langle|rangle|lVert|rVert|Vert|mid|top|"
         "alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|"
         "sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega")
_BARE_CMD = re.compile(rf"\\(?:{_CMDS})(?![A-Za-z])")
# What a bare maths run may contain: commands with braces, identifiers, numbers and operators.
# Words of two or more letters end it (except a few function names), so prose is never swallowed.
_RUN_TOKEN = re.compile(
    r"\\(?:mathrm|mathbf|mathbb|mathcal|mathit|mathsf|operatorname|text|textrm|textbf|textit)\{[^{}]*\}|"
    rf"\\(?:{_CMDS})(?![A-Za-z])|\\[{{}},;!| ]|\{{|\}}|[A-Za-z](?![A-Za-z])|\d+(?:\.\d+)?|"
    r"(?:Var|Cov|sin|cos|tan|log|ln|exp|max|min|det|tr|softmax)(?![A-Za-z])|[_^=+\-*/<>()\[\],.|!']|\s+")
# Environments (matrices, cases, aligned) are taken whole.
_ENV = re.compile(r"\\begin\{([A-Za-z]+\*?)\}.*?\\end\{\1\}", re.S)

# Simple subscripts and superscripts: a single letter, a number or a closing bracket, then _ or ^
# with a braced group or one character that does not run on into a word (so max_research stays).
_GROUP = r"\{(?:[^{}]|\{[^{}]*\})*\}"
_SIMPLE = re.compile(
    rf"(?<![\w\\])(?P<base>[A-Za-z]|\d+(?:\.\d+)?|\))"
    rf"(?:_(?P<sub>{_GROUP}|[A-Za-z0-9](?![A-Za-z0-9])))?"
    rf"(?:\^(?P<sup>{_GROUP}|\d+(?![\w])|[A-Za-z](?![A-Za-z0-9])|[*'])|(?P<prime>'))?")


def _strip(group: str) -> str:
    return group[1:-1] if group.startswith("{") and group.endswith("}") else group


def is_simple(tex: str) -> bool:
    """Only letters, digits, simple operators and sub/superscripts: plain HTML is enough."""
    return "\\" not in tex and not re.search(r"\{[^{}]*[_^][^{}]*\}", tex)


def simple_html(tex: str) -> str:
    """x_{l+1} -> x<sub>l+1</sub>, a^2 -> a<sup>2</sup>. tex is plain (unescaped) text."""
    out, pos = [], 0
    for m in _SIMPLE.finditer(tex):
        if not (m.group("sub") or m.group("sup")):
            continue
        out.append(html.escape(tex[pos:m.start()], quote=False))
        s = html.escape(m.group("base"), quote=False)
        if m.group("sub"):
            s += f"<sub>{html.escape(_strip(m.group('sub')), quote=False)}</sub>"
        if m.group("sup"):
            s += f"<sup>{html.escape(_strip(m.group('sup')), quote=False)}</sup>"
        out.append(s)
        pos = m.end()
    out.append(html.escape(tex[pos:], quote=False))
    return "".join(out)


def mathml(tex: str, display: bool = False) -> str:
    """LaTeX to MathML; falls back to readable HTML if the package is missing or the LaTeX is broken."""
    tex = tex.strip()
    if _to_mathml is not None:
        try:
            return _to_mathml(tex, display="block" if display else "inline")
        except Exception:  # noqa: BLE001 - malformed LaTeX should never break a feed
            pass
    return f"<code>{html.escape(tex, quote=False)}</code>"


def to_html(tex: str, display: bool = False) -> str:
    return mathml(tex, display) if display or not is_simple(tex) else simple_html(tex)


_FUNCS = {"Var", "Cov", "sin", "cos", "tan", "log", "ln", "exp", "max", "min", "det", "tr", "softmax"}
_TEXTCMD = re.compile(r"(\\(?:mathrm|mathbf|mathbb|mathcal|mathit|mathsf|operatorname|text|textrm|textbf|textit)\{)([^{}]*)\}")
_PROSE = re.compile(r"[A-Za-z]{2,}|[.;:?!](?=\s)|\n")


def _bare_runs(text: str) -> list[tuple[int, int]]:
    """Spans of bare maths around a LaTeX command, never reaching into prose words."""
    spans: list[tuple[int, int]] = []
    # words inside \text{...} and the like are maths, not prose: hide them from the prose search
    masked = _TEXTCMD.sub(lambda g: g.group(1) + "0" * len(g.group(2)) + "}", text)
    for m in _BARE_CMD.finditer(text):
        if spans and m.start() < spans[-1][1]:
            continue
        lb = 0  # just after the last prose word or sentence break before the command
        for w in _PROSE.finditer(masked, 0, m.start()):
            if w.group(0) in _FUNCS or masked[w.start() - 1:w.start()] == "\\":
                continue
            lb = w.end()
        start, pos = lb, lb
        while pos < m.start():  # everything from there to the command must be maths
            t = _RUN_TOKEN.match(text, pos)
            if not t or t.end() == pos:
                start = m.start()
                break
            pos = t.end()
        end = m.start()
        while end < len(text):
            t = _RUN_TOKEN.match(text, end)
            if not t or t.end() == end:
                break
            end = t.end()
        seg = text[start:end]
        s_ = start + len(seg) - len(seg.lstrip(" ,.;:"))
        e_ = end - (len(seg) - len(seg.rstrip(" ,.;:")))
        if e_ > s_ and text[s_:e_].count("{") == text[s_:e_].count("}"):
            spans.append((s_, e_))
    return spans


def _text(node: str) -> str:
    """Convert maths in one HTML text node (escaped HTML in, HTML out)."""
    raw = html.unescape(node)
    if not re.search(r"[_^$\\]", raw):
        return node
    out, pos = [], 0
    # 1. URLs are kept whole
    pieces = []
    for m in _URL.finditer(raw):
        pieces.append((raw[pos:m.start()], False))
        pieces.append((m.group(0), True))
        pos = m.end()
    pieces.append((raw[pos:], False))
    for chunk, is_url in pieces:
        out.append(html.escape(chunk, quote=False) if is_url else _convert(chunk))
    return "".join(out)


def _convert(raw: str) -> str:
    """Delimited maths, then bare runs with commands, then simple sub/superscripts."""
    found = []  # (start, end, html)
    for m in _DISPLAY.finditer(raw):
        tex = m.group(1) or m.group(2)
        if _LATEXY.search(tex) or any(c.isalpha() for c in tex):
            found.append((m.start(), m.end(), mathml(tex, display=True)))
    for m in _INLINE.finditer(raw):
        if any(s <= m.start() < e for s, e, _ in found):
            continue
        tex = m.group(1) if m.group(1) is not None else m.group(2)
        if m.group(1) is not None or _LATEXY.search(tex):
            found.append((m.start(), m.end(), to_html(tex)))
    for m in _ENV.finditer(raw):
        if not any(a < m.end() and m.start() < b for a, b, _ in found):
            found.append((m.start(), m.end(), mathml(m.group(0), display=True)))
    taken = [(s, e) for s, e, _ in found]
    for s, e in _bare_runs(raw):
        if not any(a < e and s < b for a, b in taken):
            found.append((s, e, mathml(raw[s:e])))
    found.sort()
    out, pos = [], 0
    for s, e, h in found:
        out.append(simple_html(raw[pos:s]))
        out.append(h)
        pos = e
    out.append(simple_html(raw[pos:]))
    return "".join(out)


def convert_html(fragment: str) -> str:
    """Convert maths in the text of an HTML fragment, leaving tags, attributes, links' targets,
    code and existing MathML alone."""
    parts = _TAG.split(fragment)
    skip = 0
    out = []
    for p in parts:
        if not p:
            continue
        if p.startswith("<"):
            m = _TAG_NAME.match(p)
            if m and m.group(2).lower() in _SKIP and not p.rstrip().endswith("/>"):
                skip += -1 if m.group(1) else 1
                skip = max(skip, 0)
            out.append(p)
        else:
            out.append(p if skip else _text(p))
    return "".join(out)
