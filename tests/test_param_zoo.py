import numpy as np
import pytest

from halalbot import synthetic
from halalbot.param_zoo import PARAM_ZOO
from halalbot.futures_backtest import FuturesConfig
from halalbot.strategy_zoo import run_any
from halalbot.dca_backtest import DcaConfig, run_dca
import pandas as pd


def test_param_zoo_size_and_names_unique():
    names = [z.name for z in PARAM_ZOO]
    assert len(names) == len(set(names)) and len(names) > 300


@pytest.mark.parametrize("Zc", PARAM_ZOO[::23], ids=lambda z: z.name)
def test_param_zoo_no_lookahead(Zc):
    df = synthetic.generate("regime", days=20, seed=42)
    full = Zc().fsignals(df)
    for cut in (1500, 1543, 1799):
        part = Zc().fsignals(df.iloc[:cut]); i = cut - 1
        assert bool(full.long_entry[i]) == bool(part.long_entry[i]) and bool(full.short_entry[i]) == bool(part.short_entry[i]), Zc.name


def test_dca_high_winrate_but_blowup_on_trend():
    n = 96 * 30; idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"); t = np.arange(n)
    p = 100 + 2 * np.sin(t / 8.0)
    rng = pd.DataFrame({"open": p, "high": p + 0.1, "low": p - 0.1, "close": p}, index=idx)
    r = run_dca(rng, DcaConfig(funding_rate_8h=0)); m = r.metrics(30)
    assert m["win_rate_pct"] > 90 and m["return_pct"] > 0
    p2 = 100 - 0.02 * t                                   # doimiy pasayish: long DCA martingale
    dn = pd.DataFrame({"open": p2, "high": p2 + 0.1, "low": p2 - 0.1, "close": p2}, index=idx)
    r2 = run_dca(dn, DcaConfig(funding_rate_8h=0)); m2 = r2.metrics(30)
    assert m2["return_pct"] < -30
