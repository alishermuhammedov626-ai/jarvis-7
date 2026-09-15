# MEGA sinov: 519 strategiya x 3 timeframe = 1 551 sinov, 3 bosqich, 100 000+ backtest

## Nima sinaldi
- **89 nomli strategiya**: klassik indikatorlar (43), TradingView'ning eng mashhurlari (UT Bot, Squeeze Momentum, WaveTrend,
  QQE, HalfTrend, Range Filter, STC, Hull Suite, Guppy, KAMA, Fisher, RVI, Coppock, StochRSI, AO, UO, Dual Thrust,
  R-Breaker, sham naqshlari...), SMC/ICT (8), "yuqori winrate" (grid, DCA-martingale long/short, VWAP, MTF, likvidatsiya
  soyasi, fakeout), ML (Lorentzian kNN, walk-forward logistik regressiya).
- **380 parametrik variant**: EMA/RSI/Bollinger/Donchian/MACD/SuperTrend/Keltner/Z-score/Stochastic/CCI/ADX/ROC/pullback
  x parametrlar x 4 chiqish qoidasi (SL2/TP3, SL1.5/TP1.5, SL3+trailing, signal bilan chiqish).
- **51 tasodifiy nazorat** (turli seed va chastota) — tasodif qancha "o'tishini" o'lchash uchun.
- 3 timeframe (15m, 1h, 4h), 5 bozor rejimi, 90 kun, futures 3x, taker 0.05%, funding, kuniga max 4 kirish.
- 3 bosqich, har biri butunlay yangi seedlar: 10 -> 15 -> 15 grafik/rejim.

## Voronka
| Bosqich | O'tdi | Shundan nazorat |
|---|---|---|
| 1 (77 550 backtest) | **35 / 1 551 (2.3%)** | 1 / 153 (0.7%) |
| 2 (yangi grafiklar) | **6 / 35** | 0 |
| 3 (yana yangi grafiklar) | **0 / 6** | 0 |

Nazoratlar (sof tasodif) 1-bosqichdan 0.7% o'tdi; "haqiqiy" strategiyalar 2.3%. Farq 3 barobar, lekin
2-3-bosqichda hammasi yo'qoldi. 1-bosqich "g'oliblari"ning 3-bosqichdagi natijasi: 0.0, -1.5, -2.0, -2.4, -2.5, -2.6%.
Ya'ni 1-bosqichda ko'ringan "edge" = tanlov xatosi (1 551 tadan eng yaxshisini olsangiz, u tasodifan yaxshi bo'ladi).

## Kuniga 3-4 savdo talabi
Kuniga 2.5+ savdo qiladigan **342 sinovdan 0 tasi** foydali median bilan. Eng yaxshisi -10% (Heikin Ashi 1h),
qolgani -13% dan -70% gacha. 1-bosqichdan o'tgan 35 sinovning hammasi kuniga 0.1-0.6 savdo qiladi.
Sabab arifmetik: har savdo ~0.13% kapital xarajat (3x da komissiya notionalga), kuniga 3 savdo = 90 kunda ~35%.

## "Yuqori winrate" talabi
Winrate 60%+ bo'lgan 22 sinovning median daromadi **-0.6%**. Eng yuqori winrate'lar: grid 100% (daromad -28%),
DCA-martingale short 98% (-43%), DCA long 94% (-4.5%). Winrate va daromad o'rtasida bog'liqlik yo'q, ba'zan teskari.

## Oilalar bo'yicha (1-bosqich median daromadi, %)
CCI -1.8 · ADX -2.2 · Z-score -2.5 · ML -2.9 · Bollinger -3.6 · EMA -4.6 · RSI -5.0 · Donchian -5.1 · TradingView -5.2 ·
**nazorat (tasodif) -5.7** · Stochastic -6.6 · MACD -7.1 · Keltner -7.2 · pullback -7.5 · SuperTrend -7.9 ·
yuqori winrate -9.5 · ROC -10.6 · **SMC -11.4** · sham naqshlari -20.1.
Yarmi tasodifiy kirishdan yomon. SMC va sham naqshlari eng yomonlar qatorida.

## Javob
"Internetdagi barcha strategiyani topilmaguncha sinash" bajarildi: 1 551 sinov, 3 bosqich, **topilmadi**, va
nazorat guruhi bu natija tasodif emasligini ko'rsatadi. Sintetik grafikda topib bo'lmaydi, chunki unda bashorat
qilinadigan tuzilma yo'q; real bozorda esa borligini faqat real ma'lumot ko'rsatadi. Asbob tayyor:
`python3 run_mega.py` (sintetik) yoki `python3 run_zoo.py --csv <TradingView eksport>` (real).

Real ma'lumotda ham xuddi shu voronka kutiladi: 1 500 sinovdan 30-40 tasi "ishlaydi", yangi davrda 0-3 tasi qoladi,
va ular ham kuniga 3-4 emas, haftasiga 1-3 savdo qiladi.
