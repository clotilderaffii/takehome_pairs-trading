"""Phase 4: parse Nasdaq short-interest JSON and align it with the spread (publication lag)."""

from __future__ import annotations

import json
import logging
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay
from scipy import stats

from pairs.config import RAW_DIR, TICKER_A, TICKER_B
from pairs.exceptions import DataFetchError
from pairs.spread import compute_spread

logger = logging.getLogger(__name__)

#: Business days between settlement and publication of short interest (approximate).
PUBLICATION_LAG_BDAYS: int = 7


def load_short_interest(ticker: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Parse the raw Nasdaq short-interest JSON of one ticker.

    Parameters
    ----------
    ticker : str
        Ticker symbol.
    raw_dir : Path, optional
        Directory holding ``<TICKER>_short_interest_nasdaq_<stamp>.json``.

    Returns
    -------
    pd.DataFrame
        Indexed by ``settlement_date`` (ascending), columns ``short_interest`` (shares),
        ``avg_daily_volume`` (shares) and ``days_to_cover``.

    Raises
    ------
    DataFetchError
        If no file exists, the response status is not 200, or the table is empty.

    Notes
    -----
    If several downloads exist, the most recent (by file name stamp) is used.
    """
    files = sorted(raw_dir.glob(f"{ticker}_short_interest_nasdaq_*.json"))
    if not files:
        raise DataFetchError(f"No short-interest file for {ticker} in {raw_dir}.")
    path = files[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status", {}).get("rCode") != 200:
        raise DataFetchError(f"{path.name}: response status is not 200.")
    rows = (payload.get("data") or {}).get("shortInterestTable", {}).get("rows") or []
    if not rows:
        raise DataFetchError(f"{path.name}: empty short-interest table.")

    df = (
        pd.DataFrame(
            {
                "settlement_date": pd.to_datetime(
                    [r["settlementDate"] for r in rows], format="%m/%d/%Y"
                ),
                "short_interest": [int(str(r["interest"]).replace(",", "")) for r in rows],
                "avg_daily_volume": [
                    int(str(r["avgDailyShareVolume"]).replace(",", "")) for r in rows
                ],
                "days_to_cover": [float(r["daysToCover"]) for r in rows],
            }
        )
        .set_index("settlement_date")
        .sort_index()
    )
    assert df.index.is_unique and (df["short_interest"] > 0).all()
    logger.info(
        "%s short interest: %d dates, %s -> %s (%s)",
        ticker,
        len(df),
        df.index.min().date(),
        df.index.max().date(),
        path.name,
    )
    return df


def publication_dates(
    settlement: pd.DatetimeIndex, lag_bdays: int = PUBLICATION_LAG_BDAYS
) -> pd.DatetimeIndex:
    """Approximate publication dates: settlement date plus ``lag_bdays`` weekdays.

    Parameters
    ----------
    settlement : pd.DatetimeIndex
        Settlement dates.
    lag_bdays : int, optional
        Business-day lag (exchange holidays are ignored).

    Returns
    -------
    pd.DatetimeIndex
        Publication dates, same length and order.
    """
    return pd.DatetimeIndex(settlement + BDay(lag_bdays))


def next_trading_day(dates: pd.DatetimeIndex, trading_days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Map each date to the first trading day on or after it.

    Parameters
    ----------
    dates : pd.DatetimeIndex
        Dates to map.
    trading_days : pd.DatetimeIndex
        Sorted trading days.

    Returns
    -------
    pd.DatetimeIndex
        For each input date, the first element of ``trading_days`` that is >= it.

    Raises
    ------
    DataFetchError
        If a date falls after the last trading day available.
    """
    pos = trading_days.searchsorted(dates, side="left")
    if (pos >= len(trading_days)).any():
        raise DataFetchError("A date falls after the last available trading day.")
    return pd.DatetimeIndex(trading_days[pos])


def days_to_cover_floor(si: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the settlement dates whose days-to-cover is exactly 1.0 (probable source floor)."""
    return pd.DatetimeIndex(si.index[si["days_to_cover"] == 1.0])


def build_periods(
    si_a: pd.DataFrame,
    si_b: pd.DataFrame,
    prices: pd.DataFrame,
    beta: float,
    end: date,
    use_publication: bool = True,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """One row per period between consecutive (publication or settlement) dates.

    Parameters
    ----------
    si_a, si_b : pd.DataFrame
        Output of :func:`load_short_interest` for legs A and B (same settlement dates).
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Static hedge ratio of the log spread.
    end : date
        Exclusive price cutoff, applied first.
    use_publication : bool, optional
        True (main analysis): align to publication dates. False: settlement dates
        (descriptive only).
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        Indexed by period end (trading day), columns ``start``, ``si_chg_<A>``,
        ``si_chg_<B>``, ``si_chg_diff`` (A − B, percentage points as fractions),
        ``spread_chg``, ``ret_<A>``, ``ret_<B>``, ``max_abs_ret``.

    Notes
    -----
    Period k runs from the close of anchor day k to the close of anchor day k+1. The SI
    change of period k compares the value attached to anchor k+1 with the one attached to
    anchor k. ``max_abs_ret`` is the largest absolute daily return of either stock on the
    days (k, k+1].
    """
    assert si_a.index.equals(si_b.index), "both tickers must share settlement dates"
    cut = prices[prices.index < pd.Timestamp(end)][[ticker_a, ticker_b]]
    trading = pd.DatetimeIndex(cut.index)

    settle = pd.DatetimeIndex(si_a.index)
    anchors_raw = publication_dates(settle) if use_publication else settle
    anchors = next_trading_day(anchors_raw, trading)
    assert anchors.is_monotonic_increasing and anchors.is_unique

    # Work on positional numpy arrays: pos[k] is the row of anchor k in the price table.
    pos = trading.get_indexer(anchors)
    assert (pos >= 0).all()
    s = compute_spread(cut, beta, ticker_a, ticker_b).to_numpy(dtype=float)
    pa = cut[ticker_a].to_numpy(dtype=float)
    pb = cut[ticker_b].to_numpy(dtype=float)
    abs_ret = np.abs(cut.pct_change().to_numpy(dtype=float))  # row 0 is NaN, never used
    si_a_v = si_a["short_interest"].to_numpy(dtype=float)
    si_b_v = si_b["short_interest"].to_numpy(dtype=float)

    rows = []
    for k in range(len(anchors) - 1):
        i0, i1 = int(pos[k]), int(pos[k + 1])
        rows.append(
            {
                "period_end": anchors[k + 1],
                "start": anchors[k],
                f"si_chg_{ticker_a}": si_a_v[k + 1] / si_a_v[k] - 1,
                f"si_chg_{ticker_b}": si_b_v[k + 1] / si_b_v[k] - 1,
                "spread_chg": s[i1] - s[i0],
                f"ret_{ticker_a}": pa[i1] / pa[i0] - 1,
                f"ret_{ticker_b}": pb[i1] / pb[i0] - 1,
                "max_abs_ret": float(abs_ret[i0 + 1 : i1 + 1].max()),  # days (k, k+1]
            }
        )
    periods = pd.DataFrame(rows).set_index("period_end")
    periods["si_chg_diff"] = periods[f"si_chg_{ticker_a}"] - periods[f"si_chg_{ticker_b}"]
    assert len(periods) == len(anchors) - 1 and not periods.isna().to_numpy().any()
    return periods


def critical_spearman(n: int, alpha: float = 0.05) -> float:
    """Minimum |rho| significant at level ``alpha`` (two-sided) with ``n`` observations.

    Parameters
    ----------
    n : int
        Sample size (> 2).
    alpha : float, optional
        Two-sided significance level.

    Returns
    -------
    float
        ``t / sqrt(n − 2 + t²)`` with ``t`` the ``1 − alpha/2`` quantile of Student's t with
        ``n − 2`` degrees of freedom — the same approximation scipy uses for the p-value.
    """
    assert n > 2
    t = float(stats.t.ppf(1 - alpha / 2, n - 2))
    return t / math.sqrt(n - 2 + t * t)


def spearman_tests(
    periods: pd.DataFrame, ticker_a: str = TICKER_A, ticker_b: str = TICKER_B
) -> pd.DataFrame:
    """Run the five pre-registered Spearman tests (questions 1-3).

    Parameters
    ----------
    periods : pd.DataFrame
        Output of :func:`build_periods`.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        One row per test: ``question``, ``x``, ``y``, ``rho``, ``p_value``, ``n``,
        ``rho_crit_5pct``, ``significant_5pct``, ``significant_bonferroni`` (p < 0.05 / 5).
    """
    specs = [
        ("Q1", f"si_chg_{ticker_a}", "spread_chg"),
        ("Q1", f"si_chg_{ticker_b}", "spread_chg"),
        ("Q2", "si_chg_diff", "spread_chg"),
        ("Q3", f"si_chg_{ticker_a}", "max_abs_ret"),
        ("Q3", f"si_chg_{ticker_b}", "max_abs_ret"),
    ]
    n = len(periods)
    crit = critical_spearman(n)
    rows = []
    for question, x, y in specs:
        res = stats.spearmanr(periods[x], periods[y])
        rho, p = float(res.statistic), float(res.pvalue)
        rows.append(
            {
                "question": question,
                "x": x,
                "y": y,
                "rho": rho,
                "p_value": p,
                "n": n,
                "rho_crit_5pct": crit,
                "significant_5pct": p < 0.05,
                "significant_bonferroni": p < 0.05 / len(specs),
            }
        )
    out = pd.DataFrame(rows)
    assert np.isfinite(out["rho"]).all()
    return out
