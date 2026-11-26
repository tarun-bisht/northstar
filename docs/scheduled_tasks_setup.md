# Set up your own Northstar

This copies the full setup: GitHub Actions to fetch and publish, four Claude scheduled tasks to curate, and Slack to notify. It takes about 30 minutes. Times are IST (`Asia/Kolkata`). To use another zone, see step 7.

## What runs when

| When (IST) | What | Where |
|---|---|---|
| Every day 07:17, retry 07:53 | Fetch candidates: papers, news, updates, podcasts, videos, shorts, fun | GitHub Actions (`fetch-candidates.yml`) |
| Every day 08:13 | **Daily** task (Sonnet, with Haiku, Opus and Sonnet helpers) | Claude |
| Saturday 06:46 | **Weekly** task (Opus) | Claude |
| 1st of the month 06:15 | **Monthly** task (Opus) | Claude |
| 1 Jan, Apr, Jul, Oct 06:41 | **Quarterly** task (Sonnet) | Claude |
| On every push to `main` | Validate, build the site and feeds, publish | GitHub Actions (`build-and-publish.yml`) |

The daily task needs today's fetch, so it runs after it. If GitHub starts the fetch late, the daily task starts it itself and waits (`dsys.py candidates ensure`). Weekly and monthly run before the fetch on purpose: they plan from earlier days, and the daily task announces them in Slack.

What each task does in Slack:

| Task | Slack |
|---|---|
| Daily | Reads answers in #northstar-ask. Posts polls in #northstar-polls on Thursdays (weekly) and the 25th (monthly). Posts the "ready" message in #northstar-daily, plus the week on Saturdays and the month on the 1st. Posts the quarterly review in #general at a quarter start. One light post in #random. |
| Weekly | Reads the weekly poll thread in #northstar-polls and replies "Got it" if you answered. |
| Monthly | Reads the monthly poll thread in #northstar-polls and replies "Got it" if you answered. |
| Quarterly | Nothing. The daily task announces it. |

No task ever posts about a failed source. Mobile and email notifications are off.

## Steps

### 1. Fork and publish

1. Fork this repo.
2. **Actions:** turn on workflows.
3. **Settings → Pages:** set the source to **GitHub Actions**.
4. **Settings → Environments → github-pages:** allow `main` to deploy.
5. Set `config/site.json → base_url` to your Pages address.

### 2. Make it yours

1. Edit `config/interests.json` (your three tiers). Add an `arxiv.coverage` entry in `config/sources.json` for each research interest.
2. Edit `config/sources.json` (arXiv categories, news feeds, YouTube channels and searches), `config/languages.json` and `config/preferences.json` if you like.
3. Clear my data: delete `content/`, `candidates/` and `state/stats/`, and set `state/ideas.json` to `{"ideas": []}` and `state/polls.json` to `{"polls": []}`.
4. Optional: rebuild the trust registry with **Actions → build-reputation → Run workflow**.

### 3. YouTube key (free, needed for videos and shorts)

In [Google Cloud Console](https://console.cloud.google.com/), enable **YouTube Data API v3** and create an API key restricted to it. Add it as the repository secret `YOUTUBE_API_KEY`. The free quota (10,000 units a day) is enough. Without it there are no videos or shorts, and Daily Discovery fails validation because it needs one video a day.

### 4. Slack

1. Create a Slack workspace (free is fine).
2. Create four public channels: `#northstar-daily`, `#northstar-polls` and `#northstar-ask`. `#general` and `#random` already exist.
3. Put each channel id in `config/notifications.json` (open the channel, then **channel name → About**, the id is at the bottom). Commit.
4. Connect Slack to Claude: **claude.ai → Settings → Connectors → Slack**.

### 5. alphaXiv (optional)

Connect **alphaXiv** in **claude.ai → Settings → Connectors** and sign in. The daily task adds your alphaXiv *For You* and *Hot* papers to the pool. Without it, that step is skipped.

### 6. Create the four tasks

Use a Claude Code environment that can push to your fork (the Claude GitHub app installed on the repo). The fetch dispatch (`candidates ensure`) uses the same access.

**Option A, let Claude do it.** Start a Claude session with Slack and alphaXiv connected and paste this, with `OWNER/REPO` set to your fork:

```
Set up the Northstar scheduled tasks for https://github.com/OWNER/REPO.
1. Read docs/scheduled_tasks_setup.md in that repo.
2. Delete any existing Northstar scheduled tasks.
3. Create the four tasks under "The tasks", with each name, cron, model and prompt exactly as written, replacing tarun-bisht/northstar with OWNER/REPO. Give every task my Slack and alphaXiv connectors, automatic approval, and push and email notifications off.
4. List each task with its schedule, next run, model and approval mode.
```

Running it again is safe: it replaces the tasks.

**Option B, by hand.** At [claude.ai/code/routines](https://claude.ai/code/routines), create each task below with its name, cron, model and prompt. Replace `tarun-bisht/northstar` with your fork. Add the **Slack** and **alphaXiv** connectors, turn on **Automatically approve**, and turn notifications off.

### 7. Other time zones

Change `CRON_TZ=Asia/Kolkata` in each task and the UTC crons in `.github/workflows/fetch-candidates.yml`. Keep the daily task at least 50 minutes after the main fetch, and keep weekly and monthly before the daily task.

### 8. Check it works

1. **Actions → fetch-candidates → Run workflow**, and wait for it to finish.
2. Open the daily task and click **Run now**.
3. Check: a `daily: <date>` commit on `main`, the site rebuilt, and a "ready" message in #northstar-daily.
4. If the run couldn't push or start the fetch, check the environment's GitHub access.

## The tasks

The prompts are short on purpose: the logic lives in the repo (`CLAUDE.md`, `prompts/runs/`). To change what a run does, edit the repo, not the task. Each prompt still names its Slack steps, so none gets skipped.

### Daily northstar schedule

Cron `CRON_TZ=Asia/Kolkata 13 8 * * *` · Model `claude-sonnet-5-5`

```
You are running the DAILY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/daily.md exactly, every step in order. It waits for today's fetch, reads answers to questions in #northstar-ask, makes the whole day (papers, research updates, news, exploration, languages and shorts, with Haiku, Opus and Sonnet helpers), validates, commits and pushes to main.
3. After pushing, do the Slack steps in prompts/runs/daily.md:
   - on Thursdays and the 25th, post the topic polls in #northstar-polls (prompts/runs/topic_poll.md);
   - always post the "ready" message in #northstar-daily, with the weekly one on Saturdays and the monthly one on the 1st, the quarterly review in #general at a quarter start, and one light post in #random (prompts/runs/slack_digest.md).
   Channel ids are in config/notifications.json. Post only there, and never about failed sources.
4. Never force-push. Never store private information.
```

### Weekly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 46 6 * * 6` (Saturday) · Model `claude-opus-5-5`

```
You are running the WEEKLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/weekly.md exactly, every step in order:
   - first read the answers to the weekly poll in #northstar-polls (the whole thread and the user's later messages in the channel), save them and reply "Got it" in the thread if there was an answer (prompts/runs/poll_collect.md);
   - then plan next week's package with all parts, and Papers of the week with at least 3 entries;
   - validate, commit and push to main.
3. Post nothing else to Slack: the daily run announces the week. Channel ids are in config/notifications.json.
4. Never force-push. Never store private information.
```

### Monthly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 15 6 1 * *` · Model `claude-opus-5-5`

```
You are running the MONTHLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/monthly.md exactly, every step in order:
   - first read the answers to the monthly poll in #northstar-polls (the whole thread and the user's later messages in the channel), save them and reply "Got it" in the thread if there was an answer (prompts/runs/poll_collect.md);
   - then plan this month's deep dives, challenges and language plans;
   - keep the trust registry current (config/reputation.json);
   - validate, commit and push to main.
3. Post nothing else to Slack: the daily run announces the month. Channel ids are in config/notifications.json.
4. Never force-push. Never store private information.
```

### Quarterly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 41 6 1 1,4,7,10 *` · Model `claude-sonnet-5-5`

```
You are running the QUARTERLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/quarterly.md exactly: review the quarter that just ended, validate, commit and push to main.
3. Post nothing to Slack: the daily run posts the review link in #general.
4. Never force-push. Never store private information.
```
