# Quarterly synthesis (optional)

Read `prompts/_shared.md` first.

**Purpose:** every few months, step back and look at how interests and abilities are evolving, and at what Northstar should do differently. **This is not a performance review.** No percentages, no rankings of dimensions, no "you only did X".

## Steps

1. `python scripts/dsys.py synthesis --quarter <YYYY-Qn>` (default: current quarter). It returns qualitative evidence: what was engaged with, explored per dimension, quiet dimensions, the tiers and modes engaged with, cross-domain connections, new user ideas, ideas completed or let go, and explicit interest signals.
2. Write a short, warm synthesis answering, where the evidence allows:
   - What new things have been explored?
   - What abilities have been practised?
   - What has been created?
   - What seems to have become easier?
   - What interests have emerged, and what has stopped being interesting?
   - Which areas have had little attention lately? Say this neutrally; it's an observation, not a gap to close.
   - What unexpected connections have appeared?
   - What should Northstar recommend differently?
   Say clearly when the evidence is thin (for example, little feedback was given). Don't infer more than is there.
3. **Privacy:** the synthesis is personal. Give it to the user (chat or the run summary). When running locally, you may also save it to `private/synthesis/<YYYY-Qn>.md` (gitignored). **Never commit it.**
4. **System changes** are the only thing that may be committed, and only if they are sanitized and clearly helpful: adjust `config/interests.json` (move topics between tiers, e.g. exploration → established when something stuck), tweak `config/recommendation_policy.json` guidance, or add an idea at interest level. Explain each change in one line in the summary. When unsure, propose the change in the summary instead of making it.
5. If you changed anything: `python scripts/validate.py`, then commit `quarterly: <YYYY-Qn> system adjustments`.
