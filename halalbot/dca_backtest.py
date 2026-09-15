"""3commas uslubidagi DCA / martingale bot (long yoki short), "yuqori winrate" botlarining eng mashhuri.

Bazaviy buyurtma -> narx `so_step`% qarshi yursa xavfsizlik buyurtmasi (hajm x `vol_scale`), maksimal `max_so` ta.
TP = o'rtacha narxdan `tp_pct`%. SL ixtiyoriy (`sl_pct`, 0 = yo'q). Har sikl = 1 "savdo".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class DcaConfig:
    initial_equity: float = 1000.0
    leverage: float = 3.0
    side: int = 1                # +1 long, -1 short
    base_frac: float = 0.10      # bazaviy buyurtma = kapital x leverage x base_frac
    so_step_pct: float = 1.0
    step_scale: float = 1.5      # har keyingi SO masofasi x
    vol_scale: float = 2.0
    max_so: int = 5
    tp_pct: float = 1.0
    sl_pct: float = 0.0
    taker_fee: float = 0.0005
    funding_rate_8h: float = 0.0001


def run_dca(df: pd.DataFrame, cfg: DcaConfig | None = None):
    from .grid_backtest import GridResult
    cfg = cfg or DcaConfig()
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    n = len(df); times = df.index; hour, minute = times.hour.values, times.minute.values
    fb = ((hour % 8) == 0) & (minute == 0)
    equity = cfg.initial_equity; eq = np.empty(n); trades = wins = sl_events = 0; fees = 0.0
    s = cfg.side; qty = 0.0; cost = 0.0; n_so = 0; next_so_px = np.nan; avg = np.nan; liquidated = False
    def buy(px, notional):
        nonlocal qty, cost, fees, equity
        q = notional / px; fee = notional * cfg.taker_fee; fees += fee; equity -= fee; qty += q; cost += q * px
    for i in range(n):
        if liquidated: eq[i] = 0.0; continue
        if qty == 0:
            base = equity * cfg.leverage * cfg.base_frac
            if base < 5: liquidated = True; eq[i] = equity; continue
            buy(o[i], base); avg = cost / qty; n_so = 0; step = cfg.so_step_pct
            next_so_px = avg * (1 - s * step / 100); so_notional = base * cfg.vol_scale
        # xavfsizlik buyurtmalari (sham ichida)
        while n_so < cfg.max_so and ((s > 0 and l[i] <= next_so_px) or (s < 0 and h[i] >= next_so_px)):
            if so_notional > equity * cfg.leverage - qty * avg: break     # margin yetmadi
            buy(next_so_px, so_notional); n_so += 1; avg = cost / qty; so_notional *= cfg.vol_scale
            step = cfg.so_step_pct * (cfg.step_scale ** n_so)
            next_so_px = next_so_px * (1 - s * step / 100)
        tp_px = avg * (1 + s * cfg.tp_pct / 100)
        sl_px = avg * (1 - s * cfg.sl_pct / 100) if cfg.sl_pct > 0 else np.nan
        hit_tp = (h[i] >= tp_px) if s > 0 else (l[i] <= tp_px)
        hit_sl = (not np.isnan(sl_px)) and ((l[i] <= sl_px) if s > 0 else (h[i] >= sl_px))
        if hit_sl or hit_tp:
            px = sl_px if hit_sl else tp_px
            fee = qty * px * cfg.taker_fee; fees += fee
            pnl = (px - avg) * qty * s - fee; equity += pnl; trades += 1; wins += int(pnl > 0); sl_events += int(hit_sl)
            qty = cost = 0.0
        if fb[i] and qty: equity -= qty * c[i] * cfg.funding_rate_8h * s
        unreal = (c[i] - avg) * qty * s if qty else 0.0
        if equity + unreal <= 0: liquidated = True; equity = 0.0; eq[i] = 0.0; continue
        eq[i] = equity + unreal
    if qty and not liquidated:
        pnl = (c[-1] - avg) * qty * s; equity += pnl; trades += 1; wins += int(pnl > 0); eq[-1] = equity
    return GridResult(pd.Series(eq, index=times), trades, wins, sl_events, fees, liquidated)
