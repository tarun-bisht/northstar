# Setup prompt for the scheduled tasks

This is the exact prompt used to create the five Northstar scheduled tasks. Start a Claude session and paste it as is.

```
Create the five scheduled tasks in docs/scheduled_tasks.md exactly as written, with automatic approval. Delete any older scheduled tasks with the same names first. https://github.com/tarun-bisht/northstar.git. Keep each schedule task in auto mode and add this repo also in each task.
```

What it does:

1. Reads `docs/scheduled_tasks.md` from the repo.
2. Deletes any existing scheduled tasks with the same five names.
3. Creates the Daily, Shorts, Weekly, Monthly and Quarterly tasks with the prompts and cron times from that file.
4. Sets every task to automatic approval, so runs do not wait for you.
5. Attaches this repo to the task environment with push access. Each prompt also clones the repo as its first step.

Fork owners: replace `tarun-bisht/northstar` with your own repo.
