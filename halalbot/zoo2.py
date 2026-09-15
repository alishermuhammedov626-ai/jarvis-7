"""TradingView'da eng mashhur qo'shimcha strategiyalar (2-to'plam), hammasi causal."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .strategy_zoo import Z, _f, _cross_up, _cross_dn, reg, stoch, cci, macd, adx_dmi, supertrend, hull, tema


def stoch_rsi(c, n=14, k=3, d=3):
    r = ind.rsi(c, n); lo = r.rolling(n).min(); hi = r.rolling(n).max()
    s = 100 * (r - lo) / (hi - lo).replace(0, np.nan)
    kk = s.rolling(k).mean(); return kk, kk.rolling(d).mean()

def awesome(df): hl2 = (df["high"] + df["low"]) / 2; return ind.sma(hl2, 5) - ind.sma(hl2, 34)

def ultimate(df, a=7, b=14, c=28):
    pc = df["close"].shift(1); bp = df["close"] - pd.concat([df["low"], pc], axis=1).min(axis=1)
    tr = pd.concat([df["high"], pc], axis=1).max(axis=1) - pd.concat([df["low"], pc], axis=1).min(axis=1)
    def avg(n): return bp.rolling(n).sum() / tr.rolling(n).sum().replace(0, np.nan)
    return 100 * (4 * avg(a) + 2 * avg(b) + avg(c)) / 7

def kama(c, n=10, fast=2, slow=30):
    ch = (c - c.shift(n)).abs(); vol = c.diff().abs().rolling(n).sum()
    er = ch / vol.replace(0, np.nan); sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    out = np.full(len(c), np.nan); cv = c.values; scv = sc.values; prev = np.nan
    for i in range(len(c)):
        if np.isnan(scv[i]): continue
        prev = cv[i] if np.isnan(prev) else prev + scv[i] * (cv[i] - prev); out[i] = prev
    return pd.Series(out, c.index)

def dema(c, n): e = ind.ema(c, n); return 2 * e - ind.ema(e, n)

def stc(c, fast=23, slow=50, cyc=10):
    m = ind.ema(c, fast) - ind.ema(c, slow)
    def st(x, n):
        lo = x.rolling(n).min(); hi = x.rolling(n).max(); return 100 * (x - lo) / (hi - lo).replace(0, np.nan)
    return ind.ema(st(ind.ema(st(m, cyc), 3), cyc), 3)

def wavetrend(df, n1=10, n2=21):
    ap = (df["high"] + df["low"] + df["close"]) / 3; esa = ind.ema(ap, n1); d = ind.ema((ap - esa).abs(), n1)
    ci = (ap - esa) / (0.015 * d.replace(0, np.nan)); wt1 = ind.ema(ci, n2); return wt1, ind.sma(wt1, 4)

def ut_bot(df, key=1.0, n=10):
    c = df["close"].values; a = (key * ind.atr(df, n)).values; n_ = len(df); ts = np.full(n_, np.nan)
    for i in range(1, n_):
        if np.isnan(a[i]): continue
        p = ts[i - 1]
        if np.isnan(p): ts[i] = c[i] - a[i]; continue
        if c[i] > p and c[i - 1] > p: ts[i] = max(p, c[i] - a[i])
        elif c[i] < p and c[i - 1] < p: ts[i] = min(p, c[i] + a[i])
        else: ts[i] = c[i] - a[i] if c[i] > p else c[i] + a[i]
    return pd.Series(ts, df.index)

def range_filter(c, n=100, mult=3.0):
    rng = ind.ema((ind.ema(c.diff().abs(), n)) * mult, 2 * n - 1)
    out = np.full(len(c), np.nan); cv = c.values; rv = rng.values; prev = np.nan
    for i in range(len(c)):
        if np.isnan(rv[i]): continue
        if np.isnan(prev): prev = cv[i]
        elif cv[i] > prev: prev = max(prev, cv[i] - rv[i])
        else: prev = min(prev, cv[i] + rv[i])
        out[i] = prev
    return pd.Series(out, c.index)

def fisher(df, n=9):
    hl2 = (df["high"] + df["low"]) / 2; lo = hl2.rolling(n).min(); hi = hl2.rolling(n).max()
    x = (2 * (hl2 - lo) / (hi - lo).replace(0, np.nan) - 1).clip(-0.999, 0.999)
    v = x.ewm(alpha=0.33, adjust=False).mean(); f = 0.5 * np.log((1 + v) / (1 - v)); return f.ewm(alpha=0.5, adjust=False).mean()

def rvi(df, n=10):
    def sw(x): return (x + 2 * x.shift(1) + 2 * x.shift(2) + x.shift(3)) / 6
    num = sw(df["close"] - df["open"]).rolling(n).mean(); den = sw(df["high"] - df["low"]).rolling(n).mean()
    r = num / den.replace(0, np.nan); return r, sw(r)

def coppock(c): roc = lambda n: c.pct_change(n) * 100; return (roc(14) + roc(11)).rolling(10).apply(lambda x: np.dot(x, np.arange(1, 11)) / 55, raw=True)

# ----------------------------------------------------------------- strategiyalar
@reg
class StochRsiCross(Z):
    name, family = "tv_stoch_rsi_cross", "tv"
    def fsignals(self, df):
        k, d = stoch_rsi(df["close"]); return _f(df, _cross_up(k, d) & (k < 20), _cross_dn(k, d) & (k > 80), exit_long=k > 80, exit_short=k < 20, tp_mult=0, time_stop=48)

@reg
class AwesomeOscillator(Z):
    name, family = "tv_awesome_oscillator_zero", "tv"
    def fsignals(self, df):
        ao = awesome(df); z = ao * 0; return _f(df, _cross_up(ao, z), _cross_dn(ao, z), exit_long=ao < 0, exit_short=ao > 0, tp_mult=0)

@reg
class UltimateOsc(Z):
    name, family = "tv_ultimate_oscillator", "tv"
    def fsignals(self, df):
        u = ultimate(df); return _f(df, _cross_up(u, u * 0 + 30), _cross_dn(u, u * 0 + 70), exit_long=u > 50, exit_short=u < 50, tp_mult=0, time_stop=48)

@reg
class BollingerPctB(Z):
    name, family = "tv_bollinger_pctb_rsi", "tv"
    def fsignals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2); b = (c - lo) / (hi - lo).replace(0, np.nan); r = ind.rsi(c, 14)
        return _f(df, (b < 0) & (r < 35), (b > 1) & (r > 65), exit_long=b > 0.5, exit_short=b < 0.5, tp_mult=0, time_stop=32)

@reg
class KamaCross(Z):
    name, family = "tv_kama_price_cross", "tv"
    def fsignals(self, df):
        c = df["close"]; k = kama(c); return _f(df, _cross_up(c, k), _cross_dn(c, k), exit_long=c < k, exit_short=c > k, tp_mult=0)

@reg
class DemaCross(Z):
    name, family = "tv_dema_cross_20_50", "tv"
    def fsignals(self, df):
        c = df["close"]; f, s = dema(c, 20), dema(c, 50); return _f(df, _cross_up(f, s), _cross_dn(f, s), exit_long=_cross_dn(f, s), exit_short=_cross_up(f, s), tp_mult=0)

@reg
class HullSuite(Z):
    name, family = "tv_hull_suite_55", "tv"
    def fsignals(self, df):
        h = hull(df["close"], 55); up = h > h.shift(2); u1 = up.shift(1).fillna(False).astype(bool)
        return _f(df, up & ~u1, ~up & u1, exit_long=~up, exit_short=up, tp_mult=0)

@reg
class SchaffTrendCycle(Z):
    name, family = "tv_schaff_trend_cycle", "tv"
    def fsignals(self, df):
        s = stc(df["close"]); return _f(df, _cross_up(s, s * 0 + 25), _cross_dn(s, s * 0 + 75), exit_long=_cross_dn(s, s * 0 + 75), exit_short=_cross_up(s, s * 0 + 25), tp_mult=0)

@reg
class SqueezeMomentum(Z):
    name, family = "tv_squeeze_momentum_lazybear", "tv"
    def fsignals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2); e = ind.ema(c, 20); a = ind.atr(df, 20)
        sq = (lo > e - 1.5 * a) & (hi < e + 1.5 * a)
        mom = c - ((df["high"].rolling(20).max() + df["low"].rolling(20).min()) / 2 + ind.sma(c, 20)) / 2
        rel = sq.shift(1).fillna(False).astype(bool) & ~sq
        return _f(df, rel & (mom > 0), rel & (mom < 0), exit_long=mom < 0, exit_short=mom > 0, tp_mult=0)

@reg
class WaveTrend(Z):
    name, family = "tv_wavetrend_lazybear", "tv"
    def fsignals(self, df):
        w1, w2 = wavetrend(df); return _f(df, _cross_up(w1, w2) & (w1 < -53), _cross_dn(w1, w2) & (w1 > 53), exit_long=_cross_dn(w1, w2), exit_short=_cross_up(w1, w2), tp_mult=0)

@reg
class QqeMod(Z):
    name, family = "tv_qqe_mod_simplified", "tv"
    def fsignals(self, df):
        r = ind.ema(ind.rsi(df["close"], 14), 5); band = ind.ema(ind.ema((r - r.shift(1)).abs(), 27), 27) * 4.236
        return _f(df, _cross_up(r, r * 0 + 50) & (r - r.shift(1) > 0), _cross_dn(r, r * 0 + 50), exit_long=r < 50 - band, exit_short=r > 50 + band, tp_mult=0)

@reg
class UtBotAlert(Z):
    name, family = "tv_ut_bot_alert", "tv"
    def fsignals(self, df):
        c = df["close"]; ts = ut_bot(df); return _f(df, _cross_up(c, ts), _cross_dn(c, ts), exit_long=c < ts, exit_short=c > ts, tp_mult=0)

@reg
class HalfTrend(Z):
    name, family = "tv_half_trend_simplified", "tv"
    def fsignals(self, df):
        h, l, c = df["high"], df["low"], df["close"]; hi = h.rolling(2).max().shift(1); lo = l.rolling(2).min().shift(1)
        up = (c > ind.sma(h, 2).shift(1)) & (c > hi); dn = (c < ind.sma(l, 2).shift(1)) & (c < lo)
        return _f(df, up & ~up.shift(1).fillna(False).astype(bool), dn & ~dn.shift(1).fillna(False).astype(bool), sl_mult=2, tp_mult=0, trail=2.0)

@reg
class RangeFilterDW(Z):
    name, family = "tv_range_filter_donovanwall", "tv"
    def fsignals(self, df):
        c = df["close"]; rf = range_filter(c); up = rf > rf.shift(1); dn = rf < rf.shift(1)
        return _f(df, up & (c > rf) & ~up.shift(1).fillna(False).astype(bool), dn & (c < rf) & ~dn.shift(1).fillna(False).astype(bool), exit_long=dn, exit_short=up, tp_mult=0)

@reg
class FisherCross(Z):
    name, family = "tv_fisher_transform", "tv"
    def fsignals(self, df):
        f = fisher(df); return _f(df, _cross_up(f, f.shift(1)) & (f < -1.5), _cross_dn(f, f.shift(1)) & (f > 1.5), exit_long=f > 0, exit_short=f < 0, tp_mult=0, time_stop=48)

@reg
class RviCross(Z):
    name, family = "tv_rvi_cross", "tv"
    def fsignals(self, df):
        r, s = rvi(df); return _f(df, _cross_up(r, s), _cross_dn(r, s), exit_long=_cross_dn(r, s), exit_short=_cross_up(r, s), tp_mult=0)

@reg
class CoppockZero(Z):
    name, family = "tv_coppock_curve", "tv"
    def fsignals(self, df):
        cp = coppock(df["close"]); z = cp * 0; return _f(df, _cross_up(cp, z), _cross_dn(cp, z), exit_long=cp < 0, exit_short=cp > 0, sl_mult=3, tp_mult=0)

@reg
class Guppy(Z):
    name, family = "tv_guppy_gmma", "tv"
    def fsignals(self, df):
        c = df["close"]; sh = pd.concat([ind.ema(c, n) for n in (3, 5, 8, 10, 12, 15)], axis=1); lg = pd.concat([ind.ema(c, n) for n in (30, 35, 40, 45, 50, 60)], axis=1)
        up = sh.min(axis=1) > lg.max(axis=1); dn = sh.max(axis=1) < lg.min(axis=1)
        return _f(df, up & ~up.shift(1).fillna(False).astype(bool), dn & ~dn.shift(1).fillna(False).astype(bool), exit_long=~up, exit_short=~dn, tp_mult=0)

@reg
class Macd200Ema(Z):
    name, family = "tv_macd_200ema_youtube", "tv"
    def fsignals(self, df):
        c = df["close"]; m, s, _ = macd(c); e = ind.ema(c, 200)
        return _f(df, _cross_up(m, s) & (m < 0) & (c > e), _cross_dn(m, s) & (m > 0) & (c < e), sl_mult=1.5, tp_mult=2.25)

@reg
class TripleRsi(Z):
    name, family = "tv_triple_rsi_7_14_21", "tv"
    def fsignals(self, df):
        c = df["close"]; r7, r14, r21 = ind.rsi(c, 7), ind.rsi(c, 14), ind.rsi(c, 21)
        return _f(df, (r7 < 30) & (r14 < 35) & (r21 < 40) & (r7 > r7.shift(1)), (r7 > 70) & (r14 > 65) & (r21 > 60) & (r7 < r7.shift(1)), time_stop=48)

@reg
class BbRsiMacdCombo(Z):
    name, family = "tv_bb_rsi_macd_combo", "tv"
    def fsignals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2); r = ind.rsi(c, 14); m, s, h = macd(c)
        return _f(df, (c < lo) & (r < 30) & (h > h.shift(1)), (c > hi) & (r > 70) & (h < h.shift(1)), exit_long=c > mid, exit_short=c < mid, tp_mult=0, time_stop=48)

@reg
class MorningEveningStar(Z):
    name, family = "tv_morning_evening_star", "tv"
    def fsignals(self, df):
        o, c = df["open"], df["close"]; b = c - o; a = ind.atr(df, 14)
        ms = (b.shift(2) < -0.5 * a) & (b.shift(1).abs() < 0.2 * a) & (b > 0.5 * a)
        es = (b.shift(2) > 0.5 * a) & (b.shift(1).abs() < 0.2 * a) & (b < -0.5 * a)
        return _f(df, ms, es, sl_mult=1.5, tp_mult=2.5, time_stop=32)

@reg
class ThreeSoldiersCrows(Z):
    name, family = "tv_three_white_soldiers_black_crows", "tv"
    def fsignals(self, df):
        o, c = df["open"], df["close"]; b = c - o; a = ind.atr(df, 14)
        up = (b > 0.3 * a) & (b.shift(1) > 0.3 * a) & (b.shift(2) > 0.3 * a) & (c > c.shift(1)) & (c.shift(1) > c.shift(2))
        dn = (b < -0.3 * a) & (b.shift(1) < -0.3 * a) & (b.shift(2) < -0.3 * a) & (c < c.shift(1)) & (c.shift(1) < c.shift(2))
        return _f(df, up, dn, sl_mult=2, tp_mult=3, time_stop=48)

@reg
class DojiAtBands(Z):
    name, family = "tv_doji_at_bollinger", "tv"
    def fsignals(self, df):
        o, c, h, l = df["open"], df["close"], df["high"], df["low"]; lo, mid, hi = ind.bollinger(c, 20, 2)
        doji = (c - o).abs() < 0.1 * (h - l).replace(0, np.nan)
        return _f(df, doji & (l < lo), doji & (h > hi), exit_long=c > mid, exit_short=c < mid, sl_mult=1.5, tp_mult=0, time_stop=32)

@reg
class Tweezer(Z):
    name, family = "tv_tweezer_top_bottom", "tv"
    def fsignals(self, df):
        o, c, h, l = df["open"], df["close"], df["high"], df["low"]; a = ind.atr(df, 14)
        bot = ((l - l.shift(1)).abs() < 0.1 * a) & (c.shift(1) < o.shift(1)) & (c > o)
        top = ((h - h.shift(1)).abs() < 0.1 * a) & (c.shift(1) > o.shift(1)) & (c < o)
        return _f(df, bot, top, sl_mult=1.5, tp_mult=2.5, time_stop=32)

@reg
class DualThrust(Z):
    name, family = "tv_dual_thrust", "tv"
    def fsignals(self, df):
        d = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        rng = pd.concat([d["high"].rolling(4).max() - d["close"].rolling(4).min(), d["close"].rolling(4).max() - d["low"].rolling(4).min()], axis=1).max(axis=1).shift(1)
        R = rng.reindex(df.index, method="ffill"); O = d["open"].reindex(df.index, method="ffill"); c = df["close"]
        day = ind.day_index(df.index)
        return _f(df, c > O + 0.5 * R, c < O - 0.5 * R, group=day, sl=0.5 * R, tp=1.0 * R, time_stop=96)

@reg
class RBreaker(Z):
    name, family = "tv_r_breaker", "tv"
    def fsignals(self, df):
        d = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).shift(1)
        p = (d["high"] + d["low"] + d["close"]) / 3
        bbreak = d["high"] + 2 * (p - d["low"]); sbreak = d["low"] - 2 * (d["high"] - p)
        BB, SB = bbreak.reindex(df.index, method="ffill"), sbreak.reindex(df.index, method="ffill"); c = df["close"]
        day = ind.day_index(df.index)
        return _f(df, _cross_up(c, BB), _cross_dn(c, SB), group=day, sl_mult=2, tp_mult=3, time_stop=96)

@reg
class MaEnvelope(Z):
    name, family = "tv_ma_envelope_1.5pct", "tv"
    def fsignals(self, df):
        c = df["close"]; m = ind.sma(c, 20); return _f(df, c < m * 0.985, c > m * 1.015, exit_long=c >= m, exit_short=c <= m, sl_mult=2, tp_mult=0, time_stop=48)

@reg
class DoubleSupertrend(Z):
    name, family = "tv_double_supertrend_agree", "tv"
    def fsignals(self, df):
        _, d1 = supertrend(df, 10, 1.0); _, d3 = supertrend(df, 10, 3.0)
        up = (d1 > 0) & (d3 > 0); dn = (d1 < 0) & (d3 < 0)
        return _f(df, up & ~up.shift(1).fillna(False).astype(bool), dn & ~dn.shift(1).fillna(False).astype(bool), exit_long=d1 < 0, exit_short=d1 > 0, sl_mult=3, tp_mult=0)


# ----------------------------------------------------------------- "ML" uslubidagilar (walk-forward, faqat o'tmishda o'rgatiladi)
def _features(df):
    c = df["close"]; a = ind.atr(df, 14)
    F = pd.concat([ind.rsi(c, 14) / 100 - 0.5, cci(df, 20) / 200, adx_dmi(df)[0] / 50, wavetrend(df)[0] / 100,
                   c.pct_change(4) / (a / c), c.pct_change(16) / (a / c)], axis=1)
    return F.values

@reg
class LorentzianKnn(Z):
    """TradingView 'Machine Learning: Lorentzian Classification' soddalashtirilgan: k=8 eng yaqin o'tmish nuqta, 4-sham oldinga yo'nalish."""
    name, family = "ml_lorentzian_knn_k8", "ml"
    def fsignals(self, df):
        F = _features(df); c = df["close"].values; n = len(df); H = 4; k = 8; lookback = 1500
        y = np.sign(np.roll(c, -H) - c); pred = np.zeros(n)
        for i in range(200, n, 4):                          # har 4 shamda qaror (tezlik uchun)
            lo = max(0, i - lookback); hi = i - H          # faqat natijasi ma'lum bo'lgan o'tmish
            if hi - lo < 100 or np.isnan(F[i]).any(): continue
            X = F[lo:hi]; ok = ~np.isnan(X).any(axis=1)
            if ok.sum() < 50: continue
            dist = np.log1p(np.abs(X[ok] - F[i])).sum(axis=1)
            nn = np.argsort(dist)[:k]; pred[i:i + 4] = np.sign(y[lo:hi][ok][nn].sum())
        p = pd.Series(pred, df.index)
        return _f(df, (p > 0) & (p.shift(1) <= 0), (p < 0) & (p.shift(1) >= 0), exit_long=p < 0, exit_short=p > 0, tp_mult=0, time_stop=48)

@reg
class LogisticWalkForward(Z):
    """Logistik regressiya, har 480 shamda oldingi 2000 shamda qayta o'rgatiladi (numpy, sklearn'siz)."""
    name, family = "ml_logistic_walkforward", "ml"
    def fsignals(self, df):
        F = _features(df); c = df["close"].values; n = len(df); H = 4
        y = (np.roll(c, -H) > c).astype(float); pred = np.full(n, np.nan); w = None
        for start in range(2000, n, 480):
            lo, hi = start - 2000, start - H
            X = F[lo:hi]; ok = ~np.isnan(X).any(axis=1); X = X[ok]; Y = y[lo:hi][ok]
            if len(Y) < 200: continue
            Xb = np.hstack([X, np.ones((len(X), 1))]); w = np.zeros(Xb.shape[1])
            for _ in range(200):
                pz = 1 / (1 + np.exp(-Xb @ w)); w -= 0.1 * (Xb.T @ (pz - Y) / len(Y) + 0.01 * w)
            seg = F[start:min(start + 480, n)]; segb = np.hstack([seg, np.ones((len(seg), 1))])
            pred[start:start + len(seg)] = 1 / (1 + np.exp(-np.nan_to_num(segb) @ w))
        p = pd.Series(pred, df.index)
        return _f(df, (p > 0.58) & (p.shift(1) <= 0.58), (p < 0.42) & (p.shift(1) >= 0.42), exit_long=p < 0.5, exit_short=p > 0.5, tp_mult=0, time_stop=48)
