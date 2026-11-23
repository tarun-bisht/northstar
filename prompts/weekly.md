# Weekly package (optional)

Read `prompts/_shared.md` first. Generated on Saturday for the week starting Monday (`python scripts/dsys.py period` gives `next_week`).

*"What small new thing could I learn, practise, make or experience this week, if I have time?"*

## Steps

1. Process feedback (`prompts/feedback.md`) and new ideas (`prompts/inbox.md`) first.
2. `python scripts/dsys.py context weekly --period <next_week>`:
   - `schedule.load`: light means 2–3 tiny items, normal 3–5, free 4–6. Keep the total time well under `available_hours`.
   - `ideas_scheduled_for_this_period`: the user asked for these, so include every one (`origin: "user_idea"`, `idea_id`). Seeds in `ideas_open_pool` are suggestions only (`seed_rule`): never mark them planned.
   - `preferences`: explicit signals win. Never recommend anything in `avoid`. `ignored_hint` means a different format or time, not dislike.
   - `interests_hint` (tiers), `variety` (suggestions), `already_recommended_titles` (never repeat).
3. Choose a mix by **tier**: mostly established, one growth step, and one exploration item when there's room. Kinds to draw from:
   - `research_fundamentals` (a problem with 3–4 progressive hints, never the solution), `ai_study` (fill `explain`), `paper` (fill `paper`)
   - `new_knowledge`, `people` (real-world practice), `teaching`, `culture`, `making`, `random_curiosity`, `world_understanding`
   - About one item a week can be cross-domain (`cross_domain`).
4. Every item: `tier`, `dimensions`, `mode` (learn / practise / create / experience / reflect), `topic` and `time_estimate`. At least one item should be about doing, often via `then` ("explain it to a friend", "write one critical question").
5. **Every reading, implementation or learning exercise** (categories research_fundamentals, ai_study, paper, new_knowledge, or `mode: learn`) needs **detailed `steps`** and **real `resources`**: a book with `chapters` ("Ch. 3, Sec. 3.2"), a lecture or video, a blog post or a paper, each verified. Validation enforces this.
6. Write `content/weekly/<YYYY>/<YYYY-Www>.json` with a one-line `intro`, `load` and items (`status: "suggested"`). Don't change idea statuses yourself.
7. `history rebuild`, `validate`.

A previous item returns only if feedback decided so. Then use `origin: "continued"` with `continues`, and modify it rather than copying it.
