# Northstar

Northstar is an open framework for personal growth. It finds what is worth your time each day, suggests small things to learn and try each week, and plans deeper projects each month. It is built to cut noise, not add to it.

Live site: [tarunbisht.com/northstar](https://tarunbisht.com/northstar/)

This repo is one person's real setup. You can fork it and make it your own.

## The idea

Your interests sit in three tiers.

| Tier | What it means | How it is used |
|---|---|---|
| Established | Things you already follow and enjoy. Here that is AI research and its foundations. | Most of what you see |
| Growth | Things you want to get better at. Maths, physics, neuroscience, philosophy, people skills, history, art. | Small steady steps |
| Exploration | Things you have not tried yet. | A little every day to keep your mind fresh |

Everything is optional. There are no streaks, no scores and no backlog. Real life comes first.

## What you get

| Part | When | What it gives you |
|---|---|---|
| arXiv radar | Weekdays | Good new papers that match your interests, each with its abstract and a few fixed tags |
| Research updates | Daily | Short notes on lab posts, new methods, tools and benchmarks |
| World radar | Daily | What happened, why it matters and what to watch, in a few lines |
| Daily discovery | Daily | 3 to 6 picks. Always a podcast, a video and something from each tier |
| Language pack | Daily | 5 minutes of phrases, a short dialogue and practice questions |
| YouTube shorts | Daily | Short videos across your interests, at least one per tier |
| Reading list | Weekly | Papers you should definitely read this week. Daily runs can add to it |
| Weekly package | Saturday | A few small activities plus a lesson for each language you learn |
| Monthly package | 1st of the month | One to three projects with a week by week plan, plus a plan for each language |
| Quarterly look back | Every 3 months | What you explored and what is emerging. Sent to you, never saved |

Paper tags come from one fixed list: close to your work, useful for your work, new method or architecture, strong result, benchmark or dataset, theory, survey or tutorial, worth knowing.

## How to use it

1. Copy the RSS links from the home page into any feed reader, such as Feedly, Inoreader, NetNewsWire, Reeder or Feeder.
2. Read what interests you. Skip the rest.
3. Talk to Claude in a session with this repo. For example, say "I am into pottery now", "less anime", "add Spanish", "let's practise Japanese" or "feedback: I loved the puzzle".
4. Or write ideas and feedback in `inbox/ideas.md` and `inbox/feedback.md` on GitHub. These files are public.

Some feed readers block embedded YouTube players. Every video also has a thumbnail and a link.

## How it runs

1. At 06:00 IST, GitHub Actions fetches new papers from the arXiv API and Hugging Face Daily Papers. It also fetches YouTube videos if a `YOUTUBE_API_KEY` secret is set. No AI runs in this step.
2. Claude scheduled tasks then pick the best items, write short summaries and commit them. They follow the prompts in `prompts/`.
3. GitHub Actions tests everything, builds the RSS feeds and the website, and publishes to GitHub Pages.

## Make it yours

1. Fork the repo. In Settings, turn on Pages with GitHub Actions as the source.
2. Edit `config/interests.json` for your tiers and topics. Edit `config/languages.json` for your languages. Edit `config/sources.json` for arXiv categories and YouTube searches. Edit `config/site.json` for your title and web address.
3. Empty `state/ideas.json` so it reads `{"ideas": []}`.
4. Set up Claude scheduled tasks that follow the files in `prompts/runs/`.

Useful commands:

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/validate.py
python scripts/build.py
python scripts/dsys.py -h
```

## Privacy

The repo, website and feeds are public. Your interests live in the repo but are not shown on the website. Northstar never stores private things such as project names, unpublished work, other people's names, health, relationships, schedules or travel dates. When you share something private, Claude saves only a general topic. For example, a trip becomes "documentaries about that country". The `private/` folder is ignored by Git and is safe for your own notes. Automatic checks catch obvious leaks like keys and email addresses, but they cannot understand meaning.

## Folders

| Folder | What is inside |
|---|---|
| `config/` | Your settings |
| `content/` | Everything that gets published |
| `state/` | Ideas and learned preferences |
| `inbox/` | Free text input that runs read |
| `prompts/` | Instructions Claude follows |
| `schemas/` | File formats |
| `dsys/` and `scripts/` | The toolkit |
| `tests/` | Tests |
