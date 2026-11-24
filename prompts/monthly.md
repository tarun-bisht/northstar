# Monthly package (optional)

Read `docs/vision.md` (especially §4 and §15) and `prompts/_shared.md` first. Generated on the 1st for the current month.

**Monthly = go deep.** A monthly deep dive can be about anything worth going deep on: AI research, mathematics, physics, history, philosophy, a civilization, an artist or filmmaker, music, a scientific field, a hobby, making something. There is no requirement to finish.

## Four parts, each on its own page and feed

`monthly/<month>/research.html`, `knowledge.html`, `exploration.html` and `languages.html`, with the feeds `monthly-research.xml`, `monthly-knowledge.xml`, `monthly-exploration.xml` and `monthly-languages.xml`. Every item has a `section`:

| part | section | what goes here |
|---|---|---|
| **Research** | `research` | **New in AI**: a deep dive into a method or idea that is trending in AI now (diffusion, world models, test-time compute, whatever the field is moving on), from the paper and its predecessors to an implementation. Use the poll choice in `state/polls.json` if there is one |
| | `fundamentals` | **Fundamentals**: the foundations under research, for example probability and measure, optimization, information theory, linear algebra for ML, learning theory, statistics. Use the poll choice in `state/polls.json` if there is one |
| **Knowledge** | `knowledge` | a deep dive outside AI with a `subject` (maths, physics, history, philosophy, a civilization, a science). It rotates so no subject dominates |
| | `challenges` (top-level list) | **hard challenge problems** that test knowledge and expose gaps: at least **2 maths or probability**, at least **2 physics**, and problems in **4 to 6 other subjects** (chemistry, biology, economics, computer science, astronomy, history or philosophy questions with real depth). Olympiad, entrance-exam (JEE Advanced, GRE subject tests), Putnam or university level. Each has a real `source` (competition and year, or book and exercise number), `level`, what it `tests`, 2 to 3 `hints`, and a `solution` or `solution_url` when you have one. Never invent a source: if you cannot name where a problem comes from, write your own and say `source: "Northstar original"` |
| **Exploration** | `exploration` | a deep dive to experience, practise or make. **It rotates through the three exploration pillars**: People and Self, Culture and Life, Curiosity and Making. Pick the pillar the last two months did not cover (validation warns on repeats) |
| **Languages** | `language.plans` | one plan per language (`prompts/language.md`) |

Validation enforces `research`, `fundamentals`, `knowledge` and `exploration` deep dives and the challenge rules (light months: a `research` deep dive and 1 maths and 1 physics challenge).

**Depth, not breadth.** The weekly packages explore widely. The month picks a few subjects and goes deep: a real syllabus, real exercises, something made at the end.

## Rules

- Each item is about **one month** of scope. Bigger goals get a one-month milestone; `continuation` is a suggestion, never scheduled.
- **Every month includes at least one growth item** (validation enforces this): a reading or exercise in science, mathematics, neuroscience, consciousness or philosophy chosen because it can broaden research thinking later. Say how it might connect back to research.
- Busy month (`load: light`): one or two light items. Normal month: four, one per section. Free month: up to six. Every item has a `light_version`.
- Include every idea in `ideas_scheduled_for_this_period`. Seeds are suggestions only.

## A real syllabus for every item

Each item is a small course, not a theme (validation enforces weekly tasks and resources):

- `objective`, `prerequisites`, `why` (and for growth items, the possible research connection)
- `weeks`: 4 entries, each with a `focus` and **concrete `tasks`** ("Read Ch. 2, Sec. 2.1–2.3; do exercises 2.4, 2.7"; "Watch lectures 3–4"; "Implement X in a notebook")
- `primary_resource` plus `resources`: books with `chapters`, lecture series with numbers, videos, lecture notes, blog posts, papers. Only add a URL you found in a search result or fetched in this run (`url_verified: true` only if fetched); a book chapter needs no URL. No broken links in the first place
- `exercises`, `deliverable`, `definition_of_done`, `final_synthesis`
- `modes`: combine learning with practice, creation or experience (study and then explain; learn and then build; read and then write a critical question)
- `section`, `tier`, `dimensions`, `topic`; optionally `cross_domain`

## Steps

1. Feedback for last month (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`).
2. `python scripts/dsys.py context monthly --period <YYYY-MM>`: schedule, ideas, preferences (`avoid` is binding), tiers and variety.
3. **Languages (required):** add `language.plans`, one plan per language you're learning, as in `prompts/language.md`.
4. Write `content/monthly/<YYYY>/<YYYY-MM>.json` (`status: "suggested"`), then `history rebuild` and `validate`.

Kinds: `ai_deep_dive`, `research_exploration` (research; set `section: fundamentals` for the fundamentals deep dive); `non_ai_deep_dive` (knowledge); `exploration_theme`, `creative_project`, `hobby_skill`, `people`, `teaching` (exploration); `user_idea` (set `section` explicitly).
