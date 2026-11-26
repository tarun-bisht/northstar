# Slack messages (the last step of the daily run)

The only notifications Northstar sends. Channels are in `config/notifications.json → slack`. Never post anything about sources that failed: only what is ready, and one line for a part that is missing. If the Slack tools are not available, stop and say so.

The daily run does this after it has pushed the day. It commits nothing.

1. `python scripts/dsys.py period` gives `<today>`, `<this_week>`, `<next_week>` and `<this_month>`. Site address: `config/site.json → base_url`.
2. `python scripts/dsys.py status --date <today>` lists `present` and `missing` parts.
3. `python scripts/dsys.py stats show --date <today>` gives the counts (fetched, read, passed, picked) per stream.
4. **Post the day to #northstar-daily** (`slack.daily.id`) with `slack_send_message`, once. Check first with `slack_read_channel` (last 5 messages) that today's message isn't there already. Use this layout, filling only what exists (skip a line whose numbers are missing):

   ```
   ☀️ **Northstar · <Weekday> <d Mon> is ready**

   📄 **Research** · [open](<site>/daily/<today>/research.html)
   <fetched> papers fetched → <read_stage1> read by Haiku → <read_stage2> read by Opus → **<picked> picked**
   <updates fetched> updates → **<updates picked> picked**

   🌍 **News** · [open](<site>/daily/<today>/news.html)
   <headlines> headlines → <stories> stories → **<picked> explained + <briefs> briefs**

   🧭 **Exploration** · [open](<site>/daily/<today>/exploration.html)
   <podcasts_fetched> episodes and <videos_fetched> videos → **<picked> picks**

   🎬 **Shorts** · [open](<site>/daily/<today>/shorts.html) · <shorts picked>

   🗣️ **Languages** · [open](<site>/daily/<today>/languages.html)
   ```
   If a part is missing, end with one line: `⚠️ Missing today: <part names>.` Otherwise no warning line.
5. **Saturday:** if next week's package exists (`status → next_week.package`), post a second message: `📅 **Week of <d Mon> is ready** · [open](<site>/weekly/<next_week>/index.html)` with one line per part (papers, research, knowledge, exploration, languages) giving its item count and, for knowledge, the subjects. If the user's poll pick was used, say which.
6. **The 1st:** if this month's package exists, post `🗓️ **<Month> is ready** · [open](<site>/monthly/<this_month>/index.html)` with the deep dives (one line each) and the number of challenge problems per subject. At a quarter start, also post the quarterly review in **#general** (`slack.general.id`): `📊 **<YYYY-Qn> review is ready** · [open](<site>/quarterly/<YYYY-Qn>/index.html)` with one line per part, if `content/quarterly/<YYYY>/<YYYY-Qn>.json` exists (the quarter that just ended).
7. **#random** (`slack.random.id`): one light post a day. Read `candidates/fun/<today>.json`. Most days post the latest xkcd if it's from the last 3 days, otherwise the random one: `😄 xkcd <num>: **<title>** <url>`. Some days, instead, an original short joke or pun about AI, maths, physics or research life. Never copy someone else's joke or image.
8. Add to the daily run's final message what was posted where.
