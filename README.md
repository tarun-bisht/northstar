# Northstar

An open, configurable framework for personal growth, learning, curiosity and discovery.

**Live:** [tarunbisht.com/northstar](https://tarunbisht.com/northstar/). This repo is one person's real setup; fork it and make it yours.

## Idea

Your interests live in three tiers that mean different things:

| Tier | What it is | How Northstar uses it |
|---|---|---|
| **Established** | what you follow and enjoy (here: AI research and its foundations) | most of your time, to stay relevant |
| **Growth** | what you want to understand because it develops you (maths, physics, neuroscience, philosophy, people skills, history, art) | small, steady steps |
| **Exploration** | what you haven't explored yet | optional but always present, to keep the mind fresh |

Every item is also tagged with **dimensions**: Researcher, Knowledge Explorer, World Radar, People and Self, Culture and Life, Curiosity, Discovery and Making.

Daily keeps you aware, weekly suggests something new, and monthly goes deeper. All of it is optional: no streaks, scores or backlogs, and real life comes first. Learning turns into doing: practise, create, experience, reflect.

## What it produces

| Component | When | What you get |
|---|---|---|
| arXiv Paper Radar | Mon–Fri | relevant new papers with the original abstract |
| Research Updates | daily | lab posts, methods, tools, benchmarks, debates |
| World Radar | daily | what happened, why it matters, what to watch |
| Daily Discovery | daily | 3–6 picks; **always** an established-tier podcast, a video or lecture, and something from each tier |
| YouTube Shorts | daily | up to ~100 short videos (English and Hindi), at least one per tier |
| Weekly package | Saturday | 3–5 small optional activities; every learning item has steps and resources |
| Monthly package | 1st | 1–3 one-month projects with a week-by-week syllabus (books with chapters, lectures, papers); always one growth reading in science, maths, neuroscience or philosophy |
| Quarterly synthesis | Jan/Apr/Jul/Oct | what you explored and what's emerging; delivered to you, never saved |

Validation enforces the **bold** daily rules and the weekly and monthly syllabus rules.

## Using it

- **Read:** add the feed URLs from the home page to any RSS reader (Feedly, Inoreader, NetNewsWire, Reeder, Feeder, Thunderbird). Some readers block embedded YouTube players; every video also has a thumbnail and a link.
- **Talk to Claude** in a Claude Code session with this repo: "I'm into pottery", "less anime", "I want to try X next month", "feedback: loved the puzzle, skipped the film". Claude updates the files and commits.
- **Or write** in `inbox/ideas.md` and `inbox/feedback.md` on GitHub. The next scheduled run processes them. These files are public.

## How it runs

```
GitHub Actions 06:00 IST         Claude scheduled tasks           GitHub Actions
fetch arXiv + YouTube data  ──▶  pick, write, validate, commit ──▶ test → RSS → site
(official APIs, no AI)           (prompts/runs/*.md)              (GitHub Pages)
```

arXiv uses its free official API (categories in `config/sources.json`). YouTube uses the Data API if a `YOUTUBE_API_KEY` secret is set; otherwise web search plus oEmbed, with far fewer videos. A video is called a Short only with evidence; otherwise "short video".

## Fork and configure

1. Fork. Enable Pages (Settings → Pages → Source: GitHub Actions). Optionally add `YOUTUBE_API_KEY`.
2. Edit `config/interests.json` (tiers, dimensions, world regions and topics), `config/sources.json` (arXiv categories, YouTube queries), `config/site.json` (title, URL).
3. Clear `state/ideas.json` to `{"ideas": []}`.
4. Set up scheduled Claude tasks that follow `prompts/runs/` (daily, shorts, weekly, monthly, quarterly).

```bash
pip install -r requirements.txt
python -m pytest -q              # tests
python scripts/validate.py       # config, content, privacy
python scripts/build.py          # RSS + site into _site/
python scripts/dsys.py -h        # toolkit: ideas, interests, feedback, context, …
```

## Public by design

The repo, site and feeds are public. Interests and ideas live in the repo but are never shown on the website. Never stored anywhere: credentials, project names or unpublished work, other people's names, health, relationships, schedules or travel dates, raw feedback or reflections. Claude **translates, never records**: a project becomes general topics, a trip becomes "Vietnam documentaries". `private/` is gitignored for local notes. Validation scans for obvious leaks (keys, emails, phone numbers), not meaning.

## Layout

`config/` settings · `content/` published items · `state/` ideas and learned preferences · `feedback/` sanitized feedback · `inbox/` free-text input · `candidates/` raw API data · `prompts/` how Claude generates · `schemas/` file formats · `dsys/` + `scripts/` toolkit · `tests/` · `examples/` sample data
