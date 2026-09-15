#!/usr/bin/env python3
"""Maxsus qidiruv: kuniga 3-5 savdo, SL:TP = 1:2. Barcha kirish signallari x SL={0.75,1,1.5} ATR, TP=2xSL, 15m."""
import argparse, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from halalbot import synthetic
from halalbot.futures_backtest import FuturesConfig, run_futures
from halalbot.strategy_zoo import ZOO
from halalbot.param_zoo import PARAM_ZOO
from halalbot import indicators as ind

REGIMES = ["gbm", "garch", "regime", "trend_up", "trend_down"]
SL_MULTS = (0.75, 1.0, 1.5)
BASE = {z.name: z for z in ZOO + PARAM_ZOO if not getattr(z, "is_grid", False) and not getattr(z, "is_dca", False)
        and not z.name.endswith(("__sl1.5_tp1.5", "__sl3_trail3", "__sl2_signal"))}   # parametrik chiqish dublikatlarini olib tashlaymiz


class RR2:
    """Kirish signali asl strategiyadan, chiqish: SL=k*ATR, TP=2*SL, chiqish signali yo'q, vaqt stopi 48."""
    def __init__(self, base, k): self.base, self.k = base, k; self.name = f"{base.name}@sl{k}_tp{2*k}"
    def fsignals(self, df):
        s = self.base().fsignals(df); a = ind.atr(df, 14).values
        s.sl_dist = self.k * a; s.tp_dist = 2 * self.k * a
        s.exit_long[:] = False; s.exit_short[:] = False; s.trail_atr = 0.0; s.time_stop = 48
        s.limit_price = None
        return s


def one(args):
    regime, seed, days, lev, fee, names, cap = args
    df = synthetic.generate(regime, days=days, seed=seed); rows = []
    for nm in names:
        b, k = nm.rsplit("@sl", 1); k = float(k.split("_")[0])
        try:
            m = run_futures(df, RR2(BASE[b], k), FuturesConfig(leverage=lev, taker_fee=fee, max_trades_per_day=cap)).metrics(days)
        except Exception as e:
            m = {"return_pct": np.nan, "trades_per_day": 0.0, "liquidated": 0.0, "win_rate_pct": np.nan, "max_dd_pct": np.nan, "gross_return_pct": np.nan}
        m.update(regime=regime, seed=seed, strategy=nm, family=BASE[b].family); rows.append(m)
    return rows


def stage(names, charts, seed0, a):
    jobs = [(r, seed0 + k, a.days, a.leverage, a.fee, list(names), a.cap) for r in REGIMES for k in range(charts)]
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, out in enumerate(ex.map(one, jobs, chunksize=1)):
            rows.extend(out)
            if (i + 1) % 10 == 0: print(f"    {i+1}/{len(jobs)}", flush=True)
    return pd.DataFrame(rows)


def summarize(df):
    g = df.groupby(["strategy", "family"])
    s = g.agg(median_ret=("return_pct", "median"), pct_profitable=("return_pct", lambda x: (x > 0).mean() * 100),
              liq_pct=("liquidated", lambda x: x.mean() * 100), tpd=("trades_per_day", "mean"), win_rate=("win_rate_pct", "mean"),
              median_dd=("max_dd_pct", "median"), gross=("gross_return_pct", "median")).reset_index()
    per = df.pivot_table(index="strategy", columns="regime", values="return_pct", aggfunc="median"); per.columns = [f"med_{c}" for c in per.columns]
    return s.merge(per.reset_index(), on="strategy")


def md(s, cols):
    o = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in s.iterrows(): o.append("| " + " | ".join(str(r[c]) if isinstance(r[c], str) else f"{r[c]:.1f}" for c in cols) + " |")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", type=int, default=8); ap.add_argument("--val-charts", type=int, default=15)
    ap.add_argument("--days", type=int, default=90); ap.add_argument("--leverage", type=float, default=3.0)
    ap.add_argument("--fee", type=float, default=0.0005); ap.add_argument("--cap", type=int, default=5)
    ap.add_argument("--tpd-min", type=float, default=2.5); ap.add_argument("--tpd-max", type=float, default=5.5)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--out", default="reports/rr2")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    names = [f"{b}@sl{k}_tp{2*k}" for b in BASE for k in SL_MULTS]
    print(f"{len(BASE)} kirish signali x {len(SL_MULTS)} SL = {len(names)} sinov, 15m, kuniga max {a.cap}")
    s1 = stage(names, a.charts, 1, a); s1.to_csv(out / "stage1_raw.csv", index=False)
    sum1 = summarize(s1)
    band = sum1[(sum1.tpd >= a.tpd_min) & (sum1.tpd <= a.tpd_max)]
    cand = band[(band.median_ret > 0) & (band.pct_profitable >= 55) & (band.liq_pct < 5)]
    lines = [f"# Maxsus qidiruv: kuniga {a.tpd_min:.0f}-{a.tpd_max:.0f} savdo, SL:TP = 1:2\n",
             f"- {len(BASE)} kirish signali x SL {SL_MULTS} ATR (TP = 2xSL) = {len(names)} sinov; 15m; 3x; taker {a.fee*100:.3f}%; kuniga max {a.cap}",
             f"- 1-bosqich {a.charts} grafik/rejim = {len(s1)} backtest ({time.time()-t0:.0f}s)\n",
             f"## Chastota oralig'ida ({a.tpd_min}-{a.tpd_max} savdo/kun): {len(band)} sinov; shundan foydali median: {(band.median_ret>0).sum()}; mezondan o'tgan: {len(cand)}\n",
             "### Oraliqdagi eng yaxshi 30 (1-bosqich)\n",
             md(band.sort_values("median_ret", ascending=False).head(30), ["strategy", "family", "median_ret", "pct_profitable", "tpd", "win_rate", "gross", "median_dd", "med_gbm", "med_regime"]),
             f"\n### Oraliqdagi winrate taqsimoti: o'rtacha {band.win_rate.mean():.1f}%, maks {band.win_rate.max():.1f}% (1:2 uchun komissiyasiz breakeven 33.3%, komissiya bilan ~45-50%)\n"]
    print(lines[3]); surv = cand
    for rnd, seed0 in enumerate((50_001, 90_001), start=2):
        if surv.empty: break
        sv = stage(sorted(surv.strategy), a.val_charts, seed0, a); sumv = summarize(sv).merge(surv[["strategy"]], on="strategy")
        ok = sumv[(sumv.median_ret > 0) & (sumv.pct_profitable >= 55) & (sumv.liq_pct < 5)]
        lines += [f"\n## {rnd}-bosqich (yangi seedlar {seed0}+): {len(ok)} / {len(sumv)} o'tdi\n", md(sumv.sort_values("median_ret", ascending=False), ["strategy", "median_ret", "pct_profitable", "tpd", "win_rate", "med_gbm", "med_regime", "med_trend_up", "med_trend_down"])]
        print(lines[-2]); surv = ok
    lines.append(f"\n## YAKUN: {len(surv)} sinov barcha bosqichlardan o'tdi\n" + (md(surv, ["strategy", "median_ret", "pct_profitable", "tpd", "win_rate"]) if len(surv) else "Hech biri."))
    (out / "RR2_RESULTS.md").write_text("\n".join(lines)); print(f"\n{out/'RR2_RESULTS.md'} yozildi, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
