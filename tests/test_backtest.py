from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pairs.backtest import extract_trades, run_backtest, run_strategy


def _prices() -> pd.DataFrame:
    idx = pd.bdate_range("2012-01-02", periods=6)
    return pd.DataFrame(
        {
            "INTC": [100.0, 110.0, 99.0, 99.0, 108.9, 108.9],
            "AMD": [10.0, 10.0, 11.0, 11.0, 11.0, 12.1],
        },
        index=idx,
    )


def test_position_is_signal_shifted_and_pnl_uses_it() -> None:
    prices = _prices()
    beta = 0.5
    signal = pd.Series([1, 1, 0, 0, -1, 0], index=prices.index)
    d = run_backtest(prices, beta, signal, cost_bps=0.0, lag=1)
    assert d["position"].tolist() == [0, 1, 1, 0, 0, -1]
    r_a = prices["INTC"].pct_change().fillna(0)
    r_b = prices["AMD"].pct_change().fillna(0)
    expected = d["position"] * (r_a - beta * r_b) / 1.5
    np.testing.assert_allclose(d["gross_ret"].to_numpy(), expected.to_numpy())
    # Day 1: long, INTC +10%, AMD 0% -> 0.10 / 1.5
    assert d["gross_ret"].iloc[1] == pytest.approx(0.10 / 1.5)


def test_price_level_pnl_uses_previous_gross_capital() -> None:
    prices = _prices()
    beta = 0.5
    signal = pd.Series([1, 1, 0, 0, -1, 0], index=prices.index)
    d = run_backtest(prices, beta, signal, cost_bps=0.0, lag=1, use_logs=False)
    assert d["position"].tolist() == [0, 1, 1, 0, 0, -1]
    # Day 1: long 1 INTC / short 0.5 AMD; ΔINTC = +10, ΔAMD = 0; capital at t-1 = 100 + 0.5*10.
    assert d["gross_ret"].iloc[1] == pytest.approx(10.0 / 105.0)
    # Day 2: ΔINTC = -11, ΔAMD = +1; capital at t-1 = 110 + 0.5*10.
    assert d["gross_ret"].iloc[2] == pytest.approx((-11.0 - 0.5 * 1.0) / 115.0)
    # Day 5: short; ΔINTC = 0, ΔAMD = +1.1; capital at t-1 = 108.9 + 0.5*11.
    assert d["gross_ret"].iloc[5] == pytest.approx(-(0.0 - 0.5 * 1.1) / (108.9 + 5.5))


def test_lag_two_delays_one_more_day() -> None:
    prices = _prices()
    signal = pd.Series([1, 1, 0, 0, -1, 0], index=prices.index)
    d = run_backtest(prices, 0.5, signal, lag=2)
    assert d["position"].tolist() == [0, 0, 1, 1, 0, 0]


def test_costs_per_position_change() -> None:
    prices = _prices()
    # positions: 0, 1, -1 (flip), -1, 0, 0
    signal = pd.Series([1, -1, -1, 0, 0, 0], index=prices.index)
    d = run_backtest(prices, 0.5, signal, cost_bps=5.0)
    assert d["position"].tolist() == [0, 1, -1, -1, 0, 0]
    np.testing.assert_allclose(d["cost"].to_numpy(), [0, 5e-4, 10e-4, 0, 5e-4, 0])
    np.testing.assert_allclose(d["net_ret"], d["gross_ret"] - d["cost"])


def test_trade_from_starts_flat() -> None:
    prices = _prices()
    signal = pd.Series([1, 1, 1, 1, 1, 1], index=prices.index)
    start = prices.index[2].date()
    d = run_backtest(prices, 0.5, signal, trade_from=start)
    assert d.index[0] == pd.Timestamp(start)
    assert d["position"].tolist() == [0, 1, 1, 1]
    assert d["cost"].iloc[1] == pytest.approx(5e-4)


def test_extract_trades() -> None:
    idx = pd.bdate_range("2012-01-02", periods=7)
    daily = pd.DataFrame(
        {
            "position": [0, 1, 1, -1, 0, -1, -1],
            "gross_ret": [0.0, 0.01, 0.02, -0.01, 0.0, 0.03, 0.0],
        },
        index=idx,
    )
    t = extract_trades(daily, cost_bps=5.0)
    assert t["direction"].tolist() == [1, -1, -1]
    assert t["duration_days"].tolist() == [2, 1, 2]
    assert t["open_at_end"].tolist() == [False, False, True]
    assert t["gross_return"].iloc[0] == pytest.approx(1.01 * 1.02 - 1)
    assert t["net_return"].iloc[0] == pytest.approx(1.01 * 1.02 * (1 - 5e-4) ** 2 - 1)
    assert t["entry_date"].iloc[0] == idx[1] and t["exit_date"].iloc[0] == idx[2]


def test_run_strategy_respects_end(coint_prices: pd.DataFrame) -> None:
    end = coint_prices.index[1500].date()
    run = run_strategy(coint_prices, beta=0.8, entry=2.0, lookback=60, end=end)
    assert run.daily.index.max() < pd.Timestamp(end)
    assert {"spread", "z", "position", "net_ret"} <= set(run.daily.columns)
    assert not run.daily[["position", "net_ret"]].isna().to_numpy().any()


def test_run_strategy_with_other_tickers_matches_default(coint_prices: pd.DataFrame) -> None:
    renamed = coint_prices.rename(columns={"INTC": "KO", "AMD": "PEP"})
    default = run_strategy(coint_prices, beta=0.8, entry=2.0, lookback=60, end=date(2100, 1, 1))
    other = run_strategy(
        renamed,
        beta=0.8,
        entry=2.0,
        lookback=60,
        end=date(2100, 1, 1),
        ticker_a="KO",
        ticker_b="PEP",
    )
    pd.testing.assert_frame_equal(default.daily, other.daily)
    pd.testing.assert_frame_equal(default.trades, other.trades)


def test_run_strategy_makes_money_on_cointegrated_data(coint_prices: pd.DataFrame) -> None:
    run = run_strategy(coint_prices, beta=0.8, entry=2.0, lookback=60, end=date(2100, 1, 1))
    assert len(run.trades) > 5
    assert run.daily["gross_ret"].sum() > 0
