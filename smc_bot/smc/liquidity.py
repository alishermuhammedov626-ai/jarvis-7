"""M15 liquidity map: PDH/PDL, session highs/lows, equal highs/lows."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from ..config import AnalysisConfig, SessionWindow
from ..indicators import atr, swing_points
from ..models import LiqKind, LiquidityLevel


def _utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def previous_day_levels(df: pd.DataFrame, now) -> list[LiquidityLevel]:
    now = _utc(now)
    day_start = now.normalize()
    prev_start = day_start - timedelta(days=1)
    window = df[(df.index >= prev_start) & (df.index < day_start)]
    if window.empty:
        return []
    return [
        LiquidityLevel(float(window["high"].max()), LiqKind.PDH, prev_start, "PDH"),
        LiquidityLevel(float(window["low"].min()), LiqKind.PDL, prev_start, "PDL"),
    ]


def _session_bounds(session: SessionWindow, now: pd.Timestamp):
    """Most recent session window that has already started (may be ongoing)."""
    day = now.normalize()
    start = day + timedelta(hours=session.start_hour)
    end = day + timedelta(hours=session.end_hour)
    if start > now:  # today's session not started yet -> use yesterday's
        start -= timedelta(days=1)
        end -= timedelta(days=1)
    return start, min(end, now)


def session_levels(df: pd.DataFrame, now, sessions: list[SessionWindow]) -> list[LiquidityLevel]:
    now = _utc(now)
    out: list[LiquidityLevel] = []
    for s in sessions:
        start, end = _session_bounds(s, now)
        window = df[(df.index >= start) & (df.index < end)]
        if window.empty:
            continue
        out.append(LiquidityLevel(float(window["high"].max()), LiqKind.SESSION_HIGH, start, f"{s.name}_high"))
        out.append(LiquidityLevel(float(window["low"].min()), LiqKind.SESSION_LOW, start, f"{s.name}_low"))
    return out


def equal_levels(
    df: pd.DataFrame,
    tolerance: float,
    left: int = 2,
    right: int = 2,
    lookback: int = 200,
) -> list[LiquidityLevel]:
    """Equal highs / equal lows: two consecutive confirmed swings whose prices
    differ by at most ``tolerance``.  The level is the extreme of the pair and
    is only reported while it has not been traded through yet."""
    sub = df.iloc[-lookback:] if len(df) > lookback else df
    highs, lows = swing_points(sub, left, right)
    out: list[LiquidityLevel] = []
    high_arr = sub["high"].to_numpy()
    low_arr = sub["low"].to_numpy()

    for (i1, p1), (i2, p2) in zip(highs, highs[1:]):
        if abs(p1 - p2) <= tolerance:
            level = max(p1, p2)
            # still intact: no candle after the pair pierced the level
            if len(high_arr) > i2 + 1 and high_arr[i2 + 1:].max() > level + tolerance:
                continue
            out.append(LiquidityLevel(float(level), LiqKind.EQH, sub.index[i2], "EQH"))

    for (i1, p1), (i2, p2) in zip(lows, lows[1:]):
        if abs(p1 - p2) <= tolerance:
            level = min(p1, p2)
            if len(low_arr) > i2 + 1 and low_arr[i2 + 1:].min() < level - tolerance:
                continue
            out.append(LiquidityLevel(float(level), LiqKind.EQL, sub.index[i2], "EQL"))
    return out


def build_liquidity_map(df_m15: pd.DataFrame, now, cfg: AnalysisConfig) -> list[LiquidityLevel]:
    """All liquidity levels the bot cares about, de-duplicated by price."""
    levels: list[LiquidityLevel] = []
    levels += previous_day_levels(df_m15, now)
    levels += session_levels(df_m15, now, cfg.sessions)
    a = atr(df_m15, cfg.atr_period)
    tol = float(a.iloc[-1]) * cfg.equal_level_tolerance_atr if len(a) else 0.0
    levels += equal_levels(df_m15, tol, cfg.swing_left, cfg.swing_right, cfg.equal_level_lookback)

    # de-dup: keep the "most major" level for near-identical prices
    dedup: dict[float, LiquidityLevel] = {}
    for lv in sorted(levels, key=lambda x: (not x.is_major, x.kind.value)):
        key = round(lv.price, 12)
        dedup.setdefault(key, lv)
    return sorted(dedup.values(), key=lambda x: x.price)


def levels_above(levels: list[LiquidityLevel], price: float) -> list[LiquidityLevel]:
    """Buy-side liquidity above ``price`` sorted nearest first."""
    return sorted((lv for lv in levels if lv.is_buyside and lv.price > price), key=lambda x: x.price)


def levels_below(levels: list[LiquidityLevel], price: float) -> list[LiquidityLevel]:
    """Sell-side liquidity below ``price`` sorted nearest first."""
    return sorted((lv for lv in levels if lv.is_sellside and lv.price < price), key=lambda x: -x.price)
