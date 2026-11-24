# Daily run (every day, 07:19 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. Get dates: `python scripts/dsys.py period`. `<today>` is its `date` (Asia/Kolkata).
2. Inbox: follow `prompts/inbox.md` (quick no-op when empty).
3. **arXiv**, Monday–Friday only: follow `prompts/arxiv.md`.
4. **Research updates**: follow `prompts/research_updates.md`.
5. **World radar**: follow `prompts/world.md`.
6. **Daily discovery**: follow `prompts/discovery.md`.
7. **Reading list (every weekday):** update this week's list with 0 to 3 entries: must-reads close to the user's interests, plus important trending papers, new models, lab technical reports or methods every researcher should know about. Use `python scripts/dsys.py reading add --week <this_week>` (`prompts/reading_list.md`). If this week's list doesn't exist yet, create it.
8. **Language pack (required)**: follow `prompts/language.md` (5 minutes, current focus language).
9. `python scripts/dsys.py history rebuild && python scripts/validate.py`, fix any errors, then commit `daily: <today>` and push.
10. Final message (the run summary): items per stream (world items per section), anything notable (one line each for must-read papers), and any limitations hit: list the `failed_sources` from `candidates/arxiv` and `candidates/news`, and any page you could not open. No praise, no padding.

The site shows the day as three pages: `daily/<date>/research.html` (arXiv, research updates, reading list), `news.html` (world radar) and `exploration.html` (discovery, shorts, language).

Budget: keep the whole run focused. Prefer fewer well-verified items over broad but shallow coverage.
