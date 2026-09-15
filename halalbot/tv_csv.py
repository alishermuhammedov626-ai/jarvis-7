"""TradingView 'Export chart data' CSV faylini yuklash.

TradingView eksporti: ustunlar `time, open, high, low, close, Volume...`; `time` unix sekund yoki ISO sana.
Binance klines CSV (data.binance.vision) ham qo'llab-quvvatlanadi (sarlavhasiz 12 ustun, ms).
"""
from __future__ import annotations

import pandas as pd


def load_ohlc(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None, nrows=1)
    first = str(raw.iloc[0, 0]).strip().lower()
    if first in ("time", "date", "datetime", "timestamp", "open_time"):
        df = pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        tcol = next(c for c in df.columns if c in ("time", "date", "datetime", "timestamp", "open_time"))
        t = df[tcol]
        if pd.api.types.is_numeric_dtype(t):
            unit = "ms" if t.iloc[0] > 1e11 else "s"
            idx = pd.to_datetime(t, unit=unit, utc=True)
        else:
            idx = pd.to_datetime(t, utc=True)
    else:  # Binance klines: sarlavhasiz, birinchi ustun open_time ms
        df = pd.read_csv(path, header=None)
        df = df.iloc[:, :5]; df.columns = ["time", "open", "high", "low", "close"]
        idx = pd.to_datetime(df["time"], unit="ms", utc=True)
    out = df[["open", "high", "low", "close"]].astype(float)
    out.index = pd.DatetimeIndex(idx, name="time")
    out = out[~out.index.duplicated()].sort_index()
    return out


def to_15m(df: pd.DataFrame) -> pd.DataFrame:
    """Agar ma'lumot boshqa TF bo'lsa (masalan 1m, 5m), 15m ga yig'adi; 15m bo'lsa o'zgarmaydi."""
    step = (df.index[1:] - df.index[:-1]).min()
    if step >= pd.Timedelta("15min"):
        return df
    return df.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def split_windows(df: pd.DataFrame, window_days: int = 30) -> list[pd.DataFrame]:
    """Uzun tarixni window_days uzunlikdagi bo'laklarga bo'ladi (har bo'lak = bitta 'grafik')."""
    out = []
    start = df.index[0]
    while start < df.index[-1]:
        end = start + pd.Timedelta(days=window_days)
        w = df[(df.index >= start) & (df.index < end)]
        if len(w) >= window_days * 96 * 0.8:
            out.append(w)
        start = end
    return out
