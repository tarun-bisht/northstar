# Monthly run (1st of each month, 06:15 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. `python scripts/dsys.py period` gives `this_month` (the month to plan, since this runs on the 1st). The previous month is the one to collect feedback for.
2. Feedback for the previous month's package, if `inbox/feedback.md` mentions it: `prompts/feedback.md`. Otherwise do nothing.
3. Inbox ideas: `prompts/inbox.md`.
4. Plan `this_month`: follow `prompts/monthly.md`.
5. Validate, commit `monthly: <this_month>`, push.
6. Final message: one line per deep dive with its section (New in AI, Fundamentals, knowledge, exploration) and light version, the number of challenge problems per subject, and each language's goal for the month.
