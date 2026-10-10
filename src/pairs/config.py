"""Project-wide constants: tickers, IS/OOS split date (2013-01-01), data and figure paths."""

from __future__ import annotations

from datetime import date
from pathlib import Path

#: Leg A of the regression PriceA = alpha + beta * PriceB (fixed, never inverted).
TICKER_A: str = "INTC"
#: Leg B of the regression.
TICKER_B: str = "AMD"

#: First out-of-sample date. In-sample = dates < SPLIT_DATE, out-of-sample = dates >= SPLIT_DATE.
#: Fixed by the 70/30 rule before looking at any price (see EXPERIMENTS.md).
SPLIT_DATE: date = date(2013, 1, 1)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR: Path = PROJECT_ROOT / "reports" / "figures"
