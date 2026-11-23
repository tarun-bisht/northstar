# Languages (required in daily, weekly and monthly)

Read `prompts/_shared.md` first. Languages and goals live in `config/languages.json` (`learning`, `current_focus`, levels, goals). The goal is **conversation**: speaking and listening with native speakers. Reading comes later unless the config says otherwise.

Always write the **native script, the romanization and the meaning** for every line. Keep it natural, everyday and polite. Build on recent themes without repeating them: `python scripts/dsys.py context language`.

## Daily: a 5-minute pack (current focus language only)

One item per day in `content/language/YYYY/MM/<date>.json`, with `id: "lang-<date>"` and `language: <current_focus>`:

- `theme`: one everyday situation (greetings, café, directions, shopping, small talk, work chat, feelings, numbers and time…). Progress gradually from survival phrases to real conversation.
- `phrases`: 3–6 useful lines; `dialogue`: a 2–6 line exchange that uses them.
- `practice`: 2–4 questions with answers ("How would you say…?", "Respond to…"); answers stay hidden on the site.
- `say_aloud`: one thing to say out loud today. Optionally a verified listening `resource` (a short video or audio clip).
- `minutes` ≤ 5, `tier: "growth"`, `dimensions` such as `["people", "culture"]`.

Merge with `python scripts/dsys.py daily merge language --date <today> --items /tmp/lang.json`. Validation requires a pack every day.

## Weekly: a language section (mix all languages)

Every weekly package has `language.lessons`: 1–4 lessons, usually **one per language** in `learning` (more practice in `current_focus`). Each lesson has:

- `title`, `explanation` (one small grammar point or conversation pattern, explained simply)
- `examples` (3+ lines with script, romanization and meaning)
- `questions` (3+ with answers: translate, respond, fill the gap, choose the polite form)
- `practice`: speaking and listening tasks ("role-play ordering with Claude", "shadow this clip three times", "greet one native speaker")
- optional verified `resources` (a lesson video, podcast episode, or textbook chapter)

## Monthly: a plan per language

Every monthly package has `language.plans`, with one plan per language (at least the current focus): a `goal` for the month (a concrete conversation ability, e.g. "a 2-minute self-introduction and small talk"), 4 `weeks` with concrete tasks, and verified `resources` (courses with units, textbooks with chapters, podcasts, YouTube channels).

## Changing languages

"Switch my daily focus to Telugu", "add Spanish", "I'm intermediate in Japanese now": edit `config/languages.json` (`current_focus`, `learning`, `level`, `goal`). Never record why someone is learning a language.
