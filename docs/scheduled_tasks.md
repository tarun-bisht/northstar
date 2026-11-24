# Scheduled tasks

Northstar runs on five Claude scheduled tasks. To set them up (or recreate them), start a Claude Code session on this repo and say:

> Create the five scheduled tasks in docs/scheduled_tasks.md exactly as written, with automatic approval. Delete any older scheduled tasks with the same names first.

All times are in `Asia/Kolkata`. Change the time zone and times to suit you. Every task starts after the 06:00 IST candidate fetch on GitHub Actions.

Every prompt shares the same first step:

```
Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
```

Fork owners: replace `tarun-bisht/northstar` with your own repo.

## Daily northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 19 7 * * *`

```
You are running the DAILY RADAR for my Northstar personal growth system in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md, then prompts/_shared.md, then follow prompts/runs/daily.md exactly: inbox ideas, the arXiv radar (Monday to Friday, from candidates/arxiv/<today>.json, which has arXiv and Hugging Face Daily Papers candidates), research updates, world radar, daily discovery, the reading list, and the daily language pack.
3. arXiv: keep only good, relevant papers. Copy each abstract word for word. Give 1 to 3 tags from the fixed paper_tags list only, and never write a reason. Add any must-read paper or lab technical report to this week's reading list with `python scripts/dsys.py reading add`.
4. Daily Discovery MUST include an established-tier podcast, a video, lecture or documentary, and at least one item per tier. Recommend only content in English or Hindi. I am a beginner in Japanese and Telugu, so never recommend native content in those languages, only beginner material explained in English or Hindi, unless config/languages.json sets native_content_ok true. The 5-minute language pack is REQUIRED. Write everything in plain, short English with no semicolons or em dashes, main point first. Verify every link. Never invent anything. Never store private information.
5. Run `python scripts/dsys.py history rebuild` and `python scripts/validate.py`, fix all errors, then commit and push to main as described in prompts/runs/_git.md. Never force-push.
6. End with a short summary: items per stream, papers kept and their top tags, anything added to the reading list, today's language theme, and any limitation hit.
```

## Shorts northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 15 8 * * *`

```
You are running the YOUTUBE SHORTS RADAR for my Northstar personal growth system in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md, then prompts/_shared.md, then follow prompts/runs/shorts.md and prompts/youtube_shorts.md exactly.
3. Target about 100 short videos in languages I understand: English and Hindi (config/sources.json, youtube.languages_accepted). This is NOT a quota, so never add filler. I am only a beginner in Japanese and Telugu, so never add native Japanese or Telugu videos. Instead add a few beginner lesson shorts for each, taught in English or Hindi (useful phrases, pronunciation, simple conversation), tagged tier growth and category "language learning". Native videos are allowed only for a language with native_content_ok true in config/languages.json.
4. Tag every video with a tier (established, growth or exploration, per config/interests.json): most established, a steady share of growth, some exploration, and at least one per tier (validation enforces this). Use only legitimate access: candidates/youtube/<today>.json (from the YouTube Data API via GitHub Actions) if present; otherwise web search plus oEmbed verification of each video ID. Never guess video IDs or scrape YouTube HTML. Label a video 'short' only when format_evidence is shorts_url_check. Write any text in plain, short English with no semicolons or em dashes. Never store private information.
5. Run `python scripts/dsys.py history rebuild` and `python scripts/validate.py`, fix all errors, then commit and push to main as described in prompts/runs/_git.md. Never force-push.
6. End with a short summary: number of videos, the mode used, the language split, the tier split and the language-learning shorts added.
```

## Weekly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 46 6 * * 6` (Saturday)

```
You are running the WEEKLY PACKAGE for my Northstar personal growth system in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md, then prompts/_shared.md, then follow prompts/runs/weekly.md exactly. In order: process inbox/feedback.md (prompts/feedback.md; if there is none, do nothing and don't invent any), process inbox/ideas.md (prompts/inbox.md), plan the week starting next Monday (prompts/weekly.md), and create next week's paper reading list (prompts/reading_list.md).
3. Reading list (required): 3 to 8 papers I should definitely read, relevant to my interests or methods, a new concept or architecture, or a paper with future potential. Sources can be the arXiv radar, Hugging Face trending, researcher posts on X or LinkedIn, or AI lab technical reports. Use only the fixed paper_tags, and add at most one short plain note. Verify every link.
4. Weekly package: optional for me. Mostly established, one growth step, some exploration. Learning items need detailed steps and real resources. The language section is required: one lesson per language in config/languages.json. Include every idea I scheduled. Write in plain, short English with no semicolons or em dashes. Never store private information.
5. Run `python scripts/dsys.py history rebuild` and `python scripts/validate.py`, fix all errors, then commit and push to main as described in prompts/runs/_git.md. Never force-push.
6. End with the reading list titles, the package in 4 to 6 short lines, the language lesson titles, and one line saying I can reply in inbox/feedback.md or a Claude chat, or ignore it.
```

## Monthly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 15 6 1 * *`

```
You are running the MONTHLY PACKAGE for my Northstar personal growth system in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md, then prompts/_shared.md, then follow prompts/runs/monthly.md exactly. In order: process feedback in inbox/feedback.md about last month's package (prompts/feedback.md; if there is none, do nothing); process inbox/ideas.md (prompts/inbox.md); then plan this month (prompts/monthly.md), using `python scripts/dsys.py context monthly --period <this_month>`.
3. Plan 1 to 3 optional items, each about one month in scope, each with a light version, and never open-ended. Always include at least one growth reading or exercise in science, mathematics, neuroscience or philosophy that can broaden my research thinking. Every item is a real syllabus: four weeks of concrete tasks, a primary resource plus further verified resources (books with chapter numbers, lecture numbers, videos, blogs, papers), exercises, a deliverable and a definition of done. The language section is REQUIRED: a plan per language in config/languages.json (now Japanese and Telugu), each with a concrete conversation goal, four weeks of tasks and verified resources (prompts/language.md). Include every idea I scheduled for this month. Write in plain, short English with no semicolons or em dashes, main point first. Never invent resources. Never store private information.
4. Run `python scripts/dsys.py history rebuild` and `python scripts/validate.py`, fix all errors, then commit and push to main as described in prompts/runs/_git.md. Never force-push.
5. End with the projects, one line each, with their tiers and light versions, plus each language's goal for the month.
```

## Quarterly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 41 6 1 1,4,7,10 *`

```
You are running the optional QUARTERLY SYNTHESIS for my Northstar personal growth system in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md, then prompts/_shared.md, then follow prompts/runs/quarterly.md and prompts/quarterly.md. Review the quarter that just ended (for example on 1 April, review <year>-Q1) using `python scripts/dsys.py synthesis --quarter <YYYY-Qn>`.
3. This is not a performance review: no percentages, no ranking, no judgement. Be honest when the evidence is thin. Look at the balance across the established, growth and exploration tiers.
4. The synthesis is personal. Put it ONLY in your final message and never write it to a file in the repo. Commit only small, sanitized system adjustments (for example moving a topic between tiers in config/interests.json), and only if they are clearly helpful. Run `python scripts/validate.py` before committing and never force-push.
5. End with the synthesis, short and warm, in plain English with no semicolons or em dashes, then one line per system change you made or propose.
```
