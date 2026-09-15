"""Walk-forward parameter search targeting a minimum win rate.

    python -m smc_bot.optimize --csv DOGE=data/doge_1m.csv --csv PEPE=data/pepe_1m.csv \\
        --trials 150 --target-winrate 0.60 --min-trades 30 --out best_config.json

Procedure
---------
1. Split the history into in-sample (first ``1 - oos_fraction``) and
   out-of-sample (the rest).
2. Random-search ``trials`` parameter sets on the in-sample slice.
   A set is *feasible* when ``win_rate >= target`` and ``trades >= min_trades``.
   Among feasible sets the highest expectancy (R per trade) wins; if none is
   feasible the highest win rate with enough trades is reported instead.
3. The top ``keep`` sets are re-evaluated out-of-sample.  Only a set that
   still meets the target out-of-sample is written to ``--out``; anything
   else is over-fitted and is reported as such.

The search space deliberately contains the levers that trade frequency for
quality (displacement size, sweep depth, major-only sweeps, kill-zone hours,
TP1 at 1R with a larger share, tighter setup age).
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from typing import Any

import pandas as pd

from .backtest import format_stats, load_csv, run_backtest
from .config import BotConfig, SessionWindow, load_config

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# search space: (path, choices)
KILL_ZONES = {
    "24/7": [],
    "london+ny": [{"name": "london", "start_hour": 7, "end_hour": 11},
                  {"name": "newyork", "start_hour": 12, "end_hour": 17}],
    "london+ny+asia": [{"name": "asia", "start_hour": 0, "end_hour": 3},
                       {"name": "london", "start_hour": 7, "end_hour": 11},
                       {"name": "newyork", "start_hour": 12, "end_hour": 17}],
}

SPACE: dict[str, list[Any]] = {
    "analysis.displacement_atr_mult": [1.0, 1.25, 1.5, 2.0],
    "analysis.min_sweep_depth_atr": [0.0, 0.1, 0.25, 0.4],
    "analysis.require_major_sweep": [False, True],
    "analysis.require_h1_confirm": [False, True],
    "analysis.allow_ob_fallback": [True, False],
    "analysis.entry_zone_ratio": [0.0, 0.25, 0.5],
    "analysis.sl_atr_buffer": [0.3, 0.5, 0.75],
    "analysis.max_setup_age_candles": [6, 12, 24],
    "analysis.entry_ttl_minutes": [30, 60, 120],
    "analysis.tp1_mode": ["liquidity", "fixed"],
    "analysis.tp1_fixed_rr": [0.8, 1.0, 1.5],
    "analysis.tp1_share": [0.5, 0.6, 0.7],
    "analysis.tp2_fixed_rr": [2.0, 2.5, 3.0],
    "analysis.trail_atr_mult": [0.75, 1.0, 1.5],
    "analysis.trade_windows": list(KILL_ZONES.keys()),
}


def apply_params(cfg: BotConfig, params: dict[str, Any]) -> BotConfig:
    cfg = copy.deepcopy(cfg)
    for path, value in params.items():
        obj = cfg
        *parents, leaf = path.split(".")
        for part in parents:
            obj = getattr(obj, part)
        if leaf == "trade_windows":
            value = [SessionWindow(**w) for w in KILL_ZONES[value]]
        setattr(obj, leaf, value)
    return cfg


def sample(rng: random.Random) -> dict[str, Any]:
    return {k: rng.choice(v) for k, v in SPACE.items()}


def _slice(base: dict[str, pd.DataFrame], start, end) -> dict[str, pd.DataFrame]:
    return {s: df[(df.index >= start) & (df.index < end)] for s, df in base.items()}


def _evaluate(args) -> dict:
    cfg, params, base, warmup = args
    logging.getLogger().setLevel(logging.ERROR)
    res = run_backtest(apply_params(cfg, params), base, warmup_hours=warmup)
    res.pop("equity_curve", None)
    res.pop("trade_list", None)
    return {"params": params, **res}


def feasible(r: dict, target: float, min_trades: int) -> bool:
    return r["win_rate"] >= target and r["trades"] >= min_trades


def rank_key(r: dict, target: float, min_trades: int):
    # feasible first, then expectancy; infeasible ranked by win rate
    return (feasible(r, target, min_trades), r["expectancy_r"] if feasible(r, target, min_trades) else r["win_rate"])


def optimize(cfg: BotConfig, base: dict[str, pd.DataFrame], trials: int, target: float,
             min_trades: int, oos_fraction: float, keep: int, seed: int, workers: int,
             warmup_hours: int = 48) -> dict:
    start = min(df.index[0] for df in base.values())
    end = max(df.index[-1] for df in base.values())
    split = start + (end - start) * (1 - oos_fraction)
    ins, oos = _slice(base, start, split), _slice(base, split - pd.Timedelta(hours=warmup_hours), end)

    rng = random.Random(seed)
    candidates = [sample(rng) for _ in range(trials)]
    jobs = [(cfg, p, ins, warmup_hours) for p in candidates]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_evaluate, jobs))
    else:
        results = [_evaluate(j) for j in jobs]

    results.sort(key=lambda r: rank_key(r, target, min_trades), reverse=True)
    top = results[:keep]
    oos_results = []
    for r in top:
        o = _evaluate((cfg, r["params"], oos, warmup_hours))
        oos_results.append({"in_sample": r, "out_of_sample": o,
                            "robust": feasible(r, target, min_trades) and feasible(o, target, max(5, min_trades // 4))})
    return {"split": split.isoformat(), "in_sample_ranked": results, "validated": oos_results}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--csv", action="append", required=True, help="SYMBOL=path.csv (1m candles)")
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--target-winrate", type=float, default=0.60)
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--oos-fraction", type=float, default=0.3)
    ap.add_argument("--keep", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="best_config.json")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    cfg = load_config(args.config)
    base = {}
    for item in args.csv:
        sym, path = item.split("=", 1)
        base[sym] = load_csv(path)

    report = optimize(cfg, base, args.trials, args.target_winrate, args.min_trades,
                      args.oos_fraction, args.keep, args.seed, args.workers)
    print(f"in-sample/out-of-sample split at {report['split']}")
    robust = [v for v in report["validated"] if v["robust"]]
    for v in report["validated"]:
        flag = "ROBUST" if v["robust"] else "overfit/insufficient"
        print(f"\n[{flag}] {json.dumps(v['in_sample']['params'])}")
        print("  IS :", format_stats(v["in_sample"]))
        print("  OOS:", format_stats(v["out_of_sample"]))
    if robust:
        best = robust[0]["in_sample"]["params"]
        out_cfg = asdict(apply_params(cfg, best))
        out_cfg["exchange"].pop("api_key", None); out_cfg["exchange"].pop("api_secret", None)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out_cfg, fh, indent=2)
        print(f"\nbest robust config written to {args.out}")
    else:
        print(f"\nno parameter set reached win_rate >= {args.target_winrate:.0%} out-of-sample "
              f"with >= {args.min_trades} trades; do not deploy, collect more data or relax the target")


if __name__ == "__main__":
    main()
