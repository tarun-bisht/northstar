"""Output a model can read in full.

A run reads command output and files through tools with limits: a command's output is cut after
about 30,000 characters, a file read is limited to about 25,000 tokens, and lines longer than about
2,000 characters are cut. Anything beyond is lost without notice. So:

* output up to LIMIT characters is printed as it is;
* longer output is written to part files of at most PART characters, and the command prints only
  the list of parts with an instruction to read every one;
* lines longer than WIDTH are wrapped, the continuation starting with "  ↪ ".
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

WORK = Path("/tmp/northstar")
LIMIT = 20_000   # printed directly below this
PART = 60_000    # one part file: well under one read (about 15k tokens)
WIDTH = 1_500    # longest line kept whole
CONT = "  ↪ "


def wrap(text: str, width: int = WIDTH) -> list[str]:
    out = []
    for line in text.splitlines():
        if len(line) <= width:
            out.append(line)
            continue
        pieces = textwrap.wrap(line, width - len(CONT), break_long_words=True, break_on_hyphens=False,
                               drop_whitespace=False, replace_whitespace=False)
        out.append(pieces[0])
        out += [CONT + p for p in pieces[1:]]
    return out


def parts(text: str, size: int = PART) -> list[str]:
    chunks, cur, n = [], [], 0
    for line in wrap(text):
        if cur and n + len(line) + 1 > size:
            chunks.append("\n".join(cur) + "\n")
            cur, n = [], 0
        cur.append(line)
        n += len(line) + 1
    if cur:
        chunks.append("\n".join(cur) + "\n")
    return chunks


def write_parts(text: str, stem: Path, size: int = PART) -> list[str]:
    """Write text as readable part files stem-01.txt, stem-02.txt, ... and return their paths."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    for old in stem.parent.glob(f"{stem.name}-*.txt"):
        old.unlink()
    paths = []
    for i, chunk in enumerate(parts(text, size), 1):
        p = stem.parent / f"{stem.name}-{i:02d}.txt"
        p.write_text(chunk, encoding="utf-8")
        paths.append(str(p))
    return paths


def records(obj) -> str:
    """Long JSON as one compact record per line: lists of objects become one line each, other
    values one 'key: value' line. Same content as the JSON, about a third fewer tokens."""
    import json

    def c(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    if isinstance(obj, list):
        return "\n".join(c(x) for x in obj) + "\n"
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                lines.append(f"{k}: ({len(v)}, one per line)")
                lines += [c(x) for x in v]
            elif isinstance(v, dict) and len(c(v)) > WIDTH:
                lines.append(f"{k}:")
                lines += [f"  {kk}: {c(vv)}" for kk, vv in v.items()]
            else:
                lines.append(f"{k}: {c(v)}")
        return "\n".join(lines) + "\n"
    return c(obj) + "\n"


def emit(text: str, name: str, out=None, workdir: Path = WORK, obj=None) -> None:
    out = out or sys.stdout
    if len(text) <= LIMIT and all(len(line) <= WIDTH for line in text.splitlines()):
        out.write(text)
        return
    if obj is not None:
        text = records(obj)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "output"
    paths = write_parts(text, workdir / "out" / slug)
    out.write("Output is {:,} characters, too long to show in one go. It is in {} part file(s). "
              "Read every part, in order, with the Read tool, before you decide anything. "
              "Long lines are wrapped: a line starting with '↪' continues the one above.\n{}\n"
              .format(len(text), len(paths), "\n".join(paths)))
