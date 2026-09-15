"""Protective filters for memecoin trading.

* market quality (spread / 24h volume / order-book depth)
* concurrent position cap + correlation ranking
* per-day trade count, daily loss limit, per-symbol cooldown
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..config import MarketFilterConfig, RiskConfig
from ..models import MarketQuality, Signal


def market_filter(mq: MarketQuality, cfg: MarketFilterConfig) -> tuple[bool, str]:
    if mq.bid <= 0 or mq.ask <= 0:
        return False, "no quotes"
    if mq.spread_bps > cfg.max_spread_bps:
        return False, f"spread {mq.spread_bps:.1f}bps > {cfg.max_spread_bps}bps"
    if mq.quote_volume_24h < cfg.min_quote_volume_24h:
        return False, f"24h volume {mq.quote_volume_24h:,.0f} < {cfg.min_quote_volume_24h:,.0f}"
    if mq.depth_notional < cfg.min_depth_notional:
        return False, f"depth {mq.depth_notional:,.0f} < {cfg.min_depth_notional:,.0f}"
    return True, "ok"


def order_fits_depth(notional: float, mq: MarketQuality, cfg: MarketFilterConfig) -> bool:
    return notional <= mq.depth_notional * cfg.max_order_depth_share


def rank_candidates(
    signals: list[Signal],
    qualities: dict[str, MarketQuality],
    slots: int,
) -> list[Signal]:
    """Correlation filter: memecoins move together, so when several fire at
    once keep only the ``slots`` best by (highest volume, lowest spread)."""
    if slots <= 0 or not signals:
        return []
    by_volume = sorted(signals, key=lambda s: -qualities[s.symbol].quote_volume_24h)
    by_spread = sorted(signals, key=lambda s: qualities[s.symbol].spread_bps)
    score = {s.symbol: 0 for s in signals}
    for rank, s in enumerate(by_volume):
        score[s.symbol] += rank
    for rank, s in enumerate(by_spread):
        score[s.symbol] += rank
    ordered = sorted(signals, key=lambda s: (score[s.symbol], -s.rr2))
    return ordered[:slots]


@dataclass
class TradeGovernor:
    """Daily quotas, loss limit and cooldowns.  Pure in-memory; the bot
    persists / restores it through ``to_dict`` / ``from_dict``."""

    cfg: RiskConfig
    day: str = ""
    trades_today: int = 0
    pnl_today: float = 0.0
    start_equity: float = 0.0
    last_close: dict[str, datetime] = field(default_factory=dict)

    def _roll_day(self, now: datetime, equity: float) -> None:
        day = now.strftime("%Y-%m-%d")
        if day != self.day:
            self.day = day
            self.trades_today = 0
            self.pnl_today = 0.0
            self.start_equity = equity

    def can_trade(self, symbol: str, now: datetime, equity: float) -> tuple[bool, str]:
        self._roll_day(now, equity)
        if self.trades_today >= self.cfg.max_trades_per_day:
            return False, "daily trade cap reached"
        if self.start_equity > 0:
            dd_pct = -self.pnl_today / self.start_equity * 100.0
            if dd_pct >= self.cfg.daily_loss_limit_pct:
                return False, f"daily loss limit hit ({dd_pct:.2f}%)"
        last = self.last_close.get(symbol)
        if last and now - last < timedelta(minutes=self.cfg.symbol_cooldown_minutes):
            return False, f"{symbol} in cooldown"
        return True, "ok"

    def register_open(self, now: datetime, equity: float) -> None:
        self._roll_day(now, equity)
        self.trades_today += 1

    def register_close(self, symbol: str, pnl: float, now: datetime, equity: float) -> None:
        self._roll_day(now, equity)
        self.pnl_today += pnl
        self.last_close[symbol] = now

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "trades_today": self.trades_today,
            "pnl_today": self.pnl_today,
            "start_equity": self.start_equity,
            "last_close": {k: v.isoformat() for k, v in self.last_close.items()},
        }

    @classmethod
    def from_dict(cls, cfg: RiskConfig, d: dict) -> "TradeGovernor":
        g = cls(cfg)
        g.day = d.get("day", "")
        g.trades_today = int(d.get("trades_today", 0))
        g.pnl_today = float(d.get("pnl_today", 0.0))
        g.start_equity = float(d.get("start_equity", 0.0))
        for k, v in d.get("last_close", {}).items():
            ts = datetime.fromisoformat(v)
            g.last_close[k] = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return g
