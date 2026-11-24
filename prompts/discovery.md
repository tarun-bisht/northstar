# Daily Discovery

Read `docs/vision.md` and `prompts/_shared.md` first. **5 to 8** worthwhile things to listen to, watch, read or try (`preferences.daily.discovery_target`). Fewer excellent things beat many mediocre ones.

The daily Exploration page (`daily/<date>/exploration.html`) shows discoveries in sections by `type`: **Podcasts** (podcast), **Videos and lectures** (video, lecture, documentary, playlist, course), **Reads** (article, paper, book, website), **Watch and listen** (film, series, anime, album, music, artwork) and **Try, make or go** (place, experience, project, tool, idea, person). Shorts and the language pack sit below them.

## Aim for every day

- 1 to 2 podcast episodes
- 1 to 2 videos or lectures (a YouTube video, a lecture, a documentary)
- 1 to 2 reads (an essay, article or book chapter)
- 1 thing to watch, listen to or try when it's genuinely good: a song or album, an artwork, a film, a place, a hobby
- across knowledge, culture, people and curiosity, not only AI
- **Languages:** recommend only content in languages the user understands (English, Hindi). For languages they are learning (`config/languages.json`), only beginner material explained in English or Hindi, unless that language has `native_content_ok: true`.

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
