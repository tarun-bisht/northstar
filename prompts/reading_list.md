# Papers of the week

Read `prompts/_shared.md` first.

The week's papers: a separate weekly part (`weekly/<week>/papers.html`, feed `reading.xml`), not part of daily. Three groups, set with `kind`:

1. **For you** (`kind: for_you`, 4 to 8): papers closest to the user's research interests and methods, the ones they should definitely read. Mostly from the week's arXiv radar.
2. **Trending this week** (`kind: trending`, 3 to 6): the week's most discussed papers on alphaXiv and Hugging Face Daily Papers that a researcher should know about, even outside the user's own topics. Find them with `python scripts/dsys.py candidates arxiv --trending-week <YYYY-Www>`, which collects every day's candidates for that week, ranked by votes, with the interests each one touches. Record `alphaxiv_votes` and `hf_upvotes`. New model releases and influential methods also belong here.
3. **From leading groups** (`kind: lab`, 0 to 4, set `group`): strong new work from leading labs and university groups (for example Google DeepMind, Anthropic, OpenAI, Meta FAIR, Stanford, MIT, CMU, Berkeley, Mila, Oxford, Tsinghua) that is related to AI or the user's research. Technical reports count. Find them with WebSearch or in the radar (`notable` flags).

The test for every entry: *would knowing this make me a better researcher?* (vision §6). Never padding. At most 16 entries.

## Each paper

- `id` (`rl-<short-slug>`), `title`, `url` (verified), `authors` if known, `arxiv_id` if it has one, `source`
- `tags`: 1 to 3 from `config/sources.json -> paper_tags` only, most important first
- `note`: optional, one short plain sentence saying what it is. No sales pitch. Never mention the user's projects.

## When to add

- **Weekly run (Saturday):** create next week's list with at least 3 papers (validation requires this when a weekly package exists): the for-you papers you can already see, and the trending papers of the week just ending.
- **Daily runs (every weekday):** add 0 to 3 entries to the current week's list: for-you papers from the day's radar, and trending papers as their votes climb. Keep it selective: a day with nothing worth adding is fine. Never re-add what is already on a list.

```bash
python scripts/dsys.py reading add --week <YYYY-Www> --json /tmp/papers.json   # skips papers already on any list
python scripts/dsys.py reading show --week <YYYY-Www>
```
