# How Northstar works

`docs/vision.md` says **why** Northstar exists: to find, filter, connect and recommend things genuinely worth your attention, as a compass, not a tracker. This file says **how** every part of the system serves that vision. It is the single map of the system. If you change how something works, update this file.

## 1. The rhythm

| Layer | Purpose (vision §15) | When (IST) | Made by |
|---|---|---|---|
| Daily | stay aware | papers on weekdays, everything else every day | Daily run 08:13, Shorts run 08:41 |
| Weekly | explore | Saturday 06:46, for the week starting Monday | Weekly run |
| Monthly | go deep | 1st of the month, 06:15 | Monthly run |
| Quarterly | look back | 1 Jan, Apr, Jul, Oct, 06:41 | Quarterly run |

Before the runs, GitHub Actions fetches candidates at 07:17 and refills any gaps at 07:53 (section 4). GitHub can start these hours late, so the daily and shorts runs start the fetch themselves if today's files are missing. No AI runs in that step.

## 2. Parts, each with its own URL

Every page is split into parts, so research, news and exploration never pile up in one place.

| Layer | Parts | Pages |
|---|---|---|
| Daily (be aware) | **Research**: arXiv radar, research updates. **News**: world radar by category. **Exploration**: at least one podcast and one video (they play on the page), the rest free (entertainment, free-time interests, reads), 30 to 40 shorts. **Languages**: the 5-minute pack | `daily/<date>/research.html`, `news.html`, `exploration.html`, `languages.html`, plus `index.html` |
| Weekly (explore) | Touches all six pillars of development every week (vision §4). **Papers of the week**: for you (from the daily papers), trending, and leading groups. **Research**: Fundamentals and New in AI. **Knowledge**: topics grouped by subject, maths and physics always plus 5 to 6 rotating subjects, each with a study plan and resources, and approachable maths and physics questions. **Exploration** (the largest part): curiosities, culture, people and self, curiosity and making. **Languages**: a lesson per language | `weekly/<week>/papers.html`, `research.html`, `knowledge.html`, `exploration.html`, `languages.html`, plus `index.html` |
| Monthly (go deep) | **Research**: a New in AI deep dive and a Fundamentals deep dive. **Knowledge**: a deep dive outside AI, and hard challenge problems (olympiad, entrance exam, university level) in maths, physics and 4 to 6 other subjects. **Exploration**: a deep dive that rotates through people and self, culture and life, and curiosity and making. **Languages**: a plan per language | `monthly/<month>/<part>.html`, plus `index.html` |
| Quarterly | A short summary and the topics covered, per part, plus the numbers | `quarterly/<YYYY-Qn>/<part>.html`, plus `index.html` |

The part maps live in one place, `dsys/render.py` (`DAILY_PARTS`, `WEEKLY_PARTS`, `MONTHLY_PARTS`, `QUARTERLY_PARTS`, `WEEKLY_SECTIONS`, `MONTHLY_SECTIONS`, `SUBJECTS`, `WORLD_SECTIONS`, `DISCOVERY_SECTIONS`). The site, the feeds, validation and the quarterly review all read them.

Links that leave the site open in a new tab (`target="_blank"`), in the feeds too. YouTube videos, Spotify and Apple Podcasts episodes, and podcast audio files (`audio_url`) play on the page behind a "Play here" fold, so nothing loads until you open it.

## 3. RSS feeds

One feed per part, so each can be followed on its own:

| Feed | One item per |
|---|---|
| `research.xml`, `news.xml`, `exploration.xml`, `languages.xml` | day |
| `reading.xml` (papers of the week) | paper: *For you*, *Trending this week*, *From leading groups* |
| `weekly-research.xml`, `weekly-knowledge.xml`, `weekly-exploration.xml`, `weekly-languages.xml` | week |
| `monthly-research.xml`, `monthly-knowledge.xml`, `monthly-exploration.xml`, `monthly-languages.xml` | month |
| `quarterly-research.xml`, `quarterly-knowledge.xml`, `quarterly-exploration.xml` | quarter, with the numbers |

The feed list lives in `dsys/core.py` (`FEEDS`), and each feed's size in `config/recommendation_policy.json → feeds`. Feed HTML is plain and semantic: folded sections are opened, and tags are separated, so it reads well in readers that drop CSS.

## 4. Sources and robustness

| Source | What | File |
|---|---|---|
| arXiv API, one call per category (rss.arxiv.org fallback) | new papers, with comments (venue, code) | `candidates/arxiv/<date>.json` |
| Hugging Face Daily Papers | community upvotes | same file (`hf_upvotes`) |
| alphaXiv: Hot, Likes, Comments and GitHub lists, plus one search per interest | papers becoming widely discussed, papers alphaXiv's search ties to each interest (`alphaxiv_votes`, `alphaxiv_lists`, `alphaxiv_interests`, `interest_search`) | same file |
| about 30 publisher RSS feeds (BBC, The Hindu, Indian Express, Mint, The Economic Times, CNBC, The Guardian, Al Jazeera, NPR, The Conversation in five editions, RBI and more) plus Google News (top stories by section, and searches such as Nvidia, AI, chips, ISRO, SpaceX) | headlines with summaries | `candidates/news/<date>.json` |
| YouTube Data API (needs the `YOUTUBE_API_KEY` secret) | short videos, a rotating slice of the queries each day | `candidates/youtube/<date>.json` |
| YouTube Data API, long form | lectures, talks and documentaries over 10 minutes | `candidates/videos/<date>.json` |
| podcast show feeds (found by name with the iTunes Search API) and iTunes episode search | recent episodes with their audio files, so they play on the page | `candidates/podcasts/<date>.json` |
| lab and researcher blogs, newsletters (Interconnects, Ahead of AI, Import AI, Lil'Log), Quanta, Alignment Forum, Hacker News (Algolia API), r/MachineLearning | research updates and discussion | `candidates/updates/<date>.json` |
| Hugging Face API | trending models, datasets and spaces | `candidates/hf/<date>.json` |

Google News also runs searches built from your interests (AI security, quantum computing, neuroscience, physics, mathematics, archaeology, Japan and anime, art, prizes, robotics), marked `interest: true`. X and LinkedIn have no open feed (alphaXiv's X list is rejected by its API), so their discussion reaches the radar through Hacker News, newsletters and web search, never invented.

Every request goes through `dsys/net.py`, which retries timeouts, HTTP 429 and 5xx with growing pauses and honours `Retry-After`. A source that still fails is listed in the day's `failed_sources`. It is retried two minutes later in the same job, and again by the 07:53 gap-filling run (`fetch_candidates.py <kind> --retry-failed`). A re-run only adds candidates, never removes them.

**Runs never fall back to web search for candidates.** GitHub can start scheduled workflows hours late, so the daily and shorts runs begin with `dsys.py candidates ensure` (`dsys/ensure.py`). It checks today's files. If a fetch is already queued or running, it waits for it to finish. Otherwise it starts the workflow itself (workflow_dispatch) for the missing kinds, or in retry mode for failed sources, and waits for that run to finish. It repeats this for up to four rounds and 90 minutes. A missing file is never accepted: the run skips that stream and posts the failure to Slack. A source that keeps failing inside a file that exists is listed, and the rest of the file is used.

arXiv allows one request every three seconds on a single connection. The fetcher spaces its calls to match.

**Web access in runs.** Cloud runs fetch a page without asking only when its URL came from the session (a web search result or a page already fetched). So runs search first and then fetch, and never fetch URLs straight from candidate files, which Actions already checked (`prompts/_shared.md`). This keeps scheduled runs from stalling on approval.

## 5. Choosing papers (quality from abstracts)

Reading thousands of abstracts, or any PDFs, is not possible in a run. So:

1. **Coverage.** Every research interest in `config/interests.json → established.ai_research` has an entry in `config/sources.json → arxiv.coverage`: its arXiv categories and specific keywords. Validation warns when an interest has no entry. The fetched categories are the union, so every interest is gathered.
2. **Ranking in code** (`dsys/rank.py`). Each candidate gets a relevance score from the coverage keywords (the title counts double, and a keyword only counts when the paper is in that topic's categories) plus quality signals: Hugging Face upvotes, alphaXiv votes, discussed on X, an alphaXiv search match, a notable researcher (`notable_researchers`), released code, a named venue in the arXiv comment.
3. **Shortlist.** The best 3 papers for every interest, filled up to about 80 by score, plus every trending or notable paper (`candidates arxiv --ranked`).
4. **Judgement from the abstract.** The run reads those abstracts (`candidates arxiv --ids …`) and rates each against the rubric in `prompts/arxiv.md`: a clear contribution, strong evidence, concrete results and outside signals keep a paper; vague claims, thin evaluation and recombined tricks drop it. Trending papers that pass the bar and touch any interest are kept even when keywords missed them.
5. **Papers of the week** (`reading.xml`, `weekly/<week>/papers.html`). Three groups: *For you*, the must-reads for your work from the week's radar; *Trending this week*, the week's most voted papers on alphaXiv and Hugging Face (`candidates arxiv --trending-week`); and *From leading groups*, strong work from top labs related to AI or your research. Daily runs add to it, and the weekly run sets it up. It is a weekly part, not shown in daily.

## 6. Choosing news

Every headline is categorized in code (`dsys/news.py`, keywords in `config/sources.json → world.categories`) into 12 categories: India, geopolitics, leadership changes, conflicts and disasters, economy and markets, business, technology and AI, science and space, health, climate and energy, society, and explainers. Sport, celebrity and local notices go to "other". Headlines about the same event are merged, with the other outlets in `also_in`. The run reads every category and writes two layers (`prompts/world.md`):

- **Explained items:** 12 to 20 stories worth understanding, across at least 7 categories, each with what happened, why it matters, context and what to watch.
- **Briefs:** 15 to 30 one-line headlines linking straight to the article, so other notable stories are not missed.

Markets, technology and explainers appear every day, with at least one explainer from The Conversation when its feeds have something relevant.

## 7. Slack: the one notification channel

Mobile and email notifications are off for every task. Three scheduled tasks use the Slack connector, in the channel set in `config/notifications.json`:

- **Daily digest** (09:43 IST, `prompts/runs/slack_digest.md`): one short message with links to today's pages and one line per problem. Problems come from `dsys.py status` (missing streams, failed sources, validation errors, a missing weekly or monthly package), failed GitHub Actions runs, and failed scheduled runs.
- **Topic polls** (Thursdays and the 25th, 20:07 IST, `prompts/runs/topic_poll.md`): four options for next week's New in AI topic, and four research plus four fundamentals options for next month. Reply in the thread with numbers or your own topic. No reply is fine.
- **Poll collect** (Saturdays and the 1st, 05:53 IST, `prompts/runs/poll_collect.md`): saves the answers to `state/polls.json` (`dsys.py polls`). The weekly and monthly runs read them as `poll_choices` in `context`.

## 8. What is never done (vision §2 and §17)

No streaks, scores, completion tracking, backlogs or guilt. Items carry a status only as an internal detail of the feedback step. Feedback is optional and natural ("more like this", "too basic"). Nothing is carried forward unless you ask. The repo is public, so nothing private is stored (CLAUDE.md rule 5).

## 9. Where things live

| Path | What |
|---|---|
| `docs/vision.md` | why Northstar exists. Read first |
| `docs/how_it_works.md` | this map |
| `docs/scheduled_tasks_setup.md` | the eight scheduled tasks and how to create them |
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

## 10. Changing things

- **Interests:** edit `config/interests.json`, or tell Claude (`prompts/update_interests.md`). A new research interest also needs an `arxiv.coverage` entry.
- **News feeds or categories:** `config/sources.json → world.feeds` and `world.categories`.
- **Notable researchers:** `config/sources.json → notable_researchers`.
- **Sizes and required sections:** `config/preferences.json` and `WEEKLY_REQUIRED` in `dsys/validate.py`.
- **Times:** the cron lines in the scheduled tasks and in `.github/workflows/fetch-candidates.yml`. Keep the runs after the 07:17 and 07:53 fetches.

Finish every change with `python scripts/validate.py && python -m pytest -q`.
