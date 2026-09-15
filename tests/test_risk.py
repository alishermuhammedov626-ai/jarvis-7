from datetime import timedelta

import pytest

from smc_bot.config import MarketFilterConfig, RiskConfig
from smc_bot.models import MarketQuality, MarketSpec, Side
from smc_bot.risk.filters import TradeGovernor, market_filter, rank_candidates
from smc_bot.risk.sizing import position_size, split_tp_quantities
from tests.helpers import DAY0


def test_one_percent_risk():
    spec = MarketSpec("X", amount_step=1.0, price_step=1e-5, min_amount=1, min_notional=5)
    qty = position_size(10_000, 1.0, entry=0.10, stop_loss=0.095, spec=spec, leverage=5)
    assert qty * 0.005 == pytest.approx(100, rel=0.01)


def test_cost_aware_risk_never_exceeds_one_percent():
    spec = MarketSpec("X", amount_step=1.0, price_step=1e-5, min_amount=1, min_notional=5)
    entry, sl = 0.10, 0.0998                      # 0.2% stop, typical for scalps
    qty = position_size(10_000, 1.0, entry, sl, spec, leverage=10, cost_bps=16)
    worst = qty * (entry - sl) + qty * entry * 16 / 10_000
    assert worst <= 100 + 1e-6 and worst > 95


def test_margin_cap_and_min_notional():
    spec = MarketSpec("X", 1.0, 1e-5, 1, 5, max_leverage=20)
    # tiny risk distance -> huge notional -> capped by margin
    qty = position_size(1_000, 1.0, 0.10, 0.0999, spec, leverage=5)
    assert qty * 0.10 <= 1_000 * 0.95 * 5 + 1e-6
    assert position_size(10, 1.0, 100.0, 99.0, spec, 5) == 0.0   # below min notional


def test_split_tp():
    spec = MarketSpec("X", 1.0, 1e-5, 1, 5)
    assert split_tp_quantities(101, spec) == (50, 51)
    assert split_tp_quantities(1, spec) == (0.0, 1)


def test_market_filter():
    cfg = MarketFilterConfig()
    good = MarketQuality("A", 0.1000, 0.10002, 1e8, 1e6)
    wide = MarketQuality("B", 0.1000, 0.1010, 1e8, 1e6)
    thin = MarketQuality("C", 0.1000, 0.10002, 1e6, 1e6)
    assert market_filter(good, cfg)[0]
    assert not market_filter(wide, cfg)[0]
    assert not market_filter(thin, cfg)[0]


class _Sig:
    def __init__(self, symbol, rr2=3.0):
        self.symbol, self.rr2 = symbol, rr2


def test_rank_candidates_prefers_volume_and_tight_spread():
    q = {
        "DOGE": MarketQuality("DOGE", 0.1, 0.10001, 5e8, 1e7),
        "PEPE": MarketQuality("PEPE", 0.1, 0.10003, 3e8, 1e7),
        "FLOKI": MarketQuality("FLOKI", 0.1, 0.10005, 6e7, 1e6),
    }
    sigs = [_Sig("FLOKI"), _Sig("PEPE"), _Sig("DOGE")]
    chosen = rank_candidates(sigs, q, slots=2)
    assert [s.symbol for s in chosen] == ["DOGE", "PEPE"]
    assert rank_candidates(sigs, q, slots=0) == []


def test_governor_quota_cooldown_and_loss_limit():
    cfg = RiskConfig(max_trades_per_day=2, daily_loss_limit_pct=3.0, symbol_cooldown_minutes=60)
    g = TradeGovernor(cfg)
    now = DAY0
    assert g.can_trade("A", now, 10_000)[0]
    g.register_open(now, 10_000); g.register_open(now, 10_000)
    assert not g.can_trade("A", now, 10_000)[0]
    # new day resets the counter
    now2 = now + timedelta(days=1)
    assert g.can_trade("A", now2, 10_000)[0]
    g.register_close("A", -10.0, now2, 9_990)
    assert not g.can_trade("A", now2 + timedelta(minutes=30), 9_990)[0]   # cooldown
    assert g.can_trade("A", now2 + timedelta(minutes=61), 9_990)[0]
    assert g.can_trade("B", now2, 9_990)[0]
    g.register_close("B", -340.0, now2, 9_650)
    assert not g.can_trade("B", now2 + timedelta(hours=2), 9_650)[0]      # -3.5% -> stop for the day
    now3 = now2 + timedelta(days=1)
    assert g.can_trade("B", now3, 9_650)[0]                               # new day resets
    # round-trip persistence
    g2 = TradeGovernor.from_dict(cfg, g.to_dict())
    assert g2.trades_today == g.trades_today and g2.last_close.keys() == g.last_close.keys()
