"""Neytral grid-bot simulyatori (futures, yonbosh bozor uchun).

Model:
  - Har `recenter_bars` shamda (yoki SL dan keyin) diapazon = oxirgi `lookback` shamning [min, max] (ATR bilan kengaytirilgan).
  - `levels` ta teng daraja. Markazdan pastdagi darajalarda BUY limit, yuqoridagilarda SELL limit.
  - Buy to'lsa -> bir daraja yuqorida SELL (TP) qo'yiladi; sell to'lsa -> bir daraja pastda BUY (TP).
    Har juft = bitta grid savdosi, foyda = daraja oralig'i - komissiya (maker 0.02% x 2).
  - Har darajaga notional = equity * leverage / levels.
  - SL: narx diapazondan `sl_buffer_atr` ATR tashqariga chiqsa -> barcha pozitsiyalar taker bilan yopiladi, grid to'xtaydi
    va keyingi recenter gacha kutadi.
  - Funding: netto pozitsiyaga 8 soatda bir.
Sham ichidagi yo'l: open -> (low, high yoki high, low; yopilish yo'nalishiga qarab) -> close.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import indicators as ind


@dataclass
class GridConfig:
    initial_equity: float = 1000.0
    leverage: float = 3.0
    levels: int = 10
    lookback: int = 96          # 1 kun
    recenter_bars: int = 96
    sl_buffer_atr: float = 1.0
    maker_fee: float = 0.0002
    taker_fee: float = 0.0005
    slippage: float = 0.0002
    funding_rate_8h: float = 0.0001
    sl_enabled: bool = True
    min_spacing_pct: float = 0.002   # daraja oralig'i >= 0.2% (komissiya 2x0.02% dan ancha katta bo'lsin)


@dataclass
class GridResult:
    equity_curve: pd.Series
    grid_trades: int
    grid_wins: int
    sl_events: int
    fees_paid: float
    liquidated: bool

    def metrics(self, days):
        eq = self.equity_curve; start, end = eq.iloc[0], eq.iloc[-1]
        dd = (eq / eq.cummax() - 1).min()
        daily = eq.resample("1D").last().dropna().pct_change().dropna()
        sharpe = float(daily.mean() / daily.std() * np.sqrt(365)) if len(daily) > 2 and daily.std() > 0 else 0.0
        return {"return_pct": (end / start - 1) * 100, "max_dd_pct": dd * 100, "sharpe": sharpe,
                "trades": self.grid_trades, "trades_per_day": self.grid_trades / days,
                "win_rate_pct": self.grid_wins / self.grid_trades * 100 if self.grid_trades else 0.0,
                "sl_events": self.sl_events, "fees_pct": self.fees_paid / start * 100,
                "gross_return_pct": (end / start - 1 + self.fees_paid / start) * 100,
                "liquidated": float(self.liquidated), "long_share_pct": 50.0, "profit_factor": 0.0}


def run_grid(df: pd.DataFrame, cfg: GridConfig | None = None) -> GridResult:
    cfg = cfg or GridConfig()
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    atr = ind.atr(df, 14).values
    n = len(df); times = df.index
    hour, minute = times.hour.values, times.minute.values
    funding_bar = ((hour % 8) == 0) & (minute == 0)

    equity = cfg.initial_equity
    eq = np.empty(n)
    grid_trades = grid_wins = sl_events = 0
    fees = 0.0
    active = False
    levels = np.array([])
    orders: dict[int, list] = {}      # daraja -> [(side, origin)], origin=None: kirish; origin=k0: k0 dagi pozitsiya TP'si
    inv: dict[int, tuple] = {}        # daraja -> (signed_qty, entry_px)
    lo_b = hi_b = np.nan; last_center = -10 ** 9
    liquidated = False

    def place(k, side, origin):
        orders.setdefault(k, []).append((side, origin))

    def setup(i):
        nonlocal active, levels, orders, inv, lo_b, hi_b, last_center
        if i < cfg.lookback:
            return
        lo = np.nanmin(l[i - cfg.lookback:i + 1]); hi = np.nanmax(h[i - cfg.lookback:i + 1])
        if np.isnan(atr[i]) or hi <= lo or (hi - lo) / cfg.levels / c[i] < cfg.min_spacing_pct:
            return
        levels = np.linspace(lo, hi, cfg.levels + 1)
        orders = {}; inv = {}
        mid = c[i]
        for k, p in enumerate(levels):
            if p < mid: place(k, +1, None)
            elif p > mid: place(k, -1, None)
        lo_b, hi_b = lo - cfg.sl_buffer_atr * atr[i], hi + cfg.sl_buffer_atr * atr[i]
        active = True; last_center = i

    def fill(k, side, origin, px):
        nonlocal equity, fees, grid_trades, grid_wins
        notional = equity * cfg.leverage / cfg.levels
        q = notional / px
        fee = notional * cfg.maker_fee; equity -= fee; fees += fee
        if origin is None:                                   # yangi grid pozitsiyasi
            if k in inv:
                q0, ep = inv[k]; inv[k] = (q0 + side * q, (abs(q0) * ep + q * px) / (abs(q0) + q))
            else:
                inv[k] = (side * q, px)
            tp_k = k + 1 if side > 0 else k - 1
            if 0 <= tp_k < len(levels):
                place(tp_k, -side, k)
        else:                                                # TP: origin dagi pozitsiyani yopish
            if origin not in inv:
                return
            q0, ep = inv.pop(origin)
            pnl = (px - ep) * abs(q0) * np.sign(q0)
            equity += pnl; grid_trades += 1; grid_wins += int(pnl - 2 * fee > 0)
            place(origin, int(np.sign(q0)), None)            # kirish buyurtmasi qayta qo'yiladi

    def process(target):
        for _ in range(4 * cfg.levels):
            changed = False
            for k in list(orders.keys()):
                for od in list(orders.get(k, [])):
                    side, origin = od; p = levels[k]
                    if (side > 0 and target <= p) or (side < 0 and target >= p):
                        orders[k].remove(od)
                        if not orders[k]: del orders[k]
                        fill(k, side, origin, p); changed = True
            if not changed:
                break

    def close_all(px, reason):
        nonlocal equity, fees, sl_events, active, inv, orders
        for k, (q, ep) in list(inv.items()):
            side = np.sign(q); p = px * (1 - cfg.slippage * side)
            fee = abs(q) * p * cfg.taker_fee; fees += fee
            equity += (p - ep) * abs(q) * side - fee
        inv = {}; orders = {}; active = False
        if reason == "SL": sl_events += 1

    def unrealized(px):
        return sum((px - ep) * abs(q) * np.sign(q) for q, ep in inv.values())

    for i in range(n):
        if liquidated:
            eq[i] = 0.0; continue
        if not active and i - last_center >= cfg.recenter_bars:
            setup(i)
        elif active and i - last_center >= cfg.recenter_bars and not inv:
            setup(i)
        elif active and i - last_center >= 3 * cfg.recenter_bars:
            close_all(c[i], "RECENTER"); setup(i)
        if active and i > last_center:
            path = (l[i], h[i]) if c[i] >= o[i] else (h[i], l[i])
            for target in (o[i],) + path + (c[i],):
                process(target)
            if funding_bar[i]:
                np_ = sum(q for q, _ in inv.values())
                equity -= abs(np_) * c[i] * cfg.funding_rate_8h * np.sign(np_)
            if cfg.sl_enabled and (l[i] <= lo_b or h[i] >= hi_b):
                close_all(lo_b if l[i] <= lo_b else hi_b, "SL")
                last_center = i
            if equity + unrealized(c[i]) <= 0:
                liquidated = True; equity = 0.0; eq[i] = 0.0; continue
        eq[i] = max(equity + unrealized(c[i]), 0.0)
    if inv:
        close_all(c[n - 1], "END"); eq[n - 1] = equity
    return GridResult(pd.Series(eq, index=times), grid_trades, grid_wins, sl_events, fees, liquidated)
