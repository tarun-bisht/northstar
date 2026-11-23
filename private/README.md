# private/ (never committed)

Everything in this folder except this README is ignored by Git, so it never reaches the public repository.

Use it, on your own computer, for anything personal:

- reflections and journal notes
- quarterly syntheses you want to keep
- private schedule details or anything you'd rather not publish

Scheduled cloud runs start from a fresh clone, so they can't see this folder. They never write personal text to the repository: they keep only sanitized, topic-level summaries (`state/preference_profile.json`, `practice/`) and give you anything personal in the run summary instead.

`python scripts/validate.py` fails if any file in `private/` other than this README is tracked by Git.
