# Shorts (a helper inside the daily run)

The daily run (`prompts/runs/daily.md`) starts this as a Sonnet helper after it has fetched today's files. Then:

1. `python scripts/dsys.py period` gives `<today>`. The daily run has already waited for the shorts file (`candidates ensure`). If it is missing, make no shorts today. Never search for videos instead.
2. Follow `prompts/youtube_shorts.md`.
3. Merge with `python scripts/dsys.py daily merge youtube_shorts --date <today> --items <file>`, then `python scripts/dsys.py history rebuild && python scripts/validate.py`. Don't commit: the daily run commits everything together.
4. Final message: number of videos, the language split, the tier split, and the language-learning shorts added.
