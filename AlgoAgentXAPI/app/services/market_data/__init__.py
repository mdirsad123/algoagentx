"""Market data ingestion utilities.

Phase MD-2 adds provider-agnostic candle normalization, validation, and safe
PostgreSQL upsert helpers. These utilities are intentionally not wired to any
frontend, broker fetch, or CSV upload endpoint yet.
"""

from .types import CandleImportSummary, NormalizedCandle, ValidationErrorSample
from .normalizer import normalize_candles
from .validator import validate_and_prepare_candles
from .upsert_service import upsert_market_data_candles

__all__ = [
    "CandleImportSummary",
    "NormalizedCandle",
    "ValidationErrorSample",
    "normalize_candles",
    "validate_and_prepare_candles",
    "upsert_market_data_candles",
]
