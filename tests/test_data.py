from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pairs.data import (
    daily_returns,
    load_close,
    load_pair,
    raw_price_path,
    return_correlation_table,
)
from pairs.exceptions import DataFetchError


def _write_raw(raw_dir: Path, ticker: str, dates: list[str], closes: list[float]) -> None:
    idx = pd.DatetimeIndex(pd.to_datetime(dates), name="Date")
    df = pd.DataFrame({"Close": closes, "Volume": 1}, index=idx)
    df.to_pickle(raw_price_path(ticker, raw_dir))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    _write_raw(
        tmp_path,
        "AAA",
        ["2012-12-27", "2012-12-28", "2012-12-31", "2013-01-02", "2013-01-03"],
        [10.0, 11.0, 12.0, 13.0, 14.0],
    )
    # BBB lacks 2012-12-28 and has an extra date AAA does not have.
    _write_raw(
        tmp_path,
        "BBB",
        ["2012-12-26", "2012-12-27", "2012-12-31", "2013-01-02"],
        [5.0, 4.0, 2.0, 1.0],
    )
    return tmp_path


def test_load_close_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DataFetchError, match="not found"):
        load_close("NOPE", end=date(2013, 1, 1), raw_dir=tmp_path)


def test_load_close_cutoff_is_exclusive(raw_dir: Path) -> None:
    s = load_close("AAA", end=date(2013, 1, 2), raw_dir=raw_dir)
    assert s.index.max() == pd.Timestamp("2012-12-31")
    assert pd.Timestamp("2013-01-02") not in s.index
    assert s.name == "AAA"


def test_load_close_nothing_before_end_raises(raw_dir: Path) -> None:
    with pytest.raises(DataFetchError, match="no prices"):
        load_close("AAA", end=date(2000, 1, 1), raw_dir=raw_dir)


def test_load_close_rejects_non_positive_prices(tmp_path: Path) -> None:
    _write_raw(tmp_path, "NEG", ["2012-01-03", "2012-01-04"], [1.0, 0.0])
    with pytest.raises(DataFetchError, match="non-positive"):
        load_close("NEG", end=date(2013, 1, 1), raw_dir=tmp_path)


def test_load_close_drops_missing_values(tmp_path: Path) -> None:
    _write_raw(tmp_path, "GAP", ["2012-01-03", "2012-01-04", "2012-01-05"], [1.0, np.nan, 2.0])
    s = load_close("GAP", end=date(2013, 1, 1), raw_dir=tmp_path)
    assert list(s.index) == [pd.Timestamp("2012-01-03"), pd.Timestamp("2012-01-05")]


def test_load_pair_aligns_on_common_dates_before_end(raw_dir: Path) -> None:
    prices = load_pair(end=date(2013, 1, 1), ticker_a="AAA", ticker_b="BBB", raw_dir=raw_dir)
    assert list(prices.columns) == ["AAA", "BBB"]
    assert list(prices.index) == [pd.Timestamp("2012-12-27"), pd.Timestamp("2012-12-31")]
    assert prices.loc["2012-12-31", "AAA"] == 12.0
    assert prices.loc["2012-12-31", "BBB"] == 2.0


def test_load_pair_no_common_dates_raises(tmp_path: Path) -> None:
    _write_raw(tmp_path, "XXX", ["2012-01-03"], [1.0])
    _write_raw(tmp_path, "YYY", ["2012-01-04"], [1.0])
    with pytest.raises(DataFetchError, match="share no dates"):
        load_pair(end=date(2013, 1, 1), ticker_a="XXX", ticker_b="YYY", raw_dir=tmp_path)


def test_daily_returns_values() -> None:
    idx = pd.to_datetime(["2012-01-03", "2012-01-04", "2012-01-05"])
    prices = pd.DataFrame({"A": [100.0, 110.0, 99.0], "B": [10.0, 10.0, 12.0]}, index=idx)
    r = daily_returns(prices)
    assert list(r.index) == list(idx[1:])
    np.testing.assert_allclose(r["A"].to_numpy(), [0.10, -0.10])
    np.testing.assert_allclose(r["B"].to_numpy(), [0.0, 0.20])


def test_daily_returns_rejects_nan() -> None:
    idx = pd.to_datetime(["2012-01-03", "2012-01-04"])
    prices = pd.DataFrame({"A": [1.0, np.nan], "B": [1.0, 2.0]}, index=idx)
    with pytest.raises(AssertionError):
        daily_returns(prices)


def test_return_correlation_table_by_decade() -> None:
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("1998-01-01", "2001-12-31")
    x = rng.normal(size=len(idx))
    in_90s = idx.year < 2000
    # Perfectly correlated in the 1990s, perfectly anti-correlated in the 2000s.
    y = np.where(in_90s, 2 * x, -x)
    table = return_correlation_table(pd.DataFrame({"A": x, "B": y}, index=idx))

    assert list(table.index) == ["All", "1990s", "2000s"]
    assert table.loc["1990s", "correlation"] == pytest.approx(1.0)
    assert table.loc["2000s", "correlation"] == pytest.approx(-1.0)
    assert table.loc["1990s", "n_days"] == int(in_90s.sum())
    assert table.loc["All", "n_days"] == len(idx)
    assert table.loc["2000s", "start"] == date(2000, 1, 3)
