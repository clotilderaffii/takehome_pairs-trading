"""Phase 2: daily P&L of the spread positions, executed with a one-day lag (shift(1))."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from pairs.config import TICKER_A, TICKER_B
from pairs.exceptions import InsufficientDataError
from pairs.signal import positions_from_zscore, rolling_zscore
from pairs.spread import compute_spread

logger = logging.getLogger(__name__)

#: Cost per leg, in basis points of that leg's traded notional (pre-registered, not optimized).
DEFAULT_COST_BPS: float = 5.0


@dataclass(frozen=True)
class StrategyRun:
    """Output of one strategy configuration.

    Attributes
    ----------
    daily : pd.DataFrame
        One row per day of the evaluation window; see :func:`run_backtest`, plus
        ``spread`` and ``z``.
    trades : pd.DataFrame
        One row per trade; see :func:`extract_trades`.
    """

    daily: pd.DataFrame
    trades: pd.DataFrame


def run_backtest(
    prices: pd.DataFrame,
    beta: float,
    signal: pd.Series,
    cost_bps: float = DEFAULT_COST_BPS,
    lag: int = 1,
    trade_from: date | None = None,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Backtest a spread position series on gross capital.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Hedge ratio (log-price regression), estimated beforehand.
    signal : pd.Series
        Desired position at each close, values in {-1, 0, 1}, same index as ``prices``.
    cost_bps : float, optional
        Cost in bp of each leg's traded notional per unit of position change.
    lag : int, optional
        Execution delay in days: ``position_t = signal_{t−lag}``. 1 = trade at the close the
        signal was computed on and earn the next day's return; 2 = one extra day of delay.
    trade_from : date, optional
        First day of the evaluation window. Signals before it are set to flat and rows
        before it are dropped, so every configuration starts flat on the same day.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        Columns ``signal``, ``position`` (held during the day), ``spread_ret``,
        ``gross_ret``, ``cost``, ``net_ret``.

    Notes
    -----
    ``spread_ret_t = (r_A,t − beta · r_B,t) / (1 + |beta|)``: weights ``1/(1+|beta|)`` on A
    and ``−beta/(1+|beta|)`` on B, gross exposure 1. Because the two legs sum to 1 unit of
    capital, a cost of ``cost_bps`` on each leg's notional is ``cost_bps`` of capital per
    unit of ``|Δposition|``: one entry or exit costs 5 bp, a round trip or a flip 10 bp.
    The cost is charged on the day the new position becomes active. Daily rebalancing to
    constant weights is implied and its cost ignored (declared limitation).
    """
    assert signal.index.equals(prices.index), "signal and prices must share the index"
    assert set(signal.unique()) <= {-1, 0, 1}, "signal must be in {-1, 0, 1}"
    assert lag >= 1, "execution lag must be >= 1 day (no same-bar trading)"

    sig = signal.astype(int).copy()
    if trade_from is not None:
        sig[sig.index < pd.Timestamp(trade_from)] = 0

    rets = prices[[ticker_a, ticker_b]].pct_change()
    spread_ret = ((rets[ticker_a] - beta * rets[ticker_b]) / (1 + abs(beta))).fillna(0.0)
    position = sig.shift(lag).fillna(0).astype(int)
    turnover = position.diff().abs().fillna(0.0)
    turnover.iloc[0] = abs(int(position.iloc[0]))
    cost = turnover * cost_bps / 1e4
    gross = position * spread_ret

    daily = pd.DataFrame(
        {
            "signal": sig,
            "position": position,
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

    assert not daily.isna().to_numpy().any(), "NaN in backtest output"
    assert set(daily["position"].unique()) <= {-1, 0, 1}
    return daily


def extract_trades(daily: pd.DataFrame, cost_bps: float = DEFAULT_COST_BPS) -> pd.DataFrame:
    """List the trades (maximal runs of the same non-zero position) in a backtest.

    Parameters
    ----------
    daily : pd.DataFrame
        Output of :func:`run_backtest`.
    cost_bps : float, optional
        Cost per entry and per exit, in bp of capital.

    Returns
    -------
    pd.DataFrame
        Columns ``entry_date`` and ``exit_date`` (first and last day the position is held),
        ``direction`` (+1 long spread, -1 short spread), ``duration_days`` (days held),
        ``gross_return`` (compounded), ``net_return`` and ``open_at_end``.

    Notes
    -----
    ``net_return = (1 + gross_return)·(1 − c)² − 1`` with ``c = cost_bps/10⁴``: one entry and
    one exit cost. A trade still open on the last day is treated as closed there (exit cost
    included) and flagged with ``open_at_end``. A direct flip ends one trade and starts the
    next on consecutive days, each with its own cost.
    """
    pos = daily["position"].to_numpy()
    gross = daily["gross_ret"].to_numpy()
    dates = daily.index
    c = cost_bps / 1e4
    rows: list[dict[str, object]] = []
    i, n = 0, len(pos)
    while i < n:
        if pos[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < n and pos[j + 1] == pos[i]:
            j += 1
        g = float(np.prod(1.0 + gross[i : j + 1]) - 1.0)
        rows.append(
            {
                "entry_date": dates[i],
                "exit_date": dates[j],
                "direction": int(pos[i]),
                "duration_days": j - i + 1,
                "gross_return": g,
                "net_return": (1.0 + g) * (1.0 - c) ** 2 - 1.0,
                "open_at_end": j == n - 1,
            }
        )
        i = j + 1
    columns = [
        "entry_date",
        "exit_date",
        "direction",
        "duration_days",
        "gross_return",
        "net_return",
        "open_at_end",
    ]
    trades = pd.DataFrame(rows, columns=columns)
    assert int(trades["duration_days"].sum()) == int((pos != 0).sum())
    return trades


def run_strategy(
    prices: pd.DataFrame,
    beta: float,
    entry: float,
    lookback: int,
    end: date,
    trade_from: date | None = None,
    lag: int = 1,
    cost_bps: float = DEFAULT_COST_BPS,
) -> StrategyRun:
    """Run spread -> z-score -> positions -> backtest -> trades for one configuration.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Hedge ratio, estimated beforehand (in-sample only).
    entry : float
        Entry threshold e on |z|.
    lookback : int
        Rolling window L of the z-score.
    end : date
        Exclusive cutoff, applied first: nothing on or after ``end`` is used.
    trade_from : date, optional
        Start of the common evaluation window (see :func:`run_backtest`).
    lag : int, optional
        Execution delay in days (1 = main design, 2 = robustness check).
    cost_bps : float, optional
        Cost per leg in bp.

    Returns
    -------
    StrategyRun
        Daily results (with spread and z) and the trade list.
    """
    cut = prices[prices.index < pd.Timestamp(end)]
    assert cut.index.max() < pd.Timestamp(end)
    spread = compute_spread(cut, beta)
    z = rolling_zscore(spread, lookback)
    signal = positions_from_zscore(z, entry)
    daily = run_backtest(cut, beta, signal, cost_bps=cost_bps, lag=lag, trade_from=trade_from)
    daily = daily.join(spread).join(z)
    trades = extract_trades(daily, cost_bps=cost_bps)
    logger.info(
        "e=%.1f L=%d lag=%d: %d trades, %s..%s",
        entry,
        lookback,
        lag,
        len(trades),
        daily.index.min().date(),
        daily.index.max().date(),
    )
    return StrategyRun(daily=daily, trades=trades)
