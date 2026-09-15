"""Position lifecycle manager.

PENDING  limit entry resting inside the FVG/OB
  |  filled
OPEN     SL (stop-market, full qty) + TP1 (50%) + TP2 (50%) live
  |  TP1 filled
RUNNER   SL moved to break-even, then trailed behind price by ATR
  |  SL or TP2 filled
CLOSED
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..config import AnalysisConfig, RiskConfig
from ..models import MarketSpec, Side, Signal, Trade, TradeState
from ..risk.sizing import round_step, round_step_up, split_tp_quantities
from .exchange import Exchange

log = logging.getLogger(__name__)

ACTIVE = {TradeState.PENDING, TradeState.OPEN, TradeState.RUNNER}


class PositionManager:
    def __init__(
        self,
        exchange: Exchange,
        analysis: AnalysisConfig,
        risk: RiskConfig,
        state_path: str | Path | None = None,
        on_close: Callable[[Trade], None] | None = None,
        fee_bps: float = 4.0,
    ):
        self.ex = exchange
        self.acfg = analysis
        self.rcfg = risk
        self.state_path = Path(state_path) if state_path else None
        self.on_close = on_close
        self.fee = fee_bps / 10_000.0
        self.trades: dict[str, Trade] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # persistence
    def _load(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text())
        for d in data.get("trades", []):
            for k in ("created_at", "expires_at", "closed_at"):
                if d.get(k):
                    d[k] = datetime.fromisoformat(d[k])
            d["side"] = Side(d["side"])
            d["state"] = TradeState(d["state"])
            self.trades[d["id"]] = Trade(**d)

    def save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for t in self.trades.values():
            d = asdict(t)
            for k in ("created_at", "expires_at", "closed_at"):
                if d.get(k):
                    d[k] = d[k].isoformat()
            d["side"] = t.side.value
            d["state"] = t.state.value
            rows.append(d)
        self.state_path.write_text(json.dumps({"trades": rows}, indent=2))

    # ------------------------------------------------------------------ #
    # queries
    def active(self) -> list[Trade]:
        return [t for t in self.trades.values() if t.state in ACTIVE]

    def open_slots(self) -> int:
        return max(0, self.rcfg.max_open_positions - len(self.active()))

    def has_active(self, symbol: str) -> bool:
        return any(t.symbol == symbol for t in self.active())

    # ------------------------------------------------------------------ #
    # entry
    def submit(self, sig: Signal, qty: float) -> Trade:
        spec = self.ex.market_spec(sig.symbol)
        self.ex.set_leverage(sig.symbol, self.rcfg.leverage, self.rcfg.margin_mode)
        entry_id = self.ex.place_limit(sig.symbol, sig.side, qty, sig.entry)
        t = Trade(
            id=uuid.uuid4().hex[:10],
            symbol=sig.symbol, side=sig.side, qty=qty,
            entry=sig.entry, stop_loss=sig.stop_loss, tp1=sig.tp1, tp2=sig.tp2, atr=sig.atr,
            state=TradeState.PENDING, created_at=sig.created_at, expires_at=sig.expires_at,
            entry_order_id=entry_id, signal_summary=sig.summary(),
        )
        self.trades[t.id] = t
        self.save()
        log.info("PENDING %s qty=%s | %s", t.id, qty, t.signal_summary)
        return t

    # ------------------------------------------------------------------ #
    # main poll
    def update(self, now: datetime, atr_by_symbol: dict[str, float] | None = None,
               price_by_symbol: dict[str, float] | None = None) -> None:
        atr_by_symbol = atr_by_symbol or {}
        price_by_symbol = price_by_symbol or {}
        for t in list(self.active()):
            try:
                if t.state is TradeState.PENDING:
                    self._poll_pending(t, now)
                elif t.state is TradeState.OPEN:
                    self._poll_open(t, now)
                elif t.state is TradeState.RUNNER:
                    self._poll_runner(t, now, atr_by_symbol.get(t.symbol), price_by_symbol.get(t.symbol))
            except Exception:  # keep the loop alive; the next poll retries
                log.exception("manager error on trade %s", t.id)
        self.save()

    # -- pending --------------------------------------------------------- #
    def _poll_pending(self, t: Trade, now: datetime) -> None:
        st = self.ex.order_status(t.symbol, t.entry_order_id)
        if st.status == "filled":
            self._on_entry_filled(t, st.filled or t.qty, st.avg_price or t.entry)
            return
        if st.status == "canceled":
            if st.filled > 0:
                self._on_entry_filled(t, st.filled, st.avg_price or t.entry)
            else:
                self._cancel_trade(t, now, "entry canceled")
            return
        if now >= t.expires_at:
            self.ex.cancel(t.symbol, t.entry_order_id)
            st = self.ex.order_status(t.symbol, t.entry_order_id)
            if st.filled > 0:
                self._on_entry_filled(t, st.filled, st.avg_price or t.entry)
            else:
                self._cancel_trade(t, now, "entry expired")

    def _on_entry_filled(self, t: Trade, qty: float, avg: float) -> None:
        spec = self.ex.market_spec(t.symbol)
        t.filled_qty = qty
        t.remaining_qty = qty
        t.avg_entry = avg
        close_side = t.side.opposite
        t.sl_order_id = self.ex.place_stop_market(t.symbol, close_side, qty, t.stop_loss)
        q1, q2 = split_tp_quantities(qty, spec)
        if q1 > 0:
            t.tp1_order_id = self.ex.place_take_profit_market(t.symbol, close_side, q1, t.tp1)
        t.tp2_order_id = self.ex.place_take_profit_market(t.symbol, close_side, q2, t.tp2)
        t.state = TradeState.OPEN
        log.info("OPEN %s %s %s qty=%s @ %s sl=%s tp1=%s tp2=%s", t.id, t.symbol, t.side.value,
                 qty, avg, t.stop_loss, t.tp1, t.tp2)

    # -- open ------------------------------------------------------------ #
    def _pnl(self, t: Trade, exit_price: float, qty: float) -> float:
        gross = (exit_price - t.avg_entry) * qty * t.side.sign
        fees = (t.avg_entry + exit_price) * qty * self.fee
        return gross - fees

    def _poll_open(self, t: Trade, now: datetime) -> None:
        sl = self.ex.order_status(t.symbol, t.sl_order_id)
        if sl.status == "filled":
            self._close(t, now, sl.avg_price, t.remaining_qty, "stop_loss")
            return
        tp2 = self.ex.order_status(t.symbol, t.tp2_order_id)
        if t.tp1_order_id:
            tp1 = self.ex.order_status(t.symbol, t.tp1_order_id)
            if tp1.status == "filled":
                t.realized_pnl += self._pnl(t, tp1.avg_price, tp1.filled)
                t.remaining_qty = round_step(t.remaining_qty - tp1.filled, self.ex.market_spec(t.symbol).amount_step)
                if tp2.status == "filled":  # both hit within the same poll
                    self._close(t, now, tp2.avg_price, tp2.filled, "tp2", already_counted=True)
                    return
                self._move_to_breakeven(t)
                t.state = TradeState.RUNNER
                log.info("TP1 hit %s -> SL to break-even %.8g, trailing on", t.id, t.stop_loss)
                return
        if tp2.status == "filled":
            # TP2 hit before TP1 filled (gap) -> flat; cancel the rest
            t.realized_pnl += self._pnl(t, tp2.avg_price, tp2.filled)
            t.remaining_qty = round_step(t.remaining_qty - tp2.filled, self.ex.market_spec(t.symbol).amount_step)
            if t.remaining_qty <= 0:
                self._close(t, now, tp2.avg_price, 0.0, "tp2", already_counted=True)
            else:
                t.tp2_order_id = None
                self._move_to_breakeven(t)
                t.state = TradeState.RUNNER

    def _move_to_breakeven(self, t: Trade) -> None:
        buf = t.avg_entry * self.acfg.breakeven_buffer_bps / 10_000.0
        be = t.avg_entry + buf * t.side.sign
        self._replace_sl(t, be)

    def _replace_sl(self, t: Trade, new_sl: float) -> None:
        spec = self.ex.market_spec(t.symbol)
        # round *away* from price so the stop never becomes tighter than intended
        new_sl = round_step(new_sl, spec.price_step) if t.side is Side.LONG else round_step_up(new_sl, spec.price_step)
        if t.sl_order_id:
            self.ex.cancel(t.symbol, t.sl_order_id)
        t.sl_order_id = self.ex.place_stop_market(t.symbol, t.side.opposite, t.remaining_qty, new_sl)
        t.stop_loss = new_sl

    # -- runner ---------------------------------------------------------- #
    def _poll_runner(self, t: Trade, now: datetime, atr: float | None, price: float | None) -> None:
        sl = self.ex.order_status(t.symbol, t.sl_order_id)
        if sl.status == "filled":
            self._close(t, now, sl.avg_price, t.remaining_qty, "trailing_stop")
            return
        if t.tp2_order_id:
            tp2 = self.ex.order_status(t.symbol, t.tp2_order_id)
            if tp2.status == "filled":
                self._close(t, now, tp2.avg_price, t.remaining_qty, "tp2")
                return
        # trailing: ratchet SL behind price by ATR * mult, never loosen
        if atr and price:
            candidate = price - atr * self.acfg.trail_atr_mult if t.side is Side.LONG \
                else price + atr * self.acfg.trail_atr_mult
            improves = candidate > t.stop_loss if t.side is Side.LONG else candidate < t.stop_loss
            step = self.ex.market_spec(t.symbol).price_step
            if improves and abs(candidate - t.stop_loss) >= max(step, atr * 0.1):
                self._replace_sl(t, candidate)
                log.info("TRAIL %s sl -> %.8g", t.id, t.stop_loss)

    # -- close ----------------------------------------------------------- #
    def _cancel_all(self, t: Trade) -> None:
        for oid in (t.entry_order_id, t.sl_order_id, t.tp1_order_id, t.tp2_order_id):
            if oid:
                try:
                    st = self.ex.order_status(t.symbol, oid)
                    if st.status == "open":
                        self.ex.cancel(t.symbol, oid)
                except Exception:
                    log.debug("cancel failed for %s", oid)

    def _cancel_trade(self, t: Trade, now: datetime, reason: str) -> None:
        self._cancel_all(t)
        t.state = TradeState.CANCELLED
        t.closed_at = now
        t.close_reason = reason
        log.info("CANCELLED %s (%s)", t.id, reason)

    def _close(self, t: Trade, now: datetime, exit_price: float, qty: float, reason: str,
               already_counted: bool = False) -> None:
        if qty > 0 and not already_counted:
            t.realized_pnl += self._pnl(t, exit_price, qty)
        t.remaining_qty = 0.0
        self._cancel_all(t)
        t.state = TradeState.CLOSED
        t.closed_at = now
        t.close_reason = reason
        log.info("CLOSED %s %s pnl=%.4f (%s)", t.id, t.symbol, t.realized_pnl, reason)
        if hasattr(self.ex, "apply_pnl"):
            self.ex.apply_pnl(t.realized_pnl)
        if self.on_close:
            self.on_close(t)
