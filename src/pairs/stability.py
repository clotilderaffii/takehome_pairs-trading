"""Phase 3: stability of a pair's relationship and flagging of weak-relationship periods.

Method (the brief's "medium" option): rolling OLS hedge ratio and rolling ADF test on the
spread built with each window's own beta, on log prices.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller

from pairs.config import TICKER_A, TICKER_B
from pairs.exceptions import InsufficientDataError
from pairs.metrics import annualized_return, max_drawdown, sharpe_ratio
from pairs.spread import log_prices

logger = logging.getLogger(__name__)

#: Rolling window in trading days (one year), pre-registered.
DEFAULT_WINDOW: int = 252
#: Recompute the rolling ADF every this many trading days (about monthly), pre-registered.
DEFAULT_STEP: int = 21
#: A window is "weak" when its ADF p-value is above this level, pre-registered.
WEAK_PVALUE: float = 0.05


@dataclass(frozen=True)
class RegimeComparison:
    """Weak vs strong comparison of a strategy's daily returns and trades.

    Attributes
    ----------
    table : pd.DataFrame
        Rows ``"weak"`` and ``"strong"``; columns ``n_days``, ``share_days``, ``exposure``,
        ``mean_daily_net``, ``ann_return``, ``sharpe``, ``max_dd``, ``n_trades``,
        ``win_rate_net`` (fractions, not percent).
    welch_t, welch_pvalue : float
        Welch t-test of mean daily net return, weak minus strong (two-sided).
    n_days_unflagged, n_trades_unflagged : int
        Days and trades excluded because no flag existed yet.
    """

    table: pd.DataFrame
    welch_t: float
    welch_pvalue: float
    n_days_unflagged: int
    n_trades_unflagged: int


def _cut_logs(
    prices: pd.DataFrame, end: date, ticker_a: str, ticker_b: str, window: int
) -> pd.DataFrame:
    """Keep dates < ``end``, take logs, and check there is at least one full window."""
    cut = prices[prices.index < pd.Timestamp(end)][[ticker_a, ticker_b]]
    if len(cut) < window:
        raise InsufficientDataError(f"Need at least {window} days before {end}, got {len(cut)}.")
    assert cut.index.max() < pd.Timestamp(end)
    return log_prices(cut)


def rolling_beta(
    prices: pd.DataFrame,
    end: date,
    window: int = DEFAULT_WINDOW,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.Series:
    """Compute the rolling OLS slope of ``log P_A`` on ``log P_B`` over ``window`` days.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    end : date
        Exclusive cutoff, applied first.
    window : int, optional
        Window length W in trading days; the window ending at t includes t.
    ticker_a, ticker_b : str, optional
        Legs A (dependent) and B (explanatory).

    Returns
    -------
    pd.Series
        ``beta_t``, named ``"rolling_beta"``; NaN for the first ``window − 1`` days.

    Raises
    ------
    InsufficientDataError
        If fewer than ``window`` days precede ``end``.

    Notes
    -----
    The OLS slope with intercept equals ``cov(x, y) / var(x)`` on the same window, which
    pandas computes in one vectorized pass.
    """
    logp = _cut_logs(prices, end, ticker_a, ticker_b, window)
    x, y = logp[ticker_b], logp[ticker_a]
    cov = y.rolling(window, min_periods=window).cov(x)
    var = x.rolling(window, min_periods=window).var()
    beta = (cov / var).rename("rolling_beta")
    assert beta.iloc[: window - 1].isna().all() and beta.iloc[window - 1 :].notna().all()
    return beta


def rolling_adf(
    prices: pd.DataFrame,
    end: date,
    window: int = DEFAULT_WINDOW,
    step: int = DEFAULT_STEP,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """ADF test on each window's spread, recomputed every ``step`` days.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    end : date
        Exclusive cutoff, applied first.
    window : int, optional
        Window length W in trading days.
    step : int, optional
        Recompute every ``step`` trading days, starting at the first full window.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        Indexed by computation date (the last day of each window), columns ``beta``
        (the window's own OLS slope), ``adf_stat``, ``adf_pvalue``, ``adf_lags``.

    Raises
    ------
    InsufficientDataError
        If fewer than ``window`` days precede ``end``.

    Notes
    -----
    The spread of each window is ``log P_A − beta_w · log P_B`` with ``beta_w`` estimated on
    that same window, so the ADF p-value is optimistic (declared limitation); the test uses
    a constant and AIC lag selection. A computation dated t uses data up to t only.
    """
    logp = _cut_logs(prices, end, ticker_a, ticker_b, window)
    a = logp[ticker_a].to_numpy()
    b = logp[ticker_b].to_numpy()
    rows: list[dict[str, float]] = []
    dates: list[pd.Timestamp] = []
    for k in range(window - 1, len(logp), step):
        xa, xb = a[k - window + 1 : k + 1], b[k - window + 1 : k + 1]
        beta_w = float(np.cov(xa, xb, ddof=1)[0, 1] / np.var(xb, ddof=1))
        stat, pvalue, lags, *_ = adfuller(
            xa - beta_w * xb, regression="c", autolag="AIC", result_object=False
        )
        rows.append(
            {
                "beta": beta_w,
                "adf_stat": float(stat),
                "adf_pvalue": float(pvalue),
                "adf_lags": float(lags),
            }
        )
        dates.append(logp.index[k])
    table = pd.DataFrame(rows, index=pd.DatetimeIndex(dates, name="date"))
    assert table.index.is_monotonic_increasing and table.index.max() < pd.Timestamp(end)
    logger.info(
        "Rolling ADF: %d windows of %d days every %d days, %s..%s",
        len(table),
        window,
        step,
        table.index.min().date(),
        table.index.max().date(),
    )
    return table


def weak_flag(
    adf_table: pd.DataFrame, index: pd.DatetimeIndex, threshold: float = WEAK_PVALUE
) -> pd.Series:
    """Daily weak-relationship flag usable on day t (data up to t − 1 only).

    Parameters
    ----------
    adf_table : pd.DataFrame
        Output of :func:`rolling_adf`; its dates must belong to ``index``.
    index : pd.DatetimeIndex
        Trading days on which the flag is needed.
    threshold : float, optional
        A window is weak when its ADF p-value is > ``threshold``.

    Returns
    -------
    pd.Series
        Nullable boolean (``True`` = weak, ``False`` = strong, ``<NA>`` = no ADF result yet),
        named ``"weak"``.

    Notes
    -----
    The ADF computed at the close of day t_k is applied from day t_k + 1 up to and including
    the next computation day: forward-fill the p-values, then shift by one day.
    """
    assert adf_table.index.isin(index).all(), "ADF dates must be trading days of the index"
    p_daily = adf_table["adf_pvalue"].reindex(index).ffill().shift(1)
    flag = pd.Series(pd.NA, index=index, dtype="boolean", name="weak")
    known = p_daily.notna()
    flag[known] = p_daily[known] > threshold
    return flag


def spread_leg_correlations(
    prices: pd.DataFrame,
    beta: float,
    end: date,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Correlate the daily change of the static-beta log spread with each leg's daily return.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Static hedge ratio defining the spread ``log P_A − beta · log P_B``.
    end : date
        Exclusive cutoff, applied first.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        Indexed by period (``"All"``, then ``"1980s"``, ...), columns ``n_days``,
        ``corr_with_<ticker_b>`` and ``corr_with_<ticker_a>`` (Pearson, simple daily returns).

    Notes
    -----
    Diagnostic for the hypothesis that the static-beta spread behaves like a position in
    one leg: a well-hedged spread should be only weakly correlated with either leg.
    """
    cut = prices[prices.index < pd.Timestamp(end)][[ticker_a, ticker_b]]
    assert cut.index.max() < pd.Timestamp(end)
    logp = log_prices(cut)
    d_spread = (logp[ticker_a] - beta * logp[ticker_b]).diff().iloc[1:]
    rets = cut.pct_change().iloc[1:]
    idx = rets.index
    assert isinstance(idx, pd.DatetimeIndex)

    def _row(mask: np.ndarray) -> dict[str, float]:
        ds, r = d_spread[mask], rets[mask]
        return {
            "n_days": float(mask.sum()),
            f"corr_with_{ticker_b}": float(ds.corr(r[ticker_b])),
            f"corr_with_{ticker_a}": float(ds.corr(r[ticker_a])),
        }

    rows = {"All": _row(np.ones(len(idx), dtype=bool))}
    decades = (idx.year // 10) * 10
    for decade in sorted(set(decades)):
        rows[f"{decade}s"] = _row(np.asarray(decades == decade))
    return pd.DataFrame.from_dict(rows, orient="index")


def regime_comparison(
    daily: pd.DataFrame, trades: pd.DataFrame, flag: pd.Series
) -> RegimeComparison:
    """Compare a strategy's results on weak vs strong days.

    Parameters
    ----------
    daily : pd.DataFrame
        Backtest output with ``net_ret`` and ``position`` columns.
    trades : pd.DataFrame
        Trade list with ``entry_date`` and ``net_return``.
    flag : pd.Series
        Output of :func:`weak_flag` (covering ``daily.index``).

    Returns
    -------
    RegimeComparison
        Table of metrics per regime, Welch test, and counts of unflagged days/trades.

    Notes
    -----
    All days are used, including flat days (zero return), so ``exposure`` is reported next
    to the returns. Annualized return, Sharpe and max drawdown of a regime are computed on
    the sequence of that regime's days only ("stitched" equity curve). Trades are
    classified by the flag of their entry day. The Welch p-value is approximate: daily
    returns are autocorrelated and regimes come in long blocks.
    """
    f = flag.reindex(daily.index)
    has_flag = f.notna().to_numpy()
    weak_days = (f == True).fillna(False).to_numpy(dtype=bool)  # noqa: E712
    strong_days = has_flag & ~weak_days

    entry_flag = flag.reindex(pd.DatetimeIndex(trades["entry_date"]))
    trade_has = entry_flag.notna().to_numpy()
    trade_weak = (entry_flag == True).fillna(False).to_numpy(dtype=bool)  # noqa: E712
    trade_strong = trade_has & ~trade_weak

    n_flagged = int(has_flag.sum())
    rows: dict[str, dict[str, float]] = {}
    for name, day_mask, trade_mask in (
        ("weak", weak_days, trade_weak),
        ("strong", strong_days, trade_strong),
    ):
        r = daily["net_ret"][day_mask]
        t = trades[trade_mask]
        rows[name] = {
            "n_days": float(len(r)),
            "share_days": len(r) / n_flagged if n_flagged else math.nan,
            "exposure": float((daily["position"][day_mask] != 0).mean()) if len(r) else math.nan,
            "mean_daily_net": float(r.mean()) if len(r) else math.nan,
            "ann_return": annualized_return(r) if len(r) else math.nan,
            "sharpe": sharpe_ratio(r) if len(r) > 1 else math.nan,
            "max_dd": max_drawdown(r) if len(r) else math.nan,
            "n_trades": float(len(t)),
            "win_rate_net": float((t["net_return"] > 0).mean()) if len(t) else math.nan,
        }
    table = pd.DataFrame.from_dict(rows, orient="index")

    weak_r = daily["net_ret"][weak_days]
    strong_r = daily["net_ret"][strong_days]
    if len(weak_r) > 1 and len(strong_r) > 1:
        res = stats.ttest_ind(weak_r, strong_r, equal_var=False)
        welch_t, welch_p = float(res.statistic), float(res.pvalue)
    else:
        welch_t, welch_p = math.nan, math.nan

    assert int(weak_days.sum() + strong_days.sum()) == n_flagged
    assert int(trade_weak.sum() + trade_strong.sum()) == int(trade_has.sum())
    return RegimeComparison(
        table=table,
        welch_t=welch_t,
        welch_pvalue=welch_p,
        n_days_unflagged=int(len(daily) - n_flagged),
        n_trades_unflagged=int(len(trades) - trade_has.sum()),
    )
