"""Market data sources.

``DataSource`` is the minimal interface the bot needs.  Two implementations:

* :class:`CcxtDataSource`       - live data via ccxt (public endpoints only)
* :class:`HistoricalDataSource` - in-memory candles for backtests / tests
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Protocol

import numpy as np
import pandas as pd

from ..models import MarketQuality

TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

_TTL = {"1m": 20, "5m": 30, "15m": 60, "1h": 180, "4h": 300}


def ohlcv_to_df(rows: list[list[float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts").astype(float)


def drop_unclosed(df: pd.DataFrame, timeframe: str, now: datetime) -> pd.DataFrame:
    """Remove the last candle if it has not closed yet."""
    if df.empty:
        return df
    secs = TF_SECONDS[timeframe]
    close_time = df.index[-1] + pd.Timedelta(seconds=secs)
    now_ts = pd.Timestamp(now)
    now_ts = now_ts.tz_convert("UTC") if now_ts.tzinfo else now_ts.tz_localize("UTC")
    if close_time > now_ts:
        return df.iloc[:-1]
    return df


def resample(df_small: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h"}[timeframe]
    out = df_small.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open"])


class DataSource(Protocol):
    def ohlcv(self, symbol: str, timeframe: str, limit: int, now: datetime) -> pd.DataFrame: ...
    def quality(self, symbol: str, now: datetime) -> MarketQuality: ...
    def last_price(self, symbol: str, now: datetime) -> float: ...


class CcxtDataSource:
    """Live candles + ticker + order-book depth through ccxt with light caching."""

    def __init__(self, client, depth_band_pct: float = 0.1):
        self.client = client
        self.depth_band_pct = depth_band_pct
        self._cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}

    def ohlcv(self, symbol: str, timeframe: str, limit: int, now: datetime) -> pd.DataFrame:
        key = (symbol, timeframe)
        ts = time.time()
        cached = self._cache.get(key)
        if cached and ts - cached[0] < _TTL.get(timeframe, 60) and len(cached[1]) >= limit - 1:
            df = cached[1]
        else:
            rows = self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = ohlcv_to_df(rows)
            self._cache[key] = (ts, df)
        return drop_unclosed(df, timeframe, now)

    def quality(self, symbol: str, now: datetime) -> MarketQuality:
        t = self.client.fetch_ticker(symbol)
        ob = self.client.fetch_order_book(symbol, limit=100)
        bid = float(t.get("bid") or (ob["bids"][0][0] if ob["bids"] else 0.0))
        ask = float(t.get("ask") or (ob["asks"][0][0] if ob["asks"] else 0.0))
        mid = (bid + ask) / 2 if bid and ask else 0.0
        band = mid * self.depth_band_pct / 100.0
        depth = 0.0
        for p, q in ob["bids"]:
            if p < mid - band:
                break
            depth += p * q
        for p, q in ob["asks"]:
            if p > mid + band:
                break
            depth += p * q
        qv = float(t.get("quoteVolume") or 0.0)
        return MarketQuality(symbol, bid, ask, qv, depth)

    def last_price(self, symbol: str, now: datetime) -> float:
        t = self.client.fetch_ticker(symbol)
        return float(t["last"])


class HistoricalDataSource:
    """Serves candles from an in-memory 1m (or 5m) history, sliced at ``now``.

    Used by the backtester and unit tests.  ``quality`` returns a synthetic
    MarketQuality that passes the default filters unless overridden.
    """

    def __init__(self, base: dict[str, pd.DataFrame], base_tf: str = "1m",
                 quality: dict[str, MarketQuality] | None = None,
                 spread_bps: float = 2.0):
        self.base_tf = base_tf
        self.base = {s: df.sort_index() for s, df in base.items()}
        self._resampled: dict[tuple[str, str], pd.DataFrame] = {}
        self._close_ns: dict[tuple[str, str], np.ndarray] = {}
        self._quality = quality or {}
        self.spread_bps = spread_bps

    def _frame(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = (symbol, timeframe)
        if key not in self._resampled:
            src = self.base[symbol]
            df = src if timeframe == self.base_tf else resample(src, timeframe)
            self._resampled[key] = df
            # candle close times (ns) for O(log n) slicing
            self._close_ns[key] = (df.index.as_unit("ns").asi8 + TF_SECONDS[timeframe] * 1_000_000_000)
        return self._resampled[key]

    @staticmethod
    def _ns(now: datetime) -> int:
        ts = pd.Timestamp(now)
        ts = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
        return int(ts.as_unit("ns").value)

    def ohlcv(self, symbol: str, timeframe: str, limit: int, now: datetime) -> pd.DataFrame:
        df = self._frame(symbol, timeframe)
        # only candles whose close time <= now
        pos = int(np.searchsorted(self._close_ns[(symbol, timeframe)], self._ns(now), side="right"))
        return df.iloc[max(0, pos - limit):pos]

    def candles_between(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Base-TF candles with open time in [start, end)."""
        df = self._frame(symbol, self.base_tf)
        idx = df.index.as_unit("ns").asi8
        a = int(np.searchsorted(idx, self._ns(start), side="left"))
        b = int(np.searchsorted(idx, self._ns(end), side="left"))
        return df.iloc[a:b]

    def quality(self, symbol: str, now: datetime) -> MarketQuality:
        if symbol in self._quality:
            return self._quality[symbol]
        px = self.last_price(symbol, now)
        half = px * self.spread_bps / 2 / 10_000
        return MarketQuality(symbol, px - half, px + half, 1e9, 1e7)

    def last_price(self, symbol: str, now: datetime) -> float:
        df = self.ohlcv(symbol, self.base_tf, 1, now)
        if df.empty:
            raise ValueError(f"no data for {symbol} at {now}")
        return float(df["close"].iloc[-1])

    def last_candle(self, symbol: str, now: datetime) -> pd.Series | None:
        df = self.ohlcv(symbol, self.base_tf, 1, now)
        return None if df.empty else df.iloc[-1]
