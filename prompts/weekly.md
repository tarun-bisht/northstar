# Weekly package (optional)

Read `docs/vision.md` (especially §4 to §14 and §19 to §21) and `prompts/_shared.md` first. Generated on Saturday for the week starting Monday (`python scripts/dsys.py period` gives `next_week`).

**Weekly = explore.** The question for every item is: *would this make the week intellectually, creatively or experientially richer?* Weekly is the most exploratory layer: broad, surprising and specific. Monthly is narrower and deeper. Everything is optional and nothing is tracked.

## The six pillars, every week

Every normal week touches **all six pillars of development** (vision §4, `config/interests.json → dimensions`; validation enforces this). Each item lists the pillars it serves in `dimensions`.

| pillar | dimension | what the week gives it |
|---|---|---|
| Researcher | `research` | an active research exercise, and something worth studying (vision §7, §14) |
| Knowledge Explorer | `knowledge` | maths and physics questions, and things worth knowing outside AI |
| World Radar | `world` | one place, system or long-running story explained (the daily news covers events) |
| People and Self | `people` | one real-world practice with people: understanding, then practice, then a real interaction (vision §10) |
| Culture and Life | `culture` | music, art, books, films, series, anime, and the people behind them (vision §11) |
| Curiosity, Discovery and Making | `curiosity` | something to try, make or wonder at, including something weird (vision §12) |

## Three parts, each with its own page and feed

`weekly/<week>/research.html`, `knowledge.html` and `exploration.html`, and the feeds `weekly-research.xml`, `weekly-knowledge.xml` and `weekly-exploration.xml`. Every item has a `section`, and the section decides the part.

| part | section | what goes here | per week |
|---|---|---|---|
| **Research** | `research_practice` | an active exercise: an ML or deep learning fundamentals problem, a derivation, a paper-critique exercise, an experiment-design or ablation question, "what would you test?", interpreting a plot, debugging a conclusion, a small implementation idea. Vary the form week to week. Progressive hints, never the solution | 1 to 2 |
| | `research_reading` | one paper or concept worth studying properly (`paper` or `ai_study` with `explain`). Different from the reading list: this one comes with guidance on what to notice | 1 |
| **Knowledge** | `questions` | **maths and physics questions to think about.** At least **2 maths or probability** (`subject: maths` or `probability`) and at least **2 physics** (`subject: physics`), plus optionally one from another science. Real puzzles and thought experiments, not textbook drills: each with a clear statement, why it's interesting, and 2 to 4 progressive hints, never the answer (`category: question`). Graduate-level maths is fine, and physics should build intuition (`preferences.difficulty`) | 4 to 5 |
| | `things_to_know` | **anything worth knowing and talking about**: a historical story, an idea, a scientific mystery, how something works, a remarkable person, a place, an economic puzzle, a philosophical question. The test: would it make a good conversation starter? Say what it is, why it's interesting, and one question to discuss (`category: talking_point`). Vary the subjects | 2 to 3 |
| | `world` | one place, system or long-running story explained: how something in the world works, beyond the daily news | 1 |
| **Exploration** | `culture` | the richest part of the week. For example: the life of a musician plus three songs to listen to; an artist and two works to look at slowly; a film or anime connected to an idea; a book or one chapter; an architectural movement; a cultural tradition. Name the specific works | 3 to 4 |
| | `people_self` | one real-world practice: listening, a better conversation, articulation, courage, feedback, leadership. Concrete, small and done with real people | 1 to 2 |
| | `curiosity_making` | something to try or make: a hobby, an experiment, a small build, a weird discovery, a place to go | 1 to 2 |

Language lessons appear in Exploration.

Validation requires, by `load`:
- light: `research_practice`, `questions` (1 maths and 1 physics), `culture`
- normal: `research_practice`, `questions` (2 maths and 2 physics), `things_to_know`, `culture`, `people_self`, and all six pillars
- free: all of the above, plus `research_reading` and `curiosity_making`

A normal week has about 12 to 16 small items. Most take 10 to 60 minutes. Exploration gets the most variety.

## Quality

- **Specific, never generic.** Not "listen to some jazz", but "Bill Evans: Peace Piece, Waltz for Debby, My Foolish Heart, and what to listen for in each". Not "practise listening", but a concrete exercise with a time and a person.
- **Familiar, adjacent, unexpected** (vision §19): at least two items should make the user think "I would never have searched for this myself."
- **Connections** (vision §20): one or two items are explicitly cross-domain (`cross_domain`), for example music and psychology, or physics and information theory.
- **Real resources:** every reading, implementation or learning exercise (categories research_fundamentals, ai_study, paper, new_knowledge, or `mode: learn`) has detailed `steps` and verified `resources` (a book with `chapters`, a lecture, a video, a blog post or a paper). Validation enforces this. Find links with WebSearch (`prompts/_shared.md`, web access).

## Steps

1. Process feedback (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`) first.
2. `python scripts/dsys.py context weekly --period <next_week>`:
   - `schedule.load` sets the size and required sections.
   - `ideas_scheduled_for_this_period`: the user asked for these, so include every one (`origin: "user_idea"`, `idea_id`), in the section that fits. Seeds in `ideas_open_pool` are suggestions only (`seed_rule`): never mark them planned.
   - `preferences`: explicit signals win. Never recommend anything in `avoid`. `ignored_hint` means a different format or time, not dislike.
   - `interests_hint` (tiers), `variety` (suggestions), `already_recommended_titles` (never repeat).
3. Every item: `section`, `category`, `dimensions` (its pillars), `tier`, `mode` (learn / practise / create / experience / reflect), `topic`, `time_estimate`, a short `why`, and `subject` for questions. Many items end with a `then`, for example "explain it to a friend in two minutes".
4. **Languages (required):** add `language.lessons`, one lesson per language you're learning, as in `prompts/language.md`.
5. Write `content/weekly/<YYYY>/<YYYY-Www>.json` with a one-line `intro`, `load` and items (`status: "suggested"`). Don't change idea statuses yourself.
6. `history rebuild`, `validate`.

A previous item returns only if feedback decided so. Then use `origin: "continued"` with `continues`, and modify it rather than copying it.
