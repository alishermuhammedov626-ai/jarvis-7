#!/usr/bin/env python3
"""Testnet / jonli ishga tushirish. Standart: DRY RUN, testnet."""
import argparse, logging
from halalbot.live import LiveConfig, run_forever
from halalbot.strategies import by_name

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="BTCUSDT")
ap.add_argument("--strategy", default="D", help="A/B/C/D/E yoki to'liq nom")
ap.add_argument("--quote-per-trade", type=float, default=20.0)
ap.add_argument("--max-trades-per-day", type=int, default=4)
ap.add_argument("--dry-run", type=int, default=1)
ap.add_argument("--live", type=int, default=0, help="1 = real Binance (BINANCE_LIVE=1 ham kerak)")
a = ap.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
run_forever(by_name(a.strategy), LiveConfig(symbol=a.symbol, quote_per_trade=a.quote_per_trade,
                                             max_trades_per_day=a.max_trades_per_day,
                                             dry_run=bool(a.dry_run), live=bool(a.live)))
