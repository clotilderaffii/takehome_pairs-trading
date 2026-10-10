"""Download raw short-interest data for INTC and AMD from Nasdaq's public API.

Endpoint: https://api.nasdaq.com/api/quote/<TICKER>/short-interest?assetClass=stocks
The API rejects requests without a browser-like User-Agent. Each raw JSON
response is saved as-is in data/raw/, with the download timestamp in the name.

Usage: uv run python scripts/fetch_short_interest.py
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

TICKERS: tuple[str, ...] = ("INTC", "AMD")
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://api.nasdaq.com/api/quote/{ticker}/short-interest"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with httpx.Client(headers=HEADERS, timeout=30.0) as client:
        for ticker in TICKERS:
            resp = client.get(URL.format(ticker=ticker), params={"assetClass": "stocks"})
            logger.info("%s: HTTP %d, %d bytes", ticker, resp.status_code, len(resp.content))
            resp.raise_for_status()
            payload = resp.json()
            path = RAW_DIR / f"{ticker}_short_interest_nasdaq_{stamp}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("%s: saved %s", ticker, path.name)


if __name__ == "__main__":
    main()
