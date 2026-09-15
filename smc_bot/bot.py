"""24/7 main loop.

Every ``loop_seconds``:
  1. refresh equity + market quality per symbol (spread / volume / depth)
  2. poll live trades (fills, TP1 -> BE, trailing, expiry)
  3. if slots are free and the daily governor allows it, run the SMC
     pipeline on every tradable symbol, rank the candidates (correlation
     filter) and submit limit entries for the best ones
"""
from __future__ import annotations

import json
import logging
from collections import Counter
import signal as os_signal
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import BotConfig
from .data.feed import DataSource
from .execution.exchange import Exchange
from .execution.manager import PositionManager
from .indicators import atr as atr_indicator
from .models import MarketQuality, Signal, Trade
from .risk.filters import TradeGovernor, market_filter, order_fits_depth, rank_candidates
from .risk.sizing import position_size
from .strategy.confirm import check_confirmation
from .strategy.setup import SetupEngine

log = logging.getLogger(__name__)


class SmcScalperBot:
    def __init__(self, cfg: BotConfig, data: DataSource, exchange: Exchange):
        self.cfg = cfg
        self.data = data
        self.ex = exchange
        self.engine = SetupEngine(cfg.analysis)
        state_dir = Path(cfg.state_dir) if cfg.state_dir else None
        self.gov_path = state_dir / "governor.json" if state_dir else None
        self.governor = self._load_governor()
        self.manager = PositionManager(
            exchange, cfg.analysis, cfg.risk,
            state_path=state_dir / "trades.json" if state_dir else None,
            on_close=self._on_trade_closed,
            fee_bps=cfg.exchange.fee_bps,
        )
        self._seen: set[str] = set()
        self.armed: dict[str, Signal] = {}       # confirm-mode setups waiting for a reaction
        self.skipped: Counter[str] = Counter()   # signals dropped at sizing / depth checks
        self._running = True
        self._equity_cache = 0.0

    # ------------------------------------------------------------------ #
    def _load_governor(self) -> TradeGovernor:
        windows = self.cfg.analysis.trade_windows
        if self.gov_path and self.gov_path.exists():
            return TradeGovernor.from_dict(self.cfg.risk, json.loads(self.gov_path.read_text()), windows)
        return TradeGovernor(self.cfg.risk, windows)

    def _save_governor(self) -> None:
        if not self.gov_path:
            return
        self.gov_path.parent.mkdir(parents=True, exist_ok=True)
        self.gov_path.write_text(json.dumps(self.governor.to_dict(), indent=2))

    def _on_trade_closed(self, t: Trade) -> None:
        now = t.closed_at or datetime.now(timezone.utc)
        self.governor.register_close(t.symbol, t.realized_pnl, now, self._equity_cache)
        self._save_governor()

    # ------------------------------------------------------------------ #
    def frames(self, symbol: str, now: datetime):
        a = self.cfg.analysis
        return (
            self.data.ohlcv(symbol, a.tf_bias_primary, a.candles_h4, now),
            self.data.ohlcv(symbol, a.tf_bias_secondary, a.candles_h1, now),
            self.data.ohlcv(symbol, a.tf_liquidity, a.candles_m15, now),
            self.data.ohlcv(symbol, a.tf_entry, a.candles_m5, now),
            self.data.ohlcv(symbol, a.tf_entry_fine, a.candles_m1, now),
        )

    def scan(self, now: datetime, qualities: dict[str, MarketQuality]) -> list[Signal]:
        """Run the pipeline on every tradable symbol and return fresh signals."""
        found: list[Signal] = []
        for symbol, mq in qualities.items():
            if self.manager.has_active(symbol) or symbol in self.armed:
                continue
            ok, why = self.governor.can_trade(symbol, now, self._equity_cache)
            if not ok:
                log.debug("%s skipped: %s", symbol, why)
                continue
            try:
                h4, h1, m15, m5, m1 = self.frames(symbol, now)
                sig = self.engine.evaluate(symbol, h4, h1, m15, m5, m1, now)
            except Exception:
                log.exception("analysis failed for %s", symbol)
                continue
            if sig is None:
                continue
            key = f"{symbol}|{sig.side.value}|{sig.mss.ts.isoformat()}|{sig.zone.ts.isoformat()}"
            if key in self._seen:
                continue
            found.append(sig)
            sig.meta["dedup_key"] = key
        return found

    def step(self, now: datetime | None = None) -> None:
        """One iteration of the loop (public so backtests can drive it)."""
        now = now or datetime.now(timezone.utc)
        self._equity_cache = self.ex.equity()

        # 1. market quality
        qualities: dict[str, MarketQuality] = {}
        for symbol in self.cfg.symbols:
            try:
                mq = self.data.quality(symbol, now)
            except Exception:
                log.exception("quality fetch failed for %s", symbol)
                continue
            ok, why = market_filter(mq, self.cfg.market)
            if ok:
                qualities[symbol] = mq
            else:
                log.debug("%s filtered: %s", symbol, why)

        # 2. manage open trades (ATR + price for trailing)
        atrs: dict[str, float] = {}
        prices: dict[str, float] = {}
        for t in self.manager.active():
            try:
                m5 = self.data.ohlcv(t.symbol, self.cfg.analysis.tf_entry, self.cfg.analysis.candles_m5, now)
                if len(m5):
                    atrs[t.symbol] = float(atr_indicator(m5, self.cfg.analysis.atr_period).iloc[-1])
                prices[t.symbol] = self.data.last_price(t.symbol, now)
            except Exception:
                log.exception("price/atr fetch failed for %s", t.symbol)
        self.manager.update(now, atrs, prices)

        # 3. armed setups waiting for confirmation
        self._check_armed(now, qualities)

        # 4. new entries (armed setups reserve a slot)
        slots = self.manager.open_slots() - len(self.armed)
        if slots <= 0:
            return
        signals = self.scan(now, qualities)
        if not signals:
            return
        for sig in rank_candidates(signals, qualities, slots):
            self._seen.add(sig.meta["dedup_key"])
            if self.cfg.analysis.entry_mode == "confirm":
                self.armed[sig.symbol] = sig
                log.info("ARMED %s (waiting for 1m reaction in zone)", sig.summary())
            else:
                self._submit(sig, qualities[sig.symbol], now)

    def _check_armed(self, now: datetime, qualities: dict[str, MarketQuality]) -> None:
        for symbol, sig in list(self.armed.items()):
            if now >= sig.expires_at:
                self.armed.pop(symbol)
                self.skipped["confirm_expired"] += 1
                continue
            try:
                m1 = self.data.ohlcv(symbol, "1m", self.cfg.analysis.entry_ttl_minutes + 5, now)
            except Exception:
                log.exception("m1 fetch failed for %s", symbol)
                continue
            status, price = check_confirmation(m1, sig, sig.created_at)
            if status == "invalid":
                self.armed.pop(symbol)
                self.skipped["confirm_invalidated"] += 1
            elif status == "confirmed":
                self.armed.pop(symbol)
                mq = qualities.get(symbol)
                if mq is None:
                    self.skipped["confirm_market_filtered"] += 1
                    continue
                self._rebase_targets(sig, price)
                if sig.rr2 < self.cfg.analysis.min_rr_tp2 or sig.rr1 < self.cfg.analysis.min_rr_tp1:
                    self.skipped["confirm_rr_too_low"] += 1
                    continue
                sig.created_at = now
                self._submit(sig, mq, now, market=True)

    @staticmethod
    def _rebase_targets(sig: Signal, price: float) -> None:
        """Confirmation entry: SL stays anchored to the zone, liquidity-based
        targets stay where the liquidity is, but *fixed-R* targets are
        re-expressed from the actual entry price."""
        old_risk = sig.risk_per_unit
        rr1, rr2 = sig.rr1, sig.rr2
        sig.entry = price
        new_risk = sig.risk_per_unit
        if new_risk <= 0:
            return
        if str(sig.meta.get("tp1_source", "")).startswith("fixed"):
            sig.tp1 = price + sig.side.sign * rr1 * new_risk
        if str(sig.meta.get("tp2_source", "")).startswith("fixed"):
            sig.tp2 = price + sig.side.sign * max(rr2, sig.rr1 + 1.0) * new_risk
        sig.meta["confirm_entry"] = True

    def _submit(self, sig: Signal, mq: MarketQuality, now: datetime, market: bool = False) -> None:
        spec = self.ex.market_spec(sig.symbol)
        # round-trip fees + stop-market slippage on exit (+ entry slippage for market entries)
        cost_bps = 2 * self.cfg.exchange.fee_bps + self.cfg.exchange.slippage_bps * (2 if market else 1)
        stop_bps = sig.risk_per_unit / sig.entry * 10_000.0
        if stop_bps < self.cfg.risk.min_stop_to_cost_ratio * cost_bps:
            log.info("%s: stop %.1fbps too tight vs cost %.1fbps, skipped", sig.symbol, stop_bps, cost_bps)
            self.skipped["stop_too_tight_vs_cost"] += 1
            return
        qty = position_size(self._equity_cache, self.cfg.risk.risk_per_trade_pct,
                            sig.entry, sig.stop_loss, spec, self.cfg.risk.leverage, cost_bps)
        if qty <= 0:
            log.info("%s: cannot size position within limits, skipped", sig.symbol)
            self.skipped["cannot_size"] += 1
            return
        if not order_fits_depth(qty * sig.entry, mq, self.cfg.market):
            log.info("%s: order notional too large for book depth, skipped", sig.symbol)
            self.skipped["exceeds_depth"] += 1
            return
        log.info("SIGNAL %s | tp1 from %s, tp2 from %s", sig.summary(),
                 sig.meta.get("tp1_source"), sig.meta.get("tp2_source"))
        # 1R = the full budget: price distance + round-trip costs on the notional
        risk_usd = qty * (sig.risk_per_unit + sig.entry * cost_bps / 10_000.0)
        if market:
            self.manager.submit_market(sig, qty, sig.entry, risk_usd)
        else:
            self.manager.submit(sig, qty, risk_usd)
        self.governor.register_open(now, self._equity_cache)
        self._save_governor()

    # ------------------------------------------------------------------ #
    def stop(self, *_):
        self._running = False

    def run_forever(self) -> None:
        os_signal.signal(os_signal.SIGINT, self.stop)
        os_signal.signal(os_signal.SIGTERM, self.stop)
        log.info("bot started: %s symbols, paper=%s", len(self.cfg.symbols), self.cfg.exchange.paper)
        while self._running:
            started = time.time()
            try:
                self.step()
            except Exception:
                log.exception("loop iteration failed")
            elapsed = time.time() - started
            time.sleep(max(1.0, self.cfg.loop_seconds - elapsed))
        log.info("bot stopped")


# ---------------------------------------------------------------------- #
def build_live(cfg: BotConfig) -> SmcScalperBot:
    """Wire ccxt data + (paper | real) execution."""
    import ccxt

    from .data.feed import CcxtDataSource
    from .execution.exchange import CcxtFuturesExchange, PaperExchange

    klass = getattr(ccxt, cfg.exchange.exchange_id)
    client = klass({
        "apiKey": cfg.exchange.api_key or None,
        "secret": cfg.exchange.api_secret or None,
        "enableRateLimit": True,
        "options": {"defaultType": "swap"},
    })
    if cfg.exchange.sandbox:
        client.set_sandbox_mode(True)
    client.load_markets()
    data = CcxtDataSource(client, cfg.market.depth_band_pct)

    if cfg.exchange.paper:
        real = CcxtFuturesExchange(client)
        specs = {s: real.market_spec(s) for s in cfg.symbols}
        exchange = PaperExchange(cfg.exchange.paper_equity, cfg.exchange.slippage_bps,
                                 cfg.exchange.fee_bps, specs)
        bot = SmcScalperBot(cfg, data, exchange)
        # paper fills are driven by the latest closed 1m candle each loop
        _attach_paper_fill_driver(bot, exchange)
        return bot
    return SmcScalperBot(cfg, data, CcxtFuturesExchange(client))


def _attach_paper_fill_driver(bot: SmcScalperBot, paper) -> None:
    original_step = bot.step

    def step(now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        for t in bot.manager.active():
            try:
                m1 = bot.data.ohlcv(t.symbol, "1m", 3, now)
                if len(m1):
                    last = m1.iloc[-1]
                    paper.process_candle(t.symbol, float(last["high"]), float(last["low"]), now)
            except Exception:
                log.exception("paper fill driver failed for %s", t.symbol)
        original_step(now)

    bot.step = step  # type: ignore[assignment]
