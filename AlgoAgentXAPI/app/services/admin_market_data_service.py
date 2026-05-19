from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..celery_app import is_celery_available
from ..core.redis_manager import redis_manager
from ..db.compat import as_uuid_or_str
from ..db.models import Instrument, JobStatus, MarketData


class AdminMarketDataService:
    _KNOWN_TIMEFRAME_MINUTES = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "10m": 10,
        "15m": 15,
        "30m": 30,
        "45m": 45,
        "60m": 60,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "1d": 1440,
        "1w": 10080,
    }

    _MARKET_DATA_JOB_TYPES = ["market_data_import", "market_data_upload", "market_data_refresh", "CSV_UPLOAD"]

    @staticmethod
    def _safe_json_loads(payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            data = json.loads(payload)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _normalize_timeframe_to_hours(timeframe: str | None) -> int:
        if not timeframe:
            return 24

        tf = timeframe.strip().lower()
        if tf in AdminMarketDataService._KNOWN_TIMEFRAME_MINUTES:
            minutes = AdminMarketDataService._KNOWN_TIMEFRAME_MINUTES[tf]
            return max(1, math.ceil(minutes / 60))

        match = re.match(r"^(\d+)(m|h|d|w)$", tf)
        if not match:
            return 24

        value = int(match.group(1))
        unit = match.group(2)
        if unit == "m":
            return max(1, math.ceil(value / 60))
        if unit == "h":
            return max(1, value)
        if unit == "d":
            return max(1, value * 24)
        if unit == "w":
            return max(1, value * 24 * 7)
        return 24

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_market(exchange: str | None, market: str | None, symbol: str | None = None) -> str:
        raw = " ".join([str(exchange or ""), str(market or ""), str(symbol or "")]).upper()
        if any(token in raw for token in ("CRYPTO", "BINANCE", "BTC", "ETH", "USDT")):
            return "CRYPTO"
        if any(token in raw for token in ("FOREX", "FX", "MT5", "XAU", "XAG", "USD", "EUR", "GBP", "JPY")):
            return "FOREX"
        if any(token in raw for token in ("NSE", "BSE", "INDIAN", "EQUITY", "NIFTY", "BANKNIFTY")):
            return "INDIAN_EQUITY"
        return "GENERIC"

    @staticmethod
    def _previous_weekday(value: datetime) -> datetime:
        current = value
        while current.weekday() >= 5:
            current = current - timedelta(days=1)
        return current

    @staticmethod
    def _latest_expected_time(market_rule: str, timeframe: str, now: datetime) -> datetime:
        tf = (timeframe or "").strip().lower()
        if market_rule == "CRYPTO":
            return now

        if market_rule == "FOREX":
            # Forex is treated as 24x5. On weekends, expect the last Friday candle.
            expected = AdminMarketDataService._previous_weekday(now)
            if expected.weekday() == 4 and now.weekday() >= 5:
                return expected.replace(hour=23, minute=59, second=0, microsecond=0)
            return expected

        if market_rule == "INDIAN_EQUITY":
            # Keep this intentionally simple: weekdays only, normal NSE close around 15:30 IST.
            expected = AdminMarketDataService._previous_weekday(now)
            if tf == "1d":
                return expected.replace(hour=15, minute=30, second=0, microsecond=0)
            return expected

        return now

    @staticmethod
    def _freshness_for(
        last_candle_at: datetime | None,
        timeframe: str,
        exchange: str | None = None,
        market: str | None = None,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        tf = (timeframe or "").strip().lower()
        market_rule = AdminMarketDataService._normalize_market(exchange, market, symbol)

        if last_candle_at is None:
            return {
                "freshness_status": "no_data",
                "status": "NO_DATA",
                "freshness_age_hours": None,
                "expected_freshness_status": "NO_DATA",
                "expected_fresh_hours": None,
                "warning_after_hours": None,
                "missing_from_date": None,
                "is_stale": True,
                "market_rule": market_rule,
            }

        now = AdminMarketDataService._utc_now()
        latest = AdminMarketDataService._as_utc(last_candle_at)
        if latest is None:
            return {
                "freshness_status": "no_data",
                "status": "NO_DATA",
                "freshness_age_hours": None,
                "expected_freshness_status": "NO_DATA",
                "expected_fresh_hours": None,
                "warning_after_hours": None,
                "missing_from_date": None,
                "is_stale": True,
                "market_rule": market_rule,
            }

        expected_latest = AdminMarketDataService._latest_expected_time(market_rule, tf, now)
        age_hours = max((expected_latest - latest).total_seconds() / 3600.0, 0.0)

        if tf == "5m":
            fresh_after_hours, warning_after_hours = 0.5, 24
        elif tf == "15m":
            fresh_after_hours, warning_after_hours = 1, 24
        elif tf in {"1h", "60m"}:
            fresh_after_hours, warning_after_hours = 3, 48
        elif tf == "1d":
            if latest.date() >= expected_latest.date():
                status = "fresh"
            elif age_hours <= 24 * 7:
                status = "warning"
            else:
                status = "stale"
            return {
                "freshness_status": status,
                "status": status.upper(),
                "freshness_age_hours": round(age_hours, 2),
                "expected_freshness_status": status.upper(),
                "expected_fresh_hours": 24,
                "warning_after_hours": 24 * 7,
                "missing_from_date": latest.isoformat() if status in {"warning", "stale"} else None,
                "is_stale": status == "stale",
                "market_rule": market_rule,
            }
        else:
            base_hours = AdminMarketDataService._normalize_timeframe_to_hours(tf)
            fresh_after_hours, warning_after_hours = max(1, base_hours * 3), max(24, base_hours * 6)

        if age_hours <= fresh_after_hours:
            status = "fresh"
        elif age_hours <= warning_after_hours:
            status = "warning"
        else:
            status = "stale"

        return {
            "freshness_status": status,
            "status": status.upper(),
            "freshness_age_hours": round(age_hours, 2),
            "expected_freshness_status": status.upper(),
            "expected_fresh_hours": fresh_after_hours,
            "warning_after_hours": warning_after_hours,
            "missing_from_date": latest.isoformat() if status in {"warning", "stale"} else None,
            "is_stale": status == "stale",
            "market_rule": market_rule,
        }

    @staticmethod
    async def get_catalog(db: AsyncSession) -> dict[str, Any]:
        instruments = (await db.execute(select(Instrument).order_by(Instrument.symbol.asc()))).scalars().all()
        timeframes = (
            await db.execute(
                select(MarketData.timeframe)
                .where(MarketData.timeframe.is_not(None))
                .distinct()
                .order_by(MarketData.timeframe.asc())
            )
        ).scalars().all()

        return {
            "instruments": [
                {
                    "id": instrument.id,
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                    "market": instrument.market,
                    "instrument_type": instrument.instrument_type,
                    "broker_symbol": getattr(instrument, "broker_symbol", None),
                    "upstox_instrument_key": getattr(instrument, "upstox_instrument_key", None) or getattr(instrument, "instrument_key", None),
                }
                for instrument in instruments
            ],
            "timeframes": [tf for tf in timeframes if tf],
        }

    @staticmethod
    async def list_datasets(
        db: AsyncSession,
        page: int,
        page_size: int,
        search: str | None,
        instrument_id: int | None,
        timeframe: str | None,
        freshness_status: str | None,
        stale_after_hours: int,
    ) -> dict[str, Any]:
        stmt = (
            select(
                MarketData.instrument_id.label("instrument_id"),
                Instrument.symbol.label("instrument_symbol"),
                Instrument.exchange.label("exchange"),
                Instrument.market.label("market"),
                MarketData.timeframe.label("timeframe"),
                func.min(MarketData.timestamp).label("first_candle_at"),
                func.max(MarketData.timestamp).label("last_candle_at"),
                func.count().label("total_records"),
            )
            .join(Instrument, Instrument.id == MarketData.instrument_id)
            .group_by(MarketData.instrument_id, Instrument.symbol, Instrument.exchange, Instrument.market, MarketData.timeframe)
            .order_by(Instrument.symbol.asc(), MarketData.timeframe.asc())
        )

        if instrument_id is not None:
            stmt = stmt.where(MarketData.instrument_id == instrument_id)
        if timeframe:
            stmt = stmt.where(MarketData.timeframe == timeframe)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Instrument.symbol.ilike(like),
                    Instrument.exchange.ilike(like),
                    Instrument.market.ilike(like),
                    MarketData.timeframe.ilike(like),
                )
            )

        rows = (await db.execute(stmt)).all()
        items = []
        for row in rows:
            freshness = AdminMarketDataService._freshness_for(
                row.last_candle_at,
                row.timeframe,
                row.exchange,
                row.market,
                row.instrument_symbol,
            )
            total_records = int(row.total_records or 0)
            items.append(
                {
                    "instrument_id": row.instrument_id,
                    "instrument_symbol": row.instrument_symbol,
                    "instrument": row.instrument_symbol,
                    "exchange": row.exchange,
                    "market": row.market,
                    "timeframe": row.timeframe,
                    "first_candle_at": row.first_candle_at,
                    "last_candle_at": row.last_candle_at,
                    "latest_candle_at": row.last_candle_at,
                    "latest_candle_date": row.last_candle_at.date().isoformat() if row.last_candle_at else None,
                    "total_records": total_records,
                    "record_count": total_records,
                    **freshness,
                }
            )

        if freshness_status:
            normalized = freshness_status.strip().lower()
            items = [item for item in items if item["freshness_status"] == normalized]

        total = len(items)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        paged_items = items[start : start + page_size]

        summary = {
            "total_datasets": total,
            "total_records": sum(item["total_records"] for item in items),
            "fresh_count": sum(1 for item in items if item["freshness_status"] == "fresh"),
            "warning_count": sum(1 for item in items if item["freshness_status"] == "warning"),
            "stale_count": sum(1 for item in items if item["freshness_status"] == "stale"),
            "no_data_count": sum(1 for item in items if item["freshness_status"] == "no_data"),
        }

        return {
            "items": paged_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "summary": summary,
        }

    @staticmethod
    async def list_import_jobs(
        db: AsyncSession,
        page: int,
        page_size: int,
        status: str | None,
        failed_only: bool,
        has_invalid: bool | None,
        search: str | None,
        job_type: str | None,
    ) -> dict[str, Any]:
        stmt = select(JobStatus).where(JobStatus.job_type.in_(AdminMarketDataService._MARKET_DATA_JOB_TYPES))
        if status:
            stmt = stmt.where(JobStatus.status == status)
        if job_type:
            stmt = stmt.where(JobStatus.job_type == job_type)

        stmt = stmt.order_by(JobStatus.created_at.desc())
        rows = (await db.execute(stmt)).scalars().all()

        items = []
        for row in rows:
            job_data = AdminMarketDataService._safe_json_loads(row.job_data)
            result_data = AdminMarketDataService._safe_json_loads(row.result_data)

            imported_rows = result_data.get("imported_rows")
            if imported_rows is None:
                imported_rows = result_data.get("rows_imported")
            invalid_rows = result_data.get("invalid_rows")
            if invalid_rows is None:
                invalid_rows = result_data.get("rows_invalid")

            has_invalid_data = bool((invalid_rows or 0) > 0 or result_data.get("has_invalid_data"))
            error_message = result_data.get("error") or result_data.get("error_message")
            if row.status == "failed" and not error_message:
                error_message = row.message

            dataset_uri = job_data.get("dataset_uri")
            if not dataset_uri:
                dataset_uri = result_data.get("dataset_uri")

            item = {
                "job_id": row.id,
                "job_type": row.job_type,
                "status": row.status,
                "progress": int(row.progress or 0),
                "message": row.message,
                "retry_count": int(row.retry_count or 0),
                "max_retries": int(row.max_retries or 0),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "instrument_id": job_data.get("instrument_id"),
                "timeframe": job_data.get("timeframe"),
                "source": job_data.get("source"),
                "dataset_uri": dataset_uri,
                "imported_rows": imported_rows,
                "invalid_rows": invalid_rows,
                "has_invalid_data": has_invalid_data,
                "error_message": error_message,
            }

            items.append(item)

        if failed_only:
            items = [item for item in items if item["status"] == "failed"]
        if has_invalid is not None:
            items = [item for item in items if item["has_invalid_data"] is has_invalid]
        if search:
            normalized_search = search.strip().lower()
            items = [
                item
                for item in items
                if normalized_search in str(item["job_id"]).lower()
                or normalized_search in str(item.get("instrument_id") or "").lower()
                or normalized_search in str(item.get("timeframe") or "").lower()
                or normalized_search in str(item.get("source") or "").lower()
                or normalized_search in str(item.get("dataset_uri") or "").lower()
                or normalized_search in str(item.get("error_message") or "").lower()
            ]

        total = len(items)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size

        return {
            "items": items[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def enqueue_market_data_job(
        db: AsyncSession,
        admin_user_id: str,
        job_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        job_id = str(uuid4())
        pipeline_ready = bool(is_celery_available() and redis_manager.is_available)
        message = (
            "Hook accepted and queued. Bind worker to process this market-data job type."
            if pipeline_ready
            else "Hook accepted in fallback mode. Worker binding for this job type is pending."
        )

        db.add(
            JobStatus(
                id=job_id,
                user_id=as_uuid_or_str(admin_user_id),
                job_type=job_type,
                status="pending",
                progress=0,
                message=message,
                job_data=json.dumps(payload, default=str),
                created_at=datetime.utcnow(),
            )
        )
        await db.commit()

        return {
            "job_id": job_id,
            "status": "pending",
            "job_type": job_type,
            "pipeline_ready": pipeline_ready,
            "message": message,
            "payload": payload,
        }
