"""Smart Money Concepts / ICT strategiyalari (causal, look-ahead'siz).

Qoidalar joshyattridge/smart-money-concepts kutubxonasi va ochiq manbalardagi ta'riflarga mos:
  - Swing high/low: ±n shamdagi ekstremum; FAQAT n sham o'tgach tasdiqlanadi (shift), aks holda look-ahead.
  - FVG: low[i] > high[i-2] (bullish) / high[i] < low[i-2] (bearish), o'rta sham displacement (tana > k*ATR).
  - BOS: close tasdiqlangan oxirgi swing high dan yuqoriga chiqdi; OB = impulsdan oldingi oxirgi qarama-qarshi sham.
  - CHoCH: pasayuvchi struktura (LH, LL) da close oxirgi LH dan yuqoriga chiqdi (va aksincha).
  - Liquidity sweep / Turtle soup: oldingi N-shamlik past nuqta soya bilan buzildi, close qaytdi.
  - Silver Bullet: ICT kill zone (07-08, 14-15, 18-19 UTC) ichida sweep + displacement.
  - OTE: impuls oyog'ining 62-79% retracement zonasida limit (70.5%).
  - FVG+OB confluence (FvgGold-EA uslubi): 0-100 ball, >=50 da kirish, RR 1.5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .strategy_zoo import Z, _f, reg


def confirmed_swings(df, n=10):
    """Har sham uchun: oxirgi TASDIQLANGAN swing high/low narxi va indeksi (n sham kechikish bilan)."""
    h, l = df["high"], df["low"]
    is_sh = (h == h.rolling(2 * n + 1, center=True).max())
    is_sl = (l == l.rolling(2 * n + 1, center=True).min())
    idx = np.arange(len(df))
    sh_px = pd.Series(np.where(is_sh, h, np.nan), df.index).shift(n).ffill()
    sl_px = pd.Series(np.where(is_sl, l, np.nan), df.index).shift(n).ffill()
    sh_ix = pd.Series(np.where(is_sh, idx, np.nan), df.index).shift(n).ffill()
    sl_ix = pd.Series(np.where(is_sl, idx, np.nan), df.index).shift(n).ffill()
    # oldingi swing (struktura uchun): tasdiqlangan swing o'zgarganda avvalgisini saqlaymiz
    prev_sh = _prev_distinct(sh_px.values, df.index)
    prev_sl = _prev_distinct(sl_px.values, df.index)
    return sh_px, sl_px, sh_ix, sl_ix, prev_sh, prev_sl


def _prev_distinct(v, index):
    """Har sham uchun: joriy qiymatdan OLDINGI farqli qiymat (faqat o'tmishga qarab)."""
    out = np.full(len(v), np.nan); prev = cur = np.nan
    for i in range(len(v)):
        x = v[i]
        if not np.isnan(x) and (np.isnan(cur) or x != cur):
            prev, cur = cur, x
        out[i] = prev
    return pd.Series(out, index)


def fvg(df, disp_atr=0.8):
    a = ind.atr(df, 14)
    body = (df["close"].shift(1) - df["open"].shift(1))
    bull = (df["low"] > df["high"].shift(2)) & (body > disp_atr * a)
    bear = (df["high"] < df["low"].shift(2)) & (-body > disp_atr * a)
    bull_top, bull_bot = df["low"], df["high"].shift(2)
    bear_top, bear_bot = df["low"].shift(2), df["high"]
    return bull, bear, bull_top, bull_bot, bear_top, bear_bot, a


KILL_ZONES_UTC = ((7, 8), (14, 15), (18, 19))   # ICT: 3-4 NY, 10-11 NY, 14-15 NY (EDT)


def in_killzone(idx):
    hr = idx.hour.values
    m = np.zeros(len(idx), bool)
    for a, b in KILL_ZONES_UTC:
        m |= (hr >= a) & (hr < b)
    return m


# ----------------------------------------------------------------- strategiyalar
@reg
class SmcFvgRetest(Z):
    """FVG hosil bo'ldi -> zona yuqori chegarasiga limit, SL zona pastidan tashqarida, TP 2R."""
    name, family = "smc_fvg_retest_limit", "smc"
    def fsignals(self, df):
        bull, bear, bt, bb, rt, rb, a = fvg(df)
        limit = bt.where(bull, rb.where(bear, np.nan))          # long: zona yuqorisi; short: zona pasti
        sl = (bt - bb + 0.25 * a).where(bull, (rt - rb + 0.25 * a).where(bear, np.nan))
        s = _f(df, bull, bear, sl=sl, tp=2.0 * sl, time_stop=48)
        s.limit_price = np.asarray(limit, float); s.limit_ttl = 12
        return s


@reg
class SmcOrderBlockRetest(Z):
    """BOS (close > tasdiqlangan swing high) -> impulsdan oldingi oxirgi bearish sham = OB; OB yuqorisiga limit."""
    name, family = "smc_order_block_retest", "smc"
    def fsignals(self, df):
        sh, sl_, shi, sli, _, _ = confirmed_swings(df, 10)
        c, o, h, l = (df[k] for k in ("close", "open", "high", "low"))
        a = ind.atr(df, 14).values
        bos_up = (c > sh) & (c.shift(1) <= sh)
        bos_dn = (c < sl_) & (c.shift(1) >= sl_)
        n = len(df); ov, cv, hv, lv = o.values, c.values, h.values, l.values
        lg = np.zeros(n, bool); sh_ = np.zeros(n, bool); limit = np.full(n, np.nan); sld = np.full(n, np.nan)
        for i in np.where(bos_up.values | bos_dn.values)[0]:
            if bos_up.values[i]:
                for j in range(i - 1, max(i - 20, 0), -1):
                    if cv[j] < ov[j]:                      # oxirgi bearish sham = bullish OB
                        lg[i] = True; limit[i] = hv[j]; sld[i] = hv[j] - lv[j] + 0.25 * a[i]; break
            else:
                for j in range(i - 1, max(i - 20, 0), -1):
                    if cv[j] > ov[j]:
                        sh_[i] = True; limit[i] = lv[j]; sld[i] = hv[j] - lv[j] + 0.25 * a[i]; break
        ok = sld > 0.3 * a
        s = _f(df, lg & ok, sh_ & ok, sl=sld, tp=2.0 * sld, time_stop=48)
        s.limit_price = limit; s.limit_ttl = 24
        return s


@reg
class SmcLiquiditySweep(Z):
    """Oldingi 48-shamlik past nuqta soya bilan buzildi va close qaytdi -> long; TP qarama-qarshi likvidlik (<=3R)."""
    name, family = "smc_liquidity_sweep_reversal", "smc"
    def fsignals(self, df):
        c, h, l = df["close"], df["high"], df["low"]; a = ind.atr(df, 14)
        L = l.shift(1).rolling(48).min(); H = h.shift(1).rolling(48).max()
        lg = (l < L - 0.2 * a) & (c > L); sh = (h > H + 0.2 * a) & (c < H)
        sl = (c - l + 0.25 * a).where(lg, (h - c + 0.25 * a).where(sh, np.nan))
        tp = np.minimum((H - c).where(lg, (c - L).where(sh, np.nan)), 3 * sl)
        return _f(df, lg & (tp > sl), sh & (tp > sl), sl=sl, tp=tp, time_stop=48)


@reg
class SmcChoch(Z):
    """CHoCH: pasayuvchi struktura (LH va LL) da close oxirgi LH dan yuqoriga chiqdi -> long, SL oxirgi LL."""
    name, family = "smc_choch_reversal", "smc"
    def fsignals(self, df):
        sh, sl_, _, _, psh, psl = confirmed_swings(df, 10)
        c = df["close"]; a = ind.atr(df, 14)
        bearish_struct = (sh < psh) & (sl_ < psl)
        bullish_struct = (sh > psh) & (sl_ > psl)
        lg = bearish_struct & (c > sh) & (c.shift(1) <= sh)
        sh_ = bullish_struct & (c < sl_) & (c.shift(1) >= sl_)
        sl = (c - sl_ + 0.25 * a).where(lg, (sh - c + 0.25 * a).where(sh_, np.nan))
        ok = (sl > 0.5 * a) & (sl < 6 * a)
        return _f(df, lg & ok, sh_ & ok, sl=sl, tp=2.0 * sl, time_stop=96)


@reg
class SmcSilverBullet(Z):
    """ICT Silver Bullet: kill zone ichida oldingi 2 soat diapazoni sweep + displacement sham -> TP diapazon qarama-qarshi tomoni."""
    name, family = "smc_silver_bullet_killzone", "smc"
    def fsignals(self, df):
        c, o, h, l = (df[k] for k in ("close", "open", "high", "low")); a = ind.atr(df, 14)
        kz = pd.Series(in_killzone(df.index), df.index)
        L = l.shift(1).rolling(8).min(); H = h.shift(1).rolling(8).max()
        body = c - o
        lg = kz & (l < L) & (c > L) & (body > 0.5 * a)
        sh = kz & (h > H) & (c < H) & (-body > 0.5 * a)
        sl = (c - l + 0.25 * a).where(lg, (h - c + 0.25 * a).where(sh, np.nan))
        tp = (H - c).where(lg, (c - L).where(sh, np.nan))
        day = ind.day_index(df.index) * 10 + (df.index.hour.values // 6)
        return _f(df, lg & (tp > sl), sh & (tp > sl), sl=sl, tp=tp, group=day, time_stop=16)


@reg
class SmcTurtleSoup(Z):
    """Turtle Soup (Connors/Raschke, ICT da ham): 20-shamlik past nuqta buzildi, close qaytdi -> long, TP 2R."""
    name, family = "smc_turtle_soup_20", "smc"
    def fsignals(self, df):
        c, h, l = df["close"], df["high"], df["low"]; a = ind.atr(df, 14)
        L = l.shift(1).rolling(20).min(); H = h.shift(1).rolling(20).max()
        lg = (l < L - 0.1 * a) & (c > L); sh = (h > H + 0.1 * a) & (c < H)
        sl = (c - l + 0.25 * a).where(lg, (h - c + 0.25 * a).where(sh, np.nan))
        return _f(df, lg, sh, sl=sl, tp=2.0 * sl, time_stop=32)


@reg
class SmcFvgObConfluenceScored(Z):
    """FvgGold-EA uslubi: FVG + OB ustma-ust + 1h EMA moslik + premium/discount + kill zone -> ball >= 50, RR 1.5."""
    name, family = "smc_fvg_ob_confluence_score50_rr1.5", "smc"
    def fsignals(self, df):
        bull, bear, bt, bb, rt, rb, a = fvg(df, disp_atr=0.5)
        c, o, h, l = (df[k] for k in ("close", "open", "high", "low"))
        gap = (bt - bb).where(bull, (rt - rb).where(bear, np.nan))
        rng1 = (h.shift(1) - l.shift(1)).replace(0, np.nan)
        disp = ((c.shift(1) - o.shift(1)).abs() / rng1).clip(0, 1)
        h1 = c.resample("1h").last(); e50, e200 = ind.ema(h1, 50), ind.ema(h1, 200)
        htf_up = (e50 > e200).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        px_below_e50 = (h1 < e50).shift(1).reindex(df.index, method="ffill").fillna(False).astype(bool)
        # OB ustma-ust: oldingi 10 shamda qarama-qarshi rangli sham zonasi FVG bilan kesishadimi
        ob_bull = pd.concat([((c.shift(k) < o.shift(k)) & (h.shift(k) >= bb) & (l.shift(k) <= bt)) for k in range(3, 13)], axis=1).any(axis=1)
        ob_bear = pd.concat([((c.shift(k) > o.shift(k)) & (h.shift(k) >= rb) & (l.shift(k) <= rt)) for k in range(3, 13)], axis=1).any(axis=1)
        kz = pd.Series(in_killzone(df.index), df.index)
        score_l = (gap / a).clip(0, 1) * 30 + disp * 30 + htf_up * 20 + px_below_e50 * 10 + kz * 10 + ob_bull * 20
        score_s = (gap / a).clip(0, 1) * 30 + disp * 30 + (~htf_up) * 20 + (~px_below_e50) * 10 + kz * 10 + ob_bear * 20
        lg = bull & (score_l >= 50); sh = bear & (score_s >= 50)
        entry = (bb + 0.25 * gap).where(lg, (rt - 0.25 * gap).where(sh, np.nan))
        sl = (entry - bb + 0.25 * a).where(lg, (rt - entry + 0.25 * a).where(sh, np.nan))
        s = _f(df, lg, sh, sl=sl, tp=1.5 * sl, time_stop=48)
        s.limit_price = np.asarray(entry, float); s.limit_ttl = 12
        return s


@reg
class SmcOte(Z):
    """OTE: yuqoriga trendda (HH, HL) oxirgi impuls oyog'ining 70.5% retracement darajasiga limit; SL swing low; TP swing high."""
    name, family = "smc_ote_705_retracement", "smc"
    def fsignals(self, df):
        sh, sl_, shi, sli, psh, psl = confirmed_swings(df, 10)
        c = df["close"]; a = ind.atr(df, 14)
        up = (sh > psh) & (sl_ > psl) & (shi > sli)        # oxirgi oyoq: low -> high (bullish impuls)
        dn = (sh < psh) & (sl_ < psl) & (sli > shi)
        ote_l = sh - 0.705 * (sh - sl_); ote_s = sl_ + 0.705 * (sh - sl_)
        lg = up & (c > ote_l) & (c < ote_l + 1.0 * a)       # narx zonaga yaqinlashdi -> limit qo'yamiz
        sh_ = dn & (c < ote_s) & (c > ote_s - 1.0 * a)
        sl = (ote_l - sl_ + 0.25 * a).where(lg, (sh - ote_s + 0.25 * a).where(sh_, np.nan))
        tp = (sh - ote_l).where(lg, (ote_s - sl_).where(sh_, np.nan))
        group = shi.fillna(-1).astype(np.int64).where(lg, sli.fillna(-1).astype(np.int64))
        ok = (sl > 0.5 * a) & (tp > sl)
        s = _f(df, lg & ok, sh_ & ok, sl=sl, tp=tp, group=group, time_stop=96)
        s.limit_price = np.asarray(ote_l.where(lg, ote_s.where(sh_, np.nan)), float); s.limit_ttl = 24
        return s


SMC = [z for z in __import__("halalbot.strategy_zoo", fromlist=["ZOO"]).ZOO if z.family == "smc"]
