"""Phase 2: in-sample OLS hedge ratio on log prices, the spread, and its stationarity tests."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint

from pairs.config import TICKER_A, TICKER_B
from pairs.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

#: Below this value the B leg hedges too little of the A leg's moves to call the book a pair.
BETA_WARNING_THRESHOLD: float = 0.1


@dataclass(frozen=True)
class HedgeFit:
    """Result of the OLS hedge regression ``log P_A = alpha + beta * log P_B + eps``.

    Attributes
    ----------
    alpha : float
        Intercept: the log of A's price level when B's log price is 0. It only
        shifts the spread level and does not affect the z-score.
    beta : float
        Hedge ratio: a 1% move in B goes with a beta% move in A on average.
    r_squared : float
        Share of the variance of ``log P_A`` explained by ``log P_B``.
    n_obs : int
        Number of daily observations used.
    first_date, last_date : date
        First and last date used in the fit.
    """

    alpha: float
    beta: float
    r_squared: float
    n_obs: int
    first_date: date
    last_date: date


@dataclass(frozen=True)
class StationarityResult:
    """Stationarity diagnostics of a spread.

    Attributes
    ----------
    adf_stat, adf_pvalue : float
        Augmented Dickey-Fuller statistic and p-value on the spread (constant, lags by AIC).
    adf_lags : int
        Number of lagged differences selected by AIC.
    eg_stat, eg_pvalue : float
        Engle-Granger cointegration statistic and p-value (MacKinnon critical values that
        account for beta being estimated).
    ar1_coef : float
        ``b`` in ``Δs_t = a + b·s_{t−1} + u_t``; mean reversion requires ``b < 0``.
    half_life_days : float
        ``−ln 2 / ln(1 + b)`` in trading days; ``inf`` if ``b >= 0``.
    """

    adf_stat: float
    adf_pvalue: float
    adf_lags: int
    eg_stat: float
    eg_pvalue: float
    ar1_coef: float
    half_life_days: float


def _cut(prices: pd.DataFrame, end: date) -> pd.DataFrame:
    """Keep rows with date < ``end`` and check the result is usable."""
    cut = prices[prices.index < pd.Timestamp(end)]
    if cut.empty:
        raise InsufficientDataError(f"No prices before {end}.")
    assert cut.index.max() < pd.Timestamp(end)
    return cut


def log_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Natural log of strictly positive prices.

    Parameters
    ----------
    prices : pd.DataFrame
        Prices without missing values.

    Returns
    -------
    pd.DataFrame
        ``ln(prices)``, same shape.
    """
    assert not prices.isna().to_numpy().any(), "NaN in prices"
    assert (prices > 0).to_numpy().all(), "log of non-positive price"
    return pd.DataFrame(np.log(prices.to_numpy()), index=prices.index, columns=prices.columns)


def _regression_space(prices: pd.DataFrame, use_logs: bool) -> pd.DataFrame:
    """Return log prices (main design) or the price levels themselves (brief's version)."""
    if use_logs:
        return log_prices(prices)
    assert not prices.isna().to_numpy().any(), "NaN in prices"
    return prices.astype(float)


def fit_hedge_ratio(
    prices: pd.DataFrame,
    end: date,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
    use_logs: bool = True,
) -> HedgeFit:
    """Estimate ``log P_A = alpha + beta * log P_B`` by OLS on dates before ``end``.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices with columns ``ticker_a`` and ``ticker_b``.
    end : date
        Exclusive cutoff; rows with date >= ``end`` are dropped before anything else.
    ticker_a, ticker_b : str, optional
        Dependent (A) and explanatory (B) legs.
    use_logs : bool, optional
        True (main design): regress log prices. False: regress price levels
        ``P_A = alpha + beta * P_B``, as in the brief (robustness check only).

    Returns
    -------
    HedgeFit
        alpha, beta, R² and the sample used.

    Raises
    ------
    InsufficientDataError
        If there are no prices before ``end``.

    Notes
    -----
    The main regression is on log prices rather than price levels (as in the brief): over
    the in-sample period prices span about two orders of magnitude, and a unit of log spread
    is the same percentage mispricing in every decade. OLS standard errors are not reported:
    with non-stationary regressors they are not valid.
    """
    x = _regression_space(_cut(prices, end)[[ticker_a, ticker_b]], use_logs)
    model = sm.OLS(x[ticker_a], sm.add_constant(x[ticker_b])).fit()
    fit = HedgeFit(
        alpha=float(model.params["const"]),
        beta=float(model.params[ticker_b]),
        r_squared=float(model.rsquared),
        n_obs=int(model.nobs),
        first_date=x.index.min().date(),
        last_date=x.index.max().date(),
    )
    if fit.beta <= BETA_WARNING_THRESHOLD:
        logger.warning(
            "beta = %.4f <= %.2f: the %s leg barely hedges %s",
            fit.beta,
            BETA_WARNING_THRESHOLD,
            ticker_b,
            ticker_a,
        )
    logger.info(
        "Hedge fit (%s) %s ~ %s on %s..%s: alpha=%.4f beta=%.4f R2=%.4f",
        "log prices" if use_logs else "price levels",
        ticker_a,
        ticker_b,
        fit.first_date,
        fit.last_date,
        fit.alpha,
        fit.beta,
        fit.r_squared,
    )
    return fit


def compute_spread(
    prices: pd.DataFrame,
    beta: float,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
    use_logs: bool = True,
) -> pd.Series:
    """Compute the log spread ``log P_A − beta · log P_B``.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Hedge ratio, estimated beforehand (in-sample only).
    ticker_a, ticker_b : str, optional
        Legs A and B.
    use_logs : bool, optional
        True (main design): log spread. False: price spread ``P_A − beta · P_B`` in USD.

    Returns
    -------
    pd.Series
        Spread named ``"spread"``. Each value depends only on that day's prices.

    Notes
    -----
    alpha is left out on purpose: it is a constant shift and the rolling z-score removes it.
    """
    x = _regression_space(prices[[ticker_a, ticker_b]], use_logs)
    spread = (x[ticker_a] - beta * x[ticker_b]).rename("spread")
    assert not spread.isna().any()
    return spread


def half_life(spread: pd.Series) -> tuple[float, float]:
    """Estimate the AR(1) mean-reversion coefficient and half-life of a spread.

    Parameters
    ----------
    spread : pd.Series
        Spread without missing values.

    Returns
    -------
    tuple[float, float]
        ``(b, half_life_days)`` from ``Δs_t = a + b·s_{t−1} + u_t``; the half-life is
        ``−ln 2 / ln(1 + b)``, or ``inf`` when ``b >= 0`` (no mean reversion).
    """
    lagged = spread.shift(1).iloc[1:]
    delta = spread.diff().iloc[1:]
    b = float(sm.OLS(delta, sm.add_constant(lagged)).fit().params.iloc[1])
    hl = -math.log(2) / math.log(1 + b) if -1 < b < 0 else math.inf
    return b, hl


def stationarity_tests(
    prices: pd.DataFrame,
    beta: float,
    end: date,
    ticker_a: str = TICKER_A,
    ticker_b: str = TICKER_B,
    use_logs: bool = True,
) -> StationarityResult:
    """Run ADF on the spread, Engle-Granger on the two log prices, and the AR(1) half-life.

    Parameters
    ----------
    prices : pd.DataFrame
        Aligned adjusted prices.
    beta : float
        Hedge ratio used to build the spread for the ADF test and the half-life.
    end : date
        Exclusive cutoff applied first.
    ticker_a, ticker_b : str, optional
        Legs A and B.
    use_logs : bool, optional
        True (main design): tests on log prices. False: on price levels (robustness).

    Returns
    -------
    StationarityResult
        Test statistics and p-values; null hypothesis of both tests = unit root (no mean
        reversion), so a small p-value is evidence *for* stationarity.

    Notes
    -----
    The ADF p-value on a spread built with an estimated beta is too optimistic, because OLS
    picks the beta that makes the residual look as stationary as possible. Engle-Granger
    uses critical values corrected for that, so it is the test to rely on.
    """
    cut = _cut(prices, end)
    spread = compute_spread(cut, beta, ticker_a, ticker_b, use_logs=use_logs)
    adf_stat, adf_p, adf_lags, *_ = adfuller(
        spread, regression="c", autolag="AIC", result_object=False
    )
    x = _regression_space(cut[[ticker_a, ticker_b]], use_logs)
    eg_stat, eg_p, _ = coint(x[ticker_a], x[ticker_b], trend="c", autolag="aic")
    b, hl = half_life(spread)
    return StationarityResult(
        adf_stat=float(adf_stat),
        adf_pvalue=float(adf_p),
        adf_lags=int(adf_lags),
        eg_stat=float(eg_stat),
        eg_pvalue=float(eg_p),
        ar1_coef=b,
        half_life_days=hl,
    )
