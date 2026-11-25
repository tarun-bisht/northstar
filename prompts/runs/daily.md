# Daily run (every day, 08:13 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. Get dates: `python scripts/dsys.py period`. `<today>` is its `date` (Asia/Kolkata).
   Then make sure today's fetched files are complete: `python scripts/dsys.py candidates ensure --kinds arxiv,news,podcasts,videos,updates,hf`. GitHub's scheduled fetch can start hours late or not at all, so this waits for a fetch that is already running, or starts one itself, waits until it has finished, and retries failed sources. One call waits up to 9 minutes, checking every minute. If it reports `ok: false` and says to run it again, run it again, up to 10 calls (about 90 minutes). Wait for it, and only then start the streams below: they filter the fetched files and never replace them with web search. If files are still missing after 10 calls, skip the streams whose files are missing, post the failure to Slack (`prompts/runs/_git.md`) and finish the rest. If it reports `failed_sources`, use the files as they are and list those sources in the final message.
2. Inbox: follow `prompts/inbox.md` (quick no-op when empty).
3. **arXiv**, Monday–Friday only: follow `prompts/arxiv.md`.
4. **Research updates**: follow `prompts/research_updates.md`.
5. **World radar**: follow `prompts/world.md`.
6. **Daily discovery**: follow `prompts/discovery.md`.
7. **Papers of the week (every weekday):** update this week's list (a weekly part, not shown in daily) with 0 to 3 entries: must-reads close to the user's interests, plus important trending papers, new models, lab technical reports or methods every researcher should know about. Use `python scripts/dsys.py reading add --week <this_week>` (`prompts/reading_list.md`). If this week's list doesn't exist yet, create it.
8. **Language pack (required)**: follow `prompts/language.md` (5 minutes, current focus language).
9. `python scripts/dsys.py history rebuild && python scripts/validate.py`, fix any errors, then commit `daily: <today>` and push.
10. Final message (the run summary): items per stream (world items per section), anything notable (one line each for must-read papers), and any limitations hit: list the `failed_sources` from `candidates/arxiv` and `candidates/news`, and any page you could not open. No praise, no padding.

The site shows the day as four pages: `daily/<date>/research.html` (arXiv, research updates), `news.html` (world radar), `exploration.html` (discovery, shorts) and `languages.html` (the language pack).

Budget: keep the whole run focused. Prefer fewer well-verified items over broad but shallow coverage.
