from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pairs.simulation as simulation
from pairs.backtest import run_strategy
from pairs.metrics import performance_summary
from pairs.simulation import (
    BootstrapParams,
    bootstrap_indices,
    bootstrap_path,
    load_or_simulate,
    run_simulated_path,
)
from pairs.spread import fit_hedge_ratio
from pairs.synthetic import make_synthetic_pair


def test_bootstrap_indices_are_blocks_of_consecutive_days() -> None:
    rng = np.random.default_rng(0)
    idx = bootstrap_indices(1003, 20, rng)
    assert len(idx) == 1003
    blocks = [idx[i : i + 20] for i in range(0, 1003, 20)]
    for b in blocks:
        assert (np.diff(b) == 1).all()  # consecutive historical days inside each block
    assert len(blocks[-1]) == 1003 % 20  # last block truncated
    assert idx.min() >= 0 and idx.max() <= 1002


def test_bootstrap_indices_reproducible() -> None:
    a = bootstrap_indices(500, 20, np.random.default_rng(7))
    b = bootstrap_indices(500, 20, np.random.default_rng(7))
    c = bootstrap_indices(500, 20, np.random.default_rng(8))
    assert (a == b).all() and not (a == c).all()


def test_bootstrap_path_uses_the_same_dates_for_both_stocks() -> None:
    # Encode the historical day in the returns: day t has log return +t*1e-5 for A and -t*1e-5
    # for B. If both columns take the same date, A's and B's simulated returns are opposite.
    n = 300
    t = np.arange(1, n)
    log_a = np.concatenate([[np.log(10.0)], np.log(10.0) + np.cumsum(t * 1e-5)])
    log_b = np.concatenate([[np.log(5.0)], np.log(5.0) - np.cumsum(t * 1e-5)])
    idx = pd.bdate_range("2000-01-03", periods=n)
    prices = pd.DataFrame({"INTC": np.exp(log_a), "AMD": np.exp(log_b)}, index=idx)

    draw = bootstrap_indices(n - 1, 20, np.random.default_rng(1))
    path = bootstrap_path(prices, draw)
    ra = np.diff(np.log(path["INTC"].to_numpy()))
    rb = np.diff(np.log(path["AMD"].to_numpy()))
    np.testing.assert_allclose(ra, -rb, atol=1e-12)
    np.testing.assert_allclose(ra, (draw + 1) * 1e-5, atol=1e-12)  # and it is day draw[t]
    assert path.index.equals(prices.index)
    np.testing.assert_allclose(path.iloc[0].to_numpy(), prices.iloc[0].to_numpy())


def test_run_simulated_path_matches_phase2_functions() -> None:
    path = make_synthetic_pair(600, seed=3, mean_reverting=True)
    params = BootstrapParams(split_index=420)
    out = run_simulated_path(path, params)

    split = path.index[420].date()
    fit = fit_hedge_ratio(path, end=split)
    is_run = run_strategy(
        path, fit.beta, entry=2.0, lookback=60, end=split, trade_from=path.index[119].date()
    )
    oos_run = run_strategy(
        path, fit.beta, entry=2.0, lookback=60, end=date(2100, 1, 1), trade_from=split
    )
    assert out["beta"] == pytest.approx(fit.beta)
    assert out["is_sharpe_net"] == pytest.approx(
        performance_summary(is_run.daily, is_run.trades)["sharpe_net"]
    )
    assert out["oos_sharpe_net"] == pytest.approx(
        performance_summary(oos_run.daily, oos_run.trades)["sharpe_net"]
    )
    assert 0 <= out["eg_pvalue"] <= 1


def test_run_simulated_path_with_other_tickers_matches_default() -> None:
    path = make_synthetic_pair(600, seed=5, mean_reverting=True)
    params = BootstrapParams(split_index=420)
    default = run_simulated_path(path, params)
    renamed = path.rename(columns={"INTC": "KO", "AMD": "PEP"})
    other = run_simulated_path(renamed, params, ticker_a="KO", ticker_b="PEP")
    assert default == other


def test_load_or_simulate_uses_matching_cache_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prices = make_synthetic_pair(500, seed=4, mean_reverting=False)
    params = BootstrapParams(n_paths=2, split_index=350, seed=11)
    cache = tmp_path / "sim.pkl"

    first = load_or_simulate(prices, params, cache)
    assert len(first) == 2 and cache.exists()

    def _fail(*args: object, **kwargs: object) -> pd.DataFrame:
        raise AssertionError("should have loaded the cache")

    monkeypatch.setattr(simulation, "simulate", _fail)
    again = load_or_simulate(prices, params, cache)
    pd.testing.assert_frame_equal(first, again)

    with pytest.raises(AssertionError, match="should have loaded"):
        load_or_simulate(prices, BootstrapParams(n_paths=2, split_index=350, seed=12), cache)


def test_window_starts() -> None:
    from pairs.simulation import window_starts

    assert window_starts(1000, 300, 252) == [0, 252, 504]
    assert window_starts(300, 300, 252) == [0]


def test_evaluate_window_matches_manual_pipeline() -> None:
    from pairs.simulation import evaluate_window

    window = make_synthetic_pair(400, seed=7, mean_reverting=True)
    out = evaluate_window(window, BootstrapParams())
    end = date(2100, 1, 1)
    fit = fit_hedge_ratio(window, end=end)
    run = run_strategy(
        window, fit.beta, entry=2.0, lookback=60, end=end, trade_from=window.index[119].date()
    )
    assert out["beta"] == pytest.approx(fit.beta)
    assert out["sharpe_net"] == pytest.approx(
        performance_summary(run.daily, run.trades)["sharpe_net"]
    )
    assert 0 <= out["eg_pvalue"] <= 1


def test_look_elsewhere_regenerates_the_phase5_paths() -> None:
    from pairs.simulation import look_elsewhere, simulate

    prices = make_synthetic_pair(700, seed=8, mean_reverting=False)
    params = BootstrapParams(n_paths=3, split_index=490, seed=13)
    table5 = simulate(prices, params)
    windows = look_elsewhere(prices, params, window_len=300, expected_is_beta=table5["beta"])
    assert sorted(windows["path"].unique()) == [0, 1, 2]
    assert windows.groupby("path").size().tolist() == [2, 2, 2]  # starts 0 and 252
    with pytest.raises(AssertionError, match="differs from Phase 5"):
        look_elsewhere(prices, params, window_len=300, expected_is_beta=table5["beta"] + 1.0)


def test_look_elsewhere_summary_by_hand() -> None:
    from pairs.simulation import look_elsewhere_summary

    windows = pd.DataFrame(
        {
            "path": [0, 0, 1, 1],
            "start_row": [0, 252, 0, 252],
            "eg_pvalue": [0.01, 0.50, 0.30, 0.04],
            "sharpe_net": [0.2, 1.5, 0.1, 0.9],
        }
    )
    s = look_elsewhere_summary(windows, real_pvalue=0.05, real_sharpe=1.0)
    assert s["a_share_windows_p_lt_005"] == pytest.approx(50.0)
    assert s["b_share_paths_any_p_lt_005"] == pytest.approx(100.0)
    assert s["c_share_paths_any_as_good_as_real"] == pytest.approx(
        0.0
    )  # no window with p<=0.05 and SR>=1
    assert s["d_best_sharpe_median"] == pytest.approx(1.2)
    assert s["d_real_percentile_among_best"] == pytest.approx(50.0)  # best SRs 1.5 and 0.9
