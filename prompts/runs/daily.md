# Daily run (every day, 07:19 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. Get dates: `python scripts/dsys.py period`. `<today>` is its `date` (Asia/Kolkata).
2. Inbox: follow `prompts/inbox.md` (quick no-op when empty).
3. **arXiv**, Monday–Friday only: follow `prompts/arxiv.md`.
4. **Research updates**: follow `prompts/research_updates.md`.
5. **World radar**: follow `prompts/world.md`.
6. **Daily discovery**: follow `prompts/discovery.md`.
7. **Reading list:** if you found a must read today (arXiv, a lab report, a widely discussed paper), add it with `python scripts/dsys.py reading add` (`prompts/reading_list.md`).
8. **Language pack (required)**: follow `prompts/language.md` (5 minutes, current focus language).
9. `python scripts/dsys.py history rebuild && python scripts/validate.py`, fix any errors, then commit `daily: <today>` and push.
10. Final message (the run summary): items per stream, anything notable (one line each for must-read papers), and any limitations hit (e.g. candidates missing, a source unreachable). No praise, no padding.

Budget: keep the whole run focused. Prefer fewer well-verified items over broad but shallow coverage.
