# AI usage disclosure

**Tools.** I used Claude (chat) to discuss the brief, explain concepts, review results and draft prompts, and Claude Code
to write and run the code, tests and notebooks. All files they produced are left as they are; `EXPERIMENTS.md`,
`CLAUDE.md` and the git history show how the work proceeded.

**How the methods were chosen.** The statistical methods were worked out in discussion with the AI: it proposed options
and explained them, I questioned them and decided what to adopt. Claude Code wrote the implementation.

**Ideas and decisions that came from me.**

- **Choice of pair.** I chose INTC/AMD for Phase 4 data coverage, and after the negative OOS result I chose not to
  switch pair, because choosing the pair after seeing the outcome is the selection bias this exercise is about.
- **Questions that became analyses.**
  - I asked whether the negative result could be a bug; this led to the synthetic positive/negative controls.
  - I noticed that INTC and AMD prices look related after 1997; testing that window is the look-elsewhere analysis in
    Phase 5.
  - I noticed that the z-score oscillates as if mean-reverting even though the pair is not cointegrated; this led to
    the comparison with a synthetic random walk in notebook 02.
- **The KO/PEP appendix.** Adding a second pair, after completing the five phases on INTC/AMD, to test the frozen
  pipeline was my decision. I asked whether its in-sample profit was noise, which led to running Phases 3 and 5 on it.
- **Corrections to the AI.**
  - I stopped a proposed order that would have run the Kalman extension before Phases 4–5.
  - I rejected a strategy variant outside Phase 2's scope.
  - I spotted missing outputs (the KO/PEP z-score chart) and a writeup that did not follow the brief's structure.
- **Checks.** I reviewed each proposal before approving it and every result before committing it, asked for an
  explanation of each test before accepting it, kept the log append-only, and checked with `git diff` that generalizing
  the code for KO/PEP changed no existing result.
