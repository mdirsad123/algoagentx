from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db
from ...utils.api_response import success_response

router = APIRouter()


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        result = await db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": f"public.{table_name}"})
        return result.scalar() is not None
    except Exception:
        return False


async def _column_exists(db: AsyncSession, table_name: str, column_name: str) -> bool:
    try:
        result = await db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND column_name = :column_name
                LIMIT 1
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        )
        return result.scalar() is not None
    except Exception:
        return False


async def _safe_count(db: AsyncSession, table_name: str, where_sql: str | None = None) -> int:
    """Return an aggregate count without exposing sensitive rows.

    Missing optional module tables/columns should never break the public landing page.
    """
    try:
        if not await _table_exists(db, table_name):
            return 0
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_sql:
            query += f" WHERE {where_sql}"
        result = await db.execute(text(query))
        return int(result.scalar() or 0)
    except Exception:
        return 0


@router.get("/landing-stats")
async def get_landing_stats(db: AsyncSession = Depends(get_db)):
    """Public aggregate landing page metrics only.

    This endpoint intentionally returns counts only. It does not expose users,
    broker credentials, strategy code, deployment details, or trade data.
    """
    connected_brokers_filter = None
    if await _column_exists(db, "broker_accounts", "status"):
        connected_brokers_filter = "UPPER(COALESCE(status, '')) IN ('CONNECTED', 'ACTIVE', 'AUTHORIZED')"

    live_deployments_filter = None
    if await _column_exists(db, "strategy_deployments", "status"):
        live_deployments_filter = "UPPER(COALESCE(status, '')) IN ('RUNNING', 'ACTIVE', 'STARTED', 'LIVE', 'PAUSED')"

    data = {
        "total_users": await _safe_count(db, "users"),
        "total_backtests": (await _safe_count(db, "backtests")) or (await _safe_count(db, "performance_metrics")),
        "total_strategies": await _safe_count(db, "strategies"),
        "connected_brokers": await _safe_count(db, "broker_accounts", connected_brokers_filter),
        "live_deployments": await _safe_count(db, "strategy_deployments", live_deployments_filter),
    }
    return success_response(data)
