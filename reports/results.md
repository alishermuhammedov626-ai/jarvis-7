# Monte-Carlo natijalari

- Grafiklar: 60 x 5 rejim x 3 partiya = 900 sintetik grafik, har biri 90 kun (15m)
- Backtestlar soni: 16200
- Kuniga maksimal savdo: 4; spot, long-only, leverage yo'q
- Ustunlar: daromad % (90 kun), p05/p95 = 5%/95% kvantil, pct_profitable = foydali grafiklar ulushi,
  median_gross = komissiyasiz daromad (sof 'edge'), trades_per_day, median_excess_vs_bh = buy&hold ga nisbatan

## Xulosa jadvallari

#### fee_0%_nazariy | rejim: garch (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -4.5 | -16.2 | 9.6 | 28.3 | -4.5 | -9.7 | -25.0 | 1.7 | 40.2 | -6.8 |
| B_donchian_breakout | -5.5 | -17.4 | 9.7 | 23.9 | -5.5 | -11.5 | -26.6 | 1.4 | 35.5 | -5.5 |
| C_bollinger_meanrev | 1.0 | -13.2 | 17.8 | 55.0 | 1.0 | -8.0 | -20.6 | 1.0 | 44.9 | 0.5 |
| D_session_orb | -7.9 | -20.8 | 7.6 | 18.9 | -7.9 | -14.0 | -31.0 | 2.3 | 46.2 | -7.1 |
| E_rsi_scalp | -2.7 | -8.3 | 4.1 | 26.7 | -2.7 | -4.9 | -16.0 | 0.7 | 39.8 | -2.4 |
| Z_buy_hold | -1.1 | -37.2 | 60.3 | 48.9 | -1.1 | -28.9 | -57.0 | 0.0 | 48.9 | -0.0 |

#### fee_0%_nazariy | rejim: gbm (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -3.0 | -15.0 | 9.4 | 35.6 | -3.0 | -10.0 | -21.3 | 1.8 | 40.7 | -4.3 |
| B_donchian_breakout | -1.7 | -16.2 | 20.2 | 41.1 | -1.7 | -10.7 | -26.8 | 1.4 | 36.0 | -3.2 |
| C_bollinger_meanrev | 2.2 | -11.6 | 16.6 | 64.4 | 2.2 | -7.6 | -24.3 | 0.9 | 46.9 | 1.1 |
| D_session_orb | -8.4 | -23.8 | 11.9 | 25.6 | -8.4 | -15.8 | -34.5 | 2.4 | 46.4 | -8.4 |
| E_rsi_scalp | -2.0 | -7.8 | 3.1 | 27.2 | -2.0 | -5.0 | -12.4 | 0.7 | 40.5 | -0.3 |
| Z_buy_hold | -0.5 | -36.1 | 58.7 | 47.8 | -0.5 | -29.1 | -60.0 | 0.0 | 47.8 | -0.0 |

#### fee_0%_nazariy | rejim: regime (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -6.9 | -17.8 | 4.3 | 15.6 | -6.9 | -11.5 | -28.4 | 1.8 | 38.7 | -11.8 |
| B_donchian_breakout | -9.2 | -20.1 | 5.2 | 16.1 | -9.2 | -14.0 | -27.3 | 1.4 | 34.2 | -12.9 |
| C_bollinger_meanrev | 3.6 | -8.2 | 18.8 | 70.0 | 3.6 | -7.5 | -21.4 | 1.0 | 46.3 | 2.4 |
| D_session_orb | -8.5 | -20.4 | 6.5 | 16.7 | -8.5 | -14.0 | -30.6 | 2.3 | 46.0 | -8.8 |
| E_rsi_scalp | -2.6 | -8.5 | 3.3 | 21.7 | -2.6 | -5.1 | -17.5 | 0.8 | 38.9 | -5.9 |
| Z_buy_hold | 2.5 | -29.7 | 48.2 | 53.3 | 2.5 | -25.2 | -54.1 | 0.0 | 53.3 | -0.0 |

#### fee_0%_nazariy | rejim: trend_down (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -6.3 | -16.8 | 6.2 | 16.1 | -6.3 | -10.3 | -23.7 | 1.4 | 38.4 | 23.3 |
| B_donchian_breakout | -8.1 | -18.1 | 5.7 | 15.0 | -8.1 | -11.9 | -22.3 | 1.1 | 33.8 | 23.0 |
| C_bollinger_meanrev | -1.5 | -16.0 | 15.3 | 42.2 | -1.5 | -9.7 | -23.9 | 1.2 | 42.6 | 29.2 |
| D_session_orb | -13.6 | -25.8 | 1.0 | 7.8 | -13.6 | -17.6 | -36.0 | 2.3 | 44.1 | 17.8 |
| E_rsi_scalp | -2.9 | -8.5 | 3.0 | 21.1 | -2.9 | -4.9 | -14.3 | 0.6 | 38.3 | 28.5 |
| Z_buy_hold | -31.6 | -56.6 | 10.7 | 8.3 | -31.6 | -42.2 | -69.5 | 0.0 | 8.3 | -0.0 |

#### fee_0%_nazariy | rejim: trend_up (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -0.3 | -13.4 | 13.8 | 48.9 | -0.3 | -8.7 | -21.1 | 2.0 | 42.7 | -44.0 |
| B_donchian_breakout | -1.8 | -15.3 | 14.2 | 45.6 | -1.8 | -10.0 | -24.6 | 1.6 | 37.6 | -45.2 |
| C_bollinger_meanrev | 3.8 | -8.9 | 19.3 | 71.1 | 3.8 | -7.1 | -21.6 | 0.9 | 46.6 | -40.8 |
| D_session_orb | 0.1 | -15.0 | 15.3 | 51.1 | 0.1 | -10.6 | -27.9 | 2.4 | 48.7 | -45.1 |
| E_rsi_scalp | -2.1 | -8.3 | 5.1 | 30.6 | -2.1 | -5.1 | -14.2 | 0.8 | 41.5 | -45.5 |
| Z_buy_hold | 43.2 | -9.0 | 132.0 | 87.8 | 43.2 | -20.5 | -40.9 | 0.0 | 87.8 | -0.1 |

#### fee_0.075%_BNB | rejim: garch (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -23.9 | -33.3 | -13.3 | 0.0 | -3.9 | -25.3 | -38.9 | 1.7 | 40.1 | -26.4 |
| B_donchian_breakout | -21.1 | -32.9 | -8.4 | 0.0 | -5.1 | -23.0 | -38.0 | 1.4 | 28.8 | -21.6 |
| C_bollinger_meanrev | -11.7 | -24.2 | 3.9 | 11.7 | 0.8 | -15.1 | -31.2 | 1.0 | 42.8 | -11.8 |
| D_session_orb | -30.9 | -41.5 | -20.8 | 0.0 | -6.4 | -32.6 | -46.8 | 2.3 | 43.4 | -31.2 |
| E_rsi_scalp | -11.6 | -17.5 | -5.3 | 0.0 | -2.5 | -12.1 | -23.9 | 0.7 | 39.7 | -12.1 |
| Z_buy_hold | -1.2 | -37.3 | 60.0 | 48.3 | -1.1 | -28.9 | -57.0 | 0.0 | 48.3 | -0.2 |

#### fee_0.075%_BNB | rejim: gbm (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -23.0 | -33.2 | -12.6 | 0.0 | -2.9 | -24.9 | -38.3 | 1.8 | 40.7 | -23.9 |
| B_donchian_breakout | -18.2 | -30.6 | -1.3 | 5.0 | -1.4 | -21.2 | -39.6 | 1.4 | 30.7 | -20.1 |
| C_bollinger_meanrev | -9.2 | -22.8 | 3.2 | 12.2 | 2.0 | -13.6 | -33.2 | 0.9 | 45.9 | -10.5 |
| D_session_orb | -31.1 | -42.7 | -17.1 | 0.6 | -7.2 | -33.5 | -49.6 | 2.4 | 44.0 | -31.4 |
| E_rsi_scalp | -10.9 | -16.7 | -4.9 | 0.0 | -1.8 | -11.6 | -20.8 | 0.7 | 40.5 | -9.2 |
| Z_buy_hold | -0.6 | -36.2 | 58.5 | 47.8 | -0.5 | -29.1 | -60.0 | 0.0 | 47.8 | -0.2 |

#### fee_0.075%_BNB | rejim: regime (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -26.1 | -34.4 | -18.1 | 0.0 | -6.1 | -27.5 | -44.0 | 1.8 | 38.5 | -30.8 |
| B_donchian_breakout | -24.5 | -35.4 | -12.5 | 0.0 | -8.5 | -26.6 | -40.3 | 1.4 | 27.1 | -27.6 |
| C_bollinger_meanrev | -8.7 | -21.6 | 4.7 | 12.8 | 3.2 | -13.6 | -31.3 | 1.0 | 44.4 | -10.1 |
| D_session_orb | -31.6 | -40.5 | -20.1 | 0.0 | -7.0 | -32.7 | -45.7 | 2.3 | 42.8 | -32.2 |
| E_rsi_scalp | -12.1 | -18.3 | -6.2 | 0.0 | -2.5 | -12.7 | -25.2 | 0.8 | 38.8 | -15.6 |
| Z_buy_hold | 2.4 | -29.8 | 48.0 | 53.3 | 2.5 | -25.2 | -54.1 | 0.0 | 53.3 | -0.2 |

#### fee_0.075%_BNB | rejim: trend_down (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -22.5 | -30.9 | -12.7 | 0.0 | -5.7 | -23.7 | -38.6 | 1.4 | 38.2 | 6.9 |
| B_donchian_breakout | -20.6 | -30.6 | -8.6 | 0.0 | -7.4 | -22.5 | -34.8 | 1.1 | 27.2 | 10.0 |
| C_bollinger_meanrev | -15.7 | -29.0 | -0.5 | 5.0 | -1.5 | -18.9 | -35.4 | 1.2 | 40.8 | 14.8 |
| D_session_orb | -34.9 | -44.1 | -24.4 | 0.0 | -11.9 | -35.9 | -51.2 | 2.3 | 41.2 | -4.1 |
| E_rsi_scalp | -11.1 | -16.5 | -5.1 | 0.0 | -2.9 | -11.5 | -21.8 | 0.6 | 38.2 | 20.0 |
| Z_buy_hold | -31.7 | -56.7 | 10.5 | 8.3 | -31.6 | -42.2 | -69.5 | 0.0 | 8.3 | -0.1 |

#### fee_0.075%_BNB | rejim: trend_up (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -24.0 | -33.9 | -12.8 | 0.0 | -0.1 | -25.6 | -41.0 | 2.0 | 42.5 | -68.9 |
| B_donchian_breakout | -20.0 | -31.6 | -7.1 | 0.6 | -1.3 | -22.1 | -38.6 | 1.6 | 30.6 | -64.0 |
| C_bollinger_meanrev | -7.7 | -20.2 | 7.3 | 17.8 | 3.6 | -12.2 | -30.3 | 0.9 | 44.8 | -52.0 |
| D_session_orb | -25.9 | -37.7 | -14.9 | 0.0 | -0.1 | -28.4 | -44.6 | 2.4 | 45.9 | -72.0 |
| E_rsi_scalp | -12.5 | -18.9 | -6.2 | 0.6 | -1.8 | -12.9 | -24.4 | 0.8 | 41.4 | -56.5 |
| Z_buy_hold | 43.0 | -9.2 | 131.6 | 87.8 | 43.2 | -20.5 | -40.9 | 0.0 | 87.8 | -0.3 |

#### fee_0.10% | rejim: garch (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -29.8 | -38.5 | -19.8 | 0.0 | -3.7 | -30.7 | -42.9 | 1.7 | 40.0 | -32.0 |
| B_donchian_breakout | -25.6 | -37.2 | -13.7 | 0.0 | -5.2 | -27.2 | -42.0 | 1.4 | 26.9 | -26.4 |
| C_bollinger_meanrev | -15.5 | -27.5 | -0.5 | 4.4 | 0.8 | -18.5 | -34.9 | 1.0 | 42.0 | -15.4 |
| D_session_orb | -37.4 | -47.3 | -28.2 | 0.0 | -5.9 | -38.5 | -51.3 | 2.3 | 42.4 | -37.4 |
| E_rsi_scalp | -14.6 | -20.5 | -8.0 | 0.0 | -2.5 | -14.8 | -26.4 | 0.7 | 39.7 | -14.9 |
| Z_buy_hold | -1.3 | -37.3 | 59.9 | 48.3 | -1.1 | -28.9 | -57.0 | 0.0 | 48.3 | -0.2 |

#### fee_0.10% | rejim: gbm (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -29.0 | -37.7 | -18.7 | 0.0 | -2.8 | -30.2 | -43.2 | 1.8 | 40.7 | -29.7 |
| B_donchian_breakout | -23.2 | -34.8 | -7.3 | 1.1 | -1.4 | -25.4 | -43.9 | 1.4 | 29.0 | -25.1 |
| C_bollinger_meanrev | -12.7 | -26.2 | -0.6 | 4.4 | 2.0 | -16.2 | -36.1 | 0.9 | 45.3 | -13.9 |
| D_session_orb | -37.5 | -47.9 | -24.9 | 0.0 | -6.8 | -39.2 | -53.8 | 2.4 | 43.2 | -38.0 |
| E_rsi_scalp | -13.5 | -19.5 | -7.8 | 0.0 | -1.8 | -13.8 | -23.4 | 0.7 | 40.4 | -12.0 |
| Z_buy_hold | -0.7 | -36.2 | 58.4 | 47.8 | -0.5 | -29.1 | -60.0 | 0.0 | 47.8 | -0.2 |

#### fee_0.10% | rejim: regime (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -32.1 | -40.1 | -23.5 | 0.0 | -5.8 | -32.8 | -48.4 | 1.8 | 38.4 | -36.6 |
| B_donchian_breakout | -29.3 | -39.4 | -17.1 | 0.0 | -8.2 | -30.5 | -44.1 | 1.4 | 25.2 | -31.7 |
| C_bollinger_meanrev | -12.5 | -25.7 | 1.0 | 6.7 | 3.2 | -16.2 | -34.3 | 1.0 | 43.5 | -13.7 |
| D_session_orb | -37.8 | -46.1 | -27.4 | 0.0 | -6.7 | -38.7 | -51.0 | 2.3 | 41.8 | -39.0 |
| E_rsi_scalp | -15.0 | -21.5 | -8.9 | 0.0 | -2.4 | -15.4 | -27.7 | 0.8 | 38.4 | -18.6 |
| Z_buy_hold | 2.3 | -29.8 | 47.9 | 53.3 | 2.5 | -25.2 | -54.1 | 0.0 | 53.3 | -0.2 |

#### fee_0.10% | rejim: trend_down (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -27.1 | -35.3 | -18.1 | 0.0 | -5.5 | -28.0 | -42.9 | 1.4 | 38.1 | 2.8 |
| B_donchian_breakout | -24.3 | -34.5 | -13.5 | 0.0 | -7.3 | -25.8 | -38.6 | 1.1 | 25.4 | 6.3 |
| C_bollinger_meanrev | -20.0 | -33.4 | -4.6 | 0.6 | -1.4 | -22.0 | -38.8 | 1.2 | 39.8 | 10.7 |
| D_session_orb | -40.7 | -49.1 | -31.1 | 0.0 | -11.6 | -41.4 | -55.7 | 2.3 | 40.1 | -9.7 |
| E_rsi_scalp | -13.5 | -19.4 | -7.9 | 0.0 | -2.8 | -14.0 | -24.4 | 0.6 | 38.2 | 17.5 |
| Z_buy_hold | -31.8 | -56.7 | 10.5 | 8.3 | -31.6 | -42.2 | -69.5 | 0.0 | 8.3 | -0.2 |

#### fee_0.10% | rejim: trend_up (n=180 grafik)

| strategy | median_ret | p05_ret | p95_ret | pct_profitable | median_gross | median_dd | worst_dd | trades_per_day | win_rate | median_excess_vs_bh |
|---|---|---|---|---|---|---|---|---|---|---|
| A_trend_pullback | -30.3 | -39.9 | -20.1 | 0.0 | -0.1 | -31.5 | -46.9 | 2.0 | 42.4 | -75.2 |
| B_donchian_breakout | -25.7 | -36.3 | -12.8 | 0.0 | -1.3 | -26.7 | -42.8 | 1.6 | 28.7 | -69.3 |
| C_bollinger_meanrev | -11.2 | -24.0 | 3.5 | 10.6 | 3.5 | -14.7 | -33.0 | 0.9 | 44.1 | -55.3 |
| D_session_orb | -33.3 | -44.0 | -23.0 | 0.0 | -0.1 | -34.8 | -49.5 | 2.4 | 44.9 | -79.2 |
| E_rsi_scalp | -15.6 | -22.2 | -9.7 | 0.0 | -1.7 | -16.0 | -27.8 | 0.8 | 41.4 | -59.8 |
| Z_buy_hold | 42.9 | -9.2 | 131.5 | 87.8 | 43.2 | -20.5 | -40.9 | 0.0 | 87.8 | -0.3 |

## Partiyalar orasidagi barqarorlik (median daromad har partiyada, fee 0.10%)

| regime | strategy | 0 | 1 | 2 | spread |
|---|---|---|---|---|---|
| garch | A_trend_pullback | -29.3 | -30.0 | -30.2 | 1.0 |
| garch | B_donchian_breakout | -24.9 | -26.6 | -25.8 | 1.7 |
| garch | C_bollinger_meanrev | -14.9 | -14.6 | -16.4 | 1.8 |
| garch | D_session_orb | -37.0 | -37.5 | -38.4 | 1.4 |
| garch | E_rsi_scalp | -13.6 | -15.0 | -14.6 | 1.3 |
| garch | Z_buy_hold | -7.1 | 3.2 | -0.1 | 10.4 |
| gbm | A_trend_pullback | -28.2 | -30.0 | -28.7 | 1.8 |
| gbm | B_donchian_breakout | -22.1 | -24.1 | -23.4 | 2.0 |
| gbm | C_bollinger_meanrev | -13.9 | -11.6 | -12.3 | 2.3 |
| gbm | D_session_orb | -36.8 | -37.6 | -38.5 | 1.7 |
| gbm | E_rsi_scalp | -13.0 | -13.2 | -13.9 | 1.0 |
| gbm | Z_buy_hold | -5.2 | 2.7 | -0.5 | 7.9 |
| regime | A_trend_pullback | -31.9 | -33.2 | -30.6 | 2.6 |
| regime | B_donchian_breakout | -28.1 | -28.8 | -30.3 | 2.3 |
| regime | C_bollinger_meanrev | -12.4 | -11.8 | -14.0 | 2.2 |
| regime | D_session_orb | -37.8 | -37.8 | -38.0 | 0.3 |
| regime | E_rsi_scalp | -14.6 | -15.7 | -15.2 | 1.1 |
| regime | Z_buy_hold | 0.1 | 7.7 | 3.2 | 7.6 |
| trend_down | A_trend_pullback | -25.9 | -28.6 | -26.7 | 2.7 |
| trend_down | B_donchian_breakout | -24.5 | -26.2 | -23.0 | 3.2 |
| trend_down | C_bollinger_meanrev | -19.6 | -19.7 | -21.4 | 1.9 |
| trend_down | D_session_orb | -41.1 | -40.6 | -40.7 | 0.5 |
| trend_down | E_rsi_scalp | -12.7 | -13.8 | -14.1 | 1.4 |
| trend_down | Z_buy_hold | -35.8 | -28.7 | -31.0 | 7.2 |
| trend_up | A_trend_pullback | -30.0 | -31.8 | -30.4 | 1.8 |
| trend_up | B_donchian_breakout | -24.8 | -25.8 | -25.9 | 1.1 |
| trend_up | C_bollinger_meanrev | -10.9 | -10.5 | -12.2 | 1.7 |
| trend_up | D_session_orb | -32.9 | -33.0 | -34.6 | 1.7 |
| trend_up | E_rsi_scalp | -14.9 | -16.3 | -15.6 | 1.4 |
| trend_up | Z_buy_hold | 34.4 | 49.4 | 44.6 | 15.0 |