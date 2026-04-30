from __future__ import annotations

from .types import CandleImportSummary, NormalizedCandle, ValidationErrorSample


def _is_price_shape_valid(candle: NormalizedCandle) -> tuple[bool, str | None]:
    high_values = (candle.open, candle.close, candle.low)
    low_values = (candle.open, candle.close, candle.high)
    if any(candle.high < value for value in high_values):
        return False, "high must be >= open, close, and low"
    if any(candle.low > value for value in low_values):
        return False, "low must be <= open, close, and high"
    if candle.volume < 0:
        return False, "volume cannot be negative"
    return True, None


def validate_and_prepare_candles(
    candles: list[NormalizedCandle],
    *,
    total_input_rows: int,
    normalize_errors: list[ValidationErrorSample] | None = None,
    dry_run: bool = False,
    max_error_samples: int = 25,
) -> tuple[list[NormalizedCandle], CandleImportSummary]:
    """Validate, deduplicate, and sort normalized candles."""
    errors = list(normalize_errors or [])
    valid: list[NormalizedCandle] = []

    for idx, candle in enumerate(candles):
        ok, reason = _is_price_shape_valid(candle)
        if ok:
            valid.append(candle)
        elif len(errors) < max_error_samples:
            errors.append(
                ValidationErrorSample(
                    row_index=idx,
                    reason=reason or "invalid candle",
                    row={
                        "timestamp": candle.timestamp.isoformat(),
                        "open": str(candle.open),
                        "high": str(candle.high),
                        "low": str(candle.low),
                        "close": str(candle.close),
                        "volume": str(candle.volume),
                    },
                )
            )

    by_timestamp: dict = {}
    duplicate_rows = 0
    for candle in valid:
        if candle.timestamp in by_timestamp:
            duplicate_rows += 1
        # Last value wins, which is standard for repeated vendor rows/reimports.
        by_timestamp[candle.timestamp] = candle

    prepared = sorted(by_timestamp.values(), key=lambda item: item.timestamp)

    summary = CandleImportSummary(
        total_input_rows=total_input_rows,
        valid_rows=len(prepared),
        invalid_rows=total_input_rows - len(valid),
        duplicate_rows=duplicate_rows,
        skipped_rows=0,
        min_timestamp=prepared[0].timestamp if prepared else None,
        max_timestamp=prepared[-1].timestamp if prepared else None,
        errors_sample=errors,
        dry_run=dry_run,
    )
    return prepared, summary
