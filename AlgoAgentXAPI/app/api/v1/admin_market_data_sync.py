"""Admin-only history sync, connected-account discovery and feed management."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import (BrokerAccount, Instrument, MarketData, MarketDataFeedCandle,
                          MarketDataSyncConfig, MarketDataSyncRun, User)
from ...services.market_data.daily_sync import (HISTORY_CODES, TIMEFRAMES, broker_symbol_catalog, broker_exact_match, enabled_globally,
                                                 last_expected_closed, next_daily_run, subaccounts, verify_source)
from ...services.market_data.daily_tasks import process_market_history, process_market_canonical_publish
from ...services.market_data.feed_publish import preview_publication
from ...services.market_data.feed_inspection import inspect_feed_storage
from ...utils.api_response import success_response

router = APIRouter(dependencies=[Depends(get_admin_user)])


def _masked(value):
    return "•••" + str(value)[-4:]


def _config_data(row, latest=None, source_count=0, source_first=None):
    return {
        "id": str(row.id), "broker_account_id": str(row.broker_account_id), "instrument_id": row.instrument_id,
        "provider": row.provider, "subaccount_id": row.subaccount_id, "broker_symbol": row.broker_symbol,
        "timeframe": row.timeframe, "enabled": row.enabled, "is_primary": row.is_primary,
        "publish_approved": row.publish_approved, "initial_start": row.initial_start,
        "last_candle": latest, "source_first": source_first, "source_count": source_count,
        "expected_last_closed_utc": last_expected_closed(datetime.now(timezone.utc), row.timeframe),
        "checkpoint": row.checkpoint, "last_status": row.last_status,
        "last_error": row.last_error, "last_synced_at": row.last_synced_at,
    }


class CreateConfig(BaseModel):
    broker_account_id: UUID
    subaccount_id: str = Field(min_length=1, max_length=120)
    instrument_id: int = Field(gt=0)
    broker_symbol: str = Field(min_length=1, max_length=120)
    timeframe: str = Field(default="5m")
    initial_start: datetime | None = None
    enabled: bool = False


class RunNowRequest(BaseModel):
    # Only used for a feed with no candle and no configured initial_start.
    bootstrap_days: int = Field(default=7, ge=1, le=120)


class ManualRange(BaseModel):
    start_date: datetime
    end_date: datetime
    dry_run: bool = False


class EditConfig(BaseModel):
    enabled: bool | None = None
    initial_start: datetime | None = None
    broker_symbol: str | None = Field(default=None, min_length=1, max_length=120)


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)):
    configs = (await db.execute(select(func.count()).select_from(MarketDataSyncConfig))).scalar_one()
    enabled = (await db.execute(select(func.count()).select_from(MarketDataSyncConfig).where(MarketDataSyncConfig.enabled.is_(True)))).scalar_one()
    return success_response({"feature_enabled": enabled_globally(), "config_count": configs, "enabled_count": enabled,
                             "next_scheduled_at": next_daily_run(), "timezone": "Asia/Kolkata",
                             "note": "Each broker feed is separate; legacy backtests are never overwritten."})


@router.get("/accounts")
async def accounts(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
                   search: str = "", db: AsyncSession = Depends(get_db)):
    query = select(BrokerAccount, User).join(User, User.id == BrokerAccount.user_id)
    if search.strip():
        query = query.where(BrokerAccount.account_label.ilike("%" + search[:60] + "%"))
    count = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.order_by(BrokerAccount.created_at.desc()).offset((page-1)*page_size).limit(page_size))).all()
    items = []
    for account, user in rows:
        code = str(account.broker_code or account.broker_name or "").upper()
        if code == "CTRADER_API":
            code = "CTRADER"
        items.append({"id": str(account.id), "provider": code, "label": f"{code} {_masked(account.id)}",
                      "user": _masked(user.id), "mode": account.mode, "status": account.status,
                      "subaccounts": subaccounts(account),
                      "history_supported": code in {"CTRADER", "TRADELOCKER"},
                      "capability": "READY" if code in {"CTRADER", "TRADELOCKER"} and account.status == "CONNECTED" and subaccounts(account) else "UNSUPPORTED_OR_NOT_SELECTED"})
    return success_response({"items": items, "total": count, "page": page, "page_size": page_size})


@router.get("/accounts/{account_id}/symbols")
async def discover_account_symbols(account_id: UUID, subaccount_id: str = Query(..., min_length=1, max_length=120),
                                   db: AsyncSession = Depends(get_db)):
    """Admin-only list of real broker symbols for the exact authorized trading subaccount."""
    account = await db.get(BrokerAccount, account_id)
    if account is None:
        raise HTTPException(404, "Broker account not found")
    try:
        rows = await broker_symbol_catalog(db, account, subaccount_id)
    except ValueError as exc:
        raise HTTPException(400, "Selected account cannot provide history symbols; check the trading subaccount") from exc
    except Exception as exc:
        # Never return URLs, OAuth errors, API tokens or upstream response bodies.
        raise HTTPException(503, "Broker symbol discovery unavailable; reconnect account and retry") from exc
    return success_response({"items": rows, "total": len(rows),
                             "provider": str(account.broker_code or account.broker_name).upper().replace("CTRADER_API", "CTRADER")})


async def _require_exact_symbol(db: AsyncSession, account: BrokerAccount, subaccount_id: str, symbol: str) -> str:
    try:
        rows = await broker_symbol_catalog(db, account, subaccount_id)
    except ValueError as exc:
        raise HTTPException(400, "Broker cannot provide a symbol list for the chosen trading subaccount") from exc
    except Exception as exc:
        raise HTTPException(503, "Broker symbol verification unavailable; reconnect and retry") from exc
    matched = broker_exact_match(rows, symbol)
    if not matched:
        raise HTTPException(422, "BROKER_SYMBOL: Symbol is not listed for this trading subaccount; choose an exact symbol from Discover Symbols")
    return matched


@router.get("/configs")
async def list_configs(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
                       db: AsyncSession = Depends(get_db)):
    count = (await db.execute(select(func.count()).select_from(MarketDataSyncConfig))).scalar_one()
    stmt = select(MarketDataSyncConfig, func.max(MarketDataFeedCandle.timestamp),
                  func.count(MarketDataFeedCandle.timestamp), func.min(MarketDataFeedCandle.timestamp)).outerjoin(
        MarketDataFeedCandle, MarketDataFeedCandle.feed_id == MarketDataSyncConfig.id).group_by(MarketDataSyncConfig.id)
    rows = (await db.execute(stmt.order_by(MarketDataSyncConfig.created_at.desc()).offset((page-1)*page_size).limit(page_size))).all()
    return success_response({"items": [_config_data(config, latest, source_count, source_first)
                                       for config, latest, source_count, source_first in rows],
                             "total": count, "page": page, "page_size": page_size})


@router.get("/canonical-source")
async def canonical_source(instrument_id: int = Query(..., gt=0), timeframe: str = Query(...),
                           db: AsyncSession = Depends(get_db)):
    """Use the selected primary feed, NEVER the manual tab's provider dropdown."""
    config = (await db.execute(select(MarketDataSyncConfig).where(
        MarketDataSyncConfig.instrument_id == instrument_id,
        MarketDataSyncConfig.timeframe == timeframe.strip().lower(),
        MarketDataSyncConfig.is_primary.is_(True),
        MarketDataSyncConfig.is_archived.is_(False)))).scalar_one_or_none()
    return success_response({"feed": _config_data(config) if config else None})


class PublishMissingRequest(BaseModel):
    confirm_insert_missing_only: bool = False


@router.get("/configs/{config_id}/publish-preview")
async def publish_preview(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None or config.is_archived:
        raise HTTPException(404, "Feed configuration not found")
    return success_response(await preview_publication(db, config))


@router.post("/configs/{config_id}/publish-missing", status_code=202)
async def publish_missing(config_id: UUID, payload: PublishMissingRequest,
                          db: AsyncSession = Depends(get_db)):
    """Explicit source adoption: add absent cTrader/TradeLocker timestamps only.

    The primary-selection button alone does NOT approve merging broker histories.
    Every inserted row has provenance and an audit run; conflicts are immutable.
    """
    if not payload.confirm_insert_missing_only:
        raise HTTPException(400, "Explicit insert-missing-only confirmation is required")
    config = (await db.execute(select(MarketDataSyncConfig).where(
        MarketDataSyncConfig.id == config_id).with_for_update())).scalar_one_or_none()
    if config is None or config.is_archived:
        raise HTTPException(404, "Feed configuration not found")
    if not config.is_primary:
        raise HTTPException(409, "Select this source as Primary before publishing to backtests")
    amount = (await db.execute(select(func.count()).select_from(MarketDataFeedCandle).where(
        MarketDataFeedCandle.feed_id == config.id))).scalar_one()
    if amount < 1:
        raise HTTPException(409, "Source has no stored candles. Fetch & Save a history range first")
    previously_approved = bool(config.publish_approved)
    config.publish_approved = True
    run = MarketDataSyncRun(feed_id=config.id, run_key=f"canonical-publish:{uuid4()}", status="QUEUED")
    db.add(run)
    await db.commit()
    try:
        process_market_canonical_publish.apply_async(args=[str(run.id)], queue="market_data_daily")
    except Exception as exc:
        run.status, run.error = "FAILED", "Canonical publishing worker unavailable"
        config.publish_approved = previously_approved
        await db.commit()
        raise HTTPException(503, "Canonical publishing worker unavailable; approval not changed") from exc
    return success_response({"status": "QUEUED", "run_id": str(run.id), "publish_approved": True,
                             "mode": "INSERT_MISSING_ONLY", "overwrites": 0})


@router.post("/configs/{config_id}/archive")
async def archive_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete from schedule and UI, but retain source candles and audit records."""
    config = (await db.execute(select(MarketDataSyncConfig).where(
        MarketDataSyncConfig.id == config_id).with_for_update())).scalar_one_or_none()
    if config is None or config.is_archived:
        raise HTTPException(404, "Feed configuration not found")
    active = (await db.execute(select(func.count()).select_from(MarketDataSyncRun).where(
        MarketDataSyncRun.feed_id == config.id,
        MarketDataSyncRun.status.in_(["QUEUED", "RUNNING"])))).scalar_one()
    if active:
        raise HTTPException(409, "Wait for queued/running jobs to finish before deleting the configuration")
    config.enabled = False
    config.is_primary = False
    config.publish_approved = False
    config.is_archived = True
    await db.commit()
    return success_response({"status": "ARCHIVED", "id": str(config.id),
                             "note": "Configuration hidden and schedule disabled. Historical candles and audit preserved."})


@router.get("/configs/{config_id}/verification")
async def verify_feed_candles(config_id: UUID, db: AsyncSession = Depends(get_db)):
    """Read-only, admin-only source feed verification. Never returns account secrets."""
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    return success_response(await inspect_feed_storage(db, config))


@router.post("/configs", status_code=201)
async def create_config(payload: CreateConfig, db: AsyncSession = Depends(get_db)):
    account = await db.get(BrokerAccount, payload.broker_account_id)
    if account is None:
        raise HTTPException(404, "Connected broker account not found")
    provider = str(account.broker_code or account.broker_name).upper().replace("CTRADER_API", "CTRADER")
    try:
        verify_source(account, subaccount_id=payload.subaccount_id, provider=provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    instrument = await db.get(Instrument, payload.instrument_id)
    if instrument is None or not instrument.is_active:
        raise HTTPException(400, "Choose a valid active Market Master instrument")
    tf = payload.timeframe.strip().lower()
    if tf not in TIMEFRAMES:
        raise HTTPException(400, "Unsupported broker history timeframe")
    if provider not in {"CTRADER", "TRADELOCKER"}:
        raise HTTPException(400, "This provider currently has no verified account-scoped historical adapter; choose cTrader or TradeLocker")
    if provider == "TRADELOCKER" and tf not in {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}:
        raise HTTPException(400, "TradeLocker history does not support this timeframe")
    # if not payload.broker_symbol.strip() or any(ch.isspace() for ch in payload.broker_symbol.strip()):
    #     raise HTTPException(400, "Exact broker symbol must not be blank or contain whitespace")
    verified_symbol = await _require_exact_symbol(db, account, payload.subaccount_id, payload.broker_symbol)
    # A "deleted" feed is archived, never purged. Reusing the exact configuration
    # revives its original source candles/audit rather than hitting a unique-key error.
    archived = (await db.execute(select(MarketDataSyncConfig).where(
        MarketDataSyncConfig.broker_account_id == account.id,
        MarketDataSyncConfig.subaccount_id == payload.subaccount_id,
        MarketDataSyncConfig.instrument_id == instrument.id,
        MarketDataSyncConfig.broker_symbol == verified_symbol,
        MarketDataSyncConfig.timeframe == tf,
        MarketDataSyncConfig.is_archived.is_(True)))).scalar_one_or_none()
    if archived is not None:
        archived.is_archived = False
        archived.enabled = False  # No silent re-opt-in to daily fetching.
        archived.publish_approved = False  # Explicit consent required again.
        archived.is_primary = False
        await db.commit()
        return success_response(_config_data(archived))
    row = MarketDataSyncConfig(broker_account_id=account.id, instrument_id=instrument.id,
                                provider=provider, subaccount_id=payload.subaccount_id,
                                broker_symbol=verified_symbol, timeframe=tf,
                                initial_start=payload.initial_start, enabled=payload.enabled)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Duplicate broker feed configuration") from exc
    await db.refresh(row)
    return success_response(_config_data(row))


@router.patch("/configs/{config_id}")
async def edit_config(config_id: UUID, payload: EditConfig, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    if payload.broker_symbol is not None and payload.broker_symbol.strip().casefold() != config.broker_symbol.casefold():
        if config.last_status in {"QUEUED", "RUNNING"}:
            raise HTTPException(409, "Stop or finish the running history job before correcting its symbol")
        existing = (await db.execute(select(func.count()).select_from(MarketDataFeedCandle).where(
            MarketDataFeedCandle.feed_id == config.id))).scalar_one()
        if existing:
            raise HTTPException(409, "This feed already has candles. Create a separate feed to change its broker symbol without mixing historical prices")
        account = await db.get(BrokerAccount, config.broker_account_id)
        if account is None:
            raise HTTPException(404, "Connected broker account not found")
        verify_source(account, subaccount_id=config.subaccount_id, provider=config.provider)
        verified_symbol = await _require_exact_symbol(db, account, config.subaccount_id, payload.broker_symbol)
        config.broker_symbol = verified_symbol
        config.last_error = None
        config.last_status = "NEEDS_INITIAL_IMPORT"
        config.checkpoint = None
    if payload.enabled is not None:
        config.enabled = payload.enabled
    if payload.initial_start is not None:
        if (await db.execute(select(func.count()).select_from(MarketDataFeedCandle).where(MarketDataFeedCandle.feed_id == config.id))).scalar_one():
            raise HTTPException(409, "Initial start is locked after feed data exists")
        config.initial_start = payload.initial_start
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "This exact broker symbol feed is already configured") from exc
    return success_response(_config_data(config))


@router.delete("/configs/{config_id}")
async def disable_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    # Preserve feed OHLCV, history and audit: Delete is a non-destructive disable.
    config.enabled = False
    await db.commit()
    return success_response({"status": "DISABLED", "id": str(config.id)})


@router.post("/configs/{config_id}/primary")
async def choose_primary(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    # Changing primary may not change the legacy backtest feed when history exists.
    existing_count = (await db.execute(select(func.count()).select_from(MarketData).where(
        MarketData.instrument_id == config.instrument_id, MarketData.timeframe == config.timeframe))).scalar_one()
    await db.execute(update(MarketDataSyncConfig).where(
        MarketDataSyncConfig.instrument_id == config.instrument_id, MarketDataSyncConfig.timeframe == config.timeframe).values(
        is_primary=False, publish_approved=False))
    config.is_primary = True
    config.publish_approved = existing_count == 0  # no unknown legacy provenance
    await db.commit()
    return success_response({"primary": str(config.id), "publish_approved": config.publish_approved,
                             "note": "Canonical legacy data already exists; this primary is isolated until a separately audited source migration." if existing_count else "New empty canonical dataset approved for insert-only primary publishing."})


@router.post("/configs/{config_id}/run-now", status_code=202)
async def run_now(config_id: UUID, payload: RunNowRequest | None = None, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    if config.last_status in {"QUEUED", "RUNNING"}:
        raise HTTPException(409, "This feed already has a run in progress")
    existing = (await db.execute(select(func.max(MarketDataFeedCandle.timestamp)).where(
        MarketDataFeedCandle.feed_id == config.id))).scalar_one_or_none()
    bootstrap = existing is None and config.initial_start is None
    # Run Now must be useful on a NEW feed; take a small explicit lookback instead
    # of returning NEEDS_INITIAL_IMPORT, but never start an unbounded all-years job.
    days = (payload or RunNowRequest()).bootstrap_days
    now = datetime.now(timezone.utc)
    run = MarketDataSyncRun(feed_id=config.id, run_key=f"manual:{uuid4()}", status="QUEUED",
        requested_start=now - timedelta(days=days) if bootstrap else None,
        requested_end=now if bootstrap else None)
    db.add(run)
    config.last_status = "QUEUED"
    await db.commit()
    try:
        process_market_history.apply_async(args=[str(run.id)], queue="market_data_daily")
    except Exception as exc:
        run.status = "FAILED"
        run.error = "History worker queue unavailable"
        config.last_status = "FAILED"
        await db.commit()
        raise HTTPException(503, "History worker queue unavailable") from exc
    return success_response({"status": "QUEUED", "run_id": str(run.id), "bootstrap_days": days if bootstrap else None})


@router.post("/configs/{config_id}/manual-fetch", status_code=202)
async def manual_range(config_id: UUID, payload: ManualRange, db: AsyncSession = Depends(get_db)):
    config = await db.get(MarketDataSyncConfig, config_id)
    if config is None:
        raise HTTPException(404, "Feed configuration not found")
    start = payload.start_date.replace(tzinfo=timezone.utc) if payload.start_date.tzinfo is None else payload.start_date.astimezone(timezone.utc)
    end = payload.end_date.replace(tzinfo=timezone.utc) if payload.end_date.tzinfo is None else payload.end_date.astimezone(timezone.utc)
    if not start < end <= datetime.now(timezone.utc) + timedelta(days=1):
        raise HTTPException(400, "Choose a valid UTC date range ending no later than tomorrow")
    if end - start > timedelta(days=120):
        raise HTTPException(400, "Max 120 calendar days per manual cTrader/TradeLocker job; split larger ranges")
    if config.last_status in {"QUEUED", "RUNNING"}:
        raise HTTPException(409, "This feed already has a run in progress")
    run = MarketDataSyncRun(feed_id=config.id, run_key=f"manual-range:{uuid4()}", status="QUEUED",
                             requested_start=start, requested_end=end, dry_run=payload.dry_run)
    db.add(run)
    config.last_status = "QUEUED"
    await db.commit()
    try:
        process_market_history.apply_async(args=[str(run.id)], queue="market_data_daily")
    except Exception as exc:
        run.status = "FAILED"
        run.error = "History worker queue unavailable"
        config.last_status = "FAILED"
        await db.commit()
        raise HTTPException(503, "History worker queue unavailable") from exc
    return success_response({"status": "QUEUED", "run_id": str(run.id), "dry_run": payload.dry_run})


@router.get("/runs")
async def runs(config_id: UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
               db: AsyncSession = Depends(get_db)):
    stmt = select(MarketDataSyncRun)
    if config_id:
        stmt = stmt.where(MarketDataSyncRun.feed_id == config_id)
    count = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(MarketDataSyncRun.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()
    return success_response({"items": [{"id": str(r.id), "config_id": str(r.feed_id), "status": r.status,
                                         "scheduled_date": r.scheduled_date, "requested_start": r.requested_start,
                                         "requested_end": r.requested_end, "dry_run": r.dry_run, "started_at": r.started_at,
                                         "finished_at": r.finished_at, "last_before": r.last_before, "last_after": r.last_after,
                                         "fetched": r.fetched, "inserted": r.inserted, "updated": r.updated,
                                         "invalid": r.invalid, "skipped": r.skipped, "error": r.error} for r in rows],
                             "total": count, "page": page})
