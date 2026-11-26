# Reading poll answers (the first step of the weekly and monthly runs)

Read the user's answers to the topic polls and save them before planning. The weekly run reads the weekly poll, the monthly run the monthly poll. If the Slack tools are not available, skip this and plan as usual.

1. `python scripts/dsys.py polls list --open` shows open polls with their Slack message `ts`. Take the one for the period you're planning. If there is none, skip this.
2. For each open poll, read **the whole thread** under it (`slack_read_thread`, channel `config/notifications.json → slack.polls.id`), and **the user's messages in the channel posted after the poll** (`slack_read_channel` with `oldest` = the poll's ts), in case they replied outside the thread. Nothing before the poll counts. Numbers or keys (`2`, `R2 F1`) map to the options. "Other" or free text is a topic of their own: keep it general (a concept or field), never private details. Several picks are fine. If there is no reply, the choice is empty.
3. Save: `python scripts/dsys.py polls close --kind <kind> --period <period> --choices '<json list of topics>'` (an empty list when there was no reply). For monthly polls, prefix research picks with `research:` and fundamentals picks with `fundamentals:`.
4. If there was a reply, post one short reply in the poll thread: `✅ Got it: **<topics>**. It'll be in <period>.` Otherwise post nothing.
5. The choices are now in `context` as `poll_choices`. They're committed with the package.
