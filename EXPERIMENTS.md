> Translated from Italian on 2026-10-10. Content, dates and times of every entry are unchanged.

# Experiment log

Every configuration tried (including failed ones) goes here: date and time, parameters, period (IS/OOS), main result.
Every access to the out-of-sample period must be logged explicitly.

Counters
- Backtest configurations tried on IS: 14 (Phase 2: 9 grid + 1 lag-2 robustness run; + 1 price-level robustness run;
  Kalman extension: 3 δ values)
- OOS accesses: 2 (#1: static strategy, 2026-10-10 14:06 CEST; #2: Kalman δ = 1e-4, 2026-10-10 16:12 CEST)

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

## 2026-10-10 11:35 CEST (time from git commit 87875c0) — Phase 1 (data), in-sample ONLY

*Time added on 2026-10-10 at 14:31 CEST: the entry was originally logged without a time. 11:35:22 +02:00 is the time
of git commit 87875c0, which added `notebooks/01_data.ipynb`; it is an upper bound, since the work was done
before the commit.*

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

---

## 2026-10-10 14:31 CEST — Pipeline validation on synthetic data (not a strategy attempt)

**Type:** validation of the code with a known answer. Not a strategy attempt: IS backtest counter stays at 11,
OOS access counter stays at 1. No real data used.
**Code:** `src/pairs/synthetic.py` (`make_synthetic_pair`, `run_pipeline_control`); tests in
`tests/test_pipeline_controls.py`. **Notebook:** `notebooks/00_pipeline_check.ipynb`.
**Figure:** `reports/figures/00_pipeline_controls_equity.{png,html}`.

**Data:** 8,000 business days, seed 2026 (fixed before running, single run, not changed). `log P_B` random walk with
2% daily volatility; `log P_A = 0.5 + 0.8 · log P_B + s_t`. Positive control: `s_t` AR(1)/Ornstein–Uhlenbeck with
half-life 10 days and stationary sd 0.05. Negative control: `s_t` random walk with the same daily innovations.
**Pipeline:** exactly the INTC/AMD functions — `fit_hedge_ratio`, `stationarity_tests`, `run_strategy` with e = 2.0,
L = 60, `shift(1)`, 5 bp per leg; first half IS (β estimated there only; IS window from the first day with an
L = 120 z-score, as in Phase 2), second half OOS with β frozen, starting flat.

| | positive (OU residual) | negative (random-walk residual) |
|---|---|---|
| β (true 0.8) | 0.800 | 1.122 (spurious) |
| Engle–Granger p (IS) | 1.90e-18 | 0.618 |
| ADF p (IS) | 1.53e-19 | 0.369 |
| half-life, days (IS) | 10.7 | 423.2 |
| Sharpe net IS / OOS | 1.89 / 1.92 | −0.28 / 0.24 |
| ann. return net IS / OOS (%) | 20.7 / 19.0 | −3.6 / 2.1 |
| max DD net IS / OOS (%) | −8.6 / −9.0 | −56.8 / −30.7 |
| trades IS / OOS | 84 / 84 | 58 / 68 |

**Reading:** expected results obtained. When a mean-reverting relationship exists, the pipeline recovers β, detects
cointegration and trades it profitably in- and out-of-sample; when none exists, it finds nothing and earns nothing
reliable. INTC/AMD (EG p = 0.975, half-life ≈ 6,700 days, net Sharpe −0.27 IS / −0.18 OOS) resembles the negative
control: the negative result reflects the data, not a bug hiding a real signal. Caveat: one seed per control.

---

## 2026-10-10 14:47 CEST — Phase 4 pre-registration: short interest (written BEFORE computing)

**Type:** descriptive analysis, no backtest (IS backtest counter stays at 11, OOS access counter stays at 1). The data
(2025-10-15 … 2026-09-30) lie in the OOS period; using them now is legitimate because the single OOS run of the
static strategy has been done and no parameter will change.

**Data:** the two raw JSON files already in `data/raw/` (`{INTC,AMD}_short_interest_nasdaq_20261010T082049Z.json`,
24 semi-monthly settlement dates each); not re-downloaded. Prices: `data/raw/` Yahoo checkpoints, adjusted close.

**Publication date.** Short interest becomes public about 7 business days after the settlement date. **Main
analysis:** align each value to its publication date = settlement + 7 business days (weekday calendar, exchange
holidays ignored); if that is not a trading day, use the first trading day on or after it. The settlement-date
alignment is computed with the same code and reported **as descriptive only** (no inference drawn from it).

**Data-quality flag:** days-to-cover values exactly equal to 1.0 are flagged as a probable floor of the source.

**Variables, one row per period between two consecutive publication dates (23 periods):** period k runs from the
close of publication day k to the close of publication day k+1.
- % change of the short interest of INTC and of AMD (value published at k+1 vs value published at k);
- change of the log spread `log P_INTC − 1.0471 · log P_AMD` (static IS β);
- simple return of INTC and of AMD over the period;
- maximum absolute daily return of the two stocks within the period (max over days and over both stocks).

**Exactly three questions, fixed now** (Spearman rank correlation, two-sided p-value, n = 23):
1. Does each stock's short-interest change go with the spread change in the same period? → 2 correlations
   (INTC SI change vs spread change; AMD SI change vs spread change).
2. Does the difference of the SI changes (INTC minus AMD, in percentage points) go with the spread change?
   → 1 correlation.
3. Do periods with a strong SI increase coincide with larger-than-usual moves? → 2 correlations (INTC SI change vs
   max absolute daily return; AMD SI change vs max absolute daily return).

Total: **5 Spearman tests**; no other combination will be tested. For each: ρ, p-value, n, and the minimum |ρ|
needed for significance at 5% with n = 23 (from the t approximation used for the p-value). Because of multiple
comparisons, the Bonferroni threshold 0.05 / 5 = 0.01 is reported as well.

**Declared limitations:** 23 observations → very low statistical power; 5 tests → multiple-comparison risk; a single
one-year window → not representative; the publication lag is approximate (holidays ignored, exact Nasdaq/FINRA
publication calendar not used).

---

## 2026-10-10 14:50 CEST — Phase 4 results: short interest (design as pre-registered at 14:47)

**Type:** descriptive; no backtest (IS backtests 11, OOS accesses 1, unchanged). Data not re-downloaded.
**Code:** `src/pairs/short_interest.py`; tests in `tests/test_short_interest.py` (incl. publication-date calculation).
**Notebook:** `notebooks/04_short_interest.ipynb`. **Figure:** `reports/figures/04a_short_interest_spread.{png,html}`.

**Data:** 24 settlement dates per stock, 2025-10-15 … 2026-09-30; publication anchors 2025-10-24 … 2026-10-09 (all
publication dates fell on trading days). Over the window INTC short interest +44.0%, AMD +1.1%.
**Data-quality flag:** days to cover exactly 1.0 on 6/24 INTC dates and 9/24 AMD dates (probable source floor).

**Pre-registered tests, publication-date alignment (main), Spearman, n = 23, critical |ρ| at 5% = 0.413,
Bonferroni threshold p < 0.01:**

| question | x | y | ρ | p |
|---|---|---|---|---|
| Q1 | SI change INTC | spread change | −0.145 | 0.508 |
| Q1 | SI change AMD | spread change | 0.099 | 0.654 |
| Q2 | SI change INTC − AMD | spread change | −0.276 | 0.203 |
| Q3 | SI change INTC | max abs daily return | 0.068 | 0.757 |
| Q3 | SI change AMD | max abs daily return | −0.099 | 0.654 |

→ **No test significant**, at 5% or after Bonferroni.

**Settlement-date alignment (descriptive only, no inference):** Q1 INTC ρ = 0.386 (p = 0.069), Q1 AMD ρ = −0.184
(p = 0.401), **Q2 ρ = 0.577 (p = 0.004)**, Q3 INTC ρ = 0.162 (p = 0.460), Q3 AMD ρ = −0.134 (p = 0.541).
The Q2 value is a contemporaneous co-movement (INTC short interest rising relative to AMD's in periods when INTC
outperforms), not observable in real time; at publication dates it disappears (ρ = −0.276). It was not a
pre-registered inferential test, it is one of 10 correlations computed, and it comes from 23 points in one year:
recorded as a hypothesis for other data, not as a finding.

**Reading:** with short interest aligned to when it becomes public, nothing lines up with the spread or with large
moves in this window; the power to detect anything below |ρ| ≈ 0.41 is very low.

---

## 2026-10-10 15:18 CEST — Phase 5 pre-registration: joint block bootstrap (written BEFORE computing)

**Type:** simulation. No new attempt on real data: IS backtest counter stays at 11, OOS access counter at 1.
Simulations are counted separately: **simulation runs: 1 (500 paths)** once executed.

**Why a block bootstrap and not an Ornstein–Uhlenbeck process.** The brief suggests simulating the spread as an OU
process when Phase 2 indicates mean reversion. Ours indicates the opposite (IS Engle–Granger p = 0.975, half-life
≈ 6,700 trading days ≈ 27 years; OOS EG p = 0.60). An OU calibrated on this spread would either be close to a random
walk or impose a mean reversion the data reject. The joint block bootstrap makes no assumption of mean reversion and
keeps the daily joint behaviour of the two stocks.

**Design (fixed now).**
- Data: daily **log** returns of INTC and AMD over the full history 1980-03-17 … 2026-10-09 (11,736 returns;
  legitimate, the OOS has already been used).
- Joint **moving block** bootstrap: block length **20** trading days; each block starts at a uniformly random day among
  all valid starts (overlapping blocks allowed); the **same block of dates** is used for both stocks, so the daily
  correlation is preserved. Blocks are concatenated and the last one truncated to the real length.
  **500 paths, seed 2026**, path length = real history. Prices are rebuilt from the real prices of 1980-03-17 as
  `P_0 · exp(cumsum(log returns))`; the real dates are used as labels only.
- On every path, exactly the Phase 2 procedure: split at the **same position as the real split** (day index 8,273
  of 11,737, i.e. 70.5%, so IS/OOS lengths match the real ones and Sharpe ratios are comparable); β by OLS on log
  prices of the simulated IS; Engle–Granger test on the simulated IS; main configuration e = 2.0, L = 60, `shift(1)`,
  5 bp per leg on the simulated IS (evaluation from the first day with an L = 120 z-score, as in Phase 2) and on the
  simulated OOS with β frozen (z-score warm-up from the last IS days, starting flat).
- Computation run once; the per-path table is saved to `data/processed/simulation_paths.pkl` with its parameters
  (seed, block length, number of paths, split index); the notebook reloads it and recomputes only if the parameters
  differ.

**Interpretation (declared now).**
1. The bootstrap keeps the daily correlation but destroys any long-run link beyond 20 days: the paths represent the
   hypothesis "two correlated stocks **without** a stable relationship". If the real Sharpe cannot be distinguished
   from this distribution, the behaviour of the real pair is compatible with the absence of a relationship.
2. The bootstrap also keeps each stock's average drift, so the long-run trend of the ratio (AMD's average
   outperformance over the full history) is preserved on average; what is lost is the order in which things happened.
3. Any very short-term mean reversion within a 20-day block survives, but the strategy works on a longer horizon
   (L = 60, average trade ≈ 45 days), exactly the scale that the bootstrap reshuffles.
4. A real Sharpe in the **lower** tail would mean the real pair did worse than correlated stocks with no relationship,
   e.g. because of persistent trends in the real spread.

**Outputs:** distribution of the net Sharpe on simulated IS and OOS; share of paths with Sharpe > 0; percentile of the
real net Sharpe (Phase 2: −0.27 IS; OOS access #1: −0.18; exact unrounded values recomputed with the same code) in
those distributions; distribution of the Engle–Granger p-value across paths (and share with p < 0.05), compared with
the real IS value 0.975.

---

## 2026-10-10 15:35 CEST — Phase 5 results: joint block bootstrap (design as pre-registered at 15:18)

**Simulation runs: 1 (500 paths).** IS backtest counter 11 and OOS access counter 1, unchanged.
**Code:** `src/pairs/simulation.py`, `scripts/run_simulation.py` (single run: 500 paths in 735 s, 15:20–15:32 CEST);
tests in `tests/test_simulation.py` (incl. same dates for both stocks). **Checkpoint:**
`data/processed/simulation_paths.pkl` (parameters + data fingerprint stored). **Notebook:** `notebooks/05_simulation.ipynb`
(reloads the checkpoint; path 0 regenerated and checked against it). **Figures:** `reports/figures/05a_sharpe_bootstrap_vs_real`,
`05b_eg_pvalue_bootstrap_vs_real`, `05c_ratio_paths_bootstrap_vs_real` (.png/.html).

Real reference values recomputed with the same code: net Sharpe IS −0.2718, OOS −0.1806; Engle–Granger p IS 0.9752.

| | simulated IS net Sharpe | simulated OOS net Sharpe | simulated IS Engle–Granger p |
|---|---|---|---|
| median | 0.058 | 0.036 | 0.534 |
| 5th / 95th percentile | −0.217 / 0.321 | −0.388 / 0.461 | 0.046 / 0.975 |
| share of paths > 0 | 63.6% | 54.4% | — |
| share of paths with p < 0.05 | — | — | 5.2% |
| real value | −0.272 | −0.181 | 0.975 |
| **percentile of real** | **2.8%** | **21.0%** | **94.8%** |

Other descriptive numbers (same paths): simulated-IS β median 0.683, β ≤ 0.1 on 11.0% of paths (≤ 0 on 9.4%);
correlation between simulated IS and OOS Sharpe 0.031; median trades 128 (IS) / 55 (OOS).

**Reading:** in a world of correlated stocks without a stable relationship the strategy's Sharpe is scattered around a
slightly positive value and IS does not predict OOS. The real OOS Sharpe is well inside that distribution (21st
percentile); the real IS Sharpe is in its lower tail (2.8th percentile), consistent with persistent multi-year trends in
the real static-β spread (Phase 3: spread ≈ short AMD position) that the 20-day blocks do not preserve. The Engle–Granger
test rejects at about its nominal rate under the null (5.2%), and the real p-value is high even by the null's standards.
The percentiles are descriptive, not pre-registered hypothesis tests.

---

## 2026-10-10 16:10 CEST — Kalman extension: clarifications to the 14:05 pre-registration (BEFORE any Kalman computation)

Two points not specified at 14:05, decided now with the user before writing or running any Kalman code. Nothing else in
the 14:05 design changes.
1. **Window moments of the z-score:** `var_L(a)`, `var_L(b)`, `cov_L(a, b)` are sample moments (ddof = 1), consistent
   with the rolling standard deviation of Phase 2.
2. **Static reference on the Kalman IS window** (from day index 252 to 2012-12-31): return-based metrics (annualized
   return, volatility, Sharpe, max drawdown) from the existing Phase 2 daily returns cut to the window; trade-based
   metrics (number of trades, win rate, durations) only on trades entered on or after the first day of the window — a
   trade already open on that day is excluded and flagged. No new static backtest (no 15th IS backtest).

Known property of the pre-registered design, to be reported with the results (not a change): the z-score of day t uses
the filtered β_t, already updated with day t's prices, so the filter partly absorbs day t's deviation; this is not
look-ahead (data up to t only) but can dampen the signal compared with a prediction-error z-score.

---

## 2026-10-10 16:12 CEST — Kalman extension: 3 IS runs (IS backtests #12–#14), design as pre-registered at 14:05 + 16:10

**Period:** IS only (prices < 2013-01-01). OLS initialization on 1980-03-17 … (first 252 days); evaluation window
**1981-03-17 … 2012-12-31**, starting flat. **Code:** `src/pairs/kalman.py`; tests in `tests/test_kalman.py` (known-β
recovery, first filter step by hand, z-score vs brute force, P&L by hand, look-ahead test, OOS continuation of the IS
filter). **IS backtest counter: 11 → 14.**

| net unless stated | Kalman δ = 1e-5 | **Kalman δ = 1e-4 (main)** | Kalman δ = 1e-3 | static, same window |
|---|---|---|---|---|
| ann. return gross / net (%) | 3.05 / 2.65 | 3.39 / 2.99 | 4.55 / 4.13 | −7.62 / −7.95 |
| ann. vol (%) | 20.12 | 20.35 | 20.27 | 22.14 |
| Sharpe gross / net | 0.25 / 0.23 | 0.27 / 0.25 | 0.32 / 0.30 | −0.25 / −0.26 |
| max DD net (%) | −68.28 | −70.79 | −69.71 | −96.21 |
| trades | 124 (1 open at end) | 125 | 128 | 113 |
| win rate net (%) | 67.74 | 68.00 | 70.31 | 53.98 |
| avg / max duration (days) | 37.4 / 188 | 36.8 / 185 | 35.4 / 185 | 45.1 / 188 |
| exposure (%) | 57.80 | 57.41 | 56.44 | 63.55 |
| filtered β min / median / max | 0.166 / 0.423 / 0.899 | 0.116 / 0.383 / 0.890 | 0.023 / 0.370 / 0.846 | 1.047 (fixed) |

Static reference: existing Phase 2 daily returns cut to the window; trade metrics on trades entered from 1981-03-17
(no static trade was open on that day, so none excluded).

**Reading (IS):** hedging with the filtered, local β turns the IS result from clearly negative (Sharpe −0.26) to
positive (0.23–0.30 net), with little dependence on δ across two orders of magnitude. The filtered β (median ≈ 0.38)
is close to the Phase 3 rolling β (median 0.39), far from the static 1.047. Drawdowns remain very large (≈ −70%).
Caveats: this is in-sample; the motivation for the extension came from Phase 3, itself an IS analysis; known property of
the design — the z-score uses β_t already updated with day t's prices (not look-ahead, may dampen the signal). The main
configuration δ = 1e-4 now gets its single pre-registered OOS run, whatever this result.

---

## 2026-10-10 16:12 CEST — OOS access #2: single out-of-sample run of the Kalman strategy (written BEFORE computing)

**Frozen configuration** (pre-registered 14:05, clarified 16:10, unchanged after the IS results): Kalman filter on log
prices, V = 0.001, **δ = 1e-4**, initialized by OLS on the first 252 IS days; the filter **continues from its IS state
without re-initialization** through the OOS; only the filtered β_t; z-score with β_t applied to the whole 60-day window
(sample moments); entry ±2.0, exit at zero crossing, direct flip, no stop-loss; `shift(1)`; P&L with β_t; 5 bp per leg
per position change; rf = 0.
**Period:** 2013-01-01 to 2026-10-09; the strategy starts **flat** on the first OOS trading day; the z-score window may
use the last 59 IS days. Static OOS reference: the existing result of OOS access #1 (no new static run).
**Commitment:** single run; no parameter changed after it; δ = 1e-5 and 1e-3 are **not** run on the OOS.
**OOS access counter: 2.**

---

## 2026-10-10 16:15 CEST — Result of OOS access #2 (Kalman δ = 1e-4) and Kalman summary

**Notebook:** `notebooks/06_kalman.ipynb`. **Figures:** `reports/figures/06a_kalman_beta_is`,
`06b_equity_kalman_vs_static_is`, `06c_equity_kalman_vs_static_oos` (.png/.html). Asserted in the notebook: the full-data
filter coincides with the IS filter on the IS days (no re-initialization); the static OOS reference reproduces OOS access
#1 (Sharpe net −0.18, 51 trades). Transparency note: the notebook was executed twice (the second time only to add a
descriptive Sharpe-uncertainty cell); the OOS run is deterministic and the frozen configuration was not changed, so both
executions give the identical result reported here.

| OOS 2013-01-02 … 2026-10-09 | Kalman δ = 1e-4 | static (OOS access #1) |
|---|---|---|
| ann. return gross / net (%) | −0.62 / −1.01 | −6.22 / −6.56 |
| ann. vol net (%) | 23.15 | 22.80 |
| Sharpe gross / net | 0.09 / 0.07 | −0.16 / −0.18 |
| max DD net (%) | −52.73 | −82.44 |
| trades | 54 | 51 (1 open at end) |
| win rate net (%) | 64.81 | 60.78 |
| avg / max duration (days) | 41.0 / 140 | 40.8 / 132 |
| exposure (%) | 63.89 | 60.05 |

Filtered β in the OOS: min 0.052, median 0.186, max 0.505, last 0.475. Approximate 95% interval of the OOS net Sharpe
(iid, Lo 2002; descriptive): Kalman −0.46 … 0.60; static −0.71 … 0.35 (13.7 years).

**Reading:** in-sample the Kalman hedge turns the static strategy's loss into a modest gain (net Sharpe 0.23–0.30,
little dependence on δ), but most of that gain is made before 1992 and drawdowns stay ≈ −70%. Out-of-sample it is better
than the static strategy (net Sharpe +0.07 vs −0.18, drawdown −53% vs −82%) but not profitable (net return −1.0% a year)
and not distinguishable from zero. Hedging with the local β removes most of the static strategy's losses — consistent
with Phase 3 (the static spread is mostly an AMD position) — without revealing a tradable mean-reverting relationship.
Known property of the pre-registered design reported with the results: the z-score uses β_t already updated with day t's
prices, which may dampen the signal relative to a prediction-error z-score.

---

# Appendix: second pair (KO/PEP)

This appendix does **not** replace INTC/AMD, which remains the pair of the project. It has its own counters; the
project counters above are unaffected.

Appendix counters
- Appendix IS backtests: 0 (9 planned)
- Appendix OOS accesses: 0 (1 planned)

## 2026-10-10 17:03 CEST — Appendix pre-registration (written BEFORE downloading or looking at any KO/PEP price)

**Disclosure.** This second pair was added **after** seeing the negative result on INTC/AMD, to test the pipeline on a
pair with an economic reason to be cointegrated. KO/PEP was chosen because the brief names it "the classic textbook
pair", not because of its results, which have not been looked at. Prior knowledge: the user has no information on the
recent performance of the two companies.

**Design (fixed now, identical to the main project; Phases 1–2 only).**
- Pair: **A = KO, B = PEP** (order fixed now, will not be inverted). Regression `log P_KO = α + β · log P_PEP + ε`.
- Data: Yahoo Finance via yfinance, `period="max"`, `interval="1d"`, `auto_adjust=True`, saved in `data/raw/`
  (`KO_daily_yahoo.pkl`, `PEP_daily_yahoo.pkl`, metadata `prices_metadata_KO_PEP.json`).
- Split: same rule — 70% of the common history (dates where both have a close), rounded to the nearest 1 January;
  computed showing **only dates**. IS = dates < split, OOS = dates ≥ split.
- Spread and signal: OLS on log prices estimated on the IS only; ADF and Engle–Granger on the IS; main configuration
  e = 2.0, L = 60, exit at zero crossing, direct flip, no stop-loss, `shift(1)`, 5 bp per leg per position change, rf = 0;
  same metrics as Phase 2. IS evaluation window from the first day with an L = 120 z-score, as in Phase 2.
- Grid 3×3 (e ∈ {1.5, 2.0, 2.5} × L ∈ {20, 60, 120}) on the IS only, as a sensitivity measure; the main configuration
  stays e = 2.0, L = 60 whatever the result. **9 appendix IS backtests** (the grid includes the main configuration);
  no other check (no lag-2 or price-level run).
- **One OOS run** of the main configuration with β frozen from the IS, starting flat on the first OOS day, whatever the
  IS result. **1 appendix OOS access.**
- No Phases 3–5 and no Kalman for KO/PEP: this is only a test of the Phase 1–2 pipeline.
- Charts: prices (log scale) and the KO/PEP ratio up to the split only, until the OOS run; full-history versions with
  the split line added after the OOS run, leaving the IS versions unchanged.

**Code changes allowed:** generalizations with defaults identical to the current behaviour (tickers as parameters).
Control: after any change, all tests and notebooks 01–06 are re-executed on a temporary copy of the project and their
outputs and PNGs compared with the committed ones; any difference stops the work.

## 2026-10-10 17:08 CEST — Appendix: code generalization check, KO/PEP download and split date (dates only)

**Code changes** (defaults unchanged): `run_strategy` gained `ticker_a`/`ticker_b` (default INTC/AMD), passed to
`compute_spread` and `run_backtest`; new test `test_run_strategy_with_other_tickers_matches_default`.
`scripts/fetch_prices.py` gained `--tickers`/`--meta` (defaults INTC AMD / `prices_metadata.json`) and now refuses to
overwrite existing raw files or metadata; `scripts/compute_split_date.py` gained `--tickers` (default INTC AMD).

**INTC/AMD unchanged — control result.** pytest: 94 passed. Notebooks 00, 01, 02, 02c, 03, 04, 05, 06 re-executed on a
temporary copy of the project (code of the copy imported via PYTHONPATH, figures written inside the copy; the committed
notebooks and figures were not touched). All 22 PNG files byte-identical to the committed ones; all embedded images
identical; all text outputs identical except one pre-existing pandas `UserWarning` in `02_signal` whose text contains
the name of the kernel's temporary file (`ipykernel_24568` vs `ipykernel_29328`, different at every execution); after
normalizing that file name, all text outputs of all 8 notebooks are identical. A first attempt of the control failed
to execute (the notebooks' kernel ran outside the project environment: `No module named 'pandas'`); it produced no
outputs and was re-run with `uv run`.

**KO/PEP data:** Yahoo Finance via yfinance 1.7.0, `auto_adjust=True`. KO: 16,302 rows, 1962-01-02 … 2026-10-09;
PEP: 13,703 rows, 1972-06-01 … 2026-10-09. Files `data/raw/KO_daily_yahoo.pkl`, `data/raw/PEP_daily_yahoo.pkl`,
`data/raw/prices_metadata_KO_PEP.json`. Only dates and row counts were printed.

**Split (same 70% rule, only dates shown):**

| Item | Value |
|---|---|
| First common date | 1972-06-01 |
| Last common date | 2026-10-09 |
| Common trading days | 13,703 |
| 70% point (trading days) | 2010-06-08 → 2010-01-01 |
| 70% point (calendar) | 2010-06-19 → 2010-01-01 |
| **Split date** | **2010-01-01** |
| IS (1972-06-01 … 2009-12-31) | 9,485 days (69.2%) |
| OOS (2010-01-01 … 2026-10-09) | 4,218 days (30.8%) |

The two methods agree: **KO/PEP split = 2010-01-01**.

## 2026-10-10 17:10 CEST — Appendix: KO/PEP in-sample results (appendix IS backtests #1–#9)

**Period:** IS, 1972-06-01 … 2009-12-31 (9,485 common days; 2,599 KO-only days before 1972-06-01 dropped by the
alignment). Evaluation window 1972-11-20 … 2009-12-31 (first day with an L = 120 z-score). No OOS data loaded.
**Notebook:** `notebooks/appendix_kopep.ipynb` (IS part). **Figures:** `reports/figures/appx_a_kopep_prices_ratio_is`,
`appx_b_kopep_spread_is`, `appx_c_kopep_sharpe_heatmap_is`, `appx_d_kopep_equity_is` (.png/.html).
**Appendix IS backtest counter: 9** (the pre-registered grid; nothing else run).

**Hedge regression (log prices):** α = −0.5909, β = 0.9805 (> 0, PEP acts as a hedge), R² = 0.9753.
**Stationarity of the IS spread:** ADF stat −2.156, p = 0.223 (16 lags); Engle–Granger stat −2.156, p = 0.447.
Descriptive: AR(1) b = −0.00180, half-life ≈ 386 trading days. → **No significant evidence of cointegration at 5%
over 1972–2009**, although far closer to it than INTC/AMD (EG p 0.447 vs 0.975; half-life ≈ 1.5 years vs ≈ 27).

**Grid (net unless stated):**

| e | L | ann. ret gross / net (%) | vol (%) | Sharpe gross / net | max DD net (%) | trades | win rate net (%) | avg / max dur. | exposure (%) |
|---|---|---|---|---|---|---|---|---|---|
| 1.5 | 20 | 10.32 / 8.76 | 10.69 | 0.97 / 0.84 | −23.09 | 530 | 75.85 | 11.2 / 76 | 63.39 |
| 1.5 | 60 | 7.03 / 6.37 | 10.68 | 0.69 / 0.63 | −20.48 | 229 | 79.48 | 26.2 / 173 | 64.06 |
| 1.5 | 120 | 5.11 / 4.72 | 10.57 | 0.52 / 0.49 | −21.45 | 136 | 77.21 | 44.8 / 201 | 65.09 |
| 2.0 | 20 | 9.21 / 8.18 | 9.24 | 1.00 / 0.90 | −20.57 | 351 | 77.49 | 12.0 / 72 | 45.13 |
| **2.0** | **60** | **5.75 / 5.28** | **9.82** | **0.62 / 0.57** | **−19.50** | **166** | **77.71** | **30.0 / 172** | **53.17** |
| 2.0 | 120 | 4.10 / 3.81 | 9.89 | 0.46 / 0.43 | −21.45 | 102 | 77.45 | 51.3 / 201 | 55.92 |
| 2.5 | 20 | 4.82 / 4.40 | 6.39 | 0.77 / 0.71 | −19.50 | 151 | 76.16 | 12.9 / 60 | 20.81 |
| 2.5 | 60 | 4.04 / 3.76 | 7.98 | 0.54 / 0.50 | −24.81 | 101 | 77.23 | 32.1 / 172 | 34.60 |
| 2.5 | 120 | 2.62 / 2.45 | 8.54 | 0.35 / 0.33 | −26.70 | 63 | 77.78 | 60.1 / 200 | 40.40 |

Every configuration has one trade open on 2009-12-31 (checked: a short-spread position entered in Nov–Dec 2009 in all
nine; with L = 20 the exit signal comes on 2009-12-31 itself and would execute in 2010), closed there for the trade
statistics.

**Reading (IS):** unlike INTC/AMD, the main configuration earns in-sample (net Sharpe 0.57, +5.3% a year, max drawdown
−19.5%) and **all nine** configurations are positive (net Sharpe 0.33–0.90): the result is not fragile to the
parameters; shorter lookbacks do better. This happens although the Engle–Granger test does not reject at 5%: the spread
wanders in multi-year swings (half-life ≈ 1.5 years), but the rolling z-score captures shorter-term reversion around
them. The main configuration now gets its single OOS run, whatever this result.

## 2026-10-10 17:10 CEST — Appendix OOS access #1: single OOS run of KO/PEP (written BEFORE computing)

**Frozen configuration:** log prices; β = 0.9805 estimated on the KO/PEP IS (dates < 2010-01-01) and not
re-estimated; e = 2.0, L = 60, exit at zero crossing, direct flip, no stop-loss; `shift(1)`; 5 bp per leg per position
change; rf = 0. **Period:** 2010-01-01 to the last available date (2026-10-09); the z-score may use the last 59 IS days
as warm-up; the strategy starts **flat** on the first OOS trading day. **Commitment:** single run, no parameter changed
after it; the other grid configurations are not run on the OOS. Afterwards (descriptive only): ADF / Engle–Granger on
the OOS spread, and full-history versions of the price and ratio charts with the split line.
**Appendix OOS access counter: 1.**

## 2026-10-10 17:12 CEST — Appendix: result of OOS access #1 (KO/PEP) and summary

**Notebook:** `notebooks/appendix_kopep.ipynb` (sections 4–5 appended; IS cells unchanged, IS PNGs byte-identical after
re-execution). **Figures:** `reports/figures/appx_e_kopep_equity_oos`, `appx_f_kopep_prices_ratio_full` (.png/.html).
Transparency note: the notebook was executed twice after the OOS section was added — the second time only to fix the
y-axis ticks of the OOS equity chart (they fell outside the data range). The OOS run is deterministic and the frozen
configuration was not changed; all table outputs were checked identical between the two executions.

| e = 2.0, L = 60, lag 1 | IS (1972-11-20 … 2009-12-31) | OOS (2010-01-04 … 2026-10-09) |
|---|---|---|
| ann. return gross / net (%) | 5.75 / 5.28 | −0.99 / −1.35 |
| ann. vol net (%) | 9.82 | 5.60 |
| Sharpe gross / net | 0.62 / 0.57 | −0.15 / −0.21 |
| max DD gross / net (%) | −19.42 / −19.50 | −27.16 / −28.39 |
| trades | 166 (1 open at end) | 62 (1 open at end) |
| win rate net (%) | 77.71 | 62.90 |
| avg / max duration (days) | 30.0 / 172 | 41.0 / 121 |
| exposure (%) | 53.17 | 60.24 |

**Descriptive OOS tests:** ADF on the OOS spread with the frozen β: stat −0.124, p = 0.947 (9 lags); Engle–Granger on OOS
log prices (own β): stat 0.533, p = 0.993.

**Reading:** KO/PEP is not cointegrated at 5% in the IS (EG p = 0.447), but the main configuration earns in-sample and
the whole 3×3 grid is positive (net Sharpe 0.33–0.90). The single OOS run loses (net Sharpe −0.21, −1.35% a year,
max drawdown −28%): roughly flat to positive until 2021, then the largest losses in 2025–2026, while the KO/PEP ratio
rose sharply and the strategy was short the spread. The pipeline therefore does produce in-sample profits on a pair
whose spread reverts on short horizons (and recovers genuine cointegration on synthetic data), so the INTC/AMD failure
is not a pipeline artefact; and a robust IS grid on the textbook pair still did not survive its single OOS test. No
INTC/AMD conclusion changes. Appendix counters at the end: **9 IS backtests, 1 OOS access** (as planned).

## 2026-10-10 17:24 CEST — Appendix pre-registration: Phase 3 and Phase 5 diagnostics for KO/PEP (BEFORE computing)

**Disclosure.** These analyses were decided **after** seeing the KO/PEP IS and OOS results, to explain the
out-of-sample decay (net Sharpe 0.57 IS vs −0.21 OOS) and to check whether the IS Sharpe can be distinguished from that
of two correlated stocks without a relationship. They are diagnostics, not strategy attempts: **no new strategy
backtest and no new OOS access** (appendix counters stay at 9 IS backtests and 1 OOS access). Simulations are counted
separately: **appendix simulation runs: 1** once executed.

**Phase 3 (identical methods and parameters to INTC/AMD, 13:20 pre-registration):** on log prices of the **full**
KO/PEP history 1972-06-01 … 2026-10-09 (legitimate: the OOS has been used), rolling OLS β over W = 252 days; rolling
ADF every 21 days on the window's spread with the window's own β (constant, AIC lags); weak = ADF p > 0.05; the flag
of day t uses data up to t − 1. Charts with the 2010-01-01 split line. Weak vs strong comparison of the main
configuration's **net daily returns already computed** (IS run 1972-11-20 … 2009-12-31, OOS run 2010-01-04 … 2026-10-09),
**separately for IS and OOS**: days, share, exposure, mean daily return, annualized return, Sharpe, max drawdown
(stitched), trades by entry-day flag and net win rate, Welch t-test on mean daily net return (all days, approximate).
Days/trades without a flag are excluded and counted. Same declared limitations as for INTC/AMD (optimistic p-value
with in-window β; low power with 252 days; overlapping windows; the flag says whether a local relationship exists,
not whether the static-β spread is stationary).

**Phase 5 (identical to the 15:18 pre-registration):** joint moving-block bootstrap of the daily log returns of KO and
PEP over the full common history (13,702 returns), block 20, the same dates for both stocks, **500 paths, seed 2026**,
real length, prices rebuilt from the real 1972-06-01 prices; split at the **same position as the real KO/PEP split**
(row 9,485); on each path: OLS β on the simulated IS, Engle–Granger on the simulated IS, main configuration (e = 2.0,
L = 60, `shift(1)`, 5 bp/leg; IS from the first L = 120 z-score day; OOS with β frozen, starting flat) on simulated IS
and OOS. Outputs: distributions and percentiles of the real net Sharpe (IS 0.57, OOS −0.21; exact values recomputed)
and of the real IS Engle–Granger p (0.447). **If the computation exceeds 20 minutes, the first 200 paths are used**
(same seed, so they are the first 200 of the 500) and this is declared. Checkpoint:
`data/processed/simulation_paths_KO_PEP.pkl`. Same interpretation as for INTC/AMD (correlated stocks without a stable
relationship beyond 20 days; drifts kept; a real Sharpe in the upper tail would mean the IS profit is unlikely to be
produced by such a world).

**Code changes allowed:** ticker parameters with INTC/AMD defaults; INTC/AMD results re-checked on a temporary copy as
before; any change stops the work.

## 2026-10-10 17:37 CEST — Appendix: KO/PEP Phase 3 and Phase 5 diagnostics, results (design as pre-registered at 17:24)

**Counters:** appendix IS backtests 9, appendix OOS accesses 1 (unchanged; no new strategy run); **appendix simulation
runs: 1 (500 paths)**.
**Code changes:** `run_simulated_path`, `simulate`, `load_or_simulate` gained `ticker_a`/`ticker_b` (defaults INTC/AMD;
`BootstrapParams` and the checkpoint fingerprint unchanged); `scripts/run_simulation.py` gained `--tickers`, `--split`,
`--cache`, `--n-paths` (defaults unchanged); new test `test_run_simulated_path_with_other_tickers_matches_default`.
**INTC/AMD control:** pytest 95 passed; notebooks 00–06 re-executed on a temporary copy: all text outputs identical (kernel
temporary file names normalized), all embedded images identical, all 22 PNGs byte-identical ("ALL IDENTICAL"); notebook 05
reloaded the INTC/AMD checkpoint without recomputing.
**Simulation:** `scripts/run_simulation.py --tickers KO PEP --split 2010-01-01 --cache simulation_paths_KO_PEP.pkl`,
500 paths in 543 s (< 20 min, so all 500 paths used). Checkpoint `data/processed/simulation_paths_KO_PEP.pkl`.
**Notebook:** sections 6–7 of `notebooks/appendix_kopep.ipynb`. **Figures:** `reports/figures/appx_g_kopep_rolling_beta`,
`appx_h_kopep_rolling_adf`, `appx_i_kopep_sharpe_bootstrap_vs_real` (.png/.html). Transparency note: executing the
notebook re-ran the earlier sections, including the deterministic OOS run of the frozen configuration; the six earlier
appendix PNGs are byte-identical and all tables of sections 1–5 are identical to the previous execution.

**Phase 3 (full history, 641 rolling ADF windows 1973-06-04 … 2026-09-24):**

| | IS (to 2009-12-31) | OOS (from 2010-01-01) |
|---|---|---|
| rolling β median (5th / 95th pct) | 0.703 (0.003 / 1.318) | 0.651 (−0.117 / 1.357) |
| % days with rolling β ≤ 0.1 | 8.6 | 9.7 |
| weak share of flagged days | 68.8% (of 9,233) | 80.1% (of 4,218) |

Weak share by decade: 62.1% (1970s), 61.8% (1980s), 67.6% (1990s), 81.6% (2000s), 72.5% (2010s), 91.4% (2020–2026).

Weak vs strong days, main configuration (already computed daily net returns):

| | days | share | exposure | mean daily net | ann. return | Sharpe | max DD (stitched) | trades | win rate net |
|---|---|---|---|---|---|---|---|---|---|
| IS weak | 6356 | 68.84% | 55.62% | 2.72 bp | 6.54% | 0.67 | −17.26% | 105 | 80.95% |
| IS strong | 2877 | 31.16% | 48.56% | 1.05 bp | 2.26% | 0.29 | −23.95% | 58 | 70.69% |
| OOS weak | 3378 | 80.09% | 63.56% | −0.77 bp | −2.09% | −0.33 | −29.78% | 48 | 58.33% |
| OOS strong | 840 | 19.91% | 46.90% | 0.69 bp | 1.66% | 0.40 | −4.71% | 14 | 78.57% |

Welch (weak − strong): IS t = 1.25, p = 0.210 (excluded without a flag: 133 days, 3 trades); OOS t = −1.28, p = 0.199
(none excluded). Approximate p-values.

**Phase 5 (500 paths, seed 2026, block 20, split row 9,485):**

| | simulated IS net Sharpe | simulated OOS net Sharpe | simulated IS Engle–Granger p |
|---|---|---|---|
| median | 0.324 | 0.321 | 0.391 |
| 5th / 95th percentile | 0.074 / 0.578 | −0.083 / 0.665 | 0.047 / 0.922 |
| share of paths > 0 | 98.2% | 90.0% | — |
| share of paths with p < 0.05 | — | — | 5.4% |
| real value | 0.573 | −0.215 | 0.447 |
| **percentile of real** | **94.4%** | **1.8%** | **55.0%** |

**Reading:** the KO/PEP relationship is weak most of the time and weakens further over time (82% weak days in the 2000s,
91% in 2020–2026); the weak/strong flag does not separate the strategy's results reliably (opposite signs IS vs OOS,
neither significant). In a bootstrap world without a stable relationship the strategy already earns on this pair
(median IS Sharpe 0.32); the real IS Sharpe (0.57) is near the top of that distribution but inside it (94.4th
percentile), so the IS profit is not evidence of a long-run relationship. The real OOS Sharpe (−0.21) is at the 1.8th
percentile: worse than almost all no-relationship paths, consistent with a persistent trend in the spread (2025–2026)
longer than the 20-day blocks. Diagnostics decided after seeing the results; percentiles are descriptive; nothing was
changed in the strategy.

---

# INTC/AMD: look-elsewhere analysis

## 2026-10-10 18:37 CEST — Pre-registration: look-elsewhere effect on INTC/AMD (written BEFORE computing)

**Scope:** INTC/AMD only; nothing of the KO/PEP appendix is touched. This is a simulation, not a strategy attempt:
INTC/AMD counters stay at **14 IS backtests and 2 OOS accesses**; INTC/AMD **simulation runs: 1 → 2** once executed.

**Disclosure.** The window 1997-01-01 … 2004-12-31 was chosen **a posteriori**, by looking at the INTC/AMD price charts
(the user's idea, prompted by the impression that the two stocks looked linked in that period). The purpose is to
measure how easily such a window appears **by chance** when one searches a long history for it, not to propose it as a
trading period.

**Real window (INTC/AMD):** prices from 1997-01-01 to 2004-12-31 only. On this window alone: β by OLS on the window's
log prices (deliberate look-ahead within the window: it is what someone fooled by the window would do), Engle–Granger
p-value (same `stationarity_tests` function), and the net Sharpe of the main configuration (e = 2.0, L = 60, `shift(1)`,
5 bp per leg, exit at zero, direct flip, no stop-loss), with prices restricted to the window and evaluated from the
window's first day with an L = 120 z-score (window row 119), starting flat.

**Null world:** the same 500 paths of the INTC/AMD Phase 5 bootstrap, regenerated with the same seed (2026) and block
(20); they are checked against `data/processed/simulation_paths.pkl` (the simulated-IS β recomputed on every path must
equal the stored one). On each path: windows with the **same length in trading days as the real window**, starting at
rows 0, 252, 504, … as long as the window fits in the path; on each window exactly the same procedure (β in the window,
Engle–Granger, net Sharpe from window row 119).

**Outputs:**
(a) share of single windows with Engle–Granger p < 0.05 (expected ≈ 5%);
(b) share of paths containing **at least one** window with p < 0.05;
(c) share of paths containing at least one window with p ≤ real p **and** Sharpe ≥ real Sharpe (same window);
(d) distribution of the best window's net Sharpe per path, with the real window's value.

**Run time:** if the estimate exceeds 20 minutes, only the first 200 paths are used (same seed, so they are the first
200 of the 500) and this is declared. Checkpoint: `data/processed/look_elsewhere_windows.pkl`.

## 2026-10-10 19:06 CEST — Result: look-elsewhere effect on INTC/AMD (design as pre-registered at 18:37)

**Counters:** INTC/AMD IS backtests 14 and OOS accesses 2 (unchanged); INTC/AMD **simulation runs: 2** (Phase 5; this
look-elsewhere run). KO/PEP appendix untouched.
**Run time and paths:** estimated ≈ 45 min for 500 paths (0.137 s per window × 39 windows × 500) > 20 min, so **the first
200 paths were used**, as pre-registered. Actual run: 200 paths × 39 windows = 7,800 windows of **2,013 trading days**
(the real window's length), starts every 252 rows, 1,336 s (`scripts/run_look_elsewhere.py`). All 200 regenerated paths
matched the Phase 5 table (simulated-IS β identical on every path; checked inside the run).
**Code:** new functions `window_starts`, `evaluate_window`, `look_elsewhere`, `look_elsewhere_summary` in
`src/pairs/simulation.py` (existing functions unchanged); 4 new tests in `tests/test_simulation.py` (99 tests in total).
**Notebook:** new section "Look-elsewhere effect" at the end of `notebooks/05_simulation.ipynb`. **Figures:**
`reports/figures/05d_lookelsewhere_spread_1997_2004`, `05e_lookelsewhere_best_window_sharpe` (.png/.html).

**Control that no existing result changed.** (1) Before computing, notebooks 00–06 re-executed on a temporary copy: all
22 PNGs byte-identical, all embedded images identical, all text outputs identical except in `02_signal`, where one cell's
log lines (stderr) and printed line (stdout) arrived in a different order; compared separately per stream, all 29 cells of
`02_signal` are identical (no number changed). (2) After adding the section, `05_simulation.ipynb` was executed in place:
its 15 pre-existing cells are identical to the committed version (source, outputs per stream, results, images); PNGs
05a–05c byte-identical; the three HTML files differ only in Plotly's random element ids. Two execution attempts failed
before writing the notebook with a transient Windows file lock on a PNG (`OSError: [Errno 22]`, the same issue seen
earlier today); the files written meanwhile were byte-identical. One more execution was done only to widen the x-axis of
the 05e histogram (the real-value line sat on the axis edge); all outputs were re-checked afterwards.

**Real window 1997-01-02 … 2004-12-31 (chosen a posteriori):** in-window β = 0.4799 (R² 0.406), Engle–Granger
p = **0.5118**, net Sharpe of the main configuration with the in-window β = **0.222**.

| output | value |
|---|---|
| (a) single null windows with Engle–Granger p < 0.05 | **5.8%** (of 7,800) |
| (b) null paths with at least one window p < 0.05 | **78.5%** |
| (c) null paths with a window as good as the real one (p ≤ 0.5118 and Sharpe ≥ 0.222) | **99.5%** |
| (d) best-window net Sharpe per null path: median [5th, 95th pct] | **0.80 [0.48, 1.17]** |
| (d) percentile of the real Sharpe among the best windows | **0.0%** |

**Reading:** the window picked by eye is not cointegrated (p = 0.51) and its in-window Sharpe (0.22) is below the best
window of every null path. In a world without a stable relationship, a single window passes the test about 5% of the time,
but searching ~39 windows of a history this long finds at least one "cointegrated" window in 78.5% of histories, and the
best window typically shows a net Sharpe around 0.8. The impression of a 1997–2004 link is what chance routinely produces
when a long history is searched. Caveats: 200 of 500 paths; starts every 252 days (a finer search would raise (b) and
(d)); the null is the Phase 5 bootstrap world.

---

# Final repository clean-up

## 2026-10-10 19:20 CEST — Planned descriptive additions (declared BEFORE computing them)

No new backtest, no OOS access, no simulation run; counters unchanged (INTC/AMD: 14 IS backtests, 2 OOS accesses,
2 simulation runs; KO/PEP appendix: 9 IS backtests, 1 OOS access, 1 simulation run). Purely descriptive additions,
computed from data and results already used:
1. KO/PEP appendix: chart of the IS z-score of the main configuration (L = 60, ±2 thresholds), as for INTC/AMD.
2. Notebook 01: the IS return-correlation table recomputed with log returns, next to the simple-return table.
3. Notebook 02: a two-panel chart (same y-axis) of the rolling z-score (L = 60) of the INTC/AMD IS spread and of the
   synthetic negative control's spread (random-walk residual, seed 2026, `pairs.synthetic`), with explanatory text;
   and a text-only update of the R² bullet.
Also: docstring/comment text fixes, a README, script docstrings, and a full re-execution of all notebooks on a
temporary copy to check reproducibility. Results are recorded in a closing entry.

## 2026-10-10 19:29 CEST — Clean-up results (descriptive additions, no new attempt)

Counters unchanged (INTC/AMD: 14 IS backtests, 2 OOS accesses, 2 simulation runs; KO/PEP appendix: 9, 1, 1).

**Descriptive additions:**
- `notebooks/appendix_kopep.ipynb`: IS z-score chart of the main configuration (L = 60, ±2), inserted after the IS spread;
  figure `reports/figures/appx_j_kopep_zscore_main_is.{png,html}`.
- `notebooks/01_data.ipynb`: IS return correlations with log returns next to the simple-return table: All 0.4804 (simple
  0.4832), 1980s 0.5592 (0.5565), 1990s 0.3255 (0.3301), 2000s 0.5387 (0.5452), 2010–2012 0.5849 (0.5847); largest
  absolute difference 0.0065. Text explains why the backtest uses simple returns (additive across legs) and the bootstrap
  log returns (additive over time).
- `notebooks/02_signal.ipynb`: R² bullet of "1. Hedge regression (IS)" rewritten (text only); after the z-score chart, a
  text cell on why the rolling z-score always looks mean-reverting, and the two-panel chart "Rolling z-score: INTC/AMD vs
  a pure random-walk spread" (INTC/AMD IS spread; synthetic negative control of notebook 00, seed 2026, spread with the
  β fitted on its first half, IS half shown), figure `reports/figures/02h_zscore_intc_amd_vs_random_walk.{png,html}`.

**Text-only code changes:** generic wording in docstrings/comments of `src/pairs/spread.py`, `simulation.py`,
`synthetic.py`, `stability.py`, `scripts/compute_split_date.py` (log messages untouched). All scripts already had a
docstring with purpose and usage (KO/PEP usage example added to `compute_split_date.py`); none is superseded, nothing
moved to `archive/`. New `README.md`.

**Checks.** (1) After the additions, the pre-existing cells of notebooks 01, 02 and the appendix are identical to the
committed version (source and outputs per stream), except the edited R² markdown cell; no existing PNG changed; modified
HTML files differ only in Plotly's random element ids. Several in-place executions first failed with the transient
Windows file lock seen earlier today and succeeded on retry with unchanged code. (2) **Full reproducibility:** all 9
notebooks (00, 01, 02, 02c, 03, 04, 05, 06, appendix) re-executed from a clean kernel on a temporary copy of the project:
every cell identical to the repository (stdout and stderr compared separately), and all **35 PNGs byte-identical**
("ALL IDENTICAL"). The simulation checkpoints in `data/processed/` were reloaded, not recomputed. (3) ruff, mypy: clean;
pytest: 99 passed.
