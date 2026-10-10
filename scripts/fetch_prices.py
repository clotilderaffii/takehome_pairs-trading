"""Download raw daily price history for INTC and AMD from Yahoo Finance.

Saves one pickle per ticker in data/raw/ plus a JSON metadata file with the
download timestamp and library versions. Logs only dates and row counts,
never prices: the data must not be inspected before the IS/OOS split is fixed.

Usage: uv run python scripts/fetch_prices.py
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

TICKERS: tuple[str, ...] = ("INTC", "AMD")
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch_one(ticker: str) -> pd.DataFrame:
    """Download the full daily history of one ticker, adjusted for splits/dividends."""
    df = yf.download(
        ticker,
        period="max",
        interval="1d",
        auto_adjust=True,
        progress=False,
        multi_level_index=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"Empty download for {ticker}")
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "Yahoo Finance via yfinance",
        "yfinance_version": yf.__version__,
        "pandas_version": pd.__version__,
        "params": {"period": "max", "interval": "1d", "auto_adjust": True},
        "tickers": {},
    }
    for ticker in TICKERS:
        df = fetch_one(ticker)
        path = RAW_DIR / f"{ticker}_daily_yahoo.pkl"
        df.to_pickle(path)
        info = {
            "file": path.name,
            "rows": len(df),
            "first_date": str(df.index.min().date()),
            "last_date": str(df.index.max().date()),
            "columns": list(map(str, df.columns)),
        }
        meta["tickers"][ticker] = info  # type: ignore[index]
        logger.info(
            "%s: %d rows, %s -> %s", ticker, info["rows"], info["first_date"], info["last_date"]
        )
    (RAW_DIR / "prices_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
