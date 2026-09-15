"""``python -m smc_bot [--config config.json]``"""
from __future__ import annotations

import argparse
import logging
import os

from .bot import build_live
from .config import load_config


def main() -> None:
    ap = argparse.ArgumentParser(description="SMC memecoin scalping bot")
    ap.add_argument("--config", default=None, help="JSON config overriding defaults")
    ap.add_argument("--live", action="store_true", help="send real orders (default: paper)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    cfg.exchange.api_key = os.getenv("EXCHANGE_API_KEY", cfg.exchange.api_key)
    cfg.exchange.api_secret = os.getenv("EXCHANGE_API_SECRET", cfg.exchange.api_secret)
    if args.live:
        cfg.exchange.paper = False
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_live(cfg).run_forever()


if __name__ == "__main__":
    main()
