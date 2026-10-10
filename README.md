# INTC / AMD pairs trading — BlackSwan Quants take-home

**Start here: `notebooks/summary.ipynb` — a short guided tour of the results; the other notebooks contain the full analysis.**

**Goal.** Test, as honestly as possible, whether the INTC/AMD price relationship supports a mean-reversion (pairs trading)
signal: build the spread, trade a rolling z-score, and validate it with a pre-fixed in-sample / out-of-sample split
(IS < 2013-01-01 ≤ OOS), pre-registered parameter grids, a single OOS run per strategy, stability diagnostics and
simulations. The answer is negative, and the notebooks document why (the spread has no stable mean; the static-β spread is
mostly an AMD position). Every attempt, with date and time, is logged in [EXPERIMENTS.md](EXPERIMENTS.md); the half-page
summary is in [WRITEUP.md](WRITEUP.md).

## Where to find what

| Phase | Notebook | What you will find |
|---|---|---|
| 0 — pipeline check | `notebooks/00_pipeline_check.ipynb` | Positive/negative controls on synthetic pairs: the pipeline finds a known relationship and finds nothing when there is none. |
| 1 — data | `notebooks/01_data.ipynb` | Prices (log scale), ratio and difference, daily-return correlations by decade; IS first, full history added after the OOS run. |
| 2 — spread and signal (IS) | `notebooks/02_signal.ipynb` | Log-price hedge regression, ADF / Engle–Granger, z-score signal, full 3×3 grid (Sharpe heatmap), robustness runs, diagnostics. |
| 2c — out-of-sample | `notebooks/02c_oos.ipynb` | The single OOS run of the frozen static strategy (OOS access #1). |
| 3 — stability | `notebooks/03_stability.ipynb` | Rolling β and rolling ADF, weak vs strong periods, spread-vs-leg correlations. |
| 4 — short interest | `notebooks/04_short_interest.ipynb` | Nasdaq short interest aligned to publication dates; three pre-registered questions. |
| 5 — simulation | `notebooks/05_simulation.ipynb` | Joint block bootstrap (500 paths) vs the real Sharpe; **look-elsewhere** analysis of an a-posteriori window. |
| 6 — Kalman extension | `notebooks/06_kalman.ipynb` | Pre-registered dynamic hedge ratio: 3 IS runs and its single OOS run (OOS access #2). |
| Appendix — second pair | `notebooks/appendix_kopep.ipynb` | Same Phase 1–2 pipeline on KO/PEP (separate counters), plus Phase 3/5 diagnostics. |

All figures are also saved in `reports/figures/` as static PNG (shown in the notebooks, readable on GitHub) and
interactive HTML.

## Repository structure

```
src/pairs/        package: data, spread, signal, backtest, metrics, stability, short_interest,
                  simulation, kalman, synthetic, plotting, config, exceptions
notebooks/        one notebook per phase (executed, outputs included)
tests/            pytest suite (incl. look-ahead tests)
scripts/          one-off data downloads, split-date computation, simulation runs (see each docstring)
data/raw/         raw Yahoo Finance and Nasdaq downloads (committed for reproducibility)
data/processed/   simulation checkpoints (committed; notebooks reload them)
reports/figures/  PNG + HTML figures
archive/          superseded files (kept, not deleted)
docs/             the brief and the programming guidelines
EXPERIMENTS.md    append-only experiment log: every configuration, every OOS access, with date and time
WRITEUP.md        half-page summary
```

## How to run

Python 3.12 with [uv](https://docs.astral.sh/uv/):

```bash
uv sync                      # install the exact locked environment (uv.lock)
uv run pytest                # tests
uv run ruff check . && uv run mypy
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/02_signal.ipynb   # any notebook
```

No download is needed: raw data and simulation checkpoints are in `data/`. Re-creating them is possible with the
scripts in `scripts/` (Yahoo/Nasdaq data change over time, so a new download may differ). PNG export uses `kaleido`,
which needs a local Chrome/Chromium.

## AI usage

This project was built with an AI coding assistant (Claude Code). `CLAUDE.md` (the project instructions given to the
assistant, in Italian) and the files the assistant produced (code, scripts, notebooks, logs) are left in the repository
on purpose, as part of the AI-usage disclosure required by the brief.
