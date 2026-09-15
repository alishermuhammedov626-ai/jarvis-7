from datetime import timedelta

from smc_bot.models import Bias
from smc_bot.smc.structure import detect_bias, global_bias
from tests.helpers import DAY0, ranging, trending


def test_bullish_bias():
    assert detect_bias(trending(DAY0, 240, drift=0.5)) is Bias.BULLISH


def test_bearish_bias():
    assert detect_bias(trending(DAY0, 240, drift=-0.5)) is Bias.BEARISH


def test_ranging_is_neutral():
    assert detect_bias(ranging(DAY0, 240)) is Bias.NEUTRAL


def test_h1_contradiction_neutralises_h4():
    h4 = trending(DAY0, 240, drift=0.5)
    h1_agree = trending(DAY0, 60, drift=0.3)
    h1_against = trending(DAY0, 60, drift=-0.3)
    assert global_bias(h4, h1_agree) is Bias.BULLISH
    assert global_bias(h4, h1_against) is Bias.NEUTRAL
    assert global_bias(h4, ranging(DAY0, 60)) is Bias.BULLISH
