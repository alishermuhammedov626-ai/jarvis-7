#!/usr/bin/env python3
"""MEGA sinov: barcha nomli strategiyalar + parametrik variantlar + tasodifiy nazoratlar, 3 bosqich, 3 TF.
Har bosqich butunlay yangi seedlar. 'Topildi' = 3 bosqichdan ham o'tgan. Nazoratlar necha bosqichdan o'tgani
= tasodif darajasi (empirik nol taqsimot)."""
import argparse, os, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from halalbot import synthetic
from halalbot.futures_backtest import FuturesConfig
from halalbot.strategy_zoo import ZOO, run_any
from halalbot.param_zoo import PARAM_ZOO

REGIMES = ["gbm", "garch", "regime", "trend_up", "trend_down"]
TFS = ["15m", "1h", "4h"]
ALL = {z.name: z for z in ZOO + PARAM_ZOO}


def resample(df, tf):
    return df if tf == "15m" else df.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def one(args):
    regime, seed, days, lev, fee, names = args
    base = synthetic.generate(regime, days=days, seed=seed); rows = []
    for tf in TFS:
        df = resample(base, tf)
        for nm in names:
            Zc = ALL[nm]
            if tf != "15m" and (getattr(Zc, "is_grid", False) or getattr(Zc, "is_dca", False)): continue
            try:
                m = run_any(df, Zc, FuturesConfig(leverage=lev, taker_fee=fee)).metrics(days)
            except Exception as e:
                m = {"return_pct": np.nan, "trades": 0, "liquidated": 0.0, "max_dd_pct": np.nan, "win_rate_pct": np.nan, "trades_per_day": 0.0, "gross_return_pct": np.nan, "err": str(e)[:60]}
            m.update(regime=regime, seed=seed, tf=tf, strategy=nm, family=Zc.family); rows.append(m)
    return rows


def stage(names, charts, seed0, days, lev, fee, workers):
    jobs = [(r, seed0 + k, days, lev, fee, list(names)) for r in REGIMES for k in range(charts)]
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for i, out in enumerate(ex.map(one, jobs, chunksize=1)):
            rows.extend(out)
            if (i + 1) % 10 == 0: print(f"    {i+1}/{len(jobs)} grafik", flush=True)
    return pd.DataFrame(rows)


def summarize(df):
    g = df.groupby(["tf", "strategy", "family"])
    s = g.agg(median_ret=("return_pct", "median"), pct_profitable=("return_pct", lambda x: (x > 0).mean() * 100),
              liq_pct=("liquidated", lambda x: x.mean() * 100), tpd=("trades_per_day", "mean"), win_rate=("win_rate_pct", "mean"),
              median_dd=("max_dd_pct", "median"), gross=("gross_return_pct", "median"), n=("return_pct", "size")).reset_index()
    per = df.pivot_table(index=["tf", "strategy"], columns="regime", values="return_pct", aggfunc="median")
    per.columns = [f"med_{c}" for c in per.columns]
    return s.merge(per.reset_index(), on=["tf", "strategy"])


def passes(r, min_pct): return (r["median_ret"] > 0) and (r["pct_profitable"] >= min_pct) and (r["liq_pct"] < 5) and (r["tpd"] > 0.05)


def md(s, cols):
    o = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in s.iterrows(): o.append("| " + " | ".join(str(r[c]) if isinstance(r[c], str) else f"{r[c]:.1f}" for c in cols) + " |")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", type=int, default=8); ap.add_argument("--val-charts", type=int, default=12)
    ap.add_argument("--days", type=int, default=90); ap.add_argument("--leverage", type=float, default=3.0)
    ap.add_argument("--fee", type=float, default=0.0005); ap.add_argument("--min-pct", type=float, default=55.0)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--out", default="reports/mega")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    names = list(ALL); n_ctrl = sum(1 for n in names if ALL[n].family == "control")
    print(f"{len(names)} strategiya ({n_ctrl} nazorat) x {len(TFS)} TF = {len(names)*len(TFS)} sinov; 1-bosqich {a.charts} grafik/rejim")
    s1 = stage(names, a.charts, 1, a.days, a.leverage, a.fee, a.workers); s1.to_csv(out / "stage1_raw.csv", index=False)
    sum1 = summarize(s1); c1 = sum1[sum1.apply(passes, axis=1, min_pct=a.min_pct)]
    lines = [f"# MEGA sinov: {len(names)} strategiya x 3 TF = {len(names)*3} sinov\n",
             f"- 3x, taker {a.fee*100:.3f}%, funding 0.01%/8h, kuniga max 4 kirish; {a.days} kun; rejimlar {REGIMES}",
             f"- Mezon: median > 0, foydali grafiklar >= {a.min_pct:.0f}%, likvidatsiya < 5%; har bosqich yangi seedlar",
             f"- 1-bosqich: {a.charts} grafik/rejim = {len(s1)} backtest ({time.time()-t0:.0f}s)\n",
             f"## 1-bosqich o'tganlar: {len(c1)} / {len(sum1)}  (shundan nazorat: {(c1.family=='control').sum()} / {n_ctrl*3})\n",
             md(c1.sort_values('median_ret', ascending=False).head(60), ["tf", "strategy", "family", "median_ret", "pct_profitable", "tpd", "win_rate", "med_gbm", "med_regime"])]
    print(lines[-2]); surv = c1
    for rnd, (seed0, k) in enumerate(((50_001, a.val_charts), (90_001, a.val_charts)), start=1):
        if surv.empty: break
        sv = stage(sorted(set(surv.strategy)), k, seed0, a.days, a.leverage, a.fee, a.workers); sv.to_csv(out / f"val{rnd}_raw.csv", index=False)
        sumv = summarize(sv).merge(surv[["tf", "strategy"]], on=["tf", "strategy"])
        ok = sumv[sumv.apply(passes, axis=1, min_pct=a.min_pct)]
        lines += [f"\n## {rnd+1}-bosqich (yangi seedlar {seed0}+, {k} grafik/rejim): {len(ok)} / {len(sumv)} o'tdi (nazorat: {(ok.family=='control').sum()})\n",
                  md(sumv.sort_values('median_ret', ascending=False).head(60), ["tf", "strategy", "family", "median_ret", "pct_profitable", "tpd", "win_rate", "med_gbm", "med_regime", "med_trend_up", "med_trend_down"])]
        print(lines[-2]); surv = ok
    lines.append(f"\n## YAKUN: {len(surv)} sinov 3 bosqichdan ham o'tdi (nazorat: {(surv.family=='control').sum() if len(surv) else 0})\n")
    lines.append(md(surv, ["tf", "strategy", "family", "median_ret", "pct_profitable", "tpd", "win_rate", "med_gbm", "med_regime", "med_trend_up", "med_trend_down"]) if len(surv) else "Hech biri.")
    # oilalar bo'yicha umumiy ko'rinish (1-bosqich)
    fam = sum1.groupby("family").agg(n=("median_ret", "size"), med=("median_ret", "median"), best=("median_ret", "max"), pct_pass=("median_ret", lambda x: 0)).reset_index()
    fam["pct_pass"] = [ (c1.family == f).sum() / max(1, (sum1.family == f).sum()) * 100 for f in fam.family ]
    lines += ["\n## Oilalar bo'yicha (1-bosqich): n sinov, median daromad, eng yaxshi, 1-bosqichdan o'tish %\n", md(fam.sort_values("med", ascending=False), ["family", "n", "med", "best", "pct_pass"])]
    (out / "MEGA_RESULTS.md").write_text("\n".join(lines)); print(f"\n{out/'MEGA_RESULTS.md'} yozildi, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
