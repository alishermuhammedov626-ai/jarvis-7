"""Binance SPOT jonli/testnet ijro (halol siyosat bilan o'ralgan).

Xavfsizlik:
  - Standart rejim DRY_RUN=1: hech qanday buyurtma yuborilmaydi, faqat log.
  - Standart URL testnet (https://testnet.binance.vision). Real savdo uchun
    BINANCE_LIVE=1 ni aniq o'rnatish kerak.
  - Faqat /api/v3 (spot). Futures/margin yo'llari HalalPolicy tomonidan bloklanadi.
  - Kirish: MARKET BUY (quoteOrderQty), keyin OCO SELL (TP limit + SL stop-limit).
    Spot OCO — o'z coiningni sotish uchun oddiy buyurtma, qarz/foiz yo'q.

Ishlatish (testnet):
  export BINANCE_API_KEY=... BINANCE_API_SECRET=...
  python3 run_live.py --symbol BTCUSDT --strategy D --quote-per-trade 20 --dry-run 0
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import pandas as pd

from .halal import HalalPolicy, HalalViolation
from .strategies import Strategy

log = logging.getLogger("halalbot.live")

TESTNET_URL = "https://testnet.binance.vision"
LIVE_URL = "https://api.binance.com"


@dataclass
class LiveConfig:
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    quote_per_trade: float = 20.0          # har savdoga USDT (o'z pulingizdan)
    max_trades_per_day: int = 4
    dry_run: bool = True
    live: bool = False                     # False = testnet
    fee_rate: float = 0.001


class BinanceSpot:
    def __init__(self, api_key: str, api_secret: str, base_url: str, policy: HalalPolicy):
        import requests  # kechiktirilgan import: backtest uchun kerak emas
        self._s = requests.Session()
        self._s.headers["X-MBX-APIKEY"] = api_key
        self._secret = api_secret.encode()
        self.base = base_url
        self.policy = policy

    def _sign(self, params: dict) -> dict:
        params = dict(params, timestamp=int(time.time() * 1000), recvWindow=5000)
        q = urlencode(params, doseq=True)
        params["signature"] = hmac.new(self._secret, q.encode(), hashlib.sha256).hexdigest()
        return params

    def _req(self, method: str, path: str, signed=False, **params):
        self.policy.validate_endpoint(path)           # futures/margin -> HalalViolation
        if signed:
            params = self._sign(params)
        r = self._s.request(method, self.base + path, params=params, timeout=15)
        if r.status_code >= 400:
            raise RuntimeError(f"Binance {r.status_code}: {r.text}")
        return r.json()

    # --- ma'lumot ---
    def klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        raw = self._req("GET", "/api/v3/klines", symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw, columns=["t", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tb", "tq", "i"])
        df.index = pd.to_datetime(df["t"], unit="ms", utc=True)
        df = df[["open", "high", "low", "close"]].astype(float)
        return df.iloc[:-1]                             # oxirgi (yopilmagan) shamni tashlaymiz

    def balances(self) -> dict[str, float]:
        acc = self._req("GET", "/api/v3/account", signed=True)
        return {b["asset"]: float(b["free"]) for b in acc["balances"] if float(b["free"]) > 0}

    def symbol_filters(self, symbol: str) -> dict:
        info = self._req("GET", "/api/v3/exchangeInfo", symbol=symbol)
        return {f["filterType"]: f for f in info["symbols"][0]["filters"]}

    # --- buyurtmalar (faqat spot) ---
    def market_buy(self, symbol: str, quote_qty: float, holdings_quote: float, price: float):
        self.policy.validate_symbol(symbol)
        self.policy.validate_order("BUY", quote_qty / price, 0.0, holdings_quote, price)
        return self._req("POST", "/api/v3/order", signed=True, symbol=symbol, side="BUY",
                         type="MARKET", quoteOrderQty=f"{quote_qty:.2f}")

    def oco_sell(self, symbol: str, qty: float, tp: float, sl: float, holdings_base: float, tick: float, step: float):
        self.policy.validate_symbol(symbol)
        self.policy.validate_order("SELL", qty, holdings_base, 0.0, tp)
        q = _round_step(qty, step)
        return self._req("POST", "/api/v3/orderList/oco", signed=True, symbol=symbol, side="SELL",
                         quantity=q,
                         aboveType="LIMIT_MAKER", abovePrice=_round_step(tp, tick),
                         belowType="STOP_LOSS_LIMIT", belowStopPrice=_round_step(sl, tick),
                         belowPrice=_round_step(sl * 0.998, tick), belowTimeInForce="GTC")


def _round_step(x: float, step: float) -> str:
    import math
    n = math.floor(x / step) * step
    decimals = max(0, -int(round(math.log10(step)))) if step < 1 else 0
    return f"{n:.{decimals}f}"


def run_forever(strategy: Strategy, cfg: LiveConfig, policy: HalalPolicy | None = None):
    policy = policy or HalalPolicy()
    policy.validate_config()
    policy.validate_symbol(cfg.symbol)
    base_url = LIVE_URL if cfg.live else TESTNET_URL
    if cfg.live and os.environ.get("BINANCE_LIVE") != "1":
        raise RuntimeError("Real savdo uchun BINANCE_LIVE=1 muhit o'zgaruvchisi kerak")
    client = BinanceSpot(os.environ.get("BINANCE_API_KEY", ""), os.environ.get("BINANCE_API_SECRET", ""), base_url, policy)
    base_asset, quote_asset = policy.split_symbol(cfg.symbol)
    filters = client.symbol_filters(cfg.symbol) if not cfg.dry_run else {}
    tick = float(filters.get("PRICE_FILTER", {}).get("tickSize", 0.01))
    step = float(filters.get("LOT_SIZE", {}).get("stepSize", 0.00001))
    trades_today, today = 0, None
    log.info("start symbol=%s strategy=%s dry_run=%s url=%s", cfg.symbol, strategy.name, cfg.dry_run, base_url)

    while True:
        try:
            df = client.klines(cfg.symbol, cfg.interval, 500)
            sig = strategy.signals(df)
            i = len(df) - 1
            d = df.index[i].date()
            if d != today:
                today, trades_today = d, 0
            price = float(df["close"].iloc[i])
            if sig.entry[i] and trades_today < cfg.max_trades_per_day:
                sl = price - float(sig.sl_dist[i])
                tp = price + float(sig.tp_dist[i]) if sig.tp_dist[i] == sig.tp_dist[i] else price * 1.02
                bal = client.balances() if not cfg.dry_run else {quote_asset: cfg.quote_per_trade, base_asset: 0.0}
                if bal.get(base_asset, 0.0) * price > 5:
                    log.info("pozitsiya allaqachon ochiq, o'tkazib yuborildi")
                elif cfg.dry_run:
                    log.info("[DRY] BUY %s %.2f %s @ %.2f  TP=%.2f SL=%.2f", cfg.symbol, cfg.quote_per_trade, quote_asset, price, tp, sl)
                    trades_today += 1
                else:
                    o = client.market_buy(cfg.symbol, cfg.quote_per_trade, bal.get(quote_asset, 0.0), price)
                    filled = float(o["executedQty"])
                    log.info("BUY bajarildi qty=%s", filled)
                    client.oco_sell(cfg.symbol, filled * (1 - cfg.fee_rate), tp, sl, filled, tick, step)
                    trades_today += 1
        except HalalViolation as e:
            log.error("HALOL CHEKLOVI: %s — to'xtatildi", e)
            raise
        except Exception as e:  # tarmoq/birja xatolari
            log.warning("xato: %s", e)
        _sleep_to_next_candle(cfg.interval)


def _sleep_to_next_candle(interval: str):
    mins = int(interval.rstrip("m")) if interval.endswith("m") else 60
    now = time.time()
    period = mins * 60
    time.sleep(period - (now % period) + 5)
