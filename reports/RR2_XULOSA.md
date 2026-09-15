# Maxsus qidiruv: kuniga 3-5 savdo, SL:TP = 1:2 — natija

271 kirish signali (klassik, TradingView, SMC, ML, parametrik, tasodifiy nazorat) x SL = 0.75 / 1.0 / 1.5 ATR, TP = 2xSL,
15m, futures 3x, taker 0.05%, kuniga max 5 kirish. 8 grafik/rejim x 5 rejim x 90 kun = 32 520 backtest.

## Raqamlar
- Kuniga 2.5-5.5 savdo oralig'ida: **444 sinov**. Foydali median bilan: **0**. Mezondan o'tgan: **0** (2-3-bosqichga hech narsa o'tmadi).
- Oraliqdagi winrate: o'rtacha **34.7%**, maksimal **37.7%**. Hammasi bir nuqtada to'plangan.
- Eng yaxshi "haqiqiy" strategiya (Donchian 96/48): -38.7%. Tasodifiy nazoratlar: -47..-51%. Farq shovqin darajasida.
- SMC order block ham shu yerda: -49.8%, winrate 36.2%.

## Nega hammasi 35% winrate
1:2 nisbatda tasodifiy yurishda TP ga yetish ehtimoli ≈ SL/(SL+TP) = 1/3 = 33.3%. Sinovda 34.7% chiqdi, ya'ni kirish
signali winrate'ga 1-2 punkt ta'sir qiladi, xolos. Winrate'ni asosan SL/TP geometriyasi belgilaydi, kirish usuli emas.

## Komissiya bilan breakeven
| SL masofasi | TP | Kerakli winrate (0.05% taker x2 + slippage) | Komissiyasiz |
|---|---|---|---|
| 0.20% | 0.40% | 56.7% | 33.3% |
| 0.30% (≈1 ATR 15m) | 0.60% | 48.9% | 33.3% |
| 0.45% (≈1.5 ATR) | 0.90% | 43.7% | 33.3% |
| 0.60% | 1.20% | 41.1% | 33.3% |

15m da 1 ATR ≈ 0.3%. Kerakli winrate 49%, mavjud 35%. Farq 14 punkt, buni hech qanday kirish signali bermadi.

## Xulosa
"Kuniga 3-5 savdo + 1:2" talabi sintetik bozorda bajarilmaydi: 444 variantning hammasi 33-38% winrate atrofida,
breakeven uchun 44-49% kerak. Talab bajarilishi uchun quyidagilardan biri o'zgarishi shart:
- SL masofasi kattaroq (1 kunlik ATR, ya'ni 4h+ timeframe) — lekin u holda kuniga 3-5 savdo chiqmaydi;
- komissiya 0.05% dan 0.01-0.02% ga (maker/limit + VIP daraja) — breakeven 40% ga tushadi, hali ham 35% dan yuqori;
- haqiqiy bozorda 15m da 45%+ winrate beradigan kirish — sintetikda yo'q, real ma'lumotda tekshirish kerak:
  `python3 run_rr2.py` ni `run_zoo.py --csv` bilan birlashtirib real CSV da o'tkazish mumkin.
