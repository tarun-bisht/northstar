# Monthly package (optional)

Read `prompts/_shared.md` first. Generated on the 1st for the current month.

## Rules

- 1–3 items, each about **one month** of scope. Bigger goals get a one-month milestone; `continuation` is a suggestion, never scheduled.
- **Every month includes at least one growth item** (validation enforces this): a reading or exercise in science, mathematics, neuroscience, consciousness or philosophy chosen because it can broaden research thinking later. Say how it might connect back to research.
- Busy month (`load: light`): one light item. Free month: up to three, deeper. Every item has a `light_version`.
- Include every idea in `ideas_scheduled_for_this_period`. Seeds are suggestions only.

## A real syllabus for every item

Each item is a small course, not a theme (validation enforces weekly tasks and resources):

- `objective`, `prerequisites`, `why` (and for growth items, the possible research connection)
- `weeks`: 4 entries, each with a `focus` and **concrete `tasks`** ("Read Ch. 2, Sec. 2.1–2.3; do exercises 2.4, 2.7"; "Watch lectures 3–4"; "Implement X in a notebook")
- `primary_resource` plus `resources`: books with `chapters`, lecture series with numbers, videos, blog posts, papers, each verified (`url_verified: true` only if fetched; omit `url` otherwise)
- `exercises`, `deliverable`, `definition_of_done`, `final_synthesis`
- `modes`: combine learning with practice, creation or experience (study and then explain; learn and then build; read and then write a critical question)
- `tier`, `dimensions`, `topic`; optionally `cross_domain`

## Steps

1. Feedback for last month (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`).
2. `python scripts/dsys.py context monthly --period <YYYY-MM>`: schedule, ideas, preferences (`avoid` is binding), tiers and variety.
3. **Languages (required):** add `language.plans`, one plan per language you're learning, as in `prompts/language.md`.
4. Write `content/monthly/<YYYY>/<YYYY-MM>.json` (`status: "suggested"`), then `history rebuild` and `validate`.

Kinds: `ai_deep_dive`, `non_ai_deep_dive`, `research_exploration`, `teaching`, `people`, `creative_project`, `hobby_skill`, `exploration_theme`, `user_idea`.
