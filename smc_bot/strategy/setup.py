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

from datetime import datetime, timedelta, timezone

import pandas as pd

from ..config import AnalysisConfig
from ..indicators import atr as atr_indicator
from ..models import Bias, LiquidityLevel, Side, Signal
from ..smc.displacement import detect_displacement_mss
from ..smc.liquidity import build_liquidity_map, levels_above, levels_below
from ..smc.structure import global_bias
from ..smc.sweep import detect_sweep
from ..smc.zones import select_zone


class SetupEngine:
    def __init__(self, cfg: AnalysisConfig):
        self.cfg = cfg

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

        bias = global_bias(h4, h1, cfg.swing_left, cfg.swing_right)
        if bias is Bias.NEUTRAL:
            return None
        side = Side.LONG if bias is Bias.BULLISH else Side.SHORT

        levels = build_liquidity_map(m15, now, cfg)
        if not levels:
            return None

        for tf_name, df in (("5m", m5), ("1m", m1)):
            if df is None or len(df) < cfg.atr_period + 10:
                continue
            sig = self._evaluate_tf(symbol, side, levels, df, tf_name, now)
            if sig is not None:
                sig.meta["bias"] = bias.value
                return sig
        return None

    # ------------------------------------------------------------------ #
    def _evaluate_tf(
        self,
        symbol: str,
        side: Side,
        levels: list[LiquidityLevel],
        df: pd.DataFrame,
        tf_name: str,
        now: datetime,
    ) -> Signal | None:
        cfg = self.cfg
        atr_s = atr_indicator(df, cfg.atr_period)
        atr_now = float(atr_s.iloc[-1])
        if atr_now <= 0:
            return None

        sweep = detect_sweep(df, levels, side, cfg.sweep_lookback, cfg.sweep_reclaim_within)
        if sweep is None:
            return None

        mss = detect_displacement_mss(
            df, sweep, atr_s, side,
            cfg.displacement_atr_mult, cfg.mss_max_candles_after_sweep,
            cfg.swing_left, cfg.swing_right,
        )
        if mss is None:
            return None

        zone = select_zone(df, mss, cfg.fvg_min_atr_mult * atr_now)
        if zone is None:
            return None

        entry = zone.entry_price(cfg.entry_zone_ratio)
        last_close = float(df["close"].iloc[-1])
        # we want a *retracement* into the zone: price must still be beyond it
        if side is Side.LONG and last_close <= entry:
            return None
        if side is Side.SHORT and last_close >= entry:
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
