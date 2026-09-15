from datetime import timedelta

import pytest

from smc_bot.config import AnalysisConfig, RiskConfig
from smc_bot.execution.exchange import PaperExchange
from smc_bot.execution.manager import PositionManager
from smc_bot.models import MSS, LiqKind, LiquidityLevel, MarketSpec, Side, Signal, Sweep, TradeState, Zone
from tests.helpers import DAY0

import pandas as pd


def _signal(side=Side.LONG):
    ts = pd.Timestamp(DAY0)
    lv = LiquidityLevel(100.0, LiqKind.PDL, ts, "PDL")
    zone = Zone("fvg", side, 101.0, 103.0, 1, ts)
    sweep = Sweep(lv, side, 0, 0, 99.5, ts)
    mss = MSS(side, 2, 102.0, 0, 1, ts)
    if side is Side.LONG:
        entry, sl, tp1, tp2 = 102.0, 100.5, 103.5, 106.5
    else:
        entry, sl, tp1, tp2 = 102.0, 103.5, 100.5, 97.5
    return Signal("X", side, entry, sl, tp1, tp2, 1.0, zone, sweep, mss, DAY0,
                  DAY0 + timedelta(minutes=60), "5m")


def _setup(side=Side.LONG):
    spec = MarketSpec("X", 1.0, 0.01, 1, 5)
    ex = PaperExchange(10_000, slippage_bps=0, fee_bps=0, specs={"X": spec})
    closed = []
    pm = PositionManager(ex, AnalysisConfig(trail_atr_mult=1.0, breakeven_buffer_bps=0),
                         RiskConfig(max_open_positions=2), on_close=closed.append, fee_bps=0)
    t = pm.submit(_signal(side), qty=100)
    return ex, pm, t, closed


def test_full_long_lifecycle_tp1_be_trailing_tp2():
    ex, pm, t, closed = _setup()
    now = DAY0
    assert t.state is TradeState.PENDING and pm.open_slots() == 1

    # price retraces into the FVG -> limled entry fills; SL + TP1 + TP2 placed
    ex.process_candle("X", 103.0, 101.9, now)
    pm.update(now)
    assert t.state is TradeState.OPEN
    assert {ex.orders[t.sl_order_id].kind, ex.orders[t.tp1_order_id].kind, ex.orders[t.tp2_order_id].kind} == {"stop", "tp"}
    assert ex.orders[t.tp1_order_id].qty == 50 and ex.orders[t.tp2_order_id].qty == 50

    # TP1 hit -> 50% closed, SL moved to break-even
    ex.process_candle("X", 103.6, 102.5, now)
    pm.update(now)
    assert t.state is TradeState.RUNNER
    assert t.remaining_qty == 50
    assert t.realized_pnl == pytest.approx(50 * 1.5)
    assert t.stop_loss == pytest.approx(102.0)

    # trailing: price at 105 with ATR 1 -> SL ratchets to 104, never loosened
    pm.update(now, {"X": 1.0}, {"X": 105.0})
    assert t.stop_loss == pytest.approx(104.0)
    pm.update(now, {"X": 1.0}, {"X": 104.2})
    assert t.stop_loss == pytest.approx(104.0)

    # TP2 hit -> flat
    ex.process_candle("X", 106.6, 105.0, now)
    pm.update(now)
    assert t.state is TradeState.CLOSED and t.close_reason == "tp2"
    assert t.realized_pnl == pytest.approx(50 * 1.5 + 50 * 4.5)
    assert ex.equity() == pytest.approx(10_000 + 300)
    assert closed and closed[0].id == t.id
    assert all(o.status != "open" for o in ex.orders.values())


def test_stop_loss_closes_everything():
    ex, pm, t, closed = _setup()
    ex.process_candle("X", 103.0, 101.9, DAY0)
    pm.update(DAY0)
    ex.process_candle("X", 102.5, 100.4, DAY0)      # stop-market SL at 100.5
    pm.update(DAY0)
    assert t.state is TradeState.CLOSED and t.close_reason == "stop_loss"
    assert t.realized_pnl == pytest.approx(-150)        # 1% of 10k? qty fixed at 100 here
    assert ex.orders[t.tp1_order_id].status == "canceled"


def test_pending_entry_expires():
    ex, pm, t, closed = _setup()
    pm.update(DAY0 + timedelta(minutes=61))
    assert t.state is TradeState.CANCELLED and t.close_reason == "entry expired"
    assert pm.open_slots() == 2


def test_short_lifecycle_breakeven():
    ex, pm, t, closed = _setup(Side.SHORT)
    ex.process_candle("X", 102.1, 101.0, DAY0)
    pm.update(DAY0)
    assert t.state is TradeState.OPEN
    ex.process_candle("X", 101.0, 100.4, DAY0)      # TP1 (100.5) hit
    pm.update(DAY0)
    assert t.state is TradeState.RUNNER and t.stop_loss == pytest.approx(102.0)
    ex.process_candle("X", 102.1, 101.0, DAY0)      # BE stop hit
    pm.update(DAY0)
    assert t.state is TradeState.CLOSED and t.close_reason == "trailing_stop"
    assert t.realized_pnl == pytest.approx(50 * 1.5)


def test_state_persistence_roundtrip(tmp_path):
    spec = MarketSpec("X", 1.0, 0.01, 1, 5)
    ex = PaperExchange(10_000, 0, 0, {"X": spec})
    path = tmp_path / "trades.json"
    pm = PositionManager(ex, AnalysisConfig(), RiskConfig(), state_path=path)
    t = pm.submit(_signal(), 10)
    pm2 = PositionManager(ex, AnalysisConfig(), RiskConfig(), state_path=path)
    assert t.id in pm2.trades and pm2.trades[t.id].state is TradeState.PENDING


def test_market_entry_opens_immediately_with_protection():
    spec = MarketSpec("X", 1.0, 0.01, 1, 5)
    ex = PaperExchange(10_000, slippage_bps=10, fee_bps=0, specs={"X": spec})
    pm = PositionManager(ex, AnalysisConfig(), RiskConfig(), fee_bps=0)
    t = pm.submit_market(_signal(), qty=100, price=103.3)
    assert t.state is TradeState.OPEN
    assert t.avg_entry == pytest.approx(103.3 * 1.001)
    assert ex.orders[t.sl_order_id].kind == "stop" and ex.orders[t.sl_order_id].price == 100.5
    assert ex.orders[t.tp1_order_id].qty == 50 and ex.orders[t.tp2_order_id].qty == 50
