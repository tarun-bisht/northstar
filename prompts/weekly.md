# Weekly package (optional)

Read `docs/vision.md` (especially §4 to §14 and §19 to §21) and `prompts/_shared.md` first. Generated on Saturday for the week starting Monday (`python scripts/dsys.py period` gives `next_week`).

**Weekly = explore.** The question for every item is: *would this make the week intellectually, creatively or experientially richer?* Weekly is the most exploratory layer: broad, surprising and specific. Monthly is narrower and deeper. Everything is optional and nothing is tracked.

## The six pillars, every week

Every normal week touches **all six pillars of development** (vision §4, `config/interests.json → dimensions`; validation enforces this). Each item lists the pillars it serves in `dimensions`.

| pillar | dimension | what the week gives it |
|---|---|---|
| Researcher | `research` | an active research exercise, and something worth studying (vision §7, §14) |
| Knowledge Explorer | `knowledge` | topics by subject with study plans, and maths and physics questions |
| World Radar | `world` | a knowledge topic with `subject: world`: a place, system or long-running story explained |
| People and Self | `people` | one real-world practice with people: understanding, then practice, then a real interaction (vision §10) |
| Culture and Life | `culture` | music, art, books, films, series, anime, and the people behind them (vision §11) |
| Curiosity, Discovery and Making | `curiosity` | something to try, make or wonder at, including something weird (vision §12) |

## Five parts, each with its own page and feed

`weekly/<week>/papers.html`, `research.html`, `knowledge.html`, `exploration.html` and `languages.html`, with the feeds `reading.xml`, `weekly-research.xml`, `weekly-knowledge.xml`, `weekly-exploration.xml` and `weekly-languages.xml`. Every item has a `section`, and the section decides the part.

| part | section | what goes here | per week |
|---|---|---|---|
| **Papers of the week** | (the reading list) | `content/reading/<week>.json`, built by `prompts/reading_list.md`: picks for you from the week's daily papers, the week's trending papers, and strong work from leading groups related to AI or the user's research. Not part of daily | 3 to 16 papers |
| **Research** | `research_practice` | **Fundamentals**: a core idea worked through. An ML or deep learning derivation, a proof, a small implementation, a paper-critique or experiment-design exercise. Vary the form. Steps, resources and progressive hints | 1 to 2 |
| | `research_reading` | **New in AI**: one concept that is trending in AI right now (from the week's trending papers, `candidates arxiv --trending-week <week>`, or the poll choice in `state/polls.json` if there is one), learned properly: `ai_study` with `explain`, a study plan in `steps` and resources (the paper, a good blog post, a talk) | 1 to 2 |
| **Knowledge** | `knowledge` | **topics to study, grouped by subject** (`subject`). Maths and physics are always there. Add **5 to 6 other subjects** that rotate week to week: history, philosophy, biology, chemistry, economics, the world (geopolitics, how a system works), psychology, linguistics, astronomy, literature, art, music. One topic per subject: what it is, why it is worth knowing, a study plan of 3 to 5 `steps`, and at least 2 real `resources` (a video or lecture, notes or a blog post, a book chapter with `chapters`, a paper) (`category: new_knowledge`) | 6 to 8 |
| | `questions` | **questions to test yourself.** At least **2 maths or probability** and at least **2 physics** (`subject`), more subjects optional. Weekly questions are **approachable**: 10 to 30 minutes, a clear statement, 2 to 3 progressive `hints`, a short `solution` (shown collapsed), and a `source` when it comes from a book or exam (`category: question`). The hard ones belong in the monthly challenge set | 4 to 6 |
| **Exploration** | `curiosities` | **things worth knowing and bringing up in conversation**: a story, a scientific mystery, how something works, a remarkable person, a strange fact with a real source. Say what it is, why it's interesting, and one question to discuss (`category: talking_point`) | 2 to 3 |
| | `culture` | the richest part of the week. For example: the life of a musician plus three songs to listen to; an artist and two works to look at slowly; a film or anime connected to an idea; a book or one chapter. Name the specific works | 2 to 4 |
| | `people_self` | one real-world practice: listening, a better conversation, articulation, courage, feedback, leadership. Concrete, small and done with real people | 1 to 2 |
| | `curiosity_making` | something to try or make: a hobby, an experiment, a small build, a weird discovery, a place to go | 1 to 2 |
| **Languages** | `language.lessons` | one lesson per language (`prompts/language.md`) | 1 per language |

Validation requires, by `load`:
- light: `research_practice`, `questions` (1 maths and 1 physics), `culture`
- normal: `research_practice`, `research_reading`, `knowledge` (topics in at least 5 subjects besides maths and physics), `questions` (2 maths and 2 physics), `curiosities`, `culture`, `people_self`, and all six pillars
- free: all of the above, plus `curiosity_making`

A normal week has about 16 to 22 small items. Most take 10 to 60 minutes. Nobody does all of it: it is a menu.

**Threads.** `context weekly` gives `poll_choices` (the user's Slack poll pick for New in AI: use it), `trending_this_week` (what New in AI can come from), `recent_subjects` (rotate: prefer subjects that are missing) and `recent_questions` (build on them, a step harder, never repeat). When a language is the current focus (`config/languages.json`), let one culture or curiosity item connect to that culture now and then (for Japanese: a film, an artist, a craft, a place).

## Quality

- **Specific, never generic.** Not "listen to some jazz", but "Bill Evans: Peace Piece, Waltz for Debby, My Foolish Heart, and what to listen for in each". Not "practise listening", but a concrete exercise with a time and a person.
- **Familiar, adjacent, unexpected** (vision §19): at least two items should make the user think "I would never have searched for this myself."
- **Connections** (vision §20): one or two items are explicitly cross-domain (`cross_domain`), for example music and psychology, or physics and information theory.
- **Study plans with real resources:** every knowledge topic, research item and learning exercise has a study plan in `steps` and real `resources`: videos, lectures, notes, book chapters (`chapters`), papers. Prefer free, well-known material (MIT OCW, 3Blue1Brown, Feynman Lectures online, Stanford Encyclopedia of Philosophy, standard textbooks). Validation enforces this.
- **No broken links:** only add a URL you found in a search result or fetched in this run. A book chapter needs no URL. Find links with WebSearch (`prompts/_shared.md`, web access).

## Steps

1. Process feedback (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`) first.
2. `python scripts/dsys.py context weekly --period <next_week>`:
   - `schedule.load` sets the size and required sections.
   - `ideas_scheduled_for_this_period`: the user asked for these, so include every one (`origin: "user_idea"`, `idea_id`), in the section that fits. Seeds in `ideas_open_pool` are suggestions only (`seed_rule`): never mark them planned.
   - `preferences`: explicit signals win. Never recommend anything in `avoid`. `ignored_hint` means a different format or time, not dislike.
   - `interests_hint` (tiers), `variety` (suggestions), `already_recommended_titles` (never repeat).
3. Every item: `section`, `category`, `dimensions` (its pillars), `tier`, `mode` (learn / practise / create / experience / reflect), `topic`, `time_estimate`, a short `why`, and `subject` for knowledge topics and questions. Many items end with a `then`, for example "explain it to a friend in two minutes".
4. **Languages (required):** add `language.lessons`, one lesson per language you're learning, as in `prompts/language.md`.
5. Write `content/weekly/<YYYY>/<YYYY-Www>.json` with a one-line `intro`, `load` and items (`status: "suggested"`). Don't change idea statuses yourself.
6. `history rebuild`, `validate`.

A previous item returns only if feedback decided so. Then use `origin: "continued"` with `continues`, and modify it rather than copying it.
