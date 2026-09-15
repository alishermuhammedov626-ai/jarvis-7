"""Confluence engine: turns the top-down analysis into a concrete Signal.

Pipeline (every rule must pass):
  1. H4 (+H1) bias           -> direction
  2. M15 liquidity map       -> levels
  3. M5 (fallback M1) sweep  -> liquidity taken
  4. Displacement + MSS      -> intent confirmed
  5. FVG (fallback OB)       -> entry zone
  6. SL / TP1 / TP2 with R:R validation
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd

from ..config import AnalysisConfig
from ..indicators import atr as atr_indicator
from ..models import Bias, LiquidityLevel, Side, Signal
from ..smc.zones import zone_still_valid
from ..smc.displacement import detect_displacement_mss
from ..smc.liquidity import build_liquidity_map, levels_above, levels_below
from ..smc.structure import global_bias
from ..smc.sweep import detect_sweep
from ..smc.zones import select_zone


class SetupEngine:
    def __init__(self, cfg: AnalysisConfig):
        self.cfg = cfg
        # HTF results only change when a new HTF candle closes -> memoise
        self._bias_cache: dict[str, tuple[tuple, Bias]] = {}
        self._levels_cache: dict[str, tuple[tuple, list[LiquidityLevel]]] = {}
        # how many evaluations stopped at each stage (diagnostics for tuning)
        self.funnel: Counter[str] = Counter()

    # ------------------------------------------------------------------ #
    def _in_trade_window(self, now: datetime) -> bool:
        if not self.cfg.trade_windows:
            return True
        h = now.hour
        return any(w.start_hour <= h < w.end_hour for w in self.cfg.trade_windows)

    def _cached_bias(self, symbol: str, h4: pd.DataFrame, h1: pd.DataFrame) -> Bias:
        key = (h4.index[-1] if len(h4) else None, h1.index[-1] if len(h1) else None)
        hit = self._bias_cache.get(symbol)
        if hit and hit[0] == key:
            return hit[1]
        bias = global_bias(h4, h1, self.cfg.swing_left, self.cfg.swing_right, self.cfg.require_h1_confirm)
        self._bias_cache[symbol] = (key, bias)
        return bias

    def _cached_levels(self, symbol: str, m15: pd.DataFrame, now: datetime) -> list[LiquidityLevel]:
        # session windows depend on the hour, PDH/PDL on the date
        key = (m15.index[-1] if len(m15) else None, now.date(), now.hour)
        hit = self._levels_cache.get(symbol)
        if hit and hit[0] == key:
            return hit[1]
        levels = build_liquidity_map(m15, now, self.cfg)
        self._levels_cache[symbol] = (key, levels)
        return levels

    # ------------------------------------------------------------------ #
    def evaluate(
        self,
        symbol: str,
        h4: pd.DataFrame,
        h1: pd.DataFrame,
        m15: pd.DataFrame,
        m5: pd.DataFrame,
        m1: pd.DataFrame | None,
        now: datetime | None = None,
    ) -> Signal | None:
        cfg = self.cfg
        now = now or datetime.now(timezone.utc)

        if not self._in_trade_window(now):
            self.funnel["outside_trade_window"] += 1
            return None

        bias = self._cached_bias(symbol, h4, h1)
        if bias is Bias.NEUTRAL:
            self.funnel["bias_neutral"] += 1
            return None
        side = Side.LONG if bias is Bias.BULLISH else Side.SHORT

        levels = self._cached_levels(symbol, m15, now)
        if cfg.require_major_sweep:
            levels_for_sweep = [lv for lv in levels if lv.is_major]
        else:
            levels_for_sweep = levels
        if not levels_for_sweep:
            self.funnel["no_levels"] += 1
            return None

        for tf_name, df in (("5m", m5), ("1m", m1)):
            if df is None or len(df) < cfg.atr_period + 10:
                continue
            sig = self._evaluate_tf(symbol, side, levels, levels_for_sweep, df, tf_name, now)
            if sig is not None:
                if cfg.premium_discount_filter and not self._in_discount_or_premium(sig, h1):
                    self.funnel[f"{tf_name}:premium_discount"] += 1
                    continue
                sig.meta["bias"] = bias.value
                self.funnel["signal"] += 1
                return sig
        return None

    def _in_discount_or_premium(self, sig: Signal, h1: pd.DataFrame) -> bool:
        """LONG entries must sit in the lower half of the recent H1 range,
        SHORT entries in the upper half (buy cheap / sell expensive)."""
        n = self.cfg.dealing_range_candles
        if len(h1) < 2:
            return True
        window = h1.iloc[-n:]
        hi, lo = float(window["high"].max()), float(window["low"].min())
        if hi <= lo:
            return True
        mid = (hi + lo) / 2.0
        sig.meta["dealing_range"] = (lo, hi)
        return sig.entry <= mid if sig.side is Side.LONG else sig.entry >= mid

    # ------------------------------------------------------------------ #
    def _evaluate_tf(
        self,
        symbol: str,
        side: Side,
        levels: list[LiquidityLevel],
        levels_for_sweep: list[LiquidityLevel],
        df: pd.DataFrame,
        tf_name: str,
        now: datetime,
    ) -> Signal | None:
        cfg = self.cfg
        atr_s = atr_indicator(df, cfg.atr_period)
        atr_now = float(atr_s.iloc[-1])
        if atr_now <= 0:
            return None

        sweep = detect_sweep(df, levels_for_sweep, side, cfg.sweep_lookback,
                             cfg.sweep_reclaim_within, cfg.min_sweep_depth_atr * atr_now)
        if sweep is None:
            self.funnel[f"{tf_name}:no_sweep"] += 1
            return None

        mss = detect_displacement_mss(
            df, sweep, atr_s, side,
            cfg.displacement_atr_mult, cfg.mss_max_candles_after_sweep,
            cfg.swing_left, cfg.swing_right,
        )
        if mss is None:
            self.funnel[f"{tf_name}:no_displacement_mss"] += 1
            return None
        if len(df) - 1 - mss.idx > cfg.max_setup_age_candles:
            self.funnel[f"{tf_name}:setup_stale"] += 1
            return None   # stale: the retracement window has most likely passed

        zone = select_zone(df, mss, cfg.fvg_min_atr_mult * atr_now, cfg.allow_ob_fallback)
        if zone is None:
            self.funnel[f"{tf_name}:no_zone"] += 1
            return None

        entry = zone.entry_price(cfg.entry_zone_ratio)
        last_close = float(df["close"].iloc[-1])
        # we want a *retracement* into the zone: price must still be beyond it
        if (side is Side.LONG and last_close <= entry) or (side is Side.SHORT and last_close >= entry):
            self.funnel[f"{tf_name}:already_retraced"] += 1
            return None

        buffer = cfg.sl_atr_buffer * atr_now
        stop_loss = zone.low - buffer if side is Side.LONG else zone.high + buffer
        risk = abs(entry - stop_loss)
        if risk <= 0:
            return None

        tp1, tp2, tp_meta = self._targets(side, entry, risk, levels)
        if tp1 is None or tp2 is None:
            return None

        sig = Signal(
            symbol=symbol,
            side=side,
            entry=entry,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            atr=atr_now,
            zone=zone,
            sweep=sweep,
            mss=mss,
            created_at=now,
            expires_at=now + timedelta(minutes=cfg.entry_ttl_minutes),
            timeframe=tf_name,
            meta=tp_meta,
        )
        if sig.rr1 < cfg.min_rr_tp1 or sig.rr2 < cfg.min_rr_tp2:
            self.funnel[f"{tf_name}:rr_too_low"] += 1
            return None
        return sig

    # ------------------------------------------------------------------ #
    def _targets(self, side: Side, entry: float, risk: float, levels: list[LiquidityLevel]):
        """TP1 = nearest opposing liquidity with R in [min_rr_tp1, tp2_fixed_rr),
              otherwise a fixed ``tp1_fallback_rr``.
        TP2 = next *major* opposing liquidity beyond TP1 with R in
              [min_rr_tp2, tp2_max_rr], otherwise fixed ``tp2_fixed_rr``.
        TP2 is always strictly beyond TP1."""
        cfg = self.cfg
        opposing = levels_above(levels, entry) if side is Side.LONG else levels_below(levels, entry)
        meta: dict = {}

        def rr_of(p: float) -> float:
            return abs(p - entry) / risk

        tp1 = None
        if cfg.tp1_mode == "fixed":
            tp1 = entry + side.sign * cfg.tp1_fixed_rr * risk
            meta["tp1_source"] = f"fixed_{cfg.tp1_fixed_rr:g}R"
        else:
            for lv in opposing:
                r = rr_of(lv.price)
                if r < cfg.min_rr_tp1:
                    continue          # too close: would be swept before paying
                if r >= cfg.tp2_fixed_rr:
                    break             # nearest liquidity is already a TP2-sized move
                tp1, meta["tp1_source"] = lv.price, lv.describe()
                break
        if tp1 is None:
            tp1 = entry + side.sign * cfg.tp1_fallback_rr * risk
            meta["tp1_source"] = f"fixed_{cfg.tp1_fallback_rr:g}R"
        rr1 = rr_of(tp1)

        tp2 = None
        for lv in opposing:
            if not lv.is_major:
                continue
            r = rr_of(lv.price)
            if r > rr1 and cfg.min_rr_tp2 <= r <= cfg.tp2_max_rr:
                tp2, meta["tp2_source"] = lv.price, lv.describe()
                break
        if tp2 is None or rr_of(tp2) <= rr1:
            r2 = max(cfg.tp2_fixed_rr, rr1 + 1.0)
            tp2 = entry + side.sign * r2 * risk
            meta["tp2_source"] = f"fixed_{r2:g}R"
        return tp1, tp2, meta
