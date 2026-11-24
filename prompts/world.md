# World Radar (daily)

Read `prompts/_shared.md` first.

**Purpose:** help them *understand* the world, not consume headlines. India first, then the world, with real coverage of the economy and markets every day.

## Sections

Every item gets a `section`. The daily page shows them in this order:

| section | what goes here | typical items |
|---|---|---|
| `india` | national politics, policy, courts, society, states, India's foreign relations | 3 to 4 |
| `world` | geopolitics, conflicts, elections, diplomacy, disasters, major events abroad | 3 to 4 |
| `economy_markets` | RBI and policy rates, inflation and growth data, Sensex/Nifty, rupee, crude, global markets, big corporate and banking news, regulation (SEBI) | 2 to 4, **at least 2** |
| `science_tech` | science, technology and tech policy, climate and environment, health, space | 1 to 3 |
| `explainers` | one or two well-argued explainers or expert analysis, mainly The Conversation and Indian Express Explained, on something in the news or worth knowing | 1 to 2 |

Aim for `preferences.daily.world_target` (10 to 16) items. On a genuinely quiet day fewer is fine, but never skip `economy_markets`.

## Steps

1. `python scripts/dsys.py context world --date <today>` shows recent items. Include an ongoing story only when something materially changed, and set `follows_up` to the earlier item's id.
2. Read the fetched headlines, one section at a time: `python scripts/dsys.py candidates news --date <today> --section india --brief` (then `world`, `economy_markets`, `science_tech`, `explainers`). They come from the publisher feeds in `config/sources.json → world.feeds`, fetched at 06:00 IST. Use `--brief` to scan, and drop `--brief` for a section when you need the summaries.
   - Several headlines about the same event are one item. Cluster first, then choose.
   - If `available` is false, or `failed_sources` covers a whole section, use web search for that section instead (`world.prefer` sources) and say so in `notes`.
3. Choose what matters. Ask: will this still matter in a month? Does it change something for India, for many people, or for how the world works? Prefer substance over drama and celebrity. Mix regions and topics.
4. **Economy and markets, every day.** Include one short markets item: how Indian markets (Sensex, Nifty), the rupee and crude moved and why, plus a global market move if significant. Use only figures stated in a source, with that source's date. On weekends and market holidays, cover the week's market story or a major economic data release instead.
5. Open the article for each chosen item (WebFetch), or search for a second report, before writing. Cross-check significant claims across two independent sources when possible.
6. For each item fill:
   - `section` (from the table above), `topic`, `regions`
   - `what_happened`: plain facts
   - `confirmed_facts`: a list of short, attributable facts
   - `why_it_matters`: consequences and stakes
   - `context`: the background a smart non-specialist needs (history, actors, numbers)
   - `analysis`: interpretation, clearly labelled as such (optional). For explainers, this is the author's main argument.
   - `uncertainty`: what is disputed or unknown, and which claims come from only one side
   - `what_to_watch`: concrete next signals or dates
   - `sources`: one or more, each with its own published date. `published` is the primary source's date.
7. Be neutral on contested political questions: describe positions, don't take sides. For conflicts and disasters, be factual and humane, with no graphic detail.
8. Write `/tmp/world.json`, merge with `python scripts/dsys.py daily merge world --date <today> --items /tmp/world.json`, then `history rebuild` and `validate`.

Keep every field to one or two short sentences. Say what happened, why it matters and what to watch, and stop. Validation rejects fields that run too long.
