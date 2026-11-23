# Processing the ideas inbox

Read `prompts/_shared.md` first. Run this at the start of every scheduled run (daily, weekly, monthly). It's cheap when the inbox is empty.

1. `python scripts/dsys.py inbox show ideas`. If it prints `(empty)`, stop.
2. For each line or idea, decide the user's intent, then the status:
   - "curious about X" → `curiosity`
   - "interested in X", "maybe someday" → `interested`
   - "I want to try / learn X" → `wants_to_try`
   - "X this weekend / next week / next month" → schedule it (`--week` / `--month`)
   - "not interested in X anymore" → find the existing idea and drop it with `--not-interested`
   - "recommend me X" → a request, not an idea: answer it with an on-demand recommendation (`prompts/on_demand_recommendations.md`), add the result to the next discovery file if it's a simple pick, and record the underlying interest as an idea.
3. **Scope** (`prompts/on_demand_recommendations.md` § Scoping): a first experience fits a week; building a skill or project fits a month; "explore philosophy" could be either (`either`). Don't assume weekly.
4. Check for an existing idea first (`python scripts/dsys.py ideas list`); update it rather than adding a duplicate. If it matches a **seed** idea, the user's own words make it theirs: move it with `python scripts/dsys.py ideas status <id> <status> --note "user asked"` (this records an explicit action). Only the user's words can move an idea to `wants_to_try`, `planned` or `in_progress`; never do it on your own judgement.
5. Add each one: `python scripts/dsys.py ideas add "<title>" --description "<their words + your scoping>" --scope <weekly|monthly|either|undecided> --status <...> --dimensions <...> --first-step "<a concrete first experience>" --estimate "<time>" [--week YYYY-Www | --month YYYY-MM]`
6. Do not schedule anything they did not ask to schedule. Interest is not an obligation. Curiosity and interest are never scheduled automatically.
7. The inbox is public. Record the idea at the level of an interest ("learn photography"); leave out any personal context they wrote, and never copy names, places or private reasons into `state/ideas.json`.
8. `python scripts/dsys.py inbox clear ideas`, then `validate`.
