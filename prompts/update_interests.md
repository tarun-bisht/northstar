# Updating interests from conversation

Read `prompts/_shared.md` first. Use this whenever the user says something about what they care about, in any chat: "I'm getting into pottery", "less anime for now", "I know transformers well", "I want to get better at writing", "I'm travelling to Vietnam next month", "send me videos close to the project we're working on".

**The golden rule: translate, never record.** What the user tells you can be private (their projects, travel, plans, schedule). Turn it into **general, public topics** and save only those. Never save the private fact itself, anywhere: not in config, ideas, feedback, commit messages or notes.

| They say | Save | Never save |
|---|---|---|
| "I follow / love X" (repeatedly) | `interests add established.<list> "X"` (lists: `ai_research`, `foundations`) | — |
| "I want to get better at / understand X" | `interests add growth.<list> "X"` (`for_research`, `research_skills`, `people_and_self`, `humanities_and_culture`) | — |
| "curious about X", "maybe X sometime" | `interests add exploration.<list> "X"` (`subjects`, `culture`, `making_and_curiosity`) or `world.regions` | — |
| "X has become a real interest" | `interests move exploration.<list> established.<list> "X"` (or growth → established) | — |
| "less X" / "not into X anymore" | `interests remove ...`; for a firm no, also `less_of` feedback | — |
| **a project** ("videos around the project we're working on") | the general research topics its method touches, e.g. for a project on unlearning via latent perturbation: `established.ai_research`: "unlearning with representation perturbation", "second-order unlearning", "latent-space editing" | the project's name, codename, results, collaborators or status |
| **travel or a trip** ("going to Vietnam") | interests such as `exploration.culture` or `exploration.subjects`: "Vietnam travel videos", "Vietnam documentaries", "Vietnamese cuisine", "Southeast Asian history" | dates, the fact of the trip, who with, where they're staying |
| **schedule or busyness** ("busy until the 15th", "free next week") | nothing. Just adjust this conversation's suggestions. | anything, including `config/schedules.json`, which only the user edits by hand |
| "I want to try / learn X" (an activity) | an idea at interest level: `prompts/inbox.md` (`ideas add`) | personal context |
| sources: blogs, arXiv categories, YouTube topics or languages | `config/sources.json` (the only place for these) | — |
| tone, sizes, difficulty | `config/preferences.json` | — |

`python scripts/dsys.py interests list` shows every list, and `interests find "X"` shows where something already is.

Before saving, ask yourself: *could a stranger reading this line learn something private about the user or anyone else?* If yes, generalise it further or don't save it.

After editing: `python scripts/validate.py`, then commit with a neutral message, e.g. `interests: update research and world topics`. Don't put the private reason in the commit message. Tell the user in one line what you added.
