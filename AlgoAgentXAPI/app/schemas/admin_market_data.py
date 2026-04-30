from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


FreshnessStatus = Literal["fresh", "warning", "stale", "no_data"]


class MarketDataCatalogInstrument(BaseModel):
    id: int
    symbol: str
    exchange: str
    market: str
    instrument_type: str | None = None


class MarketDataCatalogResponse(BaseModel):
    instruments: list[MarketDataCatalogInstrument]
    timeframes: list[str]


class MarketDataDatasetSummary(BaseModel):
    total_datasets: int
    total_records: int
    fresh_count: int
    warning_count: int
    stale_count: int
    no_data_count: int


class MarketDataDataset(BaseModel):
    instrument_id: int
    instrument_symbol: str
    exchange: str
    market: str
    timeframe: str
    first_candle_at: datetime | None = None
    last_candle_at: datetime | None = None
    latest_candle_date: str | None = None
    total_records: int
    freshness_status: FreshnessStatus
    freshness_age_hours: float | None = None
    expected_fresh_hours: float | None = None
    is_stale: bool


class MarketDataDatasetListResponse(BaseModel):
    items: list[MarketDataDataset]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: MarketDataDatasetSummary


class MarketDataImportRequest(BaseModel):
    instrument_id: int | None = None
    timeframe: str | None = None
    source: str = Field(default="manual")
    dataset_uri: str | None = None
    note: str | None = None
    dry_run: bool = False
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDataRefreshRequest(BaseModel):
    instrument_id: int | None = None
    timeframe: str | None = None
    source: str = Field(default="admin")
    note: str | None = None
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDataJobRecord(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: int
    message: str | None = None
    retry_count: int
    max_retries: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    instrument_id: int | None = None
    timeframe: str | None = None
    source: str | None = None
    dataset_uri: str | None = None
    imported_rows: int | None = None
    invalid_rows: int | None = None
    has_invalid_data: bool
    error_message: str | None = None


class MarketDataJobListResponse(BaseModel):
    items: list[MarketDataJobRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class MarketDataJobEnqueueResponse(BaseModel):
    job_id: str
    status: str
    job_type: str
    pipeline_ready: bool
    message: str
    payload: dict[str, Any]
