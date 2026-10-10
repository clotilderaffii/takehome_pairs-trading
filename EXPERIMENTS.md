> Translated from Italian on 2026-10-10. Content, dates and times of every entry are unchanged.

# Experiment log

Every configuration tried (including failed ones) goes here: date and time, parameters, period (IS/OOS), main result.
Every access to the out-of-sample period must be logged explicitly.

Counters
- Backtest configurations tried on IS: 0
- OOS accesses: 0

---

## 2026-10-10 10:19 CEST — Data download and IS/OOS split date (before looking at prices)

**Type:** setup, no backtest, no price inspected.

**Data:** Yahoo Finance via yfinance 1.7.0, `period="max"`, `interval="1d"`, `auto_adjust=True`.
Raw files: `data/raw/INTC_daily_yahoo.pkl`, `data/raw/AMD_daily_yahoo.pkl`, metadata in `data/raw/prices_metadata.json`.
Scripts: `scripts/fetch_prices.py`, `scripts/compute_split_date.py`.

**Rule (fixed before looking at any price or result):**
common history = dates on which both INTC and AMD have a non-missing Close.
The point at 70% of the common history is rounded to the nearest 1 January.
In-sample = dates < split, out-of-sample = dates ≥ split.
The 70% point was computed in two ways, only to check that rounding makes the choice unambiguous:
(a) 70% of the common trading days; (b) 70% of calendar time.

**Result:**

| Item | Value |
|---|---|
| First common date | 1980-03-17 |
| Last common date | 2026-10-09 |
| Common trading days | 11737 |
| 70% point (trading days) | 2012-10-05 → 2013-01-01 |
| 70% point (calendar) | 2012-10-19 → 2013-01-01 |
| **Split date** | **2013-01-01** |
| IS (1980-03-17 … 2012-12-31) | 8273 days (70.5%) |
| OOS (2013-01-01 … 2026-10-09) | 3464 days (29.5%) |

The two methods agree, so the date is unambiguous: **split = 2013-01-01**.

---

## 2026-10-10 10:20 CEST — Nasdaq short-interest download (Phase 4, raw data only)

**Type:** setup, no analysis.
Endpoint `api.nasdaq.com/api/quote/<TICKER>/short-interest?assetClass=stocks` with a browser User-Agent: HTTP 200 for INTC and AMD.
Files: `data/raw/{INTC,AMD}_short_interest_nasdaq_20261010T082049Z.json`. Script: `scripts/fetch_short_interest.py`.
Coverage: 24 semi-monthly settlement dates per stock, from 2025-10-15 to 2026-09-30.
**Validation note:** the whole window falls in the OOS period (≥ 2013-01-01). The Phase 4 analysis therefore uses OOS prices
and must be done only after the single OOS run with frozen parameters, with no feedback into the parameters.

---

## 2026-10-10 — Phase 1 (data), in-sample ONLY

**Type:** descriptive analysis, no backtest, no parameter estimated or chosen.
**Period:** IS, 1980-03-17 … 2012-12-31 (8273 common days). No data ≥ 2013-01-01 loaded:
the cut happens in `pairs.data.load_pair(end=SPLIT_DATE)` right after reading, backed by asserts.
**Notebook:** `notebooks/01_data.ipynb`. Figures: `reports/figures/01a_prices_log_is.{png,html}`,
`reports/figures/01b_ratio_difference_is.{png,html}`.

**Main results (IS):**
- Correlation of simple daily returns: 0.483 over the whole IS; 0.557 (1980s), 0.330 (1990s),
  0.545 (2000s), 0.585 (2010–2012).
- INTC/AMD ratio: 0.058 at the start, minimum 0.018 (1984-10-10), maximum 7.763 (2012-11-16), 6.144 at the end.
  No stable level, long trending regimes.
- Data checks: no NaN, no price ≤ 0; the most extreme daily returns fall on real market dates
  (e.g. October 1987), no anomalous jumps visible. INTC has 81 dividends since 1992-10-26
  (included in the adjusted price), AMD none.

**To do after the single OOS run:** regenerate Phase 1 on the full history (1980–2026). Until then
no Phase 1 chart, table or statistic uses dates ≥ 2013-01-01.
