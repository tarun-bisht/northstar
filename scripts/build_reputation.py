#!/usr/bin/env python3
"""Fill config/reputation.json -> universities with the QS World University Rankings top N.

Run by .github/workflows/build-reputation.yml (GitHub Actions has the network access this
needs). It reads the published QS results table (a PDF), takes every university ranked in
the top N, and looks up its email and web domains in the open university-domains list
(github.com/Hipo/university-domains-list). Hand-added entries (labs, research groups,
aliases) are kept. Re-run once a year when QS publishes a new table.

    python scripts/build_reputation.py --pdf-url URL [--top 1000]
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import re
import sys

import _bootstrap  # noqa: F401
from dsys import net
from dsys.core import repo_from_env
from dsys.reputation import norm

HIPO = "https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json"
REGIONS = ("Americas", "Europe", "Asia", "Oceania", "Africa")
ROW = re.compile(rf"^(=?\d+(?:\s*-\s*\d+)?\+?)\s+(.+?)\s*({'|'.join(REGIONS)})\s*$")
QS_COUNTRY_ALIASES = {"united states of america": "united states", "china (mainland)": "china",
                      "hong kong sar, china": "hong kong", "macau sar, china": "macao",
                      "korea, south": "korea, republic of", "south korea": "korea, republic of",
                      "türkiye": "turkey", "russia": "russian federation", "taiwan": "taiwan",
                      "viet nam": "vietnam", "iran, islamic republic of": "iran"}


def parse_rows(text: str, top: int) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = ROW.match(" ".join(line.split()))
        if not m:
            continue
        rank = int(re.match(r"=?(\d+)", m.group(1)).group(1))
        if rank > top:
            continue
        rows.append({"rank": rank, "rest": m.group(2)})
    return rows


def split_country(rest: str, countries: list[str]) -> tuple[str, str | None]:
    """'ETH Zurich (Swiss ...)Switzerland' -> ('ETH Zurich (Swiss ...)', 'Switzerland')."""
    low = rest.lower()
    for c in sorted(countries, key=len, reverse=True):
        if low.endswith(c.lower()):
            return rest[: len(rest) - len(c)].strip(" ,"), c
    return rest, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-url", required=True)
    ap.add_argument("--top", type=int, default=1000)
    a = ap.parse_args()
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(net.get(a.pdf_url, timeout=120)))
    text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    hipo = json.loads(net.get(HIPO, timeout=120))
    countries = sorted({h["country"] for h in hipo} | set(QS_COUNTRY_ALIASES) |
                       {"United States of America", "China (Mainland)", "Hong Kong SAR, China", "Macau SAR, China"})
    by_name = {}
    for h in hipo:
        by_name.setdefault(norm(re.sub(r"\(.*?\)", "", h["name"]).replace("The ", "")), h)
    rows = parse_rows(text, a.top)
    if len(rows) < a.top * 0.8:
        print(f"only {len(rows)} rows parsed from the PDF ({len(pdf.pages)} pages); refusing to write", file=sys.stderr)
        odd = [ln for ln in text.splitlines() if re.match(r"^\s*=?\d", ln) and not ROW.match(" ".join(ln.split()))]
        print("sample lines that did not parse:", *odd[:40], sep="\n", file=sys.stderr)
        print("last lines:", *text.splitlines()[-15:], sep="\n", file=sys.stderr)
        return 1
    repo = repo_from_env()
    path = repo.p("config", "reputation.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    have = {norm(u["name"]) for u in doc["universities"]}
    have_domains = {d for u in doc["universities"] for d in u.get("domains", [])}
    added, unmatched = 0, []
    for r in rows:
        name, country = split_country(r["rest"], countries)
        aliases = [x.strip() for x in re.findall(r"\((.*?)\)", name)]
        base = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
        key = norm(base.replace("The ", ""))
        h = by_name.get(key)
        if not h:
            close = difflib.get_close_matches(key, list(by_name), n=1, cutoff=0.9)
            h = by_name[close[0]] if close else None
        domains = sorted(set(h["domains"])) if h else []
        if key in have or (domains and set(domains) & have_domains):
            for u in doc["universities"]:  # keep the hand entry, add the rank
                if norm(u["name"].replace("The ", "")) == key or set(u.get("domains", [])) & set(domains):
                    u["qs_rank"] = r["rank"]
            continue
        if not domains:
            unmatched.append(base)
        doc["universities"].append({"name": base, "aliases": [x for x in aliases if 2 <= len(x) <= 60],
                                    "domains": domains, "country": QS_COUNTRY_ALIASES.get((country or "").lower(), country),
                                    "qs_rank": r["rank"]})
        have.add(key)
        have_domains |= set(domains)
        added += 1
    doc["universities_source"] = {"ranking": "QS World University Rankings", "url": a.pdf_url, "top": a.top,
                                  "rows": len(rows), "without_domains": len(unmatched)}
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} ranked rows, {added} universities added, {len(unmatched)} without a domain match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
