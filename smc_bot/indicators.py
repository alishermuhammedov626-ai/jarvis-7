"""Low-level indicators: ATR and fractal swing points."""
from __future__ import annotations

import numpy as np
import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Validate that ``df`` has a UTC DatetimeIndex and OHLCV columns."""
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex")
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    return df


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.fillna(df["high"] - df["low"])


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's ATR."""
    tr = true_range(df)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()


def swing_highs(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    """Boolean series: candle high is strictly higher than ``left`` candles
    before and ``right`` candles after it (confirmed fractal)."""
    h = df["high"].to_numpy()
    n = len(h)
    out = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        window_left = h[i - left:i]
        window_right = h[i + 1:i + 1 + right]
        if h[i] > window_left.max() and h[i] > window_right.max():
            out[i] = True
    return pd.Series(out, index=df.index)


def swing_lows(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    l = df["low"].to_numpy()
    n = len(l)
    out = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        window_left = l[i - left:i]
        window_right = l[i + 1:i + 1 + right]
        if l[i] < window_left.min() and l[i] < window_right.min():
            out[i] = True
    return pd.Series(out, index=df.index)


def swing_points(df: pd.DataFrame, left: int = 2, right: int = 2):
    """Return (list of (idx, high), list of (idx, low)) for confirmed swings."""
    sh = swing_highs(df, left, right).to_numpy()
    sl = swing_lows(df, left, right).to_numpy()
    highs = [(i, float(df["high"].iloc[i])) for i in np.flatnonzero(sh)]
    lows = [(i, float(df["low"].iloc[i])) for i in np.flatnonzero(sl)]
    return highs, lows


def candle_body(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()
