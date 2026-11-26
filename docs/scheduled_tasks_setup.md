# Set up your own Northstar

This copies the full setup: GitHub Actions to fetch and publish, four Claude scheduled tasks to curate, and Slack to notify. It takes about 30 minutes. Times are IST (`Asia/Kolkata`). To use another zone, see step 7.

The daily task runs after the 07:17 fetch. Weekly and monthly run before it, and the daily task announces them. The full schedule is in `docs/how_it_works.md` §1, and what each task posts in Slack is in §7.

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

The prompts only get the repo and name a runbook. Everything else, including the safety rules and every Slack step, lives in the repo (`prompts/runs/_common.md` and the runbook), so it is written once. To change what a run does, edit the repo, not the task.

### Daily northstar schedule

Cron `CRON_TZ=Asia/Kolkata 13 8 * * *` · Model `claude-sonnet-5-5`

```
You are running the DAILY run of Northstar in the GitHub repo tarun-bisht/northstar.

1. Get the repo: git clone https://github.com/tarun-bisht/northstar.git ~/northstar (if it exists: cd ~/northstar && git checkout main && git pull --rebase origin main). Then pip install -r requirements.txt (add --break-system-packages if pip refuses).
2. Follow prompts/runs/daily.md from its first step to its last, skipping none. Its last steps post the polls and messages to Slack.
```

### Weekly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 46 6 * * 6` (Saturday) · Model `claude-opus-5-5`

```
You are running the WEEKLY run of Northstar in the GitHub repo tarun-bisht/northstar.

1. Get the repo: git clone https://github.com/tarun-bisht/northstar.git ~/northstar (if it exists: cd ~/northstar && git checkout main && git pull --rebase origin main). Then pip install -r requirements.txt (add --break-system-packages if pip refuses).
2. Follow prompts/runs/weekly.md from its first step to its last, skipping none. Before planning, it reads the poll answers in Slack.
```

### Monthly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 15 6 1 * *` · Model `claude-opus-5-5`

```
You are running the MONTHLY run of Northstar in the GitHub repo tarun-bisht/northstar.

1. Get the repo: git clone https://github.com/tarun-bisht/northstar.git ~/northstar (if it exists: cd ~/northstar && git checkout main && git pull --rebase origin main). Then pip install -r requirements.txt (add --break-system-packages if pip refuses).
2. Follow prompts/runs/monthly.md from its first step to its last, skipping none. Before planning, it reads the poll answers in Slack.
```

### Quarterly northstar schedule

Cron `CRON_TZ=Asia/Kolkata 41 6 1 1,4,7,10 *` · Model `claude-sonnet-5-5`

```
You are running the QUARTERLY run of Northstar in the GitHub repo tarun-bisht/northstar.

1. Get the repo: git clone https://github.com/tarun-bisht/northstar.git ~/northstar (if it exists: cd ~/northstar && git checkout main && git pull --rebase origin main). Then pip install -r requirements.txt (add --break-system-packages if pip refuses).
2. Follow prompts/runs/quarterly.md from its first step to its last, skipping none.
```
