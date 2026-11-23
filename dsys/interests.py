"""Small, safe edits to config/interests.json, used when the user says things like
"I'm into pottery now" or "less anime, more history".

Paths are dotted keys to a list, e.g. 'established.ai_research', 'growth.for_research', 'exploration.culture'.
Values are kept as written; duplicates (case-insensitive) are ignored.
"""

from __future__ import annotations

from .core import Repo, load_json, write_json


class InterestError(ValueError):
    pass


def _path(repo: Repo):
    return repo.p("config", "interests.json")


def lists(doc: dict, prefix: str = "") -> dict[str, list]:
    """Every editable list in the file, by dotted path (dimensions are excluded)."""
    out = {}
    for k, v in doc.items():
        if k.startswith("_") or k == "dimensions":
            continue
        p = f"{prefix}{k}"
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            out[p] = v
        elif isinstance(v, dict):
            out.update(lists(v, p + "."))
    return out


def _get_list(doc: dict, path: str, create: bool = False) -> list:
    parts = path.split(".")
    cur = doc
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part.startswith("_") or part == "dimensions":
            raise InterestError(f"{path!r} is not an editable interest list")
        if part not in cur:
            if not create:
                raise InterestError(f"no list at {path!r}; existing: {', '.join(sorted(lists(doc)))}")
            if not last and i == 0:
                raise InterestError(f"unknown section {part!r}; create lists only inside existing sections")
            cur[part] = [] if last else {}
        cur = cur[part]
        if not last and not isinstance(cur, dict):
            raise InterestError(f"{'.'.join(parts[:i + 1])!r} is not a section")
    if not isinstance(cur, list):
        raise InterestError(f"{path!r} is not a list")
    return cur


def _find(lst: list, value: str) -> int | None:
    v = value.strip().lower()
    return next((i for i, x in enumerate(lst) if x.strip().lower() == v), None)


def add(doc: dict, path: str, value: str, create: bool = False) -> bool:
    value = value.strip()
    if not value:
        raise InterestError("empty value")
    lst = _get_list(doc, path, create=create)
    if _find(lst, value) is not None:
        return False
    lst.append(value)
    return True


def remove(doc: dict, path: str, value: str) -> bool:
    lst = _get_list(doc, path)
    i = _find(lst, value)
    if i is None:
        return False
    lst.pop(i)
    return True


def move(doc: dict, src: str, dst: str, value: str) -> bool:
    lst = _get_list(doc, src)
    i = _find(lst, value)
    if i is None:
        raise InterestError(f"{value!r} is not in {src!r}")
    item = lst.pop(i)
    add(doc, dst, item, create=True)
    return True


def find_everywhere(doc: dict, value: str) -> list[str]:
    return [p for p, lst in lists(doc).items() if _find(lst, value) is not None]


def load(repo: Repo) -> dict:
    return load_json(_path(repo))


def save(repo: Repo, doc: dict) -> None:
    write_json(_path(repo), doc)
