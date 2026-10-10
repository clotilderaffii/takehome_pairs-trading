from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

TRUE_ALPHA = 0.5
TRUE_BETA = 0.8


def make_cointegrated_prices(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Prices with log P_A = 0.5 + 0.8 log P_B + AR(1) noise (phi = 0.9)."""
    rng = np.random.default_rng(seed)
    log_b = 3.0 + np.cumsum(rng.normal(0, 0.02, n))
    eps = np.zeros(n)
    for t in range(1, n):
        eps[t] = 0.9 * eps[t - 1] + rng.normal(0, 0.01)
    log_a = TRUE_ALPHA + TRUE_BETA * log_b + eps
    idx = pd.bdate_range("2000-01-03", periods=n)
    return pd.DataFrame({"INTC": np.exp(log_a), "AMD": np.exp(log_b)}, index=idx)


@pytest.fixture
def coint_prices() -> pd.DataFrame:
    return make_cointegrated_prices()
