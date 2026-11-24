# Scheduled tasks setup

Northstar runs on five Claude scheduled tasks. Each task starts a fresh Claude session that clones this repo and follows one runbook in `prompts/runs/`. The task prompts are deliberately short: all the logic lives in the repo (`CLAUDE.md`, `docs/vision.md`, `prompts/`). To change what a run does, edit the repo, not the task.

| Task | When (IST) | Runbook | What it makes |
|---|---|---|---|
| Daily northstar schedule | Every day, 07:19 | `prompts/runs/daily.md` | Research (papers, updates, reading list), News, Exploration (discoveries, language pack) |
| Shorts northstar schedule | Every day, 08:15 | `prompts/runs/shorts.md` | YouTube shorts for the Exploration page |
| Weekly northstar schedule | Saturday, 06:46 | `prompts/runs/weekly.md` | Next week's Research, Knowledge and Exploration, plus the reading list |
| Monthly northstar schedule | 1st of the month, 06:15 | `prompts/runs/monthly.md` | One deep dive per part, plus language plans |
| Quarterly northstar schedule | 1 Jan, Apr, Jul, Oct, 06:41 | `prompts/runs/quarterly.md` | A short public review per part, with numbers |

Every task runs after the 06:00 IST candidate fetch on GitHub Actions and its 06:50 gap-filling run.

## Before you start

1. Fork this repo and turn on GitHub Actions and Pages (README, "Make it yours").
2. Edit `config/` for your interests, sources and languages.
3. Have a Claude account with scheduled tasks and Claude Code on the web.

## Option A: let Claude set it up (recommended)

Start a Claude session, replace `OWNER/REPO` with your fork, and paste:

```
Set up the Northstar scheduled tasks for my GitHub repo https://github.com/OWNER/REPO.

1. Read docs/scheduled_tasks_setup.md in that repo.
2. Delete any existing scheduled tasks with the same five names.
3. Create the five tasks under "The five tasks" in that file. Use each name, cron schedule and prompt exactly as written. If my repo is not tarun-bisht/northstar, replace tarun-bisht/northstar with OWNER/REPO in every prompt and change nothing else.
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

Web access is pre-approved in `.claude/settings.json` (WebFetch and WebSearch). Runs check many links, and without it they can pause to ask before each new site. Keep the file in your fork.

## Check that it works

1. Open the daily task and click **Run now**.
2. Check that a new commit landed on `main` and the site rebuilt.
3. If the run could not push, check that the task has your repo attached with push access.

## Change the times

All times use `CRON_TZ=Asia/Kolkata`. For your own time zone, change the zone name (for example `CRON_TZ=Europe/London`) and the hour. Keep every task after the 06:00 and 06:50 IST fetches, or move those in `.github/workflows/fetch-candidates.yml` too.

## The five tasks

Every prompt has the same shape: get the repo, read the rules and the vision, follow one runbook.

### Daily northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 19 7 * * *`

```
You are running the DAILY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/daily.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message.
3. Never force-push. Never store private information.
```

### Shorts northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 15 8 * * *`

```
You are running the SHORTS run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/shorts.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message.
3. Never force-push. Never store private information.
```

### Weekly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 46 6 * * 6` (Saturday)

```
You are running the WEEKLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/weekly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message.
3. Never force-push. Never store private information.
```

### Monthly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 15 6 1 * *`

```
You are running the MONTHLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/monthly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message.
3. Never force-push. Never store private information.
```

### Quarterly northstar schedule

Cron: `CRON_TZ=Asia/Kolkata 41 6 1 1,4,7,10 *`

```
You are running the QUARTERLY run of Northstar, a personal discovery system, in the GitHub repo tarun-bisht/northstar.

1. Clone or update the repo (git clone https://github.com/tarun-bisht/northstar.git ~/northstar; then cd ~/northstar && git checkout main && git pull --rebase origin main) and install requirements (pip install -r requirements.txt, adding --break-system-packages if needed).
2. Read CLAUDE.md and docs/vision.md, then follow prompts/runs/quarterly.md exactly. It says what to make, how to validate, how to commit and push to main, and what to put in your final message.
3. Never force-push. Never store private information.
```
