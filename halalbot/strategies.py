"""Strategiya variantlari. Hammasi LONG-ONLY (faqat sotib olib, keyin sotish).

Har strategiya `Signals` qaytaradi:
  entry[i]      - i-sham yopilganda kirish signali (ijro i+1 ochilishida)
  sl_dist[i]    - stop-loss masofasi (narx birligida), kirish narxidan pastda
  tp_dist[i]    - take-profit masofasi (NaN = TP yo'q, faqat trailing/exit)
  exit_sig[i]   - ochiq pozitsiyani i-sham yopilishida yopish signali
  group[i]      - sessiya identifikatori (bir sessiyada 1 ta savdo); -1 = yo'q
  trail_atr     - chandelier trailing stop koeffitsienti (0 = o'chirilgan)
  time_stop     - maksimal ushlab turish (shamlar soni)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import indicators as ind


@dataclass
class Signals:
    entry: np.ndarray
    sl_dist: np.ndarray
    tp_dist: np.ndarray
    exit_sig: np.ndarray
    group: np.ndarray
    trail_atr: float = 0.0
    time_stop: int = 10 ** 9
    atr: np.ndarray | None = None


def _pack(df, entry, sl, tp, exit_sig=None, group=None, trail=0.0, time_stop=10 ** 9, atr_arr=None):
    n = len(df)
    entry = np.asarray(entry, dtype=bool)
    entry = np.where(np.isnan(sl), False, entry)
    return Signals(
        entry=entry,
        sl_dist=np.asarray(sl, dtype=float),
        tp_dist=np.asarray(tp, dtype=float),
        exit_sig=np.zeros(n, dtype=bool) if exit_sig is None else np.asarray(exit_sig, dtype=bool),
        group=np.full(n, -1, dtype=np.int64) if group is None else np.asarray(group, dtype=np.int64),
        trail_atr=trail,
        time_stop=time_stop,
        atr=atr_arr,
    )


class Strategy:
    name = "base"
    description = ""

    def signals(self, df: pd.DataFrame) -> Signals:
        raise NotImplementedError


class TrendPullback(Strategy):
    """A) Trend + pullback: EMA50>EMA200 trendida narx EMA20 ga qaytib, yana ustiga chiqsa olamiz."""
    name = "A_trend_pullback"
    description = "EMA50>EMA200 trend, EMA20 ga pullback dan qaytish, SL=1.5ATR, TP=2.25ATR"

    def signals(self, df):
        c = df["close"]
        e20, e50, e200 = ind.ema(c, 20), ind.ema(c, 50), ind.ema(c, 200)
        r = ind.rsi(c, 14)
        a = ind.atr(df, 14)
        trend = (e50 > e200) & (c > e200)
        cross_up = (c.shift(1) < e20.shift(1)) & (c > e20)
        entry = trend & cross_up & (r > 40) & (r < 65)
        sl = 1.5 * a
        tp = 2.25 * a
        return _pack(df, entry.fillna(False), sl, tp, time_stop=32, atr_arr=a.values)


class DonchianBreakout(Strategy):
    """B) Donchian breakout: 40-shamlik (10 soat) yuqori nuqtani yorib o'tish, trailing stop."""
    name = "B_donchian_breakout"
    description = "40-sham Donchian yuqorisini yorish + EMA200 o'sayotgan, SL=2ATR, chandelier trailing 2.5ATR"

    def signals(self, df):
        c = df["close"]
        dh = ind.donchian_high(df["high"], 40)
        e200 = ind.ema(c, 200)
        a = ind.atr(df, 14)
        entry = (c > dh) & (e200 > e200.shift(8)) & (a / c > 0.0015)
        sl = 2.0 * a
        tp = np.full(len(df), np.nan)
        return _pack(df, entry.fillna(False), sl, tp, trail=2.5, time_stop=96, atr_arr=a.values)


class BollingerMeanReversion(Strategy):
    """C) O'rtachaga qaytish: pastki Bollinger + RSI<30, chiqish o'rta chiziqda."""
    name = "C_bollinger_meanrev"
    description = "Close < BB pastki(20,2) va RSI14<30 -> kirish; chiqish BB o'rtasida yoki SL=2ATR"

    def signals(self, df):
        c = df["close"]
        lo, mid, _hi = ind.bollinger(c, 20, 2.0)
        r = ind.rsi(c, 14)
        a = ind.atr(df, 14)
        entry = (c < lo) & (r < 30)
        exit_sig = c >= mid
        sl = 2.0 * a
        tp = np.full(len(df), np.nan)
        return _pack(df, entry.fillna(False), sl, tp, exit_sig=exit_sig.fillna(False), time_stop=32, atr_arr=a.values)


class SessionORB(Strategy):
    """D) Sessiya ochilish diapazoni (ORB): 4 sessiya/kun, har birida 1 savdo -> tabiiy 3-4 savdo/kun."""
    name = "D_session_orb"
    description = "Sessiya (00,07,13,19 UTC) birinchi 1 soat diapazoni; 3 soat ichida yuqorisini yorsa kirish, SL=diapazon pasti, TP=1.5x diapazon"
    SESSION_STARTS = (0, 7, 13, 19)   # UTC soatlar
    RANGE_CANDLES = 4                  # 1 soat
    WINDOW_CANDLES = 12                # keyingi 3 soat

    def signals(self, df):
        n = len(df)
        idx = df.index
        hour = idx.hour.values
        minute = idx.minute.values
        day_num = ind.day_index(idx)
        sess = np.full(n, -1, dtype=np.int64)
        for k, h in enumerate(self.SESSION_STARTS):
            mask = (hour >= h) & (hour < h + 4)
            sess[mask] = day_num[mask] * 10 + k
        pos = np.full(n, -1, dtype=np.int64)     # sessiya ichidagi sham raqami
        cur, cnt = -1, 0
        for i in range(n):
            if sess[i] != cur:
                cur, cnt = sess[i], 0
            pos[i] = cnt
            cnt += 1
        hi = df["high"].values
        lo = df["low"].values
        c = df["close"].values
        range_hi = np.full(n, np.nan)
        range_lo = np.full(n, np.nan)
        rh = rl = np.nan
        for i in range(n):
            if pos[i] == 0:
                rh, rl = hi[i], lo[i]
            elif pos[i] < self.RANGE_CANDLES:
                rh, rl = max(rh, hi[i]), min(rl, lo[i])
            if pos[i] >= self.RANGE_CANDLES and pos[i] < self.RANGE_CANDLES + self.WINDOW_CANDLES:
                range_hi[i], range_lo[i] = rh, rl
        a = ind.atr(df, 14).values
        rng = range_hi - range_lo
        entry = (c > range_hi) & (sess >= 0) & (rng / c > 0.002) & (rng / c < 0.03)
        sl = c - range_lo                      # stop = diapazon pasti
        sl = np.where(sl > 0.25 * a, sl, np.nan)
        tp = 1.5 * rng
        return _pack(df, np.nan_to_num(entry, nan=False), sl, tp, group=sess, time_stop=16, atr_arr=a)


class RsiScalp(Strategy):
    """E) Tez RSI: RSI7 30 dan yuqoriga qaytadi, EMA100 ustida, kichik TP/SL."""
    name = "E_rsi_scalp"
    description = "RSI7 30 dan yuqoriga kesib chiqadi va close>EMA100, SL=1ATR, TP=1.5ATR"

    def signals(self, df):
        c = df["close"]
        r = ind.rsi(c, 7)
        e100 = ind.ema(c, 100)
        a = ind.atr(df, 14)
        entry = (r.shift(1) < 30) & (r >= 30) & (c > e100)
        return _pack(df, entry.fillna(False), 1.0 * a, 1.5 * a, time_stop=24, atr_arr=a.values)


class BuyAndHold(Strategy):
    """Benchmark: boshida olib, oxirigacha ushlash (1 savdo)."""
    name = "Z_buy_hold"
    description = "Benchmark: bitta xarid, oxirigacha ushlash"

    def signals(self, df):
        n = len(df)
        entry = np.zeros(n, dtype=bool)
        entry[0] = True
        sl = np.full(n, np.inf)
        tp = np.full(n, np.nan)
        return _pack(df, entry, sl, tp)


ALL_STRATEGIES = [TrendPullback, DonchianBreakout, BollingerMeanReversion, SessionORB, RsiScalp, BuyAndHold]


def by_name(name: str) -> Strategy:
    for s in ALL_STRATEGIES:
        if s.name == name or s.name.split("_", 1)[0] == name.upper():
            return s()
    raise KeyError(name)
