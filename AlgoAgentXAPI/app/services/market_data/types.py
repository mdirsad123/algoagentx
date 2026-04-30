from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class NormalizedCandle:
    """Canonical candle shape used by market data ingestion."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal("0")

    def to_insert_dict(self, instrument_id: int, timeframe: str) -> dict[str, Any]:
        return {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(slots=True)
class ValidationErrorSample:
    row_index: int | None
    reason: str
    row: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandleImportSummary:
    total_input_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    min_timestamp: datetime | None = None
    max_timestamp: datetime | None = None
    errors_sample: list[ValidationErrorSample] = field(default_factory=list)
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_input_rows": self.total_input_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "duplicate_rows": self.duplicate_rows,
            "inserted_rows": self.inserted_rows,
            "updated_rows": self.updated_rows,
            "skipped_rows": self.skipped_rows,
            "min_timestamp": self.min_timestamp.isoformat() if self.min_timestamp else None,
            "max_timestamp": self.max_timestamp.isoformat() if self.max_timestamp else None,
            "errors_sample": [error.as_dict() for error in self.errors_sample],
            "dry_run": self.dry_run,
        }
