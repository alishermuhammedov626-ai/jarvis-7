from datetime import timedelta

import pandas as pd
import pytest

from smc_bot.config import AnalysisConfig
from smc_bot.models import Side
from smc_bot.strategy.confirm import check_confirmation
from smc_bot.strategy.setup import SetupEngine
from tests.helpers import DAY0, frame, trending
from tests.test_manager import _signal
from tests.test_setup import NOW, m15_two_days, m5_scenario


def _m1(rows, start=DAY0):
    return frame(rows, start, 1)


def test_confirmation_long_waits_touch_then_reaction():
    sig = _signal(Side.LONG)                       # zone 101..103
    armed = DAY0
    # 1) never touched -> wait
    m1 = _m1([(104, 104.5, 103.5, 104), (104, 104.3, 103.6, 104.1)])
    assert check_confirmation(m1, sig, armed)[0] == "wait"
    # 2) touched, still inside the zone -> wait
    m1 = _m1([(104, 104.5, 102.5, 102.8), (102.8, 102.9, 102.2, 102.5)])
    assert check_confirmation(m1, sig, armed)[0] == "wait"
    # 3) touched then bullish close above zone high and above previous high -> confirmed
    m1 = _m1([(104, 104.5, 102.5, 102.8), (102.8, 102.9, 102.2, 102.5), (102.5, 103.4, 102.4, 103.3)])
    status, px = check_confirmation(m1, sig, armed)
    assert status == "confirmed" and px == 103.3
    # 4) close through the far side -> invalid
    m1 = _m1([(104, 104.5, 102.5, 102.8), (102.8, 102.9, 100.5, 100.8)])
    assert check_confirmation(m1, sig, armed)[0] == "invalid"


def test_confirmation_short_and_armed_time_respected():
    sig = _signal(Side.SHORT)                      # zone 101..103, price below
    rows = [(101.0, 103.5, 100.9, 102.5), (102.5, 102.6, 100.5, 100.6)]
    m1 = _m1(rows)
    assert check_confirmation(m1, sig, DAY0)[0] == "confirmed"
    # armed after those candles -> they don't count
    assert check_confirmation(m1, sig, DAY0 + timedelta(minutes=5))[0] == "wait"


def test_premium_discount_filter():
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=0.5)
    cfg = AnalysisConfig(premium_discount_filter=True)
    # H1 range ~100..115 -> entry ~102 is in discount -> allowed
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3, base=100.0)
    assert SetupEngine(cfg).evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    # H1 range ~85..100 -> entry ~102 sits in premium -> LONG rejected
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3, base=85.0)
    eng = SetupEngine(cfg)
    assert eng.evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None
    assert eng.funnel["5m:premium_discount"] == 1


def test_rebase_targets_keeps_liquidity_moves_fixed():
    from smc_bot.bot import SmcScalperBot
    sig = _signal(Side.LONG)            # entry 102, sl 100.5 (risk 1.5), tp1 103.5 (1R), tp2 106.5 (3R)
    sig.meta = {"tp1_source": "asia_high@103.5", "tp2_source": "fixed_3R"}
    SmcScalperBot._rebase_targets(sig, 103.3)
    assert sig.entry == 103.3 and sig.stop_loss == 100.5
    assert sig.tp1 == 103.5                                    # liquidity target untouched
    assert sig.tp2 == pytest.approx(103.3 + 3 * (103.3 - 100.5))  # fixed 3R re-expressed
