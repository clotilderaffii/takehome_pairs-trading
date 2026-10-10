"""Run the Phase 5 joint block bootstrap once and save the per-path table.

Pre-registered in EXPERIMENTS.md (2026-10-10 15:18 CEST): 500 paths, block 20, seed 2026,
split at the real split position. Writes data/processed/simulation_paths.pkl, which
notebooks/05_simulation.ipynb reloads (recomputing only if the parameters or data differ).
The KO/PEP appendix (pre-registered 17:24 CEST) uses the same script with other arguments.

Usage: uv run python scripts/run_simulation.py
       uv run python scripts/run_simulation.py --tickers KO PEP --split 2010-01-01 \
           --cache simulation_paths_KO_PEP.pkl
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date

from pairs.config import PROCESSED_DIR, SPLIT_DATE
from pairs.data import load_pair
from pairs.simulation import BootstrapParams, load_or_simulate

logger = logging.getLogger(__name__)

FULL_END = date(2026, 10, 10)  # exclusive: last available date is 2026-10-09


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", nargs=2, default=["INTC", "AMD"], metavar=("A", "B"))
    parser.add_argument("--split", default=SPLIT_DATE.isoformat(), help="first OOS date (ISO)")
    parser.add_argument("--cache", default="simulation_paths.pkl", help="file in data/processed/")
    parser.add_argument("--n-paths", type=int, default=BootstrapParams().n_paths)
    args = parser.parse_args()
    ticker_a, ticker_b = args.tickers

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("pairs.backtest", "pairs.spread"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    prices = load_pair(end=FULL_END, ticker_a=ticker_a, ticker_b=ticker_b)
    split_rows = int((prices.index < args.split).sum())
    params = BootstrapParams(n_paths=args.n_paths, split_index=split_rows)
    t0 = time.perf_counter()
    table = load_or_simulate(prices, params, PROCESSED_DIR / args.cache, ticker_a, ticker_b)
    logger.info("Done: %d paths in %.0f s", len(table), time.perf_counter() - t0)


if __name__ == "__main__":
    main()
