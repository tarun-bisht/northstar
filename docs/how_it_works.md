# How Northstar works

`docs/vision.md` says **why** Northstar exists: to find, filter, connect and recommend things genuinely worth your attention, as a compass, not a tracker. This file says **how** every part of the system serves that vision. It is the single map of the system. If you change how something works, update this file.

## 1. The rhythm

| Layer | Purpose (vision §15) | When (IST) | Made by |
|---|---|---|---|
| Daily | stay aware | every day (papers too: other sources fill days when arXiv is quiet) | Daily run 08:13 (Sonnet coordinating Haiku, Sonnet and Opus helpers), which also posts the topic polls and the Slack messages |
| Weekly | explore | Saturday 06:46, for the week starting Monday | Weekly run |
| Monthly | go deep | 1st of the month, 06:15 | Monthly run |
| Quarterly | look back | 1 Jan, Apr, Jul, Oct, 06:41 | Quarterly run |

Before the runs, GitHub Actions scrapes everything at 07:17 and refetches failed sources at 07:53 (section 4). No AI runs in that step. GitHub can start these hours late, so the daily run starts the fetch itself if today's files are missing, and a late scheduled run that finds today's files exits without fetching again.

**Who does what.** GitHub Actions scrapes. Python cleans, removes duplicates (across sources and against the last 3 days) and compacts. Models follow one rule: **cheap models filter, Sonnet chooses and writes the daily parts, Opus only where precise, critical thinking matters.**

| Work | Model |
|---|---|
| First reading of every paper abstract, the news shortlist | Haiku |
| Daily: final paper choice, papers of the week, research updates, World Radar, discovery recommendations (videos, podcasts, reads), shorts; the quarterly review | Sonnet |
| The daily language pack (must be correct), the weekly and monthly runs (what to read and study, fundamentals, study plans, questions with answers, challenges) | Opus |

The daily run only coordinates: helpers do every large read in a fresh context and merge their part, so nothing big sits in the main run's context and gets paid for again on every step. Code does the copying: `papers pick` builds full paper items (abstract word for word) from the model's short choice list, shorts are narrowed in code (no kids' content, at most 3 per creator, best engagement per interest) before a model reads them, news rows are short refs until a story is chosen, and video and podcast descriptions show their first 300 characters.

Web search is used only where nothing can be scraped: discovery (films, books, reads, places, by theme and some randomness), targeted X and LinkedIn searches for research updates, and study resources in the weekly and monthly plans.

## 2. Parts, each with its own URL

Every page is split into parts, so research, news and exploration never pile up in one place.

| Layer | Parts | Pages |
|---|---|---|
| Daily (be aware) | **Research**: papers, research updates. **News**: world radar by category, each explained story with the idea behind it. **Exploration**: at least one podcast and one video (they play on the page), the rest free (entertainment, free-time interests, reads), each saying what you'll learn. **Shorts**: 30 to 40, on their own page so they don't distract. **Languages**: the 5-minute pack | `daily/<date>/research.html`, `news.html`, `exploration.html`, `shorts.html`, `languages.html`, plus `index.html` |
| Weekly (explore) | Touches all six pillars of development every week (vision §4). **Papers of the week**: for you (from the daily papers), trending, and leading groups. **Research**: Fundamentals and New in AI. **Knowledge**: topics grouped by subject, maths and physics always plus 5 to 6 rotating subjects, each with a study plan and resources, and approachable maths and physics questions. **Exploration** (the largest part): curiosities, culture, people and self, curiosity and making. **Languages**: a lesson per language | `weekly/<week>/papers.html`, `research.html`, `knowledge.html`, `exploration.html`, `languages.html`, plus `index.html` |
| Monthly (go deep) | **Research**: a New in AI deep dive and a Fundamentals deep dive. **Knowledge**: a deep dive outside AI, and hard challenge problems (olympiad, entrance exam, university level) in maths, physics and 4 to 6 other subjects. **Exploration**: a deep dive that rotates through people and self, culture and life, and curiosity and making. **Languages**: a plan per language | `monthly/<month>/<part>.html`, plus `index.html` |
| Quarterly | A short summary and the topics covered, per part, plus the numbers | `quarterly/<YYYY-Qn>/<part>.html`, plus `index.html` |

**Ranking and Overview.** The daily run marks up to five best items per part (`dsys.py daily overview`, field `overview`). Research shows **research updates first, then papers, every item in full and ranked best first**. Its feed has two entries a day, **Research updates** and **Paper Radar** (a minute older, so it lists below), so neither entry is huge (`dsys/overview.py rank`): the marked items, then the other top items, then the rest, each in the order the helper chose. So when time is short, read from the top. Exploration shows its marked items as an Overview section first, left out of the main list. The Slack message's Today's best lists the first three updates and the first three papers.

**Light days.** When `config/schedules.json` makes the week light (`dsys.py period → load_this_week`), the daily run uses the smaller sizes in `config/preferences.json → daily.light`: only the best of each part, with the daily rules still holding. Real life comes first.

The part maps live in one place, `dsys/render.py` (`DAILY_PARTS`, `WEEKLY_PARTS`, `MONTHLY_PARTS`, `QUARTERLY_PARTS`, `WEEKLY_SECTIONS`, `MONTHLY_SECTIONS`, `SUBJECTS`, `WORLD_SECTIONS`, `DISCOVERY_SECTIONS`). The site, the feeds, validation and the quarterly review all read them.

Links that leave the site open in a new tab (`target="_blank"`), in the feeds too. YouTube videos, Spotify and Apple Podcasts episodes, and podcast audio files (`audio_url`) play on the page behind a "Play here" fold, so nothing loads until you open it.

## 3. RSS feeds

One feed per part, so each can be followed on its own:

| Feed | One item per |
|---|---|
| `research.xml`, `news.xml`, `exploration.xml`, `shorts.xml`, `languages.xml` | day |
| `reading.xml` (papers of the week) | paper: *For you*, *Trending this week*, *From leading groups* |
| `weekly-research.xml`, `weekly-knowledge.xml`, `weekly-exploration.xml`, `weekly-languages.xml` | week |
| `monthly-research.xml`, `monthly-knowledge.xml`, `monthly-exploration.xml`, `monthly-languages.xml` | month |
| `quarterly-research.xml`, `quarterly-knowledge.xml`, `quarterly-exploration.xml` | quarter, with the numbers |

The feed list lives in `dsys/core.py` (`FEEDS`), and each feed's size in `config/recommendation_policy.json → feeds`. Every feed entry uses one template (`dsys/feedhtml.py`): a small header, section headings, entry titles, a quiet meta line, the text, then "Why it matters". Inline styles give a system font stack, a type scale and spacing, with no text colours, so light and dark reader themes both work and readers that strip styles still show clean HTML. Feeds are valid RSS 2.0 and render in readers like Inoreader, FeedFlow and NetNewsWire with no JavaScript or stylesheets (`dsys/rss.py`):

- Rich HTML goes in `<content:encoded>` inside CDATA, with a plain-text `<description>` fallback. Folded sections are opened, and `<script>`, `<style>` and stylesheet links are removed.
- **Maths** (`dsys/mathfmt.py`, on the site too): simple subscripts and superscripts (`x_{l+1}`, `a^2`) become `<sub>`/`<sup>`. Fractions, sums, integrals, matrices and Greek letters become native MathML (latex2mathml). This works with `$...$`, `$$...$$`, `\(...\)`, `\[...\]` or no delimiters. `$83` stays money, and snake_case, URLs and code are left alone.
- **Pictures**: every item has a `media:thumbnail`: the first video's picture in Exploration and Shorts, otherwise a cover for its part (`assets/covers/`, made by `scripts/make_covers.py`).
- **WebSub**: every feed declares the hub `https://pubsubhubbub.appspot.com/`, and the publish workflow pings it after each deploy. Readers then get new items within seconds instead of at their next check (Inoreader: about every 8 hours). If your domain sits behind a cache, keep `/northstar/*` uncached or cached for 10 minutes at most, so the hub fetches the new feed.
- **Titles**: in feeds, entry titles are bold links in a paragraph (`<p><strong><a>`), not `<h3>`–`<h5>` headings, which some readers drop. Section headings stay `<h2>`. Readers keep the first copy of an item, so `FEED_REV` in `dsys/rss.py` is added to every item id; bump it only when readers must see a template change for items they already have.
- **Abstracts**: every paper shows its full abstract in the feeds (no toggle: readers handle `<details>` unevenly, and some lost the title above it). On the site it sits behind an "Abstract" show/hide toggle.
- **YouTube**: videos and Shorts (watch, `youtu.be` and `/shorts/` links) play in the item through a responsive `youtube.com/embed` player. It has `allowfullscreen` and `referrerpolicy="strict-origin-when-cross-origin"`, which avoids error 153, and a "Watch on YouTube" link below for videos that can't be embedded.

## 4. Sources and robustness

All of these are fetched by `.github/workflows/fetch-candidates.yml` (`scripts/fetch_candidates.py`, helpers in `dsys/feeds.py`) into `candidates/<kind>/<date>.json`, written compactly.

| Kind | Sources |
|---|---|
| `arxiv` (every day) | arXiv API for every category in `arxiv.categories` (rss.arxiv.org fallback), Hugging Face Daily Papers, alphaXiv lists (Hot, Likes, Comments, GitHub) and one alphaXiv search per interest, and papers discussed on Reddit (ML research subreddits) and Bluesky (posts linking arXiv, alphaXiv or Hugging Face papers), fetched from the arXiv API when new. Authors, affiliations (arXiv), organizations (Hugging Face, alphaXiv), signals and the trust flag. |
| `affil` (on demand) | page 1 of the papers that passed the first reading (arXiv HTML, else the PDF's first page): affiliations and email domains. One request every 3 seconds, no retries. |
| `news` | about 33 publisher feeds, Google News for India and the US (topic sections, fixed searches, and searches built from `config/interests.json`), depth sources (The Conversation in five editions, Nature News, Quanta), the Hacker News front page, and Reddit (world news, geopolitics, science, economics). |
| `updates` | lab feeds (OpenAI, Google DeepMind, Google Research, Microsoft Research, NVIDIA, Hugging Face, Databricks, W&B, LangChain, BAIR, Stanford CRFM, CMU, EleutherAI), the Alan Turing Institute's generated feeds for labs without RSS (Anthropic, Claude, Mistral, Cohere, Ai2, Mila, xAI, the AI Security Institute, TLDR AI), researcher blogs and newsletters (Lil'Log, Carlini, Chip Huyen, Eugene Yan, Simon Willison, Interconnects, Ahead of AI, Import AI, Latent Space, Last Week in AI), Google News bridges (Meta, xAI, DeepSeek, Qwen, Anthropic, X and LinkedIn posts), Reddit, Bluesky and Hacker News. One row per canonical URL and headline. |
| `podcasts` | AI podcast feeds read directly, shows found by name through the iTunes Search API, and episode searches on your interests. Each episode keeps its audio file so it plays on the page. |
| `videos` | new uploads from curated YouTube channels (free RSS feeds) plus a rotating long-form search, with views, likes, comments, engagement rates and views per subscriber. |
| `youtube` | Shorts from a rotating slice of searches, with the same statistics. |
| `hf` | Hugging Face trending models, datasets and spaces. |
| `fun` | the latest xkcd and a random one, for #random. |

**Resilience.** Feeds are fetched in parallel (10 at a time; arXiv stays at one request every 3 seconds). `dsys/net.py` retries timeouts, 429 and 5xx three times (2, 5, 12 seconds plus jitter) and never retries 401, 403, 404 or 410. Every feed's last result is logged in `state/feed_health.json`; a feed that answered 404 or 410 is skipped for a week, then tried again. A feed can list `alternates`. One broken source never stops the rest. A re-run only adds candidates, never removes them. Real text is kept whole: only HTML, tracking parameters and extra whitespace are stripped.

**Runs never search for candidates.** The daily run begins with `dsys.py candidates ensure` (`dsys/ensure.py`): if a fetch is running it waits for it, otherwise it starts one and waits until it finishes, then retries failed sources. A papers file fetched before arXiv's daily release (01:05 UTC) counts as missing, so an early hand-started fetch never stands in for today's papers. Sources that failed are retried once per run, then the data is used as it is (some feeds, like Reddit from GitHub, fail every day). It checks once a minute; one call waits up to 9 minutes (a run's shell commands time out at 10) and the run calls it again up to 10 times. A missing file is never replaced by search: the part is skipped and the Slack message names it.

**Trust registry** (`config/reputation.json`, `dsys/reputation.py`). A binary flag: 1 when an author, an organization or affiliation, or an author email domain matches a listed researcher, lab or university. Universities: the top 1000 research universities by citations (OpenAlex) with QS ranks for the top 100 (QS gates its full table), plus hand-added groups, built by `.github/workflows/build-reputation.yml`. Labs: big tech, frontier and regional labs worldwide (Sakana, Prior Labs, Sarvam, BharatGen, Mistral, DeepSeek and many more) and public institutes. The daily run logs authors and affiliations of picked and trending papers (`state/reputation_log.json`); the monthly run adds recurring strong ones with the papers that justify them.

**Run time and tokens** (`dsys/usage.py`). Each run calls `dsys.py usage start` and `usage end`. In between, every `dsys.py` output, every paper batch and the runbook and prompts it follows are counted in `state/usage/<date>.jsonl`. `dsys.py usage show --date D` or `--week W` prints minutes and estimated tokens read per run (about 4 characters a token), with the biggest reads. The account's real meter isn't visible to a run, and writing and thinking aren't counted, so real use is higher. The numbers are for comparing runs and spotting one that reads too much. The daily Slack message shows the day's figures, and on Saturday the week's.

**Output a run can read in full** (`dsys/readable.py`). Tools cut long command output (about 30,000 characters), long file reads and very long lines without notice. So any `dsys.py` output over 20,000 characters goes to part files of at most 60,000 characters, one compact record per line with long lines wrapped, and the command prints only the list of parts to read. Paper batches for Haiku hold 40 papers in the same form. Large files are changed through commands, not by hand (`reputation add`).

**Web access in runs.** Cloud runs fetch a page without asking only when its URL came from the session (a web search result or a page already fetched). So runs never fetch URLs straight from candidate files; the scraped titles, links and summaries are used as they are (`prompts/_shared.md`).

## 5. Choosing papers

1. **Python** (`dsys.py papers stage1`): drops papers already seen and the ones that match no interest and have no quality signal (votes, discussion, notable author, venue, code). Writes compact batches: id, title, full abstract, matched interests, signals, trust flag, buzz. Coverage keywords per interest live in `arxiv.coverage`.
2. **Haiku** (`prompts/paper_triage.md`), in parallel batches: reads every abstract and sorts each paper into *strong* (on your interests, good), *field* (important for the field with little overlap) or *no*. Calibrated: usually 15 to 30% pass, and only a true doubt is kept. `papers merge` warns when more than half pass.
3. **Page 1** (`dsys.py papers enrich`): affiliations and emails for up to 200 passing papers (strong first, then by buzz; about 10 minutes), then the trust flag.
4. **Sonnet** (`prompts/arxiv.md`): reads the passing papers in full and decides. No fixed number: the best picks are `priority: top`, everything else that passes is `priority: more`, folded on the page. Trust and buzz raise confidence but never rescue an empty abstract. alphaXiv summaries are never used to judge.
5. **Every paper link goes to alphaXiv** (`alphaxiv.org/abs/<id>`), on the site and in the feeds, so you can read the paper and its summary there.
6. **Papers of the week** (`reading.xml`, `weekly/<week>/papers.html`): *For you*, *Trending this week* and *From leading groups*. Daily runs add to it; it is a weekly part.

## 6. Choosing news

Every headline is categorized in code (`dsys/news.py`) into 12 categories, duplicates are merged (`also_in`), and anything published in the last 3 days is dropped. News has two roles, both every day: **awareness** across all categories, and **interest-matched** stories from searches built from your interests. Depth sources (The Conversation, Nature News, Quanta, marked `depth`) are paired with the events they explain, so a story says *why*. Two layers (`prompts/world.md`):

- **Explained items:** 12 to 20 stories across at least 7 categories, with what happened, why it matters, context, what to watch, and a `lesson`: the concept or history behind the story, explained so it sticks. News and Exploration are part of your learning beyond AI, science and maths, so they teach, not just list.
- **Briefs:** 15 to 30 one-line headlines linking to the article.

Research updates are read the same way: one compact pass (`candidates updates --compact`), last 3 days removed, plus 5 to 8 targeted X and LinkedIn searches across all interest keywords. No cap: the best are `priority: top`, the rest folded.

**Counts.** Every stage records how many items it read and passed in `state/stats/<date>.json` (`dsys.py stats show`); the Slack message shows them.

## 7. Slack: the one notification channel

Mobile and email notifications are off for every task. All channels are public (`config/notifications.json`):

| Channel | What |
|---|---|
| #northstar-daily | "Daily is ready" with links and counts, posted at the end of the daily run (`prompts/runs/slack_digest.md`); "Week is ready" on Saturdays; "Month is ready" on the 1st; one line if a part is missing. Never messages about failed sources. |
| #northstar-polls | Thursdays: next week's New in AI topic. The 25th: next month's research and fundamentals deep dives. Posted by the daily run. Every poll ends with "Other: reply with your own topic" (`prompts/runs/topic_poll.md`). |
| #northstar-ask | Rare questions from a run, only when the answer changes what gets made (`prompts/runs/_common.md`). |
| #general | Announcements: changes to Northstar, and the quarterly review (posted by the daily run on the quarter's first day). |
| #random | One light thing a day: an xkcd link or an original joke. |

**Replies.** Reply in Slack, in the thread under a poll or question. A run reads the whole thread and your own messages in the channel after the poll, nothing before it. The weekly and monthly runs read their poll's answers before planning (`prompts/runs/poll_collect.md`); the daily run reads answers to questions at its start. Only the general topic is saved (`state/polls.json`), never private details.

## 8. What is never done (vision §2 and §17)

No streaks, scores, completion tracking, backlogs or guilt. Items carry a status only as an internal detail of the feedback step. Feedback is optional and natural ("more like this", "too basic"). Nothing is carried forward unless you ask. The repo is public, so nothing private is stored (CLAUDE.md rule 5).

## 9. Where things live

| Path | What |
|---|---|
| `docs/vision.md` | why Northstar exists. Read first |
| `docs/how_it_works.md` | this map |
| `docs/scheduled_tasks_setup.md` | how to set up your own copy, step by step: GitHub, Slack, connectors and the four scheduled tasks with their exact prompts |
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
- **Times:** the cron lines in the scheduled tasks and in `.github/workflows/fetch-candidates.yml`. Keep the daily run after the 07:17 fetch, and the weekly and monthly runs before the daily run (`docs/scheduled_tasks_setup.md`).

Finish every change with `python scripts/validate.py && python -m pytest -q`.
