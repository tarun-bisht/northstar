# YouTube Shorts run (every day, 08:41 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. `python scripts/dsys.py period` gives `<today>`. Then `python scripts/dsys.py candidates ensure --kinds youtube` and wait for it (it starts the fetch if GitHub's schedule is late and waits until it has finished). If it reports `ok: false`, make no shorts today: post the failure to Slack (`prompts/runs/_git.md`). Never search for videos instead.
2. Follow `prompts/youtube_shorts.md`.
3. `python scripts/dsys.py history rebuild && python scripts/validate.py`, then commit `youtube_shorts: <today> (<n> videos)` and push.
4. Final message: number of videos, the language split, the tier split, and the language-learning shorts added.
