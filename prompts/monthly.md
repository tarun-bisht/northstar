# Monthly package (optional)

Read `docs/vision.md` and `prompts/_shared.md` first. Generated on the 1st for the current month.

**Monthly = go deep.** A monthly deep dive can be about anything worth going deep on: AI research, mathematics, physics, history, philosophy, a civilization, an artist or filmmaker, music, a scientific field, a hobby, making something. There is no requirement to finish.

## Three parts, each on its own page

The site shows the month as `monthly/<month>/research.html`, `knowledge.html` and `exploration.html`. Every item has a `section`:

| section | what goes here |
|---|---|
| `research` | an AI research deep dive: a method family, a theory area, a field to map |
| `knowledge` | a deep dive outside AI: maths, physics, history, philosophy, a civilization, a science |
| `exploration` | a deep dive into something to experience, practise or make: an artist, filmmaker, author or musician and their work, a culture, a craft or hobby, a personal-development theme practised for a month, travel preparation, or a completely unexpected subject |

**One deep dive per part, every month** (validation enforces all three unless `load` is light). A free month may add a fourth. Language plans appear on the Exploration page.

## Rules

- Each item is about **one month** of scope. Bigger goals get a one-month milestone; `continuation` is a suggestion, never scheduled.
- **Every month includes at least one growth item** (validation enforces this): a reading or exercise in science, mathematics, neuroscience, consciousness or philosophy chosen because it can broaden research thinking later. Say how it might connect back to research.
- Busy month (`load: light`): one or two light items. Normal month: three, one per part. Free month: up to four. Every item has a `light_version`.
- Include every idea in `ideas_scheduled_for_this_period`. Seeds are suggestions only.

## A real syllabus for every item

Each item is a small course, not a theme (validation enforces weekly tasks and resources):

- `objective`, `prerequisites`, `why` (and for growth items, the possible research connection)
- `weeks`: 4 entries, each with a `focus` and **concrete `tasks`** ("Read Ch. 2, Sec. 2.1–2.3; do exercises 2.4, 2.7"; "Watch lectures 3–4"; "Implement X in a notebook")
- `primary_resource` plus `resources`: books with `chapters`, lecture series with numbers, videos, blog posts, papers, each verified (`url_verified: true` only if fetched; omit `url` otherwise)
- `exercises`, `deliverable`, `definition_of_done`, `final_synthesis`
- `modes`: combine learning with practice, creation or experience (study and then explain; learn and then build; read and then write a critical question)
- `section`, `tier`, `dimensions`, `topic`; optionally `cross_domain`

## Steps

1. Feedback for last month (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`).
2. `python scripts/dsys.py context monthly --period <YYYY-MM>`: schedule, ideas, preferences (`avoid` is binding), tiers and variety.
3. **Languages (required):** add `language.plans`, one plan per language you're learning, as in `prompts/language.md`.
4. Write `content/monthly/<YYYY>/<YYYY-MM>.json` (`status: "suggested"`), then `history rebuild` and `validate`.

Kinds: `ai_deep_dive`, `research_exploration` (research); `non_ai_deep_dive` (knowledge); `exploration_theme`, `creative_project`, `hobby_skill`, `people`, `teaching` (exploration); `user_idea` (set `section` explicitly).
