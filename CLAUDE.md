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

- **Parts, each on its own page and feed:** daily = Research, News, Exploration, Shorts, Languages. Weekly = Papers of the week, Research, Knowledge, Exploration, Languages. Monthly = Research, Knowledge, Exploration, Languages. Quarterly = Research, Knowledge, Exploration (`docs/how_it_works.md` §2).
- **Papers (every day):** staged reading (`prompts/runs/daily.md`): Python narrows, Haiku reads every remaining abstract (`prompts/paper_triage.md`), page 1 gives affiliations and trust (`config/reputation.json`), Opus decides (`prompts/arxiv.md`). No cap: best picks `priority: top`, the rest `more`. Abstracts copied word for word. Tags from `paper_tags` only. Paper links go to alphaXiv.
- **Papers of the week** (`reading.xml`, a weekly part): at least 3 entries every week in up to three groups, *For you*, *Trending this week* (`candidates arxiv --trending-week`) and *From leading groups*, kept current by the daily runs.
- **World Radar:** learning beyond AI, so every explained story has a `lesson` (the idea behind it). Awareness plus interest-matched news: 12 to 20 explained items across at least 7 of 12 categories (including leadership changes) plus 15 to 30 one-line briefs, depth pieces paired with events, nothing from the last 3 days (`prompts/world.md`).
- **Scraped, not searched:** papers, news, research updates, podcasts and videos come only from the fetched files. Search only for discovery (films, books, reads, places), targeted X and LinkedIn posts, and study resources.
- **Models:** Haiku for bulk reading and simple runs, Sonnet for news, updates and shorts, Opus for judgement (paper choice, recommendations, language packs, weekly and monthly packages). The quarterly summary uses Sonnet.
- **Daily Discovery:** curate the best, each item saying what you'll learn (`what_i_might_get_from_it`). At least one podcast and one video, lecture or documentary, at least one item per tier, the rest free. Shorts: 30 to 40, at least one per tier, on their own page.
- **Weekly:** all six pillars every normal week. Research = Fundamentals + New in AI. Knowledge grouped by `subject`: maths and physics always plus topics in 5 to 6 rotating subjects, each with a study plan (`steps`) and real resources, and approachable questions (at least 2 maths and 2 physics). Curiosities live in Exploration, the largest part.
- **Monthly:** New in AI, Fundamentals, knowledge and exploration deep dives (unless light), the exploration one rotating through people, culture and making; each a week-by-week syllabus with resources, at least one growth item, and hard `challenges` (at least 2 maths, 2 physics, 4 other subjects) with real sources.
- **Quarterly:** `quarterly draft` fills the numbers and topics. Write only the short summaries and one-line abouts.
- **Links:** never add a URL you haven't seen in a search result or fetched page. External links open in a new tab.
- **Notifications:** Slack only (`config/notifications.json`): ready messages and missing parts in #northstar-daily, polls in #northstar-polls, rare questions in #northstar-ask, announcements in #general, fun in #random. Never messages about failed sources.
- **Writing:** plain simple English, short, main point first, no semicolons or em dashes.
- **Languages** (`config/languages.json`): a 5-minute pack every day (current focus), a lesson per language every week, a plan per language every month.

## Which prompt

| Situation | Prompt |
|---|---|
| Scheduled runs (four tasks) | `prompts/runs/daily.md` (calls `shorts.md`, `topic_poll.md`, `slack_digest.md`), `weekly.md` and `monthly.md` (call `poll_collect.md`), `quarterly.md` |
| Changing how the system works | `docs/how_it_works.md` (update it too), and `docs/scheduled_tasks_setup.md` if a task, time, connector or channel changes |
| Setting up a fork, or recreating the scheduled tasks | `docs/scheduled_tasks_setup.md` (exact prompts, crons and models) |
| "Recommend me…", "I want to try…" | `prompts/on_demand_recommendations.md`, then `prompts/inbox.md` to record it |
| User shares interests, projects, trips, how busy they are | `prompts/update_interests.md` |
| Feedback on a week or month | `prompts/feedback.md` |
| Papers of the week | `prompts/reading_list.md` |
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
python scripts/dsys.py papers stage1|merge|enrich|stage2 --date D  # staged paper reading
python scripts/dsys.py candidates updates --compact             # research updates, last 3 days removed
python scripts/dsys.py reputation show|suggest                  # trust registry
python scripts/dsys.py stats show --date D                      # counts for the Slack message
python scripts/dsys.py candidates news --category C --brief    # headlines by news category
python scripts/dsys.py candidates podcasts|videos|updates|hf    # episodes, long videos, blogs, HF trending
python scripts/dsys.py candidates arxiv --search all            # alphaXiv search hits per interest
python scripts/dsys.py status                                   # what exists today, what failed
python scripts/dsys.py polls list|open|close ...                # Slack topic polls
python scripts/dsys.py quarterly draft --quarter YYYY-Qn
python scripts/validate.py && python scripts/build.py && python -m pytest -q
```

Code lives in `dsys/` (stdlib + jsonschema). Keep it simple and tested.
