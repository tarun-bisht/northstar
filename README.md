# Northstar

Northstar is a personal discovery, learning and growth companion. Each day it finds the small fraction of research, news and ideas worth your attention. Each week it suggests things to explore, and each month something to go deep on. It is a compass, not a tracker: no streaks, no scores, no backlog. Read [`docs/vision.md`](docs/vision.md) for why, and [`docs/how_it_works.md`](docs/how_it_works.md) for how.

Live site: [tarunbisht.com/northstar](https://tarunbisht.com/northstar/)

This repo is one person's real setup. Fork it and make it your own.

## What you get

| | Research | Knowledge / News | Exploration | Languages |
|---|---|---|---|---|
| **Daily** | High-quality new papers (arXiv, Hugging Face, alphaXiv), research updates | **News:** 12 to 20 explained stories plus 15 to 30 one-line briefs, from about 30 publisher feeds and Google News, in 12 categories | At least one podcast and one video that play on the page, the rest free, 30 to 40 shorts | A 5-minute pack |
| **Weekly** | Papers of the week (for you, trending, leading groups), Fundamentals, New in AI | Topics by subject (maths and physics always, plus 5 to 6 rotating subjects), each with a study plan and resources, and maths and physics questions | Curiosities, culture, people and self, curiosity and making | A lesson per language |
| **Monthly** | A New in AI deep dive and a Fundamentals deep dive | A deep dive outside AI, and hard challenge problems by subject | An exploration deep dive | A plan per language |
| **Quarterly** | Numbers, a short summary and the topics covered, for each part | | | |

Every week touches every dimension of development in `config/interests.json` (vision §4). Every part has its own page and its own RSS feed. Everything is optional.

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
