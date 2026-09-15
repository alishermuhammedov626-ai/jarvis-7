# JARVIS 7 — Independent Validation of the JARVIS 5 Historical Claim

JARVIS 7 is **not** a trading bot and **not** a strategy upgrade.
It is a validation project whose only purpose is to independently prove or
disprove a historical backtest claim written into the original JARVIS 5 source.

## The claim under test

| Item | Claimed value |
|---|---|
| Instrument | `1000SHIBUSDT` (Binance USDT-M futures, SHIB equivalent) |
| Period | 2025-01-01 00:00:00 UTC → 2025-12-31 23:59:59 UTC |
| Trades | 617 |
| Win rate | 92.06 % |
| Profit factor | 45.94 |
| Net PnL | +333.7 % |

Original strategy characteristics (as described in the source):
M15 structure, M1 confirmation, Order-Block based entries, ATR-based stop with
distance constrained to roughly 0.30 %–0.50 %, partial take-profit at +0.70 %,
full take-profit at +1.00 %, maximum holding period 24 hours.

## Canonical legacy source

> **Status:** the canonical file has not yet been placed in `legacy/`. The
> upload did not reach this repository, and no byte-identical copy exists in
> any sibling repository. The preservation commit ("Preserve canonical
> JARVIS 5 source") is made only once a file with the exact SHA-256 below is
> supplied. Until then, no data download, backtest, or strategy run is
> performed.

The file `legacy/jarvis_5_0-2.py` is the canonical legacy source and is
**frozen**. It is never edited, refactored, bug-fixed, re-formatted, or
re-tuned in this repository.

| Property | Required value |
|---|---|
| Path | `legacy/jarvis_5_0-2.py` |
| SHA-256 | `3e376069ec8248b82087de6314c13a88104e29e6e596ab089517a7cf794266b6` |
| Size | 95,339 bytes |

Verify at any time with:

```bash
sha256sum -c checksums/SHA256SUMS.txt
```

If the checksum does not match, every validation step in this repository must
refuse to run.

## Repository layout

```
jarvis-7/
├── legacy/
│   └── jarvis_5_0-2.py        # frozen canonical source (never modified)
├── checksums/
│   └── SHA256SUMS.txt         # expected SHA-256 of the legacy source
├── docs/
│   └── VALIDATION_PLAN.md     # phased validation methodology
├── README.md
└── .gitignore
```

Later phases (only after explicit authorization) add `backtest/`, `scripts/`,
`tests/` and generated `reports/` — see `docs/VALIDATION_PLAN.md`.

## Ground rules

1. The legacy source is preserved byte-for-byte; its SHA-256 is the gate.
2. The first backtest mode (`LEGACY_REPLICATION_MODE`) reproduces what the
   original logic actually does, including any look-ahead it may contain.
   Nothing is repaired, reinterpreted, filtered, tuned, or "improved".
3. A separate `CAUSAL_VALIDATION_MODE` is implemented only after the
   replication result has been reported.
4. Gross (no-cost) and realistic-cost results are always reported separately
   and never mixed.
5. Parameters are never changed after inspecting results.

## Safety

- This project never places live orders and never requires Binance API
  credentials.
- The original `JarvisEngine` is never started; Telegram is never started.
- `python legacy/jarvis_5_0-2.py` is never executed. The file is only
  byte-compiled for a syntax check and imported through an adapter that does
  not run its entry point.
- Only public historical market-data endpoints are used. No private account
  endpoints are contacted.
- `.env` files, API keys, Telegram tokens and any other secrets are excluded
  by `.gitignore` and must never be committed.
