# Slack digest run (every day, 09:07 IST)

The only notification Northstar sends: one short Slack message a day with links to today's pages, and any failure. Mobile and email notifications are off for every task.

The channel is set in `config/notifications.json` (`slack.channel_id`). Post only there. If the Slack tools are not available in this session, stop and say so in the final message.

Follow `prompts/runs/_git.md` for setup (clone or update). This run commits nothing.

1. `python scripts/dsys.py period` gives `<today>`. `python scripts/dsys.py status --date <today>` prints what exists today and what went wrong: missing daily streams, sources that failed in `candidates/*/<today>.json`, validation errors, and on Saturdays and the 1st whether next week's package or this month's package exists.
2. Check GitHub Actions (read only): `gh api repos/tarun-bisht/northstar/actions/runs?per_page=20` and note any run from the last 24 hours with `conclusion: failure`, with its name and `html_url`.
3. If the `list_triggers` tool is available, check the Northstar scheduled tasks and note any whose last run failed.
4. Post one message with `slack_send_message` to the channel. Keep it short, plain text, links on their own lines:
   - first line: `Northstar, <weekday> <d Mon>` and, if anything failed, ` (needs a look)`
   - today's pages: Research, News, Exploration, Languages (`<site>/daily/<today>/<part>.html`, site from `config/site.json → base_url`). Skip a part that has no content today.
   - on Saturday: next week's pages (`<site>/weekly/<next_week>/index.html`). On the 1st: this month's (`<site>/monthly/<this_month>/index.html`).
   - one line per problem, from steps 1 to 3, with a link when there is one. If nothing failed, say nothing about failures.
5. Final message: the text you posted, or why you could not post.

Never post private details (see CLAUDE.md rule 5). One message per day: if a message starting `Northstar, <weekday> <d Mon>` is already in the channel today (`slack_read_channel`, last 10 messages), do not post again.
