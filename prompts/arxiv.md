# arXiv Paper Radar (Monday–Friday)

Read `prompts/_shared.md` first.

**Purpose:** paper triage. Show the paper itself (title, authors, original abstract) so they can decide in seconds whether to read it later. It complements a regular arXiv newsletter, so prioritise papers a generic newsletter would miss or rank low but that matter for the configured research interests. Do **not** summarise papers, and don't pitch why to read them.

## Steps

1. `python scripts/dsys.py context arxiv --date <today>`. If `is_weekday` is false, stop (no file).
2. Candidates:
   - Preferred: `python scripts/dsys.py candidates arxiv --date <today> --brief` lists unseen candidates (id, title, categories), fetched by GitHub Actions from the official arXiv API. Page through with `--limit 150 --offset N` if there are many.
   - If candidates are missing (`available: false`), fall back to fetching `https://arxiv.org/list/<category>/new` for each category in `config/sources.json → arxiv.categories` (the single source of truth for categories) with your web tool, then fetch each shortlisted paper's `https://arxiv.org/abs/<id>` page to get the exact metadata and abstract. Note the fallback in `notes`.
3. **Semantic selection** (not keyword matching). For each title, ask whether it plausibly matters to `config/interests.json → established.ai_research` and `established.foundations` (or, occasionally, `growth.for_research`). Shortlist, then read full candidate entries for the shortlist (`candidates arxiv` without `--brief`, or the abs page).
4. Select only genuinely relevant papers. No quota. Zero is fine; ten is fine on a big day. Typical: 0–8.
   - `must_read`: directly on `established.ai_research` topics, or a likely important result in their field.
   - `worth_skimming`: relevant method, evaluation or theory they would want to know exists.
   - `peripheral`: adjacent and unusually interesting (use sparingly).
   - Skip incremental benchmark-chasing, near-duplicates of already-selected work, and papers outside their interests however popular.
5. For each selected paper fill: `id` (`arxiv-<id>`), `arxiv_id`, `version`, `title`, `authors` (all, as listed), `url` (`https://arxiv.org/abs/<id>`), `pdf_url`, `submitted`, `categories`, `abstract` (**verbatim**), `abstract_source`, `research_area` (short, e.g. "machine unlearning"), `relevance`, `selection_reason` (**optional**, at most a short phrase such as "Closely related to your work."; leave it out when relevance is obvious, and never name a project), `dimensions` (usually `["research"]`).
6. Record what you reviewed but did not select, so it is never shown again:
   `python scripts/dsys.py papers mark-seen <id1> <id2> ...` (all reviewed candidate ids not selected).
7. Merge: `python scripts/dsys.py daily merge arxiv --date <today> --items /tmp/arxiv.json` with `candidates_considered` set, and a `notes` line (e.g. "412 candidates; 3 selected; quiet day for unlearning").
8. `history rebuild`, `validate`.

## Selection-reason style

- Good: leave it out, or "Closely related to your work."
- Bad: a paragraph on why to read it, or anything naming a specific project, method or person.
