"""Binance USD-M perpetual futures backtest dvigateli (long + short, leverage, funding, likvidatsiya).

DIQQAT: bu rejim ko'pchilik ulamolar fikricha halol EMAS (funding = riba, leverage = qarz, short).
Foydalanuvchi qarori bilan qo'shilgan. HalalPolicy bu dvigatelga qo'llanmaydi.

Model:
  - Bitta ochiq pozitsiya (long yoki short). Notional <= equity * leverage.
  - Taker komissiya har tomonda (standart 0.05%), slippage har tomonda.
  - Funding har 8 soatda (00/08/16 UTC): long to'laydi, short oladi (funding_rate > 0 bo'lsa).
  - Likvidatsiya: pozitsiya zarari margin*(1 - maint) dan oshsa -> margin to'liq yo'qoladi.
  - Kirish keyingi sham ochilishida; SL/TP sham ichida high/low bilan; ikkalasi ham tegsa SL (konservativ).
  - Kuniga maksimal N kirish.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import day_index


@dataclass
class FSignals:
    long_entry: np.ndarray
    short_entry: np.ndarray
    sl_dist: np.ndarray            # narx birligida (musbat)
    tp_dist: np.ndarray            # NaN = TP yo'q
    exit_long: np.ndarray          # ochiq longni yopish signali
    exit_short: np.ndarray
    group: np.ndarray | None = None
    trail_atr: float = 0.0
    time_stop: int = 10 ** 9
    atr: np.ndarray | None = None
    limit_price: np.ndarray | None = None   # NaN = market kirish; aks holda limit buyurtma narxi
    limit_ttl: int = 8                      # limit buyurtma necha sham kutadi


@dataclass
class FuturesConfig:
    initial_equity: float = 1000.0
    leverage: float = 3.0
    taker_fee: float = 0.0005
    slippage: float = 0.0002
    funding_rate_8h: float = 0.0001      # 0.01% / 8h (Binance bazaviy)
    maint_margin: float = 0.005          # 0.5% (BTC 1-tier)
    risk_per_trade: float = 0.01         # SL masofasida equity ning 1%
    max_trades_per_day: int = 4
    allow_short: bool = True
    min_notional: float = 5.0
    maker_fee: float = 0.0002            # limit kirishlar uchun
    partial_tp_r: float = 0.0            # >0: pozitsiyaning partial_frac qismi shu R (SL masofasi karrasi) da yopiladi
    partial_frac: float = 0.6            # ... va qolganiga stop kirish narxiga (breakeven) ko'chadi


@dataclass
class FTrade:
    side: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    notional: float
    pnl: float
    reason: str


@dataclass
class FResult:
    strategy: str
    equity_curve: pd.Series
    trades: list = field(default_factory=list)
    fees_paid: float = 0.0
    funding_paid: float = 0.0
    liquidated: bool = False

    def metrics(self, days: float) -> dict:
        eq = self.equity_curve
        start, end = eq.iloc[0], eq.iloc[-1]
        ret = end / start - 1
        dd = (eq / eq.cummax() - 1).min()
        daily = eq.resample("1D").last().dropna().pct_change().dropna()
        sharpe = float(daily.mean() / daily.std() * np.sqrt(365)) if len(daily) > 2 and daily.std() > 0 else 0.0
        pnls = np.array([t.pnl for t in self.trades])
        wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
        pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else (np.inf if len(wins) else 0.0)
        n_long = sum(1 for t in self.trades if t.side == "LONG")
        return {
            "return_pct": ret * 100, "max_dd_pct": dd * 100, "sharpe": sharpe,
            "trades": len(self.trades), "trades_per_day": len(self.trades) / days,
            "long_share_pct": n_long / len(self.trades) * 100 if self.trades else 0.0,
            "win_rate_pct": len(wins) / len(pnls) * 100 if len(pnls) else 0.0,
            "profit_factor": min(pf, 99.0),
            "fees_pct": self.fees_paid / start * 100, "funding_pct": self.funding_paid / start * 100,
            "gross_return_pct": (ret + (self.fees_paid + self.funding_paid) / start) * 100,
            "liquidated": float(self.liquidated),
        }


def run_futures(df: pd.DataFrame, strat, cfg: FuturesConfig | None = None) -> FResult:
    cfg = cfg or FuturesConfig()
    sig: FSignals = strat.fsignals(df)
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    times = df.index
    day_id = day_index(times)
    hour = times.hour.values
    minute = times.minute.values
    funding_bar = ((hour % 8) == 0) & (minute == 0)
    n = len(df)

    equity = cfg.initial_equity      # margin balansi (realizatsiya qilingan)
    eq_curve = np.empty(n)
    trades: list[FTrade] = []
    fees_paid = funding_paid = 0.0
    liquidated = False

    pending = 0                       # +1 long, -1 short
    pend_sl = pend_tp = np.nan
    pend_group = -1
    pend_limit = np.nan; pend_ttl = 0
    partial_done = False; partial_px = np.nan; pos_realized = 0.0
    pos = 0                            # +1/-1/0
    entry_px = sl_px = tp_px = np.nan
    notional = qty = 0.0
    entry_i = -1
    entry_fee = 0.0
    extreme = 0.0
    trades_today, cur_day = 0, -1
    used_groups: set[int] = set()

    def close(i, px, reason):
        nonlocal equity, pos, fees_paid, qty, notional, pos_realized
        px = px * (1 - cfg.slippage * pos)
        fee = qty * px * cfg.taker_fee
        pnl = (px - entry_px) * qty * pos - fee - entry_fee + pos_realized
        equity += (px - entry_px) * qty * pos - fee
        fees_paid += fee
        trades.append(FTrade("LONG" if pos > 0 else "SHORT", times[entry_i], times[i], entry_px, px, notional, pnl, reason))
        pos = 0
        qty = notional = 0.0
        pos_realized = 0.0

    def open_position(i, px, side, sl_dist, tp_dist, is_limit):
        nonlocal equity, fees_paid, entry_fee, entry_px, pos, sl_px, tp_px, entry_i, extreme, trades_today
        nonlocal notional, qty, partial_done, partial_px, pos_realized
        risk_amt = equity * cfg.risk_per_trade
        want = equity * cfg.leverage if np.isinf(sl_dist) else min(risk_amt / (sl_dist / px), equity * cfg.leverage)
        if want < cfg.min_notional or equity <= 0:
            return False
        notional = want; qty = notional / px
        fee = notional * (cfg.maker_fee if is_limit else cfg.taker_fee)
        equity -= fee; fees_paid += fee; entry_fee = fee
        entry_px = px; pos = side
        sl_px = px - sl_dist * side
        tp_px = px + tp_dist * side if not np.isnan(tp_dist) else np.nan
        partial_done = False; pos_realized = 0.0
        partial_px = px + cfg.partial_tp_r * sl_dist * side if cfg.partial_tp_r > 0 and not np.isinf(sl_dist) else np.nan
        entry_i = i; extreme = h[i] if side > 0 else l[i]
        trades_today += 1
        return True

    for i in range(n):
        if day_id[i] != cur_day:
            cur_day, trades_today = day_id[i], 0
        if liquidated:
            eq_curve[i] = equity
            continue

        # 1) kutilayotgan kirish -> market: ochilishda; limit: narx tegsa
        if pending and pos == 0:
            side = pending
            if np.isnan(pend_limit):
                pending = 0
                px = o[i] * (1 + cfg.slippage * side)
                if open_position(i, px, side, pend_sl, pend_tp, False) and pend_group >= 0:
                    used_groups.add(pend_group)
            else:
                touched = (l[i] <= pend_limit) if side > 0 else (h[i] >= pend_limit)
                if touched:
                    pending = 0
                    px = min(pend_limit, o[i]) if side > 0 else max(pend_limit, o[i])
                    if open_position(i, px, side, pend_sl, pend_tp, True) and pend_group >= 0:
                        used_groups.add(pend_group)
                else:
                    pend_ttl -= 1
                    if pend_ttl <= 0:
                        pending = 0

        # 2) ochiq pozitsiya
        if pos != 0 and i > entry_i:
            if funding_bar[i]:
                f = notional * cfg.funding_rate_8h * pos      # long to'laydi, short oladi
                equity -= f
                funding_paid += f
            if sig.trail_atr > 0 and sig.atr is not None and not np.isnan(sig.atr[i]):
                if pos > 0:
                    extreme = max(extreme, h[i]); sl_px = max(sl_px, extreme - sig.trail_atr * sig.atr[i])
                else:
                    extreme = min(extreme, l[i]); sl_px = min(sl_px, extreme + sig.trail_atr * sig.atr[i])
            # likvidatsiya narxi
            margin = notional / cfg.leverage
            liq_px = entry_px - pos * (margin * (1 - cfg.maint_margin)) / qty
            hit_liq = (l[i] <= liq_px) if pos > 0 else (h[i] >= liq_px)
            # qisman TP + breakeven (SL dan oldin tekshiriladi, faqat SL tegmagan bo'lsa)
            hit_sl = (l[i] <= sl_px) if pos > 0 else (h[i] >= sl_px)
            if not partial_done and not np.isnan(partial_px) and not hit_sl and not hit_liq:
                hit_p = (h[i] >= partial_px) if pos > 0 else (l[i] <= partial_px)
                if hit_p:
                    pq = qty * cfg.partial_frac
                    ppx = partial_px * (1 - cfg.slippage * pos)
                    fee = pq * ppx * cfg.taker_fee
                    gain = (ppx - entry_px) * pq * pos - fee
                    equity += gain; fees_paid += fee; pos_realized += gain
                    qty -= pq; notional = qty * entry_px
                    sl_px = entry_px            # breakeven
                    partial_done = True
                    hit_sl = (l[i] <= sl_px) if pos > 0 else (h[i] >= sl_px)   # shu shamda qaytib tegishi mumkin
                    if hit_sl and ((c[i] > sl_px) if pos > 0 else (c[i] < sl_px)):
                        hit_sl = False       # partial dan keyin yopilishgacha qaytmagan deb hisoblaymiz
            hit_tp = (not np.isnan(tp_px)) and ((h[i] >= tp_px) if pos > 0 else (l[i] <= tp_px))
            if hit_liq and (pos > 0 and liq_px >= sl_px or pos < 0 and liq_px <= sl_px):
                # likvidatsiya SL dan oldin: margin to'liq yo'qoladi
                trades.append(FTrade("LONG" if pos > 0 else "SHORT", times[entry_i], times[i], entry_px, liq_px, notional,
                                     -(margin + entry_fee), "LIQ"))
                equity -= margin
                pos = 0; qty = notional = 0.0
                if equity <= 0:
                    liquidated = True; equity = 0.0
            elif hit_sl:
                px = (min(sl_px, o[i]) if pos > 0 else max(sl_px, o[i]))
                close(i, px, "SL")
            elif hit_tp:
                px = (max(tp_px, o[i]) if pos > 0 else min(tp_px, o[i]))
                close(i, px, "TP")
            elif (pos > 0 and sig.exit_long[i]) or (pos < 0 and sig.exit_short[i]):
                close(i, c[i], "EXIT")
            elif i - entry_i >= sig.time_stop:
                close(i, c[i], "TIME")
            if equity <= 0:
                liquidated = True; equity = 0.0; pos = 0

        # 3) yangi signal
        if pos == 0 and not pending and i < n - 1 and trades_today < cfg.max_trades_per_day:
            side = 0
            if sig.long_entry[i]:
                side = 1
            elif cfg.allow_short and sig.short_entry[i]:
                side = -1
            if side and not np.isnan(sig.sl_dist[i]) and sig.sl_dist[i] > 0:
                g = int(sig.group[i]) if sig.group is not None else -1
                if g < 0 or g not in used_groups:
                    pending = side
                    pend_sl = float(sig.sl_dist[i]); pend_tp = float(sig.tp_dist[i]); pend_group = g
                    pend_limit = float(sig.limit_price[i]) if sig.limit_price is not None else np.nan
                    pend_ttl = sig.limit_ttl

        unreal = (c[i] - entry_px) * qty * pos if pos else 0.0
        eq_curve[i] = max(equity + unreal, 0.0)

    if pos != 0:
        close(n - 1, c[n - 1], "END")
        eq_curve[n - 1] = equity
    return FResult(strat.name, pd.Series(eq_curve, index=times), trades, fees_paid, funding_paid, liquidated)
