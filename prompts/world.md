# World Radar (daily)

Read `prompts/_shared.md` first.

**Purpose:** help them *understand* the world, not consume headlines. India first, then the world: geopolitics, international relations, economy and finance, business, technology and science policy, society, conflicts, disasters, major global events.

## Steps

1. `python scripts/dsys.py context world --date <today>` shows recent items. For ongoing stories, include them only when something materially changed, and set `follows_up` to the earlier item's id.
2. Search the last ~24–36h across reliable sources (`config/sources.json → world.prefer`). Cross-check significant claims across two independent sources when possible.
3. Choose what matters. Ask: will this still matter in a month? Does it change something for India, for many people, or for how the world works? Typical 3–7 items, max `preferences.daily.max_world_items`. Mix regions and topics; don't let one story crowd out the rest unless it is genuinely dominant.
4. For each item:
   - `what_happened`: plain facts
   - `confirmed_facts`: a list of short, attributable facts
   - `why_it_matters`: consequences and stakes
   - `context`: the background a smart non-specialist needs (history, actors, numbers)
   - `analysis`: interpretation, clearly labelled as such (optional)
   - `uncertainty`: what is disputed or unknown, and which claims come from only one side
   - `what_to_watch`: concrete next signals or dates
   - `sources`: one or more, each with its own published date; `published` is the primary source's date
5. Be neutral on contested political questions: describe positions, don't take sides. For conflicts and disasters, be factual and humane; no graphic detail.
6. Write `/tmp/world.json`, merge with `python scripts/dsys.py daily merge world --date <today> --items /tmp/world.json`, then `history rebuild` and `validate`.

Keep every field to one or two short sentences. Say what happened, why it matters and what to watch, and stop. Validation rejects fields that run too long.
