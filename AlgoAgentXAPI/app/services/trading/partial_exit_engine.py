from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def _to_decimal_size(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _nearest_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    units = (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return units * step


def calculate_broker_partial_split(
    *,
    total_size: float | None,
    percent: float,
    quantity_mode: str,
    instrument_spec: dict[str, Any],
) -> dict[str, Any]:
    """Calculate a broker-valid partial close while preserving a valid runner.

    This service is intentionally execution-layer agnostic so the backtest engine and
    future cTrader/MT5 partial-close workers can share exactly the same min-size/step
    normalization rule.

    Contract for a 90% partial:
    - compute the requested 10% runner from the original broker-normalized position;
    - if that *unrounded* runner is below min_lot/min_quantity, do not partial-close;
    - otherwise round the requested close to the nearest broker step;
    - bound the split so both close size and remaining runner stay broker-valid.
    """
    total = _to_decimal_size(total_size)
    pct = _to_decimal_size(percent)
    mode = str(quantity_mode or "").upper()
    if total <= 0 or pct <= 0 or pct >= 1:
        return {"eligible": False, "reason": "INVALID_PARTIAL_SIZE_OR_PERCENT"}

    if mode == "LOTS":
        minimum = _to_decimal_size(instrument_spec.get("min_lot"), "0.01")
        step = _to_decimal_size(instrument_spec.get("lot_step"), "0.01")
        size_label = "lot"
    else:
        minimum = _to_decimal_size(instrument_spec.get("min_quantity"), "1")
        step = _to_decimal_size(instrument_spec.get("quantity_step"), "1")
        size_label = "quantity"

    if minimum <= 0:
        minimum = step if step > 0 else (Decimal("0.01") if mode == "LOTS" else Decimal("1"))
    if step <= 0:
        step = minimum

    requested_close = total * pct
    requested_runner = total - requested_close

    # Do not make an originally invalid runner appear valid by rounding it up.
    if requested_runner < minimum:
        return {
            "eligible": False,
            "reason": "RUNNER_BELOW_BROKER_MINIMUM",
            "size_label": size_label,
            "total_size": float(total),
            "requested_close_size": float(requested_close),
            "requested_runner_size": float(requested_runner),
            "minimum_size": float(minimum),
            "step_size": float(step),
        }

    close_size = _nearest_step(requested_close, step)
    max_close = total - minimum
    if close_size > max_close:
        close_size = max_close

    if close_size < minimum:
        return {
            "eligible": False,
            "reason": "PARTIAL_CLOSE_BELOW_BROKER_MINIMUM",
            "size_label": size_label,
            "total_size": float(total),
            "requested_close_size": float(requested_close),
            "requested_runner_size": float(requested_runner),
            "minimum_size": float(minimum),
            "step_size": float(step),
        }

    runner_size = total - close_size
    while runner_size < minimum and close_size - step >= minimum:
        close_size -= step
        runner_size += step

    if runner_size < minimum or close_size <= 0:
        return {
            "eligible": False,
            "reason": "NO_VALID_BROKER_PARTIAL_SPLIT",
            "size_label": size_label,
            "total_size": float(total),
            "requested_close_size": float(requested_close),
            "requested_runner_size": float(requested_runner),
            "minimum_size": float(minimum),
            "step_size": float(step),
        }

    return {
        "eligible": True,
        "reason": None,
        "size_label": size_label,
        "total_size": float(total),
        "requested_close_size": float(requested_close),
        "requested_runner_size": float(requested_runner),
        "partial_close_size": float(close_size),
        "runner_size": float(runner_size),
        "effective_partial_percent": float(close_size / total),
        "minimum_size": float(minimum),
        "step_size": float(step),
    }
