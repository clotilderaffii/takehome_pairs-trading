# INTC / AMD pairs trading — writeup

**Result.** INTC and AMD are correlated (daily-return correlation 0.46) but not cointegrated (Engle–Granger p = 0.975
in-sample). The pre-registered z-score strategy loses in-sample (net Sharpe −0.27) and out-of-sample (−0.18). The loss
is explained: the static hedge ratio (1.05) is more than twice the local one (median 0.39), so the spread is mostly a
short-AMD position. Synthetic pairs with a known answer show the pipeline works, so the negative result comes from the
data, not from a bug.

**Repository.** `README.md` maps each phase to its notebook. `EXPERIMENTS.md` is the timestamped, append-only log of
every pre-registration and result (INTC/AMD: 14 IS backtests, 2 OOS runs; KO/PEP: 9 IS, 1 OOS). The IS/OOS split was
fixed by rule before looking at any price (IS 1980–2012, OOS 2013–2026). AI usage: see `AI_DISCLOSURE.md`.

## Phases completed

Phases 1–5, one extension (Kalman hedge ratio), an appendix on KO/PEP. Throughout: 5 bp per leg costs, look-ahead tests
on every signal, synthetic positive/negative controls.

## Methods chosen, and why

- **Phase 2 — log prices**, because prices span two orders of magnitude (a run on price levels gives the same
  conclusion). Stationarity tested with ADF and Engle–Granger, not only by eye. Main configuration (2.0σ, 60 days)
  fixed a priori; the 3×3 grid measures sensitivity and was not used to pick a cell (all 9 are negative net).
- **Phase 3 — rolling β + rolling ADF** rather than rolling correlation, because the diagnosis needed the hedge ratio
  itself.
- **Phase 4 — Nasdaq short interest on both legs**, aligned to the publication date to avoid look-ahead; 5
  pre-registered tests on 23 periods, none significant.
- **Phase 5 — joint block bootstrap rather than OU**, because Phase 2 rejects mean reversion. The real OOS Sharpe sits
  at the 21st percentile of "correlated but unrelated" paths. A look-elsewhere test checks the 1997–2004 window, which
  looked related by eye: it is not cointegrated (p = 0.51), and in 78.5% of "no relationship" histories at least one
  eight-year window passes Engle–Granger at 5%.
- **Extension — Kalman hedge ratio.** Chosen because it tests the Phase 3 diagnosis: if the losses come from a static β
  far from the local one, a time-varying β should remove them (a basket would change the assets, walk-forward the
  validation scheme). Hyperparameters from the literature, pre-registered before the first OOS run. Net Sharpe +0.25 IS,
  +0.07 OOS (interval includes zero): most of the loss is removed, no profit is created.
- **Appendix — KO/PEP**, the brief's textbook pair, run through the frozen pipeline. The IS grid is all positive (main
  0.57), but the pair is not cointegrated (p = 0.45) and the single OOS run loses (−0.21). A bootstrap (declared after
  the result) puts the IS Sharpe at the 94th percentile of "no relationship" paths: a robust in-sample grid is not
  evidence of a lasting relationship.

## With more time

Walk-forward validation instead of a single split; Kalman noise calibrated by maximum likelihood; a z-score based on the
filter's prediction error; longer Phase 3 windows; an OU simulation of KO/PEP to ask the opposite question to the
bootstrap; a basket of three or more stocks tested with Johansen.
