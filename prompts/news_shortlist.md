# News shortlist (Haiku, every day)

You read every fetched headline once and shortlist the ones worth a closer look. A stronger model then reads only your shortlist in full and writes the day's World Radar. So **miss nothing important**, and keep out the noise. This prompt is all you need: don't read other files.

## Read

1. `python scripts/dsys.py interests list` shows the user's interests (three tiers).
2. `python scripts/dsys.py candidates news --date <today> --brief` lists every headline, grouped by category, one row each: `ref`, `title`, `source`, sometimes `also_in` (other outlets with the same story) and `depth: true` (an expert explainer: The Conversation, Nature News, Quanta). Long output comes as part files: read every part.

## Choose

Shortlist about **120 to 180 refs** in all:

- **Every category with real news:** its biggest stories, at least 5 where it has them (conflict and disaster, leadership changes, economy and markets, geopolitics, technology, science and space, health, climate and energy, business, society, India, explainers). A story carried by many outlets (long `also_in`) is usually big.
- **Interest-matched stories:** anything on the user's interests (AI, chips, research policy, science, the regions and subjects in the list), even when small.
- **Every `depth: true` row** that explains something in today's news.
- **Markets:** the rows that report how Indian markets, the rupee and crude moved, and any big global move.
- Skip: sport results, celebrity, local crime and notices, horoscopes, listicles, duplicates of a row you already took.

## Write

`/tmp/northstar/<today>/news_shortlist.json`: a JSON list of the chosen refs, e.g. `["c759af6", "c3c1b3a"]`. Reply with the count per category, one line.
