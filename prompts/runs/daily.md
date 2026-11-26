# Daily run (every day, 08:13 IST, main model Sonnet)

One task does the whole day: papers, news, updates, discovery, the language pack, shorts, the topic polls on Thursdays and the 25th, and the Slack messages.

Start and finish as in `prompts/runs/_common.md`. GitHub Actions scrapes; this run only reads, filters and writes.

**You coordinate; helpers read.** Everything you read stays in your context and is paid for again on every later step, so leave the big reads (papers, news, updates, videos, shorts) to helpers. Each starts fresh, reads one part, merges it, and replies in a few lines. Models follow one rule: cheap models filter, Sonnet chooses and writes, Opus only where it must be right.

| Work | Who |
|---|---|
| First reading of every paper abstract | **Haiku** helpers, one per batch (`prompts/paper_triage.md`) |
| News shortlist from every headline | a **Haiku** helper (`prompts/news_shortlist.md`) |
| Final paper choice and papers of the week | a **Sonnet** helper (`prompts/arxiv.md`) |
| World Radar from the shortlist | a **Sonnet** helper (`prompts/world.md`) |
| Research updates | a **Sonnet** helper (`prompts/research_updates.md`) |
| Discovery recommendations (videos, podcasts, reads) | a **Sonnet** helper (`prompts/discovery.md`) |
| Shorts | a **Sonnet** helper (`prompts/youtube_shorts.md`) |
| The language pack (must be correct) | an **Opus** helper (`prompts/language.md`) |
| Waiting, the overview, committing, Slack | you (Sonnet) |

Start helpers with the Agent tool (`model: "haiku"`, `"sonnet"` or `"opus"`), each with a complete standalone task: "In ~/northstar, follow `<prompt>` for <today> [details]. Merge, don't commit. Reply in at most five lines." Start independent helpers in the same message so they run in parallel. If the Agent tool isn't available, do the work yourself in the same order.

1. **Dates and files.** `python scripts/dsys.py period` gives `<today>` (Asia/Kolkata) and `<this_week>`. If `load_this_week` is `light`, today is a **light day**: every part uses the sizes in `config/preferences.json → daily.light` instead of the sizes in its prompt, keeping only its best. Tell each helper so.
   Then `python scripts/dsys.py candidates ensure --kinds arxiv,news,podcasts,videos,updates,hf,youtube`. It waits for a fetch that is already running, or starts one, and waits until it has finished, retrying failed sources. One call waits up to 9 minutes; if it says to run it again, do, up to 10 calls. Only then go on: everything below filters the fetched files and never replaces them with web search. If a file is still missing after 10 calls, skip the parts that need it.
2. **Answers to questions.** `python scripts/dsys.py polls list --open` lists open questions (`kind: question`) asked in #northstar-ask. For each, read the thread (`slack_read_thread`, channel `config/notifications.json → slack.ask.id`) and the user's channel messages after it (`slack_read_channel` with `oldest` = the question's ts). If there's an answer, save its general topic only (never private details): `python scripts/dsys.py polls close --kind question --period <id> --choices '["<topic>"]'`, and use it today.
3. **Inbox:** follow `prompts/inbox.md` (quick no-op when empty).
4. **alphaXiv feeds.** With the alphaXiv connector, call `get_hot_feed` and `get_for_you_feed` (the user's personal feed) and collect the arXiv ids. Add them to today's pool: `python scripts/dsys.py papers add --date <today> --ids-csv <hot ids> --tag "alphaXiv Hot"`, then the same with the For You ids and `--tag "alphaXiv For You"` (GitHub Actions fetches any paper we don't have yet; duplicates merge by arXiv id). Don't read their summaries: they're for the user, not for choosing. If the connector isn't there, skip this step.
5. **First wave, all in one message.** `python scripts/dsys.py papers stage1 --date <today>` writes the paper batches (`batches`, each with `read`, `write` and `papers`). Then start together:
   - one **Haiku** helper per batch: "Read only `prompts/paper_triage.md` in ~/northstar, then sort all <papers> papers in `<read>` (one per line). Write verdicts to `<write>`."
   - **Haiku**, news shortlist: "follow `prompts/news_shortlist.md`".
   - **Sonnet**, research updates: "follow `prompts/research_updates.md`; reply with up to 2 update ids for the overview".
   - **Sonnet**, discovery: "follow `prompts/discovery.md`; reply with up to 5 ids for the overview, best first, from different sections".
   - **Sonnet**, shorts: "follow `prompts/youtube_shorts.md`; reply with the count and the language and tier split".
   - **Opus**, language: "follow `prompts/language.md`, the daily pack".
6. **When the news shortlist is done,** start a **Sonnet** helper: "follow `prompts/world.md`, starting from the shortlist".
7. **When all paper batches are done:** `python scripts/dsys.py papers merge --date <today> --files <all write paths, comma-separated>`. If a verdict file is missing or short, run that batch again once. Then `python scripts/dsys.py papers enrich --date <today>` (page 1 for affiliations; if it says to run it again, do, up to 3 calls).
8. Then start a **Sonnet** helper for the final paper choice: "follow `prompts/arxiv.md`: read `papers stage2`, write your choices and build the items with `papers pick`, mark the rest seen, add one to three papers to papers of the week (`prompts/reading_list.md`, week <this_week>), and merge. Reply with the counts, the top titles and up to 5 paper ids for the overview, best first."
9. Wait for every helper's reply. If one failed, run it once more; if it fails again, leave that part out and name it in the final message.
10. **Overview and ranking.** When all helpers have replied, mark the best: at most 5 items per part. Exploration shows them as its Overview (left out of the main list). Research shows no Overview: the marked papers and updates go to the top of their lists, which are ranked best first, and Slack takes the first three of each. Research: from the paper and research-update helpers' ids, `python scripts/dsys.py daily overview --date <today> --part research --ids <ids, best first>`. Exploration: the discovery helper's picks, `--part exploration --ids ...`. If you skip a part, it falls back to the top items automatically.
11. Finish as in `_common.md` (validate, commit `daily: <today>`, push). This also commits the counts in `state/stats/<today>.json`.
12. **Slack, polls (Thursdays and the 25th only):** follow `prompts/runs/topic_poll.md`.
13. **Slack, messages (every day):** follow `prompts/runs/slack_digest.md`.
14. Final message: items per stream, the top papers in one line each, and anything that could not be made. No praise, no padding.
