# Pairs trading on INTC/AMD and KO/PEP — writeup

**Result.** I completed all five phases on INTC/AMD, the project's pair. Only afterwards did I run the same frozen
pipeline on KO/PEP, the brief's textbook pair (the "second pair" extension). Neither pair is cointegrated in-sample and
both lose out-of-sample. INTC/AMD loses everywhere; KO/PEP earns on the whole in-sample grid and still loses
out-of-sample. A good in-sample result was not evidence of a lasting relationship.

**Repository.** `notebooks/summary.ipynb` is a short guided tour; `README.md` maps phases to notebooks;
`EXPERIMENTS.md` is the append-only log of every pre-registration and result. Attempts:

- INTC/AMD: 14 IS backtests, 2 OOS runs, 2 simulation runs;
- KO/PEP: 9 IS backtests, 1 OOS run, 1 simulation run;
- 2 synthetic control runs.

Pre-registrations were committed together with their results, so git alone cannot prove the order. AI usage: see
`AI_DISCLOSURE.md`.

| | INTC / AMD | KO / PEP |
|---|---|---|
| In-sample / out-of-sample | 1980–2012 / 2013–2026 | 1972–2009 / 2010–2026 |
| Phase 2 — Engle–Granger p (IS); half-life | 0.975; ≈ 27 years | 0.45; ≈ 1.5 years |
| Net Sharpe IS, main config / grid of 9 | −0.27 / all negative | 0.57 / all positive |
| Net Sharpe OOS, single run | −0.18 | −0.21 |
| Phase 3 — rolling β median vs static β (IS) | 0.39 vs 1.047 | 0.70 vs 0.98 * |
| Phase 4 — short interest | association at settlement dates | not run |
| Phase 5 — real Sharpe percentile in null, IS / OOS | 2.8th / 21st | 94th / 1.8th * |
| Kalman extension, net Sharpe IS / OOS | +0.25 / +0.07 | not run |

\* Decided after seeing the KO/PEP results: diagnostics, not tests.

## Methods chosen, and why

- **Phase 2 — log prices**, because prices span two orders of magnitude; a run on price levels gives the same result.
  I tested stationarity with Engle–Granger, not only by eye. The main configuration was fixed a priori, and the grid
  only measures sensitivity.
- **Phase 3 — rolling β + rolling ADF**, because the diagnosis needed the hedge ratio itself. On INTC/AMD the static β
  is far above the local one, so the spread moves mostly with AMD (correlation −0.75). This is consistent with the
  losses, but not proof.
- **Phase 4 — short interest.** My pre-registered
  publication-date alignment compares the spread with positions from a week earlier, so it found nothing. At
  settlement dates, relative short interest moved with the spread (ρ = 0.58, p = 0.004): an association in one year
  of data, not a signal.
- **Phase 5 — block bootstrap rather than OU**, because Phase 2 finds no mean reversion to simulate. The null is
  "no link beyond 20 days".
  - KO/PEP's in-sample profit is about what this null already earns (median 0.32).
  - The look-elsewhere test is a general lesson: in 78.5% of null histories some eight-year window passes
    Engle–Granger at 5%.
- **Kalman extension (INTC/AMD).** I chose it to test the Phase 3 diagnosis. It does not confirm it: with a local β
  around 0.2 it becomes a bet on INTC instead of AMD, its IS Sharpe comes from 1981–1991, and its OOS Sharpe is
  indistinguishable from zero. It is also not blind to the declared prior knowledge about AMD.
- **Code check.** On synthetic pairs the code recovers a known OU relationship and finds nothing on a random walk. This
  rules out gross errors, but it is not a proof of power against a weak relationship.

**Limitations.** Short-borrow costs are not modelled, and neither are the Kalman's rebalancing costs. The first IS
trade inherits the signal state from before the evaluation window.

## With more time

- A power curve on synthetic pairs.
- Walk-forward validation.
- Comparing the Kalman strategy with mean reversion on INTC alone.
