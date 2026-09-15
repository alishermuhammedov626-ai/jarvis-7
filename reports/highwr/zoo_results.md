# Strategiyalar kutubxonasi — sintetik futures sinovi

- Rejim: Binance USD-M perpetual modeli, leverage 3.0x, taker 0.050%, slippage 0.02%, funding 0.01%/8h, kuniga max 4 kirish
- 6 strategiya x 2 timeframe = 12 sinov; 1-bosqich 40 grafik/rejim x 5 rejim, 90 kun; jami 2400 backtest
- O'tish mezoni: median daromad > 0, foydali grafiklar >= 55%, likvidatsiya < 5%

## 1-bosqich: barcha strategiyalar (median daromad bo'yicha)

| tf | strategy | family | median_ret | pct_profitable | p05 | p95 | median_gross | median_dd | liq_pct | tpd | win_rate | med_gbm | med_regime | med_trend_up | med_trend_down |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1h | hw_mtf_confluence_1h_15m_rejection_rsi | highwr | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 1h | hw_session_fakeout_fade_london | highwr | -3.2 | 30.5 | -10.6 | 6.6 | -1.2 | -6.0 | 0.0 | 0.2 | 54.2 | -3.6 | -1.8 | -3.0 | -4.0 |
| 1h | control_random_entry | control | -5.2 | 25.0 | -20.8 | 7.4 | -1.4 | -11.9 | 0.0 | 0.7 | 39.8 | -3.9 | -5.4 | -8.6 | -5.1 |
| 15m | hw_mtf_confluence_1h_15m_rejection_rsi | highwr | -8.8 | 8.5 | -20.0 | 3.3 | -1.8 | -11.6 | 0.0 | 0.3 | 36.4 | -8.8 | -10.8 | -9.1 | -7.3 |
| 15m | hw_session_fakeout_fade_london | highwr | -10.9 | 10.0 | -22.5 | 3.9 | -2.9 | -14.4 | 0.0 | 0.5 | 40.1 | -11.1 | -10.2 | -10.9 | -11.5 |
| 1h | hw_grid_neutral_10_levels_sl | highwr | -11.2 | 27.5 | -33.7 | 14.1 | -9.0 | -21.8 | 0.0 | 1.4 | 100.0 | -12.7 | -3.8 | -9.3 | -11.3 |
| 1h | hw_liquidation_wick_limit_order | highwr | -12.0 | 3.5 | -19.4 | -1.6 | -8.6 | -14.4 | 0.0 | 0.7 | 52.4 | -10.4 | -7.0 | -15.0 | -14.3 |
| 1h | hw_vwap_2.5sigma_tp_1sigma | highwr | -17.1 | 6.0 | -36.6 | 0.8 | -7.2 | -21.5 | 0.0 | 0.9 | 42.5 | -15.5 | -13.9 | -20.6 | -17.9 |
| 15m | hw_grid_neutral_10_levels_sl | highwr | -28.1 | 1.0 | -42.9 | -9.9 | -20.3 | -31.2 | 0.0 | 4.5 | 100.0 | -34.2 | -27.1 | -26.9 | -28.9 |
| 15m | control_random_entry | control | -42.5 | 0.0 | -59.3 | -17.7 | -11.2 | -45.5 | 0.0 | 2.7 | 40.1 | -39.4 | -46.6 | -42.0 | -46.3 |
| 15m | hw_vwap_2.5sigma_tp_1sigma | highwr | -43.5 | 0.0 | -53.8 | -24.6 | -13.8 | -45.0 | 0.0 | 2.4 | 42.9 | -37.1 | -41.6 | -45.4 | -45.9 |
| 15m | hw_liquidation_wick_limit_order | highwr | -62.1 | 0.0 | -70.9 | -52.7 | -39.3 | -62.4 | 0.0 | 2.5 | 47.5 | -61.0 | -59.0 | -63.9 | -63.0 |

## Nazorat (tasodifiy kirish)

| tf | median_ret | pct_profitable | median_gross | tpd |
|---|---|---|---|---|
| 1h | -5.2 | 25.0 | -1.4 | 0.7 |
| 15m | -42.5 | 0.0 | -11.2 | 2.7 |

## 1-bosqich nomzodlari: 0


## YAKUN: 0 strategiya barcha bosqichlardan o'tdi

Hech biri. Sintetik grafiklarda birorta strategiya tasodifdan ishonchli farq qilmadi.