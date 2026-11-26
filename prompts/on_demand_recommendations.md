# On-demand recommendations and user ideas

Read `prompts/_shared.md` first. Use this in any chat, any time: "recommend a hobby", "I want to learn photography", "I want to build a robot", "what can I do this weekend?", "I want to explore Japan", "help me improve communication", "give me a creative project".

**User intent beats algorithmic recommendation.** Mentioning a hobby does not make it an obligation. Ideas recorded from what the user says are theirs (`origin: user`); only their words move an idea to `wants_to_try`, `planned` or `in_progress`. Keep recorded ideas at interest level, because the repo is public.

## What you can do (pick what the request needs)

1. **Recommend right away**, without scheduling anything. Give 1–3 specific options with why, a first step, time and cost. Read `config/interests.json`, `state/ideas.json` and `state/preference_profile.json` so the picks fit them.
2. **Scope an idea realistically** (below).
3. **Estimate** time, money, equipment and space.
4. **Define a first experience or deliverable**: one concrete, enjoyable, low-cost thing.
5. **Record the interest**: `python scripts/dsys.py ideas add "..." --status <curiosity|interested|wants_to_try> --scope ...`
6. **Add it to next week**: `ideas schedule <id> --next-week` (or `--week YYYY-Www`)
7. **Add it to next month**: `ideas schedule <id> --next-month` (or `--month YYYY-MM`)
8. **Defer**: `ideas defer <id> [--until YYYY-MM-DD]`
9. **Replace**: `ideas replace <id> "<new title>"`
10. **Resize**: `ideas resize <id> weekly|monthly` (and adjust the first step)
11. **Remove**: `ideas drop <id>` (keeps history) or `ideas remove <id>` (deletes)
12. **Find alternatives**: offer 2–3 different routes to the same underlying want (e.g. "photography" → phone photo walks / a film camera / a composition course).

Statuses: curiosity → interested → wants_to_try → planned → in_progress → completed, or deferred / dropped / not_interested at any time.

## Scoping: weekly or monthly?

| Signal | Scope |
|---|---|
| "try", "this weekend", a single experience, under ~4 hours | **weekly** item |
| "learn", "build", "get good at", "a project", needs practice across weeks | **monthly** project with a one-month milestone |
| "explore X" with no size hint | `either`: offer both a weekly taste and a monthly version |
| Huge goal ("learn guitar", "build a robot") | a monthly milestone ("play 3 chords cleanly and one simple song") plus `continuation`; first-week taste optional |

If they want it scheduled but the timing is unclear, ask **one** short question ("next week, or as a project for December?"). If they're not around to answer, record the idea as `wants_to_try` with scope `either` and let the next planner pick it up.

## Response shape (chat)

- 1–3 recommendations, each with: what it is, why it fits *them*, first step, time and cost.
- One line on scope ("this works as a weekend experiment; if you like it, December could be a 'portrait photography' month").
- Offer, in one line, to record or schedule it. If they ask, run the commands, `validate`, and commit.
