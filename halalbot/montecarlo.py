"""Monte-Carlo: ko'p sintetik grafik x strategiya x komissiya ssenariysi.

"Qayta-qayta tekshirish": natijalar bir nechta mustaqil partiya (batch) da
turli seedlar bilan takrorlanadi va partiyalar orasidagi farq ko'rsatiladi.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict

import numpy as np
import pandas as pd

from . import synthetic
from .backtest import BacktestConfig, run
from .strategies import ALL_STRATEGIES

REGIMES = ["gbm", "garch", "regime", "trend_up", "trend_down"]
FEE_SCENARIOS = {"fee_0.10%": 0.001, "fee_0.075%_BNB": 0.00075, "fee_0%_nazariy": 0.0}


def _one_chart(args):
    regime, seed, days, fee_scenarios, max_tpd = args
    df = synthetic.generate(regime, days=days, seed=seed)
    bh = df["close"].iloc[-1] / df["close"].iloc[0] - 1
    rows = []
    for fee_name, fee in fee_scenarios.items():
        cfg = BacktestConfig(fee_rate=fee, max_trades_per_day=max_tpd)
        for S in ALL_STRATEGIES:
            m = run(df, S(), cfg).metrics(days)
            m.update(regime=regime, seed=seed, fee=fee_name, strategy=S.name,
                     bh_return_pct=bh * 100, excess_vs_bh_pct=m["return_pct"] - bh * 100)
            rows.append(m)
    return rows


def run_batch(n_charts: int, days: int, seed0: int, regimes=REGIMES, fee_scenarios=FEE_SCENARIOS,
              max_tpd: int = 4, workers: int = 4) -> pd.DataFrame:
    jobs = [(r, seed0 + k, days, fee_scenarios, max_tpd) for r in regimes for k in range(n_charts)]
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for out in ex.map(_one_chart, jobs, chunksize=4):
            rows.extend(out)
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["fee", "regime", "strategy"])
    s = g.agg(
        median_ret=("return_pct", "median"),
        mean_ret=("return_pct", "mean"),
        p05_ret=("return_pct", lambda x: x.quantile(0.05)),
        p95_ret=("return_pct", lambda x: x.quantile(0.95)),
        pct_profitable=("return_pct", lambda x: (x > 0).mean() * 100),
        median_gross=("gross_return_pct", "median"),
        median_dd=("max_dd_pct", "median"),
        worst_dd=("max_dd_pct", "min"),
        trades_per_day=("trades_per_day", "mean"),
        win_rate=("win_rate_pct", "mean"),
        median_excess_vs_bh=("excess_vs_bh_pct", "median"),
        n=("return_pct", "size"),
    ).reset_index()
    return s


def to_markdown(s: pd.DataFrame) -> str:
    cols = ["strategy", "median_ret", "p05_ret", "p95_ret", "pct_profitable", "median_gross",
            "median_dd", "worst_dd", "trades_per_day", "win_rate", "median_excess_vs_bh"]
    out = []
    for (fee, regime), grp in s.groupby(["fee", "regime"], sort=True):
        out.append(f"\n#### {fee} | rejim: {regime} (n={int(grp['n'].iloc[0])} grafik)\n")
        out.append("| " + " | ".join(cols) + " |")
        out.append("|" + "---|" * len(cols))
        for _, r in grp.sort_values("strategy").iterrows():
            vals = [r["strategy"]] + [f"{r[c]:.1f}" for c in cols[1:]]
            out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)
