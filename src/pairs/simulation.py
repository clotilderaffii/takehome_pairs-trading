"""Phase 5: joint block bootstrap of the pair and re-run of the Phase 2 signal on each path."""

from __future__ import annotations

import logging
import math
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pairs.backtest import run_strategy
from pairs.config import TICKER_A, TICKER_B
from pairs.metrics import performance_summary
from pairs.spread import fit_hedge_ratio, log_prices, stationarity_tests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapParams:
    """Pre-registered parameters of the Phase 5 simulation (EXPERIMENTS.md, 15:18 CEST).

    Attributes
    ----------
    block : int
        Block length in trading days.
    n_paths : int
        Number of simulated paths.
    seed : int
        Seed of the random generator.
    split_index : int
        Row of the first simulated OOS day (same position as the real split).
    entry, lookback, cost_bps, lag : float, int, float, int
        Phase 2 main configuration.
    is_warmup : int
        The simulated IS is evaluated from row ``is_warmup − 1`` (first L = 120 z-score day).
    """

    block: int = 20
    n_paths: int = 500
    seed: int = 2026
    split_index: int = 8273
    entry: float = 2.0
    lookback: int = 60
    cost_bps: float = 5.0
    lag: int = 1
    is_warmup: int = 120


def bootstrap_indices(n_returns: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Row indices of one moving-block bootstrap path.

    Parameters
    ----------
    n_returns : int
        Number of historical daily returns (and of returns in the path).
    block : int
        Block length.
    rng : np.random.Generator
        Random generator (advanced in place).

    Returns
    -------
    np.ndarray
        Integer array of length ``n_returns``: concatenated runs ``start, start+1, …,
        start+block−1`` with ``start`` uniform on ``[0, n_returns − block]``; the last run is
        truncated.

    Notes
    -----
    The same indices are applied to both stocks, so each simulated day takes the returns of
    both stocks from the *same* historical date.
    """
    assert 0 < block <= n_returns
    n_blocks = math.ceil(n_returns / block)
    starts = rng.integers(0, n_returns - block + 1, size=n_blocks)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n_returns]
    assert len(idx) == n_returns and idx.min() >= 0 and idx.max() < n_returns
    return idx


def bootstrap_path(prices: pd.DataFrame, idx: np.ndarray) -> pd.DataFrame:
    """Rebuild a price path from resampled joint log returns.

    Parameters
    ----------
    prices : pd.DataFrame
        Real aligned prices (n rows).
    idx : np.ndarray
        Output of :func:`bootstrap_indices` with ``n − 1`` entries.

    Returns
    -------
    pd.DataFrame
        Simulated prices with the same index and columns as ``prices``; the first row equals
        the real first prices, and day t's log returns are the real log returns of the
        historical day ``idx[t − 1]`` for *both* columns.
    """
    logp = log_prices(prices).to_numpy()
    rets = np.diff(logp, axis=0)
    assert len(idx) == len(rets)
    sim = np.vstack([logp[:1], logp[:1] + np.cumsum(rets[idx], axis=0)])
    return pd.DataFrame(np.exp(sim), index=prices.index, columns=prices.columns)


def run_simulated_path(
    path: pd.DataFrame,
    params: BootstrapParams,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> dict[str, float]:
    """Repeat the Phase 2 procedure on one simulated path.

    Parameters
    ----------
    path : pd.DataFrame
        Simulated prices (columns ``ticker_a``, ``ticker_b``).
    params : BootstrapParams
        Simulation parameters.
    ticker_a, ticker_b : str, optional
        Legs A and B (defaults: INTC, AMD).

    Returns
    -------
    dict[str, float]
        ``beta``, ``eg_pvalue`` (simulated IS), and for ``is``/``oos``: ``sharpe_net``,
        ``sharpe_gross``, ``ann_return_net``, ``n_trades``.

    Notes
    -----
    beta and the Engle-Granger test use the simulated IS only (rows < ``split_index``); the
    simulated OOS uses the frozen beta, starts flat, and takes its z-score warm-up from the
    last IS rows — exactly as Phase 2 / OOS access #1 on real data.
    """
    idx = path.index
    split_date = idx[params.split_index].date()
    end_all = (idx[-1] + pd.Timedelta(days=1)).date()

    fit = fit_hedge_ratio(path, end=split_date, ticker_a=ticker_a, ticker_b=ticker_b)
    tests = stationarity_tests(
        path, beta=fit.beta, end=split_date, ticker_a=ticker_a, ticker_b=ticker_b
    )
    is_run = run_strategy(
        path,
        fit.beta,
        entry=params.entry,
        lookback=params.lookback,
        end=split_date,
        trade_from=idx[params.is_warmup - 1].date(),
        lag=params.lag,
        cost_bps=params.cost_bps,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
    )
    oos_run = run_strategy(
        path,
        fit.beta,
        entry=params.entry,
        lookback=params.lookback,
        end=end_all,
        trade_from=split_date,
        lag=params.lag,
        cost_bps=params.cost_bps,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
    )
    out: dict[str, float] = {"beta": fit.beta, "eg_pvalue": tests.eg_pvalue}
    for name, run in (("is", is_run), ("oos", oos_run)):
        s = performance_summary(run.daily, run.trades)
        out[f"{name}_sharpe_net"] = s["sharpe_net"]
        out[f"{name}_sharpe_gross"] = s["sharpe_gross"]
        out[f"{name}_ann_return_net"] = s["ann_return_net"]
        out[f"{name}_n_trades"] = s["n_trades"]
    return out


def simulate(
    prices: pd.DataFrame,
    params: BootstrapParams,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Run all bootstrap paths.

    Parameters
    ----------
    prices : pd.DataFrame
        Real aligned prices over the full history.
    params : BootstrapParams
        Simulation parameters.
    ticker_a, ticker_b : str, optional
        Legs A and B (defaults: INTC, AMD).

    Returns
    -------
    pd.DataFrame
        One row per path (index ``path``), columns of :func:`run_simulated_path`.
    """
    prices = prices[[ticker_a, ticker_b]]
    assert params.split_index < len(prices)
    rng = np.random.default_rng(params.seed)
    rows = []
    for k in range(params.n_paths):
        idx = bootstrap_indices(len(prices) - 1, params.block, rng)
        rows.append(run_simulated_path(bootstrap_path(prices, idx), params, ticker_a, ticker_b))
        if (k + 1) % 50 == 0:
            logger.info("Simulated %d / %d paths", k + 1, params.n_paths)
    table = pd.DataFrame(rows)
    table.index.name = "path"
    return table


def load_or_simulate(
    prices: pd.DataFrame,
    params: BootstrapParams,
    cache: Path,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Load the per-path table from ``cache`` if its parameters and data match, else compute it.

    Parameters
    ----------
    prices : pd.DataFrame
        Real aligned prices over the full history.
    params : BootstrapParams
        Simulation parameters.
    cache : Path
        Pickle checkpoint, e.g. ``data/processed/simulation_paths.pkl``.
    ticker_a, ticker_b : str, optional
        Legs A and B (defaults: INTC, AMD).

    Returns
    -------
    pd.DataFrame
        Output of :func:`simulate`.

    Notes
    -----
    The checkpoint stores the parameters and a fingerprint of the input data (number of rows,
    first and last date, first and last prices); any mismatch triggers a recomputation.
    """
    fingerprint = {
        "n_rows": len(prices),
        "first_date": str(prices.index[0].date()),
        "last_date": str(prices.index[-1].date()),
        "first_prices": [float(v) for v in prices.iloc[0]],
        "last_prices": [float(v) for v in prices.iloc[-1]],
    }
    if cache.exists():
        with cache.open("rb") as f:
            stored = pickle.load(f)
        if stored.get("params") == asdict(params) and stored.get("data") == fingerprint:
            logger.info("Loaded simulation table from %s", cache)
            table: pd.DataFrame = stored["table"]
            return table
        logger.warning("Checkpoint %s does not match the parameters or data: recomputing", cache)
    table = simulate(prices, params, ticker_a, ticker_b)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as f:
        pickle.dump({"params": asdict(params), "data": fingerprint, "table": table}, f)
    logger.info("Saved simulation table to %s", cache)
    return table


def window_starts(n_rows: int, length: int, step: int = 252) -> list[int]:
    """First rows of the windows of ``length`` rows starting every ``step`` rows that fit.

    Parameters
    ----------
    n_rows : int
        Number of rows of the path.
    length : int
        Window length in rows (trading days).
    step : int, optional
        Distance between consecutive window starts.

    Returns
    -------
    list[int]
        ``[0, step, 2·step, …]`` while ``start + length <= n_rows``.
    """
    assert 0 < length <= n_rows and step > 0
    return list(range(0, n_rows - length + 1, step))


def evaluate_window(
    window: pd.DataFrame,
    params: BootstrapParams,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> dict[str, float]:
    """Fit, test and trade one window as someone fooled by that window would.

    Parameters
    ----------
    window : pd.DataFrame
        Prices of the window only (real or simulated).
    params : BootstrapParams
        Strategy parameters (entry, lookback, lag, cost) and ``is_warmup``.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    dict[str, float]
        ``beta`` (OLS on the window's log prices), ``eg_pvalue`` (Engle-Granger on the
        window), ``sharpe_net`` (main configuration, evaluated from window row
        ``is_warmup − 1``, starting flat).

    Notes
    -----
    beta is estimated on the same window it is traded on: deliberate in-window look-ahead,
    as pre-registered for the look-elsewhere analysis (18:37 CEST).
    """
    end = (window.index[-1] + pd.Timedelta(days=1)).date()
    fit = fit_hedge_ratio(window, end=end, ticker_a=ticker_a, ticker_b=ticker_b)
    tests = stationarity_tests(window, beta=fit.beta, end=end, ticker_a=ticker_a, ticker_b=ticker_b)
    run = run_strategy(
        window,
        fit.beta,
        entry=params.entry,
        lookback=params.lookback,
        end=end,
        trade_from=window.index[params.is_warmup - 1].date(),
        lag=params.lag,
        cost_bps=params.cost_bps,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
    )
    sharpe = performance_summary(run.daily, run.trades)["sharpe_net"]
    return {"beta": fit.beta, "eg_pvalue": tests.eg_pvalue, "sharpe_net": sharpe}


def look_elsewhere(
    prices: pd.DataFrame,
    params: BootstrapParams,
    window_len: int,
    step: int = 252,
    n_paths: int | None = None,
    expected_is_beta: pd.Series | None = None,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
) -> pd.DataFrame:
    """Evaluate every window of every bootstrap path (same paths as :func:`simulate`).

    Parameters
    ----------
    prices : pd.DataFrame
        Real aligned prices over the full history.
    params : BootstrapParams
        Bootstrap and strategy parameters (same seed and block as Phase 5).
    window_len : int
        Window length in trading days (that of the real window).
    step : int, optional
        Distance between window starts.
    n_paths : int, optional
        Number of paths (default ``params.n_paths``); the first ``n_paths`` of the sequence.
    expected_is_beta : pd.Series, optional
        Simulated-IS beta of each path from the Phase 5 table; if given, every regenerated
        path is checked against it.
    ticker_a, ticker_b : str, optional
        Legs A and B.

    Returns
    -------
    pd.DataFrame
        One row per (path, window): ``path``, ``start_row``, ``beta``, ``eg_pvalue``,
        ``sharpe_net``.

    Raises
    ------
    AssertionError
        If a regenerated path does not match the Phase 5 table.
    """
    prices = prices[[ticker_a, ticker_b]]
    n = params.n_paths if n_paths is None else n_paths
    rng = np.random.default_rng(params.seed)
    starts = window_starts(len(prices), window_len, step)
    rows: list[dict[str, float]] = []
    for k in range(n):
        path = bootstrap_path(prices, bootstrap_indices(len(prices) - 1, params.block, rng))
        if expected_is_beta is not None:
            split_date = path.index[params.split_index].date()
            beta_is = fit_hedge_ratio(
                path, end=split_date, ticker_a=ticker_a, ticker_b=ticker_b
            ).beta
            assert beta_is == float(expected_is_beta.iloc[k]), f"path {k} differs from Phase 5"
        for s in starts:
            res = evaluate_window(path.iloc[s : s + window_len], params, ticker_a, ticker_b)
            rows.append({"path": float(k), "start_row": float(s), **res})
        if (k + 1) % 25 == 0:
            logger.info("Look-elsewhere: %d / %d paths", k + 1, n)
    table = pd.DataFrame(rows).astype({"path": int, "start_row": int})
    return table


def look_elsewhere_summary(
    windows: pd.DataFrame, real_pvalue: float, real_sharpe: float
) -> dict[str, float]:
    """Pre-registered outputs (a)-(d) of the look-elsewhere analysis.

    Parameters
    ----------
    windows : pd.DataFrame
        Output of :func:`look_elsewhere`.
    real_pvalue, real_sharpe : float
        Engle-Granger p-value and net Sharpe of the real window.

    Returns
    -------
    dict[str, float]
        ``a_share_windows_p_lt_005``, ``b_share_paths_any_p_lt_005``,
        ``c_share_paths_any_as_good_as_real``, ``d_best_sharpe_median``,
        ``d_best_sharpe_p5``, ``d_best_sharpe_p95``, ``d_real_percentile_among_best``
        (shares and percentiles in %), plus ``n_paths`` and ``n_windows``.
    """
    by_path = windows.groupby("path")
    as_good = (windows["eg_pvalue"] <= real_pvalue) & (windows["sharpe_net"] >= real_sharpe)
    best = by_path["sharpe_net"].max()
    return {
        "n_paths": float(windows["path"].nunique()),
        "n_windows": float(len(windows)),
        "a_share_windows_p_lt_005": 100 * float((windows["eg_pvalue"] < 0.05).mean()),
        "b_share_paths_any_p_lt_005": 100 * float((by_path["eg_pvalue"].min() < 0.05).mean()),
        "c_share_paths_any_as_good_as_real": 100
        * float(as_good.groupby(windows["path"]).any().mean()),
        "d_best_sharpe_median": float(best.median()),
        "d_best_sharpe_p5": float(best.quantile(0.05)),
        "d_best_sharpe_p95": float(best.quantile(0.95)),
        "d_real_percentile_among_best": 100 * float((best <= real_sharpe).mean()),
    }
