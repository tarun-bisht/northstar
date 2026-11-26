# Monthly run (1st of each month, 06:15 IST)

Start and finish as in `prompts/runs/_common.md`. Then:

1. `python scripts/dsys.py period` gives `this_month` (the month to plan, since this runs on the 1st). The previous month is the one to collect feedback for.
2. Feedback for the previous month's package, if `inbox/feedback.md` mentions it: `prompts/feedback.md`. Otherwise do nothing.
3. Inbox ideas: `prompts/inbox.md`.
4. **Poll answers:** follow `prompts/runs/poll_collect.md` for the monthly poll of `this_month`.
5. Plan `this_month`: follow `prompts/monthly.md`.
6. **Keep the trust registry current** (`config/reputation.json`, no pressure to add anything). `python scripts/dsys.py reputation suggest` lists authors and organizations that recur in picked and trending papers over the last months but aren't in the registry, with their papers. Add one only when its papers show consistently strong work (check a few abstracts with `candidates arxiv --ids`): `python scripts/dsys.py reputation add --kind lab|researcher --name "<name>" --evidence <arXiv ids> [--aliases ...] [--domains ...] [--lab-kind ...]`. Give a domain only if you've seen it in an email or an official page. Never edit the file by hand: it is large, and existing entries stay as they are.
7. Validate, commit `monthly: <this_month>`, push. The daily run announces it in Slack.
8. Final message: one line per deep dive with its section (New in AI, Fundamentals, knowledge, exploration) and light version, the number of challenge problems per subject, and each language's goal for the month.
