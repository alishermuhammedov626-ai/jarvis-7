from datetime import timedelta

from smc_bot.config import AnalysisConfig
from smc_bot.models import LiqKind
from smc_bot.smc.liquidity import (build_liquidity_map, equal_levels, levels_above,
                                   levels_below, previous_day_levels, session_levels)
from tests.helpers import DAY0, frame


def _two_days():
    rows = []
    # previous day: 96 x 15m candles ranging 100..110
    for i in range(96):
        c = 105 + 4 * ((i % 20) - 10) / 10
        rows.append((c, c + 0.3, c - 0.3, c))
    rows[10] = (104, 110.0, 103.5, 104)   # PDH
    rows[50] = (104, 104.5, 100.0, 104)   # PDL
    # today until 10:00 -> 40 candles, asia high 104.5 at 03:00, london low 101
    for i in range(40):
        c = 102 + (i % 3) * 0.2
        rows.append((c, c + 0.2, c - 0.2, c))
    rows[96 + 12] = (103, 104.5, 102.8, 103)   # 03:00 asia high
    rows[96 + 32] = (102, 102.2, 101.0, 102)   # 08:00 london low
    return frame(rows, DAY0, 15)


def test_previous_day_levels():
    df = _two_days()
    now = DAY0 + timedelta(days=1, hours=10)
    lv = {l.kind: l.price for l in previous_day_levels(df, now)}
    assert lv[LiqKind.PDH] == 110.0
    assert lv[LiqKind.PDL] == 100.0


def test_session_levels():
    df = _two_days()
    now = DAY0 + timedelta(days=1, hours=10)
    lv = {l.label: l.price for l in session_levels(df, now, AnalysisConfig().sessions)}
    assert lv["asia_high"] == 104.5
    assert lv["london_low"] == 101.0


def test_equal_highs_detected_and_invalidated():
    rows = [(100, 100.5, 99.5, 100)] * 40
    rows[10] = (100, 103.0, 99.5, 100)
    rows[20] = (100, 103.05, 99.5, 100)   # equal high pair
    df = frame(rows, DAY0, 15)
    lv = equal_levels(df, tolerance=0.2)
    assert any(l.kind is LiqKind.EQH and abs(l.price - 103.05) < 1e-9 for l in lv)
    rows[30] = (100, 104.0, 99.5, 100)   # taken out -> no longer liquidity
    assert not [l for l in equal_levels(frame(rows, DAY0, 15), 0.2) if l.kind is LiqKind.EQH]


def test_map_and_neighbours():
    df = _two_days()
    now = DAY0 + timedelta(days=1, hours=10)
    levels = build_liquidity_map(df, now, AnalysisConfig())
    above = levels_above(levels, 102.0)
    below = levels_below(levels, 102.0)
    assert above[0].price <= above[-1].price and above[0].is_buyside
    assert below[0].price >= below[-1].price and below[0].is_sellside
    assert 110.0 in [l.price for l in above]
    assert 100.0 in [l.price for l in below]
