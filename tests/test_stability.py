from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pairs.exceptions import InsufficientDataError
from pairs.spread import log_prices
from pairs.stability import regime_comparison, rolling_adf, rolling_beta, weak_flag
from tests.conftest import TRUE_BETA, make_cointegrated_prices

FAR_END = date(2100, 1, 1)


def test_rolling_beta_matches_polyfit() -> None:
    prices = make_cointegrated_prices(n=600, seed=7)
    beta = rolling_beta(prices, end=FAR_END, window=252)
    assert beta.iloc[:251].isna().all()
    logp = log_prices(prices)
    for t in (251, 400, 599):
        w = logp.iloc[t - 251 : t + 1]
        slope = np.polyfit(w["AMD"], w["INTC"], 1)[0]
        assert beta.iloc[t] == pytest.approx(slope, rel=1e-9)


def test_rolling_beta_needs_a_full_window() -> None:
    prices = make_cointegrated_prices(n=100, seed=7)
    with pytest.raises(InsufficientDataError):
        rolling_beta(prices, end=FAR_END, window=252)


def test_rolling_adf_schedule_and_beta() -> None:
    prices = make_cointegrated_prices(n=700, seed=8)
    table = rolling_adf(prices, end=FAR_END, window=252, step=21)
    expected_dates = prices.index[list(range(251, 700, 21))]
    assert table.index.equals(pd.DatetimeIndex(expected_dates, name="date"))
    beta = rolling_beta(prices, end=FAR_END, window=252)
    np.testing.assert_allclose(table["beta"].to_numpy(), beta.loc[table.index].to_numpy())


def test_rolling_adf_separates_cointegrated_from_independent() -> None:
    coint = rolling_adf(make_cointegrated_prices(n=1200, seed=9), end=FAR_END)
    assert (coint["adf_pvalue"] < 0.05).mean() > 0.8
    assert coint["beta"].median() == pytest.approx(TRUE_BETA, abs=0.15)

    rng = np.random.default_rng(10)
    n = 1200
    idx = pd.bdate_range("2000-01-03", periods=n)
    indep = pd.DataFrame(
        {
            "INTC": np.exp(3 + np.cumsum(rng.normal(0, 0.02, n))),
            "AMD": np.exp(3 + np.cumsum(rng.normal(0, 0.02, n))),
        },
        index=idx,
    )
    table = rolling_adf(indep, end=FAR_END)
    assert (table["adf_pvalue"] > 0.05).mean() > 0.5


def test_weak_flag_uses_previous_computation_only() -> None:
    idx = pd.bdate_range("2012-01-02", periods=8)
    adf = pd.DataFrame({"adf_pvalue": [0.01, 0.20]}, index=idx[[2, 5]])
    flag = weak_flag(adf, idx, threshold=0.05)
    # days 0-2: no result yet (the day-2 computation applies from day 3)
    assert flag.iloc[:3].isna().all()
    # days 3-5: strong (p = 0.01), including day 5, the next computation day
    assert flag.iloc[3:6].tolist() == [False, False, False]
    # days 6-7: weak (p = 0.20 computed at the close of day 5)
    assert flag.iloc[6:].tolist() == [True, True]


def test_flag_does_not_look_ahead() -> None:
    prices = make_cointegrated_prices(n=900, seed=11)
    d_pos = 600
    d = prices.index[d_pos]

    rng = np.random.default_rng(12)
    tampered = prices.copy()
    future = tampered.index >= d
    tampered.loc[future] *= np.exp(rng.normal(0, 0.3, size=(int(future.sum()), 2)))

    beta0 = rolling_beta(prices, end=FAR_END)
    beta1 = rolling_beta(tampered, end=FAR_END)
    pd.testing.assert_series_equal(beta0.iloc[:d_pos], beta1.iloc[:d_pos])

    adf0 = rolling_adf(prices, end=FAR_END)
    adf1 = rolling_adf(tampered, end=FAR_END)
    pd.testing.assert_frame_equal(adf0[adf0.index < d], adf1[adf1.index < d])
    assert not adf0[adf0.index >= d].equals(adf1[adf1.index >= d])

    flag0 = weak_flag(adf0, pd.DatetimeIndex(prices.index))
    flag1 = weak_flag(adf1, pd.DatetimeIndex(tampered.index))
    # The flag on day d itself uses data up to d-1 only, so it is unchanged too.
    pd.testing.assert_series_equal(flag0.loc[:d], flag1.loc[:d])


def test_regime_comparison_by_hand() -> None:
    idx = pd.bdate_range("2012-01-02", periods=6)
    daily = pd.DataFrame(
        {
            "net_ret": [0.0, 0.01, 0.02, -0.01, 0.0, -0.03],
            "position": [0, 1, 1, -1, 0, -1],
        },
        index=idx,
    )
    flag = pd.Series([pd.NA, False, False, True, True, True], index=idx, dtype="boolean")
    trades = pd.DataFrame(
        {
            "entry_date": [idx[1], idx[3], idx[5]],
            "net_return": [0.03, -0.01, -0.03],
        }
    )
    res = regime_comparison(daily, trades, flag)
    t = res.table
    assert res.n_days_unflagged == 1 and res.n_trades_unflagged == 0
    assert t.loc["strong", "n_days"] == 2 and t.loc["weak", "n_days"] == 3
    assert t.loc["weak", "share_days"] == pytest.approx(0.6)
    assert t.loc["weak", "exposure"] == pytest.approx(2 / 3)
    assert t.loc["strong", "mean_daily_net"] == pytest.approx(0.015)
    assert t.loc["weak", "mean_daily_net"] == pytest.approx(-0.04 / 3)
    assert t.loc["strong", "n_trades"] == 1 and t.loc["weak", "n_trades"] == 2
    assert t.loc["strong", "win_rate_net"] == 1.0 and t.loc["weak", "win_rate_net"] == 0.0
    assert t.loc["weak", "max_dd"] == pytest.approx(0.99 * 0.97 - 1)
    assert res.welch_t < 0
