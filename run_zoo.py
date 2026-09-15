#!/usr/bin/env python3
"""Strategiyalar kutubxonasini ikki bosqichda sintetik grafiklarda sinash (futures rejimi).

1-bosqich (qidiruv):   barcha strategiyalar x barcha rejimlar x N grafik (seed to'plami A).
2-bosqich (tasdiqlash): 1-bosqichdan o'tganlar butunlay yangi grafiklarda (seed to'plami B, C).
"Topilgan" deb faqat B va C da ham mezonlarni qanoatlantirgan strategiya hisoblanadi.
Bu ko'p-marta-sinash (multiple testing) tuzog'idan himoya: 86 ta sinovdan tasodifan ham bir nechtasi
1-bosqichda 'yaxshi' ko'rinadi.
"""
import argparse, os, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from halalbot import synthetic
from halalbot.futures_backtest import FuturesConfig, run_futures
from halalbot.strategy_zoo import ZOO, run_any

REGIMES = ["gbm", "garch", "regime", "trend_up", "trend_down"]
TFS = ["15m", "1h"]


def resample(df, tf):
    if tf == "15m": return df
    return df.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


_REAL: dict = {}   # csv rejimida oynalar (har jarayon o'zi yuklaydi)


PARTIAL = {"r": 0.0, "frac": 0.6}


def one(args):
    regime, seed, days, lev, fee, names = args
    pr = float(os.environ.get("ZOO_PARTIAL_R", "0")); pf = float(os.environ.get("ZOO_PARTIAL_FRAC", "0.6"))
    if regime == "real":
        base = _real_window(seed)
        days = (base.index[-1] - base.index[0]).total_seconds() / 86400
    else:
        base = synthetic.generate(regime, days=days, seed=seed)
    rows = []
    for tf in TFS:
        df = resample(base, tf)
        for Zc in ZOO:
            if names and Zc.name not in names: continue
            try:
                m = run_any(df, Zc, FuturesConfig(leverage=lev, taker_fee=fee, partial_tp_r=pr, partial_frac=pf)).metrics(days)
            except Exception as e:  # bitta strategiya xatosi butun partiyani to'xtatmasin
                m = {"return_pct": np.nan, "error": str(e)[:80]}
            m.update(regime=regime, seed=seed, tf=tf, strategy=Zc.name, family=Zc.family); rows.append(m)
    return rows


def _real_window(k):
    if "windows" not in _REAL:
        from halalbot.tv_csv import load_ohlc, split_windows, to_15m
        _REAL["windows"] = split_windows(to_15m(load_ohlc(_REAL["path"])), _REAL["window_days"])
    return _REAL["windows"][k]


def run_stage(charts, seed0, days, lev, fee, names=None, workers=4, regimes=None):
    regimes = regimes or REGIMES
    jobs = [(r, seed0 + k, days, lev, fee, names) for r in regimes for k in range(charts)]
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for out in ex.map(one, jobs, chunksize=2): rows.extend(out)
    return pd.DataFrame(rows)


def summarize(df):
    g = df.groupby(["tf", "strategy", "family"])
    s = g.agg(median_ret=("return_pct", "median"), pct_profitable=("return_pct", lambda x: (x > 0).mean() * 100),
              p05=("return_pct", lambda x: x.quantile(.05)), p95=("return_pct", lambda x: x.quantile(.95)),
              median_gross=("gross_return_pct", "median"), median_dd=("max_dd_pct", "median"),
              liq_pct=("liquidated", lambda x: x.mean() * 100), tpd=("trades_per_day", "mean"),
              win_rate=("win_rate_pct", "mean"), sharpe=("sharpe", "median"), n=("return_pct", "size")).reset_index()
    # rejim bo'yicha median
    per = df.pivot_table(index=["tf", "strategy"], columns="regime", values="return_pct", aggfunc="median")
    per.columns = [f"med_{c}" for c in per.columns]
    return s.merge(per.reset_index(), on=["tf", "strategy"]).sort_values("median_ret", ascending=False)


def passes(row, min_pct=55.0):
    return (row["median_ret"] > 0) and (row["pct_profitable"] >= min_pct) and (row["liq_pct"] < 5)


def md_table(s, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in s.iterrows():
        out.append("| " + " | ".join(str(r[c]) if isinstance(r[c], str) else f"{r[c]:.1f}" for c in cols) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", type=int, default=30, help="har rejim uchun grafiklar (1-bosqich)")
    ap.add_argument("--val-charts", type=int, default=40, help="har rejim uchun grafiklar (2-bosqich, har raund)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--leverage", type=float, default=3.0)
    ap.add_argument("--fee", type=float, default=0.0005)
    ap.add_argument("--min-pct", type=float, default=55.0)
    ap.add_argument("--out", default="reports")
    ap.add_argument("--family", default=None, help="faqat shu oila (masalan highwr)")
    ap.add_argument("--partial", type=float, default=0.0, help=">0: qisman TP shu R da (60%% yopiladi) + breakeven")
    ap.add_argument("--csv", default=None, help="TradingView eksport / Binance klines CSV: REAL ma'lumotda walk-forward")
    ap.add_argument("--window-days", type=int, default=30, help="csv rejimida har 'grafik' uzunligi")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(exist_ok=True); t0 = time.time()
    os.environ["ZOO_PARTIAL_R"] = str(a.partial)
    if a.family:
        ZOO[:] = [z for z in ZOO if z.family in (a.family, "control")]
    if a.csv:
        return main_csv(a, out, t0)

    print(f"1-bosqich: {len(ZOO)} strategiya x {len(TFS)} TF x {len(REGIMES)} rejim x {a.charts} grafik ...")
    s1 = run_stage(a.charts, 1, a.days, a.leverage, a.fee)
    s1.to_csv(out / "zoo_stage1_raw.csv", index=False)
    sum1 = summarize(s1)
    cand = sum1[sum1.apply(passes, axis=1, min_pct=a.min_pct)]
    print(f"  {time.time()-t0:.0f}s, {len(s1)} backtest; nomzodlar: {len(cand)}")
    ctrl = sum1[sum1.strategy == "control_random_entry"]

    lines = [f"# Strategiyalar kutubxonasi — sintetik futures sinovi\n",
             f"- Rejim: Binance USD-M perpetual modeli, leverage {a.leverage}x, taker {a.fee*100:.3f}%, slippage 0.02%, funding 0.01%/8h, kuniga max 4 kirish",
             f"- {len(ZOO)} strategiya x {len(TFS)} timeframe = {len(ZOO)*len(TFS)} sinov; 1-bosqich {a.charts} grafik/rejim x 5 rejim, {a.days} kun; jami {len(s1)} backtest",
             f"- O'tish mezoni: median daromad > 0, foydali grafiklar >= {a.min_pct:.0f}%, likvidatsiya < 5%\n",
             "## 1-bosqich: barcha strategiyalar (median daromad bo'yicha)\n",
             md_table(sum1, ["tf", "strategy", "family", "median_ret", "pct_profitable", "p05", "p95", "median_gross", "median_dd", "liq_pct", "tpd", "win_rate", "med_gbm", "med_regime", "med_trend_up", "med_trend_down"]),
             "\n## Nazorat (tasodifiy kirish)\n", md_table(ctrl, ["tf", "median_ret", "pct_profitable", "median_gross", "tpd"]),
             f"\n## 1-bosqich nomzodlari: {len(cand)}\n"]
    if len(cand):
        lines.append(md_table(cand, ["tf", "strategy", "median_ret", "pct_profitable", "tpd", "med_gbm", "med_regime"]))

    survivors = cand
    for rnd, seed0 in enumerate((50_001, 90_001), start=1):
        if survivors.empty: break
        names = set(survivors.strategy)
        sv = run_stage(a.val_charts, seed0, a.days, a.leverage, a.fee, names=names)
        sv.to_csv(out / f"zoo_val{rnd}_raw.csv", index=False)
        sumv = summarize(sv)
        keep = sumv.merge(survivors[["tf", "strategy"]], on=["tf", "strategy"])
        ok = keep[keep.apply(passes, axis=1, min_pct=a.min_pct)]
        lines.append(f"\n## 2-bosqich, {rnd}-raund (yangi seedlar {seed0}+, {a.val_charts} grafik/rejim): {len(ok)}/{len(keep)} o'tdi\n")
        lines.append(md_table(keep, ["tf", "strategy", "median_ret", "pct_profitable", "p05", "p95", "tpd", "med_gbm", "med_regime", "med_trend_up", "med_trend_down"]))
        survivors = ok
        print(f"  tasdiqlash {rnd}: {len(ok)}/{len(keep)} o'tdi ({time.time()-t0:.0f}s)")

    lines.append(f"\n## YAKUN: {len(survivors)} strategiya barcha bosqichlardan o'tdi\n")
    if len(survivors):
        lines.append(md_table(survivors, ["tf", "strategy", "median_ret", "pct_profitable", "tpd"]))
    else:
        lines.append("Hech biri. Sintetik grafiklarda birorta strategiya tasodifdan ishonchli farq qilmadi.")
    (out / "zoo_results.md").write_text("\n".join(lines))
    print(f"\n{out/'zoo_results.md'} yozildi, {time.time()-t0:.0f}s")
    print(sum1.head(15)[["tf", "strategy", "median_ret", "pct_profitable", "tpd", "med_gbm"]].to_string(index=False))


def main_csv(a, out, t0):
    """Real ma'lumot: oynalar vaqt bo'yicha 60% / 20% / 20% ga bo'linadi (walk-forward)."""
    from halalbot.tv_csv import load_ohlc, split_windows, to_15m
    import os
    _REAL.update(path=a.csv, window_days=a.window_days)
    os.environ["HALALBOT_CSV"] = a.csv
    wins = split_windows(to_15m(load_ohlc(a.csv)), a.window_days)
    n = len(wins)
    if n < 5:
        raise SystemExit(f"Kamida 5 ta {a.window_days}-kunlik oyna kerak, topildi {n} (ko'proq tarix eksport qiling)")
    n1 = max(3, int(n * 0.6)); n2 = max(1, int(n * 0.2)); n3 = n - n1 - n2
    print(f"Real ma'lumot: {n} oyna x {a.window_days} kun ({wins[0].index[0].date()} .. {wins[-1].index[-1].date()}); "
          f"qidiruv {n1}, tasdiqlash {n2} + {n3}")

    def stage(k0, k, names=None):
        df = run_stage(k, k0, a.window_days, a.leverage, a.fee, names=names, regimes=["real"])
        return df

    s1 = stage(0, n1); s1.to_csv(out / "real_stage1_raw.csv", index=False)
    sum1 = summarize(s1); cand = sum1[sum1.apply(passes, axis=1, min_pct=a.min_pct)]
    lines = [f"# REAL ma'lumot ({a.csv}) — walk-forward sinov\n",
             f"- {n} oyna x {a.window_days} kun; qidiruv: birinchi {n1} oyna, tasdiqlash: keyingi {n2}, so'ng oxirgi {n3}",
             f"- leverage {a.leverage}x, taker {a.fee*100:.3f}%, kuniga max 4 kirish\n",
             "## 1-bosqich (in-sample)\n",
             md_table(sum1, ["tf", "strategy", "family", "median_ret", "pct_profitable", "p05", "p95", "median_gross", "median_dd", "liq_pct", "tpd", "win_rate"]),
             f"\n## Nomzodlar: {len(cand)}\n"]
    survivors = cand
    for rnd, (k0, k) in enumerate(((n1, n2), (n1 + n2, n3)), start=1):
        if survivors.empty or k <= 0: break
        sv = stage(k0, k, names=set(survivors.strategy)); sumv = summarize(sv)
        keep = sumv.merge(survivors[["tf", "strategy"]], on=["tf", "strategy"])
        ok = keep[keep.apply(passes, axis=1, min_pct=a.min_pct)]
        lines += [f"\n## 2-bosqich {rnd}-raund (out-of-sample, {k} oyna): {len(ok)}/{len(keep)} o'tdi\n",
                  md_table(keep, ["tf", "strategy", "median_ret", "pct_profitable", "p05", "p95", "tpd", "median_dd"])]
        survivors = ok
    lines.append(f"\n## YAKUN: {len(survivors)} strategiya barcha bosqichlardan o'tdi\n")
    lines.append(md_table(survivors, ["tf", "strategy", "median_ret", "pct_profitable", "tpd"]) if len(survivors) else "Hech biri.")
    if "control_random_entry" in set(survivors.strategy):
        lines.append("\n**OGOHLANTIRISH:** tasodifiy kirish nazorati ham barcha bosqichlardan o'tdi. Demak bu ma'lumot hajmi "
                     "(oynalar soni) natijani tasodifdan ajratish uchun yetarli emas. Kamida 2-3 yil tarix eksport qiling.")
    if n < 24:
        lines.append(f"\n**Eslatma:** {n} oyna kam. Ishonchli xulosa uchun 24+ oyna (2+ yil 15m tarix) tavsiya etiladi.")
    (out / "real_results.md").write_text("\n".join(lines))
    print(f"{out/'real_results.md'} yozildi, {time.time()-t0:.0f}s")
    print(sum1.head(15)[["tf", "strategy", "median_ret", "pct_profitable", "tpd"]].to_string(index=False))


if __name__ == "__main__":
    main()
