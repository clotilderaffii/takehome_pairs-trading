from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pairs.signal import positions_from_zscore, rolling_zscore


def test_rolling_zscore_matches_manual() -> None:
    s = pd.Series([1.0, 2.0, 4.0, 7.0, 11.0])
    z = rolling_zscore(s, lookback=3)
    assert z.iloc[:2].isna().all()
    window = np.array([2.0, 4.0, 7.0])
    expected = (7.0 - window.mean()) / window.std(ddof=1)
    assert z.iloc[3] == pytest.approx(expected)
    assert z.name == "z"


def test_rolling_zscore_rejects_tiny_lookback() -> None:
    with pytest.raises(AssertionError):
        rolling_zscore(pd.Series([1.0, 2.0]), lookback=1)


def _pos(z_values: list[float], entry: float = 2.0) -> list[int]:
    return positions_from_zscore(pd.Series(z_values, dtype=float), entry).tolist()


def test_positions_entry_hold_exit_long() -> None:
    #        warm-up  flat  enter  hold  hold  exit(z>=0)  flat
    z = [np.nan, 0.5, -2.1, -1.0, -0.1, 0.0, -1.5]
    assert _pos(z) == [0, 0, 1, 1, 1, 0, 0]


def test_positions_entry_hold_exit_short() -> None:
    z = [2.5, 1.0, 0.2, -0.3, 1.0]
    assert _pos(z) == [-1, -1, -1, 0, 0]


def test_positions_threshold_is_strict() -> None:
    assert _pos([-2.0, 2.0]) == [0, 0]


def test_positions_direct_flip() -> None:
    z = [-2.5, 2.6, 1.0, -0.5]
    assert _pos(z) == [1, -1, -1, 0]


def test_positions_values_are_valid() -> None:
    rng = np.random.default_rng(0)
    p = positions_from_zscore(pd.Series(rng.normal(0, 1.5, 1000)), entry=1.5)
    assert set(p.unique()) <= {-1, 0, 1}
    assert p.dtype.kind == "i"
