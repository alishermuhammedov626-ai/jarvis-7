# Xulosa: kuniga 3-4 savdo, Binance, halol — sintetik sinov natijasi

## Savolga javob
- Futures: halol emas (funding = riba, leverage = qarz, short = yo'q narsani sotish). Bot spot-only qilindi.
- Kuniga 3-4 savdo: sintetik grafiklarda birorta variant komissiyadan omon qolmadi.

## Sinov hajmi
- 5 rejim (gbm, garch, regime, trend_up, trend_down) x 60 grafik x 3 mustaqil partiya = 900 grafik, 90 kun, 15m.
- 6 strategiya x 3 komissiya ssenariysi = 16 200 backtest. + 13 parametr varianti x 200 grafik x 2 komissiya = 5 200 backtest.
- Look-ahead testi barcha strategiyalarga (bitta variantda look-ahead topildi va tuzatildi: F, 4h trend filtri —
  tuzatishdan oldin "+22% gross", tuzatishdan keyin -14..-27%).

## Raqamlar (0.10% komissiya, 90 kun, median)
| Variant | savdo/kun | median daromad | foydali grafiklar |
|---|---|---|---|
| D sessiya ORB (eng ko'p savdo) | 2.4 | -33 .. -41% | 0% |
| A trend pullback | 1.8 | -27 .. -32% | 0% |
| B Donchian breakout | 1.4 | -23 .. -29% | 0-1% |
| C Bollinger 15m | 1.0 | -11 .. -20% | 1-11% |
| E RSI scalp | 0.7 | -13 .. -16% | 0% |
| B2 Donchian 96 + trailing 4ATR | 0.7 | -8 .. -15% | 10-35% |
| **C3 Bollinger 1h** | **0.25** | **-5 .. +2%** | **35-62%** |
| Buy & hold | — | -32 .. +43% | 8-88% |

Qonuniyat aniq: savdo qancha ko'p bo'lsa, zarar shuncha katta. 0.10% x 2 tomon + slippage = ~0.24%/savdo.

## Tavsiya
1. "Kuniga 3-4 savdo" talabidan voz keching yoki uni haqiqiy ma'lumotda isbotlang (sintetikda isbot yo'q).
2. Eng halol va xavfsiz: past chastota (C3 kabi, 1h+) yoki DCA.
3. Har qanday jonli ishga tushirishdan oldin testnetda kamida 2-4 hafta dry-run.
