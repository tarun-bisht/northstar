# Daily run (every day, 08:13 IST, main model Sonnet)

Follow `prompts/runs/_git.md` for setup, validation and commit. GitHub Actions scrapes; this run only reads, filters and writes. Cheap models do bulk reading and Opus makes the judgement calls:

| Work | Who |
|---|---|
| News, research updates, putting the day together | you (Sonnet) |
| First reading of every paper abstract | **Haiku** helpers, in parallel (`prompts/paper_triage.md`) |
| Final paper choice, papers of the week, discovery picks, the language pack | **Opus** helpers |

Start helpers with the Agent tool (`model: "haiku"` or `model: "opus"`), give each a complete, standalone task (paths, prompt files, output file), and start independent helpers in the same message so they run in parallel. If the Agent tool isn't available, do the work yourself in the same order.

1. **Dates and files.** `python scripts/dsys.py period` gives `<today>` (Asia/Kolkata) and `<this_week>`.
   Then `python scripts/dsys.py candidates ensure --kinds arxiv,news,podcasts,videos,updates,hf`. It waits for a fetch that is already running, or starts one, and waits until it has finished, retrying failed sources. One call waits up to 9 minutes; if it says to run it again, do, up to 10 calls. Only then go on: everything below filters the fetched files and never replaces them with web search. If a file is still missing after 10 calls, skip the parts that need it.
2. **Answers to questions.** `python scripts/dsys.py polls list --open` lists open questions (`kind: question`) asked in #northstar-ask. For each, read the thread (`slack_read_thread`, channel `config/notifications.json → slack.ask.id`) and the user's channel messages after it (`slack_read_channel` with `oldest` = the question's ts). If there's an answer, save its general topic only (never private details): `python scripts/dsys.py polls close --kind question --period <id> --choices '["<topic>"]'`, and use it today.
3. **Inbox:** follow `prompts/inbox.md` (quick no-op when empty).
4. **alphaXiv feeds.** With the alphaXiv connector, call `get_hot_feed` and `get_for_you_feed` (the user's personal feed) and collect the arXiv ids. Add them to today's pool: `python scripts/dsys.py papers add --date <today> --ids-csv <hot ids> --tag "alphaXiv Hot"`, then the same with the For You ids and `--tag "alphaXiv For You"` (GitHub Actions fetches any paper we don't have yet; duplicates merge by arXiv id). Don't read their summaries: they're for the user, not for choosing. If the connector isn't there, skip this step.
5. **Papers, stage 1 (Haiku).** `python scripts/dsys.py papers stage1 --date <today>` writes compact batches (`batches`, about 100 papers each). Start one Haiku helper per batch, all at once: "Read `prompts/paper_triage.md` in ~/northstar, then sort the papers in `<batch>`. Write verdicts to `<batch with stage1_ replaced by verdict_>`." When all are done: `python scripts/dsys.py papers merge --date <today> --files <verdict files, comma-separated>`.
6. **Papers, page 1.** `python scripts/dsys.py papers enrich --date <today>` (GitHub Actions reads page 1 of each passing paper for affiliations and email domains). If it says to run it again, do, up to 3 calls. Papers it couldn't read are fine.
7. **In parallel, start two Opus helpers** (in one message), then do steps 8 and 9 yourself while they work:
   - **Papers, final choice:** "In ~/northstar, follow `prompts/arxiv.md` for <today>: read `python scripts/dsys.py papers stage2 --date <today>`, choose, write `/tmp/arxiv.json`, mark the rest seen, add one to three papers to this week's papers of the week (`prompts/reading_list.md`, week <this_week>), and merge. Reply with the counts and the top titles."
   - **Discovery and language:** "In ~/northstar, follow `prompts/discovery.md` and then `prompts/language.md` (the daily pack) for <today>, and merge both. Reply with the titles."
8. **Research updates:** follow `prompts/research_updates.md` (compact reading, plus up to 8 targeted X and LinkedIn searches).
9. **World Radar:** follow `prompts/world.md` (awareness across all categories, interest-matched stories, depth pieces paired with events).
10. When both helpers have replied: `python scripts/dsys.py history rebuild && python scripts/validate.py`, fix any errors, then commit `daily: <today>` and push. The counts for the Slack message are already in `state/stats/<today>.json`; commit that file too.
11. Final message: items per stream, the top papers in one line each, and anything that could not be made. No praise, no padding.

The site shows the day as four pages: `daily/<date>/research.html` (papers, research updates), `news.html`, `exploration.html` (discovery, shorts) and `languages.html`. The Slack digest (09:43) announces it.
