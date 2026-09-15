"""Sintetik narx grafiklari generatori (15 daqiqalik shamlar).

Rejimlar:
  gbm      - sof tasodifiy yurish, yog'li dumli (Student-t) shovqin, drift=0.
             Bu "hech qanday edge yo'q" nazorat guruhi: bu yerda daromad
             faqat komissiya hisobiga MANFIY bo'lishi kerak.
  garch    - GARCH(1,1) volatillik klasterlari + t-shovqin.
  regime   - Markov rejim almashinuvi: yuqoriga trend / pastga trend / diapazon
             (OU qaytish). Eng realistik variant.
  trend_up / trend_down - stress test: kuchli bir tomonlama bozor.

Volatillik BTC ning odatdagi yillik ~55-70% ga kalibrlangan.
Har bir 15m sham 5 ta 3-daqiqalik qadamdan yig'iladi (OHLC realistik bo'lishi uchun).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CANDLES_PER_DAY = 96          # 15m
SUBSTEPS = 5                  # 3m qadamlar
MINUTES_PER_YEAR = 365 * 24 * 60


def _t_noise(rng: np.random.Generator, n: int, df: float = 4.0) -> np.ndarray:
    z = rng.standard_t(df, size=n)
    return z / np.sqrt(df / (df - 2.0))       # unit variance


def _to_ohlc(sub_prices: np.ndarray, start_price: float, start: pd.Timestamp) -> pd.DataFrame:
    n_candles = len(sub_prices) // SUBSTEPS
    p = sub_prices[: n_candles * SUBSTEPS].reshape(n_candles, SUBSTEPS)
    prev_close = np.concatenate([[start_price], p[:-1, -1]])
    o = prev_close
    c = p[:, -1]
    h = np.maximum(p.max(axis=1), o)
    l = np.minimum(p.min(axis=1), o)
    idx = pd.date_range(start, periods=n_candles, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def generate(regime: str, days: int, seed: int, start_price: float = 60_000.0,
             annual_vol: float = 0.60, start: str = "2025-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * CANDLES_PER_DAY * SUBSTEPS
    step_min = 15 / SUBSTEPS
    dt = step_min / MINUTES_PER_YEAR
    base_sigma = annual_vol * np.sqrt(dt)

    if regime == "gbm":
        r = base_sigma * _t_noise(rng, n)
    elif regime == "garch":
        r = _garch(rng, n, base_sigma)
    elif regime in ("trend_up", "trend_down"):
        mu = (1.0 if regime == "trend_up" else -1.0) * 1.5 * dt   # +/-150% yillik drift (stress)
        r = mu + _garch(rng, n, base_sigma)
    elif regime == "regime":
        r = _regime_switch(rng, n, base_sigma, dt)
    elif regime == "range":
        r = _pure_range(rng, n, base_sigma)          # sof yonbosh (OU): grid uchun eng qulay holat
    else:
        raise ValueError(f"noma'lum rejim: {regime}")

    log_p = np.log(start_price) + np.cumsum(r)
    prices = np.exp(log_p)
    return _to_ohlc(prices, start_price, pd.Timestamp(start, tz="UTC"))


def _garch(rng, n, base_sigma, alpha=0.08, beta=0.90):
    omega = base_sigma ** 2 * (1 - alpha - beta)
    z = _t_noise(rng, n)
    var = np.empty(n)
    r = np.empty(n)
    v = base_sigma ** 2
    for i in range(n):
        var[i] = v
        r[i] = np.sqrt(v) * z[i]
        v = omega + alpha * r[i] ** 2 + beta * v
    return r


def _pure_range(rng, n, base_sigma, kappa_per_day=0.5):
    steps_per_day = CANDLES_PER_DAY * SUBSTEPS
    kappa = kappa_per_day / steps_per_day
    noise = _garch(rng, n, base_sigma * 0.8)
    r = np.empty(n); dev = 0.0
    for i in range(n):
        r[i] = -kappa * dev + noise[i]; dev += r[i]
    return r


def _regime_switch(rng, n, base_sigma, dt):
    # 0=range (OU), 1=trend up, 2=trend down. O'rtacha rejim davomiyligi ~2-5 kun.
    steps_per_day = CANDLES_PER_DAY * SUBSTEPS
    mean_len = np.array([4.0, 2.5, 2.0]) * steps_per_day
    stay = 1.0 - 1.0 / mean_len
    trans = np.array([
        [stay[0], (1 - stay[0]) * 0.55, (1 - stay[0]) * 0.45],
        [(1 - stay[1]) * 0.6, stay[1], (1 - stay[1]) * 0.4],
        [(1 - stay[2]) * 0.6, (1 - stay[2]) * 0.4, stay[2]],
    ])
    drift = np.array([0.0, 2.0 * dt, -2.0 * dt])           # +/-200% yillik trend drift
    vol_mult = np.array([0.8, 1.0, 1.4])                    # pasayishda volatillik yuqori
    noise = _garch(rng, n, base_sigma)
    r = np.empty(n)
    state = 0
    anchor = 0.0          # OU markazi (log-narx nisbiy)
    dev = 0.0
    kappa = 0.15 / steps_per_day * 5   # kuniga qaytish kuchi
    u = rng.random(n)
    for i in range(n):
        if state == 0:
            r[i] = -kappa * dev + noise[i] * vol_mult[0]
            dev += r[i]
        else:
            r[i] = drift[state] + noise[i] * vol_mult[state]
            dev = 0.0
        cum = trans[state].cumsum()
        new_state = int(np.searchsorted(cum, u[i]))
        if new_state != state:
            state = min(new_state, 2)
            dev = 0.0
    return r


def describe(df: pd.DataFrame) -> dict:
    ret = np.log(df["close"]).diff().dropna()
    daily = ret.groupby(ret.index.date).sum()
    return {
        "candles": len(df),
        "total_return_pct": float((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100),
        "ann_vol_pct": float(daily.std() * np.sqrt(365) * 100),
        "max_dd_pct": float(((df["close"] / df["close"].cummax()) - 1).min() * 100),
        "kurtosis_15m": float(ret.kurt()),
    }
