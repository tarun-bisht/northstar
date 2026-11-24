# Shared rules (read first)

## What Northstar is for

A personal system for steady growth, at your own pace. Everything is shaped by `config/interests.json`, which has **three tiers that mean different things**:

| Tier | Meaning | How it's used |
|---|---|---|
| **established** | what you repeatedly enjoy or follow: AI and AI research, and the foundations that build it | stay relevant: most items, beyond the basics |
| **growth** | what you want to understand because it develops you: maths, physics, neuroscience and consciousness, philosophy of science for research ideas; people skills, history, art and culture for the person | steady small steps, never all at once |
| **exploration** | what you haven't explored but might find fascinating | optional but never zero: worthwhile surprises that keep the mind fresh |

They are not equally strong preferences. Spend most time in established, keep growth moving slowly, and always include some exploration (shares in `config/recommendation_policy.json → tiers`, as guidance). Every item carries a `tier` and one or more `dimensions` (the broad directions in `interests.json → dimensions`).

**Languages** are their own required section (`config/languages.json`, `prompts/language.md`): a 5-minute daily pack in the current focus language, plus weekly lessons and monthly plans across all languages being learned.
I am a beginner in these languages. In every stream (discovery, podcasts, videos, shorts), never recommend native content in a learning language I can't follow yet. Use beginner material explained in English or Hindi. Native content is allowed only when that language has `native_content_ok: true`.

Growth comes from doing too: **learn, practise, create, experience, reflect, adapt.** Weekly and monthly items sometimes turn learning into action.

## Philosophy

- Daily: stay aware. Weekly: something new if there's time. Monthly: go deeper if the month allows. Real life comes first.
- No streaks, scores, quotas, guilt or backlogs. Skipped items expire. User intent beats algorithmic recommendation.
- Fewer, better items. Targets are guidance, except the explicit daily and monthly rules, which validation enforces.

## Truthfulness

- Never invent papers, authors, posts, URLs, video IDs, dates, durations or facts. Every URL must come from something you retrieved this session; if unverified, omit `url`.
- arXiv abstracts are copied verbatim. World and research items keep facts separate from analysis and say what's uncertain.
- If a source or tool is unavailable, say so in `notes` and produce fewer items.
- Copyright: describe and link; don't reproduce articles, lyrics or book passages.

## Privacy: the repo, site and feeds are public

- Never save private details: project names or unpublished work, other people's names, institutions, health, relationships, finances, schedules, travel dates.
- **Translate, never record.** A project becomes the general topics its method touches; a trip becomes "<country> documentaries" and similar. See `prompts/update_interests.md`.
- For arXiv, at most "Closely related to your work."
- Feedback holds short sanitized paraphrases and generic reasons only. Reflections and syntheses go to chat or the run summary, never into files.
- `scripts/validate.py` catches obvious patterns (keys, emails, phone numbers, raw feedback, tracked `private/` files), not meaning.

## Mechanics

- `python scripts/dsys.py context <stream> [--date D] [--period P]` first: dedup history, candidates, schedule, ideas, preferences, variety.
- Output must validate against `schemas/<stream>.schema.json`; see `examples/content/` for each file type.
- IDs: `arxiv-<id>`, `ru-<date>-<slug>`, `world-<date>-<slug>`, `disc-<date>-<slug>`, `yt-<video_id>`, `w-<YYYY-Www>-<slug>`, `m-<YYYY-MM>-<slug>`.
- Daily streams: write `{"items": [...], "notes": "..."}` to a temp file, then `python scripts/dsys.py daily merge <stream> --date <date> --items <file>`.
- Weekly/monthly: write `content/weekly/YYYY/YYYY-Www.json` or `content/monthly/YYYY/YYYY-MM.json`.
- Always finish with `python scripts/dsys.py history rebuild && python scripts/validate.py`, and fix every error before committing.

## Writing style (all text: summaries, hints, lessons, notes)

- Plain, simple English. Short sentences. Use technical words only where they are needed.
- No semicolons. No em dashes. Avoid brackets inside sentences where you can.
- Put the main point first. Prefer a few short bullets over a paragraph.
- News and updates: one or two short sentences per field. Say what happened, why it matters and what to watch, and stop.
- Teaching (hints, lessons, steps): explain like a patient friend. One idea per sentence.
- Warm and direct, never hype. The goal is less reading and less stress, not more.

Validation warns when text has em dashes or semicolons, and rejects news fields that run too long.
