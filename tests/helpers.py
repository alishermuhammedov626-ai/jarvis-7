"""Synthetic candle builders shared by the tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


def frame(rows: list[tuple[float, float, float, float]], start: datetime, tf_minutes: int,
          volume: float = 1000.0) -> pd.DataFrame:
    """rows = [(open, high, low, close), ...]"""
    idx = pd.date_range(start, periods=len(rows), freq=f"{tf_minutes}min", tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = volume
    return df


def trending(start: datetime, tf_minutes: int, n: int = 48, drift: float = 0.5,
             amp: float = 3.0, period: int = 8, base: float = 100.0) -> pd.DataFrame:
    """Zig-zag with drift: positive drift -> HH/HL, negative -> LH/LL."""
    rows = []
    for i in range(n):
        phase = i % period
        tri = phase if phase < period / 2 else period - phase
        c = base + drift * i + amp * tri / (period / 2)
        rows.append((c - 0.1, c + 0.2, c - 0.2, c + 0.1))
    return frame(rows, start, tf_minutes)


def ranging(start: datetime, tf_minutes: int, n: int = 48, base: float = 100.0) -> pd.DataFrame:
    rows = []
    for i in range(n):
        c = base + (1.0 if i % 2 == 0 else -1.0)
        rows.append((c, c + 0.5, c - 0.5, c))
    return frame(rows, start, tf_minutes)


def random_walk_1m(start: datetime, days: int, seed: int = 1, base: float = 0.1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * 24 * 60
    rets = rng.normal(0, 0.0008, n)
    close = base * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[base], close[:-1]])
    spread = np.abs(rng.normal(0, 0.0006, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.uniform(1e5, 1e6, n)}, index=idx)


UTC = timezone.utc
DAY0 = datetime(2025, 1, 1, tzinfo=UTC)
