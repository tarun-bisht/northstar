# Daily Discovery

Read `prompts/_shared.md` first. Roughly 3–6 worthwhile things to listen to, watch, read or try.

## Required every day (validation enforces this)

- **At least one podcast episode in the established tier** (link to the episode page, not the show).
- **At least one video, lecture or documentary** (YouTube IDs confirmed via oEmbed or the API; use the watch URL).
- **At least one item in each tier:** established, growth, exploration.

## Steps

1. `python scripts/dsys.py context discovery --date <today>`: `recent_items` (never repeat a title or URL), `preferences` (explicit signals win; never pick anything in `avoid`; `ignored_hint` means change format or timing, not dislike), `interests_hint` (the tiers) and `variety`.
2. Pick by tier:
   - **established:** AI research and its foundations; go beyond the basics.
   - **growth:** maths, physics, neuroscience, consciousness and philosophy of science that can feed research ideas; people skills, history, art and culture.
   - **exploration:** something genuinely unfamiliar and excellent, e.g. a place in `world.regions`, a subject or craft in `exploration`.
3. Most days, make one item **cross-domain** (`cross_domain: {fields, connection}`), e.g. AI and cognitive science, physics and philosophy, cinema and human behaviour.
4. Culture is chosen for quality, beauty, historical significance or emotional depth (`interests.json → culture_guidance`), not popularity.
5. Fill the fields in `schemas/recommendation.schema.json`, including `tier` and `type` (`podcast`, `video`, `lecture`, `documentary`, `article`, `book`, …). Verify every URL.
6. Merge with `python scripts/dsys.py daily merge discovery --date <today> --items /tmp/disc.json`, then `history rebuild` and `validate`.
