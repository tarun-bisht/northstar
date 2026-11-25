# Poll collect run (Saturdays and the 1st, 05:53 IST)

Read the user's answers to the topic polls and save them, so the weekly run (Saturday 06:46) and the monthly run (the 1st, 06:15) can use them.

Follow `prompts/runs/_git.md` for setup. If the Slack tools are not available, stop and say so.

1. `python scripts/dsys.py polls list --open` shows open polls with their Slack message `ts`. If there are none, stop.
2. For each open poll, read the thread with `slack_read_thread` (channel from `config/notifications.json`). Take the user's replies: numbers or keys (`2`, `R2 F1`) map to the options, and free text is a topic of their own (keep it general: a concept or field, never private details). Several picks are fine. If there is no reply, the choice is empty.
3. Save: `python scripts/dsys.py polls close --kind <kind> --period <period> --choices '<json list of topics>'` (an empty list when there was no reply). For monthly polls, prefix research picks with `research:` and fundamentals picks with `fundamentals:`.
4. `python scripts/validate.py`, commit `polls: <period>` and push.
5. If there was a reply, post one short reply in the poll thread: `Got it: <topics>. It will be in <period>.` Otherwise post nothing.
6. Final message: what was saved.
