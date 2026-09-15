# SMC strategiya: kuniga 2 savdo, 1:2 R:R

Bot profili: `profiles/two_trades_rr2.json`
Qo'lda savdo uchun ham xuddi shu qoidalar amal qiladi.

```
python -m smc_bot --config profiles/two_trades_rr2.json            # paper
python -m smc_bot.backtest --config profiles/two_trades_rr2.json --csv DOGE=data/doge_1m.csv ...
```

---

## 1. Ramka

| Qoida | Qiymat |
|---|---|
| Savdolar soni | kuniga maksimal **2**: London sessiyasida 1, New York sessiyasida 1 |
| Kill zone (UTC) | London **07:00–10:00**, New York **12:00–16:00**. Boshqa vaqtda savdo yo'q |
| Risk | har savdoda hisobning **1%** (komissiya + slippage shu 1% ichida) |
| Take-Profit | **bitta nishon: 2R** (entry + 2 × SL masofa). Qisman yopish yo'q, BE yo'q |
| Bir vaqtda | faqat **1** ochiq pozitsiya |
| Kunlik to'xtash | 2 savdo bo'ldi (natijadan qat'i nazar) **yoki** kunlik zarar −2% |
| Juftliklar | DOGE, SHIB, PEPE, WIF, BONK, FLOKI; spred ≤ 4 bps, 24h hajm ≥ 100M, depth ≥ 300k |
| Cooldown | bir juftlikda yopilgandan keyin 4 soat |

Nega bitta 2R nishon: qoidalar qancha kam bo'lsa, ijro shuncha barqaror bo'ladi.
Break-even nuqtasi 33.3% win rate. Har 1 g'alaba 2 zararni qoplaydi.

---

## 2. Kun boshida (00:00 UTC yoki sessiyadan 30 daqiqa oldin)

**H4 bias.** Oxirgi 2 ta tasdiqlangan swing high va swing low:
- HH + HL → bugun faqat **LONG**
- LH + LL → bugun faqat **SHORT**
- boshqa → bu juftlikda bugun savdo yo'q

**H1 tasdiqlash.** H1 ham xuddi shu strukturada bo'lishi **shart**
(`require_h1_confirm`). H1 neytral bo'lsa ham savdo yo'q.

**M15 likvidlik xaritasi** (faqat "major" darajalar):
- PDH / PDL (oldingi kun high/low)
- Osiyo sessiyasi high/low (00:00–08:00 UTC)
- London high/low (NY sessiyasi uchun)

EQH/EQL bu strategiyada sweep uchun ishlatilmaydi (`require_major_sweep`).

**Premium / discount.** Oxirgi 48 ta H1 sham diapazoni. LONG faqat pastki
yarmida, SHORT faqat yuqori yarmida qidiriladi.

---

## 3. Kill zone ichida: kirish shartlari (hammasi ketma-ket)

1. **Sweep.** M5 sham wick'i major darajadan kamida `0.2 × ATR` o'tadi va
   6 sham ichida close daraja ortiga qaytadi.
   LONG: PDL / Osiyo low / London low tozalanadi. SHORT: teskari.
2. **Displacement.** Sweep ekstremumidan keyin 24 sham ichida yo'nalishdagi
   sham tanasi ≥ `1.2 × ATR(14)`.
3. **MSS.** O'sha impuls sweep'dan oldingi oxirgi swing high (LONG) / swing
   low (SHORT) ni **close bilan** sindiradi.
4. **FVG.** Impuls oyog'ida FVG bo'lishi **shart** (OB bilan kirilmaydi,
   `allow_ob_fallback=false`). FVG kattaligi ≥ 0.1 ATR.
5. **Yangilik.** MSS shamidan keyin 8 tadan ko'p sham o'tmagan bo'lishi kerak.
6. **Toza yo'l.** Entry bilan 2R nishon orasida (1.8R gacha) boshqa major
   qarama-qarshi daraja bo'lmasligi kerak (`min_clear_path_rr`). Bo'lsa —
   nishon likvidlik orqasida, savdo o'tkazib yuboriladi.

Hammasi bajarilsa: **limit order FVG ning 50% iga** (CE). 45 daqiqada
to'lmasa bekor qilinadi va bu savdo hisoblanmaydi.

---

## 4. SL va TP

| | LONG | SHORT |
|---|---|---|
| SL | FVG low − 0.5 × ATR(M5) | FVG high + 0.5 × ATR(M5) |
| TP | entry + 2 × (entry − SL) | entry − 2 × (SL − entry) |

Ikkalasi ham **reduce-only stop-market / take-profit-market**. Order
qo'yilgandan keyin hech narsa o'zgartirilmaydi. SL ga tegdi — zarar 1%,
TP ga tegdi — foyda 2%. Vaqt bo'yicha chiqish yo'q: pozitsiya keyingi kunga
o'tishi mumkin, lekin yangi savdo faqat ochiq pozitsiya bo'lmaganda ochiladi.

SL masofasi (bps) komissiya + slippage dan 4 barobar kam bo'lsa savdo
o'tkazib yuboriladi: juda tor stopda xarajat R ni buzadi.

---

## 5. Kutilma jadvali (1% risk, kuniga 2 savdo, 20 savdo kuni)

| Win rate | R / savdo | Oyiga (40 savdo) |
|---|---|---|
| 33% | 0.00 | 0% |
| 40% | +0.20 | +8% |
| 45% | +0.35 | +14% |
| 50% | +0.50 | +20% |
| 55% | +0.65 | +26% |

Bu raqamlar arifmetika, bashorat emas. Aslida kuniga 2 ta setup har doim
chiqmaydi: filtrlar qat'iy, ko'p kunlarda 0–1 savdo bo'ladi. "2 savdo"
yuqori chegara, majburiyat emas. Setup yo'q — savdo yo'q.

---

## 6. Qo'lda bajaradiganlar uchun checklist

```
[ ] H4 HH/HL (LONG) yoki LH/LL (SHORT)?      yo'q -> kut
[ ] H1 ham shu strukturada?                   yo'q -> kut
[ ] Kill zone ichidamiz (07–10 / 12–16 UTC)?  yo'q -> kut
[ ] Bu sessiyada savdo qilinmaganmi?          qilingan -> keyingi sessiya
[ ] Entry discount (LONG) / premium (SHORT) da?
[ ] Major daraja sweep qilindi (wick >= 0.2 ATR, close qaytdi)?
[ ] Displacement sham >= 1.2 ATR?
[ ] MSS: swing close bilan sindirildi?
[ ] Impulsda FVG bor?
[ ] Entry -> 2R yo'lida major daraja yo'q?
[ ] Spred <= 4 bps, hajm OK?
=> limit FVG 50%, SL = FVG chekkasi -/+ 0.5 ATR, TP = 2R, 45 daqiqa kut.
```

Bir kunda ikki zarar (−2%) yoki ikki savdo bo'ldi — grafikni yoping.
