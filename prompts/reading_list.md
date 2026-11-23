# Weekly paper reading list

Read `prompts/_shared.md` first.

A short list of papers that are **definitely worth reading this week**: 3 to 8 papers, never padding.

## What belongs

- Papers close to the configured research interests or methods.
- A new concept, method or architecture worth knowing about.
- Papers with clear potential to matter in the future.
- Sources can be anything verified: the arXiv radar, Hugging Face trending papers, posts on X or LinkedIn from researchers, technical reports from AI labs (DeepSeek, OpenAI, Anthropic, Google DeepMind, Meta, Qwen, Mistral and others), or award papers at conferences.

## Each paper

- `id` (`rl-<short-slug>`), `title`, `url` (verified), `authors` if known, `arxiv_id` if it has one, `source`
- `tags`: 1 to 3 from `config/sources.json -> paper_tags` only, most important first
- `note`: optional, one short plain sentence saying what it is. No sales pitch. Never mention the user's projects.

## When to add

- **Weekly run (Saturday):** create next week's list with at least 3 papers (validation requires this when a weekly package exists).
- **Daily runs:** when you find a paper that clearly belongs, add it to this week's list.

```bash
python scripts/dsys.py reading add --week <YYYY-Www> --json /tmp/papers.json   # skips papers already on any list
python scripts/dsys.py reading show --week <YYYY-Www>
```
