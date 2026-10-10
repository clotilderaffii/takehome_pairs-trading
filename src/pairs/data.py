"""Phase 1: load the raw Yahoo Finance checkpoints, align the two series, compute returns."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pairs.config import RAW_DIR, TICKER_A, TICKER_B
from pairs.exceptions import DataFetchError

logger = logging.getLogger(__name__)


def raw_price_path(ticker: str, raw_dir: Path = RAW_DIR) -> Path:
    """Return the path of the raw Yahoo Finance pickle for ``ticker``."""
    return raw_dir / f"{ticker}_daily_yahoo.pkl"


def load_close(ticker: str, end: date, raw_dir: Path = RAW_DIR) -> pd.Series:
    """Load the adjusted daily close of one ticker, keeping only dates strictly before ``end``.

    Parameters
    ----------
    ticker : str
        Ticker symbol, e.g. ``"INTC"``.
    end : date
        Exclusive cutoff: only rows with date < ``end`` are returned. The cut is
        the first operation after reading the file.
    raw_dir : Path, optional
        Directory holding ``<TICKER>_daily_yahoo.pkl``.

    Returns
    -------
    pd.Series
        Adjusted close (``auto_adjust=True``), indexed by a sorted, unique,
        timezone-naive DatetimeIndex, named after the ticker.

    Raises
    ------
    DataFetchError
        If the file is missing, has no ``Close`` column, has no rows before
        ``end``, or contains non-positive prices.

    Notes
    -----
    Rows with a missing close are dropped (and logged) rather than filled:
    forward-filling would invent a price that never traded.
    """
    path = raw_price_path(ticker, raw_dir)
    if not path.exists():
        raise DataFetchError(f"Raw price file not found: {path}. Run scripts/fetch_prices.py.")
    raw = pd.read_pickle(path)
    if not isinstance(raw, pd.DataFrame) or "Close" not in raw.columns:
        raise DataFetchError(f"{path} is not a DataFrame with a 'Close' column.")

    if not isinstance(raw.index, pd.DatetimeIndex):
        raise DataFetchError(f"{path} is not indexed by dates.")
    close = raw["Close"]
    close = close[close.index < pd.Timestamp(end)]

    n_missing = int(close.isna().sum())
    if n_missing:
        logger.warning("%s: dropping %d rows with missing close", ticker, n_missing)
        close = close.dropna()
    if close.empty:
        raise DataFetchError(f"{ticker}: no prices before {end}.")
    if (close <= 0).any():
        raise DataFetchError(f"{ticker}: non-positive adjusted prices found.")

    close = close.sort_index().astype(float).rename(ticker)
    close.index.name = "date"
    idx = close.index
    assert isinstance(idx, pd.DatetimeIndex)
    assert idx.is_unique, f"{ticker}: duplicate dates"
    assert idx.tz is None, f"{ticker}: expected timezone-naive dates"
    assert idx.max() < pd.Timestamp(end)
    return close


def load_pair(
    end: date,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
    raw_dir: Path = RAW_DIR,
) -> pd.DataFrame:
    """Load both legs and align them on the dates where both have a price.

    Parameters
    ----------
    end : date
        Exclusive cutoff passed to :func:`load_close`; use ``SPLIT_DATE`` for
        the in-sample period.
    ticker_a, ticker_b : str, optional
        Leg A and leg B (defaults: INTC, AMD).
    raw_dir : Path, optional
        Directory holding the raw pickles.

    Returns
    -------
    pd.DataFrame
        Columns ``[ticker_a, ticker_b]``, one row per common trading day, all
        dates < ``end``, no missing values.

    Raises
    ------
    DataFetchError
        If either file is missing/invalid or the two series share no dates.
    """
    a = load_close(ticker_a, end=end, raw_dir=raw_dir)
    b = load_close(ticker_b, end=end, raw_dir=raw_dir)
    prices = pd.concat([a, b], axis=1, join="inner")

    n_dropped = len(a) + len(b) - 2 * len(prices)
    if n_dropped:
        logger.warning("Alignment dropped %d rows present in only one series", n_dropped)
    if prices.empty:
        raise DataFetchError(f"{ticker_a} and {ticker_b} share no dates before {end}.")

    assert list(prices.columns) == [ticker_a, ticker_b]
    assert not prices.isna().to_numpy().any(), "NaN in aligned prices"
    assert prices.index.is_monotonic_increasing and prices.index.is_unique
    assert prices.index.max() < pd.Timestamp(end), "date >= cutoff leaked into the data"
    logger.info(
        "Loaded %s/%s: %d common days, %s -> %s (end=%s, exclusive)",
        ticker_a,
        ticker_b,
        len(prices),
        prices.index.min().date(),
        prices.index.max().date(),
        end,
    )
    return prices


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple daily returns ``P_t / P_{t-1} - 1`` for each column.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned prices without missing values, e.g. the output of :func:`load_pair`.

    Returns
    -------
    pd.DataFrame
        Same columns, one row fewer (the first date has no previous price).

    Notes
    -----
    Returns are taken between consecutive *common* trading days, so both legs
    always cover exactly the same interval.
    """
    assert not prices.isna().to_numpy().any(), "NaN in prices"
    returns = prices.pct_change().iloc[1:]
    assert not returns.isna().to_numpy().any(), "NaN in returns"
    assert len(returns) == len(prices) - 1
    return returns


def return_correlation_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of the two legs' daily returns, overall and per decade.

    Parameters
    ----------
    returns : pd.DataFrame
        Two-column daily returns, e.g. the output of :func:`daily_returns`.

    Returns
    -------
    pd.DataFrame
        Indexed by period label (``"All"`` first, then ``"1980s"``, ...), with
        columns ``start``, ``end`` (first/last date used), ``n_days`` and
        ``correlation``. Partial decades at the edges are kept and their
        actual coverage is visible in ``start``/``end``.
    """
    assert returns.shape[1] == 2, "expected exactly two return columns"
    col_a, col_b = returns.columns

    def _row(chunk: pd.DataFrame) -> dict[str, object]:
        return {
            "start": chunk.index.min().date(),
            "end": chunk.index.max().date(),
            "n_days": len(chunk),
            "correlation": float(chunk[col_a].corr(chunk[col_b])),
        }

    rows = {"All": _row(returns)}
    idx = returns.index
    assert isinstance(idx, pd.DatetimeIndex), "returns must be indexed by dates"
    decades = (idx.year // 10) * 10
    for decade, chunk in returns.groupby(decades):
        rows[f"{decade}s"] = _row(chunk)

    table = pd.DataFrame.from_dict(rows, orient="index")
    table.index.name = "period"
    assert table["n_days"].iloc[1:].sum() == len(returns)
    assert table["correlation"].between(-1.0, 1.0).all()
    return table
