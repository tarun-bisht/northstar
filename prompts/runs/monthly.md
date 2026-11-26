# Monthly run (1st of each month, 06:15 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. `python scripts/dsys.py period` gives `this_month` (the month to plan, since this runs on the 1st). The previous month is the one to collect feedback for.
2. Feedback for the previous month's package, if `inbox/feedback.md` mentions it: `prompts/feedback.md`. Otherwise do nothing.
3. Inbox ideas: `prompts/inbox.md`.
4. Plan `this_month`: follow `prompts/monthly.md`.
5. **Keep the trust registry current** (`config/reputation.json`, no pressure to add anything). `python scripts/dsys.py reputation suggest` lists authors and organizations that recur in picked and trending papers over the last months but aren't in the registry, with their papers. Add one only when its papers show consistently strong work (check a few abstracts with `candidates arxiv --ids`): a lab or group to `labs` (with aliases and a domain only if you've seen it in an email or official page), a person to `researchers`. For each addition append `{"name", "kind", "date", "evidence": [arXiv ids]}` to `added`. Never remove entries you didn't add this way.
6. Validate, commit `monthly: <this_month>`, push.
7. Final message: one line per deep dive with its section (New in AI, Fundamentals, knowledge, exploration) and light version, the number of challenge problems per subject, and each language's goal for the month.
