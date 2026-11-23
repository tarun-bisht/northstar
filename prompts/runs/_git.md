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
