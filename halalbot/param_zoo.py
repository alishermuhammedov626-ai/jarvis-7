"""Parametrik strategiya generatori: shablon x parametrlar x chiqish qoidasi -> yuzlab variantlar.
Har variant `Z` sinfi; nomi determinik. Nazorat: N ta tasodifiy-kirish varianti (empirik nol taqsimot)."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from . import indicators as ind
from .strategy_zoo import Z, _f, _cross_up, _cross_dn, stoch, cci, macd, adx_dmi, supertrend

EXITS = {"sl2_tp3": dict(sl_mult=2, tp_mult=3), "sl1.5_tp1.5": dict(sl_mult=1.5, tp_mult=1.5),
         "sl3_trail3": dict(sl_mult=3, tp_mult=0, trail=3.0), "sl2_signal": dict(sl_mult=2, tp_mult=0)}


def _mk(name, fam, fn):
    cls = type(name, (Z,), {"name": name, "family": fam, "fsignals": lambda self, df, fn=fn: fn(df)})
    return cls


def _apply_exit(df, lg, sh, ex, exit_long=None, exit_short=None, **kw):
    e = dict(EXITS[ex]); use_sig = ex == "sl2_signal"
    return _f(df, lg, sh, exit_long=exit_long if use_sig else None, exit_short=exit_short if use_sig else None, **e, **kw)


def build(n_random=50):
    out = []
    # 1) EMA kesishma
    for f, s in [(5, 13), (8, 21), (9, 21), (13, 34), (21, 55), (34, 89), (50, 100), (50, 200), (20, 100)]:
        for ex in EXITS:
            def fn(df, f=f, s=s, ex=ex):
                c = df["close"]; a, b = ind.ema(c, f), ind.ema(c, s)
                return _apply_exit(df, _cross_up(a, b), _cross_dn(a, b), ex, _cross_dn(a, b), _cross_up(a, b))
            out.append(_mk(f"p_ema_{f}_{s}__{ex}", "p_ema", fn))
    # 2) RSI qaytish
    for n, lo in itertools.product((2, 5, 7, 14, 21), ((20, 80), (25, 75), (30, 70), (35, 65))):
        for ex in ("sl2_tp3", "sl1.5_tp1.5", "sl2_signal"):
            def fn(df, n=n, lo=lo[0], hi=lo[1], ex=ex):
                r = ind.rsi(df["close"], n)
                return _apply_exit(df, _cross_up(r, r * 0 + lo), _cross_dn(r, r * 0 + hi), ex, r > 50, r < 50, time_stop=64)
            out.append(_mk(f"p_rsi_{n}_{lo[0]}_{lo[1]}__{ex}", "p_rsi", fn))
    # 3) Bollinger qaytish va breakout
    for n, k in itertools.product((10, 20, 30, 50), (1.5, 2.0, 2.5, 3.0)):
        for ex in ("sl2_tp3", "sl2_signal"):
            def fn(df, n=n, k=k, ex=ex):
                c = df["close"]; lo, mid, hi = ind.bollinger(c, n, k)
                return _apply_exit(df, c < lo, c > hi, ex, c >= mid, c <= mid, time_stop=48)
            out.append(_mk(f"p_bbrev_{n}_{k}__{ex}", "p_bb", fn))
            def fn2(df, n=n, k=k, ex=ex):
                c = df["close"]; lo, mid, hi = ind.bollinger(c, n, k)
                return _apply_exit(df, _cross_up(c, hi), _cross_dn(c, lo), ex, c < mid, c > mid)
            out.append(_mk(f"p_bbbreak_{n}_{k}__{ex}", "p_bb", fn2))
    # 4) Donchian
    for n, xn in [(10, 5), (20, 10), (40, 20), (55, 20), (96, 48), (192, 96)]:
        for ex in ("sl2_signal", "sl3_trail3", "sl2_tp3"):
            def fn(df, n=n, xn=xn, ex=ex):
                c = df["close"]; dh, dl = ind.donchian_high(df["high"], n), ind.donchian_low(df["low"], n)
                xh, xl = ind.donchian_high(df["high"], xn), ind.donchian_low(df["low"], xn)
                return _apply_exit(df, c > dh, c < dl, ex, c < xl, c > xh)
            out.append(_mk(f"p_donchian_{n}_{xn}__{ex}", "p_donchian", fn))
    # 5) MACD
    for f, s, g in [(12, 26, 9), (8, 17, 9), (5, 35, 5), (19, 39, 9), (24, 52, 18)]:
        for ex in EXITS:
            def fn(df, f=f, s=s, g=g, ex=ex):
                m, si, _ = macd(df["close"], f, s, g)
                return _apply_exit(df, _cross_up(m, si), _cross_dn(m, si), ex, _cross_dn(m, si), _cross_up(m, si))
            out.append(_mk(f"p_macd_{f}_{s}_{g}__{ex}", "p_macd", fn))
    # 6) SuperTrend
    for n, m in itertools.product((7, 10, 14, 20), (1.5, 2.0, 3.0, 4.0)):
        for ex in ("sl2_signal", "sl3_trail3"):
            def fn(df, n=n, m=m, ex=ex):
                _, d = supertrend(df, n, m)
                return _apply_exit(df, (d > 0) & (d.shift(1) < 0), (d < 0) & (d.shift(1) > 0), ex, d < 0, d > 0)
            out.append(_mk(f"p_supertrend_{n}_{m}__{ex}", "p_supertrend", fn))
    # 7) Keltner breakout
    for n, m in itertools.product((10, 20, 50), (1.0, 1.5, 2.0, 3.0)):
        for ex in ("sl2_signal", "sl2_tp3"):
            def fn(df, n=n, m=m, ex=ex):
                c = df["close"]; e = ind.ema(c, n); a = ind.atr(df, n)
                return _apply_exit(df, _cross_up(c, e + m * a), _cross_dn(c, e - m * a), ex, c < e, c > e)
            out.append(_mk(f"p_keltner_{n}_{m}__{ex}", "p_keltner", fn))
    # 8) Z-score
    for n, z in itertools.product((20, 50, 100, 200), (1.5, 2.0, 2.5, 3.0)):
        for ex in ("sl2_signal", "sl2_tp3"):
            def fn(df, n=n, z=z, ex=ex):
                c = df["close"]; zz = (c - c.rolling(n).mean()) / c.rolling(n).std()
                return _apply_exit(df, zz < -z, zz > z, ex, zz > 0, zz < 0, time_stop=96)
            out.append(_mk(f"p_zscore_{n}_{z}__{ex}", "p_zscore", fn))
    # 9) Stochastic
    for n, th in itertools.product((5, 9, 14, 21), ((20, 80), (10, 90))):
        for ex in ("sl2_tp3", "sl2_signal"):
            def fn(df, n=n, lo=th[0], hi=th[1], ex=ex):
                k, d = stoch(df, n)
                return _apply_exit(df, _cross_up(k, d) & (k < lo), _cross_dn(k, d) & (k > hi), ex, k > hi, k < lo, time_stop=48)
            out.append(_mk(f"p_stoch_{n}_{th[0]}_{th[1]}__{ex}", "p_stoch", fn))
    # 10) CCI
    for n, t in itertools.product((14, 20, 50), (100, 150, 200)):
        for ex in ("sl2_tp3", "sl2_signal"):
            def fn(df, n=n, t=t, ex=ex):
                x = cci(df, n)
                return _apply_exit(df, _cross_up(x, x * 0 - t), _cross_dn(x, x * 0 + t), ex, x > 0, x < 0, time_stop=48)
            out.append(_mk(f"p_cci_{n}_{t}__{ex}", "p_cci", fn))
    # 11) ADX/DMI
    for n, t in itertools.product((10, 14, 20), (20, 25, 30)):
        for ex in ("sl2_signal", "sl3_trail3"):
            def fn(df, n=n, t=t, ex=ex):
                adx, p, m = adx_dmi(df, n)
                return _apply_exit(df, (adx > t) & _cross_up(p, m), (adx > t) & _cross_dn(p, m), ex, _cross_dn(p, m), _cross_up(p, m))
            out.append(_mk(f"p_adx_{n}_{t}__{ex}", "p_adx", fn))
    # 12) ROC momentum
    for n, t in itertools.product((6, 12, 24, 48), (0.3, 0.5, 1.0)):
        for ex in ("sl2_signal", "sl2_tp3"):
            def fn(df, n=n, t=t, ex=ex):
                r = df["close"].pct_change(n) * 100
                return _apply_exit(df, _cross_up(r, r * 0 + t), _cross_dn(r, r * 0 - t), ex, r < 0, r > 0, time_stop=48)
            out.append(_mk(f"p_roc_{n}_{t}__{ex}", "p_roc", fn))
    # 13) Trend filtri + pullback (EMA200 + EMA20)
    for tr, pb in itertools.product((100, 200), (10, 20, 50)):
        for ex in ("sl2_tp3", "sl1.5_tp1.5", "sl3_trail3"):
            def fn(df, tr=tr, pb=pb, ex=ex):
                c = df["close"]; e1, e2 = ind.ema(c, pb), ind.ema(c, tr)
                return _apply_exit(df, (c > e2) & _cross_up(c, e1), (c < e2) & _cross_dn(c, e1), ex, c < e2, c > e2, time_stop=64)
            out.append(_mk(f"p_pullback_{tr}_{pb}__{ex}", "p_pullback", fn))
    # nazorat: tasodifiy kirish, har xil seed va chastota
    for k in range(n_random):
        for ex in ("sl2_tp3",):
            def fn(df, k=k, ex=ex):
                rng = np.random.default_rng(1000 + k + int(df["close"].iloc[0]) % 997)
                u = rng.random(len(df)); p = 0.005 + 0.03 * (k % 5) / 4
                return _apply_exit(df, u < p, u > 1 - p, ex, time_stop=48)
            out.append(_mk(f"control_random_{k:02d}", "control", fn))
    return out


PARAM_ZOO = build()
