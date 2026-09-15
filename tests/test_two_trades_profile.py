from datetime import timedelta

import pytest

from smc_bot.config import AnalysisConfig, RiskConfig, SessionWindow, load_config
from smc_bot.models import LiqKind, LiquidityLevel
from smc_bot.risk.filters import TradeGovernor
from smc_bot.strategy.setup import SetupEngine
from tests.helpers import DAY0, trending
from tests.test_setup import NOW, m15_two_days, m5_scenario


def test_profile_loads_with_single_2r_target():
    cfg = load_config("profiles/two_trades_rr2.json")
    assert cfg.analysis.tp1_share == 0.0 and cfg.analysis.tp2_fixed_rr == 2.0
    assert cfg.risk.max_trades_per_day == 2 and cfg.risk.max_trades_per_window == 1


def test_one_trade_per_window():
    windows = [SessionWindow("london", 7, 10), SessionWindow("newyork", 12, 16)]
    g = TradeGovernor(RiskConfig(max_trades_per_day=2, max_trades_per_window=1), windows)
    london = DAY0 + timedelta(hours=8)
    ny = DAY0 + timedelta(hours=13)
    assert g.can_trade("A", london, 10_000)[0]
    g.register_open(london, 10_000)
    assert not g.can_trade("B", london + timedelta(minutes=30), 10_000)[0]   # London used up
    assert g.can_trade("B", ny, 10_000)[0]                                    # NY still free
    g.register_open(ny, 10_000)
    assert not g.can_trade("C", ny + timedelta(minutes=30), 10_000)[0]
    g2 = TradeGovernor.from_dict(RiskConfig(max_trades_per_window=1), g.to_dict(), windows)
    assert g2.trades_by_window == {"london": 1, "newyork": 1}


def test_clear_path_rejects_liquidity_before_target():
    h4 = trending(DAY0 - timedelta(days=8), 240, drift=0.5)
    h1 = trending(DAY0 - timedelta(days=2), 60, drift=0.3)
    # asia high 104.5 sits ~1.7R above the entry (~102.1, risk ~1.45) -> blocks a 2R path
    eng = SetupEngine(AnalysisConfig(min_clear_path_rr=1.8, tp1_share=0.0, tp2_fixed_rr=2.0))
    assert eng.evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW) is None
    assert eng.funnel["5m:liquidity_in_path"] == 1
    eng = SetupEngine(AnalysisConfig(min_clear_path_rr=1.0, tp1_share=0.0, tp2_fixed_rr=2.0))
    sig = eng.evaluate("T", h4, h1, m15_two_days(), m5_scenario(), None, NOW)
    assert sig is not None and sig.rr2 == pytest.approx(2.0)
