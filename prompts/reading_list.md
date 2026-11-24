# Weekly paper reading list

Read `prompts/_shared.md` first.

A short list of papers and works that are **definitely worth reading this week**: 3 to 10, never padding. It is shown every day in the Research part of the daily page, so the daily runs keep it current.

The test for every entry: *would knowing this make me a better researcher?* (vision §6). Two kinds belong:
1. **Important to me:** close to or useful for the configured research interests and methods.
2. **Important for any researcher right now:** a widely discussed or fast-trending paper (high `alphaxiv_votes` or `hf_upvotes`), a new model release or technical report from a major lab, an influential method or methodology, an important negative result or a field-shifting benchmark.

## What belongs

- Papers close to the configured research interests or methods.
- A new concept, method or architecture worth knowing about.
- Papers with clear potential to matter in the future.
- Sources can be anything verified: the arXiv radar, Hugging Face trending papers, alphaXiv trending (https://www.alphaxiv.org, or `alphaxiv_votes` in the arXiv candidates), papers by notable researchers, posts on X or LinkedIn from researchers, technical reports from AI labs (DeepSeek, OpenAI, Anthropic, Google DeepMind, Meta, Qwen, Mistral and others), or award papers at conferences.

## Each paper

- `id` (`rl-<short-slug>`), `title`, `url` (verified), `authors` if known, `arxiv_id` if it has one, `source`
- `tags`: 1 to 3 from `config/sources.json -> paper_tags` only, most important first
- `note`: optional, one short plain sentence saying what it is. No sales pitch. Never mention the user's projects.

## When to add

- **Weekly run (Saturday):** create next week's list with at least 3 papers (validation requires this when a weekly package exists).
- **Daily runs (every weekday):** review the day's candidates, trending signals and lab releases, and add 0 to 3 entries that clearly belong to the current week's list. Keep it selective: a day with nothing worth adding is fine. Never re-add what is already on a list.

```bash
python scripts/dsys.py reading add --week <YYYY-Www> --json /tmp/papers.json   # skips papers already on any list
python scripts/dsys.py reading show --week <YYYY-Www>
```
