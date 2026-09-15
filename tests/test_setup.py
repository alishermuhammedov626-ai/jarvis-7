"""End-to-end confluence scenario: PDL sweep -> displacement -> MSS -> FVG -> LONG."""
from datetime import timedelta

import pytest

from smc_bot.config import AnalysisConfig
from smc_bot.indicators import atr
from smc_bot.models import Side
from smc_bot.smc.displacement import detect_displacement_mss
from smc_bot.smc.liquidity import build_liquidity_map
from smc_bot.smc.sweep import detect_sweep
from smc_bot.smc.zones import find_fvg, find_ob
from smc_bot.strategy.setup import SetupEngine
from tests.helpers import DAY0, frame, trending

NOW = DAY0 + timedelta(days=1, hours=10)


def m15_two_days():
    rows = []
    for i in range(96):                       # previous day 100..110
        c = 105 + 4 * ((i % 20) - 10) / 10
        rows.append((c, c + 0.3, c - 0.3, c))
    rows[10] = (104, 110.0, 103.5, 104)       # PDH 110
    rows[50] = (104, 104.5, 100.0, 104)       # PDL 100
    for i in range(40):                       # today 00:00 - 10:00
        c = 101.5 + (i % 2) * 0.1
        rows.append((c, c + 0.15, c - 0.15, c))
    rows[96 + 12] = (103, 104.5, 102.8, 103)  # asia high 104.5
    return frame(rows, DAY0, 15)


def m5_scenario():
    """30 candles 07:30-10:00: base ~101.5, swing high 102 at idx 20, sweep of
    PDL (100) at idx 26, displacement + MSS at idx 27 leaving an FVG."""
    rows = []
    for i in range(30):
        c = 101.3 + (i % 3) * 0.15
        rows.append((c, c + 0.15, c - 0.15, c + 0.05))
    rows[20] = (101.6, 102.0, 101.5, 101.9)       # swing high 102.0
    rows[21] = (101.9, 101.95, 101.6, 101.7)
    rows[22] = (101.7, 101.75, 101.4, 101.5)
    rows[23] = (101.5, 101.55, 101.2, 101.3)
    rows[24] = (101.3, 101.35, 101.0, 101.1)
    rows[25] = (101.1, 101.15, 100.8, 100.9)
    rows[26] = (100.9, 100.95, 99.5, 100.4)       # sweep below PDL, close back above
    rows[27] = (100.4, 103.6, 100.3, 103.5)       # displacement, breaks 102.0 -> MSS
    rows[28] = (103.5, 103.9, 103.2, 103.7)       # FVG: low 103.2 > high[26] 100.95
    rows[29] = (103.7, 103.8, 103.4, 103.6)
    return frame(rows, DAY0 + timedelta(days=1, hours=7, minutes=30), 5)


@pytest.fixture
def cfg():
    return AnalysisConfig()


def test_sweep_mss_and_zone(cfg):
    m15 = m15_two_days()
    m5 = m5_scenario()
    levels = build_liquidity_map(m15, NOW, cfg)
    sweep = detect_sweep(m5, levels, Side.LONG, cfg.sweep_lookback, cfg.sweep_reclaim_within)
    assert sweep is not None and sweep.extreme == 99.5 and sweep.reclaim_idx >= 26

    a = atr(m5, cfg.atr_period)
    mss = detect_displacement_mss(m5, sweep, a, Side.LONG, cfg.displacement_atr_mult,
                                  cfg.mss_max_candles_after_sweep)
    assert mss is not None
    assert mss.idx == 27 and mss.broken_level == 102.0 and mss.leg_start_idx == 26

    fvg = find_fvg(m5, mss)
    assert fvg is not None and fvg.kind == "fvg"
    assert fvg.low == pytest.approx(100.95) and fvg.high == pytest.approx(103.2)

    ob = find_ob(m5, mss)
    assert ob is not None and ob.kind == "ob" and ob.low == 99.5   # sweep candle is bearish


def test_engine_produces_valid_long(cfg):
    engine = SetupEngine(cfg)
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=0.5)
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3)
    m15, m5 = m15_two_days(), m5_scenario()

    sig = engine.evaluate("TEST", h4, h1, m15, m5, None, NOW)
    assert sig is not None
    assert sig.side is Side.LONG
    assert sig.zone.kind == "fvg"
    # entry = midpoint of the FVG, still below current price (retracement pending)
    assert sig.entry == pytest.approx((100.95 + 103.2) / 2)
    assert sig.entry < float(m5["close"].iloc[-1])
    # SL below FVG low with 0.5 ATR buffer
    assert sig.stop_loss == pytest.approx(100.95 - 0.5 * sig.atr)
    # TP1 = nearest buy-side liquidity (asia high), TP2 = 3R because PDH is too far
    assert sig.tp1 == 104.5
    assert sig.rr1 >= cfg.min_rr_tp1
    assert sig.rr2 == pytest.approx(cfg.tp2_fixed_rr)
    assert sig.meta["tp2_source"].startswith("fixed")
    assert sig.expires_at == NOW + timedelta(minutes=cfg.entry_ttl_minutes)


def test_engine_rejects_when_bias_bearish(cfg):
    engine = SetupEngine(cfg)
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=-0.5)
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=-0.3)
    assert engine.evaluate("TEST", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None


def test_engine_rejects_without_sweep(cfg):
    engine = SetupEngine(cfg)
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=0.5)
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3)
    # same impulse candles, but every low stays above the lowest M15 level
    # (asia low 101.35): no liquidity was taken, so no setup may be produced
    rows = []
    for i in range(30):
        c = 101.6 + (i % 3) * 0.15
        rows.append((c, c + 0.15, c - 0.15, c + 0.05))
    rows[27] = (101.7, 103.6, 101.6, 103.5)
    rows[28] = (103.5, 103.9, 103.2, 103.7)
    rows[29] = (103.7, 103.8, 103.4, 103.6)
    m5 = frame(rows, DAY0 + timedelta(days=1, hours=7, minutes=30), 5)
    assert engine.evaluate("TEST", h4, h1, m15_two_days(), m5, None, NOW) is None


def test_tp1_never_beyond_tp2(cfg):
    """If the nearest opposing liquidity is already >= 3R away, TP1 falls back
    to a fixed R and TP2 stays beyond it."""
    engine = SetupEngine(cfg)
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=0.5)
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3)
    m15 = m15_two_days()
    m15.iloc[96 + 12] = [103, 103.2, 102.8, 103, 1000.0]     # remove asia high -> next level is PDH (far)
    sig = engine.evaluate("TEST", h4, h1, m15, m5_scenario(), None, NOW)
    assert sig is not None
    assert sig.rr1 == pytest.approx(cfg.tp1_fallback_rr)
    assert sig.rr2 > sig.rr1 and sig.rr2 >= cfg.min_rr_tp2
    assert sig.meta["tp1_source"].startswith("fixed")
