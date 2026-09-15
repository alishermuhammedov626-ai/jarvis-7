#!/usr/bin/env python3
"""Parametr variantlari sinovi: xarajatdan omon qoladigan sozlama bormi?
Har variant bir xil sintetik grafiklar to'plamida (seed lar bir xil) solishtiriladi."""
import argparse, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from halalbot import synthetic
from halalbot.backtest import BacktestConfig, run
from halalbot import strategies as S
from halalbot import indicators as ind


class A_wide(S.TrendPullback):
    name = "A2_pullback_TP3_noTimeStop"
    def signals(self, df):
        s = super().signals(df); s.tp_dist = s.sl_dist * 2.0; s.time_stop = 96; return s

class B_slow(S.DonchianBreakout):
    name = "B2_donchian96_trail4"
    def signals(self, df):
        c = df["close"]; dh = ind.donchian_high(df["high"], 96); e200 = ind.ema(c, 200); a = ind.atr(df, 14)
        entry = (c > dh) & (e200 > e200.shift(16))
        return S._pack(df, entry.fillna(False), 3.0 * a, np.full(len(df), np.nan), trail=4.0, time_stop=288, atr_arr=a.values)

class C_upper(S.BollingerMeanReversion):
    name = "C2_bb_exit_upper"
    def signals(self, df):
        c = df["close"]; lo, mid, hi = ind.bollinger(c, 20, 2.0); r = ind.rsi(c, 14); a = ind.atr(df, 14)
        entry = (c < lo) & (r < 30); exit_sig = c >= hi
        return S._pack(df, entry.fillna(False), 2.5 * a, np.full(len(df), np.nan), exit_sig=exit_sig.fillna(False), time_stop=64, atr_arr=a.values)

class C_1h(S.BollingerMeanReversion):
    name = "C3_bb_1h_timeframe"
    def signals(self, df):
        h = df.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        c = h["close"]; lo, mid, _ = ind.bollinger(c, 20, 2.0); r = ind.rsi(c, 14); a = ind.atr(h, 14)
        entry = ((c < lo) & (r < 30)).reindex(df.index, method="ffill").fillna(False).astype(bool)
        # 1h signal faqat shu soatning oxirgi 15m shamida ishlasin
        last = (df.index.minute == 45)
        entry = entry & last
        exit_sig = (c >= mid).reindex(df.index, method="ffill").fillna(False).astype(bool) & last
        sl = (2.0 * a).reindex(df.index, method="ffill").where(last)   # faqat yopilgan 1h sham ATR'i
        return S._pack(df, entry, sl, np.full(len(df), np.nan), exit_sig=exit_sig, time_stop=128, atr_arr=None)

class D_wide(S.SessionORB):
    name = "D2_orb_TP3x"
    def signals(self, df):
        s = super().signals(df); s.tp_dist = s.tp_dist * 2.0; s.time_stop = 15; return s

class E_wide(S.RsiScalp):
    name = "E2_rsi_TP2.5"
    def signals(self, df):
        s = super().signals(df); s.tp_dist = s.sl_dist * 2.5; s.time_stop = 48; return s

class A_4h_trend(S.Strategy):
    """4 soatlik trend filtri + 15m pullback; TP yo'q, trailing 3 ATR."""
    name = "F_4h_trend_15m_pullback"
    def signals(self, df):
        c = df["close"]; e20 = ind.ema(c, 20); a = ind.atr(df, 14)
        h4 = df["close"].resample("4h").last(); e4 = ind.ema(h4, 50)
        up = ((h4 > e4) & (e4 > e4.shift(1))).shift(1)   # shift(1): faqat YOPILGAN 4h sham (look-ahead yo'q)
        up15 = up.reindex(df.index, method="ffill").fillna(False).astype(bool)
        cross_up = (c.shift(1) < e20.shift(1)) & (c > e20)
        entry = up15 & cross_up.fillna(False)
        return S._pack(df, entry, 2.0 * a, np.full(len(df), np.nan), trail=3.0, time_stop=192, atr_arr=a.values)


VARIANTS = [S.TrendPullback, A_wide, S.DonchianBreakout, B_slow, S.BollingerMeanReversion, C_upper, C_1h,
            S.SessionORB, D_wide, S.RsiScalp, E_wide, A_4h_trend, S.BuyAndHold]


def one(args):
    regime, seed, days, fee = args
    df = synthetic.generate(regime, days=days, seed=seed)
    rows = []
    for V in VARIANTS:
        m = run(df, V(), BacktestConfig(fee_rate=fee)).metrics(days)
        m.update(regime=regime, seed=seed, strategy=V.name); rows.append(m)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--charts", type=int, default=40); ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--fee", type=float, default=0.00075); ap.add_argument("--seed0", type=int, default=777)
    a = ap.parse_args(); t = time.time()
    jobs = [(r, a.seed0 + k, a.days, a.fee) for r in ["gbm", "garch", "regime", "trend_up", "trend_down"] for k in range(a.charts)]
    rows = []
    with ProcessPoolExecutor(4) as ex:
        for out in ex.map(one, jobs, chunksize=4): rows.extend(out)
    df = pd.DataFrame(rows)
    g = df.groupby(["strategy", "regime"])
    print(f"fee={a.fee*100:.3f}%  charts/regime={a.charts}  days={a.days}  ({time.time()-t:.0f}s)\n")
    print("MEDIAN daromad %:"); print(g["return_pct"].median().unstack().round(1))
    print("\nFoydali grafiklar %:"); print(g["return_pct"].apply(lambda x: (x > 0).mean() * 100).unstack().round(0))
    print("\nKomissiyasiz (gross) median %:"); print(g["gross_return_pct"].median().unstack().round(1))
    print("\nSavdo/kun:"); print(g["trades_per_day"].mean().unstack().round(2))
    print("\nMedian max drawdown %:"); print(g["max_dd_pct"].median().unstack().round(1))
    df.to_csv("reports/variants_raw.csv", index=False)
