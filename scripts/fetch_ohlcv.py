"""Download 1m candles for backtesting.

    python scripts/fetch_ohlcv.py --symbol DOGE/USDT:USDT --days 30 --out data/doge_1m.csv
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd


def fetch(exchange_id: str, symbol: str, days: int, timeframe: str = "1m") -> pd.DataFrame:
    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    ex.load_markets()
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    rows: list[list[float]] = []
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=1500)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + 1
        if len(batch) < 1500:
            break
        time.sleep(ex.rateLimit / 1000)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts").sort_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default="binanceusdm")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    df = fetch(args.exchange, args.symbol, args.days)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out)
    print(f"{len(df)} candles -> {args.out}")


if __name__ == "__main__":
    main()
