# arXiv Paper Radar (Monday to Friday)

Read `prompts/_shared.md` first.

The job is to filter. From hundreds of new papers, keep only the good ones that matter for the configured interests, and drop the rest. Fewer and better is the point.

## Steps

1. `python scripts/dsys.py context arxiv --date <today>`. If `is_weekday` is false, stop.
2. Candidates: `python scripts/dsys.py candidates arxiv --date <today> --brief` lists unseen papers from the arXiv API, Hugging Face Daily Papers and alphaXiv trending (fetched at 06:00 IST, gaps refilled at 06:50). Page with `--limit 150 --offset N`. The brief rows carry signals: `hf_upvotes`, `alphaxiv_votes` and `notable_authors`.
   - If the file is missing, or its `failed_sources` lists categories, read `https://arxiv.org/list/<category>/new` for those categories instead, and say so in `notes`.
3. **Shortlist by title, then decide by abstract.** Scan titles against `config/interests.json` (`established.ai_research`, `established.foundations`, sometimes `growth.for_research`) and keep a generous shortlist. Then read the full abstract of every shortlisted paper (`candidates arxiv` without `--brief`, or the abs page) and decide on the abstract, never on the title alone.
4. Interests are broad. Besides the user's core areas, deep learning in general counts, including information retrieval, graph neural networks, diffusion and generative models, world models, deep learning for combinatorial optimization, and AI for science such as protein structure (AlphaFold-style work).
5. Keep only good papers. Signs of quality: a clear contribution, careful evaluation, code or data released, a strong group or venue, or real community interest (`hf_upvotes`, `alphaxiv_votes`). Drop incremental tweaks, thin benchmark chasing and near duplicates. Zero papers on a quiet day is fine.
6. **Notable researchers.** A paper with `notable_authors` (list in `config/sources.json → notable_researchers`), or by another widely recognised researcher or lab, is kept when its abstract touches any interest above, even if it would otherwise be borderline. Give it the tag `notable researcher`.
7. For each kept paper, fill: `id` (`arxiv-<id>`), `arxiv_id`, `title`, `authors`, `url`, `pdf_url`, `submitted`, `categories`, `abstract` (**copied word for word**), `abstract_source`, `research_area` (two or three words), `hf_upvotes` if known, `dimensions`.
8. **Tags, not reasons.** Give 1 to 3 tags from `paper_tags` in the context, most important first. These are the only tags allowed:
   close to your work, useful for your work, new method or architecture, strong result, notable researcher, benchmark or dataset, theory, survey or tutorial, worth knowing.
   Never write a reason or explanation. Never mention a project or method of the user's.
9. Mark the rest as seen: `python scripts/dsys.py papers mark-seen <id> ...`.
10. If a paper is a must read for the week, also add it to the reading list (`prompts/reading_list.md`).
11. Merge: `python scripts/dsys.py daily merge arxiv --date <today> --items /tmp/arxiv.json`, then `history rebuild` and `validate`.
