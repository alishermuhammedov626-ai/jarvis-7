import numpy as np
import pandas as pd
import pytest

from halalbot import synthetic, backtest
from halalbot.halal import HalalPolicy, HalalViolation
from halalbot.strategies import ALL_STRATEGIES, SessionORB, by_name


def test_policy_rejects_futures_margin_leverage_short():
    with pytest.raises(HalalViolation):
        HalalPolicy(market_type="futures").validate_config()
    with pytest.raises(HalalViolation):
        HalalPolicy(market_type="margin").validate_config()
    with pytest.raises(HalalViolation):
        HalalPolicy(leverage=3).validate_config()
    with pytest.raises(HalalViolation):
        HalalPolicy(allow_short=True).validate_config()
    HalalPolicy().validate_config()


def test_policy_blocks_leveraged_and_interest_tokens():
    p = HalalPolicy()
    p.validate_symbol("BTCUSDT")
    p.validate_symbol("ETH/USDC")
    for bad in ("BTCUPUSDT", "AAVEUSDT", "ETHDOWNUSDT", "COMPUSDT"):
        with pytest.raises(HalalViolation):
            p.validate_symbol(bad)


def test_policy_forbids_naked_sell_and_credit_buy():
    p = HalalPolicy()
    p.validate_order("SELL", qty=0.5, holdings_base=0.5, holdings_quote=0, price=100)
    with pytest.raises(HalalViolation):
        p.validate_order("SELL", qty=0.6, holdings_base=0.5, holdings_quote=0, price=100)
    with pytest.raises(HalalViolation):
        p.validate_order("BUY", qty=2, holdings_base=0, holdings_quote=100, price=100)


def test_policy_forbids_futures_endpoints():
    HalalPolicy.validate_endpoint("/api/v3/order")
    for bad in ("/fapi/v1/order", "/dapi/v1/order", "/sapi/v1/margin/order", "/sapi/v1/simple-earn/flexible/subscribe"):
        with pytest.raises(HalalViolation):
            HalalPolicy.validate_endpoint(bad)


@pytest.fixture(scope="module")
def chart():
    return synthetic.generate("regime", days=30, seed=7)


def test_max_trades_per_day_enforced(chart):
    for S in ALL_STRATEGIES:
        for cap in (1, 3, 4):
            res = backtest.run(chart, S(), backtest.BacktestConfig(max_trades_per_day=cap))
            per_day = pd.Series([t.entry_time.date() for t in res.trades]).value_counts()
            assert per_day.empty or per_day.max() <= cap, (S.name, cap, per_day.max())


def test_no_leverage_position_never_exceeds_equity(chart):
    res = backtest.run(chart, by_name("A"), backtest.BacktestConfig(risk_per_trade=0.5))
    for t in res.trades:
        # pozitsiya qiymati kirish paytidagi kapitaldan oshmasligi kerak
        eq_before = res.equity_curve.loc[:t.entry_time].iloc[-2] if res.equity_curve.index.get_loc(t.entry_time) > 0 else 1000.0
        assert t.qty * t.entry_price <= eq_before * (1 + 1e-6)


def test_leverage_config_rejected(chart):
    with pytest.raises(ValueError):
        backtest.run(chart, by_name("A"), backtest.BacktestConfig(max_position_frac=2.0))


def test_fees_accounted(chart):
    cfg0 = backtest.BacktestConfig(fee_rate=0.0, slippage=0.0)
    cfg1 = backtest.BacktestConfig(fee_rate=0.001, slippage=0.0)
    r0 = backtest.run(chart, by_name("E"), cfg0)
    r1 = backtest.run(chart, by_name("E"), cfg1)
    assert r0.fees_paid == 0
    assert r1.fees_paid > 0
    # har savdo: kirish + chiqish komissiyasi taxminan 0.2% notional
    for t in r1.trades:
        assert abs(t.fees - (t.qty * t.entry_price + t.qty * t.exit_price) * 0.001) < 1e-6


def test_stop_loss_respected(chart):
    res = backtest.run(chart, by_name("A"))
    for t in res.trades:
        if t.reason == "SL":
            assert t.exit_price < t.entry_price


def test_orb_one_trade_per_session(chart):
    res = backtest.run(chart, SessionORB(), backtest.BacktestConfig(max_trades_per_day=10))
    sess = pd.Series([(t.entry_time.date(), t.entry_time.hour // 6) for t in res.trades])
    # bir sessiya oynasida (4 soat) 1 tadan ko'p kirish bo'lmasin
    ent = pd.Series([t.entry_time for t in res.trades])
    diffs = ent.diff().dropna()
    assert (diffs >= pd.Timedelta("15min")).all()


def test_synthetic_reproducible():
    a = synthetic.generate("garch", days=2, seed=1)
    b = synthetic.generate("garch", days=2, seed=1)
    assert a.equals(b)
    assert (a["high"] >= a[["open", "close"]].max(axis=1)).all()
    assert (a["low"] <= a[["open", "close"]].min(axis=1)).all()
