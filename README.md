# jarvis-7 — Binance savdo boti + sintetik backtester (spot halol rejimi va futures rejimi)

## Futures rejimi (foydalanuvchi qarori bilan qo'shilgan) — 43 strategiya sinovi

Futures ko'pchilik ulamolar fikricha halol emas; foydalanuvchi shunga qaramay futures rejimini so'radi.
`halalbot/futures_backtest.py` (long+short, leverage, funding, likvidatsiya), `halalbot/strategy_zoo.py`
(43 mashhur strategiya), `run_zoo.py` (ikki bosqichli qidiruv), `halalbot/futures_live.py` (testnet/jonli).

**Natija: 12 900 backtestda 0 strategiya mezondan o'tdi.** Kuniga 2.5+ savdo qiladiganlar 90 kunda median
-25..-66%, tasodifiy kirish nazorati -42%. Komissiya 0% qilinganda 11 ta "topildi", yangi grafiklarda 2 ta,
yana yangi grafiklarda 0 ta qoldi — ko'p marta sinash tuzog'i. To'liq: `reports/FUTURES_XULOSA.md`,
`reports/zoo_results.md`, `reports/zoo_fee0/zoo_results.md`.

```bash
python3 run_zoo.py --charts 30 --val-charts 40 --leverage 3 --fee 0.0005     # ~3 daqiqa, 4 yadro
python3 run_futures_live.py --strategy bollinger_meanrev_20_2 --leverage 3 --dry-run 1   # testnet dry-run
```

## "Yuqori winrate" usullari (grid, VWAP σ, MTF confluence, qisman TP, likvidatsiya soyasi, fakeout, order book, funding arbitraj)

`reports/HIGHWR_XULOSA.md` — 8 usul bo'yicha sinov. Qisqacha: grid to'r savdolari 100% foyda bilan yopiladi,
lekin SL bilan -17..-32%, SL'siz faqat sof yonboshda foyda (trendda -24%, DD -39%); qisman TP + breakeven
winrate'ni 35%->46% oshiradi, daromadni -38%->-43% tushiradi; qolganlari manfiy. Order book skalping va
funding arbitraj backtest qilib bo'lmaydi (birinchisiga L2 stakan, ikkinchisiga funding tarixi kerak).
```bash
python3 run_zoo.py --family highwr --charts 40      # 6 usul, ikki bosqich
python3 run_zoo.py --partial 1.0                    # istalgan to'plam qisman TP + breakeven bilan
python3 run_partial_compare.py                      # oddiy vs qisman TP solishtiruv
```

## TradingView bilan ishlash (real ma'lumot)

Bu muhitdan TradingView/Binance ga tarmoq yopiq, shuning uchun real ma'lumot ikki yo'l bilan olinadi:

**1-yo'l: Pine Script — TradingView'ning o'zida sinash.** `tradingview/strategy_zoo.pine` faylini Pine Editor'ga
joylashtiring, "Add to chart", grafik: `BINANCE:BTCUSDT.P`, 15m. Sozlamalardan strategiyani tanlang (23 ta),
Strategy Tester natijani ko'rsatadi. Sozlamalar Python backtester bilan bir xil: 0.05% komissiya, 3x, kuniga
max 4 kirish, SL 2 ATR, TP 3 ATR, 1% risk. **Muhim:** "Sinov boshi/oxiri" sanalarini ikkiga bo'ling
(masalan 2023 = qidiruv, 2024-2025 = tasdiqlash) va faqat ikkalasida ham foydali bo'lganini hisobga oling.
`control_random_entry` ni ham ishga tushiring: agar u ham "foydali" chiqsa, davr tasodifan qulay bo'lgan.

**2-yo'l: CSV eksport — 43 strategiyani shu yerda walk-forward sinash.** TradingView grafigida
o'ng yuqori menyu -> "Export chart data..." (pullik tarifda), 15m, iloji boricha uzoq tarix. Yoki
Binance klines CSV (`data.binance.vision`, sarlavhasiz ham bo'ladi). Keyin:

```bash
python3 run_zoo.py --csv BINANCE_BTCUSDT.P_15.csv --window-days 30 --leverage 3 --fee 0.0005
```
Tarix 30 kunlik oynalarga bo'linadi: birinchi 60% qidiruv, keyingi 20% va oxirgi 20% tasdiqlash (out-of-sample).
Natija `reports/real_results.md`. Tasodifiy nazorat ham o'tsa, hisobot ogohlantiradi. 24+ oyna (2+ yil) tavsiya.

---

# Spot (halol) rejimi

## Eng muhim xulosa (avval buni o'qing)

1. **Binance Futures halol emas** (ko'pchilik ulamolar, AAOIFI standarti 20). Sabablari:
   funding rate = riba, leverage = qarzga savdo, short = o'zingda yo'q narsani sotish, gharar.
   Shuning uchun bu bot **faqat Binance SPOT** da, **faqat o'z pulingizga**, **faqat sotib olib keyin sotish**
   (long-only) rejimida ishlaydi. Futures/margin/earn API yo'llari kodda bloklangan (`halalbot/halal.py`).
2. **Sintetik grafiklarda kuniga 3-4 marta savdo qiladigan birorta variant komissiyadan omon qolmadi.**
   900 ta sintetik grafik x 6 strategiya x 3 komissiya ssenariysi (16 200 backtest) + 13 ta parametr varianti
   (2 600 backtest) sinovdan o'tdi. 0.10% komissiyada faol strategiyalarning **100% grafikda zarar**
   (90 kunda median -13% dan -38% gacha). Sabab oddiy: har savdo ~0.20% komissiya + ~0.04% slippage yeydi,
   kuniga 2-4 savdo = kapitalning ~0.5-1% i **har kuni** xarajatga ketadi.
3. Komissiyani 0% qilib ko'rilganda ham (nazariy) sof "edge" nolga yaqin: ya'ni strategiyalar tasodifiy
   bozorda haqiqiy ustunlikka ega emas — bu kutilgan natija (sintetik grafikda bashorat qilinadigan narsa yo'q).
4. Nisbatan eng yaxshi variant: **C3 — 1 soatlik Bollinger o'rtachaga qaytish** (kuniga ~0.25 savdo,
   median ≈ 0%, max drawdown ~5-6%). U "3-4 savdo/kun" talabiga mos kelmaydi, lekin kamida kapitalni yemaydi.

**Halol va sintetik natijaga asoslanib rostini aytaman: "kuniga 3-4 marta, ishonchli foyda" degan bot
mavjud emas. Yuqori chastota = yuqori komissiya = deyarli kafolatlangan zarar.** Foyda kutish
uchun haqiqiy bozor ma'lumotida (walk-forward) sinov va past chastota kerak.

## Nima qurildi

```
halalbot/
  halal.py       Halol siyosat: spot-only, 1x, short yo'q, naked sell yo'q, futures/margin/earn endpointlar bloklangan
  synthetic.py   Sintetik 15m grafiklar: gbm, garch, regime (Markov trend/diapazon), trend_up, trend_down
  indicators.py  EMA, RSI, ATR, Bollinger, Donchian
  strategies.py  A trend-pullback, B Donchian breakout, C Bollinger mean-reversion, D sessiya ORB, E RSI scalp, Z buy&hold
  backtest.py    Spot long-only dvigatel: keyingi ochilishda kirish, SL/TP sham ichida, komissiya+slippage,
                 kuniga maksimal N savdo, pozitsiya ≤ kapital (leverage yo'q)
  montecarlo.py  Ko'p grafik x strategiya x komissiya, partiyalar orasidagi barqarorlik
  live.py        Binance SPOT REST (testnet standart, DRY_RUN standart), MARKET BUY + OCO SELL (TP/SL)
run_montecarlo.py  Takroriy Monte-Carlo -> reports/results.md, results.json
run_variants.py    Parametr variantlari sinovi
run_live.py        Testnet/jonli ishga tushirish
tests/             24 test: halol cheklovlari, kunlik limit, leverage yo'qligi, komissiya hisobi, look-ahead yo'qligi
```

## Ishga tushirish

```bash
pip install -r requirements.txt
python3 -m pytest -q tests                       # 24 test
python3 run_montecarlo.py --charts 60 --batches 3 --days 90   # ~100 s, 4 yadro
python3 run_variants.py --charts 40 --fee 0.00075
```

Testnet (hech qanday real pul yo'q), avval dry-run:
```bash
export BINANCE_API_KEY=... BINANCE_API_SECRET=...      # testnet.binance.vision kalitlari
python3 run_live.py --symbol BTCUSDT --strategy C --quote-per-trade 20 --dry-run 1
python3 run_live.py --symbol BTCUSDT --strategy C --quote-per-trade 20 --dry-run 0   # testnetga buyurtma
```
Real hisob: qo'shimcha `--live 1` va `BINANCE_LIVE=1` kerak (ikki qavat himoya). Bu muhitdan Binance ga
tarmoq yopiq bo'lgani uchun jonli/testnet modul **real serverga qarshi sinalmagan**; avval testnetda tekshiring.

## Natijalar (90 kun, 15m, spot, 0.10% komissiya, 180 grafik/rejim)

Median daromad %, `pct` = foydali grafiklar ulushi:

| Strategiya | gbm | garch | regime | trend_down | trend_up | pct foydali | savdo/kun |
|---|---|---|---|---|---|---|---|
| A trend pullback | -29.0 | -29.8 | -32.1 | -27.1 | -30.3 | 0% | 1.8 |
| B Donchian breakout | -23.2 | -25.6 | -29.3 | -24.3 | -25.7 | 0-1% | 1.4 |
| C Bollinger mean-rev | -12.7 | -15.5 | -12.5 | -20.0 | -11.2 | 1-11% | 1.0 |
| D sessiya ORB | -37.5 | -37.4 | -37.8 | -40.7 | -33.3 | 0% | 2.4 |
| E RSI scalp | -13.5 | -14.6 | -15.0 | -13.5 | -15.6 | 0% | 0.7 |
| Z buy & hold | -0.7 | -1.3 | 2.3 | -31.8 | 42.9 | 8-88% | — |

Komissiyasiz (nazariy 0%) ham: A -3..-7, B -2..-9, C +1..+4, D -8..-14, E -2..-3. Ya'ni yo'qotishning
~80% i komissiya, qolgani strategiyalarda edge yo'qligi. To'liq jadval: `reports/results.md`,
parametr variantlari: `reports/variants_fee0.10.txt`, `reports/variants_fee0.075.txt`.

Partiyalar orasidagi farq (3 mustaqil takror, turli seedlar) median daromadda 1-3 punkt: natija barqaror,
tasodif emas.

## Bot qanday halol qilingan

- `HalalPolicy.validate_config()` — bozor turi spot, leverage 1x, short o'chiq bo'lmasa xato.
- `validate_symbol()` — leverage tokenlar (UP/DOWN/BULL/BEAR), foiz protokollari (AAVE, COMP...), qimor tokenlari bloklangan.
- `validate_order()` — SELL faqat hisobda bor miqdorga, BUY faqat mavjud naqdga (qarz yo'q).
- `validate_endpoint()` — `/fapi`, `/dapi`, `/sapi/v1/margin`, `/sapi/v1/simple-earn`, `/sapi/v1/loan` va h.k. chaqirilsa xato.
- Backtest dvigatelida `max_position_frac > 1` (leverage) `ValueError`.

Bu texnik filtr, fatvo emas. Qaysi coin va qaysi savdo turi halol ekanini o'z ulamoingiz bilan tasdiqlang.
Ba'zi ulamolar spot kripto savdosini ham makruh/shubhali deb hisoblaydi.

## Keyingi halol qadamlar (agar davom etmoqchi bo'lsangiz)

1. Haqiqiy Binance spot tarixini (`/api/v3/klines`) yuklab, shu dvigatelda walk-forward sinov.
2. Chastotani kamaytirish: 1h-4h shamlar, kuniga 0-1 savdo; komissiya ulushi keskin tushadi.
3. BNB bilan komissiya 0.075%, maker (limit) buyurtmalar; ba'zi juftlarda (masalan BTC/FDUSD) davriy 0% komissiya aksiyalari.
4. Eng halol va eng arzon variant: DCA (muntazam kichik xaridlar), savdo emas, investitsiya.
