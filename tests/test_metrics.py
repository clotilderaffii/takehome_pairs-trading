from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pairs.metrics import (
    annualized_return,
    annualized_volatility,
    max_drawdown,
    performance_summary,
    sharpe_ratio,
)


def test_annualized_return_constant_daily() -> None:
    r = pd.Series([0.001] * 252)
    assert annualized_return(r) == pytest.approx(1.001**252 - 1)


def test_annualized_return_two_years() -> None:
    r = pd.Series([0.0] * 503 + [0.21])  # +21% over 504 days = 2 years -> 10% a year
    assert annualized_return(r) == pytest.approx(0.10)


def test_volatility_and_sharpe() -> None:
    r = pd.Series([0.01, -0.01] * 126)
    assert annualized_volatility(r) == pytest.approx(r.std() * math.sqrt(252))
    assert sharpe_ratio(r) == pytest.approx(0.0, abs=1e-12)
    r2 = pd.Series([0.002, 0.0] * 126)
    assert sharpe_ratio(r2) == pytest.approx(r2.mean() / r2.std() * math.sqrt(252))


def test_sharpe_nan_when_flat() -> None:
    assert math.isnan(sharpe_ratio(pd.Series([0.0] * 10)))


def test_max_drawdown_known_path() -> None:
    # equity: 1 -> 1.1 -> 0.88 -> 0.968 ; peak 1.1, trough 0.88 -> -20%
    r = pd.Series([0.10, -0.20, 0.10])
    assert max_drawdown(r) == pytest.approx(-0.20)


def test_max_drawdown_from_start() -> None:
    assert max_drawdown(pd.Series([-0.5, 0.1])) == pytest.approx(-0.5)


def test_performance_summary_keys_and_trade_stats() -> None:
    idx = pd.bdate_range("2012-01-02", periods=4)
    daily = pd.DataFrame(
        {
            "position": [0, 1, 1, 0],
            "gross_ret": [0.0, 0.01, 0.01, 0.0],
            "net_ret": [0.0, 0.0095, 0.01, -0.0005],
        },
        index=idx,
    )
    trades = pd.DataFrame(
        {"duration_days": [2, 4], "net_return": [0.02, -0.01], "open_at_end": [False, True]}
    )
    s = performance_summary(daily, trades)
    assert s["n_trades"] == 2
    assert s["win_rate_net"] == pytest.approx(0.5)
    assert s["avg_duration_days"] == pytest.approx(3.0)
    assert s["max_duration_days"] == 4
    assert s["exposure"] == pytest.approx(0.5)
    assert s["n_open_at_end"] == 1
    assert np.isfinite(s["sharpe_gross"]) and np.isfinite(s["sharpe_net"])
