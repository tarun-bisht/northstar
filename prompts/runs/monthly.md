# Monthly run (1st of each month, 06:15 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. `python scripts/dsys.py period` gives `this_month` (the month to plan, since this runs on the 1st). The previous month is the one to collect feedback for.
2. Feedback for the previous month's package, if `inbox/feedback.md` mentions it: `prompts/feedback.md`. Otherwise do nothing.
3. Inbox ideas: `prompts/inbox.md`.
4. Plan `this_month`: follow `prompts/monthly.md`.
5. Validate, commit `monthly: <this_month>`, push.
6. Final message: the 1–3 projects in one line each, plus their light versions.
