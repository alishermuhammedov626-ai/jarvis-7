"""Order execution back-ends.

* :class:`CcxtFuturesExchange` - real USDT-M perpetual orders through ccxt
  (SL/TP are *reduce-only stop-market* orders as required for memecoins).
* :class:`PaperExchange`       - simulated fills driven by candles; used by
  paper-trading mode and the backtester.
"""
from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol

from ..models import MarketQuality, MarketSpec, Side

log = logging.getLogger(__name__)


@dataclass
class OrderStatus:
    id: str
    status: str            # open | filled | canceled
    filled: float = 0.0
    avg_price: float = 0.0
    remaining: float = 0.0


class Exchange(Protocol):
    def market_spec(self, symbol: str) -> MarketSpec: ...
    def equity(self) -> float: ...
    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> None: ...
    def place_limit(self, symbol: str, side: Side, qty: float, price: float) -> str: ...
    def place_stop_market(self, symbol: str, close_side: Side, qty: float, stop_price: float) -> str: ...
    def place_take_profit_market(self, symbol: str, close_side: Side, qty: float, stop_price: float) -> str: ...
    def cancel(self, symbol: str, order_id: str) -> None: ...
    def order_status(self, symbol: str, order_id: str) -> OrderStatus: ...


def _order_side(side: Side) -> str:
    return "buy" if side is Side.LONG else "sell"


# --------------------------------------------------------------------------- #
class CcxtFuturesExchange:
    def __init__(self, client):
        self.client = client
        self._specs: dict[str, MarketSpec] = {}
        self.client.load_markets()

    def market_spec(self, symbol: str) -> MarketSpec:
        if symbol not in self._specs:
            m = self.client.market(symbol)
            prec = m.get("precision", {})
            limits = m.get("limits", {})
            amount_step = prec.get("amount") or 1e-8
            price_step = prec.get("price") or 1e-8
            # ccxt returns precision either as a step or as number of decimals
            if amount_step >= 1 and self.client.precisionMode != 4:  # 4 == TICK_SIZE
                amount_step = 10 ** (-int(amount_step))
            if price_step >= 1 and self.client.precisionMode != 4:
                price_step = 10 ** (-int(price_step))
            self._specs[symbol] = MarketSpec(
                symbol=symbol,
                amount_step=float(amount_step),
                price_step=float(price_step),
                min_amount=float((limits.get("amount") or {}).get("min") or amount_step),
                min_notional=float((limits.get("cost") or {}).get("min") or 5.0),
                max_leverage=int((limits.get("leverage") or {}).get("max") or 20),
            )
        return self._specs[symbol]

    def equity(self) -> float:
        bal = self.client.fetch_balance()
        usdt = bal.get("USDT", {})
        total = usdt.get("total")
        if total is None:
            total = bal.get("total", {}).get("USDT", 0.0)
        return float(total or 0.0)

    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> None:
        try:
            self.client.set_margin_mode(margin_mode, symbol)
        except Exception as e:  # already set -> most exchanges raise
            log.debug("set_margin_mode(%s): %s", symbol, e)
        try:
            self.client.set_leverage(leverage, symbol)
        except Exception as e:
            log.warning("set_leverage(%s): %s", symbol, e)

    def _price(self, symbol: str, price: float) -> float:
        return float(self.client.price_to_precision(symbol, price))

    def _amount(self, symbol: str, qty: float) -> float:
        return float(self.client.amount_to_precision(symbol, qty))

    def place_limit(self, symbol: str, side: Side, qty: float, price: float) -> str:
        o = self.client.create_order(
            symbol, "limit", _order_side(side), self._amount(symbol, qty),
            self._price(symbol, price), {"timeInForce": "GTC"},
        )
        return str(o["id"])

    def place_stop_market(self, symbol: str, close_side: Side, qty: float, stop_price: float) -> str:
        o = self.client.create_order(
            symbol, "market", _order_side(close_side), self._amount(symbol, qty), None,
            {"stopLossPrice": self._price(symbol, stop_price), "reduceOnly": True},
        )
        return str(o["id"])

    def place_take_profit_market(self, symbol: str, close_side: Side, qty: float, stop_price: float) -> str:
        o = self.client.create_order(
            symbol, "market", _order_side(close_side), self._amount(symbol, qty), None,
            {"takeProfitPrice": self._price(symbol, stop_price), "reduceOnly": True},
        )
        return str(o["id"])

    def cancel(self, symbol: str, order_id: str) -> None:
        try:
            self.client.cancel_order(order_id, symbol)
        except Exception as e:
            log.debug("cancel %s %s: %s", symbol, order_id, e)

    def order_status(self, symbol: str, order_id: str) -> OrderStatus:
        o = self.client.fetch_order(order_id, symbol)
        status = o.get("status") or "open"
        status = {"closed": "filled", "canceled": "canceled", "cancelled": "canceled",
                  "expired": "canceled", "rejected": "canceled"}.get(status, status)
        return OrderStatus(
            id=str(o["id"]), status=status,
            filled=float(o.get("filled") or 0.0),
            avg_price=float(o.get("average") or o.get("price") or 0.0),
            remaining=float(o.get("remaining") or 0.0),
        )


# --------------------------------------------------------------------------- #
@dataclass
class _PaperOrder:
    id: str
    symbol: str
    side: Side          # order side (buy=LONG / sell=SHORT)
    kind: str           # limit | stop | tp
    qty: float
    price: float
    status: str = "open"
    filled: float = 0.0
    avg_price: float = 0.0
    filled_at: Optional[datetime] = None


class PaperExchange:
    """Deterministic fill simulator.

    Feed it candles through :meth:`process_candle`; orders fill in the same
    way a real stop-market / take-profit-market / limit order would:

    * limit buy  fills when candle.low  <= price (at price)
    * limit sell fills when candle.high >= price
    * stop sell  fills when candle.low  <= stop (at stop minus slippage)
    * stop buy   fills when candle.high >= stop (at stop plus slippage)
    * tp sell    fills when candle.high >= tp  (at tp minus slippage)
    * tp buy     fills when candle.low  <= tp  (at tp plus slippage)

    If a candle touches both SL and TP of the same position the *stop* is
    assumed to fill first (conservative).
    """

    paper_mode = True

    def __init__(self, equity: float, slippage_bps: float = 8.0, fee_bps: float = 4.0,
                 specs: dict[str, MarketSpec] | None = None):
        self._equity = equity
        self.slippage = slippage_bps / 10_000.0
        self.fee = fee_bps / 10_000.0
        self.orders: dict[str, _PaperOrder] = {}
        self._ids = itertools.count(1)
        self._specs = specs or {}
        self.fills: list[dict] = []

    # -- Exchange protocol --------------------------------------------- #
    def market_spec(self, symbol: str) -> MarketSpec:
        return self._specs.get(symbol) or MarketSpec(symbol, 1.0, 1e-8, 1.0, 5.0, 20)

    def equity(self) -> float:
        return self._equity

    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> None:
        return None

    def _new(self, symbol: str, side: Side, kind: str, qty: float, price: float) -> str:
        oid = f"p{next(self._ids)}"
        self.orders[oid] = _PaperOrder(oid, symbol, side, kind, qty, price)
        return oid

    def place_limit(self, symbol, side, qty, price):
        return self._new(symbol, side, "limit", qty, price)

    def place_stop_market(self, symbol, close_side, qty, stop_price):
        return self._new(symbol, close_side, "stop", qty, stop_price)

    def place_take_profit_market(self, symbol, close_side, qty, stop_price):
        return self._new(symbol, close_side, "tp", qty, stop_price)

    def cancel(self, symbol, order_id):
        o = self.orders.get(order_id)
        if o and o.status == "open":
            o.status = "canceled"

    def order_status(self, symbol, order_id) -> OrderStatus:
        o = self.orders[order_id]
        return OrderStatus(o.id, o.status, o.filled, o.avg_price, o.qty - o.filled)

    # -- simulation ------------------------------------------------------ #
    def apply_pnl(self, pnl: float) -> None:
        self._equity += pnl

    def _fill(self, o: _PaperOrder, price: float, ts: datetime) -> None:
        o.status = "filled"
        o.filled = o.qty
        o.avg_price = price
        o.filled_at = ts
        self.fills.append({"id": o.id, "symbol": o.symbol, "kind": o.kind,
                           "side": o.side.value, "qty": o.qty, "price": price, "ts": ts})

    def process_candle(self, symbol: str, high: float, low: float, ts: datetime) -> list[str]:
        """Fill resting orders against one candle.  Returns filled order ids.
        Stops are evaluated before take-profits (conservative)."""
        filled: list[str] = []
        order = {"stop": 0, "limit": 1, "tp": 2}
        for o in sorted((o for o in self.orders.values() if o.symbol == symbol and o.status == "open"),
                        key=lambda x: order[x.kind]):
            if o.kind == "limit":
                if o.side is Side.LONG and low <= o.price:
                    self._fill(o, o.price, ts); filled.append(o.id)
                elif o.side is Side.SHORT and high >= o.price:
                    self._fill(o, o.price, ts); filled.append(o.id)
            elif o.kind == "stop":
                if o.side is Side.SHORT and low <= o.price:      # SL of a long
                    self._fill(o, o.price * (1 - self.slippage), ts); filled.append(o.id)
                elif o.side is Side.LONG and high >= o.price:    # SL of a short
                    self._fill(o, o.price * (1 + self.slippage), ts); filled.append(o.id)
            elif o.kind == "tp":
                if o.side is Side.SHORT and high >= o.price:     # TP of a long
                    self._fill(o, o.price * (1 - self.slippage), ts); filled.append(o.id)
                elif o.side is Side.LONG and low <= o.price:     # TP of a short
                    self._fill(o, o.price * (1 + self.slippage), ts); filled.append(o.id)
        return filled
