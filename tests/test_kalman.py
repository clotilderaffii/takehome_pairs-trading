from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from pairs.kalman import (
    kalman_filter,
    kalman_zscore,
    run_backtest_dynamic,
    run_kalman_strategy,
    summary_on_window,
)
from pairs.spread import log_prices
from tests.conftest import TRUE_BETA, make_cointegrated_prices

FAR_END = date(2100, 1, 1)


def test_filter_recovers_known_beta() -> None:
    prices = make_cointegrated_prices(n=2000, seed=21)
    state = kalman_filter(prices, end=FAR_END, delta=1e-4)
    assert state.iloc[:252].isna().all().all()
    assert state["beta"].iloc[1000:].mean() == pytest.approx(TRUE_BETA, abs=0.05)


def test_filter_first_step_by_hand() -> None:
    prices = make_cointegrated_prices(n=300, seed=22)
    delta, v = 1e-4, 0.001
    state = kalman_filter(prices, end=FAR_END, delta=delta, v=v)
    logp = log_prices(prices)
    y, xb = logp["INTC"].to_numpy(), logp["AMD"].to_numpy()
    ols = sm.OLS(y[:252], sm.add_constant(xb[:252])).fit()
    x0, p0 = np.asarray(ols.params), np.asarray(ols.cov_params())
    p_pred = p0 + delta / (1 - delta) * np.eye(2)
    h = np.array([1.0, xb[252]])
    e = y[252] - h @ x0
    s = h @ p_pred @ h + v
    x1 = x0 + p_pred @ h / s * e
    assert state["alpha"].iloc[252] == pytest.approx(x1[0])
    assert state["beta"].iloc[252] == pytest.approx(x1[1])
    assert state["innovation"].iloc[252] == pytest.approx(e)
    assert state["innovation_var"].iloc[252] == pytest.approx(s)


def test_zscore_matches_brute_force() -> None:
    prices = make_cointegrated_prices(n=400, seed=23)
    beta = kalman_filter(prices, end=FAR_END, delta=1e-4)["beta"]
    z = kalman_zscore(prices, beta, lookback=60)
    logp = log_prices(prices)
    for t in (260, 320, 399):
        w = logp.iloc[t - 59 : t + 1]
        s = w["INTC"] - beta.iloc[t] * w["AMD"]
        expected = (s.iloc[-1] - s.mean()) / s.std(ddof=1)
        assert z.iloc[t] == pytest.approx(expected, rel=1e-7)
    assert z.iloc[:252].isna().all()


def test_dynamic_pnl_uses_previous_day_beta_and_position() -> None:
    idx = pd.bdate_range("2012-01-02", periods=4)
    prices = pd.DataFrame(
        {"INTC": [100.0, 110.0, 99.0, 99.0], "AMD": [10.0, 10.0, 11.0, 11.0]}, index=idx
    )
    beta = pd.Series([0.5, 2.0, 1.0, 1.0], index=idx)
    signal = pd.Series([1, -1, 0, 0], index=idx)
    d = run_backtest_dynamic(prices, beta, signal, cost_bps=5.0)
    assert d["position"].tolist() == [0, 1, -1, 0]
    # day 1: long, beta_0 = 0.5; INTC +10%, AMD 0%
    assert d["gross_ret"].iloc[1] == pytest.approx(0.10 / 1.5)
    # day 2: short, beta_1 = 2.0; INTC -10%, AMD +10%
    assert d["gross_ret"].iloc[2] == pytest.approx(-(-0.10 - 2.0 * 0.10) / 3.0)
    np.testing.assert_allclose(d["cost"].to_numpy(), [0, 5e-4, 10e-4, 5e-4])


def test_kalman_does_not_look_ahead() -> None:
    prices = make_cointegrated_prices(n=900, seed=24)
    d_pos = 600
    d = prices.index[d_pos]
    rng = np.random.default_rng(25)
    tampered = prices.copy()
    future = tampered.index > d
    tampered.loc[future] *= np.exp(rng.normal(0, 0.3, size=(int(future.sum()), 2)))

    start = prices.index[252].date()
    base = run_kalman_strategy(prices, delta=1e-4, end=FAR_END, trade_from=start).daily
    alt = run_kalman_strategy(tampered, delta=1e-4, end=FAR_END, trade_from=start).daily
    after = base.index > d
    assert not base.loc[after, "beta"].equals(alt.loc[after, "beta"])
    cols = ["alpha", "beta", "z", "signal", "position", "gross_ret", "net_ret"]
    pd.testing.assert_frame_equal(base.loc[:d, cols], alt.loc[:d, cols])


def test_oos_run_continues_the_is_filter() -> None:
    prices = make_cointegrated_prices(n=900, seed=26)
    split = prices.index[600].date()
    full = kalman_filter(prices, end=FAR_END, delta=1e-4)
    is_only = kalman_filter(prices, end=split, delta=1e-4)
    pd.testing.assert_frame_equal(full.loc[is_only.index], is_only)


def test_summary_on_window_excludes_trade_open_at_start() -> None:
    idx = pd.bdate_range("2012-01-02", periods=6)
    daily = pd.DataFrame(
        {
            "position": [1, 1, 0, -1, -1, 0],
            "gross_ret": [0.01, 0.01, 0.0, 0.02, 0.0, 0.0],
            "net_ret": [0.01, 0.01, 0.0, 0.02, 0.0, 0.0],
        },
        index=idx,
    )
    trades = pd.DataFrame(
        {
            "entry_date": [idx[0], idx[3]],
            "exit_date": [idx[1], idx[4]],
            "duration_days": [2, 2],
            "net_return": [0.02, 0.02],
            "open_at_end": [False, False],
        }
    )
    summary, n_open = summary_on_window(daily, trades, start=idx[1].date())
    assert n_open == 1
    assert summary["n_trades"] == 1
    assert summary["exposure"] == pytest.approx(3 / 5)
