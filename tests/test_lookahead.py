"""Look-ahead test: with beta fixed, changing prices after date d must not change the past.

beta is estimated once on the whole in-sample period (declared limitation), so it is held
fixed here; the test checks everything downstream of beta, for both the log-price design
and the price-level robustness design.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pairs.backtest import run_backtest
from pairs.signal import positions_from_zscore, rolling_zscore
from pairs.spread import compute_spread
from tests.conftest import make_cointegrated_prices

BETA = 0.8


def _pipeline(prices: pd.DataFrame, lookback: int, entry: float, use_logs: bool) -> pd.DataFrame:
    spread = compute_spread(prices, BETA, use_logs=use_logs)
    z = rolling_zscore(spread, lookback)
    signal = positions_from_zscore(z, entry)
    daily = run_backtest(prices, BETA, signal, cost_bps=5.0, lag=1, use_logs=use_logs)
    return daily.join(spread).join(z)


@pytest.mark.parametrize("use_logs", [True, False])
@pytest.mark.parametrize(("lookback", "entry"), [(20, 1.5), (60, 2.0), (120, 2.5)])
def test_future_prices_do_not_change_the_past(lookback: int, entry: float, use_logs: bool) -> None:
    prices = make_cointegrated_prices(n=1500, seed=5)
    d = prices.index[900]

    rng = np.random.default_rng(42)
    tampered = prices.copy()
    future = tampered.index > d
    tampered.loc[future] *= np.exp(rng.normal(0, 0.3, size=(int(future.sum()), 2)))

    base = _pipeline(prices, lookback, entry, use_logs)
    alt = _pipeline(tampered, lookback, entry, use_logs)

    # The tampering really changes the future...
    assert not base.loc[future, "spread"].equals(alt.loc[future, "spread"])
    # ...but spread, z-score, signal, position and P&L up to d are identical.
    cols = ["spread", "z", "signal", "position", "gross_ret", "net_ret"]
    pd.testing.assert_frame_equal(base.loc[:d, cols], alt.loc[:d, cols])


def test_position_on_day_after_d_depends_only_on_signal_up_to_d() -> None:
    prices = make_cointegrated_prices(n=800, seed=6)
    daily = _pipeline(prices, 60, 2.0, use_logs=True)
    assert (daily["position"].iloc[1:].to_numpy() == daily["signal"].iloc[:-1].to_numpy()).all()
    assert daily["position"].iloc[0] == 0
    assert date(2000, 1, 3) == daily.index[0].date()
