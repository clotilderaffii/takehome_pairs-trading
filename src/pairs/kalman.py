"""Extension: dynamic hedge ratio with a two-state Kalman filter (pre-registered 2026-10-10 14:05).

Model: ``log P_A,t = alpha_t + beta_t · log P_B,t + eps_t``, ``eps_t ~ N(0, V)``; the state
``(alpha_t, beta_t)`` follows a random walk with covariance ``W = delta / (1 − delta) · I``.
Only the *filtered* state (data up to and including t) is ever computed; there is no smoother.
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pairs.backtest import DEFAULT_COST_BPS, StrategyRun, extract_trades
from pairs.config import TICKER_A, TICKER_B
from pairs.exceptions import InsufficientDataError
from pairs.metrics import performance_summary
from pairs.signal import positions_from_zscore
from pairs.spread import log_prices

logger = logging.getLogger(__name__)

#: Observation noise variance (Chan, 2013), pre-registered, not optimized.
KALMAN_V: float = 0.001
#: Main configuration of the transition parameter delta, pre-registered.
KALMAN_DELTA_MAIN: float = 1e-4
#: Sensitivity values of delta, pre-registered (3 IS attempts).
KALMAN_DELTAS: tuple[float, ...] = (1e-5, 1e-4, 1e-3)
#: Days used for the OLS initialization (excluded from evaluation).
KALMAN_INIT_WINDOW: int = 252


def kalman_filter(
    prices: pd.DataFrame,
    end: date,
    delta: float,
    v: float = KALMAN_V,
    init_window: int = KALMAN_INIT_WINDOW,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Run the two-state Kalman filter on log prices and return the filtered state.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    end : date
        Exclusive cutoff, applied first.
    delta : float
        Transition parameter: state noise covariance ``W = delta / (1 − delta) · I``.
    v : float, optional
        Observation noise variance V.
    init_window : int, optional
        Number of initial days used for the OLS initialization.
    ticker_a, ticker_b : str, optional
        Dependent (A) and explanatory (B) legs.

    Returns
    -------
    pd.DataFrame
        Columns ``alpha``, ``beta`` (filtered, data up to and including t), ``innovation``
        (``y_t − ŷ_{t|t−1}``) and ``innovation_var``; NaN on the ``init_window`` OLS days.

    Raises
    ------
    InsufficientDataError
        If there are not more than ``init_window`` days before ``end``.

    Notes
    -----
    Initial state mean = OLS (alpha, beta) on the first ``init_window`` days; initial state
    covariance = the OLS coefficient covariance ``σ²(XᵀX)⁻¹`` of the same regression. From
    day ``init_window`` (0-based) on, each day: predict ``P ← P + W`` (the state mean is
    unchanged), then update with that day's observation:
    ``e = y − Hx``, ``S = H P Hᵀ + V``, ``K = P Hᵀ / S``, ``x ← x + K e``,
    ``P ← P − K H P`` with ``H = [1, log P_B,t]``.
    """
    assert 0 < delta < 1 and v > 0
    cut = prices[prices.index < pd.Timestamp(end)][[ticker_a, ticker_b]]
    if len(cut) <= init_window:
        raise InsufficientDataError(f"Need more than {init_window} days before {end}.")
    logp = log_prices(cut)
    y = logp[ticker_a].to_numpy()
    xb = logp[ticker_b].to_numpy()

    ols = sm.OLS(y[:init_window], sm.add_constant(xb[:init_window])).fit()
    x = np.asarray(ols.params, dtype=float).copy()
    p = np.asarray(ols.cov_params(), dtype=float).copy()
    w = delta / (1.0 - delta) * np.eye(2)

    n = len(y)
    out = np.full((n, 4), np.nan)
    for t in range(init_window, n):
        p = p + w  # predict (random-walk state: mean unchanged)
        h = np.array([1.0, xb[t]])
        e = y[t] - h @ x
        s = float(h @ p @ h) + v
        k = (p @ h) / s
        x = x + k * e
        p = p - np.outer(k, h @ p)
        out[t] = (x[0], x[1], e, s)

    state = pd.DataFrame(
        out, index=cut.index, columns=["alpha", "beta", "innovation", "innovation_var"]
    )
    assert state.iloc[:init_window].isna().all().all()
    assert state.iloc[init_window:].notna().all().all()
    return state


def kalman_zscore(
    prices: pd.DataFrame,
    beta: pd.Series,
    lookback: int,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.Series:
    """z-score of day t applying beta_t to the whole rolling window.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices (same index as ``beta``).
    beta : pd.Series
        Filtered beta_t (NaN where undefined).
    lookback : int
        Window length L; the window ends at t inclusive.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.Series
        ``z_t = (s_t − m_t) / sqrt(q_t)`` named ``"z"``, with ``a = log P_A``,
        ``b = log P_B``, ``s_t = a_t − beta_t·b_t``,
        ``m_t = mean_L(a) − beta_t·mean_L(b)`` and
        ``q_t = var_L(a) + beta_t²·var_L(b) − 2·beta_t·cov_L(a, b)`` (sample moments, ddof=1).
        NaN where beta_t or a full window is missing.

    Notes
    -----
    Equivalent to building the spread of the last L days with the single value beta_t and
    standardizing its last value against that window. Uses data up to t only.
    """
    assert beta.index.equals(prices.index) and lookback >= 2
    logp = log_prices(prices[[ticker_a, ticker_b]])
    a, b = logp[ticker_a], logp[ticker_b]
    roll_a = a.rolling(lookback, min_periods=lookback)
    roll_b = b.rolling(lookback, min_periods=lookback)
    mean = roll_a.mean() - beta * roll_b.mean()
    var = roll_a.var(ddof=1) + beta**2 * roll_b.var(ddof=1) - 2 * beta * roll_a.cov(b, ddof=1)
    z = (a - beta * b - mean) / var.pow(0.5)
    return z.rename("z")


def run_backtest_dynamic(
    prices: pd.DataFrame,
    beta: pd.Series,
    signal: pd.Series,
    cost_bps: float = DEFAULT_COST_BPS,
    trade_from: date | None = None,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Backtest with a time-varying hedge ratio, executed with a one-day lag.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : pd.Series
        Filtered beta_t, same index as ``prices``.
    signal : pd.Series
        Desired position at each close, values in {-1, 0, 1}.
    cost_bps : float, optional
        Cost in bp of each leg's traded notional per unit of position change.
    trade_from : date, optional
        First day of the evaluation window; signals before it are set flat and rows before
        it are dropped.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        Columns ``signal``, ``position``, ``beta_used``, ``spread_ret``, ``gross_ret``,
        ``cost``, ``net_ret``.

    Notes
    -----
    Day t+1 P&L = ``position_t × (r_A,t+1 − beta_t · r_B,t+1) / (1 + |beta_t|)``: the
    position and the hedge ratio are those known at the close of day t. Costs are
    ``cost_bps × |Δposition|`` of gross capital; the rebalancing caused by changes of beta
    is not charged (declared limitation).
    """
    assert signal.index.equals(prices.index) and beta.index.equals(prices.index)
    assert set(signal.unique()) <= {-1, 0, 1}
    sig = signal.astype(int).copy()
    if trade_from is not None:
        sig[sig.index < pd.Timestamp(trade_from)] = 0

    rets = prices[[ticker_a, ticker_b]].pct_change()
    position = sig.shift(1).fillna(0).astype(int)
    beta_used = beta.shift(1)
    assert beta_used[position != 0].notna().all(), "position held without a known beta"
    spread_ret = ((rets[ticker_a] - beta_used * rets[ticker_b]) / (1 + beta_used.abs())).fillna(0.0)
    turnover = position.diff().abs().fillna(0.0)
    turnover.iloc[0] = abs(int(position.iloc[0]))
    cost = turnover * cost_bps / 1e4
    gross = position * spread_ret

    daily = pd.DataFrame(
        {
            "signal": sig,
            "position": position,
            "beta_used": beta_used,
            "spread_ret": spread_ret,
            "gross_ret": gross,
            "cost": cost,
            "net_ret": gross - cost,
        }
    )
    if trade_from is not None:
        daily = daily[daily.index >= pd.Timestamp(trade_from)]
        if daily.empty:
            raise InsufficientDataError(f"No data on or after trade_from={trade_from}.")
        assert daily["position"].iloc[0] == 0, "must start flat at trade_from"
    cols = ["position", "spread_ret", "gross_ret", "cost", "net_ret"]
    assert not daily[cols].isna().to_numpy().any()
    return daily


def run_kalman_strategy(
    prices: pd.DataFrame,
    delta: float,
    end: date,
    trade_from: date,
    entry: float = 2.0,
    lookback: int = 60,
    cost_bps: float = DEFAULT_COST_BPS,
    v: float = KALMAN_V,
    init_window: int = KALMAN_INIT_WINDOW,
) -> StrategyRun:
    """Kalman beta -> z-score -> positions -> backtest -> trades for one delta.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    delta : float
        Transition parameter of the filter.
    end : date
        Exclusive cutoff, applied first.
    trade_from : date
        First day of the evaluation window (the strategy starts flat there).
    entry, lookback, cost_bps : optional
        Phase 2 signal parameters (pre-registered: 2.0, 60, 5 bp).
    v, init_window : optional
        Observation variance and OLS initialization length.

    Returns
    -------
    StrategyRun
        Daily results (with ``alpha``, ``beta``, ``z``) and the trade list.

    Notes
    -----
    The filter runs continuously from the start of the data: for an OOS run with ``end``
    after the split and ``trade_from`` at the split, it continues from its IS state
    without re-initialization.
    """
    cut = prices[prices.index < pd.Timestamp(end)]
    state = kalman_filter(cut, end=end, delta=delta, v=v, init_window=init_window)
    assert pd.Timestamp(trade_from) >= cut.index[init_window], (
        "evaluation must exclude the init days"
    )
    z = kalman_zscore(cut, state["beta"], lookback)
    signal = positions_from_zscore(z, entry)
    daily = run_backtest_dynamic(
        cut, state["beta"], signal, cost_bps=cost_bps, trade_from=trade_from
    )
    daily = daily.join(state[["alpha", "beta"]]).join(z)
    trades = extract_trades(daily, cost_bps=cost_bps)
    logger.info(
        "Kalman delta=%g: %d trades, %s..%s",
        delta,
        len(trades),
        daily.index.min().date(),
        daily.index.max().date(),
    )
    return StrategyRun(daily=daily, trades=trades)


def summary_on_window(
    daily: pd.DataFrame, trades: pd.DataFrame, start: date
) -> tuple[dict[str, float], int]:
    """Metrics of an existing backtest restricted to the window starting at ``start``.

    Parameters
    ----------
    daily : pd.DataFrame
        Existing daily backtest output (e.g. the Phase 2 static run).
    trades : pd.DataFrame
        Its trade list.
    start : date
        First day of the window.

    Returns
    -------
    tuple[dict[str, float], int]
        ``performance_summary`` on the cut daily returns and on the trades entered on or
        after ``start``, and the number of excluded trades already open on ``start``.

    Notes
    -----
    Pre-registered clarification (16:10): return-based metrics come from the existing
    daily returns cut to the window; trade-based metrics only from trades entered in the
    window; a trade already open at the start is excluded and flagged. No new backtest.
    """
    ts = pd.Timestamp(start)
    cut = daily[daily.index >= ts]
    entries = pd.DatetimeIndex(trades["entry_date"])
    exits = pd.DatetimeIndex(trades["exit_date"])
    inside = trades[entries >= ts]
    n_open_at_start = int(((entries < ts) & (exits >= ts)).sum())
    return performance_summary(cut, inside), n_open_at_start
