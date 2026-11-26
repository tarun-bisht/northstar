# Northstar

Northstar is a personal discovery, learning and growth companion. Each day it finds the small fraction of research, news and ideas worth your attention. Each week it suggests things to explore, and each month something to go deep on. It is a compass, not a tracker: no streaks, no scores, no backlog. Read [`docs/vision.md`](docs/vision.md) for why, and [`docs/how_it_works.md`](docs/how_it_works.md) for how.

Live site: [tarunbisht.com/northstar](https://tarunbisht.com/northstar/)

This repo is one person's real setup. Fork it and make it your own.

## What you get

| | Research | Knowledge / News | Exploration | Languages |
|---|---|---|---|---|
| **Daily** | High-quality new papers every day (arXiv, Hugging Face, alphaXiv, Reddit, Bluesky), research updates from labs, researchers and newsletters | **News:** 12 to 20 explained stories plus 15 to 30 one-line briefs, from about 30 publisher feeds and Google News, in 12 categories | At least one podcast and one video that play on the page, the rest free, each with what you'll learn. Shorts on their own page | A 5-minute pack |
| **Weekly** | Papers of the week (for you, trending, leading groups), Fundamentals, New in AI | Topics by subject (maths and physics always, plus 5 to 6 rotating subjects), each with a study plan and resources, and maths and physics questions | Curiosities, culture, people and self, curiosity and making | A lesson per language |
| **Monthly** | A New in AI deep dive and a Fundamentals deep dive | A deep dive outside AI, and hard challenge problems by subject | An exploration deep dive | A plan per language |
| **Quarterly** | Numbers, a short summary and the topics covered, for each part | | | |

Slack is the only notification: a daily "ready" message with links and how many items were read and picked, polls on Thursdays and the 25th where you pick what to go deep on next, and something light in #random.

GitHub Actions scrapes everything (papers, news, research updates, podcasts, videos). Claude only reads and filters: Haiku reads every candidate paper abstract, Opus makes the final choices. Every paper link opens on alphaXiv.

Every week touches every dimension of development in `config/interests.json` (vision §4). Every part has its own page and its own RSS feed. Everything is optional.

## How to use it

1. Copy feed links from the home page into a feed reader (Feedly, Inoreader, NetNewsWire, Reeder, Feeder).
2. Read what interests you. Skip the rest.
3. Talk to Claude in a session with this repo: "I am into pottery now", "less anime", "more like the Sakamoto piece", "let's practise Japanese".
4. Or write ideas and feedback in `inbox/ideas.md` and `inbox/feedback.md` on GitHub. These files are public.

## How it runs

| When (IST) | What |
|---|---|
| 07:17, retry 07:53 | GitHub Actions scrapes papers, news, updates, podcasts and videos. No AI. |
| 08:13 daily | Claude reads, filters and writes the day, posts polls on Thursdays and the 25th, and sends the Slack messages. |
| Saturday 06:46 | Claude plans next week (after reading your poll answer). |
| 1st 06:15 | Claude plans the month (after reading your poll answer). |
| 1 Jan, Apr, Jul, Oct 06:41 | Claude writes the quarterly review. |
| Every push | GitHub Actions validates, builds the site and feeds, and publishes. |

If GitHub starts the scrape late, the daily run starts it and waits. It never searches instead. The full map is in [`docs/how_it_works.md`](docs/how_it_works.md).

## Make it yours

Follow [`docs/scheduled_tasks_setup.md`](docs/scheduled_tasks_setup.md). It copies this exact setup in eight steps:

1. Fork, then turn on Actions and Pages.
2. Edit `config/` for your interests, sources and languages, and clear my data.
3. Add a free `YOUTUBE_API_KEY` secret.
4. Create the Slack channels and put their ids in `config/notifications.json`.
5. Connect Slack and alphaXiv to Claude.
6. Create the four scheduled tasks (exact prompts, crons and models are in the guide).
7. Change time zones if you need to.
8. Run it once and check.

```bash
pip install -r requirements.txt
python -m pytest -q          # tests
python scripts/validate.py   # content and config checks
python scripts/build.py      # site and feeds into _site/
python scripts/dsys.py -h    # the toolkit
```
