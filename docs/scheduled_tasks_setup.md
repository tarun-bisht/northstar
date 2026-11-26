# Scheduled tasks setup

Northstar runs on four Claude scheduled tasks. Each task starts a fresh Claude session that clones this repo and follows one runbook in `prompts/runs/`. The task prompts are deliberately short: all the logic lives in the repo (`CLAUDE.md`, `docs/vision.md`, `prompts/`). To change what a run does, edit the repo, not the task.

| Task | When (IST) | Model | Runbook | What it does |
|---|---|---|---|---|
| Daily northstar schedule | Every day, 08:13 | Sonnet (starts Haiku, Opus and Sonnet helpers) | `prompts/runs/daily.md` | Research, News, Exploration, Shorts and Languages; topic polls on Thursdays and the 25th; the Slack "ready" messages and #random |
| Weekly northstar schedule | Saturday, 06:46 | Opus | `prompts/runs/weekly.md` | Reads the weekly poll answers, then next week's package and Papers of the week |
| Monthly northstar schedule | 1st of the month, 06:15 | Opus | `prompts/runs/monthly.md` | Reads the monthly poll answers, then the month's deep dives, challenges and language plans; keeps the trust registry current |
| Quarterly northstar schedule | 1 Jan, Apr, Jul, Oct, 06:41 | Sonnet | `prompts/runs/quarterly.md` | A short public review per part, with numbers |

The other runbooks are steps these call: `shorts.md` (a helper of the daily run), `topic_poll.md` and `slack_digest.md` (daily run), `poll_collect.md` (weekly and monthly runs).

**Connectors and notifications.** Every task has the Slack and alphaXiv connectors. Mobile push and email are off for every task. Slack channels are in `config/notifications.json`.

**Timing.** GitHub Actions fetches at 07:17 IST and retries failed sources at 07:53. GitHub can start these hours late, so the daily run starts the fetch itself when today's files are missing (`dsys.py candidates ensure`). The weekly and monthly runs finish before the daily run, which then announces them.

## Before you start

1. Fork this repo and turn on GitHub Actions and Pages (README, "Make it yours").
2. Edit `config/` for your interests, sources and languages.
3. Have a Claude account with scheduled tasks and Claude Code on the web.

## Option A: let Claude set it up (recommended)

Start a Claude session, replace `OWNER/REPO` with your fork, and paste:

```
Set up the Northstar scheduled tasks for my GitHub repo https://github.com/OWNER/REPO.

1. Read docs/scheduled_tasks_setup.md in that repo.
2. Delete any existing Northstar scheduled tasks.
3. Create the four tasks under "The tasks" in that file, with mobile and email notifications off and the model shown. Give every task my Slack and alphaXiv connectors. Use each name, cron schedule and prompt exactly as written. If my repo is not tarun-bisht/northstar, replace tarun-bisht/northstar with OWNER/REPO in every prompt and change nothing else.
4. Give every task automatic approval (auto mode), so runs never wait for me.
5. Attach my repo to every task with push access, so runs can commit to main.
6. When done, list each task with its schedule, next run time and approval mode.
```

Running it again is safe. It replaces the old tasks instead of adding copies.

## Option B: create the tasks by hand

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines).
2. For each task below, create a task with its name, cron schedule and prompt. Replace `tarun-bisht/northstar` with your fork.
3. Set **Repository** to your fork. No connectors are needed. The **Default** environment is fine.
4. In the task settings, turn on **Automatically approve**.

**Web access.** Scheduled runs never wait for approval when they follow the web-access rule in `prompts/_shared.md`: search first, then fetch only URLs from the search results. Cloud runs need approval to fetch a URL that didn't come from the session itself (one typed from memory or read from a file). `.claude/settings.json` allows WebFetch and WebSearch, but it can't lift that rule.

## Check that it works

1. Open the daily task and click **Run now**.
2. Check that a new commit landed on `main` and the site rebuilt.
3. If the run could not push, check that the task has your repo attached with push access.

## Change the times

All times use `CRON_TZ=Asia/Kolkata`. For your own time zone, change the zone name (for example `CRON_TZ=Europe/London`) and the hour. Keep every task after the 07:17 and 07:53 IST fetches, or move those in `.github/workflows/fetch-candidates.yml` too.

## The tasks

Every prompt has the same shape: get the repo, read the rules and the vision, follow one runbook.

### Daily northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 13 8 * * *`

```
You are running the DAILY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/daily.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message. If the run fails, post one line to the Slack channel in config/notifications.json (prompts/runs/_git.md).
3. Never force-push. Never store private information.
```

### Weekly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 46 6 * * 6` (Saturday)

```
You are running the WEEKLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/weekly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message. If the run fails, post one line to the Slack channel in config/notifications.json (prompts/runs/_git.md).
3. Never force-push. Never store private information.
```

### Monthly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 15 6 1 * *`

```
You are running the MONTHLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/monthly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message. If the run fails, post one line to the Slack channel in config/notifications.json (prompts/runs/_git.md).
3. Never force-push. Never store private information.
```

### Quarterly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 41 6 1 1,4,7,10 *`

```
You are running the QUARTERLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/quarterly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message. If the run fails, post one line to the Slack channel in config/notifications.json (prompts/runs/_git.md).
3. Never force-push. Never store private information.
```
