"""Phase 2: rolling z-score of the spread (past data only) and long/short/exit positions."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_zscore(spread: pd.Series, lookback: int) -> pd.Series:
    """Standardize the spread against its own trailing window.

    Parameters
    ----------
    spread : pd.Series
        Spread series.
    lookback : int
        Window length L in trading days (>= 2).

    Returns
    -------
    pd.Series
        ``z_t = (s_t − mean(s_{t−L+1..t})) / std(s_{t−L+1..t})`` named ``"z"``; NaN for the
        first ``L − 1`` days (warm-up).

    Notes
    -----
    The window ends at day t inclusive: z_t uses only information available at the close of
    day t. The trade based on it is executed from day t+1 (see ``backtest.run_backtest``).
    The sample standard deviation (ddof=1) is used.
    """
    assert lookback >= 2, "lookback must be at least 2"
    roll = spread.rolling(window=lookback, min_periods=lookback)
    z = (spread - roll.mean()) / roll.std(ddof=1)
    return z.rename("z")


def positions_from_zscore(z: pd.Series, entry: float) -> pd.Series:
    """Turn a z-score into desired positions with entry at ±``entry`` and exit at zero.

    Parameters
    ----------
    z : pd.Series
        z-score (NaN during warm-up).
    entry : float
        Entry threshold e > 0.

    Returns
    -------
    pd.Series
        Integer series in {-1, 0, 1} named ``"signal"``: the position *desired* at the
        close of each day. +1 = long spread (long A, short beta·B), -1 = short spread.

    Notes
    -----
    Rules, evaluated day by day with memory of the current state:

    - flat: go long if z < −e, short if z > +e;
    - long: exit when z >= 0; short: exit when z <= 0;
    - if the exit and the opposite entry hold on the same day, flip directly;
    - NaN z (warm-up) means flat.

    No stop-loss. Each output value depends only on z up to that day.
    """
    assert entry > 0, "entry threshold must be positive"
    values = z.to_numpy(dtype=float)
    out = np.zeros(len(values), dtype=int)
    state = 0
    for i, zi in enumerate(values):
        if np.isnan(zi):
            state = 0
        else:
            if (state == 1 and zi >= 0) or (state == -1 and zi <= 0):
                state = 0
            if state == 0:
                if zi < -entry:
                    state = 1
                elif zi > entry:
                    state = -1
        out[i] = state
    signal = pd.Series(out, index=z.index, name="signal")
    assert set(np.unique(out)) <= {-1, 0, 1}
    return signal
