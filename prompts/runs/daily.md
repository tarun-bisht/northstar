# Daily run (every day, 08:13 IST, main model Sonnet)

One task does the whole day: papers, news, updates, discovery, the language pack, shorts, the topic polls on Thursdays and the 25th, and the Slack messages.

Start and finish as in `prompts/runs/_common.md`. GitHub Actions scrapes; this run only reads, filters and writes. Cheap models do bulk reading and Opus makes the judgement calls:

| Work | Who |
|---|---|
| News, research updates, putting the day together | you (Sonnet) |
| First reading of every paper abstract | **Haiku** helpers, in parallel (`prompts/paper_triage.md`) |
| Final paper choice, papers of the week, discovery picks, the language pack | **Opus** helpers |
| Shorts (`prompts/youtube_shorts.md`) | a **Sonnet** helper |

Start helpers with the Agent tool (`model: "haiku"`, `"sonnet"` or `"opus"`), give each a complete, standalone task (paths, prompt files, output file), and start independent helpers in the same message so they run in parallel. If the Agent tool isn't available, do the work yourself in the same order.

1. **Dates and files.** `python scripts/dsys.py period` gives `<today>` (Asia/Kolkata) and `<this_week>`. If `load_this_week` is `light`, today is a **light day**: every part uses the sizes in `config/preferences.json → daily.light` instead of the sizes in its prompt, keeping only its best. Tell each helper so.
   Then `python scripts/dsys.py candidates ensure --kinds arxiv,news,podcasts,videos,updates,hf,youtube`. It waits for a fetch that is already running, or starts one, and waits until it has finished, retrying failed sources. One call waits up to 9 minutes; if it says to run it again, do, up to 10 calls. Only then go on: everything below filters the fetched files and never replaces them with web search. If a file is still missing after 10 calls, skip the parts that need it.
2. **Answers to questions.** `python scripts/dsys.py polls list --open` lists open questions (`kind: question`) asked in #northstar-ask. For each, read the thread (`slack_read_thread`, channel `config/notifications.json → slack.ask.id`) and the user's channel messages after it (`slack_read_channel` with `oldest` = the question's ts). If there's an answer, save its general topic only (never private details): `python scripts/dsys.py polls close --kind question --period <id> --choices '["<topic>"]'`, and use it today.
3. **Inbox:** follow `prompts/inbox.md` (quick no-op when empty).
4. **alphaXiv feeds.** With the alphaXiv connector, call `get_hot_feed` and `get_for_you_feed` (the user's personal feed) and collect the arXiv ids. Add them to today's pool: `python scripts/dsys.py papers add --date <today> --ids-csv <hot ids> --tag "alphaXiv Hot"`, then the same with the For You ids and `--tag "alphaXiv For You"` (GitHub Actions fetches any paper we don't have yet; duplicates merge by arXiv id). Don't read their summaries: they're for the user, not for choosing. If the connector isn't there, skip this step.
5. **Papers, stage 1 (Haiku).** `python scripts/dsys.py papers stage1 --date <today>` writes batches of 40 papers (`batches`, each with a `read` and a `write` path). Start one Haiku helper per batch, all at once: "Read `prompts/paper_triage.md` in ~/northstar, then sort all <papers> papers in `<read>` (one per line). Write verdicts to `<write>`." When all are done: `python scripts/dsys.py papers merge --date <today> --files <all write paths, comma-separated>`. If a verdict file is missing or short, run that batch again once.
6. **Papers, page 1.** `python scripts/dsys.py papers enrich --date <today>` (GitHub Actions reads page 1 of each passing paper for affiliations and email domains). If it says to run it again, do, up to 3 calls. Papers it couldn't read are fine.
7. **In parallel, start three helpers** (in one message), then do steps 8 and 9 yourself while they work:
   - **Papers, final choice (Opus):** "In ~/northstar, follow `prompts/arxiv.md` for <today>: read `python scripts/dsys.py papers stage2 --date <today>`, choose, write `/tmp/arxiv.json`, mark the rest seen, add one to three papers to this week's papers of the week (`prompts/reading_list.md`, week <this_week>), and merge. Reply with the counts, the top titles, and the one paper to start the day with (its id and one line on why)."
   - **Discovery and language (Opus):** "In ~/northstar, follow `prompts/discovery.md` and then `prompts/language.md` (the daily pack) for <today>, and merge both. Reply with the titles, and the one exploration pick to start the day with (its id and one line on why)."
   - **Shorts (Sonnet):** "In ~/northstar, follow `prompts/youtube_shorts.md` for <today> (the shorts file is already fetched) and merge. Don't commit. Reply with the count and the language and tier split."
8. **Research updates:** follow `prompts/research_updates.md`.
9. **World Radar:** follow `prompts/world.md`.
10. **Start here.** When all helpers have replied, pick the day's way in: the helpers' paper and exploration picks, and the one news story you'd most want the user to read. `python scripts/dsys.py daily start-here --date <today> --pick <paper id>="<why>" --pick <story id>="<why>" --pick <exploration id>="<why>"`. One plain line each, under 160 characters, saying what the user gets from it. Skip a part that has nothing worth it.
11. Finish as in `_common.md` (validate, commit `daily: <today>`, push). This also commits the counts in `state/stats/<today>.json`.
12. **Slack, polls (Thursdays and the 25th only):** follow `prompts/runs/topic_poll.md`.
13. **Slack, messages (every day):** follow `prompts/runs/slack_digest.md`.
14. Final message: items per stream, the top papers in one line each, and anything that could not be made. No praise, no padding.
