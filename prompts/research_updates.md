# Research Updates (daily, separate from arXiv)

Read `prompts/_shared.md` first.

**Purpose:** catch the research developments that are *not* arXiv listings: lab announcements, researcher posts and threads, new methods/results/benchmarks/tools, conference news (deadlines, acceptances, policy changes), technical debates, unusually useful resources. **Not generic AI news**: no funding rounds, product launches or hype unless they change research practice.

## Steps

1. `python scripts/dsys.py context research_updates --date <today>`. Avoid anything in `recent_items` (same story) unless there is a genuine new development; then set a new id and mention the earlier one in `what_happened`.
2. Start from the fetched files, then search (last ~48h), focused on their areas (`config/interests.json → research`):
   - `python scripts/dsys.py candidates updates --date <today>`: lab blogs, researcher blogs and newsletters (Interconnects, Ahead of AI, Import AI, Lil'Log and others), Hacker News AI stories with points and comments, r/MachineLearning top posts. These URLs were fetched by Actions, so they are real, but open or search for one before you cite it in a run (web access rules in `prompts/_shared.md`)
   - `python scripts/dsys.py candidates hf --date <today>`: trending models, datasets and spaces on Hugging Face (a new open model or benchmark dataset is often the update)
   - papers with the signal `discussed on X` in `candidates arxiv --ranked`
   - web search for e.g. "unlearning", "jailbreak", "interpretability", "agent security", "LLM judge", "prompt injection" plus "new", "release", "benchmark", restricted to recent results
   - X/Twitter and LinkedIn posts **only** if reachable via search results or the post page. Never fabricate or reconstruct posts; if you cannot open it, do not include it.
   - conference sites (NeurIPS, ICML, ICLR, ACL/ARR, EMNLP, USENIX Security, IEEE S&P, SaTML) for deadline or policy news
3. Filter aggressively. Include an item only if a researcher in their area would be glad to know it today. Typical 0–6, max `preferences.daily.max_research_updates`.
4. For each item: `what_happened` (facts, 1–3 sentences), `why_it_matters` (for researchers in these areas, in general public-safe terms), `what_to_watch` (what would confirm, refute or extend it), `source` (prefer the original: the lab post, the GitHub repo, the author's thread, not a news rewrite), `published` (source date), `kind`, `research_area`, `uncertainty` when claims are unreplicated.
5. Write `/tmp/ru.json` and merge: `python scripts/dsys.py daily merge research_updates --date <today> --items /tmp/ru.json`. Add `notes` describing coverage, e.g. "X not reachable today; covered via lab blogs and GitHub".
6. `history rebuild`, `validate`.

Keep every field to one or two short sentences. If an item is a paper or technical report that is a must read, also add it to this week's papers of the week list (`prompts/reading_list.md`).
