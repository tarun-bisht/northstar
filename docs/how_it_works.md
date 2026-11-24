# How Northstar works

`docs/vision.md` says **why** Northstar exists: to find, filter, connect and recommend things genuinely worth your attention, as a compass, not a tracker. This file says **how** every part of the system serves that vision. It is the single map of the system. If you change how something works, update this file.

## 1. The rhythm

| Layer | Purpose (vision §15) | When (IST) | Made by |
|---|---|---|---|
| Daily | stay aware | papers on weekdays, everything else every day | Daily run 07:19, Shorts run 08:15 |
| Weekly | explore | Saturday 06:46, for the week starting Monday | Weekly run |
| Monthly | go deep | 1st of the month, 06:15 | Monthly run |
| Quarterly | look back | 1 Jan, Apr, Jul, Oct, 06:41 | Quarterly run |

Before the runs, GitHub Actions fetches candidates at 06:00 and refills any gaps at 06:50 (section 4). No AI runs in that step.

## 2. Three parts, each with its own URL

Every page is split into parts, so research, news and exploration never pile up in one place.

| Layer | Parts | Pages |
|---|---|---|
| Daily | **Research**: arXiv radar, research updates, this week's reading list. **News**: world radar by category. **Exploration**: podcasts, videos and lectures, reads, watch and listen, things to try, shorts, language pack | `daily/<date>/research.html`, `news.html`, `exploration.html`, plus `index.html` overview |
| Weekly | **Research**: research practice, research reading. **Knowledge**: questions (maths, physics, science), things to know and talk about, understanding the world. **Exploration**: culture, people and self, curiosity and making, language lessons | `weekly/<week>/research.html`, `knowledge.html`, `exploration.html`, plus `index.html` |
| Monthly | One deep dive per part: **research**, **knowledge**, **exploration** (an artist, a culture, a craft, a personal theme, anything unexpected), plus language plans | `monthly/<month>/<part>.html`, plus `index.html` |
| Quarterly | A short summary and the topics covered, per part, plus the numbers | `quarterly/<YYYY-Qn>/<part>.html`, plus `index.html` |

The part maps live in one place, `dsys/render.py` (`DAILY_PARTS`, `PERIOD_PARTS`, `WEEKLY_SECTIONS`, `MONTHLY_SECTIONS`, `WORLD_SECTIONS`, `DISCOVERY_SECTIONS`). The site, the feeds, validation and the quarterly review all read them.

## 3. RSS feeds

| Feed | One item per |
|---|---|
| `research.xml`, `news.xml`, `exploration.xml` | day, one part each |
| `weekly.xml`, `monthly.xml` | part of each week or month |
| `quarterly.xml` | part of each quarter, plus an overview |
| `arxiv.xml`, `world.xml`, `discovery.xml`, `youtube-shorts.xml`, `language.xml`, `research-updates.xml`, `reading.xml` | single item, for readers who want one stream |

Feed HTML is plain and semantic: folded sections are opened, and tags are separated, so it reads well in readers that drop CSS.

## 4. Sources and robustness

| Source | What | File |
|---|---|---|
| arXiv API, one call per category (rss.arxiv.org fallback) | new papers, with comments (venue, code) | `candidates/arxiv/<date>.json` |
| Hugging Face Daily Papers | community upvotes | same file (`hf_upvotes`) |
| alphaXiv trending | papers becoming widely discussed (`alphaxiv_votes`) | same file |
| about 30 publisher RSS feeds (BBC, The Hindu, Indian Express, Mint, The Economic Times, CNBC, The Guardian, Al Jazeera, NPR, The Conversation in five editions, RBI and more) plus Google News (top stories by section, and searches such as Nvidia, AI, chips, ISRO, SpaceX) | headlines with summaries | `candidates/news/<date>.json` |
| YouTube Data API (needs the `YOUTUBE_API_KEY` secret) | short videos | `candidates/youtube/<date>.json` |

Every request goes through `dsys/net.py`, which retries timeouts, HTTP 429 and 5xx with growing pauses and honours `Retry-After`. A source that still fails is listed in the day's `failed_sources`. It is retried two minutes later in the same job, and again by the 06:50 gap-filling run (`fetch_candidates.py <kind> --retry-failed`). A re-run only adds candidates, never removes them. Runs fall back to web search for anything still missing and say so in `notes`.

arXiv allows one request every three seconds on a single connection. The fetcher spaces its calls to match.

**Web access in runs.** Cloud runs fetch a page without asking only when its URL came from the session (a web search result or a page already fetched). So runs search first and then fetch, and never fetch URLs straight from candidate files, which Actions already checked (`prompts/_shared.md`). This keeps scheduled runs from stalling on approval.

## 5. Choosing papers (quality from abstracts)

Reading thousands of abstracts, or any PDFs, is not possible in a run. So:

1. **Coverage.** Every research interest in `config/interests.json → established.ai_research` has an entry in `config/sources.json → arxiv.coverage`: its arXiv categories and specific keywords. Validation warns when an interest has no entry. The fetched categories are the union, so every interest is gathered.
2. **Ranking in code** (`dsys/rank.py`). Each candidate gets a relevance score from the coverage keywords (the title counts double, and a keyword only counts when the paper is in that topic's categories) plus quality signals: Hugging Face upvotes, alphaXiv votes, a notable researcher (`notable_researchers`), released code, a named venue in the arXiv comment.
3. **Shortlist.** The best 3 papers for every interest, filled up to about 80 by score, plus every trending or notable paper (`candidates arxiv --ranked`).
4. **Judgement from the abstract.** The run reads those abstracts (`candidates arxiv --ids …`) and rates each against the rubric in `prompts/arxiv.md`: a clear contribution, strong evidence, concrete results and outside signals keep a paper; vague claims, thin evaluation and recombined tricks drop it. Trending papers that pass the bar and touch any interest are kept even when keywords missed them.
5. **Reading list.** The best one to three papers each weekday join the week's reading list: must-reads for your work plus important trending papers, new models, lab reports and methods.

## 6. Choosing news

Every headline is categorized in code (`dsys/news.py`, keywords in `config/sources.json → world.categories`) into 11 categories: India, geopolitics, conflicts and disasters, economy and markets, business, technology and AI, science and space, health, climate and energy, society, and explainers. Sport, celebrity and local notices go to "other". Headlines about the same event are merged, with the other outlets in `also_in`. The run reads every category and writes two layers (`prompts/world.md`):

- **Explained items:** 12 to 20 stories worth understanding, across at least 7 categories, each with what happened, why it matters, context and what to watch.
- **Briefs:** 15 to 30 one-line headlines linking straight to the article, so other notable stories are not missed.

Markets, technology and explainers appear every day, with at least one explainer from The Conversation when its feeds have something relevant.

## 7. What is never done (vision §2 and §17)

No streaks, scores, completion tracking, backlogs or guilt. Items carry a status only as an internal detail of the feedback step. Feedback is optional and natural ("more like this", "too basic"). Nothing is carried forward unless you ask. The repo is public, so nothing private is stored (CLAUDE.md rule 5).

## 8. Where things live

| Path | What |
|---|---|
| `docs/vision.md` | why Northstar exists. Read first |
| `docs/how_it_works.md` | this map |
| `docs/scheduled_tasks_setup.md` | the five scheduled tasks and how to create them |
| `CLAUDE.md` | rules every Claude run follows |
| `prompts/runs/*.md` | what each scheduled run does, step by step |
| `prompts/*.md` | how to make each kind of content |
| `config/interests.json` | what you care about, in three tiers |
| `config/sources.json` | where to look: arXiv categories and coverage, ranking, alphaXiv, notable researchers, news feeds and categories, YouTube queries, paper tags |
| `config/languages.json` | languages you're learning |
| `config/preferences.json` | sizes and tone |
| `config/schedules.json` | usual free time (light, normal or free weeks) |
| `config/site.json`, `config/recommendation_policy.json` | site settings, feed windows, recommendation rules |
| `schemas/` | the JSON shape of every content file |
| `dsys/` | the code: fetching (`net`, `arxiv`, `news`, `youtube`), ranking (`rank`), validation, site and RSS (`render`, `site`, `rss`), planning helpers |
| `scripts/` | entry points: `dsys.py` (CLI), `fetch_candidates.py`, `validate.py`, `build.py` |
| `content/` | everything published, by stream and date |
| `candidates/` | raw fetched candidates (14 days kept) |
| `state/` | histories and ideas, so nothing repeats |
| `inbox/` | ideas and feedback you write (public) |

## 9. Changing things

- **Interests:** edit `config/interests.json`, or tell Claude (`prompts/update_interests.md`). A new research interest also needs an `arxiv.coverage` entry.
- **News feeds or categories:** `config/sources.json → world.feeds` and `world.categories`.
- **Notable researchers:** `config/sources.json → notable_researchers`.
- **Sizes and required sections:** `config/preferences.json` and `WEEKLY_REQUIRED` in `dsys/validate.py`.
- **Times:** the cron lines in the scheduled tasks and in `.github/workflows/fetch-candidates.yml`. Keep the runs after the 06:00 and 06:50 fetches.

Finish every change with `python scripts/validate.py && python -m pytest -q`.
