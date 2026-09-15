"""Displacement + Market Structure Shift (MSS) after a sweep."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import swing_points
from ..models import MSS, Side, Sweep


def _structural_level(df: pd.DataFrame, before_idx: int, side: Side, left: int, right: int) -> float | None:
    """Level whose break confirms MSS.

    LONG : the last confirmed swing high formed before the sweep extreme.
    SHORT: the last confirmed swing low formed before the sweep extreme.
    """
    sub = df.iloc[: before_idx + 1]
    highs, lows = swing_points(sub, left, right)
    pts = highs if side is Side.LONG else lows
    pts = [(i, p) for i, p in pts if i < before_idx]
    if not pts:
        return None
    return float(pts[-1][1])


def detect_displacement_mss(
    df: pd.DataFrame,
    sweep: Sweep,
    atr: pd.Series,
    side: Side,
    displacement_atr_mult: float = 1.0,
    max_candles_after_sweep: int = 24,
    left: int = 2,
    right: int = 2,
) -> MSS | None:
    """Confirm that, after the sweep, an impulsive candle (body >= k*ATR) in
    the trade direction closed through the structural level."""
    n = len(df)
    lows = df["low"].to_numpy()
    highs = df["high"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()
    atr_arr = atr.to_numpy()

    # index of the sweep extreme (start of the impulse leg)
    seg = slice(sweep.breach_idx, sweep.reclaim_idx + 1)
    if side is Side.LONG:
        leg_start = sweep.breach_idx + int(np.argmin(lows[seg]))
    else:
        leg_start = sweep.breach_idx + int(np.argmax(highs[seg]))

    level = _structural_level(df, leg_start, side, left, right)
    if level is None:
        return None
    # the structural level must lie on the correct side of the sweep extreme
    if side is Side.LONG and level <= sweep.extreme:
        return None
    if side is Side.SHORT and level >= sweep.extreme:
        return None

    end = min(n, leg_start + max_candles_after_sweep + 1)
    disp_idx: int | None = None
    for k in range(leg_start, end):
        body = closes[k] - opens[k]
        directional = body > 0 if side is Side.LONG else body < 0
        if directional and abs(body) >= displacement_atr_mult * atr_arr[k]:
            if disp_idx is None:
                disp_idx = k
        broke = closes[k] > level if side is Side.LONG else closes[k] < level
        if broke and disp_idx is not None:
            return MSS(side, k, level, leg_start, disp_idx, df.index[k])
    return None
