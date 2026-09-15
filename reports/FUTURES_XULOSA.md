# Futures rejimi: 43 strategiya, ikki bosqichli sintetik sinov — xulosa

## Nima sinaldi
- Dvigatel: Binance USD-M perpetual modeli. Long + short, leverage 3x, taker 0.05% har tomonda,
  slippage 0.02%, funding 0.01%/8h, likvidatsiya (maint 0.5%), kuniga max 4 kirish, SL masofasida 1% risk.
- 43 strategiya (internetdagi eng mashhurlari: EMA/TEMA/Hull kesishmalar, EMA ribbon, golden cross, MACD 3 xil,
  RSI 4 xil, Connors RSI2, Stochastic, CCI, Williams %R, Bollinger 2 xil, Keltner, Turtle 20/10 va 55/20,
  SuperTrend, Parabolic SAR, Chandelier, Larry Williams, ADX/DMI, Ichimoku, Aroon, Vortex, TRIX, ROC,
  Z-score, Heikin Ashi, inside bar, engulfing, pin bar, 3-bar reversal, sessiya ORB, kunlik pivot,
  US ochilish momentum, Elder triple screen, MTF EMA+MACD) + tasodifiy kirish nazorati.
- 2 timeframe (15m, 1h) x 5 rejim (gbm, garch, regime, trend_up, trend_down) x 30 grafik x 90 kun.
- 1-bosqich: 12 900 backtest. Mezon: median daromad > 0, foydali grafiklar >= 55%, likvidatsiya < 5%.
- 2-bosqich: o'tganlar butunlay yangi seedlarda 2 raund.

## Natija (3x, 0.05%)
**0 nomzod.** 86 sinovning (43 x 2 TF) hech biri 1-bosqich mezonini qanoatlantirmadi.
Kuniga 2.5+ savdo qiladigan 32 ta variantning barchasi 90 kunda median -25% .. -66%; foydali grafiklar 0-13%.
Tasodifiy kirish nazorati: -42.5%. Ya'ni ko'pchilik "mashhur" strategiya tasodifiy kirishdan farq qilmaydi,
bir qismi undan ham yomon.

Komissiyasiz (gross) ustun: eng yaxshisi +2.4% (stochastic), eng yomoni -19%. Sof edge ~0.
Har savdo o'rtacha 0.129% kapital xarajat (3x da komissiya notionalga hisoblanadi, ya'ni marginga 3 barobar).

## Nazorat sinovi: komissiya 0%, leverage 1x (reports/zoo_fee0/)
Bu "ko'p marta sinash tuzog'i"ning aniq namoyishi:
- 1-bosqich: 11 strategiya mezondan o'tdi (median +1.3 .. +4.9%).
- 2-bosqich 1-raund (yangi grafiklar): 11 dan 2 tasi qoldi (TRIX, Bollinger).
- 2-bosqich 2-raund (yana yangi grafiklar): 2 dan 0 tasi qoldi.
86 sinov qilsangiz, tasodifan 10 tasi "ishlaydi"; yangi ma'lumotda yo'qoladi. Ayni shu sabab internetdagi
"backtestda 300% bergan" strategiyalar jonli hisobda yo'qotadi.

## Nima uchun "topilmaguncha" davom etish ma'nosiz
Sintetik grafik — bu tasodifiy jarayon. Unda hech qanday bashorat qilinadigan naqsh yo'q (regime rejimida
faqat sekin trend bor, u ham 15m shovqinida ko'rinmaydi). Shuning uchun sintetik ma'lumotda "foydali strategiya"
topish matematik jihatdan mumkin emas; topilgani doim tasodif bo'ladi va keyingi sinovda yo'qoladi
(yuqoridagi 11 -> 2 -> 0 buni ko'rsatdi).

Haqiqiy edge faqat HAQIQIY bozor ma'lumotida sinalishi mumkin, u ham walk-forward va out-of-sample bilan.
Bu muhitdan Binance/Bybit/Kraken/Coinbase/CoinGecko/Yahoo ga tarmoq yopiq, shuning uchun real ma'lumot olinmadi.

## Tayyor asboblar
- `halalbot/futures_backtest.py` — futures dvigateli (test qilingan: short PnL, likvidatsiya, funding yo'nalishi, leverage chegarasi).
- `halalbot/strategy_zoo.py` — 43 strategiya, hammasi look-ahead testidan o'tgan.
- `run_zoo.py` — ikki bosqichli qidiruv; real ma'lumot bo'lsa `synthetic.generate` o'rniga CSV yuklash kifoya.
- `halalbot/futures_live.py`, `run_futures_live.py` — testnet/jonli ijro (DRY RUN standart), real serverga qarshi sinalmagan.
