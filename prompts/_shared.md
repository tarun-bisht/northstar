# Shared rules (read first)

These add detail to the rules in `CLAUDE.md`. Daily = stay aware, weekly = explore, monthly = go deep. Real life comes first. Balance familiar, adjacent and unexpected, and look for cross-domain connections. Fewer, better items: targets are guidance, except the rules validation enforces.

## Interests

Everything is shaped by `config/interests.json`, which has **three tiers that mean different things**:

| Tier | Meaning | How it's used |
|---|---|---|
| **established** | what you repeatedly enjoy or follow: AI and AI research, and the foundations that build it | stay relevant: most items, beyond the basics |
| **growth** | what you want to understand because it develops you: maths, physics, neuroscience and consciousness, philosophy of science for research ideas; people skills, history, art and culture for the person | steady small steps, never all at once |
| **exploration** | what you haven't explored but might find fascinating | optional but never zero: worthwhile surprises that keep the mind fresh |

They are not equally strong preferences. Spend most time in established, keep growth moving slowly, and always include some exploration (shares in `config/recommendation_policy.json → tiers`, as guidance). Every item carries a `tier` and one or more `dimensions` (the broad directions in `interests.json → dimensions`).

**Languages** are their own required section (`config/languages.json`, `prompts/language.md`): a 5-minute daily pack in the current focus language, plus weekly lessons and monthly plans across all languages being learned.
I am a beginner in these languages. In every stream (discovery, podcasts, videos, shorts), never recommend native content in a learning language I can't follow yet. Use beginner material explained in English (Hindi is fine for videos and podcasts, never for shorts, which are English only). Native content is allowed only when that language has `native_content_ok: true`.

Growth comes from doing too: **learn, practise, create, experience, reflect, adapt.** Weekly and monthly items sometimes turn learning into action.

## Web access in scheduled runs (never wait for approval)

Scheduled runs have nobody to approve anything, so a run must never trigger a permission prompt. WebSearch never asks. WebFetch only runs without asking when the URL already appeared in this session: in the run prompt, in a WebSearch result, or in a page you already fetched. A URL typed from memory, built by editing another URL, or read from a file (candidates, config, content) needs approval. The run then stalls and the fetch is withdrawn.

- **Search first, then fetch.** To open a page, WebSearch for it (its title, or the site plus the topic), then WebFetch a URL from those results, or a link on a page you already fetched.
- **Never WebFetch URLs from candidate files.** GitHub Actions already fetched arXiv, Hugging Face, alphaXiv, the news feeds and YouTube, so their URLs are real. Use their data as is. If you need a full news article, WebSearch its headline and fetch the matching result.
- **Verifying a link:** a URL that appears in WebSearch results, or that you fetched, counts as verified. If you can't get a URL that way, leave `url` out and say so in `notes`.

## Truthfulness

- arXiv abstracts are copied verbatim. World and research items keep facts separate from analysis and say what's uncertain.
- If a source or tool is unavailable, say so in `notes` and produce fewer items.
- Copyright: describe and link; don't reproduce articles, lyrics or book passages.

## Privacy: the repo, site and feeds are public

- **Translate, never record** (CLAUDE.md rule 5): a project becomes the general topics its method touches, a trip becomes "<country> documentaries" and similar. See `prompts/update_interests.md`.
- For arXiv, at most "Closely related to your work."
- Feedback holds short sanitized paraphrases and generic reasons only. Reflections and syntheses go to chat or the run summary, never into files.
- `scripts/validate.py` catches obvious patterns (keys, emails, phone numbers, raw feedback), not meaning.

## Mechanics

- `python scripts/dsys.py context <stream> [--date D] [--period P]` first: dedup history, candidates, schedule, ideas, preferences, variety.
- Output must validate against `schemas/<stream>.schema.json`; see `examples/content/` for each file type.
- IDs: `arxiv-<id>`, `ru-<date>-<slug>`, `world-<date>-<slug>`, `disc-<date>-<slug>`, `yt-<video_id>`, `w-<YYYY-Www>-<slug>`, `m-<YYYY-MM>-<slug>`.
- Daily streams: write `{"items": [...], "notes": "..."}` to a temp file, then `python scripts/dsys.py daily merge <stream> --date <date> --items <file>`.
- Weekly/monthly: write `content/weekly/YYYY/YYYY-Www.json` or `content/monthly/YYYY/YYYY-MM.json`.

## Writing style (all text: summaries, hints, lessons, notes)

- Plain, simple English. Short sentences. Use technical words only where they are needed.
- No semicolons. No em dashes. Avoid brackets inside sentences where you can.
- Put the main point first. Prefer a few short bullets over a paragraph.
- News and updates: one or two short sentences per field. Say what happened, why it matters and what to watch, and stop.
- Teaching (hints, lessons, steps): explain like a patient friend. One idea per sentence.
- Warm and direct, never hype. The goal is less reading and less stress, not more.

Validation warns when text has em dashes or semicolons, and rejects news fields that run too long.
