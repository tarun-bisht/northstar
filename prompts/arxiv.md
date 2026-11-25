# arXiv Paper Radar (Monday to Friday)

Read `prompts/_shared.md` first.

The job is to filter. From a few thousand new papers, keep only the high-quality ones that would make the user a better researcher (vision §6), and drop the rest. Fewer and better is the point. A typical day keeps 5 to 12. Zero is fine on a quiet day.

## Where candidates come from

`candidates/arxiv/<today>.json` is fetched at 06:00 IST (gaps refilled at 06:50) from three sources:
- the **arXiv API**, for every category in `config/sources.json → arxiv.categories`, which together cover every research interest (`arxiv.coverage`). rss.arxiv.org is the fallback.
- **Hugging Face Daily Papers**: community upvotes (`hf_upvotes`).
- **alphaXiv**: four community lists over 7 days, Hot, Likes, Twitter (X) and GitHub (`alphaxiv_votes`, `alphaxiv_lists`). The Twitter (X) list is how research discussion on X reaches the radar (signal `discussed on X`). Plus one **alphaXiv search per interest** (`alphaxiv_interests`, signal `alphaXiv search: ...`), which also catches papers the keywords miss. All of these feed the ranking.

## Steps

1. `python scripts/dsys.py context arxiv --date <today>`. If `is_weekday` is false, stop.
2. **Ranked shortlist (code, no AI):** `python scripts/dsys.py candidates arxiv --date <today> --ranked`. Every paper is scored in code from its title, abstract and signals (`dsys/rank.py`). The shortlist holds the best 3 papers for every interest, filled up to about 80 by score, plus `also_trending_or_notable`. Each row shows `interests` (which ones it matches), `signals` (votes, upvotes, notable researcher, code released, venue) and `score`.
   - If the file is missing, or `failed_sources` lists categories, WebSearch for that day's new papers in those categories (for example "arXiv cs.LG new submissions"), WebFetch the arxiv.org listing page from the results, and say so in `notes`. Never type an arxiv.org URL into WebFetch directly (`prompts/_shared.md`, web access).
3. **Read abstracts, in batches:** `python scripts/dsys.py candidates arxiv --date <today> --ids <id1>,<id2>,...` prints full candidates. Read every abstract in the shortlist and in `also_trending_or_notable`. Never decide from a title alone. Never open PDFs. The abstract and the signals are the evidence.
4. **Judge quality from the abstract.** Rate each paper 1 to 5 in your head:
   - **5, keep:** a clear, specific contribution; strong evidence (experiments on standard benchmarks against strong baselines, real theory, or a large careful analysis); concrete results stated; plus at least one outside signal (venue, notable group, community votes, released code).
   - **4, keep:** clear contribution and solid evidence, even without outside signals.
   - **3, keep only if** it is close to the user's own work or the abstract shows an unusually useful idea, dataset or negative result.
   - **1 to 2, drop.** Red flags: a "novel framework" with no stated results; one small dataset; a combination of existing tricks; overclaiming without evidence; a prompt wrapper with no evaluation; an application with no transferable insight; a vague abstract.
5. **What to keep (vision §6).** Both kinds count:
   - *direct relevance:* close to or useful for the user's research interests
   - *research development value:* an important method, a challenged assumption, a useful theory, a strong benchmark, an exposed failure mode, a useful methodology, a connection between fields, an important negative result, a field-shifting idea
   - **Trending is a reason on its own.** A paper in `also_trending_or_notable` that is high quality and touches any interest is kept, even if it scored low on keywords. "This paper is becoming widely discussed" is valuable for a researcher.
   - **Notable researchers.** A paper with `notable_authors` (or by another widely recognised group) is kept when its abstract touches any interest and passes the quality bar. Tag it `notable researcher`.
6. Balance the day: don't let one area take every slot. If five good papers are all on one topic, keep the best two or three.
7. For each kept paper, fill: `id` (`arxiv-<id>`), `arxiv_id`, `title`, `authors`, `url`, `pdf_url`, `submitted`, `categories`, `abstract` (**copied word for word**), `abstract_source`, `research_area` (two or three words), `hf_upvotes` if known, `dimensions`.
8. **Tags, not reasons.** Give 1 to 3 tags from `paper_tags`, most important first. These are the only tags allowed:
   close to your work, useful for your work, new method or architecture, strong result, notable researcher, benchmark or dataset, theory, survey or tutorial, worth knowing.
   Never write a reason or explanation. Never mention a project or method of the user's.
9. Mark every shortlisted paper you read but did not keep as seen: `python scripts/dsys.py papers mark-seen <id> ...`.
10. **Reading list:** the best one to three papers of the day (yours, or trending and important for any researcher) also go on this week's papers of the week list (`prompts/reading_list.md`).
11. Merge: `python scripts/dsys.py daily merge arxiv --date <today> --items /tmp/arxiv.json`, then `history rebuild` and `validate`. Put a one-line `notes` on the day: how many candidates, how many shortlisted, how many kept.
