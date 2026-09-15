# MEGA sinov: 519 strategiya x 3 TF = 1557 sinov

- 3x, taker 0.050%, funding 0.01%/8h, kuniga max 4 kirish; 90 kun; rejimlar ['gbm', 'garch', 'regime', 'trend_up', 'trend_down']
- Mezon: median > 0, foydali grafiklar >= 55%, likvidatsiya < 5%; har bosqich yangi seedlar
- 1-bosqich: 10 grafik/rejim = 77550 backtest (403s)

## 1-bosqich o'tganlar: 35 / 1551  (shundan nazorat: 1 / 153)

| tf | strategy | family | median_ret | pct_profitable | tpd | win_rate | med_gbm | med_regime |
|---|---|---|---|---|---|---|---|---|
| 1h | p_cci_50_150__sl2_tp3 | p_cci | 3.2 | 70.0 | 0.4 | 47.9 | 5.8 | 4.7 |
| 1h | p_cci_50_200__sl2_tp3 | p_cci | 2.6 | 70.0 | 0.1 | 52.1 | 4.9 | 2.5 |
| 1h | p_cci_50_200__sl2_signal | p_cci | 2.3 | 62.0 | 0.1 | 50.4 | 4.2 | 4.0 |
| 1h | p_rsi_21_30_70__sl2_signal | p_rsi | 2.1 | 62.0 | 0.3 | 48.0 | 2.0 | 6.1 |
| 1h | p_rsi_14_25_75__sl2_signal | p_rsi | 2.0 | 62.0 | 0.3 | 53.9 | 1.5 | 6.4 |
| 1h | p_zscore_100_3.0__sl2_signal | p_zscore | 2.0 | 56.0 | 0.1 | 35.0 | 4.0 | 5.3 |
| 1h | p_cci_50_150__sl2_signal | p_cci | 1.8 | 68.0 | 0.4 | 49.8 | 6.0 | 2.5 |
| 1h | p_bbrev_50_3.0__sl2_signal | p_bb | 1.7 | 60.0 | 0.2 | 43.5 | 3.1 | 5.0 |
| 4h | tv_range_filter_donovanwall | tv | 1.7 | 62.0 | 0.1 | 35.4 | -0.8 | -0.3 |
| 4h | p_donchian_96_48__sl2_tp3 | p_donchian | 1.4 | 58.0 | 0.1 | 43.2 | 1.6 | -0.9 |
| 1h | p_ema_21_55__sl2_signal | p_ema | 1.4 | 56.0 | 0.4 | 21.2 | 2.8 | -12.5 |
| 4h | tv_dema_cross_20_50 | tv | 1.4 | 60.0 | 0.2 | 33.7 | -0.1 | -2.3 |
| 4h | trix_zero_cross | momentum | 1.3 | 56.0 | 0.1 | 29.2 | -1.1 | -2.9 |
| 4h | p_bbbreak_10_2.0__sl2_tp3 | p_bb | 1.2 | 58.0 | 0.2 | 42.3 | 2.4 | -3.1 |
| 4h | p_ema_20_100__sl2_signal | p_ema | 1.1 | 58.0 | 0.1 | 29.1 | -0.1 | 2.1 |
| 1h | p_rsi_14_25_75__sl2_tp3 | p_rsi | 1.1 | 56.0 | 0.3 | 46.2 | -0.4 | 6.3 |
| 4h | p_stoch_9_10_90__sl2_signal | p_stoch | 1.0 | 60.0 | 0.1 | 52.7 | 1.5 | 2.4 |
| 4h | p_donchian_10_5__sl2_tp3 | p_donchian | 0.9 | 58.0 | 0.3 | 42.1 | 0.1 | -1.8 |
| 4h | p_donchian_192_96__sl2_tp3 | p_donchian | 0.9 | 60.0 | 0.1 | 42.1 | 0.9 | 0.5 |
| 4h | p_stoch_5_20_80__sl2_tp3 | p_stoch | 0.9 | 56.0 | 0.3 | 41.6 | 1.5 | 1.7 |
| 4h | p_donchian_96_48__sl2_signal | p_donchian | 0.8 | 56.0 | 0.1 | 32.5 | 1.4 | -0.9 |
| 1h | p_rsi_21_25_75__sl2_signal | p_rsi | 0.8 | 64.0 | 0.1 | 47.9 | 0.8 | 2.4 |
| 4h | p_keltner_20_3.0__sl2_tp3 | p_keltner | 0.8 | 62.0 | 0.1 | 46.3 | 1.0 | -0.1 |
| 1h | p_bbbreak_20_3.0__sl2_tp3 | p_bb | 0.8 | 64.0 | 0.2 | 47.7 | 1.3 | -2.7 |
| 1h | p_cci_14_200__sl2_signal | p_cci | 0.8 | 56.0 | 0.3 | 59.0 | 1.2 | 0.8 |
| 4h | p_bbbreak_50_2.0__sl2_signal | p_bb | 0.7 | 56.0 | 0.1 | 31.5 | 0.3 | -4.0 |
| 4h | p_keltner_10_1.5__sl2_tp3 | p_keltner | 0.6 | 56.0 | 0.2 | 42.1 | -1.4 | -3.8 |
| 4h | p_stoch_21_10_90__sl2_signal | p_stoch | 0.5 | 56.0 | 0.2 | 40.8 | -1.6 | 3.5 |
| 4h | control_random_38 | control | 0.5 | 58.0 | 0.2 | 44.5 | 0.2 | -2.6 |
| 4h | p_bbbreak_10_2.5__sl2_tp3 | p_bb | 0.4 | 60.0 | 0.1 | 44.9 | -0.4 | 0.5 |
| 1h | p_zscore_100_3.0__sl2_tp3 | p_zscore | 0.4 | 58.0 | 0.1 | 44.2 | 0.8 | 1.7 |
| 4h | p_rsi_14_25_75__sl2_signal | p_rsi | 0.4 | 58.0 | 0.1 | 55.5 | 0.4 | 0.4 |
| 4h | p_donchian_96_48__sl3_trail3 | p_donchian | 0.3 | 56.0 | 0.1 | 40.0 | -0.1 | -0.4 |
| 4h | p_rsi_5_35_65__sl1.5_tp1.5 | p_rsi | 0.3 | 56.0 | 0.6 | 52.2 | -0.3 | 1.5 |
| 4h | tv_fisher_transform | tv | 0.2 | 58.0 | 0.1 | 60.5 | -0.3 | 1.0 |

## 2-bosqich (yangi seedlar 50001+, 15 grafik/rejim): 6 / 35 o'tdi (nazorat: 0)

| tf | strategy | family | median_ret | pct_profitable | tpd | win_rate | med_gbm | med_regime | med_trend_up | med_trend_down |
|---|---|---|---|---|---|---|---|---|---|---|
| 4h | p_bbbreak_50_2.0__sl2_signal | p_bb | 1.4 | 57.3 | 0.1 | 34.7 | 0.4 | -0.1 | 4.6 | 1.5 |
| 4h | p_donchian_96_48__sl2_signal | p_donchian | 1.1 | 57.3 | 0.1 | 31.9 | 0.7 | -0.1 | 5.5 | -0.5 |
| 1h | p_bbrev_50_3.0__sl2_signal | p_bb | 0.8 | 53.3 | 0.2 | 41.7 | -3.6 | 6.0 | -2.6 | 1.0 |
| 1h | p_rsi_21_25_75__sl2_signal | p_rsi | 0.7 | 60.0 | 0.1 | 48.0 | 0.9 | 1.4 | 0.3 | -0.5 |
| 4h | p_keltner_20_3.0__sl2_tp3 | p_keltner | 0.6 | 58.7 | 0.1 | 44.2 | 0.9 | -0.2 | 1.4 | 1.6 |
| 4h | p_donchian_96_48__sl2_tp3 | p_donchian | 0.4 | 56.0 | 0.1 | 41.9 | -0.3 | -0.3 | 2.6 | -0.8 |
| 4h | p_bbbreak_10_2.0__sl2_tp3 | p_bb | 0.2 | 56.0 | 0.3 | 41.1 | 0.2 | -4.0 | 1.8 | 1.2 |
| 4h | p_keltner_10_1.5__sl2_tp3 | p_keltner | 0.2 | 50.7 | 0.2 | 41.0 | -0.2 | -1.0 | 1.9 | 0.3 |
| 4h | p_rsi_14_25_75__sl2_signal | p_rsi | 0.1 | 50.7 | 0.1 | 52.1 | 0.4 | 0.8 | -0.8 | -0.2 |
| 4h | p_ema_20_100__sl2_signal | p_ema | 0.0 | 49.3 | 0.1 | 31.1 | -2.0 | 1.9 | 0.9 | 1.1 |
| 4h | p_donchian_192_96__sl2_tp3 | p_donchian | -0.3 | 45.3 | 0.1 | 39.6 | -0.1 | -1.2 | 1.2 | 0.3 |
| 1h | p_rsi_14_25_75__sl2_tp3 | p_rsi | -0.5 | 48.0 | 0.3 | 44.5 | -0.4 | 3.1 | -3.0 | -1.3 |
| 1h | p_rsi_21_30_70__sl2_signal | p_rsi | -0.5 | 49.3 | 0.3 | 44.7 | 0.5 | 5.4 | -1.8 | -2.3 |
| 4h | trix_zero_cross | momentum | -0.5 | 45.3 | 0.1 | 29.7 | -0.6 | -1.2 | 0.9 | -1.1 |
| 1h | p_cci_50_200__sl2_tp3 | p_cci | -0.6 | 45.3 | 0.2 | 41.0 | -0.1 | 2.4 | -2.7 | -0.6 |
| 4h | tv_fisher_transform | tv | -0.6 | 45.3 | 0.1 | 57.4 | -2.1 | 0.8 | -0.1 | -1.1 |
| 4h | p_bbbreak_10_2.5__sl2_tp3 | p_bb | -0.6 | 42.7 | 0.1 | 35.9 | -0.6 | -1.0 | 0.8 | -1.3 |
| 4h | p_donchian_96_48__sl3_trail3 | p_donchian | -0.6 | 44.0 | 0.1 | 38.7 | -1.2 | -1.2 | 1.1 | -1.1 |
| 4h | control_random_38 | control | -0.7 | 45.3 | 0.2 | 40.5 | 0.2 | -0.9 | -0.6 | 0.2 |
| 1h | p_zscore_100_3.0__sl2_signal | p_zscore | -0.8 | 45.3 | 0.1 | 30.7 | -2.8 | 0.2 | -3.8 | 1.5 |
| 4h | p_stoch_5_20_80__sl2_tp3 | p_stoch | -0.8 | 44.0 | 0.3 | 42.8 | -0.0 | -1.4 | -0.3 | -1.0 |
| 4h | p_rsi_5_35_65__sl1.5_tp1.5 | p_rsi | -0.9 | 46.7 | 0.6 | 51.7 | -1.9 | -0.9 | -2.6 | -0.8 |
| 1h | p_zscore_100_3.0__sl2_tp3 | p_zscore | -0.9 | 42.7 | 0.1 | 41.2 | -1.1 | 2.2 | -3.7 | -0.4 |
| 4h | tv_range_filter_donovanwall | tv | -1.0 | 36.0 | 0.1 | 30.3 | -2.0 | -2.5 | 0.7 | -0.0 |
| 1h | p_rsi_14_25_75__sl2_signal | p_rsi | -1.2 | 42.7 | 0.3 | 49.8 | 1.0 | 3.8 | -2.7 | -2.7 |
| 1h | p_cci_50_200__sl2_signal | p_cci | -1.3 | 40.0 | 0.2 | 41.2 | -2.0 | 2.2 | -2.0 | 0.0 |
| 1h | p_bbbreak_20_3.0__sl2_tp3 | p_bb | -1.3 | 34.7 | 0.2 | 38.7 | -0.4 | -5.2 | -1.1 | -1.3 |
| 4h | p_stoch_21_10_90__sl2_signal | p_stoch | -1.6 | 44.0 | 0.2 | 41.8 | -2.3 | 3.1 | -5.0 | 0.2 |
| 4h | p_stoch_9_10_90__sl2_signal | p_stoch | -1.9 | 32.0 | 0.2 | 47.9 | -2.0 | 0.5 | -2.1 | -2.4 |
| 1h | p_cci_14_200__sl2_signal | p_cci | -2.5 | 29.3 | 0.3 | 53.0 | -1.9 | -0.8 | -4.3 | -1.4 |
| 4h | p_donchian_10_5__sl2_tp3 | p_donchian | -2.8 | 42.7 | 0.4 | 40.2 | -3.4 | -5.2 | 3.0 | 2.0 |
| 4h | tv_dema_cross_20_50 | tv | -2.8 | 34.7 | 0.2 | 27.7 | 0.7 | -3.5 | -1.6 | -1.9 |
| 1h | p_ema_21_55__sl2_signal | p_ema | -2.9 | 44.0 | 0.4 | 22.2 | 1.7 | -16.0 | 1.1 | 0.8 |
| 1h | p_cci_50_150__sl2_tp3 | p_cci | -3.4 | 33.3 | 0.4 | 40.5 | -3.0 | 1.4 | -6.1 | -3.4 |
| 1h | p_cci_50_150__sl2_signal | p_cci | -3.4 | 34.7 | 0.4 | 42.3 | -4.3 | 1.6 | -6.3 | -0.1 |

## 3-bosqich (yangi seedlar 90001+, 15 grafik/rejim): 0 / 6 o'tdi (nazorat: 0)

| tf | strategy | family | median_ret | pct_profitable | tpd | win_rate | med_gbm | med_regime | med_trend_up | med_trend_down |
|---|---|---|---|---|---|---|---|---|---|---|
| 1h | p_rsi_21_25_75__sl2_signal | p_rsi | 0.0 | 48.0 | 0.1 | 39.9 | -0.4 | 0.6 | -1.1 | 0.0 |
| 4h | p_keltner_20_3.0__sl2_tp3 | p_keltner | -1.5 | 29.3 | 0.1 | 31.6 | -1.3 | -2.5 | -0.7 | -2.6 |
| 4h | p_donchian_96_48__sl2_tp3 | p_donchian | -2.0 | 33.3 | 0.1 | 33.6 | -3.3 | -3.8 | 1.5 | -1.8 |
| 4h | p_bbbreak_50_2.0__sl2_signal | p_bb | -2.4 | 38.7 | 0.1 | 29.4 | -4.0 | -5.7 | 2.1 | -0.5 |
| 4h | p_donchian_96_48__sl2_signal | p_donchian | -2.5 | 40.0 | 0.1 | 24.4 | -2.8 | -4.5 | 5.1 | -2.1 |
| 4h | p_bbbreak_10_2.0__sl2_tp3 | p_bb | -2.6 | 28.0 | 0.2 | 36.9 | -3.1 | -6.3 | -0.5 | -1.8 |

## YAKUN: 0 sinov 3 bosqichdan ham o'tdi (nazorat: 0)

Hech biri.

## Oilalar bo'yicha (1-bosqich): n sinov, median daromad, eng yaxshi, 1-bosqichdan o'tish %

| family | n | med | best | pct_pass |
|---|---|---|---|---|
| session | 3.0 | 0.0 | 0.0 | 0.0 |
| p_cci | 54.0 | -1.8 | 3.2 | 9.3 |
| p_adx | 54.0 | -2.2 | 0.8 | 0.0 |
| p_zscore | 96.0 | -2.5 | 2.0 | 2.1 |
| ml | 6.0 | -2.9 | 0.0 | 0.0 |
| breakout | 21.0 | -3.2 | 0.0 | 0.0 |
| p_bb | 192.0 | -3.6 | 1.7 | 2.6 |
| p_ema | 108.0 | -4.6 | 1.4 | 1.9 |
| p_rsi | 180.0 | -5.0 | 2.1 | 3.3 |
| p_donchian | 54.0 | -5.1 | 1.4 | 9.3 |
| tv | 87.0 | -5.2 | 1.7 | 3.4 |
| meanrev | 27.0 | -5.4 | 1.1 | 0.0 |
| control | 153.0 | -5.7 | 0.6 | 0.7 |
| p_stoch | 48.0 | -6.6 | 1.0 | 6.2 |
| trend | 48.0 | -7.0 | 0.7 | 0.0 |
| p_macd | 60.0 | -7.1 | -0.6 | 0.0 |
| p_keltner | 72.0 | -7.2 | 1.3 | 2.8 |
| momentum | 18.0 | -7.2 | 1.3 | 5.6 |
| p_pullback | 54.0 | -7.5 | 0.1 | 0.0 |
| p_supertrend | 96.0 | -7.9 | 0.8 | 0.0 |
| highwr | 15.0 | -9.5 | 0.0 | 0.0 |
| p_roc | 72.0 | -10.6 | 0.7 | 0.0 |
| smc | 24.0 | -11.4 | 0.0 | 0.0 |
| pattern | 9.0 | -20.1 | -1.6 | 0.0 |