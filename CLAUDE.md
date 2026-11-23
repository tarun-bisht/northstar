# Northstar: instructions for Claude

Northstar is a public, forkable personal growth system. Claude generates content into JSON; GitHub Actions validates it and publishes RSS feeds and a website. See `README.md`.

## Rules

1. Read `prompts/_shared.md` before generating anything.
2. Interests have three tiers (`config/interests.json`): **established** (most items: AI research and its foundations), **growth** (steady steps: maths, physics, neuroscience, philosophy, people skills, history, art), **exploration** (always some: worthwhile surprises). Every item has a `tier` and `dimensions`.
3. Never fabricate papers, videos, URLs, dates or facts. Omit what you can't verify.
4. Optional means optional: no streaks, scores, quotas or automatic carry-over. User intent beats the algorithm.
5. Everything is public. Never store private details (project names, unpublished work, people, institutions, health, relationships, schedules, travel dates, raw feedback, reflections). **Translate, never record**: save only general topics.
6. Finish every change with `python scripts/dsys.py history rebuild && python scripts/validate.py`. Never commit invalid content.

## Enforced content rules

- Daily Discovery: an established-tier podcast, a video/lecture/documentary, and at least one item per tier.
- Shorts: at least one per tier.
- Weekly learning items: detailed steps and real resources (book chapters, lectures, blogs, papers).
- Monthly: a week-by-week syllabus with resources, and at least one growth reading or exercise.
- arXiv and reading list: tags from the fixed `paper_tags` list only, never free-text reasons. Every week has a reading list of at least 3 papers.
- Writing: plain simple English, short, main point first, no semicolons or em dashes.
- Languages (`config/languages.json`): a 5-minute pack every day (current focus), a lesson per language every week, a plan per language every month.

## Which prompt

| Situation | Prompt |
|---|---|
| Scheduled runs | `prompts/runs/daily.md`, `shorts.md`, `weekly.md`, `monthly.md`, `quarterly.md` |
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
python scripts/validate.py && python scripts/build.py && python -m pytest -q
```

Code lives in `dsys/` (stdlib + jsonschema). Keep it simple and tested.
