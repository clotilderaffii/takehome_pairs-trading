> Translated from Italian on 2026-10-10. Content, dates and times of every entry are unchanged.

# Experiment log

Every configuration tried (including failed ones) goes here: date and time, parameters, period (IS/OOS), main result.
Every access to the out-of-sample period must be logged explicitly.

Counters
- Backtest configurations tried on IS: 10 (9 grid + 1 pre-registered robustness run, Phase 2)
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

---

## 2026-10-10 11:56 CEST — Phase 2 pre-registration (written BEFORE any Phase 2 computation)

**Type:** declarations and design. No spread, regression, test or backtest has been run at the time of writing.

### a) Choice of pair
INTC/AMD was chosen because it is the only one of the three suggested pairs with Nasdaq short-interest data
available for both legs (Phase 4). The choice was made before looking at any price.

### b) Prior knowledge (disclosed)
Before starting I already knew, roughly, that AMD strongly outperformed Intel from about 2015 onwards,
i.e. in the out-of-sample period. This knowledge has not been used in any design choice below; it is
disclosed because it could bias expectations about the OOS result.

### c) Design (fixed now; not to be modified after seeing results)

**Hedge regression (IS only).** OLS on log adjusted prices, estimated on dates < 2013-01-01:
`log P_INTC = α + β · log P_AMD + ε`. Spread = `log P_INTC − β · log P_AMD`.
Deviation from the brief (which uses price levels), motivated by Phase 1: over the IS period prices span
about two orders of magnitude and the dollar difference is not comparable across decades; in logs, a unit
of spread means the same percentage mispricing in 1985 and in 2010.
Report α, β, R² and their meaning. If β ≤ 0 or β is very close to zero, flag it as a problem: the AMD leg
would no longer act as a hedge.

**Stationarity of the IS spread.** ADF test on the spread (constant, lag length by AIC) and Engle–Granger
cointegration test (`log P_INTC` on `log P_AMD`), both with p-values. The outcome is reported whatever it is.
Engle–Granger is the appropriate test because β is estimated (the plain ADF p-value on an estimated
residual is too optimistic).

**Half-life (descriptive only).** Half-life of mean reversion of the IS spread from an AR(1) regression
`Δs_t = a + b·s_{t−1} + u_t`, half-life = `−ln 2 / ln(1 + b)`. It is reported only as a diagnostic and
**will not be used to modify the grid, whatever value it takes.**

**Signal.** `z_t = (s_t − mean_L(s)_t) / std_L(s)_t`, rolling window of the last L days ending at t
(inclusive), `min_periods = L`, so only data up to the close of day t are used.
- Long spread (long INTC, short β AMD) when z < −e; short spread when z > +e.
- Exit when z crosses zero (long exits when z ≥ 0, short exits when z ≤ 0). No stop-loss.
- Direct flip: if on the same day the exit condition and the opposite entry condition both hold
  (e.g. long and z > +e), the position flips directly; this counts as one exit plus one new entry.
- During the z-score warm-up (z undefined) the position is flat.

**Execution.** Signal computed at the close of day t, position active from day t+1
(`position = signal.shift(1)`): the position earns the return from close t to close t+1.

**P&L.** Daily return on gross capital: `position × (r_INTC − β · r_AMD) / (1 + |β|)`, with r simple daily
returns. Leg weights are `1/(1+|β|)` (INTC) and `−β/(1+|β|)` (AMD), so the gross exposure is 1.

**Risk-free rate = 0.** The P&L of the long/short position is treated as an excess return, so the
risk-free rate is not subtracted again; this is the standard convention for market-neutral strategies.
Caveat: this is exact for a dollar-neutral book; with β ≠ 1 the book carries a net exposure of
`(1 − β)/(1 + β)` of capital, whose financing at the risk-free rate is ignored.

**Costs.** 5 bp on the traded notional of each leg at every position change. Since the two legs sum to
1 unit of gross capital, this is 5 bp of capital per entry or exit, 10 bp per round trip and 10 bp per
direct flip (cost = 5 bp × |Δposition|). Fixed value, not optimized. Results reported both gross and net.

**Grid (declared now, shown in full).** e ∈ {1.5, 2.0, 2.5} × L ∈ {20, 60, 120} = 9 configurations.
**Main configuration fixed a priori: e = 2.0, L = 60**, regardless of results. The grid measures
sensitivity; it is not used to pick the best configuration.

**Robustness check (pre-registered, counted as an attempt).** Main configuration only, with one extra day
of execution delay (`position = signal.shift(2)`). Total IS backtests planned: 9 + 1 = **10**.

**Evaluation window.** All configurations are evaluated on the same window: from the first day on which
the L = 120 z-score exists to 2012-12-31, so that the metrics are comparable.

**Metrics** (252 trading days per year, rf = 0): annualized return (compounded), annualized volatility,
Sharpe ratio, max drawdown, number of trades, win rate (share of trades with positive **net** return),
average and maximum trade duration (trading days), share of days in the market.
A trade still open on 2012-12-31 is closed at that date for the trade statistics and flagged.

**Declared limitations.**
1. β is estimated on the whole IS period, so an IS trade in 1985 uses a β that "knows" 2012. This is the
   unavoidable optimism of an in-sample backtest and the reason the OOS test exists.
2. Constant leg weights imply daily rebalancing of the two legs; the cost of that rebalancing is ignored.

**Look-ahead test.** With β held fixed (because β is estimated on the whole IS, limitation 1), modifying
prices after a date d must not change the spread, the z-score or the positions up to d.

---

## 2026-10-10 12:03 CEST — Phase 2 results, IS only (design exactly as pre-registered at 11:56)

**Period:** IS. Regression on 1980-03-17 … 2012-12-31 (8273 days). Common evaluation window
1980-09-04 … 2012-12-31 (first day with an L = 120 z-score). No OOS data loaded.
**Code:** `src/pairs/{spread,signal,backtest,metrics}.py`; tests incl. look-ahead test with fixed β
(`tests/test_lookahead.py`). **Notebook:** `notebooks/02_signal.ipynb`.
**Figures:** `reports/figures/02a_spread_is`, `02b_zscore_main_is`, `02c_equity_main_is`, `02d_sharpe_heatmap_is` (.png/.html).

**Hedge regression:** α = −1.2311, β = 1.0471 (> 0, AMD acts as a hedge), R² = 0.1499.

**Stationarity of the IS spread:** ADF stat −0.313, p = 0.924 (5 lags); Engle–Granger stat −0.315,
p = 0.975. AR(1) b ≈ −0.0001, half-life ≈ 6705 trading days (descriptive only; grid unchanged).
→ **No evidence of stationarity / cointegration in-sample.**

**All 10 IS backtests** (returns, vol, max DD in % per year / %; Sharpe annualized, rf = 0):

| # | e | L | lag | ann. ret gross | ann. ret net | vol | Sharpe gross | Sharpe net | max DD net | trades | win rate net | avg / max duration (days) | exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.5 | 20 | 1 | −2.42 | −3.63 | 22.93 | 0.01 | −0.05 | −93.80 | 403 | 64.27 | 13.9 / 92 | 68.69 |
| 2 | 1.5 | 60 | 1 | −8.13 | −8.55 | 23.46 | −0.24 | −0.26 | −97.25 | 149 | 58.39 | 39.5 / 193 | 72.21 |
| 3 | 1.5 | 120 | 1 | −5.12 | −5.35 | 23.27 | −0.11 | −0.12 | −93.86 | 79 | 68.35 | 75.8 / 494 | 73.41 |
| 4 | 2.0 | 20 | 1 | −2.25 | −3.13 | 20.78 | −0.01 | −0.05 | −94.04 | 292 | 62.33 | 15.1 / 91 | 53.96 |
| **5 (main)** | **2.0** | **60** | **1** | **−7.84** | **−8.16** | **22.22** | **−0.26** | **−0.27** | **−96.21** | **115** | **53.91** | **45.4 / 188** | **63.96** |
| 6 | 2.0 | 120 | 1 | −5.30 | −5.47 | 21.99 | −0.14 | −0.15 | −88.53 | 59 | 61.02 | 88.0 / 487 | 63.65 |
| 7 | 2.5 | 20 | 1 | −2.91 | −3.34 | 16.24 | −0.10 | −0.13 | −87.57 | 143 | 59.44 | 16.8 / 89 | 29.53 |
| 8 | 2.5 | 60 | 1 | −4.87 | −5.12 | 19.84 | −0.15 | −0.17 | −90.61 | 83 | 57.83 | 47.4 / 155 | 48.23 |
| 9 | 2.5 | 120 | 1 | −4.94 | −5.07 | 20.33 | −0.15 | −0.15 | −85.02 | 43 | 53.49 | 101.4 / 479 | 53.50 |
| 10 (robustness) | 2.0 | 60 | 2 | −8.43 | −8.75 | 22.14 | −0.29 | −0.30 | −95.72 | 115 | 55.65 | 45.4 / 188 | 63.96 |

Vol shown is net (gross differs by ≤ 0.01 pp). Configurations 3, 6 and 9 each have one trade open on
2012-12-31, closed there for the trade statistics.

**Main configuration diagnostic (same trades, no new backtest):** win rate 53.9%, average winning trade
+4.55%, average losing trade −9.45%; long-spread and short-spread trades lose about equally (sum of log net
returns −1.34 and −1.41). Worst trades last 97–153 days while the spread keeps drifting; no stop-loss.

**Reading:** the IS spread has no stable mean, and the rolling z-score keeps signalling reversion towards
a level that moves. Every configuration has negative net Sharpe; the failure is not specific to one
parameter choice. Costs are not the cause (Sharpe lowered by at most 0.06). Nothing was changed after
seeing these results; the OOS has not been touched.
