"""Liquidity sweep detection on the entry timeframe."""
from __future__ import annotations

import pandas as pd

from ..models import LiquidityLevel, Side, Sweep


def detect_sweep(
    df: pd.DataFrame,
    levels: list[LiquidityLevel],
    side: Side,
    lookback: int = 36,
    reclaim_within: int = 6,
) -> Sweep | None:
    """Find the most recent sweep that sets up a trade in ``side`` direction.

    LONG  : a sell-side level (below price) is pierced by a wick and price
            closes back *above* it within ``reclaim_within`` candles.
    SHORT : a buy-side level is pierced and price closes back *below* it.

    Only levels formed *before* the breach candle count.
    """
    n = len(df)
    if n == 0:
        return None
    start = max(0, n - lookback)
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    index = df.index

    candidates = [lv for lv in levels if (lv.is_sellside if side is Side.LONG else lv.is_buyside)]
    best: Sweep | None = None

    for lv in candidates:
        i = start
        while i < n:
            if index[i] < lv.ts:      # level did not exist yet
                i += 1
                continue
            pierced = lows[i] < lv.price if side is Side.LONG else highs[i] > lv.price
            if not pierced:
                i += 1
                continue
            # look for the reclaim close
            reclaim = None
            for j in range(i, min(n, i + reclaim_within + 1)):
                ok = closes[j] > lv.price if side is Side.LONG else closes[j] < lv.price
                if ok:
                    reclaim = j
                    break
            if reclaim is None:
                # price accepted beyond the level -> not a sweep, skip past the run
                i += 1
                continue
            seg_low = lows[i:reclaim + 1].min()
            seg_high = highs[i:reclaim + 1].max()
            extreme = float(seg_low if side is Side.LONG else seg_high)
            sw = Sweep(lv, side, i, reclaim, extreme, index[reclaim])
            if best is None or sw.reclaim_idx > best.reclaim_idx:
                best = sw
            i = reclaim + 1
    return best
