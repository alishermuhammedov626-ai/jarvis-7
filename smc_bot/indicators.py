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


def _fractal(values: np.ndarray, left: int, right: int, high: bool) -> np.ndarray:
    n = len(values)
    out = np.zeros(n, dtype=bool)
    width = left + right + 1
    if n < width:
        return out
    w = np.lib.stride_tricks.sliding_window_view(values, width)
    center = w[:, left]
    if high:
        mask = (center > w[:, :left].max(axis=1)) & (center > w[:, left + 1:].max(axis=1))
    else:
        mask = (center < w[:, :left].min(axis=1)) & (center < w[:, left + 1:].min(axis=1))
    out[left:n - right] = mask
    return out


def swing_highs(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    """Boolean series: candle high is strictly higher than ``left`` candles
    before and ``right`` candles after it (confirmed fractal)."""
    return pd.Series(_fractal(df["high"].to_numpy(), left, right, True), index=df.index)


def swing_lows(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    return pd.Series(_fractal(df["low"].to_numpy(), left, right, False), index=df.index)


def swing_points(df: pd.DataFrame, left: int = 2, right: int = 2):
    """Return (list of (idx, high), list of (idx, low)) for confirmed swings."""
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    sh = _fractal(h, left, right, True)
    sl = _fractal(l, left, right, False)
    highs = [(int(i), float(h[i])) for i in np.flatnonzero(sh)]
    lows = [(int(i), float(l[i])) for i in np.flatnonzero(sl)]
    return highs, lows


def candle_body(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()
