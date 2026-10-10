from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from pairs.exceptions import DataFetchError
from pairs.short_interest import (
    build_periods,
    critical_spearman,
    days_to_cover_floor,
    load_short_interest,
    next_trading_day,
    publication_dates,
    spearman_tests,
)


def _write_si(raw_dir: Path, ticker: str, rows: list[dict[str, object]], rcode: int = 200) -> None:
    payload = {
        "data": {"symbol": ticker.lower(), "shortInterestTable": {"rows": rows}},
        "status": {"rCode": rcode},
    }
    path = raw_dir / f"{ticker}_short_interest_nasdaq_20261010T000000Z.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def _row(d: str, si: str, vol: str = "1,000", dtc: float = 2.5) -> dict[str, object]:
    return {"settlementDate": d, "interest": si, "avgDailyShareVolume": vol, "daysToCover": dtc}


def test_load_short_interest_parses_and_sorts(tmp_path: Path) -> None:
    _write_si(
        tmp_path, "XYZ", [_row("02/27/2026", "1,200,000", dtc=1.0), _row("02/13/2026", "1,000,000")]
    )
    si = load_short_interest("XYZ", raw_dir=tmp_path)
    assert list(si.index) == [pd.Timestamp("2026-02-13"), pd.Timestamp("2026-02-27")]
    assert si["short_interest"].tolist() == [1_000_000, 1_200_000]
    assert si["avg_daily_volume"].tolist() == [1000, 1000]
    assert list(days_to_cover_floor(si)) == [pd.Timestamp("2026-02-27")]


def test_load_short_interest_errors(tmp_path: Path) -> None:
    with pytest.raises(DataFetchError, match="No short-interest file"):
        load_short_interest("NOPE", raw_dir=tmp_path)
    _write_si(tmp_path, "BAD", [_row("02/13/2026", "1")], rcode=400)
    with pytest.raises(DataFetchError, match="status"):
        load_short_interest("BAD", raw_dir=tmp_path)
    _write_si(tmp_path, "EMPTY", [])
    with pytest.raises(DataFetchError, match="empty"):
        load_short_interest("EMPTY", raw_dir=tmp_path)


def test_publication_dates_add_seven_business_days() -> None:
    settle = pd.DatetimeIndex(["2026-09-30", "2025-10-31", "2026-01-15"])
    pub = publication_dates(settle)
    # Wed 2026-09-30 -> Fri 2026-10-09; Fri 2025-10-31 -> Tue 2025-11-11 (weekends skipped)
    assert list(pub[:2]) == [pd.Timestamp("2026-10-09"), pd.Timestamp("2025-11-11")]
    # Thu 2026-01-15 -> Mon 2026-01-26
    assert pub[2] == pd.Timestamp("2026-01-26")


def test_next_trading_day() -> None:
    trading = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-07"])
    out = next_trading_day(pd.DatetimeIndex(["2026-01-02", "2026-01-03", "2026-01-06"]), trading)
    assert list(out) == [
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-05"),
        pd.Timestamp("2026-01-07"),
    ]
    with pytest.raises(DataFetchError):
        next_trading_day(pd.DatetimeIndex(["2026-01-08"]), trading)


def test_build_periods_by_hand() -> None:
    idx = pd.bdate_range("2026-01-05", periods=6)  # Mon..Mon
    prices = pd.DataFrame(
        {"INTC": [10.0, 11.0, 12.1, 12.1, 11.0, 11.0], "AMD": [20.0, 20.0, 22.0, 22.0, 22.0, 24.2]},
        index=idx,
    )
    settle = pd.DatetimeIndex([idx[0], idx[2], idx[5]], name="settlement_date")
    si_a = pd.DataFrame({"short_interest": [100, 110, 99], "days_to_cover": 2.0}, index=settle)
    si_b = pd.DataFrame({"short_interest": [200, 200, 300], "days_to_cover": 2.0}, index=settle)

    p = build_periods(si_a, si_b, prices, beta=1.0, end=date(2100, 1, 1), use_publication=False)
    assert len(p) == 2
    np.testing.assert_allclose(p["si_chg_INTC"], [0.10, -0.10])
    np.testing.assert_allclose(p["si_chg_AMD"], [0.0, 0.5])
    np.testing.assert_allclose(p["si_chg_diff"], [0.10, -0.60])
    np.testing.assert_allclose(p["ret_INTC"], [0.21, 11.0 / 12.1 - 1])
    np.testing.assert_allclose(p["ret_AMD"], [0.10, 0.10])
    expected_spread = [math.log(1.21) - math.log(1.1), math.log(11 / 12.1) - math.log(1.1)]
    np.testing.assert_allclose(p["spread_chg"], expected_spread)
    # Period 1 days: idx[1] (INTC +10%), idx[2] (INTC +10%, AMD +10%) -> max 0.10
    assert p["max_abs_ret"].iloc[0] == pytest.approx(0.10)
    assert p["start"].iloc[1] == idx[2] and p.index[1] == idx[5]


def test_build_periods_publication_shift() -> None:
    idx = pd.bdate_range("2026-01-05", periods=40)
    rng = np.random.default_rng(0)
    prices = pd.DataFrame(
        {
            "INTC": np.exp(np.cumsum(rng.normal(0, 0.01, 40))),
            "AMD": np.exp(np.cumsum(rng.normal(0, 0.01, 40))),
        },
        index=idx,
    )
    settle = pd.DatetimeIndex([idx[0], idx[10], idx[20]])
    si = pd.DataFrame({"short_interest": [1, 2, 3], "days_to_cover": 1.5}, index=settle)
    p = build_periods(si, si, prices, beta=1.0, end=date(2100, 1, 1), use_publication=True)
    assert p["start"].iloc[0] == idx[7] and p.index[0] == idx[17] and p.index[1] == idx[27]


def test_critical_spearman_matches_pvalue() -> None:
    n = 23
    r = critical_spearman(n)
    assert r == pytest.approx(0.413, abs=0.002)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    assert 2 * stats.t.sf(t, n - 2) == pytest.approx(0.05, abs=1e-9)


def test_spearman_tests_shape_and_values() -> None:
    n = 23
    x = np.arange(n, dtype=float)
    periods = pd.DataFrame(
        {
            "si_chg_INTC": x,
            "si_chg_AMD": -x,
            "si_chg_diff": 2 * x,
            "spread_chg": x**3,
            "max_abs_ret": np.r_[x[1:], x[:1]],
        }
    )
    out = spearman_tests(periods)
    assert out["question"].tolist() == ["Q1", "Q1", "Q2", "Q3", "Q3"]
    assert out["rho"].iloc[0] == pytest.approx(1.0)
    assert out["rho"].iloc[1] == pytest.approx(-1.0)
    assert out["rho"].iloc[2] == pytest.approx(1.0)
    assert (out["n"] == n).all()
    assert bool(out["significant_bonferroni"].iloc[0])
