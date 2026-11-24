# World Radar (daily)

Read `prompts/_shared.md` first.

**Purpose:** help them *understand* the world, not consume headlines. For every item the test is: what happened, why does it matter, and is it worth their attention? This is not a generic news feed.

## News categories

Every item gets one `section`. The daily page groups items by section in this order:

| section | what goes here |
|---|---|
| `india` | national politics, governance, courts, states, Indian policy and society |
| `geopolitics` | international relations, diplomacy, elections abroad, alliances, sanctions, India's foreign relations |
| `conflict_disaster` | wars and armed conflicts, terrorism, natural disasters, humanitarian crises |
| `economy_markets` | RBI and central banks, inflation, growth and jobs data, Sensex/Nifty, rupee, bonds, crude, global markets, trade and tariffs, SEBI and financial regulation |
| `business_tech` | major companies and deals, banking and corporate news, the tech industry, AI policy, chips, telecom, startups |
| `science_health` | science discoveries, space, public health, medicine |
| `climate_energy` | climate, environment, energy transition, oil and gas, power, extreme weather trends |
| `society` | demographics, migration, education, urbanisation, inequality, culture and social change |
| `explainers` | well-argued explainers and expert analysis (The Conversation, Indian Express Explained) on something in the news or worth understanding |

Also set `topic` (the finer subject: `geopolitics`, `trade`, `energy`, `migration`, `policy`, …) and `regions`.

## How much

- Aim for `preferences.daily.world_target` (10 to 16) items across **at least 6 categories**.
- Every day: `india` 2 to 3, `economy_markets` at least 2 (one is a short markets item), and at least 1 explainer.
- The rest by importance. On a quiet day fewer is fine, but never pad.
- **Regions:** India first, then the world. Over a week, cover South Asia, East and Southeast Asia, the Middle East, Europe, Africa, the Americas, Central Asia and Oceania when something there matters. Don't let one region or story crowd out the rest unless it is genuinely dominant.

## Steps

1. `python scripts/dsys.py context world --date <today>` shows recent items. Include an ongoing story only when something materially changed, and set `follows_up` to the earlier item's id.
2. **Read every headline, by category.** `python scripts/dsys.py candidates news --date <today> --brief` lists every headline fetched at 06:00 IST from the publisher feeds (`config/sources.json → world.feeds`). In code, each headline gets a news category (`world.categories`), and headlines about the same event are merged into one row with `also_in` listing the other outlets. Read the categories one at a time with `--category <name>`, and drop `--brief` when you need summaries. The code category is a hint: assign each chosen item its own `section`. The `other` bucket (sport, celebrity, local notices, crime) is usually skipped.
   - A story many outlets carry (long `also_in`) is often the day's big story, but judge importance yourself.
   - If `available` is false, or `failed_sources` leaves a category empty, use web search for it (`world.prefer` sources) and say so in `notes`.
3. Filter hard. Keep what will still matter in a month, changes something for India or for many people, or shows how the world works. Drop crime blotter, celebrity, sport results and minor politics.
4. **Markets item, every day:** how Indian markets (Sensex, Nifty), the rupee and crude moved and why, plus a global move if significant. Use only figures stated in a source, with that source's date. On weekends and market holidays, cover the week's market story or a major data release instead.
5. Before writing, WebSearch each chosen story's headline: this gives a second report and article URLs you can WebFetch without approval (`prompts/_shared.md`, web access). Never fetch a URL straight from the candidates file. Cross-check significant claims across two independent sources when possible.
6. For each item fill: `section`, `topic`, `regions`, `what_happened` (plain facts), `confirmed_facts` (short attributable facts), `why_it_matters`, `context` (background a smart non-specialist needs), `analysis` (optional and labelled as interpretation; for explainers, the author's main argument), `uncertainty`, `what_to_watch`, and `sources` (each with its own published date; `published` is the primary source's date).
7. Be neutral on contested political questions: describe positions, don't take sides. For conflicts and disasters, be factual and humane, with no graphic detail.
8. Write `/tmp/world.json`, merge with `python scripts/dsys.py daily merge world --date <today> --items /tmp/world.json`, then `history rebuild` and `validate`.

Keep every field to one or two short sentences. Validation rejects fields that run too long.
