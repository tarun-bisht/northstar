# Git procedure for scheduled runs

```bash
# 1. Get the repo (fresh session each run)
git clone https://github.com/tarun-bisht/northstar.git ~/northstar 2>/dev/null || true
cd ~/northstar
git checkout main && git pull --rebase origin main
pip install -q -r requirements.txt  # add --break-system-packages if pip refuses

# 2. ... do the work described in the runbook ...

# 3. Validate. Never commit invalid content.
python scripts/dsys.py history rebuild
python scripts/validate.py

# 4. Commit and push (retry once on a race with the candidates workflow)
git add -A content state feedback inbox config
git commit -m "<stream>: <date> (<n> items)"
git push origin main || (git pull --rebase origin main && git push origin main)
```

- Only commit to `main`; never force-push.
- If validation keeps failing, fix the content. If you can't, remove only the offending items, note it in `notes`, and commit what is valid.
- If pushing is refused because of missing permissions, stop and report it in the run summary. Don't try other routes.
- Never commit secrets. There are none in this repo; the YouTube key lives only in GitHub Actions secrets.

## Questions to the user

If a choice truly needs the user (the answer changes what gets made, and no file says it), post one short question in **#northstar-ask** (`config/notifications.json → slack.ask.id`), formatted with the question in bold and two to four numbered options plus "Other". Record it: `python scripts/dsys.py polls open --kind question --period q-<today>-<n> --ts <ts> --options /tmp/options.json`. Then go on with the most reasonable choice; the daily run reads the answer later. Rarely: at most one question a week.

## If the run fails

If a part couldn't be made, don't post about it: the Slack digest reports missing parts in its daily message. Put what went wrong in the final message.
