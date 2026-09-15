# Smart Money Concepts (SMC/ICT) botlari: internet manbalari + o'z sinovimiz

## 1. Internetdagi ochiq manbalar nima deydi

Qidiruv: GitHub (ochiq kod), mustaqil backtest tadqiqotlari, TradingView skriptlari, blog/Medium da'volari.
Manbalar ishonchlilik darajasi bo'yicha ajratildi.

### A. Mustaqil, metodologiyasi ochiq tadqiqotlar (eng ishonchli)
| Manba | Nima sinaldi | Natija |
|---|---|---|
| StatOasis "ICT backtest — what survives" | OB (18 variant), FVG (18), liquidity sweep (3), OTE (6) = 648 mexanik konfiguratsiya, SPY/QQQ/DIA/IWM, kunlik, 1993+ | **Hech biri statistik ahamiyatli edge bermadi** (eng yaxshisi OB/SPY, t = +1.22). 648 dan 0 tasi indeksni ushlab turishdan yaxshi emas. |
| FXNX "Do SMC work? backtest evidence" | Asosiy juftlarda mexanik SMC kirishlar | Xom winrate **38-45%**. Qarama-qarshi likvidlik hovuzida TP olinsa 55-62%, lekin R kichik. |
| elabel17/mnq-ict-smc-bot (GitHub, MNQ, Pine + Python) | OB + FVG + BOS + likvidlik, NY sessiya | Python dvigatelda **7 ta look-ahead xatosi** topildi. Tuzatishdan oldin +$1 625 bashorat, aslida -$832. Tuzatilgach PF **1.03**; 160 konfiguratsiya qidiruvida maksimal PF 1.13. Faqat bitta 15m variant tick-by-tick tekshirilgan (55 savdo, PF 2.12, 4 oy) — namuna juda kichik. |
| islero/ICT-NT (GitHub, ES futures) | FVG + likvidlik + Turtle Soup, 2025 yil 10 oy | Winrate **35.4%**, PF 1.34, 79 pozitsiya, +13.5%. Forward test yo'q. |
| starckyang/smc_quant (GitHub, ETHUSDT) | OB + FVG + BOS, kirish OB retest | Training 2020-21: winrate **23%**, +92%; test 2024: winrate **50%**, +53%, DD 16.6%. Trendda ishlaydi, yonboshda ko'p soxta signal. |
| prashanthaitha24/nq-strategy-b-bot (GitHub, MNQ) | 5m FVG ichida 15m FVG, long-only, 09:30-12:00 ET | 2023-2026: 432 savdo, winrate **46-68%** (o'rtacha 53.5%), PF 2.3, DD $786. Out-of-sample ajratilmagan, bitta bozor, bitta yo'nalish. |
| foeed/FvgGold-EA (GitHub, XAUUSD M15, MQL5) | Ballli FVG + OB, RR 1.5, kill zone | 6 oy: winrate **45.3%**, +48.7%, 64 savdo; 3 oy: 40%, +5.2%. PF/DD oshkor qilinmagan, forward test yo'q. |

### B. Da'volar (kod yoki hisobot ochiq emas)
| Manba | Da'vo | Dalil |
|---|---|---|
| YouTube/bloglar: "ICT Silver Bullet 72% winrate", "70-80%" | 70-80% | Qo'lda backtest, davr tanlangan; o'sha manbalar "2023 dan oldin natija butunlay boshqacha" deb tan oladi. Qat'iy ijroda 55-65%. |
| Medium "2 600 savdo, 61% winrate, PF 2.17, +2.27R" | 61% | Qo'lda, mualliflik tanlovi, kod yo'q, out-of-sample yo'q. |
| Medium "AI-bot XAUUSD 70% winrate, +5 381%" | 70% | Dalil yo'q; +5 381% real emas. |
| NadirAliOfficial/STAR-EA (GitHub, MQL5) | XAUUSD H1: PF 2.57, winrate 62.5%, DD 2.28% | Faqat .mq5 fayl; hisobot, equity curve, savdo jurnali yo'q. |
| "Liquidity sweep 60-70% winrate" (bloglar, YouTube "75%") | 60-75% | Qo'lda, tasdiq shartlari sub'ektiv. |
| Steve292/Xtrade, Prasad1612/SMC-Screener, joshyattridge/smart-money-concepts | Kod bor | Natija e'lon qilinmagan; kutubxonalar indikator, strategiya emas. |

### C. Umumiy qonuniyat
- **Kod ochiq va metodologiya qat'iy bo'lgan sari winrate 23-45% ga tushadi.** 60-80% raqamlar faqat qo'lda backtest va yopiq kodda uchraydi.
- Eng halol GitHub loyihasi (mnq-ict-smc-bot) o'z-o'zini fosh qildi: 7 look-ahead xatosi, tuzatilgach PF 1.03 (nol edge).
- SMC "bot"larining aksariyati aslida indikator (chizadi), savdo qoidasi va natijasi yo'q.
- Eng yirik mexanik tadqiqot (648 konfiguratsiya, 30 yil) hech qanday edge topmadi.

## 2. O'z sinovimiz: 8 SMC strategiya, sintetik futures (3x, 0.05%, 15m va 1h)

Qoidalar joshyattridge kutubxonasi ta'riflari bo'yicha, **causal** (swing'lar faqat 10 sham o'tgach tasdiqlanadi,
95 ta look-ahead testi o'tgan). 5 rejim x 40 grafik x 90 kun = 3 600 backtest.

| Strategiya | 15m median | 15m winrate | 1h median | 1h winrate | 1h foydali grafik |
|---|---|---|---|---|---|
| CHoCH reversal | -1.8% | 39% | **-0.4%** | 39% | 44.5% |
| Silver Bullet (kill zone sweep) | -6.5% | 36% | -1.3% | 36% | 38% |
| OTE 70.5% retracement | -13.9% | 30% | -3.4% | 30% | 30% |
| Order block retest (limit) | -48.1% | 30% | -11.0% | 31% | 11% |
| Liquidity sweep reversal | -46.0% | 28% | -11.1% | 28% | 19.5% |
| Turtle Soup 20 | -68.2% | 35% | -23.3% | 36% | 3% |
| FVG retest (limit) | -74.1% | 31% | -34.5% | 32% | 2% |
| FVG+OB ballli confluence, RR 1.5 | -84.7% | 28% | -57.3% | 33% | 0% |
| *Nazorat: tasodifiy kirish* | -42.5% | 40% | -5.2% | 40% | 25% |

- Mezondan (median > 0, 55%+ foydali) **0 / 16 o'tdi**.
- Winrate 28-40%: internetdagi mustaqil tadqiqotlar (38-45%) bilan mos, "70-80%" bilan emas.
- Komissiyasiz (gross) eng yaxshisi +0.5% (CHoCH 15m): sof edge nol.
- Eng yaxshi ikkitasi (CHoCH, Silver Bullet 1h) tasodifiy kirishdan yaxshi, lekin nol atrofida. Kuniga 0.1 savdo.
- "Confluence" (ko'p shart) yaxshilamadi, yomonlashtirdi: 15m da -85%. Ko'p filtr = ko'p tanlov erkinligi = overfitting.

## 3. Javob: "eng yuqori winrate'li SMC bot" qaysi?
Ochiq manbalarda **tekshirilgan** (kod + hisobot + out-of-sample) va winrate 60%+ bo'lgan SMC bot **topilmadi**.
Eng yaqini prashanthaitha24/nq-strategy-b-bot (MNQ, long-only, 53.5%, PF 2.3), lekin out-of-sample yo'q va
bitta bozor. Sintetik sinovda ham, 30 yillik indeks tadqiqotida ham mexanik SMC edge bermadi.

SMC'ning haqiqiy natijasi qo'lda savdo qiluvchi odamga bog'liq (sub'ektiv zona tanlovi). Uni botga aylantirganda
sub'ektivlik yo'qoladi va winrate 30-45% ga tushadi. Shuning uchun "SMC bot 80% winrate" reklamalari
yo qo'lda backtest, yo look-ahead, yo tanlangan davr.

Real ma'lumotda tekshirish: `python3 run_zoo.py --family smc --csv <TradingView eksport>.csv`.
