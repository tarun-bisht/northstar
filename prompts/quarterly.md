# Quarterly review

Read `prompts/_shared.md` first.

**Purpose:** a short, public look back at three months, in three parts with their own pages: `quarterly/<YYYY-Qn>/research.html`, `knowledge.html` and `exploration.html`, plus an overview with the numbers. Keep it small. This run should be quick and cheap.

## Steps

1. `python scripts/dsys.py quarterly draft --quarter <YYYY-Qn>`. This writes `content/quarterly/<YYYY>/<YYYY-Qn>.json` with every number filled in (`stats`) and, for each part, the weekly and monthly topics of the quarter. Never edit `stats` by hand.
2. For each part with topics, fill `parts.<part>.summary`: two to four plain lines (at most 600 characters).
   - research: themes in the papers, reading lists and research exercises, and what to lean into next
   - knowledge: what was learned and explored outside AI
   - exploration: culture, people and making, and anything that stood out
   No praise, no judgement, no percentages, no scores. Say so if there is little to go on.
3. Fill each topic's `about`: one plain sentence (at most 200 characters) on what the topic is. Read the package file only if the title isn't enough.
4. **Public file.** No private details: no project names, people, institutions, schedules or reflections. Topics and counts only.
5. Optional system changes, only if clearly helpful and sanitized: move a topic between tiers in `config/interests.json` or add an idea at interest level. One line each in your final message.
6. `python scripts/dsys.py history rebuild && python scripts/validate.py`, then commit `quarterly: <YYYY-Qn> review` and push.
