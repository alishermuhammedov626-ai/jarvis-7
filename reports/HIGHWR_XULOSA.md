# "Yuqori winrate" usullari — 8 ta da'vo, sintetik sinov natijasi

Sinov: futures modeli (3x, taker 0.05%, maker 0.02%, funding 0.01%/8h, kuniga max 4 kirish), 5 rejim x 40 grafik x 90 kun,
15m va 1h; grid uchun qo'shimcha sof yonbosh ("range", OU) rejim. Kod: `halalbot/grid_backtest.py`,
`halalbot/strategy_zoo.py` (`hw_*`), `run_zoo.py --family highwr`, `run_partial_compare.py`.
To'liq jadvallar: `reports/highwr/zoo_results.md`, `reports/grid_variants.txt`, `reports/partial_tp_compare.txt`.

## 1. Grid bot (yonbosh bozor) — da'vo: to'r savdolarining 85-95% foyda bilan yopiladi
**Da'voning birinchi qismi TASDIQLANDI: to'r savdolarining 100% i foyda bilan yopildi.** Lekin bu hisob
ko'rsatkichi emas: grid'da yo'qotish savdo sifatida emas, ochiq inventar (drawdown) va SL sifatida keladi.

| Variant | range (sof yonbosh) | gbm | regime | trend_up |
|---|---|---|---|---|
| SL bor, 1 ATR bufer, 1 kunlik diapazon | -30% (0% foydali, 90 kunda ~50 SL) | -31% | -28% | -32% |
| SL bor, 20 daraja, 2 kunlik | -17% | -23% | -24% | -24% |
| SL yo'q, 4 kunlik diapazon | **+66% (100% foydali)** | +7% (56%) | +9% (64%) | **-24% (24%), DD -39%** |

Xulosa: "SL diapazon tashqarisiga albatta qo'yilishi shart" maslahati grid'ni o'ldiradi — real volatillikda
diapazon chegarasi doim tegadi. SL'siz grid faqat bozor haqiqatan yonbosh qolsa ishlaydi; trend boshlansa
bir harakatda -24..-40%. Bozor qachon yonbosh bo'lishini oldindan bilish mumkin emas — bu grid'ning asl xavfi.
Sof OU bozor sun'iy: BTC hech qachon 90 kun davomida OU bo'lmagan.

## 2. VWAP 2.5σ dan qaytish, TP 1σ da
Hajm sintetikda yo'q, VWAP o'rniga kunlik ankerli TWAP ishlatildi (xuddi shu mantiq).
15m: median **-43%**, 0% foydali, winrate 43%. 1h: -17%, winrate 42%. Kichik TP winrate'ni oshirmadi, chunki
2.5σ dan tashqariga chiqqan narx ko'pincha davom etadi (fat tails) va SL kattaroq.

## 3. Ko'p taymfreym confluence (1h trend + 15m daraja + rad etish shami + RSI)
Savdolar keskin kamaydi (0.3/kun) — bu da'voning to'g'ri qismi. Winrate 36%, median -8.8%, 8.5% foydali.
"75-85% winrate" tasdiqlanmadi. Hajm tasdig'i sintetikda yo'q.

## 4. Qisman TP (60% 1R da) + breakeven stop — da'vo: winrate'ni oshirishning eng sog'lom usuli
Barcha 47 strategiyada bir xil grafiklarda solishtirildi (9 400 backtest):
- winrate: **34.9% -> 45.8%** (da'vo TASDIQLANDI: winrate oshadi)
- median daromad: **-38.5% -> -42.7%** (lekin daromad TUSHDI)
- daromadi yaxshilangan: 4/47; foydaga chiqqan: 0/47.
Sabab: breakeven stop ko'p savdoni "nol" qiladi, lekin katta yutuqlarning yarmini erta yopadi. Winrate va
daromad har xil narsa: bu usul psixologik qulay, moliyaviy neytral yoki salbiy.

## 5. Likvidatsiya soyasini limit buyurtma bilan ushlash
Limit kirish (maker 0.02%), support -0.5 ATR, TP +1 ATR, SL 1.5 ATR. 15m: **-62%** (eng yomoni), winrate 47%.
Sintetik grafikda likvidatsiya kaskadi yo'q (bu real bozorning mikrostruktura hodisasi), shuning uchun
bu usulni sintetikda adolatli baholab bo'lmaydi — lekin "soya" bo'lmaganda strategiya oddiy pastga tushayotgan
pichoqni ushlashga aylanadi. Faqat real tick ma'lumotda tekshirish ma'noli.

## 6. Sessiya fakeout fade (Osiyo diapazoni, London ochilishi)
Winrate 54% (1h) / 40% (15m), median -3% / -11%, 30% / 10% foydali. Nazorat (tasodif): -5% / -43%.
15m da tasodifdan ancha yaxshi, lekin baribir manfiy. Sintetikda sessiya effekti yo'q (narx sessiyani bilmaydi),
real bozorda London ochilishi haqiqatan boshqacha — bu usul real ma'lumotda sinashga arziydi.

## 7. Order book devorlaridan skalping — SINAB BO'LMAYDI
Backtest uchun L2 stakan tarixi (har bir buyurtma) kerak; OHLC yetarli emas. Avtomatlashtirish uchun jonli
websocket stakan + soniyalar ichida qaror. Bu "strategiya" emas, qo'lda tajriba; bot sifatida faqat real
stakan ma'lumoti bilan yozish va sinash mumkin.

## 8. Funding rate arbitraji (spot long + futures short) — SINAB BO'LMAYDI, lekin hisoblash mumkin
Narxga bog'liq emas, backtest emas, arifmetika:
- Binance bazaviy funding 0.01%/8h = 0.03%/kun = **~11%/yil** (funding musbat bo'lganda). Real o'rtacha
  2023-2025 da taxminan 5-15%/yil, bull davrlarda 30%+, bear davrlarda manfiy (siz to'laysiz).
- Xarajat: spot xarid 0.1% + futures short 0.05% + yopish 0.15% = **~0.3%** har sikl; 0.03%/kun da 10 kun qoplaydi.
- Xavf: funding manfiyga o'tadi (chiqish kerak), futures tomoni likvidatsiya (1x da narx 2x oshsa; margin qo'shish kerak),
  spot va futures narxi farqi (basis) chiqishda.
- Winrate ma'nosiz (savdo yo'q); daromad past va barqaror. Bu 8 usuldan yagona matematik asosli daromad manbai,
  ammo "kuniga 3-4 savdo" emas, oylik pozitsiya. Halol nuqtai nazardan: bu aynan futures + funding (riba).

## Umumiy xulosa
| # | Usul | Da'vo qilingan winrate | Sinovda | Daromad |
|---|---|---|---|---|
| 1 | Grid | 85-95% | 100% (to'r savdolari) | SL bilan -17..-32%; SL'siz faqat sof yonboshda + |
| 2 | VWAP σ qaytish | yuqori | 42-43% | -17..-43% |
| 3 | MTF confluence | 75-85% | 36% | -9% |
| 4 | Qisman TP + BE | oshadi | 35% -> 46% (oshdi) | -38% -> -43% (tushdi) |
| 5 | Likvidatsiya soyasi | yuqori | 47% | -62% (sintetikda adolatsiz) |
| 6 | Sessiya fakeout | yuqori | 40-54% | -3..-11% (real ma'lumotda sinashga arziydi) |
| 7 | Order book devori | juda yuqori | sinab bo'lmaydi | — |
| 8 | Funding arbitraj | 90%+ | savdo yo'q | ~5-15%/yil, past xavf, halol emas |

Yuqori winrate ≠ foyda. Winrate'ni har doim oshirish mumkin (kichik TP, katta SL, breakeven), lekin
kutilgan daromad = winrate x o'rtacha yutuq - (1 - winrate) x o'rtacha yo'qotish - xarajatlar. 1-6 usullarda
xarajat va SL yo'qotishlari yutuqlardan katta. Faqat 6 (sessiya fakeout) va 5 (likvidatsiya soyasi) real
bozor mikrostrukturasiga tayanadi va sintetikda emas, real ma'lumotda sinalishi kerak (`run_zoo.py --csv`).
