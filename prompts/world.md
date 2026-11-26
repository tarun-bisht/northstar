# World Radar (daily)

Read `prompts/_shared.md` first.

**Purpose:** help them *understand* the world, not consume headlines. For every item the test is: what happened, why does it matter, and is it worth their attention? This is not a generic news feed.

## News categories

Every item gets one `section`. The daily News page groups items by section in this order:

| section | what goes here |
|---|---|
| `india` | national politics, governance, courts, states, Indian policy and society |
| `geopolitics` | international relations, diplomacy, elections abroad, alliances, sanctions, India's foreign relations |
| `leadership` | leadership changes with national or global impact only (see the rule below) |
| `conflict_disaster` | wars and armed conflicts, terrorism, natural disasters, humanitarian crises |
| `economy_markets` | RBI and central banks, inflation, growth and jobs data, Sensex/Nifty, rupee, bonds, crude, global markets, trade and tariffs, SEBI |
| `business` | major companies, deals, results, banking and corporate news, startups |
| `technology` | the tech industry and AI: Nvidia, OpenAI, Google, chips and semiconductors, AI policy, cybersecurity, telecom, big launches |
| `science_space` | science discoveries, space (ISRO, NASA, SpaceX, missions, launches), physics, biology |
| `health` | public health, medicine, outbreaks, drug approvals |
| `climate_energy` | climate, environment, energy transition, oil and gas, power, extreme weather |
| `society` | demographics, migration, education, urbanisation, inequality, culture and social change |
| `explainers` | well-argued explainers and expert analysis: The Conversation, Indian Express Explained |

**Leadership changes: only what matters beyond one town.** Include: heads of state and government, and major ministers (finance, foreign, defence, home) in any country; central bank governors; heads of major international bodies (UN agencies, IMF, World Bank, WTO, WHO); military chiefs; CEOs, founders, chairs and top executives of major companies (large listed companies, big tech, AI labs such as OpenAI, Anthropic, Google DeepMind and Meta AI, top Indian groups such as Tata, Reliance, Adani, Infosys, HDFC); well-known people leaving or joining such companies; election results that change a government. Exclude: local officials, mayors of small towns, school boards, councils, clubs, unions, small companies, sports bodies, and court admissions. The test: does this change affect a country, a global market, a major company or a field?

Also set `topic` (the finer subject: `geopolitics`, `trade`, `energy`, `migration`, `policy`, …) and `regions`.

## Two layers: explained stories and briefs

The world is busy. Cover it in two layers, so the user sees most of what matters without every story costing a full write-up.

1. **Explained items** (`items`): **12 to 20** (`preferences.daily.world_target`) across **at least 7 categories**, with the full fields below. These are the stories worth understanding.
2. **Briefs** (`briefs`): **15 to 30** more one-line headlines (`preferences.daily.world_briefs_target`), for other notable stories, so nothing important is missed. Each brief is `{title, url, source, section, line}`: the headline, the article URL **copied from the candidates** (no fetch needed), the outlet, the category, and an optional `line` of at most one sentence saying why it's notable. Every category with real news gets something, either an explained item or a brief.

Every day:
- `india` 2 to 4 explained items
- `economy_markets` at least 2, one of them a short markets item
- `technology` at least 2 (AI and the tech industry move fast: Nvidia, OpenAI, chips, policy)
- `science_space` at least 1 when there is real news, space included
- `leadership`: every significant change of leader worldwide that day, as an explained item if it matters for India or the world, otherwise as a brief
- `explainers` at least 2, **at least one from The Conversation** whenever its feeds have something relevant (they use a 96-hour window)
- the rest by importance. On a quiet day fewer is fine, but never pad.

**Regions:** India first, then the world. Over a week, cover South Asia, East and Southeast Asia, the Middle East, Europe, Africa, the Americas, Central Asia and Oceania when something there matters. Don't let one region or story crowd out the rest unless it is genuinely dominant.

## Steps

1. `python scripts/dsys.py context world --date <today>` shows recent items. Include an ongoing story only when something materially changed, and set `follows_up` to the earlier item's id.
2. **Sweep every category, and miss nothing.** Go through all 12 categories in the table, one at a time, as a checklist (`--category <name>`, plus `other` to rescue anything miscategorized). Stories come only from the fetched file: never search for stories. Headlines published in the last 3 days are already removed. Note in `notes` any category that had nothing worth including.

   **Read every headline, by category.** `python scripts/dsys.py candidates news --date <today> --brief` lists every headline fetched at 07:17 IST from the publisher feeds and Google News (`config/sources.json → world.feeds` and `world.google_news`, which includes searches for subjects such as Nvidia, AI, chips, ISRO and SpaceX). In code, each headline gets a news category (`world.categories`), and headlines about the same event are merged into one row with `also_in` listing the other outlets. Read the categories one at a time with `--category <name>`, and drop `--brief` when you need summaries. The code category is a hint: assign each chosen item its own `section`. The `other` bucket (sport, celebrity, local notices, crime) is usually skipped.
   - A story many outlets carry (long `also_in`) is often the day's big story, but judge importance yourself.
   - Headlines come only from this file (the daily run has already waited for the fetch). If `failed_sources` leaves a category thin, say so in `notes`. Web search is only for reading more about a story you picked from the file, never for finding stories.
3. Choose. Two kinds of news, both every day: **awareness** (the big stories in every category, whatever the user's interests) and **interest-matched** stories (from searches built from `config/interests.json`: AI, science, research policy, the regions and topics they follow). Explained items: what will still matter in a month, changes something for India or for many people, or shows how the world works.
   **Depth, not just events.** A big story should say *why*: why the economy is slowing, why forests are being cut, why a policy changed. Rows marked `depth: true` (The Conversation, Nature News, Quanta) are explainers by experts: pair them with the event they explain, and use them for `context` and `analysis` with their own link in `sources`. Briefs: other genuinely notable stories, including ones the user would never have searched for. Drop crime blotter, celebrity, sport results and minor local politics.
4. **Markets item, every day:** how Indian markets (Sensex, Nifty), the rupee and crude moved and why, plus a global move if significant. Use only figures stated in a source, with that source's date. On weekends and market holidays, cover the week's market story or a major data release instead.
5. Write from the fetched rows first: full summaries, `also_in` (other outlets covering the same story) and paired depth pieces. Only when they don't give enough facts for an explained item, WebSearch that story's headline to read more (`prompts/_shared.md`, web access). Never fetch a URL straight from the candidates file. Cross-check significant claims across two independent sources when possible.
6. For each item fill: `section`, `topic`, `regions`, `what_happened` (plain facts), `confirmed_facts` (short attributable facts), `why_it_matters`, `context` (background a smart non-specialist needs), `analysis` (optional and labelled as interpretation; for explainers, the author's main argument), `uncertainty`, `what_to_watch`, and `sources` (each with its own published date; `published` is the primary source's date).
7. Be neutral on contested political questions: describe positions, don't take sides. For conflicts and disasters, be factual and humane, with no graphic detail.
8. Write `/tmp/world.json` as `{"items": [...], "briefs": [...], "notes": "..."}`, merge with `python scripts/dsys.py daily merge world --date <today> --items /tmp/world.json`, then `history rebuild` and `validate`. Briefs need no WebFetch: their URLs come straight from the candidates, which Actions already fetched.

Keep every field to one or two short sentences. Validation rejects fields that run too long.
