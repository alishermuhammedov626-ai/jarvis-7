"""Fair Value Gaps and Order Blocks inside the displacement leg."""
from __future__ import annotations

import pandas as pd

from ..models import MSS, Side, Zone


def find_fvg(df: pd.DataFrame, mss: MSS, min_size: float = 0.0) -> Zone | None:
    """Best FVG created by the impulse leg [leg_start, mss.idx].

    Bullish FVG at middle candle i: low[i+1] > high[i-1]
    Bearish FVG at middle candle i: high[i+1] < low[i-1]
    Among candidates the one produced by the largest-bodied candle wins
    (the true displacement gap); ties go to the most recent.
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()
    best: Zone | None = None
    best_body = -1.0
    # the middle candle may be any candle of the leg *including* the MSS
    # candle itself (its gap is only complete once the next candle closes)
    for i in range(max(1, mss.leg_start_idx), min(mss.idx + 1, len(df) - 1)):
        if mss.side is Side.LONG:
            lo, hi = highs[i - 1], lows[i + 1]
        else:
            lo, hi = highs[i + 1], lows[i - 1]
        if hi - lo < max(min_size, 0.0) or hi <= lo:
            continue
        body = abs(closes[i] - opens[i])
        if body >= best_body:
            best_body = body
            best = Zone("fvg", mss.side, float(lo), float(hi), i, df.index[i])
    return best


def find_ob(df: pd.DataFrame, mss: MSS) -> Zone | None:
    """Order block: last opposite-coloured candle before the displacement
    candle.  Falls back to the candle at the sweep extreme."""
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    for i in range(mss.displacement_idx - 1, mss.leg_start_idx - 1, -1):
        if i < 0:
            break
        opposite = closes[i] < opens[i] if mss.side is Side.LONG else closes[i] > opens[i]
        if opposite:
            return Zone("ob", mss.side, float(lows[i]), float(highs[i]), i, df.index[i])
    i = mss.leg_start_idx
    return Zone("ob", mss.side, float(lows[i]), float(highs[i]), i, df.index[i])


def zone_still_valid(df: pd.DataFrame, zone: Zone) -> bool:
    """A zone is invalid once price has *closed* through its far edge, or
    already traded fully through it, after it was formed."""
    after = df.iloc[zone.idx + 1:]
    if after.empty:
        return True
    if zone.side is Side.LONG:
        return bool((after["close"] > zone.low).all())
    return bool((after["close"] < zone.high).all())


def select_zone(df: pd.DataFrame, mss: MSS, fvg_min_size: float, allow_ob: bool = True) -> Zone | None:
    """Prefer FVG, fall back to OB (if allowed)."""
    z = find_fvg(df, mss, fvg_min_size)
    if z is not None and zone_still_valid(df, z):
        return z
    if not allow_ob:
        return None
    z = find_ob(df, mss)
    if z is not None and zone_still_valid(df, z):
        return z
    return None
