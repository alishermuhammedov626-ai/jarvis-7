"""Binance USD-M perpetual futures jonli/testnet ijro (foydalanuvchi qarori bilan qo'shilgan).

Xavfsizlik:
  - Standart DRY_RUN=1 (buyurtma yuborilmaydi), standart URL testnet (https://testnet.binancefuture.com).
  - Real savdo: --live 1 va BINANCE_FUTURES_LIVE=1 muhit o'zgaruvchisi (ikki qavat).
  - Kirish: MARKET; SL: STOP_MARKET (closePosition); TP: TAKE_PROFIT_MARKET (closePosition).
  - Bitta ochiq pozitsiya, kuniga maksimal N kirish, leverage /fapi/v1/leverage orqali o'rnatiladi.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import pandas as pd

log = logging.getLogger("halalbot.futures_live")
TESTNET = "https://testnet.binancefuture.com"
LIVE = "https://fapi.binance.com"


@dataclass
class FLiveConfig:
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    leverage: int = 3
    risk_per_trade: float = 0.01
    max_trades_per_day: int = 4
    dry_run: bool = True
    live: bool = False


class BinanceFutures:
    def __init__(self, key, secret, base):
        import requests
        self.s = requests.Session(); self.s.headers["X-MBX-APIKEY"] = key
        self.secret = secret.encode(); self.base = base

    def _req(self, method, path, signed=False, **params):
        if signed:
            params = dict(params, timestamp=int(time.time() * 1000), recvWindow=5000)
            params["signature"] = hmac.new(self.secret, urlencode(params, doseq=True).encode(), hashlib.sha256).hexdigest()
        r = self.s.request(method, self.base + path, params=params, timeout=15)
        if r.status_code >= 400:
            raise RuntimeError(f"Binance {r.status_code}: {r.text}")
        return r.json()

    def klines(self, symbol, interval, limit=500):
        raw = self._req("GET", "/fapi/v1/klines", symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw).iloc[:, :5]; df.columns = ["t", "open", "high", "low", "close"]
        df.index = pd.to_datetime(df["t"], unit="ms", utc=True)
        return df[["open", "high", "low", "close"]].astype(float).iloc[:-1]

    def set_leverage(self, symbol, lev): return self._req("POST", "/fapi/v1/leverage", True, symbol=symbol, leverage=lev)
    def balance_usdt(self):
        for b in self._req("GET", "/fapi/v2/balance", True):
            if b["asset"] == "USDT": return float(b["availableBalance"])
        return 0.0
    def position_amt(self, symbol):
        for p in self._req("GET", "/fapi/v2/positionRisk", True, symbol=symbol):
            if p["symbol"] == symbol: return float(p["positionAmt"])
        return 0.0
    def filters(self, symbol):
        info = self._req("GET", "/fapi/v1/exchangeInfo")
        s = next(x for x in info["symbols"] if x["symbol"] == symbol)
        f = {x["filterType"]: x for x in s["filters"]}
        return float(f["PRICE_FILTER"]["tickSize"]), float(f["LOT_SIZE"]["stepSize"])
    def market(self, symbol, side, qty):
        return self._req("POST", "/fapi/v1/order", True, symbol=symbol, side=side, type="MARKET", quantity=qty)
    def stop_close(self, symbol, side, stop_price, kind):
        return self._req("POST", "/fapi/v1/order", True, symbol=symbol, side=side, type=kind,
                         stopPrice=stop_price, closePosition="true", workingType="MARK_PRICE")
    def cancel_all(self, symbol): return self._req("DELETE", "/fapi/v1/allOpenOrders", True, symbol=symbol)


def _rnd(x, step):
    d = max(0, -int(round(math.log10(step)))) if step < 1 else 0
    return f"{math.floor(x / step) * step:.{d}f}"


def run_forever(strategy, cfg: FLiveConfig):
    if cfg.live and os.environ.get("BINANCE_FUTURES_LIVE") != "1":
        raise RuntimeError("Real futures savdo uchun BINANCE_FUTURES_LIVE=1 kerak")
    cl = BinanceFutures(os.environ.get("BINANCE_API_KEY", ""), os.environ.get("BINANCE_API_SECRET", ""), LIVE if cfg.live else TESTNET)
    tick, step = (0.1, 0.001) if cfg.dry_run else cl.filters(cfg.symbol)
    if not cfg.dry_run: cl.set_leverage(cfg.symbol, cfg.leverage)
    trades_today, today = 0, None
    log.info("start %s %s lev=%s dry_run=%s", cfg.symbol, strategy.name, cfg.leverage, cfg.dry_run)
    while True:
        try:
            df = cl.klines(cfg.symbol, cfg.interval)
            sig = strategy.fsignals(df); i = len(df) - 1
            if df.index[i].date() != today: today, trades_today = df.index[i].date(), 0
            side = 1 if sig.long_entry[i] else (-1 if sig.short_entry[i] else 0)
            if side and trades_today < cfg.max_trades_per_day and not math.isnan(sig.sl_dist[i]):
                px = float(df["close"].iloc[i]); sl = px - side * float(sig.sl_dist[i])
                tp = px + side * float(sig.tp_dist[i]) if sig.tp_dist[i] == sig.tp_dist[i] else None
                bal = 1000.0 if cfg.dry_run else cl.balance_usdt()
                pos = 0.0 if cfg.dry_run else cl.position_amt(cfg.symbol)
                if pos != 0:
                    log.info("pozitsiya ochiq (%s), o'tkazib yuborildi", pos); 
                else:
                    notional = min(bal * cfg.risk_per_trade / (abs(px - sl) / px), bal * cfg.leverage)
                    qty = _rnd(notional / px, step)
                    if cfg.dry_run:
                        log.info("[DRY] %s %s qty=%s @%.2f SL=%.2f TP=%s", "BUY" if side > 0 else "SELL", cfg.symbol, qty, px, sl, tp)
                    else:
                        cl.cancel_all(cfg.symbol)
                        cl.market(cfg.symbol, "BUY" if side > 0 else "SELL", qty)
                        close_side = "SELL" if side > 0 else "BUY"
                        cl.stop_close(cfg.symbol, close_side, _rnd(sl, tick), "STOP_MARKET")
                        if tp: cl.stop_close(cfg.symbol, close_side, _rnd(tp, tick), "TAKE_PROFIT_MARKET")
                        log.info("kirish bajarildi qty=%s SL=%.2f TP=%s", qty, sl, tp)
                    trades_today += 1
        except Exception as e:
            log.warning("xato: %s", e)
        mins = int(cfg.interval.rstrip("m")) if cfg.interval.endswith("m") else 60
        time.sleep(mins * 60 - time.time() % (mins * 60) + 5)
