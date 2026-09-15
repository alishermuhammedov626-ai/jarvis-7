from datetime import timedelta

from smc_bot.backtest import summarize
from smc_bot.config import BotConfig
from smc_bot.models import Side, Trade, TradeState
from smc_bot.optimize import SPACE, apply_params, optimize, sample
from tests.helpers import DAY0, random_walk_1m

import random


def _trade(pnl, risk=100.0, tp1=False, reason="stop_loss"):
    t = Trade("i", "X", Side.LONG, 1, 1, 1, 1, 1, 1, TradeState.CLOSED, DAY0, DAY0)
    t.realized_pnl, t.risk_usd, t.tp1_hit, t.close_reason = pnl, risk, tp1, reason
    return t


def test_summarize_metrics():
    trades = [_trade(200, tp1=True, reason="tp2"), _trade(60, tp1=True, reason="trailing_stop"),
              _trade(-100), _trade(-100)]
    s = summarize(trades, [(DAY0, 10_000), (DAY0, 10_260), (DAY0, 10_060)], 10_000)
    assert s["trades"] == 4 and s["win_rate"] == 0.5 and s["tp1_hit_rate"] == 0.5
    assert s["expectancy_r"] == (2.0 + 0.6 - 1 - 1) / 4
    assert s["profit_factor"] == 260 / 200
    assert s["max_drawdown_pct"] > 0


def test_apply_params_sets_nested_and_windows():
    p = sample(random.Random(0))
    assert set(p) == set(SPACE)
    cfg = apply_params(BotConfig(), {"analysis.displacement_atr_mult": 1.5, "analysis.trade_windows": "london+ny"})
    assert cfg.analysis.displacement_atr_mult == 1.5
    assert [w.name for w in cfg.analysis.trade_windows] == ["london", "newyork"]
    assert BotConfig().analysis.displacement_atr_mult == 1.0     # original untouched


def test_optimize_smoke():
    cfg = BotConfig()
    base = {"A": random_walk_1m(DAY0, days=4, seed=3)}
    rep = optimize(cfg, base, trials=2, target=0.6, min_trades=1, oos_fraction=0.4,
                   keep=2, seed=1, workers=1, warmup_hours=24)
    assert len(rep["in_sample_ranked"]) == 2 and len(rep["validated"]) == 2
    assert all("robust" in v for v in rep["validated"])
