"""Run the INTC/AMD look-elsewhere simulation once and save the per-window table.

Pre-registered in EXPERIMENTS.md (2026-10-10 18:37 CEST): the same bootstrap paths as Phase 5
(seed 2026, block 20), regenerated and checked against data/processed/simulation_paths.pkl;
windows with the length of the real window 1997-01-01 … 2004-12-31, starting every 252 rows.
The runtime estimate exceeded 20 minutes, so the first 200 paths are used (as pre-registered).
Writes data/processed/look_elsewhere_windows.pkl, reloaded by notebooks/05_simulation.ipynb.

Usage: uv run python scripts/run_look_elsewhere.py
"""

from __future__ import annotations

import logging
import pickle
import time
from dataclasses import asdict
from datetime import date

import pandas as pd

from pairs.config import PROCESSED_DIR
from pairs.data import load_pair
from pairs.simulation import BootstrapParams, look_elsewhere

logger = logging.getLogger(__name__)

FULL_END = date(2026, 10, 10)  # exclusive: last available date is 2026-10-09
WINDOW_START, WINDOW_END = date(1997, 1, 1), date(2004, 12, 31)
STEP = 252
N_PATHS = 200  # estimate for 500 paths ≈ 45 min > 20 min (pre-registered fallback)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("pairs.backtest", "pairs.spread"):
        logging.getLogger(noisy).setLevel(logging.ERROR)
    prices = load_pair(end=FULL_END)
    in_window = (prices.index >= pd.Timestamp(WINDOW_START)) & (
        prices.index <= pd.Timestamp(WINDOW_END)
    )
    window_len = int(in_window.sum())
    params = BootstrapParams()

    with (PROCESSED_DIR / "simulation_paths.pkl").open("rb") as f:
        phase5 = pickle.load(f)
    assert phase5["params"] == asdict(params), "Phase 5 checkpoint parameters differ"

    t0 = time.perf_counter()
    table = look_elsewhere(
        prices,
        params,
        window_len=window_len,
        step=STEP,
        n_paths=N_PATHS,
        expected_is_beta=phase5["table"]["beta"],
    )
    out = {
        "params": asdict(params),
        "window_len": window_len,
        "step": STEP,
        "n_paths": N_PATHS,
        "table": table,
    }
    with (PROCESSED_DIR / "look_elsewhere_windows.pkl").open("wb") as f:
        pickle.dump(out, f)
    logger.info(
        "Done: %d paths x %d windows (length %d) in %.0f s",
        N_PATHS,
        table.groupby("path").size().iloc[0],
        window_len,
        time.perf_counter() - t0,
    )


if __name__ == "__main__":
    main()
