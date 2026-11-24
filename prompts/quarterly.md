# Quarterly review

Read `prompts/_shared.md` first.

**Purpose:** a short, public look back at three months: numbers, a few lines on research and discovery, and the topics the weekly and monthly packages covered. It is published on the site and in `feeds/quarterly.xml`. Keep it small. This run should be quick and cheap.

## Steps

1. `python scripts/dsys.py quarterly draft --quarter <YYYY-Qn>`. This writes `content/quarterly/<YYYY>/<YYYY-Qn>.json` with every number filled in and the list of weekly and monthly topics. Never edit `stats` by hand.
2. Fill `summary`: five or six short lines, at most 900 characters, about **research and discovery only**. What themes ran through the papers, reading lists and research updates? What did the weekly and monthly packages cover? What could Northstar lean into next quarter? Leave out news and shorts. Plain sentences, no praise, no judgement, no percentages, no scores. Say so if there is little to go on.
3. Fill each topic's `about`: one plain sentence (at most 200 characters) saying what the topic is. Read the package file only if the title isn't enough.
4. **Public file.** No private details: no project names, people, institutions, schedules or reflections. Topics and counts only.
5. Optional system changes, only if clearly helpful and sanitized: move a topic between tiers in `config/interests.json` or add an idea at interest level. One line each in your final message.
6. `python scripts/dsys.py history rebuild && python scripts/validate.py`, then commit `quarterly: <YYYY-Qn> review` and push.

Final message: the summary, then one line per system change, if any.
