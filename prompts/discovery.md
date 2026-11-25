# Daily Discovery

Read `docs/vision.md` and `prompts/_shared.md` first. Worthwhile things to listen to, watch, read or try. There is no fixed number: fewer excellent things beat many mediocre ones (at most 14).

The daily Exploration page (`daily/<date>/exploration.html`) shows discoveries in sections by `type`: **Podcasts** (podcast), **Videos and lectures** (video, lecture, documentary, playlist, course), **Reads** (article, paper, book, website), **Watch and listen** (film, series, anime, album, music, artwork) and **Try, make or go** (place, experience, project, tool, idea, person). Shorts sit below them. The language pack has its own page (`daily/<date>/languages.html`).

## Every day

- **At least one podcast episode** (link to the episode page, not the show). Add `audio_url` (the episode's audio file, from the show's RSS feed or `candidates/podcasts` when present) so it plays on the page. Spotify and Apple Podcasts episode links also play on the page.
- **At least one video, lecture or documentary** (YouTube IDs confirmed via oEmbed or the API; use the watch URL, it plays on the page).
- **The rest is free and random**: entertainment, things to enjoy in free time (films, anime, music, games, sport stories, cooking, travel), interests from `config/interests.json`, and reads (an essay, article or book chapter). Mix knowledge, culture, people and curiosity, not only AI.
- **At least one item in each tier:** established, growth, exploration (validation enforces the podcast, the video and the tiers).
- **Languages:** recommend only content in languages the user understands (English, Hindi). For languages they are learning (`config/languages.json`), only beginner material explained in English or Hindi, unless that language has `native_content_ok: true`.
- **No broken links:** only URLs found in a search result or fetched in this run.

## Steps

1. `python scripts/dsys.py context discovery --date <today>`: `recent_items` (never repeat a title or URL), `preferences` (explicit signals win; never pick anything in `avoid`; `ignored_hint` means change format or timing, not dislike), `interests_hint` (the tiers) and `variety`.
2. Podcasts and videos come only from the fetched candidates, never from search (the daily run has already waited for them):
   - `python scripts/dsys.py candidates podcasts --date <today>`: recent episodes of good shows (AI, science, philosophy, history, culture) and episode searches on the user's interests, each with `audio_url` so it plays on the page. Copy `url`, `audio_url` and the show name as they are.
   - `python scripts/dsys.py candidates videos --date <today>`: long-form lectures, talks and documentaries with durations.
   - Films, books, music and places have no fetched source yet, so only for these use web search, and only URLs you saw in a search result or fetched page.
3. Pick by tier:
   - **established:** AI research and its foundations; go beyond the basics.
   - **growth:** maths, physics, neuroscience, consciousness and philosophy of science that can feed research ideas; people skills, history, art and culture.
   - **exploration:** something genuinely unfamiliar and excellent, e.g. a place in `world.regions`, a subject or craft in `exploration`.
4. Most days, make one item **cross-domain** (`cross_domain: {fields, connection}`), e.g. AI and cognitive science, physics and philosophy, cinema and human behaviour.
5. Culture is chosen for quality, beauty, historical significance or emotional depth (`interests.json → culture_guidance`), not popularity.
6. Fill the fields in `schemas/recommendation.schema.json`, including `tier` and `type` (`podcast`, `video`, `lecture`, `documentary`, `article`, `book`, …). Verify every URL.
7. Merge with `python scripts/dsys.py daily merge discovery --date <today> --items /tmp/disc.json`, then `history rebuild` and `validate`.
