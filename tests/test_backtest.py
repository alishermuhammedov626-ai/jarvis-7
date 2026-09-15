from datetime import timedelta

from smc_bot.backtest import run_backtest
from smc_bot.config import BotConfig
from smc_bot.data.feed import HistoricalDataSource, drop_unclosed, resample
from tests.helpers import DAY0, random_walk_1m


def test_resample_and_slicing():
    m1 = random_walk_1m(DAY0, days=1)
    src = HistoricalDataSource({"A": m1}, "1m")
    now = DAY0 + timedelta(hours=6, minutes=2)
    m5 = src.ohlcv("A", "5m", 50, now)
    assert len(m5) == 50
    assert m5.index[-1] == DAY0 + timedelta(hours=5, minutes=55)   # 06:00 candle not closed yet
    h1 = src.ohlcv("A", "1h", 10, now)
    assert h1.index[-1] == DAY0 + timedelta(hours=5)
    assert abs(h1["high"].iloc[-1] - m1[(m1.index >= h1.index[-1]) & (m1.index < now.replace(minute=0))]["high"].max()) < 1e-12


def test_drop_unclosed():
    m1 = random_walk_1m(DAY0, days=1)
    m15 = resample(m1, "15m")
    now = DAY0 + timedelta(hours=1, minutes=5)
    df = drop_unclosed(m15.iloc[:5], "15m", now)     # last candle opens 01:00 -> not closed
    assert df.index[-1] == DAY0 + timedelta(minutes=45)


def test_backtest_runs_end_to_end():
    cfg = BotConfig()
    cfg.analysis.candles_m1 = 120
    base = {"A": random_walk_1m(DAY0, days=3, seed=7), "B": random_walk_1m(DAY0, days=3, seed=11)}
    res = run_backtest(cfg, base, warmup_hours=30)
    assert set(res) >= {"trades", "win_rate", "profit_factor", "final_equity", "equity_curve"}
    assert len(res["equity_curve"]) > 0
    assert res["final_equity"] > 0
