# SMC Memecoin Scalping Bot (24/7)

DOGE, SHIB, PEPE, WIF, BONK, FLOKI bo'yicha **Smart Money Concept (SMC)** asosida
skalping qiladigan algoritmik bot. Kuniga 2–4 ta sifatli savdo, har bir savdoda
risk **hisobning 1%** dan oshmaydi, TP kamida **1:2 / 1:3 R:R**.

Python 3.10+, `ccxt` (USDT-M perpetual futures, standart: Binance USDⓈ-M),
`pandas`, `numpy`.

```
pip install -r requirements.txt
python -m pytest -q                      # 44 ta test
python -m smc_bot --config config.example.json          # paper (simulyatsiya) rejimi
EXCHANGE_API_KEY=... EXCHANGE_API_SECRET=... \
python -m smc_bot --config config.example.json --live   # haqiqiy orderlar
```

---

## 1. Umumiy arxitektura

```
smc_bot/
├── config.py            barcha sozlamalar (JSON bilan qayta yozish mumkin)
├── models.py            Side, Bias, LiquidityLevel, Sweep, MSS, Zone, Signal, Trade
├── indicators.py        ATR (Wilder), fractal swing high/low
├── data/feed.py         ccxt (jonli) va tarixiy (backtest) ma'lumot manbalari
├── smc/
│   ├── structure.py     H4/H1 bias: HH/HL -> LONG, LH/LL -> SHORT
│   ├── liquidity.py     M15 likvidlik xaritasi: PDH/PDL, sessiya H/L, EQH/EQL
│   ├── sweep.py         likvidlik sweep detektori
│   ├── displacement.py  Displacement (body >= ATR) + MSS
│   └── zones.py         FVG va Order Block, zona hali "toza"mi
├── strategy/setup.py    confluence dvigateli -> Signal (entry/SL/TP1/TP2)
├── risk/
│   ├── sizing.py        1% risk (komissiya + slippage hisobga olingan)
│   └── filters.py       spred/hajm/depth filtri, korrelyatsiya, kunlik limitlar
├── execution/
│   ├── exchange.py      CcxtFuturesExchange (real) / PaperExchange (simulyator)
│   └── manager.py       pozitsiya hayot sikli: PENDING -> OPEN -> RUNNER -> CLOSED
├── bot.py               24/7 asosiy loop
└── backtest.py          xuddi shu loopni tarixiy 1m shamlarda ishlatadi
```

Bot har **60 soniyada** bir marta `SmcScalperBot.step()` ni bajaradi:

1. Har bir juftlik uchun bozor sifatini (spred, 24h hajm, order-book chuqurligi) oladi
   va filtrdan o'tmaganlarni chiqarib tashlaydi.
2. Ochiq savdolarni yangilaydi (limit to'ldi-mi, TP1 urildimi, BE/trailing, muddat).
3. Bo'sh slot bo'lsa va kunlik limitlar ruxsat bersa — har bir juftlikda SMC
   pipeline'ni ishga tushiradi, kandidatlarni reytinglaydi (korrelyatsiya filtri) va
   eng yaxshilariga limit order qo'yadi.

Holat `state/trades.json` va `state/governor.json` ga yoziladi, shuning uchun bot
qayta ishga tushganda ochiq pozitsiyalar va kunlik hisob yo'qolmaydi.

---

## 2. Top-Down tahlil ketma-ketligi

### 2.1 H4 + H1 — global bias (`smc/structure.py`)

Har taymfreymda tasdiqlangan fractal swing'lar (chapdan 2, o'ngdan 2 sham) olinadi.
Oxirgi ikkita swing high va swing low solishtiriladi:

| Holat | Natija |
|---|---|
| Higher High **va** Higher Low | `BULLISH` → faqat LONG |
| Lower High **va** Lower Low | `BEARISH` → faqat SHORT |
| boshqa | `NEUTRAL` → savdo yo'q |

Qoida: **H4 yo'nalishni belgilaydi**, H1 faqat tasdiqlaydi yoki neytral bo'ladi.
Agar H1 H4 ga qarshi bo'lsa — bot chetda turadi.

### 2.2 M15 — likvidlik xaritasi (`smc/liquidity.py`)

| Daraja | Qanday hisoblanadi |
|---|---|
| **PDH / PDL** | oldingi UTC kunning high/low |
| **Asia H/L** | 00:00–08:00 UTC oynasi (bugungi boshlanmagan bo'lsa — kechagi) |
| **London H/L** | 07:00–13:00 UTC oynasi |
| **EQH / EQL** | ikkita ketma-ket swing farqi ≤ `0.15 × ATR(M15)`; daraja allaqachon sindirilgan bo'lsa ro'yxatdan chiqadi |

Highs = **buy-side** likvidlik (narxdan yuqorida), lows = **sell-side**.
PDH/PDL va sessiya darajalari **"major"** hisoblanadi (TP2 uchun ishlatiladi).

### 2.3 M5 → M1 — kirish nuqtasi

Pipeline avval M5 da, topilmasa M1 da ishlaydi (`strategy/setup.py`).

---

## 3. Kirish shartlari (confluence — hammasi bir vaqtda)

```
bias(H4,H1) ≠ NEUTRAL
  └─ sweep(M15 daraja, M5/M1)           smc/sweep.py
       └─ displacement + MSS             smc/displacement.py
            └─ FVG (bo'lmasa OB)         smc/zones.py
                 └─ narx hali zonaga qaytmagan
                      └─ SL/TP hisoblash, R:R tekshiruvi
```

**Likvidlik sweep.** LONG uchun: sham low'i sell-side darajadan pastga o'tadi
(wick), keyin ≤ 6 sham ichida close daraja **ustida** bo'ladi. SHORT — teskari.
Oxirgi 36 sham ichida eng so'nggi sweep olinadi. Daraja shamdan oldin shakllangan
bo'lishi shart.

**Displacement + MSS.** Sweep ekstremumidan boshlab (impuls oyog'ining boshi)
24 sham ichida:
- yo'nalishdagi sham tanasi `|close − open| ≥ 1.0 × ATR(14)` (displacement), **va**
- close strukturaviy darajani sindiradi: LONG uchun sweep'dan oldingi oxirgi
  tasdiqlangan swing high, SHORT uchun swing low (MSS).

**FVG / OB.** Impuls oyog'i ichida (`leg_start … MSS shami`):
- FVG: `low[i+1] > high[i-1]` (bullish) / `high[i+1] < low[i-1]` (bearish),
  kattaligi ≥ `0.1 × ATR`. Bir nechta bo'lsa — eng katta tanali (haqiqiy
  displacement) sham hosil qilgani tanlanadi.
- OB: displacement shamidan oldingi oxirgi qarama-qarshi rangli sham; bo'lmasa
  sweep ekstremum shami.
- Avval FVG, u yo'q yoki allaqachon "to'ldirilgan" (close zona orqasidan chiqqan)
  bo'lsa — OB.

**Kirish.** Zona ichida `entry_zone_ratio = 0.5` (zona o'rtasi, CE) ga
**limit order** qo'yiladi. Narx hozir zona narigi tomonida bo'lishi shart (retracement
kutiladi, "quvib" kirilmaydi). Order **60 daqiqa** to'lmasa bekor qilinadi.

---

## 4. Stop-Loss va Take-Profit

| | LONG | SHORT |
|---|---|---|
| **SL** | `zona.low − 0.5 × ATR` | `zona.high + 0.5 × ATR` |
| **TP1** | eng yaqin buy-side daraja, R ∈ [1.0, 3.0); bo'lmasa 1.5R | eng yaqin sell-side daraja |
| **TP2** | TP1 dan narida joylashgan keyingi **major** daraja, R ∈ [2.0, 4.0]; bo'lmasa 3R (har doim TP1 dan narida) | teskari |

Signal `rr1 < 1.0` yoki `rr2 < 2.0` bo'lsa rad etiladi.

Pozitsiya menejeri (`execution/manager.py`):

1. Limit to'lgach: **SL — reduce-only stop-market** (to'liq hajm),
   **TP1 — take-profit-market 50%**, **TP2 — take-profit-market 50%**.
2. TP1 urilgach: eski SL bekor qilinadi, qolgan 50% uchun SL
   **break-even + 5 bps** (komissiya bufer) ga qo'yiladi → holat `RUNNER`.
3. `RUNNER` da har loopda **trailing**: `SL = narx ∓ 1.0 × ATR(M5)`, faqat
   foyda tomonga suriladi (hech qachon bo'shatilmaydi).
4. SL yoki TP2 urilgach barcha qolgan orderlar bekor qilinadi → `CLOSED`.

Memecoinlarda narx "sakraydi", shuning uchun SL/TP hech qachon limit emas —
faqat **stop-market / take-profit-market**, `reduceOnly=True`.

---

## 5. Risk boshqaruvi va memecoin himoyasi

### 5.1 Hajm (`risk/sizing.py`)

```
risk_usd       = equity × 1%
risk_per_unit  = |entry − SL| + entry × (2×fee + slippage)/10 000
qty            = risk_usd / risk_per_unit   → birja step'iga yaxlitlanadi
```

Komissiya va kutilayotgan slippage hisobga olinadi, shuning uchun **eng yomon
holatda ham zarar 1% dan oshmaydi**. Margin `leverage` (standart 5x, isolated) bilan
hisobning 95% idan oshsa hajm qisqartiriladi; min-notional/min-amount tekshiriladi.

Qo'shimcha: SL masofasi (bps) `< 3 × (2×fee + slippage)` bo'lsa setup tashlab
yuboriladi — juda tor stoplarda xarajat R ni "yeb qo'yadi".

### 5.2 Bozor filtri (`risk/filters.py`)

| Parametr | Standart | Ma'nosi |
|---|---|---|
| `max_spread_bps` | 6 | spred ≥ 0.06% → savdo yo'q |
| `min_quote_volume_24h` | 50 M USDT | past likvidli juftlik chiqariladi |
| `min_depth_notional` | 200 k USDT | mid ±0.1% ichidagi order-book hajmi |
| `max_order_depth_share` | 10% | order depth'ning 10% idan katta bo'lmasin |

### 5.3 Korrelyatsiya filtri

Bir vaqtning o'zida maksimal `max_open_positions = 2` (3 gacha sozlanadi). Bir
loopda bir nechta juftlikda signal chiqsa — **24h hajmi eng katta va spredi eng
past** bo'lganlar (ikkala reyting yig'indisi, teng bo'lsa yuqori R:R) tanlanadi.
Bir juftlikda bir vaqtda faqat bitta pozitsiya.

### 5.4 Kunlik boshqaruv (`TradeGovernor`)

- kuniga maksimal **4** savdo (UTC bo'yicha yangilanadi);
- kunlik zarar **−3%** ga yetsa — kun oxirigacha yangi savdo yo'q;
- yopilgan juftlikda **90 daqiqa** cooldown;
- bir xil setup (symbol + MSS vaqti + zona) ikki marta yuborilmaydi.

---

## 6. Sozlash

`config.example.json` ni nusxalab o'zgartiring. Faqat kerakli maydonlarni yozish
kifoya — qolgani `config.py` dagi standart qiymatlarni oladi. Muhim parametrlar:

| Yo'l | Standart | Izoh |
|---|---|---|
| `analysis.displacement_atr_mult` | 1.0 | displacement sham tanasi / ATR |
| `analysis.sl_atr_buffer` | 0.5 | SL bufer |
| `analysis.entry_zone_ratio` | 0.5 | 0 = zona chekkasi, 0.5 = o'rtasi |
| `analysis.entry_ttl_minutes` | 60 | limit order muddati |
| `analysis.trail_atr_mult` | 1.0 | trailing masofa |
| `risk.risk_per_trade_pct` | 1.0 | |
| `risk.max_open_positions` | 2 | 2–3 |
| `risk.max_trades_per_day` | 4 | |
| `exchange.paper` | true | `--live` bayrog'i false qiladi |

API kalitlar `EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET` muhit o'zgaruvchilaridan
o'qiladi (JSON ga yozmang).

---

## 7. Backtest

```
python scripts/fetch_ohlcv.py --symbol DOGE/USDT:USDT --days 30 --out data/doge_1m.csv
python scripts/fetch_ohlcv.py --symbol PEPE/USDT:USDT --days 30 --out data/pepe_1m.csv
python -m smc_bot.backtest --csv DOGE=data/doge_1m.csv --csv PEPE=data/pepe_1m.csv
```

Backtester **jonli bot bilan bir xil `step()`** ni 5 daqiqalik qadamlar bilan
tarixiy 1m shamlar ustida yurgizadi; orderlar `PaperExchange` orqali to'ldiriladi
(limit — narx tegsa, stop/TP — market + slippage; bitta sham SL va TP ga ham
tegsa, avval SL hisoblanadi — konservativ). Natija: savdolar soni, win-rate,
profit factor, net PnL, equity egri chizig'i.

> Sintetik random-walk ma'lumotda strategiya ustunlikka ega emas (bu kutilgan
> holat — unda struktura yo'q). Haqiqiy baholash uchun birjadan yuklangan
> ma'lumot ishlating va parametrlarni faqat out-of-sample davrda tasdiqlang.

---

## 8. Win rate'ni oshirish (60%+ maqsadi)

Win rate **faqat real ma'lumotda o'lchanadi va sozlanadi**. Bu repoda buning
uchun uchta vosita bor.

### 8.1 Sifat filtrlari (`AnalysisConfig`)

Har biri chastotani kamaytirib, sifatni oshiradi:

| Parametr | Ta'siri |
|---|---|
| `require_h1_confirm` | H1 ham H4 bilan bir yo'nalishda bo'lishi shart (neytral yetmaydi) |
| `require_major_sweep` | faqat PDH/PDL va sessiya H/L sweep'lari (EQH/EQL emas) |
| `min_sweep_depth_atr` | wick darajadan kamida shuncha ATR o'tishi kerak (shovqin emas, haqiqiy sweep) |
| `displacement_atr_mult` | 1.5–2.0: faqat kuchli impulslar |
| `allow_ob_fallback=false` | faqat FVG, OB bilan kirilmaydi |
| `max_setup_age_candles` | MSS dan keyin N sham ichida kirilmasa setup eskiradi |
| `trade_windows` | faqat London (07–11) va NY (12–17 UTC) "kill zone" larida kirish |
| `tp1_mode="fixed"`, `tp1_fixed_rr=1.0`, `tp1_share=0.6` | TP1 = 1R da 60%, keyin BE: "g'alaba" tezroq qayd etiladi, TP2 baribir ≥ 2R |
| `entry_mode="confirm"` | "ko'r" limit o'rniga: narx zonaga kirib, M1 sham yo'nalishda zonadan tashqariga yopilib, oldingi sham high/low'ini olgandan keyin market kirish. Zona "teshib o'tiladigan" savdolar chiqib ketadi; SL zonada qoladi, qat'iy R nishonlar yangi entry'dan qayta hisoblanadi |
| `premium_discount_filter` | LONG faqat oxirgi 48 H1 sham diapazonining pastki yarmida (discount), SHORT yuqori yarmida (premium) |

`profiles/high_winrate.json` shu filtrlarning tayyor kombinatsiyasi:

```
python -m smc_bot.backtest --config profiles/high_winrate.json --csv DOGE=data/doge_1m.csv ...
```

### 8.2 Voronka diagnostikasi

Backtest oxirida `rejection funnel` chiqadi: nechta baholash `bias_neutral`,
`5m:no_sweep`, `5m:no_displacement_mss`, `5m:no_zone`, `5m:rr_too_low` va h.k.
bosqichida to'xtagani. Qaysi filtr setuplarni "yeb qo'yayotgani"ni ko'rsatadi.

### 8.3 Walk-forward optimizator

```
python -m smc_bot.optimize --csv DOGE=data/doge_1m.csv --csv PEPE=data/pepe_1m.csv \
    --csv WIF=data/wif_1m.csv --trials 150 --target-winrate 0.60 --min-trades 30 \
    --oos-fraction 0.3 --workers 4 --out best_config.json
```

1. Tarix in-sample (70%) / out-of-sample (30%) ga bo'linadi.
2. 150 ta tasodifiy parametr to'plami in-sample'da sinaladi. `win_rate ≥ 60%`
   va `trades ≥ 30` bo'lganlar orasidan eng yuqori R-kutilma tanlanadi.
3. Eng yaxshi 5 tasi out-of-sample'da qayta tekshiriladi. **Faqat OOS da ham
   60% ni ushlab qolgan** to'plam `best_config.json` ga yoziladi; qolganlari
   "overfit" deb belgilanadi.

Agar hech bir to'plam OOS da 60% ga chiqmasa, dastur buni ochiq aytadi. Bunday
holatda parametrlarni qo'lda "60% ga sozlash" o'z-o'zini aldash bo'ladi:
ko'proq ma'lumot yig'ing (kamida 90 kun, 6 juftlik) yoki maqsadni R-kutilma
bo'yicha qo'ying (win rate 45% + 2.25R ham foydali tizim).

### 8.4 "G'alaba" ta'rifi

Backtest ikkita ko'rsatkichni beradi: `win_rate` (sof PnL > 0) va
`tp1_hit_rate` (TP1 ga yetgan, keyin BE dan chiqqan savdolar ham kiradi).
TP1 = 1R / 60% modelida ikkinchisi birinchisidan yuqori bo'ladi; 60% maqsadini
qaysi ta'rifda qo'yayotganingizni aniq belgilang.

## 9. Ishga tushirish (24/7)

```
# systemd misoli
[Service]
WorkingDirectory=/opt/smc-bot
Environment=EXCHANGE_API_KEY=...
Environment=EXCHANGE_API_SECRET=...
ExecStart=/usr/bin/python3 -m smc_bot --config config.json --live
Restart=always
RestartSec=10
```

Tavsiya etilgan tartib: **1)** `paper: true` bilan kamida 2 hafta;
**2)** `sandbox: true` (testnet); **3)** minimal depozit bilan live.

## 10. Cheklovlar / ogohlantirish

- Bu dasturiy ta'minot moliyaviy maslahat emas; memecoin fyuchers savdosi yuqori
  riskli. Kod real pul bilan ishlatilishidan oldin sizning tomoningizdan
  backtest va forward-test qilinishi kerak.
- ccxt unifikatsiyalangan `stopLossPrice` / `takeProfitPrice` parametrlari
  Binance USDⓈ-M va Bybit da tekshirilgan yondashuv; boshqa birjalar uchun
  `CcxtFuturesExchange` ni moslashtiring.
- Paper rejimda fill'lar oxirgi yopilgan 1m sham high/low bo'yicha simulyatsiya
  qilinadi; haqiqiy fill'lar farq qilishi mumkin.
