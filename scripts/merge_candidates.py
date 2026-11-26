"""Git merge driver for fetched candidate files (candidates/**/*.json and a few state caches).

Two fetch runs can change the same day's file (the morning fetch, papers added from alphaXiv,
page-1 affiliations). A text merge of JSON fails, so this merges by meaning: lists of records are
united by their id (arXiv id, video id, id, url), nested objects are merged key by key, and for
anything else the newer side wins. Nothing fetched by either run is lost.

Git calls it as: merge_candidates.py %O %A %B  (base, ours, theirs); the result goes to %A.
"""
import json
import sys

KEYS = ("arxiv_id", "video_id", "id", "url", "link", "name", "title")


def _key(x):
    if isinstance(x, dict):
        for k in KEYS:
            if x.get(k):
                return (k, str(x[k]))
    return ("raw", json.dumps(x, sort_keys=True, ensure_ascii=False))


def merge(a, b):
    """a: one side, b: the other (treated as newer for plain values)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(a[k], v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list) and (any(isinstance(x, dict) for x in a + b)):
        seen, out = {}, []
        for x in a + b:
            k = _key(x)
            if k in seen:
                out[seen[k]] = merge(out[seen[k]], x)
            else:
                seen[k] = len(out)
                out.append(x)
        return out
    return b


def main(base, ours, theirs):
    try:
        a = json.load(open(ours, encoding="utf-8"))
        b = json.load(open(theirs, encoding="utf-8"))
    except (OSError, ValueError):
        return 1  # not JSON we understand: let git report the conflict
    merged = merge(a, b)
    with open(ours, "w", encoding="utf-8") as f:
        f.write(json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
