# Northstar: instructions for Claude

Northstar is a public, forkable personal discovery and growth companion. GitHub Actions scrapes candidates; Claude reads, filters and writes JSON; GitHub Actions validates it and publishes a website and RSS feeds. `docs/how_it_works.md` is the map of the whole system, `prompts/runs/` holds one runbook per scheduled task, and `docs/scheduled_tasks_setup.md` holds the exact task prompts.

## Rules

0. **The vision comes first.** Test every choice against the guiding question of `docs/vision.md`: *does this help the person discover, understand, practise, create or experience something genuinely worthwhile, while respecting their attention and freedom?* Curation and discovery, never tracking. Planning prompts (weekly, monthly, discovery) read the vision in full. Other work uses this question.
1. Read `prompts/_shared.md` before generating anything. It holds the shared rules: tiers, web access, truthfulness, privacy details, mechanics and writing style.
2. Never fabricate papers, videos, URLs, dates or facts. Never add a URL you haven't seen in a search result or fetched page.
3. **Scraped, not searched:** papers, news, research updates, podcasts and videos come only from the fetched candidate files. Search only for discovery (films, books, reads, places), targeted X and LinkedIn posts, and study resources.
4. Optional means optional: no streaks, scores, quotas or automatic carry-over. User intent beats the algorithm.
5. Everything is public. Never store private details (project names, unpublished work, people, institutions, health, relationships, finances, schedules, travel dates, raw feedback, reflections). **Translate, never record**: save only general topics.
6. Finish every change with `python scripts/dsys.py history rebuild && python scripts/validate.py`. Never commit invalid content. Never force-push. Only commit to `main`.
7. Slack is the only notification (`config/notifications.json`). Never post about failed sources.
8. When you change how the system works, update `docs/how_it_works.md`. When you change a task, time, connector or channel, update `docs/scheduled_tasks_setup.md` and the live task to match.

## Which prompt

| Situation | Prompt |
|---|---|
| Scheduled runs | `prompts/runs/daily.md`, `weekly.md`, `monthly.md`, `quarterly.md` (each says which prompts it calls) |
| Setting up a fork, or recreating the scheduled tasks | `docs/scheduled_tasks_setup.md` |
| "Recommend me…", "I want to try…" | `prompts/on_demand_recommendations.md`, then `prompts/inbox.md` to record it |
| User shares interests, projects, trips, how busy they are | `prompts/update_interests.md` |
| Feedback on a week or month | `prompts/feedback.md` |
| Papers of the week | `prompts/reading_list.md` |
| Language lessons, packs, plans | `prompts/language.md` |
| "Let's practise Japanese", "quiz me" | `prompts/language_practice.md` |

## Commands

```bash
python scripts/dsys.py period                                  # today, this/next week and month
python scripts/dsys.py context <stream> [--date D] [--period P]  # what a planner should know
python scripts/dsys.py candidates ensure --kinds ...           # wait for (or start) today's fetch
python scripts/dsys.py candidates <kind> ...                   # read fetched candidates
python scripts/dsys.py papers stage1|merge|enrich|stage2|add --date D
python scripts/dsys.py daily merge <stream> --date D --items file.json
python scripts/dsys.py daily start-here --date D --pick <id>="<why>" ...  # the day's way in
python scripts/dsys.py reading show|add --week W --json papers.json
python scripts/dsys.py reputation show|suggest|add ...                 # trust registry (never edit by hand)
python scripts/dsys.py ideas|interests|feedback|polls|stats|status ...
python scripts/dsys.py quarterly draft --quarter YYYY-Qn
python scripts/validate.py && python scripts/build.py && python -m pytest -q
```

Run `python scripts/dsys.py <command> -h` for options. Long output arrives as part files: read every part. Code lives in `dsys/` (stdlib + jsonschema). Keep it simple and tested.
