# Research Updates (daily, separate from arXiv)

Read `prompts/_shared.md` first.

**Purpose:** catch the research developments that are *not* arXiv listings: lab announcements, researcher posts and threads, new methods/results/benchmarks/tools, conference news (deadlines, acceptances, policy changes), technical debates, unusually useful resources. **Not generic AI news**: no funding rounds, product launches or hype unless they change research practice.

## Steps

1. `python scripts/dsys.py context research_updates --date <today>`. Avoid anything in `recent_items` (same story) unless there is a genuine new development; then set a new id and mention the earlier one in `what_happened`.
2. Read the fetched updates in one compact pass: `python scripts/dsys.py candidates updates --date <today> --compact`. Short keys: `n` row, `t` title, `s` source, `k` kind (lab, researcher, newsletter, news, social, discussion), `u` link, `d` date, `x` full summary, `pts` Hacker News points, `likes` Bluesky likes. Items already published in the last 3 days are removed. Sources: lab, researcher and newsletter feeds (the Alan Turing Institute's feeds cover Anthropic, Claude, Mistral, Cohere, Ai2, Mila, xAI and the AI Security Institute), Google News bridges for Meta, xAI, DeepSeek and Qwen, Reddit, Bluesky and Hacker News. Use the links as they are: they were fetched by GitHub Actions.
   Also:
   - `python scripts/dsys.py candidates hf --date <today>`: trending models, datasets and spaces on Hugging Face.
   - `python scripts/dsys.py candidates podcasts --date <today>`: AI and research podcast episodes from today or yesterday that match the interests can be an update (`kind: podcast`).
   - **X and LinkedIn posts (the only web searches here):** run 5 to 8 targeted searches built from the interest keywords in `config/interests.json` (all of them, not only AI), several keywords per search, for example `site:x.com ("machine unlearning" OR "interpretability" OR "AI agents") paper OR release` and `site:linkedin.com ("world models" OR "diffusion models") research`. Keep only posts by researchers or labs that announce something real (a paper, release, dataset, result). Use the post URL from the search result. If a post can't be confirmed from the result, skip it.
3. Filter for quality, and never drop a real development to keep the list short. Include an item if a researcher in these areas would be glad to know it today. Order them: the clearest and most important as `priority: top`, the rest that pass as `priority: more` (shown folded). Deduplicate by story: one item per development, with the best source.
4. For each item: `what_happened` (facts, 1–3 sentences), `why_it_matters` (for researchers in these areas, in general public-safe terms), `what_to_watch` (what would confirm, refute or extend it), `source` (the item's own link from the file: prefer the lab post or the author's blog over a discussion thread), `published` (source date), `kind`, `research_area`, `uncertainty` when claims are unreplicated.
5. Write `/tmp/ru.json` and merge: `python scripts/dsys.py daily merge research_updates --date <today> --items /tmp/ru.json`. Add `notes` describing coverage, e.g. which sources failed today (`errors` in the updates file).
6. `history rebuild`, `validate`.

Keep every field to one or two short sentences. If an item is a paper or technical report that is a must read, also add it to this week's papers of the week list (`prompts/reading_list.md`).
