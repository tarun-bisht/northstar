# YouTube Shorts run (every day, 08:15 IST)

Follow `prompts/runs/_git.md` for setup, validation and commit. Then:

1. `python scripts/dsys.py period` gives `<today>`.
2. Follow `prompts/youtube_shorts.md`.
3. `python scripts/dsys.py history rebuild && python scripts/validate.py`, then commit `youtube_shorts: <today> (<n> videos)` and push.
4. Final message: number of videos, the mode used (Data API candidates or oEmbed fallback), and the dimension spread in one line.
