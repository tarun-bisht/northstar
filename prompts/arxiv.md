# Paper Radar (every day): final choice

Read `prompts/_shared.md` first.

The job is to filter, and never to lose quality work. Keep the papers that are high quality **and** on the user's interests, and the high-quality papers that matter for the field even with little overlap. The bar is real: on a normal day that means roughly 10 to 40 papers, with 5 to 15 of them `top`, and **never more than 40** (`papers pick` keeps the first 40 of your list). A bigger list means the bar slipped: keep only papers worth the user's time, the most relevant first. Order them **most relevant first**: that order is exactly how the user reads them, top to bottom, stopping when time runs out. The best picks are `priority: top`, everything else that passes the bar `priority: more`, listed after them.

## Where candidates come from

`candidates/arxiv/<today>.json`, fetched by GitHub Actions every day (the daily run waits for it with `candidates ensure`): the arXiv API for every category in `config/sources.json → arxiv.categories`, Hugging Face Daily Papers, alphaXiv lists and one alphaXiv search per interest, and papers discussed on Reddit and Bluesky (`reddit_mentions`, `bluesky_mentions`, `bluesky_likes`). arXiv publishes nothing on Saturday and Sunday mornings in India and on some holidays. Those days the other sources still bring papers, so the radar runs every day.

Papers come only from these files, never from web search.

## The stages (the daily run does 1 to 3, you do 4)

1. **Python** (`dsys.py papers stage1`): drops papers already seen, keeps every paper that matches an interest or has a quality signal, and writes compact batches.
2. **Cheap model** (`prompts/paper_triage.md`): reads every abstract in the batches and sorts each into strong, field or no. Calibrated: usually 15 to 30% pass, and only a true doubt is kept.
3. **Page 1** (`dsys.py papers enrich`): GitHub Actions reads page 1 of each passing paper for affiliations and email domains, and sets the trust flag (`config/reputation.json`).
4. **You** (`dsys.py papers stage2`): the passing papers in full, with lane, affiliations, `trusted`, `trust_matches`, interests, signals and buzz.

## Steps

1. `python scripts/dsys.py papers stage2 --date <today>` prints the papers that passed the first reading. Read every one. Never decide from a title alone. Never open PDFs. The abstract, affiliations and signals are the evidence.
2. `python scripts/dsys.py context arxiv --date <today>` for recent picks (don't repeat a paper).
3. **Judge quality.** Rate each paper 1 to 5 in your head:
   - **5, keep as top:** a clear, specific contribution; strong evidence (experiments on standard benchmarks against strong baselines, real theory, or a large careful analysis); concrete results stated; plus at least one outside signal (trusted group, venue, community votes, discussion, released code).
   - **4, keep:** clear contribution and solid evidence, even without outside signals.
   - **3, drop**, unless it is very close to the user's own research topics. A 3 that only touches an interest is not kept.
   - **1 to 2, drop.** Red flags: a "novel framework" with no stated results; one small dataset; a combination of existing tricks; overclaiming without evidence; a prompt wrapper with no evaluation; an application with no transferable insight; a vague abstract.
4. **What to keep (vision §6).** Both kinds count, matching the two lanes:
   - *direct relevance:* close to or useful for the user's research interests
   - *research development value:* an important method, a challenged assumption, a useful theory, a strong benchmark, an exposed failure mode, a useful methodology, a connection between fields, an important negative result, a field-shifting idea
   - **Trending is a reason on its own.** A high-quality paper with high buzz is kept even with little overlap: "this is becoming widely discussed" is valuable for a researcher.
   - **Trust is a hint, not a verdict.** `trusted: 1` (a known university, lab, researcher or email domain) raises confidence. It never rescues an empty abstract, and `trusted: 0` never sinks a strong one. Tag notable groups `notable researcher`.
5. **Order, never cap.** `priority: top` for the papers you'd tell a friend to read today (usually 5 to 12, balanced across areas). Everything else that passes the bar is `priority: more`. Nothing good is dropped to keep the list short.
6. **Write only your judgement.** For each kept paper, best first, write one entry to `/tmp/arxiv_choices.json`: `{"arxiv_id", "priority", "research_area" (two or three words), "tags", "dimensions"}`. Then `python scripts/dsys.py papers pick --date <today> --choices /tmp/arxiv_choices.json` builds the full items in `/tmp/arxiv.json` from the fetched data: title, authors, the arxiv.org link (the site turns it into an alphaXiv link), dates, categories, the abstract word for word, affiliations, trust, lane and upvotes. Never retype those. If it reports `missing` ids, fix the ids. Never use alphaXiv summaries to judge a paper.
7. **Tags, not reasons.** Give 1 to 3 tags from `paper_tags`, most important first. These are the only tags allowed:
   close to your work, useful for your work, new method or architecture, strong result, notable researcher, benchmark or dataset, theory, survey or tutorial, worth knowing.
   Never write a reason or explanation. Never mention a project or method of the user's.
8. Mark every paper you read but did not keep as seen: `python scripts/dsys.py papers mark-seen <id> ...`.
9. **Papers of the week:** the best one to three papers of the day (yours, or trending and important for any researcher) also go on this week's papers of the week list (`prompts/reading_list.md`).
10. Merge the built items: `python scripts/dsys.py daily merge arxiv --date <today> --items /tmp/arxiv.json` (it records the counts for the Slack message), then `history rebuild` and `validate`. Put a one-line `notes` on the day: how many fetched, read, passed and kept.
