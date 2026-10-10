"""Run the Phase 5 joint block bootstrap once and save the per-path table.

Pre-registered in EXPERIMENTS.md (2026-10-10 15:18 CEST): 500 paths, block 20, seed 2026,
split at the real split position. Writes data/processed/simulation_paths.pkl, which
notebooks/05_simulation.ipynb reloads (recomputing only if the parameters or data differ).

Usage: uv run python scripts/run_simulation.py
"""

from __future__ import annotations

import logging
import time
from datetime import date

from pairs.config import PROCESSED_DIR, SPLIT_DATE
from pairs.data import load_pair
from pairs.simulation import BootstrapParams, load_or_simulate

logger = logging.getLogger(__name__)

FULL_END = date(2026, 10, 10)  # exclusive: last available date is 2026-10-09


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("pairs.backtest", "pairs.spread"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    prices = load_pair(end=FULL_END)
    params = BootstrapParams()
    split_rows = int((prices.index < SPLIT_DATE.isoformat()).sum())
    assert split_rows == params.split_index, "split index must match the real IS/OOS split"
    t0 = time.perf_counter()
    table = load_or_simulate(prices, params, PROCESSED_DIR / "simulation_paths.pkl")
    logger.info("Done: %d paths in %.0f s", len(table), time.perf_counter() - t0)


if __name__ == "__main__":
    main()
