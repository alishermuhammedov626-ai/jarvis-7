"""Internetdagi mashhur strategiyalar kutubxonasi (futures: long + short).

Har strategiya `fsignals(df) -> FSignals`. Standart: SL = 2 ATR, TP = 3 ATR, time_stop 96 sham,
agar strategiyaning o'z chiqish qoidasi bo'lmasa. Hajm (volume) sintetik grafikda yo'q, shuning uchun
OBV/MFI/VWAP/volume-breakout kabi hajmga bog'liq strategiyalar kiritilmagan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .futures_backtest import FSignals

# ----------------------------------------------------------------- qo'shimcha indikatorlar

def stoch(df, n=14, d=3):
    lo = df["low"].rolling(n).min(); hi = df["high"].rolling(n).max()
    k = 100 * (df["close"] - lo) / (hi - lo).replace(0, np.nan)
    return k, k.rolling(d).mean()

def cci(df, n=20):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = tp.rolling(n).mean()
    md = (tp - ma).abs().rolling(n).mean()
    return (tp - ma) / (0.015 * md.replace(0, np.nan))

def williams_r(df, n=14):
    hi = df["high"].rolling(n).max(); lo = df["low"].rolling(n).min()
    return -100 * (hi - df["close"]) / (hi - lo).replace(0, np.nan)

def wma(s, n):
    w = np.arange(1, n + 1, dtype=float)
    return s.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)

def hull(s, n=20):
    return wma(2 * wma(s, n // 2) - wma(s, n), int(np.sqrt(n)))

def tema(s, n):
    e1 = ind.ema(s, n); e2 = ind.ema(e1, n); e3 = ind.ema(e2, n)
    return 3 * e1 - 3 * e2 + e3

def macd(s, f=12, sl=26, sg=9):
    m = ind.ema(s, f) - ind.ema(s, sl); si = ind.ema(m, sg)
    return m, si, m - si

def adx_dmi(df, n=14):
    up = df["high"].diff(); dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0); minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = ind.atr(df, 1)
    atr_n = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi

def supertrend(df, n=10, mult=3.0):
    a = ind.atr(df, n); hl2 = (df["high"] + df["low"]) / 2
    ub = (hl2 + mult * a).values; lb = (hl2 - mult * a).values; c = df["close"].values
    n_ = len(df); st = np.full(n_, np.nan); dir_ = np.zeros(n_)
    fub, flb = ub.copy(), lb.copy()
    for i in range(1, n_):
        if np.isnan(a.values[i]): continue
        fub[i] = ub[i] if (np.isnan(fub[i - 1]) or ub[i] < fub[i - 1] or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (np.isnan(flb[i - 1]) or lb[i] > flb[i - 1] or c[i - 1] < flb[i - 1]) else flb[i - 1]
        if dir_[i - 1] >= 0:
            dir_[i] = -1 if c[i] < flb[i] else 1
        else:
            dir_[i] = 1 if c[i] > fub[i] else -1
        st[i] = flb[i] if dir_[i] > 0 else fub[i]
    return pd.Series(st, df.index), pd.Series(dir_, df.index)

def psar(df, af0=0.02, af_max=0.2):
    h, l = df["high"].values, df["low"].values; n = len(df)
    sar = np.full(n, np.nan); trend = np.ones(n)
    if n < 3: return pd.Series(sar, df.index), pd.Series(trend, df.index)
    up = True; af = af0; ep = h[0]; sar[0] = l[0]
    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if up:
            sar[i] = min(sar[i], l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar[i]:
                up = False; sar[i] = ep; ep = l[i]; af = af0
            elif h[i] > ep:
                ep = h[i]; af = min(af + af0, af_max)
        else:
            sar[i] = max(sar[i], h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar[i]:
                up = True; sar[i] = ep; ep = h[i]; af = af0
            elif l[i] < ep:
                ep = l[i]; af = min(af + af0, af_max)
        trend[i] = 1 if up else -1
    return pd.Series(sar, df.index), pd.Series(trend, df.index)

def ichimoku(df):
    conv = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    base = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    span_a = ((conv + base) / 2).shift(26)
    span_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    return conv, base, span_a, span_b

def heikin_ashi(df):
    ha_c = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_o = ha_c.copy()
    o = df["open"].values; c = ha_c.values; out = np.empty(len(df)); out[0] = o[0]
    for i in range(1, len(df)): out[i] = (out[i - 1] + c[i - 1]) / 2
    return pd.Series(out, df.index), ha_c

def aroon(df, n=25):
    up = df["high"].rolling(n + 1).apply(lambda x: 100 * x.argmax() / n, raw=True)
    dn = df["low"].rolling(n + 1).apply(lambda x: 100 * x.argmin() / n, raw=True)
    return up, dn

def vortex(df, n=14):
    vp = (df["high"] - df["low"].shift(1)).abs().rolling(n).sum()
    vm = (df["low"] - df["high"].shift(1)).abs().rolling(n).sum()
    tr = ind.atr(df, 1).rolling(n).sum()
    return vp / tr, vm / tr

def trix(s, n=15):
    t = ind.ema(ind.ema(ind.ema(s, n), n), n)
    return t.pct_change() * 100

# ----------------------------------------------------------------- yordamchi

def _f(df, long, short, sl=None, tp=None, exit_long=None, exit_short=None, group=None,
       trail=0.0, time_stop=96, sl_mult=2.0, tp_mult=3.0):
    n = len(df); a = ind.atr(df, 14)
    sl = sl_mult * a if sl is None else sl
    tp = (tp_mult * a if tp_mult else pd.Series(np.nan, index=df.index)) if tp is None else tp
    z = np.zeros(n, dtype=bool)
    def b(x): return z if x is None else np.asarray(pd.Series(x, index=df.index).fillna(False).astype(bool))
    return FSignals(long_entry=b(long), short_entry=b(short),
                    sl_dist=np.asarray(sl, dtype=float), tp_dist=np.asarray(tp, dtype=float),
                    exit_long=b(exit_long), exit_short=b(exit_short),
                    group=None if group is None else np.asarray(group, dtype=np.int64),
                    trail_atr=trail, time_stop=time_stop, atr=a.values)

def _cross_up(a, b): return (a.shift(1) <= b.shift(1)) & (a > b)
def _cross_dn(a, b): return (a.shift(1) >= b.shift(1)) & (a < b)

class Z:
    name = "base"; family = ""
    def fsignals(self, df): raise NotImplementedError

ZOO: list[type] = []
def reg(cls): ZOO.append(cls); return cls

# ----------------------------------------------------------------- 1. MA kesishmalari
@reg
class EmaCross9_21(Z):
    name, family = "ema_cross_9_21", "trend"
    def fsignals(self, df):
        c = df["close"]; f, s = ind.ema(c, 9), ind.ema(c, 21)
        return _f(df, _cross_up(f, s), _cross_dn(f, s), exit_long=_cross_dn(f, s), exit_short=_cross_up(f, s), tp_mult=0, time_stop=10**9)

@reg
class EmaCross50_200(Z):
    name, family = "golden_death_cross_50_200", "trend"
    def fsignals(self, df):
        c = df["close"]; f, s = ind.ema(c, 50), ind.ema(c, 200)
        return _f(df, _cross_up(f, s), _cross_dn(f, s), exit_long=_cross_dn(f, s), exit_short=_cross_up(f, s), sl_mult=3, tp_mult=0, time_stop=10**9)

@reg
class TemaCross(Z):
    name, family = "tema_cross_10_30", "trend"
    def fsignals(self, df):
        c = df["close"]; f, s = tema(c, 10), tema(c, 30)
        return _f(df, _cross_up(f, s), _cross_dn(f, s), exit_long=_cross_dn(f, s), exit_short=_cross_up(f, s), tp_mult=0)

@reg
class HullSlope(Z):
    name, family = "hull_ma_slope", "trend"
    def fsignals(self, df):
        h = hull(df["close"], 20); up = h > h.shift(1); dn = h < h.shift(1)
        u1 = up.shift(1).fillna(False).astype(bool); d1 = dn.shift(1).fillna(False).astype(bool)
        return _f(df, up & ~u1, dn & ~d1, exit_long=dn, exit_short=up, tp_mult=0)

@reg
class EmaRibbon(Z):
    name, family = "ema_ribbon_alignment", "trend"
    def fsignals(self, df):
        c = df["close"]; e = [ind.ema(c, n) for n in (8, 13, 21, 34, 55)]
        bull = pd.concat([e[i] > e[i + 1] for i in range(4)], axis=1).all(axis=1)
        bear = pd.concat([e[i] < e[i + 1] for i in range(4)], axis=1).all(axis=1)
        b1 = bull.shift(1).fillna(False).astype(bool); r1 = bear.shift(1).fillna(False).astype(bool)
        return _f(df, bull & ~b1, bear & ~r1, exit_long=~bull, exit_short=~bear, tp_mult=0)

@reg
class Ema200Pullback(Z):
    name, family = "ema200_trend_ema20_pullback", "trend"
    def fsignals(self, df):
        c = df["close"]; e20, e200 = ind.ema(c, 20), ind.ema(c, 200)
        return _f(df, (c > e200) & _cross_up(c, e20), (c < e200) & _cross_dn(c, e20), sl_mult=1.5, tp_mult=2.25, time_stop=32)

# ----------------------------------------------------------------- 2. MACD
@reg
class MacdCross(Z):
    name, family = "macd_signal_cross", "momentum"
    def fsignals(self, df):
        m, s, _ = macd(df["close"])
        return _f(df, _cross_up(m, s), _cross_dn(m, s), exit_long=_cross_dn(m, s), exit_short=_cross_up(m, s), tp_mult=0)

@reg
class MacdZero(Z):
    name, family = "macd_zero_line", "momentum"
    def fsignals(self, df):
        m, _, _ = macd(df["close"]); z = m * 0
        return _f(df, _cross_up(m, z), _cross_dn(m, z), exit_long=_cross_dn(m, z), exit_short=_cross_up(m, z), tp_mult=0)

@reg
class MacdHistReversal(Z):
    name, family = "macd_histogram_reversal", "momentum"
    def fsignals(self, df):
        _, _, h = macd(df["close"])
        lg = (h < 0) & (h > h.shift(1)) & (h.shift(1) <= h.shift(2))
        sh = (h > 0) & (h < h.shift(1)) & (h.shift(1) >= h.shift(2))
        return _f(df, lg, sh, time_stop=48)

# ----------------------------------------------------------------- 3. Ossilyatorlar
@reg
class RsiReversal(Z):
    name, family = "rsi14_30_70_reversal", "meanrev"
    def fsignals(self, df):
        r = ind.rsi(df["close"], 14)
        return _f(df, _cross_up(r, r * 0 + 30), _cross_dn(r, r * 0 + 70), exit_long=r > 50, exit_short=r < 50, tp_mult=0, time_stop=64)

@reg
class Rsi2Connors(Z):
    name, family = "connors_rsi2_sma200", "meanrev"
    def fsignals(self, df):
        c = df["close"]; r = ind.rsi(c, 2); s200 = ind.sma(c, 200); s5 = ind.sma(c, 5)
        return _f(df, (c > s200) & (r < 10), (c < s200) & (r > 90), exit_long=c > s5, exit_short=c < s5, sl_mult=3, tp_mult=0, time_stop=40)

@reg
class RsiMomentum(Z):
    name, family = "rsi_50_momentum", "momentum"
    def fsignals(self, df):
        c = df["close"]; r = ind.rsi(c, 14); e = ind.ema(c, 100); m = r * 0 + 50
        return _f(df, (c > e) & _cross_up(r, m), (c < e) & _cross_dn(r, m), time_stop=48)

@reg
class StochCross(Z):
    name, family = "stochastic_20_80_cross", "meanrev"
    def fsignals(self, df):
        k, d = stoch(df)
        return _f(df, _cross_up(k, d) & (k < 20), _cross_dn(k, d) & (k > 80), exit_long=k > 80, exit_short=k < 20, tp_mult=0, time_stop=48)

@reg
class CciReversal(Z):
    name, family = "cci_100_reversal", "meanrev"
    def fsignals(self, df):
        x = cci(df); m1, p1 = x * 0 - 100, x * 0 + 100
        return _f(df, _cross_up(x, m1), _cross_dn(x, p1), exit_long=x > 0, exit_short=x < 0, tp_mult=0, time_stop=48)

@reg
class WilliamsR(Z):
    name, family = "williams_r_reversal", "meanrev"
    def fsignals(self, df):
        w = williams_r(df)
        return _f(df, _cross_up(w, w * 0 - 80), _cross_dn(w, w * 0 - 20), exit_long=w > -50, exit_short=w < -50, tp_mult=0, time_stop=48)

@reg
class RsiDivergence(Z):
    name, family = "rsi_divergence_simple", "meanrev"
    def fsignals(self, df):
        c = df["close"]; r = ind.rsi(c, 14); n = 20
        lower_low = c < c.rolling(n).min().shift(1)
        higher_rsi = r > r.rolling(n).min().shift(1) + 3
        higher_high = c > c.rolling(n).max().shift(1)
        lower_rsi = r < r.rolling(n).max().shift(1) - 3
        return _f(df, lower_low & higher_rsi & (r < 40), higher_high & lower_rsi & (r > 60), time_stop=48)

# ----------------------------------------------------------------- 4. Volatillik / kanallar
@reg
class BollingerMeanRev(Z):
    name, family = "bollinger_meanrev_20_2", "meanrev"
    def fsignals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2)
        return _f(df, c < lo, c > hi, exit_long=c >= mid, exit_short=c <= mid, tp_mult=0, time_stop=32)

@reg
class BollingerSqueezeBreakout(Z):
    name, family = "bollinger_squeeze_breakout", "breakout"
    def fsignals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2); w = (hi - lo) / mid
        squeeze = w.shift(1) <= w.rolling(96).min().shift(1) * 1.1
        return _f(df, squeeze & (c > hi), squeeze & (c < lo), trail=2.5, tp_mult=0, time_stop=96)

@reg
class KeltnerBreakout(Z):
    name, family = "keltner_breakout", "breakout"
    def fsignals(self, df):
        c = df["close"]; e = ind.ema(c, 20); a = ind.atr(df, 10); hi, lo = e + 2 * a, e - 2 * a
        return _f(df, _cross_up(c, hi), _cross_dn(c, lo), exit_long=c < e, exit_short=c > e, tp_mult=0)

@reg
class Donchian20_10Turtle(Z):
    name, family = "turtle_donchian_20_10", "breakout"
    def fsignals(self, df):
        c = df["close"]; dh, dl = ind.donchian_high(df["high"], 20), ind.donchian_low(df["low"], 20)
        xh, xl = ind.donchian_high(df["high"], 10), ind.donchian_low(df["low"], 10)
        return _f(df, c > dh, c < dl, exit_long=c < xl, exit_short=c > xh, tp_mult=0, time_stop=10**9)

@reg
class Donchian55_20Turtle(Z):
    name, family = "turtle_donchian_55_20", "breakout"
    def fsignals(self, df):
        c = df["close"]; dh, dl = ind.donchian_high(df["high"], 55), ind.donchian_low(df["low"], 55)
        xh, xl = ind.donchian_high(df["high"], 20), ind.donchian_low(df["low"], 20)
        return _f(df, c > dh, c < dl, exit_long=c < xl, exit_short=c > xh, tp_mult=0, time_stop=10**9)

@reg
class SuperTrend(Z):
    name, family = "supertrend_10_3", "trend"
    def fsignals(self, df):
        st, d = supertrend(df)
        return _f(df, (d > 0) & (d.shift(1) < 0), (d < 0) & (d.shift(1) > 0), exit_long=d < 0, exit_short=d > 0, sl_mult=3, tp_mult=0, time_stop=10**9)

@reg
class ParabolicSar(Z):
    name, family = "parabolic_sar_flip", "trend"
    def fsignals(self, df):
        s, t = psar(df)
        return _f(df, (t > 0) & (t.shift(1) < 0), (t < 0) & (t.shift(1) > 0), exit_long=t < 0, exit_short=t > 0, sl_mult=3, tp_mult=0, time_stop=10**9)

@reg
class ChandelierTrend(Z):
    name, family = "chandelier_exit_trend", "trend"
    def fsignals(self, df):
        c = df["close"]; e = ind.ema(c, 50)
        return _f(df, _cross_up(c, e), _cross_dn(c, e), trail=3.0, sl_mult=3, tp_mult=0, time_stop=10**9)

@reg
class LarryWilliamsVolBreakout(Z):
    name, family = "larry_williams_volatility_breakout", "breakout"
    def fsignals(self, df):
        d = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        prev_range = (d["high"] - d["low"]).shift(1)
        day_open = d["open"]
        rng = prev_range.reindex(df.index, method="ffill"); op = day_open.reindex(df.index, method="ffill")
        c = df["close"]; k = 0.5
        day = ind.day_index(df.index)
        return _f(df, c > op + k * rng, c < op - k * rng, group=day, sl=rng * k, tp=rng * k * 1.5, time_stop=96)

# ----------------------------------------------------------------- 5. Trend kuchi
@reg
class AdxDmi(Z):
    name, family = "adx25_dmi_cross", "trend"
    def fsignals(self, df):
        adx, p, m = adx_dmi(df)
        return _f(df, (adx > 25) & _cross_up(p, m), (adx > 25) & _cross_dn(p, m), exit_long=_cross_dn(p, m), exit_short=_cross_up(p, m), tp_mult=0)

@reg
class Ichimoku(Z):
    name, family = "ichimoku_tk_cross_cloud", "trend"
    def fsignals(self, df):
        conv, base, sa, sb = ichimoku(df); c = df["close"]
        above = c > pd.concat([sa, sb], axis=1).max(axis=1); below = c < pd.concat([sa, sb], axis=1).min(axis=1)
        return _f(df, _cross_up(conv, base) & above, _cross_dn(conv, base) & below, exit_long=_cross_dn(conv, base), exit_short=_cross_up(conv, base), sl_mult=3, tp_mult=0)

@reg
class AroonCross(Z):
    name, family = "aroon_cross", "trend"
    def fsignals(self, df):
        up, dn = aroon(df)
        return _f(df, _cross_up(up, dn) & (up > 70), _cross_dn(up, dn) & (dn > 70), exit_long=_cross_dn(up, dn), exit_short=_cross_up(up, dn), tp_mult=0)

@reg
class VortexCross(Z):
    name, family = "vortex_cross", "trend"
    def fsignals(self, df):
        vp, vm = vortex(df)
        return _f(df, _cross_up(vp, vm), _cross_dn(vp, vm), exit_long=_cross_dn(vp, vm), exit_short=_cross_up(vp, vm), tp_mult=0)

@reg
class TrixCross(Z):
    name, family = "trix_zero_cross", "momentum"
    def fsignals(self, df):
        t = trix(df["close"]); z = t * 0
        return _f(df, _cross_up(t, z), _cross_dn(t, z), exit_long=_cross_dn(t, z), exit_short=_cross_up(t, z), tp_mult=0)

@reg
class RocMomentum(Z):
    name, family = "roc_momentum_12", "momentum"
    def fsignals(self, df):
        c = df["close"]; roc = c.pct_change(12) * 100; z = roc * 0
        return _f(df, _cross_up(roc, z + 0.5), _cross_dn(roc, z - 0.5), exit_long=roc < 0, exit_short=roc > 0, tp_mult=0, time_stop=48)

@reg
class ZScoreMeanRev(Z):
    name, family = "zscore_meanrev_2", "meanrev"
    def fsignals(self, df):
        c = df["close"]; m = c.rolling(50).mean(); s = c.rolling(50).std(); z = (c - m) / s
        return _f(df, z < -2, z > 2, exit_long=z > 0, exit_short=z < 0, sl_mult=3, tp_mult=0, time_stop=64)

# ----------------------------------------------------------------- 6. Sham naqshlari
@reg
class HeikinAshiTrend(Z):
    name, family = "heikin_ashi_color_change", "trend"
    def fsignals(self, df):
        ho, hc = heikin_ashi(df); g = hc > ho
        g1 = g.shift(1).fillna(False).astype(bool); g2 = g.shift(2).fillna(False).astype(bool)
        lg = g & g1 & ~g2; sh = ~g & ~g1 & g2
        return _f(df, lg, sh, exit_long=~g & ~g1, exit_short=g & g1, tp_mult=0)

@reg
class InsideBarBreakout(Z):
    name, family = "inside_bar_breakout", "breakout"
    def fsignals(self, df):
        h, l, c = df["high"], df["low"], df["close"]
        inside = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
        return _f(df, inside & (c > h.shift(2)), inside & (c < l.shift(2)), sl_mult=1.5, tp_mult=2.5, time_stop=32)

@reg
class Engulfing(Z):
    name, family = "engulfing_candle_trend", "pattern"
    def fsignals(self, df):
        o, c = df["open"], df["close"]; e = ind.ema(c, 100)
        bull = (c > o) & (c.shift(1) < o.shift(1)) & (c > o.shift(1)) & (o <= c.shift(1))
        bear = (c < o) & (c.shift(1) > o.shift(1)) & (c < o.shift(1)) & (o >= c.shift(1))
        return _f(df, bull & (c > e), bear & (c < e), sl_mult=1.5, tp_mult=2.5, time_stop=32)

@reg
class PinBar(Z):
    name, family = "pin_bar_hammer_shooting_star", "pattern"
    def fsignals(self, df):
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]; rng = (h - l).replace(0, np.nan)
        body = (c - o).abs(); lower = pd.concat([o, c], axis=1).min(axis=1) - l; upper = h - pd.concat([o, c], axis=1).max(axis=1)
        e = ind.ema(c, 100)
        hammer = (lower > 2 * body) & (upper < 0.3 * rng) & (c > e)
        star = (upper > 2 * body) & (lower < 0.3 * rng) & (c < e)
        return _f(df, hammer, star, sl_mult=1.5, tp_mult=2.5, time_stop=32)

@reg
class ThreeBarReversal(Z):
    name, family = "three_bar_reversal", "pattern"
    def fsignals(self, df):
        c, l, h = df["close"], df["low"], df["high"]
        lg = (l.shift(1) < l.shift(2)) & (l.shift(1) < l) & (c > h.shift(1))
        sh = (h.shift(1) > h.shift(2)) & (h.shift(1) > h) & (c < l.shift(1))
        return _f(df, lg, sh, sl_mult=1.5, tp_mult=2.5, time_stop=32)

# ----------------------------------------------------------------- 7. Vaqt / sessiya
@reg
class SessionORB(Z):
    name, family = "session_opening_range_breakout", "breakout"
    STARTS = (0, 7, 13, 19)
    def fsignals(self, df):
        n = len(df); idx = df.index; hour = idx.hour.values; day = ind.day_index(idx)
        sess = np.full(n, -1, dtype=np.int64)
        for k, hh in enumerate(self.STARTS):
            m = (hour >= hh) & (hour < hh + 4); sess[m] = day[m] * 10 + k
        pos = np.zeros(n, dtype=int); cur = -1; cnt = 0
        for i in range(n):
            if sess[i] != cur: cur, cnt = sess[i], 0
            pos[i] = cnt; cnt += 1
        h, l, c = df["high"].values, df["low"].values, df["close"].values
        rh = np.full(n, np.nan); rl = np.full(n, np.nan); a = b = np.nan
        for i in range(n):
            if pos[i] == 0: a, b = h[i], l[i]
            elif pos[i] < 4: a, b = max(a, h[i]), min(b, l[i])
            if 4 <= pos[i] < 16: rh[i], rl[i] = a, b
        rng = rh - rl
        ok = (sess >= 0) & (rng / c > 0.002) & (rng / c < 0.03)
        lg = ok & (c > rh); sh = ok & (c < rl)
        sl = np.where(lg, c - rl, np.where(sh, rh - c, np.nan))
        return _f(df, lg, sh, group=sess, sl=sl, tp=1.5 * rng, time_stop=16)

@reg
class DailyPivotBounce(Z):
    name, family = "daily_pivot_points", "meanrev"
    def fsignals(self, df):
        d = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).shift(1)
        p = (d["high"] + d["low"] + d["close"]) / 3; s1 = 2 * p - d["high"]; r1 = 2 * p - d["low"]
        P, S1, R1 = (x.reindex(df.index, method="ffill") for x in (p, s1, r1))
        c, l, h = df["close"], df["low"], df["high"]
        lg = (l <= S1) & (c > S1); sh = (h >= R1) & (c < R1)
        return _f(df, lg, sh, exit_long=c >= P, exit_short=c <= P, sl_mult=1.5, tp_mult=0, time_stop=48)

@reg
class TimeOfDayMomentum(Z):
    name, family = "us_open_momentum_1330utc", "session"
    def fsignals(self, df):
        idx = df.index; at = (idx.hour == 14) & (idx.minute == 30)     # US ochilishidan 1 soat keyin
        c = df["close"]; ret1h = c / c.shift(4) - 1
        return _f(df, pd.Series(at, idx) & (ret1h > 0.003), pd.Series(at, idx) & (ret1h < -0.003), time_stop=16)

# ----------------------------------------------------------------- 8. Yuqori TF filtr + past TF kirish
@reg
class TripleScreen(Z):
    name, family = "elder_triple_screen_4h_15m", "trend"
    def fsignals(self, df):
        h4 = df["close"].resample("4h").last(); e = ind.ema(h4, 26)
        up = ((h4 > e) & (e > e.shift(1))).shift(1); dn = ((h4 < e) & (e < e.shift(1))).shift(1)   # faqat yopilgan 4h
        up15 = up.reindex(df.index, method="ffill").fillna(False).astype(bool)
        dn15 = dn.reindex(df.index, method="ffill").fillna(False).astype(bool)
        k, d = stoch(df)
        return _f(df, up15 & _cross_up(k, d) & (k < 30), dn15 & _cross_dn(k, d) & (k > 70), trail=3.0, tp_mult=0, time_stop=96)

@reg
class MtfEmaMacd(Z):
    name, family = "mtf_1h_ema_15m_macd", "trend"
    def fsignals(self, df):
        h1 = df["close"].resample("1h").last(); e = ind.ema(h1, 50)
        up = (h1 > e).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        dn = (h1 < e).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        m, s, _ = macd(df["close"])
        return _f(df, up & _cross_up(m, s), dn & _cross_dn(m, s), exit_long=_cross_dn(m, s), exit_short=_cross_up(m, s), tp_mult=0)

# ----------------------------------------------------------------- 9. Nazorat guruhi
@reg
class RandomEntry(Z):
    """Nazorat: tasodifiy kirish. Agar boshqa strategiya bundan yaxshi bo'lmasa, uning 'edge'i yo'q."""
    name, family = "control_random_entry", "control"
    def fsignals(self, df):
        rng = np.random.default_rng(int(df["close"].iloc[0] * 1000) % 2**32)
        u = rng.random(len(df))
        return _f(df, u < 0.02, u > 0.98, time_stop=48)


def zoo_names(): return [z.name for z in ZOO]


# ================================================================= "Yuqori winrate" to'plami (foydalanuvchi ro'yxati)

def _session_twap_bands(df):
    """Hajm yo'q -> VWAP o'rniga kunlik ankerli TWAP (hlc3 o'rtachasi) va uning kumulyativ std'i."""
    tp = ((df["high"] + df["low"] + df["close"]) / 3).values
    day = ind.day_index(df.index)
    n = len(df); mean = np.full(n, np.nan); sd = np.full(n, np.nan)
    s = s2 = 0.0; k = 0; cur = -1
    for i in range(n):
        if day[i] != cur: cur, s, s2, k = day[i], 0.0, 0.0, 0
        s += tp[i]; s2 += tp[i] ** 2; k += 1
        if k >= 8:
            m = s / k; v = max(s2 / k - m * m, 0.0)
            mean[i] = m; sd[i] = np.sqrt(v)
    return pd.Series(mean, df.index), pd.Series(sd, df.index)


@reg
class VwapBandReversion(Z):
    """2) VWAP 2.5σ dan qaytish, TP faqat 1σ chizig'igacha (kichik maqsad)."""
    name, family = "hw_vwap_2.5sigma_tp_1sigma", "highwr"
    def fsignals(self, df):
        m, sd = _session_twap_bands(df); c = df["close"]
        lg = c < m - 2.5 * sd; sh = c > m + 2.5 * sd
        tp = ((m - sd) - c).where(lg, (c - (m + sd)).where(sh, np.nan)).clip(lower=0)
        sl = 1.5 * sd
        return _f(df, lg & (tp > 0), sh & (tp > 0), sl=sl, tp=tp, time_stop=24)


@reg
class MtfConfluence(Z):
    """3) Ko'p taymfreym mos kelishi: 1h trend + 15m daraja + rad etish shami + RSI. (Hajm sintetikda yo'q.)"""
    name, family = "hw_mtf_confluence_1h_15m_rejection_rsi", "highwr"
    def fsignals(self, df):
        c, o, h, l = df["close"], df["open"], df["high"], df["low"]
        h1 = c.resample("1h").last(); e = ind.ema(h1, 50)
        up = ((h1 > e) & (e > e.shift(1))).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        dn = ((h1 < e) & (e < e.shift(1))).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        a = ind.atr(df, 14); r = ind.rsi(c, 14)
        sup = l.shift(1).rolling(48).min(); res = h.shift(1).rolling(48).max()      # 15m kuchli daraja (12 soat)
        near_sup = (l <= sup + 0.5 * a) & (c > sup); near_res = (h >= res - 0.5 * a) & (c < res)
        rng = (h - l).replace(0, np.nan); body = (c - o).abs()
        lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l; upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
        rej_long = (lower_wick > 0.5 * rng) & (c > o); rej_short = (upper_wick > 0.5 * rng) & (c < o)
        lg = up & near_sup & rej_long & (r < 50) & (r > r.shift(1))
        sh = dn & near_res & rej_short & (r > 50) & (r < r.shift(1))
        sl = (c - l + 0.25 * a).where(lg, (h - c + 0.25 * a).where(sh, np.nan))
        return _f(df, lg, sh, sl=sl, tp=2.0 * sl, time_stop=48)


@reg
class LiquidationWickLimit(Z):
    """5) Likvidatsiya soyasini limit buyurtma bilan ushlash: support ostida limit, kichik TP."""
    name, family = "hw_liquidation_wick_limit_order", "highwr"
    def fsignals(self, df):
        c, h, l = df["close"], df["high"], df["low"]; a = ind.atr(df, 14)
        sup = l.shift(1).rolling(96).min(); res = h.shift(1).rolling(96).max()
        # signal: narx support/resistansga yaqinlashdi (1 ATR ichida) -> limit qo'yamiz
        lg = (l <= sup + 1.0 * a) & (c > sup); sh = (h >= res - 1.0 * a) & (c < res)
        limit = (sup - 0.5 * a).where(lg, (res + 0.5 * a).where(sh, np.nan))
        s = _f(df, lg, sh, sl=1.5 * a, tp=1.0 * a, time_stop=16)
        s.limit_price = np.asarray(limit, dtype=float); s.limit_ttl = 8
        return s


@reg
class SessionFakeoutFade(Z):
    """6) Osiyo diapazoni (00-07 UTC) London ochilishida buziladi va qaytadi -> qarama-qarshi kirish, TP diapazon o'rtasi."""
    name, family = "hw_session_fakeout_fade_london", "highwr"
    def fsignals(self, df):
        idx = df.index; hour = idx.hour.values; day = ind.day_index(idx); n = len(df)
        h, l, c = df["high"].values, df["low"].values, df["close"].values
        a = ind.atr(df, 14).values
        rh = np.full(n, np.nan); rl = np.full(n, np.nan)
        lg = np.zeros(n, bool); sh = np.zeros(n, bool); tp = np.full(n, np.nan); sl = np.full(n, np.nan)
        cur = -1; ah = al = np.nan; broke_up = broke_dn = False; ext = np.nan
        for i in range(n):
            if day[i] != cur:
                cur = day[i]; ah = al = np.nan; broke_up = broke_dn = False
            if hour[i] < 7:
                ah = h[i] if np.isnan(ah) else max(ah, h[i]); al = l[i] if np.isnan(al) else min(al, l[i])
            elif 7 <= hour[i] < 11 and not np.isnan(ah):
                if not broke_up and c[i] > ah: broke_up = True; ext = h[i]
                elif broke_up and c[i] < ah:                        # diapazonga qaytdi -> short
                    sh[i] = True; sl[i] = ext - c[i] + 0.25 * a[i]; tp[i] = c[i] - (ah + al) / 2; broke_up = False
                if not broke_dn and c[i] < al: broke_dn = True; ext = l[i]
                elif broke_dn and c[i] > al:                         # qaytdi -> long
                    lg[i] = True; sl[i] = c[i] - ext + 0.25 * a[i]; tp[i] = (ah + al) / 2 - c[i]; broke_dn = False
                if broke_up: ext = max(ext, h[i])
                if broke_dn: ext = min(ext, l[i])
        ok = (tp > 0) & (sl > 0)
        return _f(df, lg & ok, sh & ok, sl=sl, tp=tp, group=day, time_stop=32)


@reg
class GridNeutral(Z):
    """1) Neytral grid-bot (yonbosh bozor). Alohida simulyator: halalbot/grid_backtest.py."""
    name, family = "hw_grid_neutral_10_levels_sl", "highwr"
    is_grid = True
    def fsignals(self, df):
        raise NotImplementedError("grid alohida dvigatelda ishlaydi: run_any() ni ishlating")


def run_any(df, Zc, cfg):
    """Strategiya turiga qarab mos dvigatelni chaqiradi (grid yoki signal-asosli)."""
    from .futures_backtest import run_futures
    if getattr(Zc, "is_grid", False):
        from .grid_backtest import GridConfig, run_grid
        return run_grid(df, GridConfig(leverage=cfg.leverage, taker_fee=cfg.taker_fee, maker_fee=cfg.maker_fee,
                                       slippage=cfg.slippage, funding_rate_8h=cfg.funding_rate_8h))
    return run_futures(df, Zc(), cfg)


HIGHWR = [z for z in ZOO if z.family == "highwr"]


from . import smc as _smc  # noqa: E402  (SMC strategiyalarini ro'yxatga qo'shadi)
SMC = _smc.SMC
