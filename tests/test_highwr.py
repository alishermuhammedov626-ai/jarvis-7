import numpy as np
import pandas as pd
import pytest

from halalbot import synthetic
from halalbot.futures_backtest import FSignals, FuturesConfig, run_futures
from halalbot.grid_backtest import GridConfig, run_grid
from halalbot.strategy_zoo import HIGHWR


class LimitFixed:
    name = "limit_fixed"
    def __init__(self, i, limit, ttl=5): self.i, self.limit, self.ttl = i, limit, ttl
    def fsignals(self, df):
        n = len(df); z = np.zeros(n, bool); lg = z.copy(); lg[self.i] = True
        lim = np.full(n, np.nan); lim[self.i] = self.limit
        return FSignals(lg, z, np.full(n, 5.0), np.full(n, np.nan), z, z, limit_price=lim, limit_ttl=self.ttl)


def chart(prices):
    idx = pd.date_range("2025-01-01", periods=len(prices), freq="15min", tz="UTC")
    p = np.array(prices, float)
    return pd.DataFrame({"open": p, "high": p + 0.5, "low": p - 0.5, "close": p}, index=idx)


def test_limit_fills_only_when_touched_and_expires():
    df = chart([100] * 20)
    cfg = FuturesConfig(taker_fee=0, maker_fee=0, slippage=0, funding_rate_8h=0)
    r = run_futures(df, LimitFixed(2, limit=98.0, ttl=5), cfg)      # low = 99.5 -> hech qachon tegmaydi
    assert len(r.trades) == 0
    df2 = chart([100] * 5 + [98] + [100] * 14)                        # 6-shamda low 97.5 <= 98
    r2 = run_futures(df2, LimitFixed(2, limit=98.0, ttl=5), cfg)
    assert len(r2.trades) == 1 and r2.trades[0].entry_price == pytest.approx(98.0)
    r3 = run_futures(chart([100] * 10 + [98] + [100] * 9), LimitFixed(2, limit=98.0, ttl=3), cfg)   # muddati o'tgan
    assert len(r3.trades) == 0


def test_partial_tp_breakeven_turns_loss_into_zero():
    # 100 -> 103 (partial 1R=+2 tegadi) -> 100.4 (low 99.9: breakeven stop 100 da yopiladi) -> 97
    df = chart([100] * 3 + [103] * 2 + [100.4] + [97] * 4)
    class S:
        name = "s"
        def fsignals(self, d):
            n = len(d); z = np.zeros(n, bool); lg = z.copy(); lg[1] = True
            return FSignals(lg, z, np.full(n, 2.0), np.full(n, 6.0), z, z)
    base = FuturesConfig(taker_fee=0, slippage=0, funding_rate_8h=0, risk_per_trade=1.0, leverage=1)
    r0 = run_futures(df, S(), base)
    assert r0.trades[0].reason == "SL" and r0.trades[0].pnl < 0
    r1 = run_futures(df, S(), FuturesConfig(**{**base.__dict__, "partial_tp_r": 1.0, "partial_frac": 0.5}))
    t = r1.trades[0]
    assert t.reason == "SL" and t.pnl > 0            # 50% +2 da yopildi, qolgani 100 da (breakeven) -> jami musbat
    assert t.pnl == pytest.approx(0.5 * 10 * 2, rel=1e-6)   # qty=10 (1000/100), yarmi x 2 foyda


def test_grid_profits_in_perfect_range_and_loses_on_breakout():
    n = 96 * 6
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    t = np.arange(n)
    p = 100 + 3 * np.sin(t / 6.0)                     # mukammal tebranish 97..103
    rng = pd.DataFrame({"open": p, "high": p + 0.2, "low": p - 0.2, "close": p}, index=idx)
    cfg = GridConfig(funding_rate_8h=0, lookback=96, recenter_bars=96, sl_buffer_atr=3.0)
    r = run_grid(rng, cfg); m = r.metrics(6)
    assert m["trades"] > 20 and m["win_rate_pct"] > 80 and m["return_pct"] > 0
    p2 = p.copy(); p2[300:] = 130.0                   # kuchli breakout
    br = pd.DataFrame({"open": p2, "high": p2 + 0.2, "low": p2 - 0.2, "close": p2}, index=idx)
    r2 = run_grid(br, cfg)
    assert r2.sl_events >= 1


@pytest.mark.parametrize("Zc", [z for z in HIGHWR if not getattr(z, "is_grid", False)], ids=lambda z: z.name)
def test_highwr_no_lookahead(Zc):
    df = synthetic.generate("regime", days=20, seed=42)
    full = Zc().fsignals(df)
    for cut in (1500, 1543, 1601, 1799, 1830):
        part = Zc().fsignals(df.iloc[:cut]); i = cut - 1
        assert bool(full.long_entry[i]) == bool(part.long_entry[i]), f"{Zc.name} long[{i}]"
        assert bool(full.short_entry[i]) == bool(part.short_entry[i]), f"{Zc.name} short[{i}]"
        if full.long_entry[i] or full.short_entry[i]:
            assert np.isclose(full.sl_dist[i], part.sl_dist[i]) and np.isclose(full.tp_dist[i], part.tp_dist[i])
            if full.limit_price is not None:
                assert np.isclose(full.limit_price[i], part.limit_price[i])


def test_highwr_produce_trades():
    df = synthetic.generate("regime", days=60, seed=5)
    from halalbot.strategy_zoo import run_any
    for Zc in HIGHWR:
        r = run_any(df, Zc, FuturesConfig())
        assert r.metrics(60)["trades"] > 0, Zc.name
