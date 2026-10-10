"""Performance metrics: annualized return, volatility, Sharpe, max drawdown, trade statistics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

#: Trading days per year used for annualization.
TRADING_DAYS: int = 252


def annualized_return(returns: pd.Series) -> float:
    """Compounded annual growth rate of a daily return series.

    Parameters
    ----------
    returns : pd.Series
        Daily simple returns.

    Returns
    -------
    float
        ``(prod(1 + r))^(252 / n) − 1``.
    """
    assert len(returns) > 0 and not returns.isna().any()
    growth = float(np.prod(1.0 + returns.to_numpy()))
    if growth <= 0:
        return -1.0
    return float(growth ** (TRADING_DAYS / len(returns))) - 1.0


def annualized_volatility(returns: pd.Series) -> float:
    """Annualized standard deviation ``std(r) · √252`` (sample std, ddof=1)."""
    return float(returns.std(ddof=1)) * math.sqrt(TRADING_DAYS)


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualized Sharpe ratio ``mean(r) / std(r) · √252`` with risk-free rate 0.

    Parameters
    ----------
    returns : pd.Series
        Daily simple returns, including flat days (zero return).

    Returns
    -------
    float
        Sharpe ratio, NaN if the volatility is zero.

    Notes
    -----
    rf = 0 because the long/short P&L is treated as an excess return (pre-registered).
    """
    std = float(returns.std(ddof=1))
    if std == 0 or math.isnan(std):
        return math.nan
    return float(returns.mean()) / std * math.sqrt(TRADING_DAYS)


def max_drawdown(returns: pd.Series) -> float:
    """Largest peak-to-trough loss of the compounded equity curve (starting at 1).

    Parameters
    ----------
    returns : pd.Series
        Daily simple returns.

    Returns
    -------
    float
        Max drawdown as a non-positive fraction, e.g. -0.25 for a 25% loss.
    """
    equity = np.concatenate([[1.0], np.cumprod(1.0 + returns.to_numpy())])
    peak = np.maximum.accumulate(equity)
    dd = float((equity / peak - 1.0).min())
    assert dd <= 0
    return dd


def performance_summary(daily: pd.DataFrame, trades: pd.DataFrame) -> dict[str, float]:
    """All pre-registered metrics for one backtest, gross and net of costs.

    Parameters
    ----------
    daily : pd.DataFrame
        Output of ``backtest.run_backtest`` (needs ``gross_ret``, ``net_ret``, ``position``).
    trades : pd.DataFrame
        Output of ``backtest.extract_trades``.

    Returns
    -------
    dict[str, float]
        ``ann_return_{gross,net}``, ``ann_vol_{gross,net}``, ``sharpe_{gross,net}``,
        ``max_dd_{gross,net}``, ``n_trades``, ``win_rate_net``, ``avg_duration_days``,
        ``max_duration_days``, ``exposure`` (share of days in a position),
        ``n_open_at_end``.
    """
    out: dict[str, float] = {}
    for kind in ("gross", "net"):
        r = daily[f"{kind}_ret"]
        out[f"ann_return_{kind}"] = annualized_return(r)
        out[f"ann_vol_{kind}"] = annualized_volatility(r)
        out[f"sharpe_{kind}"] = sharpe_ratio(r)
        out[f"max_dd_{kind}"] = max_drawdown(r)
    n = len(trades)
    out["n_trades"] = float(n)
    out["win_rate_net"] = float((trades["net_return"] > 0).mean()) if n else math.nan
    out["avg_duration_days"] = float(trades["duration_days"].mean()) if n else math.nan
    out["max_duration_days"] = float(trades["duration_days"].max()) if n else math.nan
    out["exposure"] = float((daily["position"] != 0).mean())
    out["n_open_at_end"] = float(trades["open_at_end"].sum()) if n else 0.0
    return out
