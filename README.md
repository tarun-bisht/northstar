# Northstar

Northstar is a personal discovery, learning and growth companion. Each day it finds the small fraction of research, news and ideas worth your attention. Each week it suggests things to explore, and each month something to go deep on. It is a compass, not a tracker: no streaks, no scores, no backlog. Read [`docs/vision.md`](docs/vision.md) for why, and [`docs/how_it_works.md`](docs/how_it_works.md) for how.

Live site: [tarunbisht.com/northstar](https://tarunbisht.com/northstar/)

This repo is one person's real setup. Fork it and make it your own.

## What you get

| | Research | Knowledge / News | Exploration |
|---|---|---|---|
| **Daily** | High-quality new papers (arXiv, Hugging Face, alphaXiv), research updates, this week's reading list | **News:** 10 to 16 stories by category (India, geopolitics, conflicts, economy and markets, business and tech, science and health, climate and energy, society, explainers) | Podcasts, videos and lectures, reads, things to watch, listen to and try, YouTube shorts, a 5-minute language pack |
| **Weekly** | A research exercise and something worth studying | Questions to think about (maths, physics, science) and things to know and talk about | Culture (music, art, books, films, anime), people and self, curiosity and making, language lessons |
| **Monthly** | A research deep dive | A knowledge deep dive | An exploration deep dive, plus language plans |
| **Quarterly** | Numbers, a short summary and the topics covered, for each part | | |

Every part has its own page and its own RSS feed. Everything is optional.

## How to use it

1. Copy feed links from the home page into a feed reader (Feedly, Inoreader, NetNewsWire, Reeder, Feeder).
2. Read what interests you. Skip the rest.
3. Talk to Claude in a session with this repo: "I am into pottery now", "less anime", "more like the Sakamoto piece", "let's practise Japanese".
4. Or write ideas and feedback in `inbox/ideas.md` and `inbox/feedback.md` on GitHub. These files are public.

## How it runs

1. **06:00 IST, GitHub Actions** fetches candidates: papers, headlines and videos. No AI runs here. Failed sources are retried in the same job and again at 06:50.
2. **Claude scheduled tasks** pick the best items, write short notes and commit them, following `prompts/runs/`.
3. **GitHub Actions** validates everything, builds the site and feeds, and publishes to GitHub Pages.

The full map, including how papers are ranked from their abstracts, is in [`docs/how_it_works.md`](docs/how_it_works.md).

## Make it yours

1. **Fork and publish.** Fork the repo. In **Actions**, turn on workflows. In **Settings → Pages**, set the source to **GitHub Actions**. In **Settings → Environments → github-pages**, allow `main` to deploy.
2. **Personalise.** Edit `config/`: `interests.json` (your tiers), `sources.json` (arXiv coverage, news feeds, YouTube searches), `languages.json` and `site.json`. Then clear my data: delete `content/` and `candidates/`, and set `state/ideas.json` to `{"ideas": []}`.
3. **YouTube key (optional, free).** In [Google Cloud Console](https://console.cloud.google.com/), enable **YouTube Data API v3** and create an API key restricted to it. Add it as the repository secret `YOUTUBE_API_KEY`. The free quota is 10,000 units a day, and each search costs 100.
4. **Scheduled tasks.** Follow [`docs/scheduled_tasks_setup.md`](docs/scheduled_tasks_setup.md), then click **Run now** on the daily task.

```bash
pip install -r requirements.txt
python -m pytest -q          # tests
python scripts/validate.py   # content and config checks
python scripts/build.py      # site and feeds into _site/
python scripts/dsys.py -h    # the toolkit
```
