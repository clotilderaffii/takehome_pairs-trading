from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pairs.exceptions import InsufficientDataError
from pairs.spread import compute_spread, fit_hedge_ratio, half_life, stationarity_tests
from tests.conftest import TRUE_ALPHA, TRUE_BETA, make_cointegrated_prices


def test_fit_recovers_known_alpha_beta(coint_prices: pd.DataFrame) -> None:
    fit = fit_hedge_ratio(coint_prices, end=date(2100, 1, 1))
    assert fit.beta == pytest.approx(TRUE_BETA, abs=0.02)
    assert fit.alpha == pytest.approx(TRUE_ALPHA, abs=0.1)
    assert 0.9 < fit.r_squared <= 1.0
    assert fit.n_obs == len(coint_prices)


def test_fit_ignores_data_on_or_after_end(coint_prices: pd.DataFrame) -> None:
    end = coint_prices.index[1000].date()
    base = fit_hedge_ratio(coint_prices, end=end)
    tampered = coint_prices.copy()
    tampered.loc[tampered.index >= pd.Timestamp(end)] *= 7.0
    again = fit_hedge_ratio(tampered, end=end)
    assert again == base
    assert base.n_obs == 1000
    assert base.last_date < end


def test_fit_raises_without_data_before_end(coint_prices: pd.DataFrame) -> None:
    with pytest.raises(InsufficientDataError):
        fit_hedge_ratio(coint_prices, end=date(1990, 1, 1))


def test_compute_spread_formula() -> None:
    idx = pd.to_datetime(["2012-01-03", "2012-01-04"])
    prices = pd.DataFrame({"INTC": [math.e, math.e**2], "AMD": [1.0, math.e]}, index=idx)
    s = compute_spread(prices, beta=0.5)
    np.testing.assert_allclose(s.to_numpy(), [1.0, 2.0 - 0.5])
    assert s.name == "spread"


def test_half_life_of_known_ar1() -> None:
    rng = np.random.default_rng(1)
    phi, n = 0.95, 20000
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal()
    b, hl = half_life(pd.Series(x))
    assert b == pytest.approx(phi - 1, abs=0.01)
    assert hl == pytest.approx(-math.log(2) / math.log(phi), rel=0.15)


def test_half_life_infinite_for_random_walk_like() -> None:
    s = pd.Series(np.arange(100, dtype=float) ** 2)  # explosive: b >= 0
    _, hl = half_life(s)
    assert hl == math.inf


def test_stationarity_detects_cointegration() -> None:
    prices = make_cointegrated_prices(n=3000, seed=2)
    res = stationarity_tests(prices, beta=TRUE_BETA, end=date(2100, 1, 1))
    assert res.eg_pvalue < 0.01
    assert res.adf_pvalue < 0.01
    assert res.ar1_coef < 0
    assert 0 < res.half_life_days < 50


def test_stationarity_rejects_independent_random_walks() -> None:
    rng = np.random.default_rng(3)
    n = 3000
    idx = pd.bdate_range("2000-01-03", periods=n)
    prices = pd.DataFrame(
        {
            "INTC": np.exp(3 + np.cumsum(rng.normal(0, 0.02, n))),
            "AMD": np.exp(3 + np.cumsum(rng.normal(0, 0.02, n))),
        },
        index=idx,
    )
    fit = fit_hedge_ratio(prices, end=date(2100, 1, 1))
    res = stationarity_tests(prices, beta=fit.beta, end=date(2100, 1, 1))
    assert res.eg_pvalue > 0.05
