"""Bot configuration.

All tunable parameters live here.  Values can be overridden from a JSON file
(see ``config.example.json``) via :func:`load_config`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class SessionWindow:
    """A trading session expressed in UTC hours [start, end)."""

    name: str
    start_hour: int
    end_hour: int


@dataclass
class AnalysisConfig:
    """Parameters of the SMC detection pipeline."""

    # Timeframes (ccxt notation)
    tf_bias_primary: str = "4h"
    tf_bias_secondary: str = "1h"
    tf_liquidity: str = "15m"
    tf_entry: str = "5m"
    tf_entry_fine: str = "1m"

    # How many candles to request per timeframe
    candles_h4: int = 200
    candles_h1: int = 300
    candles_m15: int = 400
    candles_m5: int = 300
    candles_m1: int = 300

    # Swing detection (fractal) width for structure / liquidity
    swing_left: int = 2
    swing_right: int = 2

    # ATR
    atr_period: int = 14

    # Equal highs / lows tolerance as a multiple of ATR (15m)
    equal_level_tolerance_atr: float = 0.15
    equal_level_lookback: int = 200

    # Sessions (UTC)
    sessions: list[SessionWindow] = field(
        default_factory=lambda: [
            SessionWindow("asia", 0, 8),
            SessionWindow("london", 7, 13),
        ]
    )

    # Sweep: how many entry-TF candles back we accept a sweep, and how many
    # candles after the wick the price must reclaim the level
    sweep_lookback: int = 36
    sweep_reclaim_within: int = 6

    # Displacement candle body must be >= this multiple of ATR
    displacement_atr_mult: float = 1.0
    # MSS must happen within this many candles after the sweep
    mss_max_candles_after_sweep: int = 24

    # FVG minimum size in ATR multiples (filters micro gaps)
    fvg_min_atr_mult: float = 0.10

    # Where inside the zone the limit order is placed.
    # 0.0 = zone edge nearest to price, 0.5 = midpoint (consequent encroachment)
    entry_zone_ratio: float = 0.5

    # SL buffer: ATR * this
    sl_atr_buffer: float = 0.5

    # R:R rules
    min_rr_tp1: float = 1.0
    min_rr_tp2: float = 2.0
    tp2_fixed_rr: float = 3.0
    tp2_max_rr: float = 4.0
    tp1_fallback_rr: float = 1.5

    # Pending limit order lifetime (minutes)
    entry_ttl_minutes: int = 60

    # Trailing stop after TP1: SL = price -/+ ATR * this (never loosened)
    trail_atr_mult: float = 1.0
    # Break-even buffer in bps to cover fees/slippage
    breakeven_buffer_bps: float = 5.0


@dataclass
class RiskConfig:
    """Account / risk-management rules."""

    risk_per_trade_pct: float = 1.0  # % of equity risked per trade
    max_open_positions: int = 2      # 2..3 per spec
    max_trades_per_day: int = 4
    daily_loss_limit_pct: float = 3.0  # stop trading for the day below this
    symbol_cooldown_minutes: int = 90  # no re-entry on same symbol after close
    leverage: int = 5
    margin_mode: str = "isolated"
    # stop distance (bps of price) must be >= this multiple of round-trip
    # cost (2*fee + slippage); protects against setups where costs eat the R
    min_stop_to_cost_ratio: float = 3.0


@dataclass
class MarketFilterConfig:
    """Liquidity / spread protection for memecoins."""

    max_spread_bps: float = 6.0
    min_quote_volume_24h: float = 50_000_000.0  # USDT
    # notional resting within +-0.1% of mid, both sides summed
    min_depth_notional: float = 200_000.0
    depth_band_pct: float = 0.1
    # the bot refuses to place an order larger than this share of the depth
    max_order_depth_share: float = 0.10


@dataclass
class ExchangeConfig:
    exchange_id: str = "binanceusdm"
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = False
    paper: bool = True           # simulate fills, no real orders
    paper_equity: float = 10_000.0
    slippage_bps: float = 8.0    # assumed slippage on stop-market fills (paper)
    fee_bps: float = 4.0         # taker fee estimate (paper)


@dataclass
class BotConfig:
    symbols: list[str] = field(
        default_factory=lambda: [
            "DOGE/USDT:USDT",
            "SHIB/USDT:USDT",
            "PEPE/USDT:USDT",
            "WIF/USDT:USDT",
            "BONK/USDT:USDT",
            "FLOKI/USDT:USDT",
        ]
    )
    loop_seconds: int = 60
    state_dir: str = "state"
    log_level: str = "INFO"
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    market: MarketFilterConfig = field(default_factory=MarketFilterConfig)
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)


def _merge(dc: Any, data: dict[str, Any]) -> Any:
    """Recursively apply ``data`` on top of dataclass ``dc``."""
    for f in fields(dc):
        if f.name not in data:
            continue
        value = data[f.name]
        current = getattr(dc, f.name)
        if is_dataclass(current) and isinstance(value, dict):
            _merge(current, value)
        elif f.name == "sessions" and isinstance(value, list):
            setattr(dc, f.name, [SessionWindow(**s) for s in value])
        else:
            setattr(dc, f.name, value)
    return dc


def load_config(path: str | Path | None = None) -> BotConfig:
    """Return the default config, optionally overridden by a JSON file."""
    cfg = BotConfig()
    if path is None:
        return cfg
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return _merge(cfg, data)


def dump_config(cfg: BotConfig) -> dict[str, Any]:
    return asdict(cfg)
