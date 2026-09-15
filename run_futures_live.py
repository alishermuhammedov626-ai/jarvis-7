#!/usr/bin/env python3
"""Futures testnet/jonli ishga tushirish. Standart: DRY RUN, testnet."""
import argparse, logging
from halalbot.futures_live import FLiveConfig, run_forever
from halalbot.strategy_zoo import ZOO

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="BTCUSDT"); ap.add_argument("--strategy", required=True, help="strategy_zoo dagi nom")
ap.add_argument("--leverage", type=int, default=3); ap.add_argument("--risk", type=float, default=0.01)
ap.add_argument("--max-trades-per-day", type=int, default=4)
ap.add_argument("--dry-run", type=int, default=1); ap.add_argument("--live", type=int, default=0)
a = ap.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
strat = next(z for z in ZOO if z.name == a.strategy)()
run_forever(strat, FLiveConfig(symbol=a.symbol, leverage=a.leverage, risk_per_trade=a.risk,
                               max_trades_per_day=a.max_trades_per_day, dry_run=bool(a.dry_run), live=bool(a.live)))
