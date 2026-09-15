"""Quality filters that trade frequency for win rate."""
from datetime import timedelta

import pytest

from smc_bot.config import AnalysisConfig, SessionWindow, load_config
from smc_bot.models import Bias, Side
from smc_bot.smc.structure import global_bias
from smc_bot.strategy.setup import SetupEngine
from tests.helpers import DAY0, ranging, trending
from tests.test_setup import NOW, m15_two_days, m5_scenario


def _htf():
    return (trending(DAY0 - timedelta(days=8), 240, drift=0.5),
            trending(DAY0 - timedelta(days=2), 60, drift=0.3))


def test_require_h1_confirm():
    h4 = trending(DAY0, 240, drift=0.5)
    assert global_bias(h4, ranging(DAY0, 60)) is Bias.BULLISH
    assert global_bias(h4, ranging(DAY0, 60), require_h1_confirm=True) is Bias.NEUTRAL


def test_baseline_signal_exists():
    h4, h1 = _htf()
    assert SetupEngine(AnalysisConfig()).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)


def test_trade_window_blocks_outside_hours():
    h4, h1 = _htf()
    cfg = AnalysisConfig(trade_windows=[SessionWindow("ny", 12, 17)])   # NOW is 10:00 UTC
    assert SetupEngine(cfg).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None
    cfg = AnalysisConfig(trade_windows=[SessionWindow("london", 7, 11)])
    assert SetupEngine(cfg).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)


def test_min_sweep_depth():
    h4, h1 = _htf()
    # sweep depth in the scenario: asia low 101.35 -> wick 99.5 = 1.85; ATR ~ 0.6
    assert SetupEngine(AnalysisConfig(min_sweep_depth_atr=0.5)).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    assert SetupEngine(AnalysisConfig(min_sweep_depth_atr=10.0)).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None


def test_max_setup_age():
    h4, h1 = _htf()
    # MSS at idx 27 of 30 -> age 2 candles
    assert SetupEngine(AnalysisConfig(max_setup_age_candles=2)).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    assert SetupEngine(AnalysisConfig(max_setup_age_candles=1)).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None


def test_require_major_sweep_only_uses_major_levels():
    h4, h1 = _htf()
    sig = SetupEngine(AnalysisConfig(require_major_sweep=True)).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    assert sig is not None and sig.sweep.level.is_major


def test_fixed_tp1_mode_and_share():
    h4, h1 = _htf()
    cfg = AnalysisConfig(tp1_mode="fixed", tp1_fixed_rr=1.0, tp1_share=0.6)
    sig = SetupEngine(cfg).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    assert sig is not None
    assert sig.rr1 == pytest.approx(1.0)
    assert sig.rr2 >= cfg.min_rr_tp2 and sig.rr2 > sig.rr1


def test_high_winrate_profile_loads():
    cfg = load_config("profiles/high_winrate.json")
    assert cfg.analysis.require_major_sweep and cfg.analysis.tp1_mode == "fixed"
    assert [w.name for w in cfg.analysis.trade_windows] == ["london", "newyork"]
    assert cfg.risk.risk_per_trade_pct == 1.0
