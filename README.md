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

**1. Fork and publish**

1. Fork the repo.
2. Open the **Actions** tab and turn on workflows. Forks start with them off.
3. In **Settings → Pages**, set the source to **GitHub Actions**.
4. In **Settings → Environments → github-pages**, make sure `main` is allowed to deploy.

**2. Personalise**

1. Edit the files in `config/`. Use `interests.json` for your tiers, `languages.json` for your languages, `sources.json` for arXiv categories and YouTube searches, and `site.json` for your title, web address and repo.
2. Clear my data. Delete everything in `content/` and `candidates/`, and set `state/ideas.json` to `{"ideas": []}`.

**3. YouTube key (optional, free)**

Without a key, Shorts come from web search and you get far fewer of them.

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project.
2. Go to **APIs & Services → Library** and enable **YouTube Data API v3**.
3. Go to **APIs & Services → Credentials → Create credentials → API key**. Restrict the key to YouTube Data API v3.
4. In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**. Name it `YOUTUBE_API_KEY` and paste the key.

The free quota is 10,000 units a day. Each search costs 100, so keep the searches in `config/sources.json` under 100.

**4. Claude scheduled tasks**

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines) and create the five tasks in [`docs/scheduled_tasks.md`](docs/scheduled_tasks.md). Copy each name, prompt and schedule. Put your own repo in the prompts.
2. For each task, set **Repository** to your fork. No connectors are needed, and the **Default** environment is fine.
3. Click **Run now** on the daily task to test it.

Useful commands:

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/validate.py
python scripts/build.py
python scripts/dsys.py -h
```

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
