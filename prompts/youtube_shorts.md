# YouTube Shorts Radar (daily, high volume)

Read `prompts/_shared.md` first.

**Purpose:** a scrollable feed of short videos (**30 to 40 a day**, `preferences.daily.youtube_shorts_target`) covering all dimensions: informative, entertaining, insightful, creative, fascinating. Better 30 great ones than 40 with filler. They play on the page.

## Legitimate access only

- **Preferred:** candidates fetched by GitHub Actions via the YouTube Data API v3 (`candidates/youtube/<date>.json`, needs the `YOUTUBE_API_KEY` repository secret). These have real IDs, titles, channels, durations and dates.
- **No fallback.** Videos come only from the candidates file. If it is missing or empty after `candidates ensure` (empty means no `YOUTUBE_API_KEY`), make no shorts today and report it.
- Never scrape YouTube HTML, and never construct or guess video ids.

## Steps

1. `python scripts/dsys.py context youtube_shorts --date <today>` shows candidate availability, creators used in the last 7 days, and the per-creator soft limit.
2. If candidates are available: `python scripts/dsys.py candidates youtube --date <today>`. They are already narrowed in code: unseen IDs only, near-duplicate titles removed, nothing made for kids, at most 3 per creator, within the accepted languages, `format` classified, then the best 250 by engagement taken in turn from each interest's search (`prefiltered` says how many of how many). Read them all. Each shows the first 300 characters of its description; build `url`, `embed_url` and `thumbnail` from `video_id` as in step 8.
3. **Languages:** English only (`config/sources.json → youtube.languages_accepted`). No Hindi shorts. Don't add filler to reach a number. Set `language` to the language the video is spoken in.
   **Languages I am learning** (Japanese, Telugu, see `config/languages.json`): I am a beginner, so never add native videos in these languages. Add a few beginner lesson shorts taught in English instead (useful phrases, pronunciation, simple conversation). Tag them `tier: growth`, `category: "language learning"`, and say which language in `topic`. Native videos come only after that language has `native_content_ok: true`.
4. Select **from data, never by watching**: each candidate has `views`, `likes`, `comments`, the start of its description, duration and channel. Prefer strong engagement (likes and comments relative to views) and descriptions that show substance, matched to the interests. Reject:
   - clickbait or misleading titles, engagement bait ("wait for it", "you won't believe")
   - reposted or copied clips (channel isn't the creator), compilations of others' work
   - low-quality AI-generated voiceover slideshows, pseudo-science, rage content, get-rich-quick or hustle content
   - near-duplicates of each other or of history
   - more than ~3 videos per creator per day (the soft limit; spread creators across days)
5. **Tiers (validation enforces this):** tag every video `tier` = established (AI, research, maths/physics for research), growth (maths, physics, neuroscience, consciousness, philosophy, people skills, history, art) or exploration (places, cultures, crafts, unusual science). Include **at least one per tier**, with most in established, a steady share of growth, and some exploration.
6. Aim for breadth across dimensions and topics (science, math, AI, history, philosophy, psychology, communication and EQ, books, cinema and anime, music, art, architecture, photography, DIY, electronics, game dev, inventions, places, people, experiments). Within a topic, prefer creators known for accuracy. Don't let any one topic dominate.
7. **Shorts vs other short videos.** Never assert that a video is a Short from its duration. Use the candidate's `format` and `format_evidence` as given: `short` only when `format_evidence` is `shorts_url_check`; otherwise `short_form` (known not to be a Short) or `unknown`.
8. Item fields (`schemas/youtube_shorts.schema.json`): `id` = `yt-<video_id>`; `url` = `https://www.youtube.com/shorts/<id>` **only** if `format` is `short`, otherwise `https://www.youtube.com/watch?v=<id>`; `embed_url` = `https://www.youtube.com/embed/<id>`; `thumbnail` = `https://i.ytimg.com/vi/<id>/hqdefault.jpg`; `channel.name` (and `channel.id` from the API); `duration_seconds` and `published` only from the API; `topic`, `category`, `tier`, `dimensions`, `language`; `why_it_matches` (one line, concrete); `discovery_source`; `format`, `format_evidence`; `verification.method` (`youtube_data_api` or `oembed`) and `verification.verified_at`.
9. Write `/tmp/yt.json` with `candidates_considered`, merge with `python scripts/dsys.py daily merge youtube_shorts --date <today> --items /tmp/yt.json`, then `history rebuild` and `validate`. Validation rejects malformed IDs, mismatched URLs, "short" claims without evidence and repeated videos. It warns about creator over-representation and near-duplicate titles.
