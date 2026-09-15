"""Look-ahead (kelajakni ko'rish) testi: i-shamdagi signal faqat i gacha bo'lgan ma'lumotga bog'liq bo'lishi kerak."""
import numpy as np
import pytest

from halalbot import synthetic
from halalbot.strategies import ALL_STRATEGIES
import run_variants


ALL = list({V.name: V for V in ALL_STRATEGIES + run_variants.VARIANTS}.values())


@pytest.mark.parametrize("V", ALL, ids=lambda V: V.name)
def test_no_lookahead(V):
    df = synthetic.generate("regime", days=20, seed=42)
    full = V().signals(df)
    for cut in (1500, 1543, 1601, 1799):        # turli soat/sessiya chegaralari
        part = V().signals(df.iloc[:cut])
        i = cut - 1
        assert bool(full.entry[i]) == bool(part.entry[i]), f"{V.name}: entry[{i}] kelajakka bog'liq"
        assert bool(full.exit_sig[i]) == bool(part.exit_sig[i]), f"{V.name}: exit[{i}] kelajakka bog'liq"
        if not np.isnan(full.sl_dist[i]) or not np.isnan(part.sl_dist[i]):
            assert np.isclose(full.sl_dist[i], part.sl_dist[i], equal_nan=True), f"{V.name}: sl[{i}]"
