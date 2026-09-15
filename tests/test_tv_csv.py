import pandas as pd
from halalbot import synthetic
from halalbot.tv_csv import load_ohlc, split_windows, to_15m


def _tv_csv(tmp_path, df, iso=False):
    t = df.index.strftime("%Y-%m-%dT%H:%M:%SZ") if iso else ((df.index - pd.Timestamp("1970-01-01", tz="UTC")).total_seconds()).astype("int64")
    p = tmp_path / "x.csv"
    pd.DataFrame({"time": t, "open": df.open.values, "high": df.high.values, "low": df.low.values, "close": df.close.values, "Volume": 1.0}).to_csv(p, index=False)
    return p


def test_load_tradingview_unix_and_iso(tmp_path):
    df = synthetic.generate("gbm", days=3, seed=1)
    for iso in (False, True):
        d = load_ohlc(str(_tv_csv(tmp_path, df, iso)))
        assert len(d) == len(df) and d.index[0] == df.index[0]
        assert abs(d.close.iloc[-1] - df.close.iloc[-1]) < 1e-6


def test_load_binance_klines_headerless(tmp_path):
    df = synthetic.generate("gbm", days=2, seed=2)
    ms = ((df.index - pd.Timestamp("1970-01-01", tz="UTC")).total_seconds() * 1000).astype("int64")
    p = tmp_path / "k.csv"
    pd.DataFrame({0: ms, 1: df.open.values, 2: df.high.values, 3: df.low.values, 4: df.close.values, 5: 1, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0}).to_csv(p, index=False, header=False)
    d = load_ohlc(str(p))
    assert len(d) == len(df) and d.index[5] == df.index[5]


def test_resample_and_windows():
    df = synthetic.generate("gbm", days=65, seed=3)
    m5 = df.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).ffill()
    back = to_15m(m5)
    assert len(back) == len(df)
    assert len(split_windows(df, 30)) == 2
