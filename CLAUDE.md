# Northstar: instructions for Claude

Northstar is a public, forkable personal discovery and growth companion. Claude generates content into JSON; GitHub Actions validates it and publishes RSS feeds and a website. `docs/vision.md` is why it exists, `docs/how_it_works.md` is the map of the whole system, and `prompts/runs/` holds one runbook per scheduled run.

## Rules

0. **The vision comes first.** `docs/vision.md` says what Northstar is for: curation and discovery, never tracking. Read it before generating anything, and test every choice against its guiding question: *does this help the person discover, understand, practise, create or experience something genuinely worthwhile, while respecting their attention and freedom?*
1. Read `prompts/_shared.md` before generating anything.
2. Interests have three tiers (`config/interests.json`): **established** (most items: AI research and its foundations), **growth** (steady steps: maths, physics, neuroscience, philosophy, people skills, history, art), **exploration** (always some: worthwhile surprises). Every item has a `tier` and `dimensions`.
3. Never fabricate papers, videos, URLs, dates or facts. Omit what you can't verify.
4. Optional means optional: no streaks, scores, quotas or automatic carry-over. User intent beats the algorithm.
5. Everything is public. Never store private details (project names, unpublished work, people, institutions, health, relationships, schedules, travel dates, raw feedback, reflections). **Translate, never record**: save only general topics.
6. Finish every change with `python scripts/dsys.py history rebuild && python scripts/validate.py`. Never commit invalid content.

## Enforced content rules

- **Parts, each on its own page:** daily = Research (papers, research updates, reading list), News (world radar by category), Exploration (discovery by type, shorts, language). Weekly, monthly and quarterly = Research, Knowledge, Exploration (`docs/how_it_works.md` §2).
- **Papers:** read the code-ranked shortlist (`candidates arxiv --ranked`), judge each abstract against the rubric in `prompts/arxiv.md`, keep trending and notable papers that pass it. Abstracts copied word for word. Tags from the fixed `paper_tags` list only, never free-text reasons.
- **Reading list** (`reading.xml`): at least 3 entries every week in two groups, *For you* and *Trending this week* (`candidates arxiv --trending-week`), kept current by the daily runs.
- **World Radar:** 12 to 20 explained items across at least 7 of 12 categories (including leadership changes) plus 15 to 30 one-line briefs. Markets, technology and explainers every day, with a Conversation explainer when available (`prompts/world.md`).
- **Daily Discovery:** an established-tier podcast, a video, lecture or documentary, and at least one item per tier. Shorts: at least one per tier.
- **Weekly:** all six pillars of development every normal week, items grouped by `section`, at least 2 maths and 2 physics questions (`subject`), exploration the largest part. Learning items have detailed steps and real resources (book chapters, lectures, blogs, papers).
- **Monthly:** a research, a knowledge and an exploration deep dive (unless light), the exploration one rotating through people, culture and making; each a week-by-week syllabus with resources, and at least one growth item.
- **Quarterly:** `quarterly draft` fills the numbers and topics. Write only the short summaries and one-line abouts.
- **Writing:** plain simple English, short, main point first, no semicolons or em dashes.
- **Languages** (`config/languages.json`): a 5-minute pack every day (current focus), a lesson per language every week, a plan per language every month.

## Which prompt

| Situation | Prompt |
|---|---|
| Scheduled runs | `prompts/runs/daily.md`, `shorts.md`, `weekly.md`, `monthly.md`, `quarterly.md` |
| Changing how the system works | `docs/how_it_works.md` (update it too) |
| "Recommend me…", "I want to try…" | `prompts/on_demand_recommendations.md`, then `prompts/inbox.md` to record it |
| User shares interests, projects, trips, how busy they are | `prompts/update_interests.md` |
| Feedback on a week or month | `prompts/feedback.md` |
| Weekly paper reading list | `prompts/reading_list.md` |
| Language lessons, packs, plans | `prompts/language.md` |
| "Let's practise Japanese", "quiz me" | `prompts/language_practice.md` |

## Commands

```bash
python scripts/dsys.py period                                  # this/next week and month
python scripts/dsys.py context <stream> [--period P]           # what a planner should know
python scripts/dsys.py daily merge <stream> --items file.json
python scripts/dsys.py ideas add|list|schedule|defer|drop|resize|replace|remove ...
python scripts/dsys.py interests list|find|add|remove|move ...  # e.g. growth.for_research
python scripts/dsys.py feedback record|apply --period P ...
python scripts/dsys.py reading show|add --week W --json papers.json
python scripts/dsys.py candidates arxiv --ranked | --ids a,b   # ranked shortlist, then full abstracts
python scripts/dsys.py candidates news --category C --brief    # headlines by news category
python scripts/dsys.py quarterly draft --quarter YYYY-Qn
python scripts/validate.py && python scripts/build.py && python -m pytest -q
```

Code lives in `dsys/` (stdlib + jsonschema). Keep it simple and tested.
