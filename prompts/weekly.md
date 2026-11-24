# Weekly package (optional)

Read `docs/vision.md` and `prompts/_shared.md` first. Generated on Saturday for the week starting Monday (`python scripts/dsys.py period` gives `next_week`).

**Weekly = explore.** The question is: *what would make this week intellectually, creatively or experientially richer?* Everything is optional. Nothing is tracked. Items are small, specific and genuinely worth the time. Never generic.

## Sections

Every item has a `section`. The page shows items under these headings, in this order:

| section | what goes here | per week |
|---|---|---|
| `research_practice` | an active research exercise: an ML or deep learning fundamentals problem, a derivation, a paper-critique exercise, an experiment-design or ablation question, "what would you test?", interpreting a plot, a small implementation idea. Vary the form week to week. Hints, never the solution | 1 to 2 |
| `research_reading` | one paper or concept worth studying properly (`paper` or `ai_study` with `explain`) | 0 to 1 |
| `questions` | questions to think about: maths, probability, physics, other sciences. Puzzles and thought experiments with 2 to 4 progressive hints (`category: question`) | 2 to 3 |
| `talking_points` | history and philosophy: a story, an idea, a debate or a person worth knowing, the kind of thing you could bring up in conversation (`category: talking_point`). Say what it is, why it's interesting and one question to discuss | 1 to 2 |
| `culture` | music, art, books, films, series, anime, architecture, and the people behind them. For example: the life of a musician plus three songs to listen to, an artist and two works to look at, a film connected to an idea, a book or one chapter, an anime | 2 to 3 |
| `people_self` | one real-world practice: listening, a better conversation, articulation, courage, feedback, leadership. Understanding, then practice, then a real interaction | 1 |
| `curiosity_making` | something to try or make: a hobby, an experiment, a small build, something weird worth discovering | 1 |
| `world` | optional: a place, system or long-running story explained | 0 to 1 |

Validation requires these sections, by `load`:
- light: `research_practice`, `questions`, `culture`
- normal: `research_practice`, `questions`, `talking_points`, `culture`, `people_self`
- free: all of the above, plus `research_reading` and `curiosity_making`

Typical size is 8 to 14 small items (`preferences.weekly.typical_item_count`). Most take 10 to 60 minutes.

## Balance

- Mix familiar, adjacent and unexpected (vision §19). At least one item should make the user think "I would never have searched for this myself."
- About one item a week is explicitly cross-domain (`cross_domain`), for example music and psychology, or physics and information theory.
- Use the tiers: established for research, growth for maths, physics, philosophy, people and culture, and exploration for surprises.

## Steps

1. Process feedback (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`) first.
2. `python scripts/dsys.py context weekly --period <next_week>`:
   - `schedule.load` sets the size and required sections.
   - `ideas_scheduled_for_this_period`: the user asked for these, so include every one (`origin: "user_idea"`, `idea_id`), in the section that fits. Seeds in `ideas_open_pool` are suggestions only (`seed_rule`): never mark them planned.
   - `preferences`: explicit signals win. Never recommend anything in `avoid`. `ignored_hint` means a different format or time, not dislike.
   - `interests_hint` (tiers), `variety` (suggestions), `already_recommended_titles` (never repeat).
3. Every item: `section`, `category`, `tier`, `dimensions`, `mode` (learn / practise / create / experience / reflect), `topic`, `time_estimate`, and a short `why`. Many items end with a `then`, for example "explain it to a friend in two minutes".
4. **Every reading, implementation or learning exercise** (categories research_fundamentals, ai_study, paper, new_knowledge, or `mode: learn`) needs **detailed `steps`** and **real `resources`**: a book with `chapters` ("Ch. 3, Sec. 3.2"), a lecture or video, a blog post or a paper, each verified. Validation enforces this. Culture items name the specific work (song titles, film, chapter) with a verified link where one exists.
5. **Languages (required):** add `language.lessons`, one lesson per language you're learning, as in `prompts/language.md`.
6. Write `content/weekly/<YYYY>/<YYYY-Www>.json` with a one-line `intro`, `load` and items (`status: "suggested"`). Don't change idea statuses yourself.
7. `history rebuild`, `validate`.

A previous item returns only if feedback decided so. Then use `origin: "continued"` with `continues`, and modify it rather than copying it.
