"""Positive and negative controls: the INTC/AMD pipeline on synthetic pairs with a known answer.

Validation of the code, not a strategy attempt. Positive control: a mean-reverting residual
(half-life 10 days) -> the pipeline must find beta ≈ 0.8, cointegration, and a clearly positive
net Sharpe in- and out-of-sample. Negative control: a random-walk residual -> no cointegration
and a net Sharpe near zero or negative.
"""

from __future__ import annotations

import pytest

from pairs.synthetic import (
    SYNTH_BETA,
    ControlResult,
    make_synthetic_pair,
    run_pipeline_control,
)

N_DAYS = 8000
SEED = 2026


@pytest.fixture(scope="module")
def positive() -> ControlResult:
    return run_pipeline_control(make_synthetic_pair(N_DAYS, seed=SEED, mean_reverting=True))


@pytest.fixture(scope="module")
def negative() -> ControlResult:
    return run_pipeline_control(make_synthetic_pair(N_DAYS, seed=SEED, mean_reverting=False))


def test_positive_control_recovers_the_relationship(positive: ControlResult) -> None:
    assert positive.fit.beta == pytest.approx(SYNTH_BETA, abs=0.01)
    assert positive.tests.eg_pvalue < 0.01
    assert 5 < positive.tests.half_life_days < 20  # true half-life: 10 days


def test_positive_control_is_profitable_in_and_out_of_sample(positive: ControlResult) -> None:
    assert positive.is_summary["sharpe_net"] > 1.0
    assert positive.oos_summary["sharpe_net"] > 1.0
    assert positive.is_summary["n_trades"] > 30 and positive.oos_summary["n_trades"] > 30


def test_negative_control_finds_no_relationship(negative: ControlResult) -> None:
    assert negative.tests.eg_pvalue > 0.1


def test_negative_control_is_not_profitable(negative: ControlResult) -> None:
    assert negative.is_summary["sharpe_net"] < 0.5
    assert negative.oos_summary["sharpe_net"] < 0.5


def test_controls_use_a_strict_is_oos_split(positive: ControlResult) -> None:
    split = positive.split_date
    assert positive.fit.last_date < split
    assert positive.is_run.daily.index.max().date() < split
    assert positive.oos_run.daily.index.min().date() >= split
    assert positive.oos_run.daily["position"].iloc[0] == 0
