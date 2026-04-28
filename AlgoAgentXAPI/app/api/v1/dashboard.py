from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...utils.api_response import success_response

router = APIRouter()


RUNNING_STATUSES = ("RUNNING", "ACTIVE", "STARTED", "LIVE")
PAUSED_STATUSES = ("PAUSED", "STOPPED", "INACTIVE")
CONNECTED_STATUSES = ("CONNECTED", "ACTIVE", "READY")
COMPLETED_STATUSES = ("COMPLETED", "SUCCESS", "DONE")
FAILED_STATUSES = ("FAILED", "ERROR", "CANCELLED")


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return default


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        result = await db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        )
        return result.scalar() is not None
    except Exception:
        await db.rollback()
        return False


async def _safe_scalar(db: AsyncSession, sql: str, params: dict[str, Any], default: Any = 0) -> Any:
    try:
        result = await db.execute(text(sql), params)
        value = result.scalar()
        return default if value is None else value
    except Exception:
        await db.rollback()
        return default


async def _safe_rows(db: AsyncSession, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        result = await db.execute(text(sql), params)
        return [dict(row._mapping) for row in result.fetchall()]
    except Exception:
        await db.rollback()
        return []


async def _broker_summary(db: AsyncSession, user_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not await _table_exists(db, "broker_accounts"):
        return {"total_broker_accounts": 0, "connected_brokers": 0, "active_broker_accounts": 0, "accounts": []}, []

    total = await _safe_scalar(db, "SELECT COUNT(*) FROM broker_accounts WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id})
    connected = await _safe_scalar(
        db,
        """
        SELECT COUNT(*) FROM broker_accounts
        WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status, '')) IN ('CONNECTED','ACTIVE','READY')
        """,
        {"user_id": user_id},
    )
    active = await _safe_scalar(
        db,
        """
        SELECT COUNT(*) FROM broker_accounts
        WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status, '')) NOT IN ('DISCONNECTED','ERROR','FAILED')
        """,
        {"user_id": user_id},
    )
    accounts = await _safe_rows(
        db,
        """
        SELECT id, broker_name, broker_code, account_label, mode, status, last_connected_at, updated_at
        FROM broker_accounts
        WHERE CAST(user_id AS TEXT)=:user_id
        ORDER BY COALESCE(updated_at, created_at) DESC
        LIMIT 5
        """,
        {"user_id": user_id},
    )
    mapped = [
        {
            "id": str(row.get("id")),
            "broker_name": row.get("broker_name") or row.get("broker_code") or "Broker",
            "account_label": row.get("account_label") or "Broker Account",
            "mode": row.get("mode") or "DEMO",
            "status": row.get("status") or "UNKNOWN",
            "last_sync_at": _iso(row.get("last_connected_at") or row.get("updated_at")),
        }
        for row in accounts
    ]
    return {
        "total_broker_accounts": _to_int(total),
        "connected_brokers": _to_int(connected),
        "active_broker_accounts": _to_int(active),
        "accounts": mapped,
    }, mapped


async def _strategy_summary(db: AsyncSession, user_id: str) -> dict[str, Any]:
    has_strategies = await _table_exists(db, "strategies")
    has_deployments = await _table_exists(db, "strategy_deployments")

    my_strategies = published = total = 0
    if has_strategies:
        my_strategies = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM strategies WHERE CAST(created_by AS TEXT)=:user_id", {"user_id": user_id}))
        published = _to_int(
            await _safe_scalar(
                db,
                """
                SELECT COUNT(*) FROM strategies
                WHERE UPPER(COALESCE(visibility,'')) IN ('PUBLIC','PUBLISHED')
                   OR UPPER(COALESCE(lifecycle_status,'')) IN ('PUBLISHED','LIVE_APPROVED','APPROVED')
                """,
                {},
            )
        )
        total = my_strategies + published

    deployed = running = paused = 0
    if has_deployments:
        deployed = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}))
        running = _to_int(
            await _safe_scalar(
                db,
                "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('RUNNING','ACTIVE','STARTED','LIVE')",
                {"user_id": user_id},
            )
        )
        paused = _to_int(
            await _safe_scalar(
                db,
                "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('PAUSED','STOPPED','INACTIVE')",
                {"user_id": user_id},
            )
        )

    return {
        "total_strategies": total,
        "my_strategies": my_strategies,
        "published_strategies": published,
        "deployed_strategies": deployed,
        "running_strategies": running,
        "paused_strategies": paused,
    }


async def _backtest_summary(db: AsyncSession, user_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not await _table_exists(db, "performance_metrics"):
        return {
            "total_backtests": 0,
            "completed_backtests": 0,
            "failed_backtests": 0,
            "best_return_pct": 0,
            "best_strategy_name": None,
            "last_backtest_at": None,
        }, []

    total = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM performance_metrics WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}))
    completed = _to_int(
        await _safe_scalar(
            db,
            "SELECT COUNT(*) FROM performance_metrics WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('COMPLETED','SUCCESS','DONE')",
            {"user_id": user_id},
        )
    )
    failed = _to_int(
        await _safe_scalar(
            db,
            "SELECT COUNT(*) FROM performance_metrics WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('FAILED','ERROR','CANCELLED')",
            {"user_id": user_id},
        )
    )
    best_rows = await _safe_rows(
        db,
        """
        SELECT pm.return_pct, pm.net_profit, pm.strategy_id, s.name AS strategy_name
        FROM performance_metrics pm
        LEFT JOIN strategies s ON CAST(s.id AS TEXT)=CAST(pm.strategy_id AS TEXT)
        WHERE CAST(pm.user_id AS TEXT)=:user_id
        ORDER BY COALESCE(pm.return_pct, 0) DESC, COALESCE(pm.net_profit, 0) DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    best = best_rows[0] if best_rows else {}
    last_at = await _safe_scalar(
        db,
        "SELECT MAX(created_at) FROM performance_metrics WHERE CAST(user_id AS TEXT)=:user_id",
        {"user_id": user_id},
        None,
    )
    recent = await _safe_rows(
        db,
        """
        SELECT pm.id, pm.strategy_id, s.name AS strategy_name, pm.instrument_id, pm.timeframe,
               pm.status, pm.return_pct, pm.net_profit, pm.total_trades, pm.created_at
        FROM performance_metrics pm
        LEFT JOIN strategies s ON CAST(s.id AS TEXT)=CAST(pm.strategy_id AS TEXT)
        WHERE CAST(pm.user_id AS TEXT)=:user_id
        ORDER BY pm.created_at DESC
        LIMIT 5
        """,
        {"user_id": user_id},
    )
    recent_backtests = [
        {
            "id": str(row.get("id")),
            "strategy_name": row.get("strategy_name") or row.get("strategy_id") or "Strategy",
            "timeframe": row.get("timeframe") or "-",
            "status": row.get("status") or "UNKNOWN",
            "return_pct": _to_float(row.get("return_pct")),
            "net_profit": _to_float(row.get("net_profit")),
            "total_trades": _to_int(row.get("total_trades")),
            "created_at": _iso(row.get("created_at")),
        }
        for row in recent
    ]
    return {
        "total_backtests": total,
        "completed_backtests": completed,
        "failed_backtests": failed,
        "best_return_pct": _to_float(best.get("return_pct")),
        "best_strategy_name": best.get("strategy_name") or best.get("strategy_id"),
        "last_backtest_at": _iso(last_at),
    }, recent_backtests


async def _live_summary(db: AsyncSession, user_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    has_deployments = await _table_exists(db, "strategy_deployments")
    has_positions = await _table_exists(db, "live_positions")
    has_orders = await _table_exists(db, "live_orders")
    has_signals = await _table_exists(db, "live_signals")

    total_dep = running = paused = 0
    live_sync = False
    approved_any = False
    approval_required = True
    if has_deployments:
        total_dep = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}))
        running = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('RUNNING','ACTIVE','STARTED','LIVE')", {"user_id": user_id}))
        paused = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,'')) IN ('PAUSED','STOPPED','INACTIVE')", {"user_id": user_id}))
        live_sync = bool(await _safe_scalar(db, "SELECT BOOL_OR(COALESCE(live_sync_enabled, false)) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}, False))
        approved_any = bool(await _safe_scalar(db, "SELECT BOOL_OR(COALESCE(live_approved, false)) FROM strategy_deployments WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}, False))
        approval_required = not approved_any

    open_positions = 0
    total_pnl = today_pnl = 0.0
    if has_positions:
        open_positions = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM live_positions WHERE CAST(user_id AS TEXT)=:user_id AND UPPER(COALESCE(status,''))='OPEN'", {"user_id": user_id}))
        total_pnl = _to_float(await _safe_scalar(db, "SELECT COALESCE(SUM(COALESCE(realized_pnl,0)+COALESCE(unrealized_pnl,0)),0) FROM live_positions WHERE CAST(user_id AS TEXT)=:user_id", {"user_id": user_id}))
        today_pnl = _to_float(await _safe_scalar(db, "SELECT COALESCE(SUM(COALESCE(realized_pnl,0)+COALESCE(unrealized_pnl,0)),0) FROM live_positions WHERE CAST(user_id AS TEXT)=:user_id AND COALESCE(updated_at, created_at)::date = CURRENT_DATE", {"user_id": user_id}))

    today_orders = 0
    recent_orders: list[dict[str, Any]] = []
    if has_orders:
        today_orders = _to_int(await _safe_scalar(db, "SELECT COUNT(*) FROM live_orders WHERE CAST(user_id AS TEXT)=:user_id AND created_at::date = CURRENT_DATE", {"user_id": user_id}))
        rows = await _safe_rows(db, """
            SELECT id, symbol, side, qty, executed_price, entry_price, status, created_at
            FROM live_orders
            WHERE CAST(user_id AS TEXT)=:user_id
            ORDER BY created_at DESC
            LIMIT 5
        """, {"user_id": user_id})
        recent_orders = [
            {
                "id": str(row.get("id")),
                "symbol": row.get("symbol") or "-",
                "side": row.get("side") or "-",
                "qty": _to_float(row.get("qty")),
                "price": _to_float(row.get("executed_price") or row.get("entry_price")),
                "status": row.get("status") or "UNKNOWN",
                "created_at": _iso(row.get("created_at")),
            }
            for row in rows
        ]

    recent_signals: list[dict[str, Any]] = []
    if has_signals:
        rows = await _safe_rows(db, """
            SELECT id, symbol, signal_type, side, price, confidence, status, reason, created_at
            FROM live_signals
            WHERE CAST(user_id AS TEXT)=:user_id
            ORDER BY created_at DESC
            LIMIT 5
        """, {"user_id": user_id})
        recent_signals = [
            {
                "id": str(row.get("id")),
                "symbol": row.get("symbol") or "-",
                "signal": row.get("side") or row.get("signal_type") or "-",
                "price": _to_float(row.get("price")),
                "confidence": _to_float(row.get("confidence")),
                "status": row.get("status") or "RECEIVED",
                "reason": row.get("reason"),
                "created_at": _iso(row.get("created_at")),
            }
            for row in rows
        ]

    return {
        "total_deployments": total_dep,
        "running_deployments": running,
        "paused_deployments": paused,
        "live_sync_enabled": live_sync,
        "approval_required": approval_required,
        "open_positions": open_positions,
        "today_orders": today_orders,
        "today_pnl": today_pnl,
        "total_pnl": total_pnl,
    }, recent_signals, recent_orders


async def _billing_summary(db: AsyncSession, user_id: str) -> dict[str, Any]:
    credit_balance = 0
    if await _table_exists(db, "user_credits"):
        credit_balance = _to_int(await _safe_scalar(db, "SELECT balance FROM user_credits WHERE CAST(user_id AS TEXT)=:user_id LIMIT 1", {"user_id": user_id}))

    active_subscription = False
    plan = None
    if await _table_exists(db, "user_subscriptions"):
        rows = await _safe_rows(
            db,
            """
            SELECT us.status, us.plan_code_snapshot, p.code AS plan_code
            FROM user_subscriptions us
            LEFT JOIN plans p ON p.id = us.plan_id
            WHERE CAST(us.user_id AS TEXT)=:user_id
              AND UPPER(COALESCE(us.status,'')) IN ('ACTIVE','TRIAL')
              AND us.end_at >= NOW()
            ORDER BY us.created_at DESC
            LIMIT 1
            """,
            {"user_id": user_id},
        )
        if rows:
            active_subscription = True
            plan = rows[0].get("plan_code_snapshot") or rows[0].get("plan_code")

    return {"credit_balance": credit_balance, "active_subscription": active_subscription, "subscription_plan": plan}


async def _recent_broker_logs(db: AsyncSession, user_id: str, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logs = []
    if await _table_exists(db, "live_trade_logs"):
        rows = await _safe_rows(db, """
            SELECT id, event_type, level, message, created_at
            FROM live_trade_logs
            WHERE CAST(user_id AS TEXT)=:user_id
            ORDER BY created_at DESC
            LIMIT 5
        """, {"user_id": user_id})
        logs = [
            {
                "id": str(row.get("id")),
                "event_type": row.get("event_type") or "LOG",
                "level": row.get("level") or "INFO",
                "message": row.get("message") or "-",
                "created_at": _iso(row.get("created_at")),
            }
            for row in rows
        ]
    if logs:
        return logs
    return [
        {
            "id": item.get("id"),
            "event_type": "BROKER_ACCOUNT",
            "level": item.get("status") or "UNKNOWN",
            "message": f"{item.get('broker_name')} - {item.get('account_label')}",
            "created_at": item.get("last_sync_at"),
        }
        for item in accounts[:3]
    ]


@router.get("/user-summary")
async def get_user_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated user dashboard summary with aggregate counts only."""
    user_id = str(current_user.get("user_id") or current_user.get("id"))

    portfolio, broker_accounts = await _broker_summary(db, user_id)
    strategies = await _strategy_summary(db, user_id)
    backtests, recent_backtests = await _backtest_summary(db, user_id)
    live_trading, recent_signals, recent_orders = await _live_summary(db, user_id)
    billing = await _billing_summary(db, user_id)
    recent_broker_logs = await _recent_broker_logs(db, user_id, broker_accounts)

    return success_response(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "portfolio": portfolio,
            "strategies": strategies,
            "backtests": backtests,
            "live_trading": live_trading,
            "billing": billing,
            "recent": {
                "recent_signals": recent_signals,
                "recent_backtests": recent_backtests,
                "recent_orders": recent_orders,
                "recent_broker_logs": recent_broker_logs,
            },
        }
    )
