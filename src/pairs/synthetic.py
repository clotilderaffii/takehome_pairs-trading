"""Synthetic price pairs with a known answer, for positive/negative controls of the pipeline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from pairs.backtest import StrategyRun, run_strategy
from pairs.config import TICKER_A, TICKER_B
from pairs.metrics import performance_summary
from pairs.spread import HedgeFit, StationarityResult, fit_hedge_ratio, stationarity_tests

#: Parameters of the pre-specified controls (not tuned).
SYNTH_ALPHA: float = 0.5
SYNTH_BETA: float = 0.8
SYNTH_VOL_B: float = 0.02
SYNTH_HALF_LIFE: float = 10.0
SYNTH_STATIONARY_SD: float = 0.05


def make_synthetic_pair(
    n_days: int,
    seed: int,
    mean_reverting: bool,
    start: str = "2000-01-03",
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Build prices with ``log P_A = alpha + beta · log P_B + s_t`` and a chosen residual ``s_t``.

    Parameters
    ----------
    n_days : int
        Number of business days.
    seed : int
        Seed of the random generator (results are fully reproducible).
    mean_reverting : bool
        True (positive control): ``s_t`` is a discretized Ornstein-Uhlenbeck / AR(1) process
        with half-life 10 days and stationary standard deviation 0.05. False (negative
        control): ``s_t`` is a random walk with the *same* daily innovations, so there is no
        stable relationship.
    start : str, optional
        First business day of the index.
    ticker_a, ticker_b : str, optional
        Column names, so the same pipeline functions run unchanged.

    Returns
    -------
    pd.DataFrame
        Columns ``[ticker_a, ticker_b]`` of strictly positive prices on a business-day index.

    Notes
    -----
    ``log P_B`` is a random walk with daily volatility 2%, starting at ``ln 20``. The AR(1)
    coefficient is ``phi = 2^(−1/10)`` (half-life 10 days) and the innovation standard
    deviation is ``0.05 · sqrt(1 − phi²)``, so the stationary sd of ``s_t`` is 0.05; ``s_0``
    is drawn from the stationary distribution. In the negative control ``s_t`` cumulates the
    same innovations (``s_0 = 0``).
    """
    rng = np.random.default_rng(seed)
    log_b = math.log(20.0) + np.cumsum(rng.normal(0.0, SYNTH_VOL_B, n_days))

    phi = 2.0 ** (-1.0 / SYNTH_HALF_LIFE)
    sigma_eps = SYNTH_STATIONARY_SD * math.sqrt(1.0 - phi**2)
    eps = rng.normal(0.0, sigma_eps, n_days)
    s = np.empty(n_days)
    if mean_reverting:
        s[0] = rng.normal(0.0, SYNTH_STATIONARY_SD)
        for t in range(1, n_days):
            s[t] = phi * s[t - 1] + eps[t]
    else:
        s[0] = 0.0
        s[1:] = np.cumsum(eps[1:])

    log_a = SYNTH_ALPHA + SYNTH_BETA * log_b + s
    idx = pd.bdate_range(start, periods=n_days)
    prices = pd.DataFrame({ticker_a: np.exp(log_a), ticker_b: np.exp(log_b)}, index=idx)
    assert (prices > 0).to_numpy().all() and not prices.isna().to_numpy().any()
    return prices


@dataclass(frozen=True)
class ControlResult:
    """Output of :func:`run_pipeline_control`.

    Attributes
    ----------
    fit : HedgeFit
        Hedge regression on the IS half.
    tests : StationarityResult
        ADF / Engle-Granger / half-life on the IS half.
    is_run, oos_run : StrategyRun
        Backtests on the IS and OOS halves (same strategy, beta frozen from IS).
    is_summary, oos_summary : dict[str, float]
        ``metrics.performance_summary`` of each run.
    split_date : date
        First OOS day.
    """

    fit: HedgeFit
    tests: StationarityResult
    is_run: StrategyRun
    oos_run: StrategyRun
    is_summary: dict[str, float]
    oos_summary: dict[str, float]
    split_date: date


def run_pipeline_control(
    prices: pd.DataFrame,
    entry: float = 2.0,
    lookback: int = 60,
    cost_bps: float = 5.0,
    lag: int = 1,
) -> ControlResult:
    """Run the project's Phase 2 pipeline on a price pair, first half IS and second half OOS.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned prices with columns ``TICKER_A`` and ``TICKER_B``.
    entry, lookback, cost_bps, lag : optional
        Strategy parameters; defaults are the frozen main configuration of Phase 2.

    Returns
    -------
    ControlResult
        Fit, tests and IS/OOS backtests with their metrics.

    Notes
    -----
    Mirrors Phase 2 and Phase 2c: ``fit_hedge_ratio`` and ``stationarity_tests`` on the IS
    half only; IS backtest from the first day with an L = 120 z-score (Phase 2 common window);
    OOS backtest with beta frozen from the IS, z-score warm-up from the last IS days, starting
    flat on the first OOS day.
    """
    split_ts = prices.index[len(prices) // 2]
    split_date = split_ts.date()
    end_all = (prices.index[-1] + pd.Timedelta(days=1)).date()

    fit = fit_hedge_ratio(prices, end=split_date)
    tests = stationarity_tests(prices, beta=fit.beta, end=split_date)
    is_from = prices.index[120 - 1].date()
    is_run = run_strategy(
        prices,
        fit.beta,
        entry=entry,
        lookback=lookback,
        end=split_date,
        trade_from=is_from,
        lag=lag,
        cost_bps=cost_bps,
    )
    oos_run = run_strategy(
        prices,
        fit.beta,
        entry=entry,
        lookback=lookback,
        end=end_all,
        trade_from=split_date,
        lag=lag,
        cost_bps=cost_bps,
    )
    assert is_run.daily.index.max() < split_ts <= oos_run.daily.index.min()
    return ControlResult(
        fit=fit,
        tests=tests,
        is_run=is_run,
        oos_run=oos_run,
        is_summary=performance_summary(is_run.daily, is_run.trades),
        oos_summary=performance_summary(oos_run.daily, oos_run.trades),
        split_date=split_date,
    )
