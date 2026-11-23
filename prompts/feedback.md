# Processing feedback (weekly / monthly)

Read `prompts/_shared.md` first.

Feedback arrives naturally, in `inbox/feedback.md`, in a chat, or as a one-liner. There are no forms. Your job is to turn it into structured feedback, decide what happens to each item, and apply it.

## Steps

1. Read what they wrote (`python scripts/dsys.py inbox show feedback`, or the chat) and the package(s) it refers to (`content/weekly/...`, `content/monthly/...`). Match loose references ("the probability puzzle", "the pottery thing") to item ids. If a reference is genuinely ambiguous and a person is present, ask one short question; otherwise skip that part and note it.
2. For each mentioned item choose a `status`: completed, partially_completed, not_started, skipped, in_progress, dropped.
3. Choose a `decision` thoughtfully, using the reason they gave and the item's history:
   - `done`: finished, nothing more
   - `drop`: not interested, or no longer relevant
   - `reschedule`: they still want it and simply lacked time (give `decision_target` if they named a time)
   - `reduce_scope`: it was too big; note the smaller version in `decision_note`
   - `modify`: same aim, different form (e.g. a video instead of a book)
   - `split`: break a big item into a first milestone (note it)
   - `replace`: wrong fit; the next package should offer something different
   - `keep_in_progress`: ongoing and going well (e.g. a monthly project continuing)
   - `none`: let it go quietly. **This is the default for skipped or not-started items with no stated wish to continue.** Do not carry things forward by default.
   - If an item has already been rescheduled twice, do not reschedule it again; prefer reduce_scope, modify, replace or drop. (The tool enforces this limit.)
4. Capture what helps future recommendations as **short, sanitized paraphrases** (max ~200 characters, no names, no private details): `learned`, `enjoyed`, `difficult`, plus a generic `skip_reason` (one of no_time, too_long, too_hard, not_interesting, other). Add explicit signals when they gave them: `interest` (more / same / less / not_interested) and `difficulty_feedback` (too_easy / right / too_hard). Put `more_of` and `less_of` into `general`. **Never store the raw text**; the schema has no field for it, and validation rejects it.
   - Silence is not a signal. An item they didn't mention, or skipped "no time", says nothing about interest. Don't set `interest: less` unless they said so.
5. Write `/tmp/fb.json` = `{"entries": [...], "general": {...}}` and run:

```bash
python scripts/dsys.py feedback record --period <YYYY-Www|YYYY-MM> --json /tmp/fb.json
python scripts/dsys.py feedback apply --period <period>
```

   `apply` updates item statuses in the package, moves continuing items into the ideas registry for the next period, lets everything else expire, and folds topic-level signals into `state/preference_profile.json` (explicit signals override inferred ones; untouched items are only ever counted as "ignored", which planners treat as a timing or format issue, never as dislike).
6. Schedules and life events are **never** recorded: no dates, no reasons, no `config/schedules.json` edits. Use only the generic `skip_reason` values (no_time, too_long, too_hard, not_interesting, other). If something they mention suggests new interests (a trip to Vietnam, say), follow `prompts/update_interests.md` and save general topics only.
7. Clear the inbox (`python scripts/dsys.py inbox clear feedback`), then `history rebuild` and `validate`.

Never respond to feedback with judgement ("you only completed 1 of 5"). Learn from it quietly.
