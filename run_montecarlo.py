#!/usr/bin/env python3
"""Sintetik grafiklarda takroriy Monte-Carlo sinovi. Natija: reports/results.md, reports/results.json"""
import argparse, json, time
from pathlib import Path

import numpy as np
import pandas as pd

from halalbot import montecarlo as mc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", type=int, default=60, help="har rejim uchun grafiklar soni (har partiyada)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--batches", type=int, default=3, help="mustaqil takrorlar soni (turli seedlar)")
    ap.add_argument("--max-trades-per-day", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(exist_ok=True)
    all_batches = []
    t0 = time.time()
    for b in range(a.batches):
        seed0 = 10_000 * (b + 1)
        df = mc.run_batch(a.charts, a.days, seed0, max_tpd=a.max_trades_per_day, workers=a.workers)
        df["batch"] = b
        all_batches.append(df)
        print(f"partiya {b+1}/{a.batches} tayyor ({time.time()-t0:.0f}s), {len(df)} backtest")
    full = pd.concat(all_batches, ignore_index=True)
    full.to_csv(out / "raw_results.csv", index=False)

    summary = mc.summarize(full)
    summary.to_json(out / "results.json", orient="records", indent=1)

    # partiyalar orasidagi barqarorlik: median daromad har partiyada
    stab = (full.groupby(["fee", "regime", "strategy", "batch"])["return_pct"].median()
            .unstack("batch"))
    stab["spread"] = stab.max(axis=1) - stab.min(axis=1)

    lines = [f"# Monte-Carlo natijalari\n",
             f"- Grafiklar: {a.charts} x {len(mc.REGIMES)} rejim x {a.batches} partiya = {a.charts*len(mc.REGIMES)*a.batches} sintetik grafik, har biri {a.days} kun (15m)",
             f"- Backtestlar soni: {len(full)}",
             f"- Kuniga maksimal savdo: {a.max_trades_per_day}; spot, long-only, leverage yo'q",
             f"- Ustunlar: daromad % ({a.days} kun), p05/p95 = 5%/95% kvantil, pct_profitable = foydali grafiklar ulushi,",
             "  median_gross = komissiyasiz daromad (sof 'edge'), trades_per_day, median_excess_vs_bh = buy&hold ga nisbatan\n",
             "## Xulosa jadvallari", mc.to_markdown(summary),
             "\n## Partiyalar orasidagi barqarorlik (median daromad har partiyada, fee 0.10%)\n"]
    st = stab.loc["fee_0.10%"].reset_index()
    cols = ["regime", "strategy"] + [c for c in st.columns if isinstance(c, (int, np.integer))] + ["spread"]
    lines.append("| " + " | ".join(str(c) for c in cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in st.iterrows():
        lines.append("| " + " | ".join(str(r[c]) if isinstance(r[c], str) else f"{r[c]:.1f}" for c in cols) + " |")
    (out / "results.md").write_text("\n".join(lines))
    print(f"\n{out/'results.md'} yozildi. Jami {time.time()-t0:.0f}s")
    print(summary[summary.fee == "fee_0.10%"].pivot(index="strategy", columns="regime", values="median_ret").round(1))


if __name__ == "__main__":
    main()
