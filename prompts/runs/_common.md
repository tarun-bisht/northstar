# Every scheduled run

The task prompt has already cloned the repo to `~/northstar` and installed the requirements. Work there.

## Start

Read `CLAUDE.md` and `prompts/_shared.md`. Run `python scripts/dsys.py usage start --run <daily|weekly|monthly|quarterly>` (times the run and counts what it reads). Then follow your runbook from its first step to its last, skipping none.

## Finish: validate, commit, push

```bash
python scripts/dsys.py usage end            # stamps the end; keep its numbers for the final message
python scripts/dsys.py history rebuild && python scripts/validate.py
git add -A content state feedback inbox config
git commit -m "<stream>: <date> (<n> items)"
git push origin main || (git pull --rebase origin main && git push origin main)
```

- If validation keeps failing, fix the content. If you can't, remove only the offending items, note it in `notes`, and commit what is valid.
- If pushing is refused for missing permissions, stop and report it in the final message. Don't try other routes.
- Never commit secrets. The only one, the YouTube key, lives in GitHub Actions secrets.

## Questions to the user

Only when a choice truly needs the user (the answer changes what gets made, and no file says it), and at most one a week: post one short question in **#northstar-ask** (`slack.ask.id`), the question in bold with two to four numbered options plus "Other". Record it with `python scripts/dsys.py polls open --kind question --period q-<today>-<n> --ts <ts> --options /tmp/options.json`, then go on with the most reasonable choice. The daily run reads the answer later.

## When something fails

Don't post about it. The daily Slack message names missing parts. Put what went wrong in the final message.
