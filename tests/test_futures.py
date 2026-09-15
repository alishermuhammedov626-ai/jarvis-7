import numpy as np
import pandas as pd
import pytest

from halalbot import synthetic
from halalbot.futures_backtest import FSignals, FuturesConfig, run_futures
from halalbot.strategy_zoo import ZOO


class Fixed:
    """Test strategiyasi: berilgan indeksda long/short kirish, SL/TP masofasi sobit."""
    name = "fixed"
    def __init__(self, i, side, sl, tp=np.nan, time_stop=10**9):
        self.i, self.side, self.sl, self.tp, self.ts = i, side, sl, tp, time_stop
    def fsignals(self, df):
        n = len(df); z = np.zeros(n, bool); lg = z.copy(); sh = z.copy()
        (lg if self.side > 0 else sh)[self.i] = True
        return FSignals(lg, sh, np.full(n, self.sl), np.full(n, self.tp), z, z, time_stop=self.ts)


def flat_chart(n=200, px=100.0):
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    p = np.full(n, px)
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p}, index=idx)


def test_short_profits_when_price_falls():
    df = flat_chart(); df.loc[df.index[50:], ["open", "high", "low", "close"]] = 90.0
    r = run_futures(df, Fixed(10, -1, sl=50.0), FuturesConfig(leverage=1, taker_fee=0, slippage=0, funding_rate_8h=0, risk_per_trade=1.0))
    assert len(r.trades) == 1 and r.trades[0].side == "SHORT" and r.trades[0].pnl > 0
    assert r.equity_curve.iloc[-1] == pytest.approx(1100.0)


def test_long_loses_when_price_falls():
    df = flat_chart(); df.loc[df.index[50:], ["open", "high", "low", "close"]] = 90.0
    r = run_futures(df, Fixed(10, +1, sl=50.0), FuturesConfig(leverage=1, taker_fee=0, slippage=0, funding_rate_8h=0, risk_per_trade=1.0))
    assert r.equity_curve.iloc[-1] == pytest.approx(900.0)


def test_liquidation_at_high_leverage():
    df = flat_chart(); df.loc[df.index[50:], ["open", "high", "low", "close"]] = 90.0   # -10% > 1/20
    r = run_futures(df, Fixed(10, +1, sl=50.0), FuturesConfig(leverage=20, taker_fee=0, slippage=0, funding_rate_8h=0, risk_per_trade=1.0))
    assert r.trades[0].reason == "LIQ"
    assert r.equity_curve.iloc[-1] == pytest.approx(900.0)   # margin (100) yo'qoldi, hisob qoldi
    r2 = run_futures(df, Fixed(10, +1, sl=np.inf), FuturesConfig(leverage=20, taker_fee=0, slippage=0, funding_rate_8h=0, risk_per_trade=1.0))
    assert r2.liquidated and r2.equity_curve.iloc[-1] == 0.0   # butun hisob likvidatsiya


def test_funding_direction():
    df = flat_chart(n=96 * 2)
    cfg = FuturesConfig(leverage=1, taker_fee=0, slippage=0, funding_rate_8h=0.001, risk_per_trade=1.0)
    rl = run_futures(df, Fixed(1, +1, sl=50.0), cfg)
    rs = run_futures(df, Fixed(1, -1, sl=50.0), cfg)
    assert rl.funding_paid > 0 and rs.funding_paid < 0
    assert rl.equity_curve.iloc[-1] < 1000 < rs.equity_curve.iloc[-1]


def test_notional_capped_by_leverage():
    df = flat_chart()
    r = run_futures(df, Fixed(10, +1, sl=0.01), FuturesConfig(leverage=3, risk_per_trade=1.0, taker_fee=0, slippage=0))
    assert r.trades[0].notional <= 1000 * 3 + 1e-6


def test_max_trades_per_day_futures():
    df = synthetic.generate("regime", days=20, seed=3)
    for Zc in ZOO[:10]:
        r = run_futures(df, Zc(), FuturesConfig(max_trades_per_day=3))
        per_day = pd.Series([t.entry_time.date() for t in r.trades]).value_counts()
        assert per_day.empty or per_day.max() <= 3


@pytest.mark.parametrize("Zc", [z for z in ZOO if not getattr(z, "is_grid", False)], ids=lambda z: z.name)
def test_zoo_no_lookahead(Zc):
    if Zc.name == "control_random_entry":
        pytest.skip("tasodifiy nazorat")
    df = synthetic.generate("regime", days=20, seed=42)
    full = Zc().fsignals(df)
    for cut in (1500, 1543, 1601, 1799, 1830):
        part = Zc().fsignals(df.iloc[:cut]); i = cut - 1
        assert bool(full.long_entry[i]) == bool(part.long_entry[i]), f"{Zc.name} long[{i}]"
        assert bool(full.short_entry[i]) == bool(part.short_entry[i]), f"{Zc.name} short[{i}]"
        assert bool(full.exit_long[i]) == bool(part.exit_long[i]), f"{Zc.name} exit_long[{i}]"
        if full.long_entry[i] or full.short_entry[i]:
            assert np.isclose(full.sl_dist[i], part.sl_dist[i]), f"{Zc.name} sl[{i}]"
