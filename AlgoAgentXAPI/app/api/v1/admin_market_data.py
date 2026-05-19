from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str
from ...db.models import Instrument, JobStatus, MarketData
from ...schemas.admin_market_data import (
    MarketDataCatalogResponse,
    MarketDataDatasetListResponse,
    MarketDataImportRequest,
    MarketDataJobEnqueueResponse,
    MarketDataJobListResponse,
    MarketDataRefreshRequest,
)
from ...services.admin_market_data_service import AdminMarketDataService
from ...services.market_data import upsert_market_data_candles
from ...services.market_data.providers import (
    MarketDataProviderError,
    ProviderNotFoundError,
    ProviderNotImplementedError,
    get_market_data_provider,
    normalize_provider_name,
)
from ...utils.api_response import success_response

router = APIRouter()


def _is_supported_timeframe(timeframe: str) -> bool:
    value = (timeframe or "").strip().lower()
    if not value:
        return False
    return value in AdminMarketDataService._KNOWN_TIMEFRAME_MINUTES


def _clean_source(source: str | None) -> str:
    cleaned = (source or "CSV").strip()
    return cleaned[:50] if cleaned else "CSV"


def _clean_error_message(message: str | None, *, max_length: int = 600) -> str | None:
    if not message:
        return None
    text = str(message).replace("\r", " ").replace("\n", " ").strip()
    # Keep provider/user-facing errors useful while avoiding huge traceback-like payloads in job rows.
    for marker in ("Traceback (most recent call last):", "File \"", "pydantic_core._pydantic_core"):
        if marker in text:
            text = text.split(marker, 1)[0].strip() or "Market data operation failed"
    return text[:max_length]


async def _read_csv_upload(file: UploadFile, *, max_bytes: int = 15 * 1024 * 1024) -> list[dict[str, Any]]:
    filename = file.filename or ""
    if filename and not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported for this import")

    raw = await file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="CSV file is too large. Maximum allowed size is 15 MB")
    if not raw:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="Unable to read CSV encoding. Please upload UTF-8 CSV") from exc

    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV header row is required")

    rows: list[dict[str, Any]] = []
    for row in reader:
        cleaned = {str(key).strip(): (value.strip() if isinstance(value, str) else value) for key, value in row.items() if key is not None}
        if any(value not in (None, "") for value in cleaned.values()):
            rows.append(cleaned)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no candle rows")
    return rows


async def _create_csv_upload_job(
    db: AsyncSession,
    *,
    admin_user_id: str,
    instrument_id: int,
    timeframe: str,
    source: str,
    filename: str | None,
    dry_run: bool,
    status_value: str,
    message: str,
    summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> str | None:
    try:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        summary_payload = summary or {}
        job_data = {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "source": source,
            "dataset_uri": filename,
            "dry_run": dry_run,
            "job_type": "CSV_UPLOAD",
        }
        result_data = {
            "summary": summary_payload,
            "imported_rows": int(summary_payload.get("inserted_rows") or 0),
            "updated_rows": int(summary_payload.get("updated_rows") or 0),
            "invalid_rows": int(summary_payload.get("invalid_rows") or 0),
            "duplicate_rows": int(summary_payload.get("duplicate_rows") or 0),
            "has_invalid_data": bool(summary_payload.get("invalid_rows") or 0),
        }
        if error_message:
            result_data["error_message"] = _clean_error_message(error_message)

        db.add(
            JobStatus(
                id=job_id,
                user_id=as_uuid_or_str(admin_user_id),
                job_type="CSV_UPLOAD",
                status=status_value,
                progress=100 if status_value == "completed" else 0,
                message=message,
                job_data=json.dumps(job_data, default=str),
                result_data=json.dumps(result_data, default=str),
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        return job_id
    except Exception:
        # Job tracking should not fail the import response.
        return None


async def _create_market_data_operation_job(
    db: AsyncSession,
    *,
    admin_user_id: str,
    job_type: str,
    provider: str,
    instrument_id: int,
    timeframe: str,
    symbol: str | None,
    instrument_key: str | None,
    dry_run: bool,
    status_value: str,
    message: str,
    summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> str | None:
    """Best-effort job-status audit row for broker import/refresh operations.

    The market-data admin page already has an import jobs/failure section. This
    helper keeps broker operations visible there without introducing a new table
    or blocking the import if job tracking has an unexpected legacy schema issue.
    """
    try:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        summary_payload = summary or {}
        cleaned_error = _clean_error_message(error_message)
        job_data = {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "source": provider,
            "provider": provider,
            "symbol": symbol,
            "instrument_key": instrument_key,
            "dry_run": dry_run,
        }
        result_data = {
            "summary": summary_payload,
            "imported_rows": int(summary_payload.get("inserted_rows") or 0),
            "updated_rows": int(summary_payload.get("updated_rows") or 0),
            "invalid_rows": int(summary_payload.get("invalid_rows") or 0),
            "duplicate_rows": int(summary_payload.get("duplicate_rows") or 0),
            "has_invalid_data": bool(summary_payload.get("invalid_rows") or 0),
        }
        if cleaned_error:
            result_data["error_message"] = cleaned_error

        db.add(
            JobStatus(
                id=job_id,
                user_id=as_uuid_or_str(admin_user_id),
                job_type=job_type,
                status=status_value,
                progress=100 if status_value == "completed" else 0,
                message=message,
                job_data=json.dumps(job_data, default=str),
                result_data=json.dumps(result_data, default=str),
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        return job_id
    except Exception:
        return None


class MarketDataFetchRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=30)
    symbol: str = Field(..., min_length=1, max_length=100)
    instrument_key: str | None = Field(default=None, max_length=255)
    broker_account_id: str | None = Field(default=None, max_length=80)
    instrument_id: int = Field(..., ge=1)
    timeframe: str = Field(..., min_length=1, max_length=20)
    start_date: datetime | date
    end_date: datetime | date
    dry_run: bool = False


class MarketDataRefreshMissingRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=30)
    symbol: str = Field(..., min_length=1, max_length=100)
    instrument_key: str | None = Field(default=None, max_length=255)
    broker_account_id: str | None = Field(default=None, max_length=80)
    instrument_id: int = Field(..., ge=1)
    timeframe: str = Field(..., min_length=1, max_length=20)
    end_date: datetime | date | None = None
    dry_run: bool = False



def _as_utc_datetime(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.combine(value, time.min)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc_end_datetime(value: datetime | date | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.combine(value, time.max)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timeframe_overlap(timeframe: str) -> timedelta:
    minutes = AdminMarketDataService._KNOWN_TIMEFRAME_MINUTES.get((timeframe or "").strip().lower(), 60)
    if minutes >= 1440:
        return timedelta(days=2)
    return timedelta(minutes=max(minutes * 3, 15))


def _clean_symbol(symbol: str) -> str:
    # Preserve case for MT5 broker suffixes such as XAUUSDc/XAGUSDc/BTCUSDc.
    # Binance provider normalizes to uppercase internally.
    cleaned = (symbol or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="symbol is required")
    return cleaned[:100]


def _provider_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, ProviderNotFoundError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ProviderNotImplementedError):
        return HTTPException(status_code=501, detail=str(exc))
    if isinstance(exc, MarketDataProviderError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Market data provider fetch failed")


async def _validate_instrument_if_provided(db: AsyncSession, instrument_id: int | None) -> None:
    if instrument_id is None:
        return
    instrument = (await db.execute(select(Instrument.id).where(Instrument.id == instrument_id))).scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument with ID {instrument_id} not found")


@router.get("/catalog")
async def get_market_data_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    catalog = await AdminMarketDataService.get_catalog(db)
    payload = MarketDataCatalogResponse(**catalog).model_dump(mode="json")
    return success_response(payload)


@router.get("/datasets")
async def get_market_data_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(default=None),
    instrument_id: int | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    freshness_status: str | None = Query(default=None, pattern="^(fresh|warning|stale|no_data)$"),
    stale_after_hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, instrument_id)

    datasets = await AdminMarketDataService.list_datasets(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        instrument_id=instrument_id,
        timeframe=timeframe,
        freshness_status=freshness_status,
        stale_after_hours=stale_after_hours,
    )
    payload = MarketDataDatasetListResponse(**datasets).model_dump(mode="json")
    return success_response(payload, "No data found" if payload.get("total", 0) == 0 else None)


@router.get("/jobs")
async def get_market_data_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(default=None),
    failed_only: bool = Query(default=False),
    has_invalid: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    job_type: str | None = Query(default=None, pattern="^(market_data_import|market_data_upload|market_data_refresh|CSV_UPLOAD)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    jobs = await AdminMarketDataService.list_import_jobs(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        failed_only=failed_only,
        has_invalid=has_invalid,
        search=search,
        job_type=job_type,
    )
    payload = MarketDataJobListResponse(**jobs).model_dump(mode="json")
    return success_response(payload, "No data found" if payload.get("total", 0) == 0 else None)


@router.post("/upload-csv")
async def upload_market_data_csv(
    instrument_id: int = Form(...),
    timeframe: str = Form(...),
    source: str = Form(default="CSV"),
    dry_run: bool = Form(default=False),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, instrument_id)

    normalized_timeframe = timeframe.strip().lower()
    if not _is_supported_timeframe(normalized_timeframe):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe '{timeframe}'. Supported examples: 1m, 5m, 15m, 1h, 1d",
        )

    cleaned_source = _clean_source(source)
    rows = await _read_csv_upload(file)

    try:
        summary_obj = await upsert_market_data_candles(
            db,
            instrument_id=instrument_id,
            timeframe=normalized_timeframe,
            candles=rows,
            source=cleaned_source,
            dry_run=dry_run,
            commit=False,
        )
        summary = summary_obj.as_dict()

        if summary.get("valid_rows", 0) == 0:
            await db.rollback()
            job_id = await _create_csv_upload_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                instrument_id=instrument_id,
                timeframe=normalized_timeframe,
                source=cleaned_source,
                filename=file.filename,
                dry_run=dry_run,
                status_value="failed",
                message="CSV import failed: no valid candle rows found",
                summary=summary,
                error_message="No valid candle rows found",
            )
            await db.commit()
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "CSV import failed because no valid candle rows were found",
                    "summary": summary,
                    "job_id": job_id,
                },
            )

        job_id = await _create_csv_upload_job(
            db,
            admin_user_id=str(current_user["user_id"]),
            instrument_id=instrument_id,
            timeframe=normalized_timeframe,
            source=cleaned_source,
            filename=file.filename,
            dry_run=dry_run,
            status_value="completed",
            message="CSV dry run completed" if dry_run else "CSV upload import completed",
            summary=summary,
        )
        await db.commit()

        payload = {
            "status": "success",
            "job_id": job_id,
            "instrument_id": instrument_id,
            "timeframe": normalized_timeframe,
            "source": cleaned_source,
            "dry_run": dry_run,
            "filename": file.filename,
            "summary": summary,
        }
        return success_response(payload)
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        try:
            await _create_csv_upload_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                instrument_id=instrument_id,
                timeframe=normalized_timeframe,
                source=cleaned_source,
                filename=file.filename,
                dry_run=dry_run,
                status_value="failed",
                message="CSV upload import failed",
                error_message=str(exc),
            )
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSV upload import failed. Please verify the CSV format and try again.",
        ) from exc




@router.post("/fetch-preview")
async def fetch_market_data_preview(
    request: MarketDataFetchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)

    provider_name = normalize_provider_name(request.provider)
    normalized_timeframe = request.timeframe.strip().lower()
    if not _is_supported_timeframe(normalized_timeframe):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe '{request.timeframe}'. Supported examples: 1m, 5m, 15m, 1h, 1d",
        )

    start_dt = _as_utc_datetime(request.start_date)
    end_dt = _as_utc_end_datetime(request.end_date)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_date must be greater than start_date")

    symbol = _clean_symbol(request.symbol)
    try:
        provider = get_market_data_provider(provider_name)
        candles = await provider.fetch_candles(
            symbol=symbol,
            timeframe=normalized_timeframe,
            start_date=start_dt,
            end_date=end_dt,
            instrument_id=request.instrument_id,
            instrument_key=request.instrument_key,
            broker_account_id=request.broker_account_id,
            db=db,
        )
        summary_obj = await upsert_market_data_candles(
            db,
            instrument_id=request.instrument_id,
            timeframe=normalized_timeframe,
            candles=candles,
            source=provider_name,
            dry_run=True,
            commit=False,
        )
        await db.rollback()
    except Exception as exc:
        raise _provider_error_to_http(exc) from exc

    payload = {
        "provider": provider_name,
        "symbol": symbol,
        "instrument_key": request.instrument_key,
        "instrument_id": request.instrument_id,
        "timeframe": normalized_timeframe,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "summary": summary_obj.as_dict(),
        "saved": False,
        "note": "Preview only. No candles were inserted or updated.",
    }
    return success_response(payload)


@router.post("/fetch-import")
async def fetch_market_data_import(
    request: MarketDataFetchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)

    provider_name = normalize_provider_name(request.provider)

    normalized_timeframe = request.timeframe.strip().lower()
    if not _is_supported_timeframe(normalized_timeframe):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe '{request.timeframe}'. Supported examples: 1m, 5m, 15m, 1h, 1d",
        )

    start_dt = _as_utc_datetime(request.start_date)
    end_dt = _as_utc_end_datetime(request.end_date)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_date must be greater than start_date")

    symbol = _clean_symbol(request.symbol)
    try:
        provider = get_market_data_provider(provider_name)
        candles = await provider.fetch_candles(
            symbol=symbol,
            timeframe=normalized_timeframe,
            start_date=start_dt,
            end_date=end_dt,
            instrument_id=request.instrument_id,
            instrument_key=request.instrument_key,
            broker_account_id=request.broker_account_id,
            db=db,
        )
        summary_obj = await upsert_market_data_candles(
            db,
            instrument_id=request.instrument_id,
            timeframe=normalized_timeframe,
            candles=candles,
            source=provider_name,
            dry_run=request.dry_run,
            commit=False,
        )
        summary = summary_obj.as_dict()
        if int(summary.get("valid_rows") or 0) <= 0:
            await db.rollback()
            await _create_market_data_operation_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                job_type="market_data_import",
                provider=provider_name,
                instrument_id=request.instrument_id,
                timeframe=normalized_timeframe,
                symbol=symbol,
                instrument_key=request.instrument_key,
                dry_run=request.dry_run,
                status_value="failed",
                message="Broker import failed: no valid candle rows found",
                summary=summary,
                error_message="No valid candle rows found",
            )
            await db.commit()
            raise HTTPException(
                status_code=422,
                detail={"message": "No valid candle rows were returned by the provider", "summary": summary},
            )
        job_id = await _create_market_data_operation_job(
            db,
            admin_user_id=str(current_user["user_id"]),
            job_type="market_data_import",
            provider=provider_name,
            instrument_id=request.instrument_id,
            timeframe=normalized_timeframe,
            symbol=symbol,
            instrument_key=request.instrument_key,
            dry_run=request.dry_run,
            status_value="completed",
            message="Broker fetch dry run completed" if request.dry_run else "Broker historical candles imported",
            summary=summary,
        )
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        try:
            await _create_market_data_operation_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                job_type="market_data_import",
                provider=provider_name,
                instrument_id=request.instrument_id,
                timeframe=normalized_timeframe,
                symbol=symbol if "symbol" in locals() else request.symbol,
                instrument_key=request.instrument_key,
                dry_run=request.dry_run,
                status_value="failed",
                message="Broker historical candle import failed",
                error_message=str(exc),
            )
            await db.commit()
        except Exception:
            await db.rollback()
        raise _provider_error_to_http(exc) from exc

    payload = {
        "provider": provider_name,
        "symbol": symbol,
        "instrument_key": request.instrument_key,
        "instrument_id": request.instrument_id,
        "timeframe": normalized_timeframe,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "summary": summary_obj.as_dict(),
        "dry_run": request.dry_run,
        "saved": not request.dry_run,
        "job_id": job_id,
        "note": "Dry run only. No candles were inserted or updated." if request.dry_run else "Historical candles imported into market_data.",
    }
    return success_response(payload)

@router.post("/refresh-missing")
async def refresh_missing_market_data(
    request: MarketDataRefreshMissingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)

    provider_name = normalize_provider_name(request.provider)
    normalized_timeframe = request.timeframe.strip().lower()
    if not _is_supported_timeframe(normalized_timeframe):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe '{request.timeframe}'. Supported examples: 1m, 5m, 15m, 1h, 1d",
        )

    latest_candle_at = (
        await db.execute(
            select(func.max(MarketData.timestamp)).where(
                MarketData.instrument_id == request.instrument_id,
                MarketData.timeframe == normalized_timeframe,
            )
        )
    ).scalar_one_or_none()

    if latest_candle_at is None:
        raise HTTPException(
            status_code=400,
            detail="No existing candles found for this instrument/timeframe. Use Fetch & Save first, then Refresh Missing later.",
        )

    latest_candle_at = _as_utc_datetime(latest_candle_at)
    start_dt = latest_candle_at - _timeframe_overlap(normalized_timeframe)
    end_dt = _as_utc_end_datetime(request.end_date)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="Dataset is already up to date for the selected end_date")

    symbol = _clean_symbol(request.symbol)
    try:
        provider = get_market_data_provider(provider_name)
        candles = await provider.fetch_candles(
            symbol=symbol,
            timeframe=normalized_timeframe,
            start_date=start_dt,
            end_date=end_dt,
            instrument_id=request.instrument_id,
            instrument_key=request.instrument_key,
            broker_account_id=request.broker_account_id,
            db=db,
        )
        summary_obj = await upsert_market_data_candles(
            db,
            instrument_id=request.instrument_id,
            timeframe=normalized_timeframe,
            candles=candles,
            source=provider_name,
            dry_run=request.dry_run,
            commit=False,
        )
        summary = summary_obj.as_dict()
        if int(summary.get("valid_rows") or 0) <= 0:
            await db.rollback()
            await _create_market_data_operation_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                job_type="market_data_refresh",
                provider=provider_name,
                instrument_id=request.instrument_id,
                timeframe=normalized_timeframe,
                symbol=symbol,
                instrument_key=request.instrument_key,
                dry_run=request.dry_run,
                status_value="failed",
                message="Refresh missing failed: no valid candle rows found",
                summary=summary,
                error_message="No valid candle rows found",
            )
            await db.commit()
            raise HTTPException(
                status_code=422,
                detail={"message": "No valid missing candles were returned by the provider", "summary": summary},
            )
        job_id = await _create_market_data_operation_job(
            db,
            admin_user_id=str(current_user["user_id"]),
            job_type="market_data_refresh",
            provider=provider_name,
            instrument_id=request.instrument_id,
            timeframe=normalized_timeframe,
            symbol=symbol,
            instrument_key=request.instrument_key,
            dry_run=request.dry_run,
            status_value="completed",
            message="Refresh missing dry run completed" if request.dry_run else "Missing candles refreshed",
            summary=summary,
        )
        if request.dry_run:
            await db.rollback()
        else:
            await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        try:
            await _create_market_data_operation_job(
                db,
                admin_user_id=str(current_user["user_id"]),
                job_type="market_data_refresh",
                provider=provider_name,
                instrument_id=request.instrument_id,
                timeframe=normalized_timeframe,
                symbol=symbol if "symbol" in locals() else request.symbol,
                instrument_key=request.instrument_key,
                dry_run=request.dry_run,
                status_value="failed",
                message="Refresh missing candles failed",
                error_message=str(exc),
            )
            await db.commit()
        except Exception:
            await db.rollback()
        raise _provider_error_to_http(exc) from exc

    payload = {
        "provider": provider_name,
        "symbol": symbol,
        "instrument_key": request.instrument_key,
        "instrument_id": request.instrument_id,
        "timeframe": normalized_timeframe,
        "latest_existing_candle_at": latest_candle_at.isoformat(),
        "refresh_start_date": start_dt.isoformat(),
        "refresh_end_date": end_dt.isoformat(),
        "summary": summary_obj.as_dict(),
        "dry_run": request.dry_run,
        "saved": not request.dry_run,
        "job_id": job_id if not request.dry_run else None,
        "note": "Dry run only. Missing candles were not saved." if request.dry_run else "Missing candles refreshed into market_data.",
    }
    return success_response(payload)


@router.post("/hooks/import")
async def enqueue_market_data_import(
    request: MarketDataImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)
    job = await AdminMarketDataService.enqueue_market_data_job(
        db=db,
        admin_user_id=str(current_user["user_id"]),
        job_type="market_data_import",
        payload=request.model_dump(mode="json"),
    )
    payload = MarketDataJobEnqueueResponse(**job).model_dump(mode="json")
    return success_response(payload)


@router.post("/hooks/upload")
async def enqueue_market_data_upload(
    request: MarketDataImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)
    job = await AdminMarketDataService.enqueue_market_data_job(
        db=db,
        admin_user_id=str(current_user["user_id"]),
        job_type="market_data_upload",
        payload=request.model_dump(mode="json"),
    )
    payload = MarketDataJobEnqueueResponse(**job).model_dump(mode="json")
    return success_response(payload)


@router.post("/hooks/refresh")
async def enqueue_market_data_refresh(
    request: MarketDataRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    await _validate_instrument_if_provided(db, request.instrument_id)
    job = await AdminMarketDataService.enqueue_market_data_job(
        db=db,
        admin_user_id=str(current_user["user_id"]),
        job_type="market_data_refresh",
        payload=request.model_dump(mode="json"),
    )
    payload = MarketDataJobEnqueueResponse(**job).model_dump(mode="json")
    return success_response(payload)
