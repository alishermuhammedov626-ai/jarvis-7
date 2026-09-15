# Strategiyalar kutubxonasi — sintetik futures sinovi

- Rejim: Binance USD-M perpetual modeli, leverage 3.0x, taker 0.050%, slippage 0.02%, funding 0.01%/8h, kuniga max 4 kirish
- 9 strategiya x 2 timeframe = 18 sinov; 1-bosqich 40 grafik/rejim x 5 rejim, 90 kun; jami 3600 backtest
- O'tish mezoni: median daromad > 0, foydali grafiklar >= 55%, likvidatsiya < 5%

## 1-bosqich: barcha strategiyalar (median daromad bo'yicha)

| tf | strategy | family | median_ret | pct_profitable | p05 | p95 | median_gross | median_dd | liq_pct | tpd | win_rate | med_gbm | med_regime | med_trend_up | med_trend_down |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1h | smc_choch_reversal | smc | -0.4 | 44.5 | -6.6 | 5.9 | -0.1 | -4.3 | 0.0 | 0.1 | 39.0 | 0.3 | -1.3 | 0.1 | -1.4 |
| 1h | smc_silver_bullet_killzone | smc | -1.3 | 38.0 | -7.2 | 5.4 | -0.8 | -4.2 | 0.0 | 0.1 | 36.1 | -0.9 | -0.8 | -2.3 | -1.3 |
| 15m | smc_choch_reversal | smc | -1.8 | 40.0 | -12.2 | 11.6 | 0.5 | -9.2 | 0.0 | 0.4 | 39.2 | -0.7 | -5.1 | -1.8 | -2.0 |
| 1h | smc_ote_705_retracement | smc | -3.4 | 30.0 | -11.3 | 7.6 | -2.5 | -7.4 | 0.0 | 0.2 | 29.9 | -1.9 | -5.9 | -1.4 | -3.5 |
| 1h | control_random_entry | control | -5.2 | 25.0 | -20.8 | 7.4 | -1.4 | -11.9 | 0.0 | 0.7 | 39.8 | -3.9 | -5.4 | -8.6 | -5.1 |
| 15m | smc_silver_bullet_killzone | smc | -6.5 | 12.5 | -20.7 | 3.5 | 0.2 | -11.1 | 0.0 | 0.3 | 36.0 | -5.2 | -7.1 | -6.7 | -7.0 |
| 1h | smc_order_block_retest | smc | -11.0 | 11.0 | -24.5 | 4.7 | -7.3 | -15.0 | 0.0 | 0.4 | 31.1 | -6.4 | -14.9 | -10.6 | -10.8 |
| 1h | smc_liquidity_sweep_reversal | smc | -11.1 | 19.5 | -28.5 | 12.7 | -2.7 | -19.5 | 0.0 | 0.7 | 28.5 | -11.8 | -4.8 | -13.1 | -12.9 |
| 15m | smc_ote_705_retracement | smc | -13.9 | 9.0 | -27.2 | 2.3 | -7.4 | -18.6 | 0.0 | 0.6 | 30.1 | -15.3 | -14.7 | -11.4 | -14.1 |
| 1h | smc_turtle_soup_20 | smc | -23.3 | 3.0 | -43.8 | -1.4 | -4.9 | -29.4 | 0.0 | 1.5 | 35.9 | -21.8 | -17.8 | -26.6 | -25.9 |
| 1h | smc_fvg_retest_limit | smc | -34.5 | 2.0 | -51.2 | -14.2 | -21.0 | -38.6 | 0.0 | 1.5 | 32.4 | -35.1 | -39.6 | -33.7 | -34.3 |
| 15m | control_random_entry | control | -42.5 | 0.0 | -59.3 | -17.7 | -11.2 | -45.5 | 0.0 | 2.7 | 40.1 | -39.4 | -46.6 | -42.0 | -46.3 |
| 15m | smc_liquidity_sweep_reversal | smc | -46.0 | 0.0 | -61.5 | -30.0 | -6.7 | -50.4 | 0.0 | 2.2 | 28.5 | -46.1 | -40.5 | -47.0 | -47.8 |
| 15m | smc_order_block_retest | smc | -48.1 | 0.0 | -61.2 | -31.5 | -28.0 | -49.7 | 0.0 | 1.8 | 29.6 | -45.9 | -51.9 | -48.6 | -45.2 |
| 1h | smc_fvg_ob_confluence_score50_rr1.5 | smc | -57.3 | 0.0 | -71.0 | -35.3 | -39.2 | -58.3 | 0.0 | 1.5 | 33.0 | -55.4 | -58.8 | -58.4 | -57.3 |
| 15m | smc_turtle_soup_20 | smc | -68.2 | 0.0 | -77.9 | -55.9 | -15.3 | -69.8 | 0.0 | 3.6 | 35.3 | -67.9 | -68.5 | -69.5 | -67.6 |
| 15m | smc_fvg_retest_limit | smc | -74.1 | 0.0 | -82.6 | -63.3 | -39.5 | -74.9 | 0.0 | 3.9 | 30.7 | -72.8 | -75.9 | -75.1 | -73.6 |
| 15m | smc_fvg_ob_confluence_score50_rr1.5 | smc | -84.7 | 0.0 | -89.4 | -79.3 | -51.6 | -84.8 | 0.0 | 3.9 | 28.0 | -86.6 | -84.6 | -84.3 | -84.1 |

## Nazorat (tasodifiy kirish)

| tf | median_ret | pct_profitable | median_gross | tpd |
|---|---|---|---|---|
| 1h | -5.2 | 25.0 | -1.4 | 0.7 |
| 15m | -42.5 | 0.0 | -11.2 | 2.7 |

## 1-bosqich nomzodlari: 0


## YAKUN: 0 strategiya barcha bosqichlardan o'tdi

Hech biri. Sintetik grafiklarda birorta strategiya tasodifdan ishonchli farq qilmadi.