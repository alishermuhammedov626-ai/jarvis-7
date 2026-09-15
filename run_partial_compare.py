#!/usr/bin/env python3
"""4) 'Qisman TP + breakeven' da'vosini tekshirish: har strategiya bir xil grafiklarda oddiy va partial rejimda."""
import time
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
from halalbot import synthetic
from halalbot.futures_backtest import FuturesConfig
from halalbot.strategy_zoo import ZOO, run_any

REGIMES = ["gbm", "garch", "regime", "trend_up", "trend_down"]

def one(args):
    regime, seed, days = args
    df = synthetic.generate(regime, days=days, seed=seed); rows = []
    for Zc in ZOO:
        if getattr(Zc, "is_grid", False): continue
        for mode, pr in (("oddiy", 0.0), ("partial_1R_60%_BE", 1.0)):
            m = run_any(df, Zc, FuturesConfig(leverage=3, taker_fee=0.0005, partial_tp_r=pr, partial_frac=0.6)).metrics(days)
            m.update(regime=regime, seed=seed, strategy=Zc.name, mode=mode); rows.append(m)
    return rows

if __name__ == "__main__":
    t = time.time(); rows = []
    with ProcessPoolExecutor(4) as ex:
        for out in ex.map(one, [(r, 300 + k, 90) for r in REGIMES for k in range(20)], chunksize=2): rows.extend(out)
    df = pd.DataFrame(rows)
    g = df.groupby(["strategy", "mode"]).agg(median_ret=("return_pct", "median"), win_rate=("win_rate_pct", "mean"),
                                             pct_prof=("return_pct", lambda x: (x > 0).mean() * 100), dd=("max_dd_pct", "median")).unstack("mode")
    g.columns = [f"{a}__{b}" for a, b in g.columns]
    g["win_rate_delta"] = g["win_rate__partial_1R_60%_BE"] - g["win_rate__oddiy"]
    g["ret_delta"] = g["median_ret__partial_1R_60%_BE"] - g["median_ret__oddiy"]
    g = g.sort_values("ret_delta", ascending=False).round(1)
    cols = ["win_rate__oddiy", "win_rate__partial_1R_60%_BE", "win_rate_delta", "median_ret__oddiy", "median_ret__partial_1R_60%_BE", "ret_delta", "pct_prof__oddiy", "pct_prof__partial_1R_60%_BE"]
    txt = [f"Qisman TP (1R da 60%) + breakeven vs oddiy — {len(df)} backtest, 100 grafik, 3x, 0.05%  ({time.time()-t:.0f}s)\n",
           g[cols].to_string(), "\n\nO'RTACHA (barcha strategiyalar):",
           f"win rate: {g['win_rate__oddiy'].mean():.1f}% -> {g['win_rate__partial_1R_60%_BE'].mean():.1f}%",
           f"median daromad: {g['median_ret__oddiy'].mean():.1f}% -> {g['median_ret__partial_1R_60%_BE'].mean():.1f}%",
           f"daromadi yaxshilangan strategiyalar: {(g['ret_delta'] > 0).sum()}/{len(g)}; foydaga chiqqanlar: {(g['median_ret__partial_1R_60%_BE'] > 0).sum()}/{len(g)}"]
    open("reports/partial_tp_compare.txt", "w").write("\n".join(txt)); print("\n".join(txt[-5:]))
