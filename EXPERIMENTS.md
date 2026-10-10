> Translated from Italian on 2026-10-10. Content, dates and times of every entry are unchanged.

# Experiment log

Every configuration tried (including failed ones) goes here: date and time, parameters, period (IS/OOS), main result.
Every access to the out-of-sample period must be logged explicitly.

Counters
- Backtest configurations tried on IS: 11 (Phase 2: 9 grid + 1 lag-2 robustness run; + 1 price-level robustness run)
- OOS accesses: 1 (#1: static strategy, 2026-10-10 14:06 CEST)

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

---

## 2026-10-10 12:36 CEST — Pre-registration: robustness run on price levels, as in the brief (written BEFORE computing it)

**Type:** robustness check, IS only. Counted as an attempt: IS backtest counter 10 → **11**.

**Motivation.** Phase 2 deviated from the brief by regressing log prices instead of price levels. This run
checks that the negative Phase 2 result does not depend on that choice. It is not a new candidate strategy:
whatever the outcome, the main configuration of the project stays the log-price one fixed at 11:56.

**Design.**
- OLS on IS (dates < 2013-01-01): `P_INTC = α + β · P_AMD + ε`. Spread = `P_INTC − β · P_AMD` (adjusted prices, USD).
- ADF test on the price spread and Engle–Granger test on the two price series, with p-values.
- Main configuration only: e = 2.0, L = 60, `shift(1)`, same signal rules (exit at zero crossing, direct flip,
  no stop-loss), same costs (5 bp per leg per position change), same metrics, same evaluation window as
  Phase 2 (1980-09-04 … 2012-12-31).
- P&L: hold 1 share of INTC and β shares of AMD (short when long the spread). Daily return
  `position_t × (ΔP_INTC,t − β · ΔP_AMD,t) / (P_INTC,t−1 + |β| · P_AMD,t−1)`, i.e. return on the gross
  capital at the previous close. Costs: 5 bp of each leg's traded notional = 5 bp of gross capital per unit
  of |Δposition|, as in Phase 2.

---

## 2026-10-10 12:41 CEST — Result: robustness run on price levels (IS backtest #11)

**Period:** IS; regression 1980-03-17 … 2012-12-31, evaluation window 1980-09-04 … 2012-12-31 (same as Phase 2).
No OOS data loaded. Code: `use_logs=False` option in `pairs.spread` / `pairs.backtest` (look-ahead test
extended to it). Notebook: section "Robustness: price levels as in the brief" in `notebooks/02_signal.ipynb`.
Figure: `reports/figures/02e_spread_levels_is.{png,html}`.

**Regression (price levels):** α = 2.1677 USD, β = 0.5255 (> 0, AMD acts as a hedge), R² = 0.2213.
**Stationarity:** ADF on the price spread stat −1.619, p = 0.473 (36 lags); Engle–Granger stat −1.621,
p = 0.712. Descriptive: AR(1) b = −0.00092, half-life ≈ 751 trading days. → **not stationary.**

| e = 2.0, L = 60, lag 1 | log prices (main, #5) | price levels (#11) |
|---|---|---|
| ann. return gross / net (%) | −7.84 / −8.16 | −8.37 / −8.69 |
| ann. vol net (%) | 22.22 | 28.21 |
| Sharpe gross / net | −0.26 / −0.27 | −0.17 / −0.18 |
| max DD net (%) | −96.21 | −97.45 |
| trades | 115 | 116 |
| win rate net (%) | 53.91 | 56.03 |
| avg / max duration (days) | 45.4 / 188 | 44.0 / 189 |
| exposure (%) | 63.96 | 62.63 |

**Diagnostic (descriptive):** with a fixed number of shares the AMD leg is a median 92.3% of gross capital in
the 1980s, 69.0% in the 1990s, 31.2% in the 2000s and 20.4% in 2010–2012: the price-level book is not
balanced over time, which explains the higher volatility.

**Reading:** the negative Phase 2 result does not depend on the log-price choice. Nothing changed after
seeing this result; the main configuration of the project remains the log-price one.

---

## 2026-10-10 13:20 CEST — Phase 3 pre-registration: rolling β + rolling ADF (written BEFORE computing)

**Type:** stability analysis, IS only (dates < 2013-01-01). **Not a new backtest:** the IS backtest counter
stays at 11. No Phase 2 parameter is modified.

**Method** (the brief's "medium" option), on log adjusted prices, rolling window **W = 252** trading days:
- **Rolling β:** for every day t, OLS slope (with intercept) of `log P_INTC` on `log P_AMD` over the 252 days
  ending at t inclusive (computed as rolling cov/var, identical to the OLS slope). Undefined for the first 251 days.
- **Rolling ADF:** every **21** trading days (≈ monthly, to limit computation), starting at the first day with a
  full window (IS index 251, then 272, 293, …): build the window's spread with the window's own β and run the
  ADF test (constant, lag length by AIC).
- **Weak period:** ADF p-value > **0.05**, i.e. the window's spread does not look stationary.
- **No look-ahead:** the ADF computed at the close of day t_k applies from day t_k + 1 up to and including the
  next recomputation day; hence the flag used on day t only uses data up to t − 1. Days before the first ADF
  result have no flag.

**Check required by the brief:** does the Phase 2 signal perform worse in weak periods? Using the daily **net**
returns of the main configuration (e = 2.0, L = 60, static β = 1.0471, lag 1) on the Phase 2 evaluation window,
recomputed with the same function and parameters (identical by construction, asserted; not a new backtest).
For weak vs strong days: number of days and share, exposure (share of days in a position), annualized return,
Sharpe, max drawdown; number of trades and net win rate with trades classified by the flag of their entry day.
**Welch t-test** on the difference of mean daily net returns, using **all days** of the window including flat
days (returns as actually experienced, consistent with the Sharpe), with each regime's exposure reported
alongside: a regime with more flat days has a mean pulled towards zero for that reason alone.

**Operational details.**
1. Days without a flag (from 1980-09-04 until the first ADF result, around March 1981) and trades entered on
   such days are excluded from the comparison; their number is reported.
2. Metrics on non-contiguous days: annualized return, Sharpe and max drawdown of a regime are computed on the
   sequence of that regime's days only; max drawdown is therefore that of a "stitched" equity curve made of the
   weak (or strong) days only.

**Declared limitations.**
1. The ADF p-value on a spread whose β is estimated in the same window is optimistic, so the classification
   tends to *under*-count weak periods.
2. With 252 observations the ADF has low power: even a stationary but slow spread often gives p > 0.05, which
   pushes in the opposite direction (weak periods *over*-counted).
3. Consecutive windows overlap by about 92% (231 of 252 days), so flags are highly persistent; the Welch p-value
   is approximate, because daily returns are autocorrelated and regimes come in long blocks (less independent
   information than the day count suggests).
4. The flag measures whether a relationship (with a *local* β) exists in the period, **not** whether the
   static-β spread that the strategy actually trades is stationary.

---

## 2026-10-10 13:25 CEST — Phase 3 results, IS only (design exactly as pre-registered at 13:20)

**Type:** stability analysis; no new backtest (IS backtest counter stays at 11). The main configuration's daily
returns were recomputed with the same function and parameters; identity with Phase 2 asserted
(Sharpe net −0.27, 115 trades). No OOS data loaded.
**Code:** `src/pairs/stability.py` (+ `shade_periods` in `plotting.py`); tests in `tests/test_stability.py`
incl. a look-ahead test on the flag. **Notebook:** `notebooks/03_stability.ipynb`.
**Figures:** `reports/figures/03a_rolling_beta_is`, `03b_rolling_adf_pvalue_is`, `03c_equity_weak_shaded_is` (.png/.html).

**Rolling β (252 days, log prices):** median 0.386; 5th–95th percentile −0.177 … 0.953; min −0.614, max 1.865;
std 0.371; β ≤ 0 on 12.2% of days, β ≤ 0.1 on 20.5%. Static IS β = 1.047 lies above the 95th percentile.

**Rolling ADF (every 21 days):** 382 windows, first computed 1981-03-16, last 2012-11-30; 332 windows with
p > 0.05. Weak days: **86.9%** of flagged IS days (6,971 of 8,021; 1981-03-17 … 2012-12-31). Strong share by
decade: 34.0% (1980s), 5.0% (1990s), 2.5% (2000s), 13.9% (2010–2012).

**Main configuration (e = 2.0, L = 60, static β, lag 1, net), weak vs strong days:**

| regime | days | share | exposure | mean daily net | ann. return | Sharpe | max DD (stitched) | trades | win rate net |
|---|---|---|---|---|---|---|---|---|---|
| weak | 6971 | 86.91% | 64.73% | −2.40 bp | −8.21% | −0.27 | −94.22% | 90 | 50.00% |
| strong | 1050 | 13.09% | 55.71% | −1.72 bp | −6.23% | −0.21 | −38.74% | 23 | 69.57% |

Welch t-test on mean daily net return (weak − strong): t = −0.16, p = 0.875 (approximate). Excluded (no flag
yet): 133 days, 2 trades.

**Reading:** the relationship is unstable (β varies widely, often ≤ 0) and fails the rolling stationarity test
on most of the IS, especially after 1990. The signal loses in both regimes; weak days are slightly worse but
not distinguishably so. Max drawdowns are not comparable across regimes (different lengths of stitched curves).
Untested hypothesis noted for later: with a local β around 0.4 and a static hedge of 1.05, the static-β spread
behaves largely like a position in AMD.

---

## 2026-10-10 13:59 CEST — Phase 3 addition: test of the "spread ≈ AMD position" hypothesis (IS only)

**Type:** descriptive diagnostic, no backtest (IS backtest counter stays at 11). No OOS data loaded.
**Code:** `pairs.stability.spread_leg_correlations` (+ test). **Notebook:** section 4 of `notebooks/03_stability.ipynb`.
Also: the x-axis of `03b_rolling_adf_pvalue_is` now starts at the first data date (1980-03-17); PNG regenerated.

Pearson correlation of the daily change of the static-β log spread (`log P_INTC − 1.047·log P_AMD`) with each
leg's simple daily return:

| period | days | corr with AMD | corr with INTC |
|---|---|---|---|
| All IS | 8272 | −0.754 | 0.208 |
| 1980s | 2475 | −0.609 | 0.319 |
| 1990s | 2528 | −0.802 | 0.295 |
| 2000s | 2515 | −0.777 | 0.101 |
| 2010–2012 | 754 | −0.892 | −0.157 |

**Reading:** hypothesis confirmed in-sample. The static-β spread is mostly a short AMD position (correlation
−0.75 overall, more negative after the 1980s), and only weakly linked to INTC. A long-spread trade is largely a
bet against AMD; the Phase 2 signal behaves like a contrarian bet on one volatile stock rather than on the
relationship.

---

## 2026-10-10 14:05 CEST — Pre-registration: Kalman extension (to be implemented after Phases 4–5)

**Type:** design only. No code written, nothing computed. Written **before** OOS access #1 (static strategy,
next entry), so the OOS result of the static strategy cannot influence this design.

**Motivation (Phase 3).** The local one-year β has median 0.39 against the static IS β of 1.047; the static-β
spread is mostly a short AMD position (correlation −0.75 with AMD's daily return). A time-varying hedge ratio
is the natural attempt to hedge with the local relationship instead.

**Model.** `log P_INTC,t = α_t + β_t · log P_AMD,t + ε_t`, `ε_t ~ N(0, V)`; state `x_t = (α_t, β_t)` follows a
random walk `x_t = x_{t−1} + w_t`, `w_t ~ N(0, W)`. Two-state Kalman filter implemented by hand in numpy.

**Hyperparameters** from the literature (E. Chan, *Algorithmic Trading*, 2013), **not optimized**:
V = 0.001; W = δ/(1 − δ) · I with **δ = 1e-4 (main configuration)**. Sensitivity: δ ∈ {1e-5, 1e-4, 1e-3},
i.e. **3 IS attempts** (IS backtest counter 11 → 14 when run). Declared limitation: these values come from a
price-level ETF example and are applied to log prices without rescaling; they are not calibrated to this pair.

**Initialization.** State mean = OLS (α, β) on the first 252 days of the IS; initial state covariance = the OLS
coefficient covariance matrix from the same 252 days. These 252 days are excluded from the evaluation. The
filter then runs forward day by day from day 253; in the OOS run it continues from its IS state without
re-initialization.

**No look-ahead.** Only the **filtered** state (data up to and including t) is used, never the smoothed one.
A pytest test will check that modifying prices after a date d does not change β_t, the z-score or positions
up to d.

**Signal** identical to Phase 2: L = 60, entry ±2.0, exit when z crosses 0, direct flip allowed, no stop-loss,
`shift(1)` execution, 5 bp per leg per position change, rf = 0. The z-score of day t applies β_t to the whole
window, with `a = log P_INTC`, `b = log P_AMD`:
`s_t = a_t − β_t·b_t`, mean = `mean_L(a) − β_t·mean_L(b)`,
variance = `var_L(a) + β_t²·var_L(b) − 2·β_t·cov_L(a, b)`, `z_t = (s_t − mean) / sqrt(variance)`.

**P&L** of day t+1: `position_t × (r_INTC,t+1 − β_t · r_AMD,t+1) / (1 + |β_t|)`. Declared limitation: the
rebalancing costs caused by changes in β are not counted (only position changes pay 5 bp per leg).

**Evaluation.** IS: from the first day after the 252-day initialization to 2012-12-31; the static strategy is
reported on the same window for comparison (from its existing daily returns, not a new backtest). Same metrics
as Phase 2.

**OOS.** The main configuration δ = 1e-4 will have its own single OOS run after implementation (planned OOS
access #2), **whatever its IS result**. The design will not be modified after seeing the OOS of the static
strategy.

---

## 2026-10-10 14:06 CEST — OOS access #1: single out-of-sample run of the static strategy (written BEFORE computing)

**Frozen configuration** (pre-registered 11:56, unchanged): log prices; β = 1.0471 estimated on the IS
(dates < 2013-01-01) and **not re-estimated**; e = 2.0, L = 60; `shift(1)`; 5 bp per leg per position change;
rf = 0; exit at zero crossing, direct flip, no stop-loss.
**Period:** 2013-01-01 to the last available date in `data/raw/` (2026-10-09). The z-score may use the last 59
IS days as warm-up; the strategy starts **flat** on the first OOS trading day.
**Commitment:** no parameter will be modified after this run, and no other run of the static strategy on the OOS
will be made. Descriptive only: ADF and Engle–Granger tests on the OOS spread.
**OOS access counter: 1.**

---

## 2026-10-10 14:07 CEST — Result of OOS access #1 (static strategy)

**Notebook:** `notebooks/02c_oos.ipynb`. **Figures:** `reports/figures/02f_equity_oos`, `02g_spread_oos` (.png/.html).
β = 1.0471 re-checked as estimated on IS only (last date used 2012-12-31). IS reference recomputed with the same
function and parameters (Sharpe net −0.27, 115 trades; asserted). OOS: 2013-01-02 … 2026-10-09, 3464 days,
started flat.

| e = 2.0, L = 60, lag 1 | IS (1980-09-04 … 2012-12-31) | OOS (2013-01-02 … 2026-10-09) |
|---|---|---|
| ann. return gross / net (%) | −7.84 / −8.16 | −6.22 / −6.56 |
| ann. vol net (%) | 22.22 | 22.80 |
| Sharpe gross / net | −0.26 / −0.27 | −0.16 / −0.18 |
| max DD gross / net (%) | −95.93 / −96.21 | −81.80 / −82.44 |
| trades | 115 | 51 (1 open at end, closed on 2026-10-09 for the stats) |
| win rate net (%) | 53.91 | 60.78 |
| avg / max duration (days) | 45.4 / 188 | 40.8 / 132 |
| exposure (%) | 63.96 | 60.05 |

**Descriptive stationarity tests on the OOS:** ADF on the spread with the frozen β: stat −0.513, p = 0.890
(0 lags); Engle–Granger on OOS log prices (β re-estimated on the OOS by the test): stat −1.870, p = 0.595.

**Reading:** the negative IS result is confirmed out-of-sample. The frozen-β spread trends down from its 2015
peak for about a decade (AMD's outperformance; the spread is mostly a short AMD position, Phase 3), and the
strategy loses most of its value in 2016–2021. No parameter was changed after this run; no other OOS run of the
static strategy will be made. Pending (as logged at Phase 1): regenerate Phase 1 on the full history.

---

## 2026-10-10 14:17 CEST — Phase 1 on the full history (1980–2026), after OOS access #1

**Type:** descriptive only, as planned at Phase 1; not used to choose or change anything. Not a backtest and not a
new OOS access of any strategy (OOS access counter stays at 1; IS backtest counter stays at 11).
**Notebook:** new section "Full history (1980–2026), generated after the single OOS run" at the end of
`notebooks/01_data.ipynb`; the IS cells, tables and figures are unchanged (IS PNG files byte-identical after
re-execution). **Figures:** `reports/figures/01c_prices_log_full`, `01d_ratio_difference_full` (.png/.html), with the
2013-01-01 split marked by a vertical dashed line.
**Data:** 11,737 common days, 1980-03-17 … 2026-10-09.

**INTC/AMD ratio:** 0.058 at the start, minimum 0.018 (1984-10-10), maximum 13.752 (2015-09-30), 0.172 at the end.

**Correlation of simple daily returns (full history):**

| period | days | correlation |
|---|---|---|
| All | 11736 | 0.459 |
| 1980s | 2475 | 0.557 |
| 1990s | 2528 | 0.330 |
| 2000s | 2515 | 0.545 |
| 2010s (2010–2019) | 2516 | 0.374 |
| 2020s (2020 – 2026-10-09) | 1702 | 0.498 |

**Reading:** daily co-movement stays positive and moderate in every decade, while the price levels drift apart
(ratio from its 2015 peak down by almost two orders of magnitude): the same correlation-vs-stable-spread
distinction found in-sample.
