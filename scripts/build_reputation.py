#!/usr/bin/env python3
"""Fill config/reputation.json -> universities with the world's top research universities.

Run by .github/workflows/build-reputation.yml (GitHub Actions has the network access this
needs). QS gates its full table (the Excel needs a form), and public QS PDFs list only the
top 100. So the list is built from two open sources:
- OpenAlex (api.openalex.org): the top N universities by citations, with acronyms,
  alternative names and web domains;
- the QS results PDF, when given, to add each university's QS rank (top 100 in public PDFs).
Email domains come from the open university-domains list (github.com/Hipo). Hand-added
entries (labs, research groups, aliases) are kept. Re-run once a year.

    python scripts/build_reputation.py [--top 1000] [--pdf-url URL]
"""

from __future__ import annotations

import argparse
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
    ap.add_argument("--pdf-url", default="")
    ap.add_argument("--top", type=int, default=1000)
    a = ap.parse_args()
    repo = repo_from_env()
    path = repo.p("config", "reputation.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    hipo = json.loads(net.get(HIPO, timeout=120))
    n = add_openalex(doc, hipo, a.top)
    print(f"OpenAlex: {n} universities added")
    if a.pdf_url:
        add_qs(doc, hipo, a.pdf_url, a.top)
    doc["universities_source"] = {"openalex_top_by_citations": a.top, "qs_pdf": a.pdf_url or None}
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(doc['universities'])} universities in the registry")
    return 0


OPENALEX = "https://api.openalex.org/institutions"


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    host = re.sub(r"^www\d?\.", "", host)
    return host or None


def add_openalex(doc: dict, hipo: list, top: int) -> int:
    hipo_by_name = {norm(h["name"]): h for h in hipo}
    have = {norm(u["name"]) for u in doc["universities"]}
    have_domains = {d for u in doc["universities"] for d in u.get("domains", [])}
    added, page = 0, 1
    while added < top and page <= (top // 200) + 3:
        q = f"{OPENALEX}?filter=type:education&sort=cited_by_count:desc&per_page=200&page={page}&mailto=northstar@users.noreply.github.com"
        rows = json.loads(net.get(q, timeout=60)).get("results", [])
        if not rows:
            break
        for r in rows:
            name = r.get("display_name", "")
            dom = _domain(r.get("homepage_url"))
            h = hipo_by_name.get(norm(name))
            domains = sorted({d for d in ([dom] if dom else []) + (h["domains"] if h else []) if d})
            if norm(name) in have or set(domains) & have_domains:
                continue
            aliases = [x for x in (r.get("display_name_acronyms") or []) + (r.get("display_name_alternatives") or [])
                       if 3 <= len(x) <= 80][:6]
            doc["universities"].append({"name": name, "aliases": aliases, "domains": domains,
                                        "country": r.get("country_code"), "openalex_rank": page * 200 - 200 + rows.index(r) + 1})
            have.add(norm(name))
            have_domains |= set(domains)
            added += 1
            if added >= top:
                break
        page += 1
    return added


def add_qs(doc: dict, hipo: list, pdf_url: str, top: int) -> None:
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(net.get(pdf_url, timeout=120)))
    text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    countries = sorted({h["country"] for h in hipo} | set(QS_COUNTRY_ALIASES) |
                       {"United States of America", "China (Mainland)", "Hong Kong SAR, China", "Macau SAR, China"})
    rows = parse_rows(text, top)
    marked = 0
    for r in rows:
        name, _ = split_country(r["rest"], countries)
        key = norm(re.sub(r"\s*\(.*?\)\s*", " ", name).strip().replace("The ", ""))
        aliases = [x.strip() for x in re.findall(r"\((.*?)\)", name)]
        for u in doc["universities"]:
            if norm(u["name"].replace("The ", "")) == key or key in {norm(x) for x in u.get("aliases", [])}:
                u["qs_rank"] = r["rank"]
                u["aliases"] = sorted(set(u.get("aliases", [])) | {x for x in aliases if 2 <= len(x) <= 60})
                marked += 1
                break
    print(f"QS: {len(rows)} ranked rows read, {marked} matched to the registry")

if __name__ == "__main__":
    sys.exit(main())
