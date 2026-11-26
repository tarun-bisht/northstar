# Topic poll run (Thursdays and the 25th, 20:07 IST, model Sonnet)

Ask the user in Slack what to go deep on next. Their answer steers the next weekly and monthly packages. It is optional: no answer means the run picks as usual.

Channel: **#northstar-polls** (`config/notifications.json → slack.polls.id`). If the Slack tools are not available, stop and say so.

Follow `prompts/runs/_git.md` for setup. Then:

1. `python scripts/dsys.py period` gives `<today>`, `next_week` and `next_month`. The cron fires on Thursdays and on the 25th. On a Thursday post the weekly poll. On the 25th post the monthly poll. On a day that is both, post both. On any other day, stop.
2. **Weekly poll (Thursday): the New in AI topic for next week.** Pick 4 options, mostly AI research concepts that are trending now and worth learning properly: use `python scripts/dsys.py candidates arxiv --trending-week <this_week>`, `candidates arxiv --search all`, and `context weekly --period <next_week>` (skip anything covered recently). Post, formatted like this:
   ```
   🗳️ **Weekly poll · <next_week>**
   Which AI topic should **New in AI** cover next week?

   **1.** <topic> · <why, one line>
   **2.** <topic> · <why>
   **3.** <topic> · <why>
   **4.** <topic> · <why>
   **5.** Other · reply with your own topic

   Reply in this thread with a number, several numbers, or your topic. No reply is fine.
   ```
3. **Monthly poll (25th): the research and fundamentals deep dives for next month.** Two lists of 4 options each. Research (New in AI): methods the field is moving on. Fundamentals: the foundations under the user's research (`config/interests.json`), e.g. probability, optimisation, information theory, learning theory, game theory, statistics. Post:
   ```
   🗳️ **Monthly poll · <next_month>**
   What should we go deep on?

   🔬 **Research**
   **R1.** <topic> · <why>
   **R2.** … **R3.** … **R4.** …
   **R5.** Other · reply with your own topic

   📐 **Fundamentals**
   **F1.** <topic> · <why>
   **F2.** … **F3.** … **F4.** …
   **F5.** Other · reply with your own topic

   Reply in this thread with e.g. "R2 F1", or your own topics. No reply is fine.
   ```
4. Record each poll you posted: `python scripts/dsys.py polls open --kind weekly|monthly --period <next_week|next_month> --ts <message ts> --options /tmp/options.json`, where the options file is a JSON list of `{"key": "1", "topic": "..."}` (monthly keys `R1`..`R4`, `F1`..`F4`). Then `python scripts/validate.py`, commit `polls: open <period>` and push.
5. Final message: the polls you posted.

Topics are general (a concept or field), never private details.
