"""Compute the in-sample / out-of-sample split date (70/30 rule).

Rule: on the common history of INTC and AMD (dates where both have a
non-missing Close), take the point at 70% of the history and round it to the
nearest 1 January. Computed two ways (70% of trading days, 70% of calendar
time) to check that the rounding makes the choice unambiguous.

Only dates are logged, never prices.

Usage: uv run python scripts/compute_split_date.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
IS_FRACTION = 0.70


def nearest_jan_first(ts: pd.Timestamp) -> pd.Timestamp:
    """Round a timestamp to the closest 1 January (ties go to the later year)."""
    lower = pd.Timestamp(year=ts.year, month=1, day=1)
    upper = pd.Timestamp(year=ts.year + 1, month=1, day=1)
    return lower if (ts - lower) < (upper - ts) else upper


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    closes = {
        t: pd.read_pickle(RAW_DIR / f"{t}_daily_yahoo.pkl")["Close"].dropna()
        for t in ("INTC", "AMD")
    }
    common = closes["INTC"].index.intersection(closes["AMD"].index).sort_values()
    n = len(common)
    first, last = common[0], common[-1]

    by_count = common[int(IS_FRACTION * n)]
    by_calendar = first + IS_FRACTION * (last - first)
    split_count = nearest_jan_first(by_count)
    split_calendar = nearest_jan_first(by_calendar)

    logger.info("common trading days : %d", n)
    logger.info("first common date   : %s", first.date())
    logger.info("last common date    : %s", last.date())
    logger.info("70%% point (days)    : %s -> rounded %s", by_count.date(), split_count.date())
    logger.info(
        "70%% point (calendar): %s -> rounded %s", by_calendar.date(), split_calendar.date()
    )
    n_is = int((common < split_count).sum())
    logger.info(
        "IS days < split: %d (%.1f%%), OOS days >= split: %d", n_is, 100 * n_is / n, n - n_is
    )


if __name__ == "__main__":
    main()
