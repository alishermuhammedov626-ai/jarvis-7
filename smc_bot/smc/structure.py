"""Market structure: Higher-Highs/Higher-Lows vs Lower-Highs/Lower-Lows bias."""
from __future__ import annotations

import pandas as pd

from ..indicators import swing_points
from ..models import Bias


def detect_bias(df: pd.DataFrame, left: int = 2, right: int = 2) -> Bias:
    """Bias from the last two confirmed swing highs and swing lows.

    * HH + HL  -> BULLISH
    * LH + LL  -> BEARISH
    * anything else -> NEUTRAL (ranging / transitioning)
    """
    if len(df) < left + right + 4:
        return Bias.NEUTRAL
    highs, lows = swing_points(df, left, right)
    if len(highs) < 2 or len(lows) < 2:
        return Bias.NEUTRAL
    (_, h1), (_, h2) = highs[-2], highs[-1]
    (_, l1), (_, l2) = lows[-2], lows[-1]
    if h2 > h1 and l2 > l1:
        return Bias.BULLISH
    if h2 < h1 and l2 < l1:
        return Bias.BEARISH
    return Bias.NEUTRAL


def global_bias(df_h4: pd.DataFrame, df_h1: pd.DataFrame, left: int = 2, right: int = 2,
                require_h1_confirm: bool = False) -> Bias:
    """H4 sets the direction; H1 may only confirm or stay neutral.

    If H1 structure contradicts H4 we stand aside (NEUTRAL).  With
    ``require_h1_confirm`` H1 must actively agree.
    """
    b4 = detect_bias(df_h4, left, right)
    if b4 is Bias.NEUTRAL:
        return Bias.NEUTRAL
    b1 = detect_bias(df_h1, left, right)
    if b1 is not b4 and (require_h1_confirm or b1 is not Bias.NEUTRAL):
        return Bias.NEUTRAL
    return b4
