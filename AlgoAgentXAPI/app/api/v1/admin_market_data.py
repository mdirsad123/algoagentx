from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import Instrument
from ...schemas.admin_market_data import (
    MarketDataCatalogResponse,
    MarketDataDatasetListResponse,
    MarketDataImportRequest,
    MarketDataJobEnqueueResponse,
    MarketDataJobListResponse,
    MarketDataRefreshRequest,
)
from ...services.admin_market_data_service import AdminMarketDataService
from ...utils.api_response import success_response

router = APIRouter()


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
    job_type: str | None = Query(default=None, pattern="^(market_data_import|market_data_upload|market_data_refresh)$"),
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
