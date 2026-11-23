# arXiv Paper Radar (Monday to Friday)

Read `prompts/_shared.md` first.

The job is to filter. From hundreds of new papers, keep only the good ones that matter for the configured interests, and drop the rest. Fewer and better is the point.

## Steps

1. `python scripts/dsys.py context arxiv --date <today>`. If `is_weekday` is false, stop.
2. Candidates: `python scripts/dsys.py candidates arxiv --date <today> --brief` lists unseen papers from the arXiv API and Hugging Face Daily Papers (fetched at 06:00 IST). Page with `--limit 150 --offset N`. If the file is missing, read `https://arxiv.org/list/<category>/new` for each category in `config/sources.json` instead, and note it.
3. Shortlist by meaning, not keywords, against `config/interests.json` (`established.ai_research`, `established.foundations`, sometimes `growth.for_research`).
4. Keep only good papers. Signs of quality: a clear contribution, careful evaluation, code or data released, a strong group or venue, or real community interest (`hf_upvotes`). Drop incremental tweaks, thin benchmark chasing and near duplicates. Zero papers on a quiet day is fine.
5. For each kept paper, read the full candidate (or the abs page) and fill: `id` (`arxiv-<id>`), `arxiv_id`, `title`, `authors`, `url`, `pdf_url`, `submitted`, `categories`, `abstract` (**copied word for word**), `abstract_source`, `research_area` (two or three words), `hf_upvotes` if known, `dimensions`.
6. **Tags, not reasons.** Give 1 to 3 tags from `paper_tags` in the context, most important first. These are the only tags allowed:
   close to your work, useful for your work, new method or architecture, strong result, benchmark or dataset, theory, survey or tutorial, worth knowing.
   Never write a reason or explanation. Never mention a project or method of the user's.
7. Mark the rest as seen: `python scripts/dsys.py papers mark-seen <id> ...`.
8. If a paper is a must read for the week, also add it to the reading list (`prompts/reading_list.md`).
9. Merge: `python scripts/dsys.py daily merge arxiv --date <today> --items /tmp/arxiv.json`, then `history rebuild` and `validate`.
