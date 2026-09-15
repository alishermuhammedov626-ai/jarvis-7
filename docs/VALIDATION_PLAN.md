# JARVIS 7 — Validation Plan

## Purpose

Independently prove or disprove the historical claim embedded in the original
JARVIS 5 source (`legacy/jarvis_5_0-2.py`):

> 1000SHIBUSDT, 2025-01-01 → 2025-12-31:
> 617 trades, 92.06 % win rate, profit factor 45.94, net PnL +333.7 %.

The objective is **not** to improve the strategy. The objective is to find out
whether the number is real, and if not, why.

## Non-negotiable constraints

- `legacy/jarvis_5_0-2.py` is frozen. SHA-256 must equal
  `3e376069ec8248b82087de6314c13a88104e29e6e596ab089517a7cf794266b6`
  (95,339 bytes). Any mismatch halts all validation.
- No live orders, no API credentials, no `JarvisEngine`, no Telegram,
  never `python legacy/jarvis_5_0-2.py`.
- Public historical market data only.
- No secrets in git.
- History is never rewritten after the source checksum is committed.

---

## Phase 1 — Preserve the original (this delivery)

1. Copy the uploaded `jarvis_5_0-2.py` into `legacy/` unchanged.
2. Compute SHA-256; it must match the value above. Otherwise stop.
3. Byte-compile the file for a syntax check (`py_compile`) without modifying
   or executing it.
4. Create `README.md`, `.gitignore`, `docs/VALIDATION_PLAN.md`,
   `checksums/SHA256SUMS.txt`.
5. Commit ("Preserve canonical JARVIS 5 source") and push.

Deliverable: repository, branch, commit SHA, source SHA-256, byte size,
compile result, committed file list.

---

## Phase 2 — Separate backtest harness (requires explicit authorization)

The legacy file is never edited. Everything is built **around** it.

```
backtest/
    __init__.py
    data.py             # download / cache / audit market data
    legacy_adapter.py   # imports the frozen source without running its entry point
    engine.py           # replays candles through the original logic
    metrics.py          # trade statistics
scripts/
    download_data.py
    run_legacy_backtest.py
tests/
    test_legacy_integrity.py    # SHA-256 gate
    test_metrics.py
    test_backtest_determinism.py
reports/                        # generated, git-ignored
```

### 2a. Data

Source: Binance USDT-M Futures public historical klines.
Symbol: `1000SHIBUSDT`. Range: 2025-01-01 00:00:00 UTC → 2025-12-31 23:59:59 UTC.
Timeframes: M1 (raw download) and M15 (derived deterministically from M1 where
possible).

Data must be chronologically sorted, duplicate-checked, gap-checked,
UTC-normalized, cached locally, and never silently forward-filled.

Before any strategy run, write `reports/data_audit.json` with: first
timestamp, last timestamp, row count, duplicates, missing-minute count,
missing intervals, M1/M15 alignment, symbol used, source.

### 2b. Mode A — `LEGACY_REPLICATION_MODE` (first)

Reproduce what the original JARVIS 5 logic actually does:

- original M15/M1 behaviour and signal-timing semantics
- Order Block logic, displacement logic, M1 confirmation logic
- ATR calculation, SL rules, partial TP, full TP, trailing, max hold,
  cooldown (if part of the tested logic)

Explicitly **not** done in this mode: making it causal, repairing suspected
look-ahead, adding filters, adding ML, optimizing or tuning parameters,
changing parameters after seeing results.

Primary question: can 617 / 92.06 % / PF 45.94 / +333.7 % be reproduced?

### 2c. Mode B — `CAUSAL_VALIDATION_MODE` (later, only after Mode A is reported)

Remove future-data / look-ahead and test the same economic hypothesis
honestly. Not implemented or run until Mode A is complete and reported.

### 2d. Execution accounting

Two separate result sets, never mixed:

1. **Gross legacy result** — no fees, no slippage (reproduces the claim).
2. **Realistic cost result** — explicitly declared Binance Futures fee and
   slippage assumptions.

### 2e. Metrics

total trades, wins, losses, win rate, 95 % CI for win rate, gross profit,
gross loss, profit factor, expectancy per trade, total return, maximum
drawdown, average trade, median trade, average and median holding time, long
and short trade counts, long and short WR, monthly results, exit-reason counts,
partial-TP count, full-TP count, SL count, max-hold exits, largest win,
largest loss.

Exports: `reports/legacy_trades.csv`, `reports/legacy_monthly.csv`,
`reports/legacy_summary.json`, `reports/legacy_summary.md`.

Each trade record: trade id, symbol, direction, M15 setup timestamp,
displacement timestamp, M1 zone-touch timestamp, M1 confirmation timestamp,
entry timestamp, entry price, initial SL, exit timestamp, exit price, exit
reason, partial TP information, gross return, costs, net return.

### 2f. Critical validation check

For each of trades, WR, PF, PnL report: claimed, reproduced, absolute
difference, relative difference. A close WR alone does not count as
reproduction.

Outcome classification:

- `EXACTLY_REPRODUCED`
- `CLOSE_BUT_NOT_EXACT`
- `NOT_REPRODUCED`
- `METHODOLOGY_BLOCKED`

### 2g. Source integrity test

`tests/test_legacy_integrity.py` computes the SHA-256 of
`legacy/jarvis_5_0-2.py` and refuses validation if it differs from the
expected value.
