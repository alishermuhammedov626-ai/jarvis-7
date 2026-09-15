"""Core data types shared by the analysis, risk and execution layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def opposite(self) -> "Side":
        return Side.SHORT if self is Side.LONG else Side.LONG

    @property
    def sign(self) -> int:
        return 1 if self is Side.LONG else -1


class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class LiqKind(str, Enum):
    PDH = "pdh"
    PDL = "pdl"
    SESSION_HIGH = "session_high"
    SESSION_LOW = "session_low"
    EQH = "eqh"
    EQL = "eql"


_HIGH_KINDS = {LiqKind.PDH, LiqKind.SESSION_HIGH, LiqKind.EQH}
_MAJOR_KINDS = {LiqKind.PDH, LiqKind.PDL, LiqKind.SESSION_HIGH, LiqKind.SESSION_LOW}


@dataclass(frozen=True)
class LiquidityLevel:
    price: float
    kind: LiqKind
    ts: pd.Timestamp
    label: str = ""

    @property
    def is_buyside(self) -> bool:
        """Buy-side liquidity sits above price (stops of shorts / breakout buys)."""
        return self.kind in _HIGH_KINDS

    @property
    def is_sellside(self) -> bool:
        return not self.is_buyside

    @property
    def is_major(self) -> bool:
        return self.kind in _MAJOR_KINDS

    def describe(self) -> str:
        return f"{self.label or self.kind.value}@{self.price:.8g}"


@dataclass
class Sweep:
    level: LiquidityLevel
    side: Side               # side of the trade this sweep sets up
    breach_idx: int          # first candle that pierced the level
    reclaim_idx: int         # candle that closed back beyond the level
    extreme: float           # wick extreme of the sweep
    ts: pd.Timestamp


@dataclass
class MSS:
    side: Side
    idx: int                 # candle that closed through the structural level
    broken_level: float
    leg_start_idx: int       # candle of the sweep extreme (start of impulse)
    displacement_idx: int    # first candle satisfying the displacement rule
    ts: pd.Timestamp


@dataclass
class Zone:
    kind: str                # "fvg" | "ob"
    side: Side
    low: float
    high: float
    idx: int
    ts: pd.Timestamp

    @property
    def size(self) -> float:
        return self.high - self.low

    def entry_price(self, ratio: float) -> float:
        """Price ``ratio`` of the way into the zone from the near edge."""
        ratio = min(max(ratio, 0.0), 1.0)
        if self.side is Side.LONG:
            return self.high - self.size * ratio
        return self.low + self.size * ratio


@dataclass
class Signal:
    symbol: str
    side: Side
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    atr: float
    zone: Zone
    sweep: Sweep
    mss: MSS
    created_at: datetime
    expires_at: datetime
    timeframe: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry - self.stop_loss)

    def rr(self, target: float) -> float:
        if self.risk_per_unit == 0:
            return 0.0
        return abs(target - self.entry) / self.risk_per_unit

    @property
    def rr1(self) -> float:
        return self.rr(self.tp1)

    @property
    def rr2(self) -> float:
        return self.rr(self.tp2)

    def summary(self) -> str:
        return (
            f"{self.symbol} {self.side.value.upper()} entry={self.entry:.8g} "
            f"sl={self.stop_loss:.8g} tp1={self.tp1:.8g} (R{self.rr1:.2f}) "
            f"tp2={self.tp2:.8g} (R{self.rr2:.2f}) zone={self.zone.kind} "
            f"sweep={self.sweep.level.describe()}"
        )


@dataclass
class MarketQuality:
    symbol: str
    bid: float
    ask: float
    quote_volume_24h: float
    depth_notional: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_bps(self) -> float:
        if self.mid <= 0:
            return float("inf")
        return (self.ask - self.bid) / self.mid * 10_000.0


@dataclass
class MarketSpec:
    symbol: str
    amount_step: float
    price_step: float
    min_amount: float
    min_notional: float
    max_leverage: int = 20


class TradeState(str, Enum):
    PENDING = "pending"        # limit entry resting
    OPEN = "open"              # filled, SL + TP1 + TP2 live
    RUNNER = "runner"          # TP1 filled, SL at BE / trailing
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Trade:
    id: str
    symbol: str
    side: Side
    qty: float
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    atr: float
    state: TradeState
    created_at: datetime
    expires_at: datetime
    entry_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    tp1_order_id: Optional[str] = None
    tp2_order_id: Optional[str] = None
    filled_qty: float = 0.0
    remaining_qty: float = 0.0
    avg_entry: float = 0.0
    realized_pnl: float = 0.0
    closed_at: Optional[datetime] = None
    close_reason: str = ""
    signal_summary: str = ""
    risk_usd: float = 0.0
    tp1_hit: bool = False

    @property
    def r_multiple(self) -> float:
        return self.realized_pnl / self.risk_usd if self.risk_usd > 0 else 0.0
