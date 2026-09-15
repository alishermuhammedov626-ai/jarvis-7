"""Reaction-based entry confirmation on the 1m chart.

After a setup is *armed* we wait for price to tag the zone and then close
back out of it in the trade direction with a candle that also takes the
previous candle's high (long) / low (short): a micro market-structure shift
off the zone.  If price closes through the far side of the zone the setup is
invalid.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from ..models import Side, Signal


def check_confirmation(m1: pd.DataFrame, sig: Signal, armed_at: datetime) -> tuple[str, float]:
    """Return ("wait" | "confirmed" | "invalid", price).

    Only candles that *opened at or after* ``armed_at`` are considered.
    ``price`` is the confirming candle's close (0.0 otherwise).
    """
    zone = sig.zone
    if m1 is None or m1.empty:
        return "wait", 0.0
    armed_ts = pd.Timestamp(armed_at)
    armed_ts = armed_ts.tz_convert("UTC") if armed_ts.tzinfo else armed_ts.tz_localize("UTC")
    df = m1[m1.index >= armed_ts]
    if df.empty:
        return "wait", 0.0
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy(); c = df["close"].to_numpy()
    touched = False
    for k in range(len(df)):
        if sig.side is Side.LONG:
            if c[k] < zone.low:
                return "invalid", 0.0
            if l[k] <= zone.high:
                touched = True
            if touched and c[k] > o[k] and c[k] > zone.high and (k == 0 or c[k] > h[k - 1]):
                return "confirmed", float(c[k])
        else:
            if c[k] > zone.high:
                return "invalid", 0.0
            if h[k] >= zone.low:
                touched = True
            if touched and c[k] < o[k] and c[k] < zone.low and (k == 0 or c[k] < l[k - 1]):
                return "confirmed", float(c[k])
    return "wait", 0.0
