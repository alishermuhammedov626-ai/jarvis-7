"""Spot, long-only backtest dvigateli.

Qoidalar (halol cheklovlari dvigatelning o'ziga o'rnatilgan):
  - Faqat bitta ochiq pozitsiya; pozitsiya hajmi hech qachon kapitaldan oshmaydi (leverage yo'q).
  - Short yo'q: pozitsiya faqat BUY bilan ochiladi, SELL bilan yopiladi.
  - Kuniga maksimal `max_trades_per_day` ta kirish.
  - Kirish keyingi sham ochilishida (look-ahead yo'q). SL/TP sham ichida high/low bilan tekshiriladi;
    ikkalasi ham bir shamda tegsa, konservativ tarzda SL hisoblanadi.
  - Komissiya har tomonda (`fee_rate`), slippage har tomonda (`slippage`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import day_index
from .strategies import Signals, Strategy


@dataclass
class BacktestConfig:
    initial_equity: float = 1000.0
    fee_rate: float = 0.001          # Binance spot taker 0.10%
    slippage: float = 0.0002         # 0.02% har tomonda
    risk_per_trade: float = 0.01     # kapitalning 1% i SL masofasida xavf
    max_position_frac: float = 1.0   # maksimal 100% kapital (leverage yo'q)
    max_trades_per_day: int = 4
    min_trade_notional: float = 10.0  # Binance minNotional ~ 10 USDT


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    fees: float
    reason: str


@dataclass
class Result:
    strategy: str
    equity_curve: pd.Series
    trades: list = field(default_factory=list)
    fees_paid: float = 0.0

    def metrics(self, days: float) -> dict:
        eq = self.equity_curve
        start, end = eq.iloc[0], eq.iloc[-1]
        ret = end / start - 1
        dd = (eq / eq.cummax() - 1).min()
        daily = eq.resample("1D").last().dropna().pct_change().dropna()
        sharpe = float(daily.mean() / daily.std() * np.sqrt(365)) if len(daily) > 2 and daily.std() > 0 else 0.0
        pnls = np.array([t.pnl for t in self.trades])
        wins = pnls[pnls > 0]
        losses = pnls[pnls <= 0]
        pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else (np.inf if len(wins) else 0.0)
        return {
            "return_pct": ret * 100,
            "max_dd_pct": dd * 100,
            "sharpe": sharpe,
            "trades": len(self.trades),
            "trades_per_day": len(self.trades) / days,
            "win_rate_pct": (len(wins) / len(pnls) * 100) if len(pnls) else 0.0,
            "profit_factor": pf,
            "avg_trade_pct": float(pnls.mean() / start * 100) if len(pnls) else 0.0,
            "fees_pct_of_start": self.fees_paid / start * 100,
            "gross_return_pct": (ret + self.fees_paid / start) * 100,   # komissiyasiz (sof edge)
        }


def run(df: pd.DataFrame, strat: Strategy, cfg: BacktestConfig | None = None) -> Result:
    cfg = cfg or BacktestConfig()
    if cfg.max_position_frac > 1.0:
        raise ValueError("max_position_frac > 1 = leverage; halol emas")
    sig: Signals = strat.signals(df)
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    times = df.index
    day_id = day_index(times)
    n = len(df)

    cash = cfg.initial_equity
    qty = 0.0
    equity = np.empty(n)
    trades: list[Trade] = []
    fees_paid = 0.0

    pending = False
    pend_sl = pend_tp = np.nan
    pend_group = -1
    in_pos = False
    entry_px = sl_px = tp_px = np.nan
    entry_i = -1
    entry_fee = 0.0
    trades_today = 0
    cur_day = -1
    used_groups: set[int] = set()
    highest = 0.0

    def close_position(i, px, reason):
        nonlocal cash, qty, in_pos, fees_paid, entry_fee
        px = px * (1 - cfg.slippage)
        proceeds = qty * px
        fee = proceeds * cfg.fee_rate
        cash += proceeds - fee
        fees_paid += fee
        cost = qty * entry_px
        pnl = proceeds - fee - cost - entry_fee
        trades.append(Trade(times[entry_i], times[i], entry_px, px, qty, pnl, fee + entry_fee, reason))
        qty = 0.0
        in_pos = False

    for i in range(n):
        if day_id[i] != cur_day:
            cur_day = day_id[i]
            trades_today = 0

        # 1) kutilayotgan kirishni ochilishda ijro etish
        if pending and not in_pos:
            pending = False
            px = o[i] * (1 + cfg.slippage)
            sl_dist = pend_sl
            risk_amt = cash * cfg.risk_per_trade
            if np.isinf(sl_dist):
                notional = cash * cfg.max_position_frac
            else:
                notional = min(risk_amt / (sl_dist / px), cash * cfg.max_position_frac)
            notional = min(notional, cash / (1 + cfg.fee_rate))   # komissiya ham naqddan
            if notional >= cfg.min_trade_notional:
                qty = notional / px
                fee = notional * cfg.fee_rate
                cash -= notional + fee
                fees_paid += fee
                entry_fee = fee
                entry_px = px
                sl_px = px - sl_dist
                tp_px = px + pend_tp if not np.isnan(pend_tp) else np.nan
                entry_i = i
                highest = h[i]
                in_pos = True
                trades_today += 1
                if pend_group >= 0:
                    used_groups.add(pend_group)

        # 2) ochiq pozitsiyani boshqarish
        if in_pos and i > entry_i:
            if sig.trail_atr > 0 and sig.atr is not None and not np.isnan(sig.atr[i]):
                highest = max(highest, h[i])
                sl_px = max(sl_px, highest - sig.trail_atr * sig.atr[i])
            if l[i] <= sl_px:
                close_position(i, min(sl_px, o[i]), "SL")
            elif not np.isnan(tp_px) and h[i] >= tp_px:
                close_position(i, max(tp_px, o[i]), "TP")
            elif sig.exit_sig[i]:
                close_position(i, c[i], "EXIT")
            elif i - entry_i >= sig.time_stop:
                close_position(i, c[i], "TIME")

        # 3) yangi signal (sham yopilishida) -> keyingi ochilishda ijro
        if not in_pos and not pending and sig.entry[i] and i < n - 1:
            g = int(sig.group[i])
            if trades_today < cfg.max_trades_per_day and (g < 0 or g not in used_groups):
                pending = True
                pend_sl = float(sig.sl_dist[i])
                pend_tp = float(sig.tp_dist[i])
                pend_group = g

        equity[i] = cash + qty * c[i]

    if in_pos:
        close_position(n - 1, c[n - 1], "END")
        equity[n - 1] = cash
    res = Result(strategy=strat.name, equity_curve=pd.Series(equity, index=times), trades=trades, fees_paid=fees_paid)
    return res
