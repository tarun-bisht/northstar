# Quarterly run (1st of Jan, Apr, Jul, Oct, 06:41 IST)

Start and finish as in `prompts/runs/_common.md`. Then:

1. The quarter to review is the one that just ended (e.g. on 1 April, review `<year>-Q1`). If today is not the first day of a quarter (a run started by hand), review the current quarter so far, and say "so far" in the summary.
2. Follow `prompts/quarterly.md`. It writes a public review file, validates it and commits `quarterly: <YYYY-Qn> review`.
3. Final message: each part's summary, then one line per system change, if any.
