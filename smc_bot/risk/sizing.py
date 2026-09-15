"""Position sizing: fixed fractional risk (1% of equity by default)."""
from __future__ import annotations

import math

from ..models import MarketSpec


def round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor(value / step + 1e-9) * step


def round_step_up(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.ceil(value / step - 1e-9) * step


def position_size(
    equity: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
    spec: MarketSpec,
    leverage: int,
    cost_bps: float = 0.0,
) -> float:
    """Quantity such that the *worst-case* loss equals ``equity * risk_pct``.

    The loss on a stop-out is the price distance plus round-trip fees and the
    expected stop-market slippage (``cost_bps`` of notional), so the
    per-unit risk is inflated by that amount.  Returns 0.0 when the trade
    cannot be sized within exchange limits or the required margin exceeds
    the account.
    """
    if equity <= 0:
        return 0.0
    risk_per_unit = abs(entry - stop_loss) + entry * cost_bps / 10_000.0
    if abs(entry - stop_loss) <= 0:
        return 0.0
    risk_usd = equity * risk_pct / 100.0
    qty = risk_usd / risk_per_unit
    qty = round_step(qty, spec.amount_step)
    if qty < spec.min_amount:
        return 0.0
    notional = qty * entry
    if notional < spec.min_notional:
        return 0.0
    # margin check: never exceed what the account can post with configured leverage
    lev = max(1, min(leverage, spec.max_leverage))
    if notional / lev > equity * 0.95:
        qty = round_step(equity * 0.95 * lev / entry, spec.amount_step)
        if qty < spec.min_amount or qty * entry < spec.min_notional:
            return 0.0
    return float(qty)


def split_tp_quantities(qty: float, spec: MarketSpec, tp1_share: float = 0.5) -> tuple[float, float]:
    """Split ``qty`` into TP1 and TP2 legs respecting the amount step."""
    q1 = round_step(qty * tp1_share, spec.amount_step)
    q2 = round_step(qty - q1, spec.amount_step)
    if q1 < spec.min_amount or q2 < spec.min_amount:
        # cannot split -> everything at TP2 (still protected by SL)
        return 0.0, qty
    return q1, q2
