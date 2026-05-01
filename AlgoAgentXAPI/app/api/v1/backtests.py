from __future__ import annotations

import json
import logging
from io import BytesIO
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from math import ceil
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import String, and_, cast, desc, func, or_, select, text, update
from sqlalchemy.orm import load_only
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db, get_user_entitlements
from ...db.compat import as_uuid_or_str
from ...db.models import (
    CreditTransaction,
    CreditTransactionType,
    EquityCurve,
    Instrument,
    JobStatus,
    MarketData,
    PerformanceMetric,
    PnLCalendar,
    Strategy,
    Trade,
)
from ...schemas.backtests import BacktestCostPreviewRequest, BacktestRunRequest
from ...services.backtest_service import BacktestService
from ...services.credits.management import CreditManagementService
from ...services.metrics import MetricsCalculator
from ...services.notification_service import NotificationService
from ...services.pricing.backtest_pricing_service import BacktestPricingService
from ...utils.api_response import success_response

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _decimal(value, fallback: Decimal = Decimal("0")) -> Decimal:
    try:
        if value is None:
            return fallback
        return Decimal(str(value))
    except Exception:
        return fallback


def _as_uuid(value: str) -> UUID:
    return UUID(str(value))


def _parse_date_param(value, field_name: str = "date") -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise HTTPException(status_code=422, detail=f"Invalid {field_name}. Use yyyy-mm-dd or dd-mm-yyyy.")


def _ensure_aware_datetime(value):
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime()


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else ""
        if dialect == "sqlite":
            result = await db.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = :name"),
                {"name": table_name},
            )
            return result.scalar() is not None

        result = await db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        )
        return result.scalar() is not None
    except Exception:
        return False




async def _column_exists(db: AsyncSession, table_name: str, column_name: str) -> bool:
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else ""
        if dialect == "sqlite":
            result = await db.execute(text(f"PRAGMA table_info({table_name})"))
            return any(row[1] == column_name for row in result.fetchall())

        result = await db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
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
async def _column_udt_name(db: AsyncSession, table_name: str, column_name: str) -> str | None:
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else ""
        if dialect == "sqlite":
            result = await db.execute(text(f"PRAGMA table_info({table_name})"))
            for row in result.fetchall():
                if row[1] == column_name:
                    return str(row[2]).lower()
            return None

        result = await db.execute(
            text(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                  AND column_name = :column_name
                LIMIT 1
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        )
        value = result.scalar()
        return str(value).lower() if value else None
    except Exception:
        return None


async def _table_columns_meta(db: AsyncSession, table_name: str) -> list[dict[str, str]]:
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "sqlite":
        result = await db.execute(text(f"PRAGMA table_info({table_name})"))
        rows = []
        for row in result.fetchall():
            rows.append({
                "column_name": row[1],
                "is_nullable": "NO" if row[3] else "YES",
                "data_type": str(row[2]).lower(),
                "udt_name": str(row[2]).lower(),
                "column_default": row[4],
            })
        return rows

    result = await db.execute(
        text(
            """
            SELECT
                column_name,
                is_nullable,
                data_type,
                udt_name,
                column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
            ORDER BY ordinal_position
            """
        ),
        {"table_name": table_name},
    )
    return [dict(row._mapping) for row in result]


def _default_perf_metric_value(
    column_name: str,
    payload: BacktestRunRequest,
    service_response,
    metrics: dict,
    winning_trades: int,
    losing_trades: int,
    total_trades: int,
):
    final_capital = _to_float(service_response.final_capital, 0.0)
    initial_capital = _to_float(payload.capital, 0.0)
    net_profit = _to_float(metrics.get("net_profit"), 0.0)
    trade_pnls = [_to_float(getattr(trade, "pnl", 0.0), 0.0) for trade in (service_response.result.trades or [])]
    wins = [p for p in trade_pnls if p > 0]
    losses = [abs(p) for p in trade_pnls if p < 0]
    return_pct = ((final_capital - initial_capital) / initial_capital * 100.0) if initial_capital else 0.0
    expectancy = (net_profit / total_trades) if total_trades else 0.0

    special_values = {
        "id": None,
        "user_id": as_uuid_or_str(payload.user_id) if hasattr(payload, "user_id") else None,
        "period": f"{payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
        "strategy_id": payload.strategy_id,
        "instrument_id": payload.instrument_id,
        "timeframe": payload.timeframe,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "initial_capital": _decimal(initial_capital),
        "final_capital": _decimal(final_capital),
        "net_profit": _decimal(net_profit),
        "max_drawdown": _decimal(metrics.get("max_drawdown", 0.0)),
        "sharpe_ratio": _decimal(metrics.get("sharpe_ratio", 0.0)),
        "sortino_ratio": _decimal(metrics.get("sortino_ratio", 0.0)),
        "calmar_ratio": _decimal(metrics.get("calmar_ratio", 0.0)),
        "win_rate": _decimal(metrics.get("win_rate", 0.0)),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "profit_factor": _decimal(metrics.get("profit_factor", 0.0)),
        "avg_win": _decimal((sum(wins) / len(wins)) if wins else 0.0),
        "avg_loss": _decimal((sum(losses) / len(losses)) if losses else 0.0),
        "expectancy": _decimal(expectancy),
        "return_pct": _decimal(return_pct),
        "status": "completed",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    return special_values.get(column_name)


async def _resolve_backtest_fk_value(db: AsyncSession, table_name: str, backtest_id: str):
    udt_name = await _column_udt_name(db, table_name, "backtest_id")
    if udt_name in {"uuid"}:
        return _as_uuid(backtest_id)
    return backtest_id


def _trade_df_from_service(service_response) -> pd.DataFrame:
    if not service_response.result.trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "pnl"])
    return pd.DataFrame(
        [
            {
                "entry_time": trade.entry_datetime,
                "exit_time": trade.exit_datetime,
                "pnl": _to_float(trade.pnl),
            }
            for trade in service_response.result.trades
        ]
    )


def _equity_df_from_service(service_response, start_date: date) -> pd.DataFrame:
    if not service_response.result.equity_curve:
        return pd.DataFrame(columns=["timestamp", "equity"])

    base = datetime.combine(start_date, time(0, 0, 0))
    rows = []
    for i, value in enumerate(service_response.result.equity_curve):
        rows.append({"timestamp": base + timedelta(minutes=i), "equity": _to_float(value)})
    return pd.DataFrame(rows)


async def _quote_backtest_cost(
    db: AsyncSession,
    plan_code: str | None,
    strategy_id: str | None,
    instrument_id: int | None,
    timeframe: str,
    start_date: date,
    end_date: date,
    use_actual_candle_count: bool,
) -> dict:
    strategy_parameters = None
    if strategy_id:
        strategy = await db.get(Strategy, strategy_id)
        if strategy and isinstance(strategy.parameters, dict):
            strategy_parameters = strategy.parameters

    return await BacktestPricingService.quote_backtest_cost(
        db,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        instrument_id=instrument_id,
        strategy_parameters=strategy_parameters,
        use_actual_candle_count=use_actual_candle_count,
        plan_code=plan_code,
    )



async def _get_market_data_availability_guard(
    db: AsyncSession,
    instrument_id: int,
    timeframe: str,
    start_date: date,
    end_date: date,
) -> dict:
    requested_start = datetime.combine(start_date, time.min)
    requested_end = datetime.combine(end_date, time.max)

    instrument = await db.get(Instrument, instrument_id)
    symbol = str(getattr(instrument, "symbol", "") or "").upper()
    market = str(getattr(instrument, "market", "") or "").upper()
    is_forex_like = market == "FOREX" or any(token in symbol for token in ["XAU", "XAG", "EUR", "GBP", "JPY", "USD"])
    boundary_tolerance_days = 3 if is_forex_like else 1

    overall = (
        await db.execute(
            select(
                func.min(MarketData.timestamp).label("available_start"),
                func.max(MarketData.timestamp).label("available_end"),
                func.count().label("total_count"),
            ).where(
                MarketData.instrument_id == instrument_id,
                MarketData.timeframe == timeframe,
            )
        )
    ).first()

    ranged = (
        await db.execute(
            select(
                func.min(MarketData.timestamp).label("range_start"),
                func.max(MarketData.timestamp).label("range_end"),
                func.count().label("record_count"),
            ).where(
                MarketData.instrument_id == instrument_id,
                MarketData.timeframe == timeframe,
                MarketData.timestamp >= requested_start,
                MarketData.timestamp <= requested_end,
            )
        )
    ).first()

    available_start = getattr(overall, "available_start", None) if overall else None
    available_end = getattr(overall, "available_end", None) if overall else None
    total_count = int(getattr(overall, "total_count", 0) or 0) if overall else 0
    range_start = getattr(ranged, "range_start", None) if ranged else None
    range_end = getattr(ranged, "range_end", None) if ranged else None
    record_count = int(getattr(ranged, "record_count", 0) or 0) if ranged else 0

    range_start_date = range_start.date() if range_start else None
    range_end_date = range_end.date() if range_end else None
    dataset_start_date = available_start.date() if available_start else None
    dataset_end_date = available_end.date() if available_end else None

    missing_before = False
    missing_after = False
    if record_count > 0 and range_start_date:
        missing_before = (range_start_date - start_date).days > boundary_tolerance_days
    elif dataset_start_date:
        missing_before = (dataset_start_date - start_date).days > boundary_tolerance_days

    if record_count > 0 and range_end_date:
        missing_after = (end_date - range_end_date).days > boundary_tolerance_days
    elif dataset_end_date:
        missing_after = (end_date - dataset_end_date).days > boundary_tolerance_days

    dataset_missing = total_count <= 0 or available_start is None or available_end is None
    blocked = dataset_missing or record_count <= 0 or missing_before or missing_after

    if dataset_missing:
        message = "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles."
        status_value = "error"
    elif record_count <= 0:
        message = "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles."
        status_value = "error"
    elif blocked:
        message = "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles."
        status_value = "error"
    else:
        message = "Market data available for selected range."
        status_value = "ok"

    return {
        "status": status_value,
        "available": not blocked,
        "blocked": blocked,
        "message": message,
        "instrument_id": instrument_id,
        "timeframe": timeframe,
        "requested_start": requested_start,
        "requested_end": requested_end,
        "requested_start_iso": requested_start.isoformat(),
        "requested_end_iso": requested_end.isoformat(),
        "available_start": range_start,
        "available_end": range_end,
        "available_start_iso": range_start.isoformat() if range_start else None,
        "available_end_iso": range_end.isoformat() if range_end else None,
        "dataset_start_iso": available_start.isoformat() if available_start else None,
        "dataset_end_iso": available_end.isoformat() if available_end else None,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "record_count": record_count,
        "total_count": total_count,
        "boundary_tolerance_days": boundary_tolerance_days,
        "is_forex_like": is_forex_like,
    }


def _raise_market_data_unavailable(availability: dict) -> None:
    raise HTTPException(
        status_code=400,
        detail={
            "code": "MARKET_DATA_UNAVAILABLE",
            "message": availability.get("message") or (
                "Market data is missing for this instrument/timeframe/date range. "
                "Ask admin to import missing candles."
            ),
            "available_start": availability.get("available_start_iso"),
            "available_end": availability.get("available_end_iso"),
            "dataset_start": availability.get("dataset_start_iso"),
            "dataset_end": availability.get("dataset_end_iso"),
            "requested_start": availability.get("requested_start_iso"),
            "requested_end": availability.get("requested_end_iso"),
            "missing_before": bool(availability.get("missing_before")),
            "missing_after": bool(availability.get("missing_after")),
            "record_count": int(availability.get("record_count") or 0),
            "action": "Ask admin to import missing candles for this instrument/timeframe/date range.",
        },
    )


async def _get_backtest_debit_map(db: AsyncSession, backtest_ids: list[str]) -> dict[str, dict]:
    if not backtest_ids:
        return {}

    rows = (
        await db.execute(
            select(
                CreditTransaction.backtest_id,
                CreditTransaction.id,
                CreditTransaction.amount,
                CreditTransaction.transaction_type,
                CreditTransaction.source,
            )
            .where(CreditTransaction.backtest_id.in_(backtest_ids))
            .order_by(CreditTransaction.created_at.desc())
        )
    ).all()

    debit_map: dict[str, dict] = {}
    for backtest_id, txn_id, amount, transaction_type, source in rows:
        key = str(backtest_id)
        if key not in debit_map:
            debit_map[key] = {
                "debit_transaction_id": None,
                "credit_cost": 0.0,
                "included_debited": 0.0,
                "wallet_debited": 0.0,
                "included_refunded": 0.0,
                "wallet_refunded": 0.0,
                "effective_credit_cost": 0.0,
            }

        tx_type = transaction_type.name if hasattr(transaction_type, "name") else str(transaction_type).upper()
        tx_source = str(source or "").lower()
        tx_amount = _to_float(amount)

        if tx_type == CreditTransactionType.DEBIT.name:
            if debit_map[key]["debit_transaction_id"] is None:
                debit_map[key]["debit_transaction_id"] = str(txn_id)

            debit_map[key]["credit_cost"] += tx_amount
            if tx_source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_DEBIT:
                debit_map[key]["included_debited"] += tx_amount
            else:
                debit_map[key]["wallet_debited"] += tx_amount

        if tx_type == CreditTransactionType.REFUND.name:
            if tx_source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_REFUND:
                debit_map[key]["included_refunded"] += tx_amount
            else:
                debit_map[key]["wallet_refunded"] += tx_amount

    for key in debit_map.keys():
        debit_total = float(debit_map[key]["credit_cost"])
        refund_total = float(debit_map[key]["included_refunded"] + debit_map[key]["wallet_refunded"])
        debit_map[key]["effective_credit_cost"] = max(debit_total - refund_total, 0.0)

    return debit_map


async def _serialize_summary(
    db: AsyncSession,
    row: PerformanceMetric,
    strategy_name: str | None = None,
    instrument_symbol: str | None = None,
    credit_cost: float | None = None,
    debit_transaction_id: str | None = None,
) -> dict:
    if strategy_name is None and row.strategy_id:
        strategy_name = (
            await db.execute(select(Strategy.name).where(Strategy.id == row.strategy_id))
        ).scalar_one_or_none()
    if instrument_symbol is None and row.instrument_id:
        instrument_symbol = (
            await db.execute(select(Instrument.symbol).where(Instrument.id == row.instrument_id))
        ).scalar_one_or_none()

    return {
        "id": str(row.id),
        "strategy_id": row.strategy_id,
        "strategy_name": strategy_name,
        "instrument_id": row.instrument_id,
        "instrument_symbol": instrument_symbol,
        "timeframe": row.timeframe,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "initial_capital": _to_float(row.initial_capital),
        "final_capital": _to_float(row.final_capital),
        "net_profit": _to_float(row.net_profit),
        "max_drawdown": _to_float(row.max_drawdown),
        "sharpe_ratio": _to_float(row.sharpe_ratio),
        "win_rate": _to_float(row.win_rate),
        "total_trades": _to_int(row.total_trades),
        "winning_trades": _to_int(getattr(row, "winning_trades", 0)),
        "losing_trades": _to_int(getattr(row, "losing_trades", 0)),
        "profit_factor": _to_float(getattr(row, "profit_factor", None)),
        "credit_cost": credit_cost,
        "effective_credit_cost": credit_cost,
        "debit_transaction_id": debit_transaction_id,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": (row.__dict__.get("updated_at").isoformat() if row.__dict__.get("updated_at") else None),
        "return_pct": _to_float(getattr(row, "return_pct", None), None),
        "avg_win": _to_float(getattr(row, "avg_win", None), None),
        "avg_loss": _to_float(getattr(row, "avg_loss", None), None),
        "expectancy": _to_float(getattr(row, "expectancy", None), None),
    }


async def _save_backtest_payload(
    db: AsyncSession,
    *,
    user_id: str,
    payload: BacktestRunRequest,
    service_response,
    metrics: dict,
) -> str:
    backtest_uuid = uuid4()
    backtest_id = str(backtest_uuid)

    win_rate = Decimal(str(metrics.get("win_rate", 0.0)))
    total_trades = int(service_response.total_trades or 0)
    winning_trades = int(round(total_trades * float(win_rate))) if total_trades > 0 else 0
    losing_trades = max(total_trades - winning_trades, 0)

    insert_values = {
        "id": backtest_id,
        "user_id": as_uuid_or_str(user_id),
        "strategy_id": payload.strategy_id,
        "instrument_id": payload.instrument_id,
        "timeframe": payload.timeframe,
        "period": f"{payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "initial_capital": _decimal(payload.capital),
        "final_capital": _decimal(service_response.final_capital),
        "net_profit": _decimal(metrics.get("net_profit")),
        "max_drawdown": _decimal(metrics.get("max_drawdown")),
        "sharpe_ratio": _decimal(metrics.get("sharpe_ratio")),
        "win_rate": win_rate,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "profit_factor": _decimal(metrics.get("profit_factor")),
        "return_pct": _decimal(metrics.get("return_pct")),
        "avg_win": _decimal(metrics.get("avg_win")),
        "avg_loss": _decimal(metrics.get("avg_loss")),
        "expectancy": _decimal(metrics.get("expectancy")),
        "status": "completed",
    }

    column_meta = await _table_columns_meta(db, "performance_metrics")
    available_columns = [meta["column_name"] for meta in column_meta]
    missing_columns = sorted(set(insert_values.keys()) - set(available_columns))
    if missing_columns:
        logger.warning(
            "performance_metrics is missing columns %s; persisting compatible subset only",
            ", ".join(missing_columns),
        )

    if not available_columns:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DB_MIGRATION_REQUIRED",
                "message": "performance_metrics table is missing required backtest columns. Run scripts/backtest_performance_metrics_safe_migration.sql and retry.",
                "migration": "scripts/backtest_performance_metrics_safe_migration.sql",
            },
        )

    final_insert_values = {column: insert_values[column] for column in available_columns if column in insert_values}
    class _PayloadShim:
        pass
    payload_shim = _PayloadShim()
    payload_shim.user_id = user_id
    payload_shim.strategy_id = payload.strategy_id
    payload_shim.instrument_id = payload.instrument_id
    payload_shim.timeframe = payload.timeframe
    payload_shim.start_date = payload.start_date
    payload_shim.end_date = payload.end_date
    payload_shim.capital = payload.capital

    for meta in column_meta:
        column = meta["column_name"]
        if column in final_insert_values:
            continue
        if str(meta.get("is_nullable", "YES")).upper() == "NO" and not meta.get("column_default"):
            fallback = _default_perf_metric_value(
                column,
                payload_shim,
                service_response,
                metrics,
                winning_trades,
                losing_trades,
                total_trades,
            )
            if fallback is None:
                data_type = str(meta.get("data_type") or meta.get("udt_name") or "").lower()
                if any(token in data_type for token in ["int", "numeric", "double", "real", "decimal"]):
                    fallback = 0
                elif data_type == "date":
                    fallback = payload.start_date
                elif "time" in data_type:
                    fallback = datetime.utcnow()
                elif meta.get("udt_name") == "uuid":
                    fallback = None
                else:
                    fallback = ""
            if fallback is not None:
                final_insert_values[column] = fallback

    columns_sql = ", ".join(final_insert_values.keys())
    values_sql = ", ".join(f":{column}" for column in final_insert_values.keys())
    await db.execute(
        text(f"INSERT INTO performance_metrics ({columns_sql}) VALUES ({values_sql})"),
        final_insert_values,
    )
    await db.flush()

    trades_fk_value = await _resolve_backtest_fk_value(db, "trades", backtest_id)
    equity_fk_value = await _resolve_backtest_fk_value(db, "equity_curve", backtest_id)
    pnl_fk_value = await _resolve_backtest_fk_value(db, "pnl_calendar", backtest_id)

    if await _table_exists(db, "metrics"):
        try:
            async with db.begin_nested():
                for metric_name in ["net_profit", "win_rate", "max_drawdown", "sharpe_ratio", "profit_factor"]:
                    await db.execute(
                        text(
                            """
                            INSERT INTO metrics (id, backtest_id, name, value)
                            VALUES (:id, :backtest_id, :name, :value)
                            """
                        ),
                        {
                            "id": str(uuid4()),
                            "backtest_id": backtest_id,
                            "name": metric_name,
                            "value": _to_float(metrics.get(metric_name)),
                        },
                    )
        except Exception as exc:
            logger.warning("Failed to persist metrics rows for backtest %s: %s", backtest_id, exc)

    if service_response.result.trades:
        try:
            async with db.begin_nested():
                for trade in service_response.result.trades:
                    db.add(
                        Trade(
                            id=int(uuid4().int % 9_000_000_000_000_000_000),
                            backtest_id=trades_fk_value,
                            instrument_id=payload.instrument_id,
                            entry_time=_ensure_aware_datetime(trade.entry_datetime),
                            exit_time=_ensure_aware_datetime(trade.exit_datetime),
                            side=trade.direction,
                            quantity=int(_to_float(trade.quantity, 0.0)),
                            entry_price=_decimal(trade.entry_price),
                            exit_price=_decimal(trade.exit_price),
                            pnl=_decimal(trade.pnl),
                            exit_type=trade.exit_reason,
                        )
                    )
        except Exception as exc:
            logger.warning("Failed to persist trades for backtest %s: %s", backtest_id, exc)

    if service_response.result.equity_curve:
        try:
            async with db.begin_nested():
                base = datetime.combine(payload.start_date, time(0, 0, 0))
                for idx, equity in enumerate(service_response.result.equity_curve):
                    db.add(
                        EquityCurve(
                            backtest_id=equity_fk_value,
                            timestamp=_ensure_aware_datetime(base + timedelta(minutes=idx)),
                            equity=_decimal(equity),
                        )
                    )
        except Exception as exc:
            logger.warning("Failed to persist equity curve for backtest %s: %s", backtest_id, exc)

    if service_response.result.trades:
        try:
            pnl_map: dict[date, Decimal] = {}
            for trade in service_response.result.trades:
                if not trade.exit_datetime:
                    continue
                day = trade.exit_datetime.date()
                pnl_map[day] = pnl_map.get(day, Decimal("0")) + _decimal(trade.pnl)

            if pnl_map:
                async with db.begin_nested():
                    for day, pnl in pnl_map.items():
                        db.add(PnLCalendar(backtest_id=pnl_fk_value, date=day, pnl=pnl))
        except Exception as exc:
            logger.warning("Failed to persist pnl calendar for backtest %s: %s", backtest_id, exc)

    return backtest_id


def _build_detail_export_frames(detail: dict):
    summary = detail.get("summary", {}) if isinstance(detail, dict) else {}
    metrics_rows = [
        ["Backtest ID", summary.get("id")],
        ["Strategy", summary.get("strategy_name")],
        ["Instrument", summary.get("instrument_symbol")],
        ["Timeframe", summary.get("timeframe")],
        ["Initial Capital", summary.get("initial_capital")],
        ["Final Capital", summary.get("final_capital")],
        ["Net Profit", summary.get("net_profit")],
        ["Return %", summary.get("return_pct")],
        ["Win Rate", summary.get("win_rate")],
        ["Sharpe Ratio", summary.get("sharpe_ratio")],
        ["Max Drawdown", summary.get("max_drawdown")],
        ["Profit Factor", summary.get("profit_factor")],
        ["Avg Win", summary.get("avg_win")],
        ["Avg Loss", summary.get("avg_loss")],
        ["Expectancy", summary.get("expectancy")],
        ["Total Trades", summary.get("total_trades")],
        ["Winning Trades", summary.get("winning_trades")],
        ["Losing Trades", summary.get("losing_trades")],
        ["Created At", summary.get("created_at")],
    ]
    metrics_df = pd.DataFrame(metrics_rows, columns=["Metric", "Value"])
    trades_df = pd.DataFrame(detail.get("trades", []))
    equity_df = pd.DataFrame(detail.get("equity_curve", []))
    pnl_df = pd.DataFrame(detail.get("pnl_calendar", []))
    return metrics_df, trades_df, equity_df, pnl_df


async def _detail_payload_for_export(backtest_id: str, db: AsyncSession, current_user: dict) -> dict:
    response = await get_backtest_detail(backtest_id=backtest_id, db=db, current_user=current_user)
    payload = response.get("data") if isinstance(response, dict) and "data" in response else response
    return payload


def _autosize_excel_sheet(ws):
    header_fill = PatternFill(fill_type="solid", fgColor="2F1B57")
    header_font = Font(color="FFFFFF", bold=True)
    for row in ws.iter_rows(min_row=1, max_row=1):
        for cell in row:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
    for column_cells in ws.columns:
        values = ["" if cell.value is None else str(cell.value) for cell in column_cells]
        width = min(max(len(v) for v in values) + 2, 42) if values else 12
        ws.column_dimensions[get_column_letter(column_cells[0].column)].width = max(width, 12)


def _build_trade_analysis_frames(detail: dict):
    trades = detail.get("trades", []) if isinstance(detail, dict) else []
    if not trades:
        empty = pd.DataFrame(columns=["label", "value"])
        return empty, empty, empty

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df["entry_time"] = pd.to_datetime(trades_df.get("entry_time"), errors="coerce")
        trades_df["exit_time"] = pd.to_datetime(trades_df.get("exit_time"), errors="coerce")
        trades_df["pnl"] = pd.to_numeric(trades_df.get("pnl"), errors="coerce").fillna(0.0)
        trades_df["quantity"] = pd.to_numeric(trades_df.get("quantity"), errors="coerce").fillna(0)
        trades_df["duration_minutes"] = ((trades_df["exit_time"] - trades_df["entry_time"]).dt.total_seconds() / 60.0).fillna(0.0)

    side_breakdown = (
        trades_df.groupby("side", dropna=False)
        .agg(trades=("id", "count"), total_pnl=("pnl", "sum"), avg_pnl=("pnl", "mean"))
        .reset_index()
    ) if not trades_df.empty else pd.DataFrame(columns=["side", "trades", "total_pnl", "avg_pnl"])

    daily_trades = pd.DataFrame(columns=["date", "trade_count", "daily_pnl"])
    if not trades_df.empty and "exit_time" in trades_df.columns:
        temp = trades_df.copy()
        temp["date"] = temp["exit_time"].dt.date
        daily_trades = temp.groupby("date").agg(trade_count=("id", "count"), daily_pnl=("pnl", "sum")).reset_index()

    highlights = pd.DataFrame([
        ["Largest Win", float(trades_df["pnl"].max()) if not trades_df.empty else 0.0],
        ["Largest Loss", float(trades_df["pnl"].min()) if not trades_df.empty else 0.0],
        ["Average Duration (min)", float(trades_df["duration_minutes"].mean()) if not trades_df.empty else 0.0],
        ["Median Duration (min)", float(trades_df["duration_minutes"].median()) if not trades_df.empty else 0.0],
        ["Average Position Size", float(trades_df["quantity"].mean()) if not trades_df.empty else 0.0],
    ], columns=["Metric", "Value"])

    return side_breakdown, daily_trades, highlights


@router.get("/{backtest_id}/export/excel")
async def export_backtest_excel(backtest_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    detail = await _detail_payload_for_export(backtest_id, db, current_user)
    metrics_df, trades_df, equity_df, pnl_df = _build_detail_export_frames(detail)
    side_df, daily_trades_df, highlights_df = _build_trade_analysis_frames(detail)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        metrics_df.to_excel(writer, sheet_name="Summary", index=False)
        highlights_df.to_excel(writer, sheet_name="Highlights", index=False)
        trades_df.to_excel(writer, sheet_name="Trades", index=False)
        side_df.to_excel(writer, sheet_name="Trade Breakdown", index=False)
        daily_trades_df.to_excel(writer, sheet_name="Daily Trades", index=False)
        equity_df.to_excel(writer, sheet_name="Equity Curve", index=False)
        pnl_df.to_excel(writer, sheet_name="PnL Calendar", index=False)
    output.seek(0)
    workbook = load_workbook(output)
    for sheet in workbook.worksheets:
        _autosize_excel_sheet(sheet)
        sheet.freeze_panes = "A2"
    formatted = BytesIO()
    workbook.save(formatted)
    formatted.seek(0)
    filename = f"backtest-{backtest_id}-full-report.xlsx"
    return StreamingResponse(formatted, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{backtest_id}/export/pdf")
async def export_backtest_pdf(backtest_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    detail = await _detail_payload_for_export(backtest_id, db, current_user)
    summary = detail.get("summary", {})
    trades = detail.get("trades", [])
    pnl_calendar = detail.get("pnl_calendar", [])
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    def new_page(title: str | None = None):
        c.showPage()
        c.setFont("Helvetica-Bold", 15)
        c.drawString(15 * mm, height - 18 * mm, title or "AlgoAgentX Backtest Report")
        c.setFont("Helvetica", 9)
        return height - 28 * mm

    y = height - 18 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, y, "AlgoAgentX Backtest Report")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    fields = [
        ("Backtest ID", summary.get("id")),
        ("Strategy", summary.get("strategy_name")),
        ("Instrument", summary.get("instrument_symbol")),
        ("Timeframe", summary.get("timeframe")),
        ("Initial Capital", summary.get("initial_capital")),
        ("Final Capital", summary.get("final_capital")),
        ("Net Profit", summary.get("net_profit")),
        ("Return %", summary.get("return_pct")),
        ("Win Rate", summary.get("win_rate")),
        ("Sharpe", summary.get("sharpe_ratio")),
        ("Drawdown", summary.get("max_drawdown")),
        ("Profit Factor", summary.get("profit_factor")),
        ("Avg Win", summary.get("avg_win")),
        ("Avg Loss", summary.get("avg_loss")),
        ("Expectancy", summary.get("expectancy")),
        ("Trades", summary.get("total_trades")),
        ("Created At", summary.get("created_at")),
    ]
    for label, value in fields:
        c.drawString(15 * mm, y, f"{label}: {value}")
        y -= 6 * mm
        if y < 22 * mm:
            y = new_page("Backtest Report - Summary Continued")

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, "Trade List")
    y -= 7 * mm
    c.setFont("Helvetica", 8)
    if not trades:
        c.drawString(15 * mm, y, "No trades available for this run.")
        y -= 6 * mm
    else:
        for idx, trade in enumerate(trades, start=1):
            line = f"{idx}. {trade.get('entry_time')} | {trade.get('side')} | qty {trade.get('quantity')} | entry {trade.get('entry_price')} | exit {trade.get('exit_price')} | pnl {trade.get('pnl')} | {trade.get('exit_type')}"
            c.drawString(15 * mm, y, line[:145])
            y -= 5 * mm
            if y < 18 * mm:
                y = new_page("Backtest Report - Trades")

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, "PnL Calendar")
    y -= 7 * mm
    c.setFont("Helvetica", 8)
    for row in pnl_calendar[:120]:
        c.drawString(15 * mm, y, f"{row.get('date')}: {row.get('pnl')}")
        y -= 5 * mm
        if y < 18 * mm:
            y = new_page("Backtest Report - PnL Calendar")

    c.save()
    output.seek(0)
    filename = f"backtest-{backtest_id}-full-report.pdf"
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/config")
async def get_backtest_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements),
):
    user_id = current_user["user_id"]
    uid = as_uuid_or_str(user_id)

    strategies = (
        await db.execute(
            select(Strategy)
            .where(or_(Strategy.visibility == "PUBLIC", Strategy.created_by == uid))
            .order_by(Strategy.created_at.desc())
        )
    ).scalars().all()
    instruments = (await db.execute(select(Instrument).order_by(Instrument.symbol.asc()))).scalars().all()
    timeframes = (
        await db.execute(select(MarketData.timeframe).distinct().order_by(MarketData.timeframe.asc()))
    ).scalars().all()

    try:
        capacity = await CreditManagementService.get_credit_capacity(db, str(user_id), for_update=False)
    except Exception:
        capacity = {
            "wallet_balance": 0,
            "included_balance": 0,
            "total_available": 0,
            "subscription_state": "NONE",
            "subscription_id": None,
            "refill_applied": False,
            "next_refill_at": None,
        }

    return success_response(
        {
            "strategies": [{"id": str(s.id), "name": s.name} for s in strategies],
            "instruments": [
                {
                    "id": i.id,
                    "symbol": i.symbol,
                    "exchange": i.exchange,
                    "market": i.market,
                    "instrument_type": i.instrument_type,
                }
                for i in instruments
            ],
            "timeframes": [tf for tf in timeframes if tf],
            "credits": {
                "balance": _to_float(capacity.get("total_available") or 0),
                "current_balance": _to_float(capacity.get("total_available") or 0),
                "wallet_balance": _to_int(capacity.get("wallet_balance") or 0),
                "included": _to_int(capacity.get("included_balance") or 0),
                "included_balance": _to_int(capacity.get("included_balance") or 0),
                "total_available": _to_int(capacity.get("total_available") or 0),
                "subscription_state": capacity.get("subscription_state"),
                "next_refill_at": capacity.get("next_refill_at").isoformat() if capacity.get("next_refill_at") else None,
                "deduction_order": ["subscription", "wallet"],
            },
            "limits": {
                "max_backtests_per_day": _to_int(entitlements.get("features", {}).get("backtests_per_day", 5)),
                "max_date_range_days": _to_int(entitlements.get("features", {}).get("max_date_range_days", 30)),
            },
        }
    )


@router.get("/timeframes")
async def get_backtest_timeframes(
    instrument_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MarketData.timeframe).distinct().order_by(MarketData.timeframe.asc())
    if instrument_id is not None:
        stmt = stmt.where(MarketData.instrument_id == instrument_id)
    rows = (await db.execute(stmt)).scalars().all()
    return success_response({"timeframes": [tf for tf in rows if tf]})


@router.get("/data-availability")
async def get_data_availability(
    instrument_id: int,
    timeframe: str,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    parsed_start_date = _parse_date_param(start_date, "start_date")
    parsed_end_date = _parse_date_param(end_date, "end_date")

    summary = (
        await db.execute(
            select(
                func.min(MarketData.timestamp).label("min_ts"),
                func.max(MarketData.timestamp).label("max_ts"),
                func.count().label("count"),
            ).where(MarketData.instrument_id == instrument_id, MarketData.timeframe == timeframe)
        )
    ).first()

    if not summary or summary.min_ts is None:
        return success_response(
            {
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                "status": "error",
                "available": False,
                "coverage_status": "BLOCKED",
                "message": "Market data is missing for this instrument/timeframe/date range. Ask admin to import missing candles.",
                "candle_count": 0,
                "total_candles": 0,
                "matched_candles": 0,
                "min_timestamp": None,
                "max_timestamp": None,
                "requested_candle_count": 0,
            }
        )

    requested_count = None
    range_min = None
    range_max = None
    missing_before = False
    missing_after = False
    coverage_status = "AVAILABLE"
    message = "Market data available for selected range."

    if parsed_start_date and parsed_end_date:
        guard = await _get_market_data_availability_guard(db, instrument_id, timeframe, parsed_start_date, parsed_end_date)
        requested_count = guard["record_count"]
        range_min = guard.get("available_start")
        range_max = guard.get("available_end")
        missing_before = bool(guard.get("missing_before"))
        missing_after = bool(guard.get("missing_after"))
        coverage_status = "BLOCKED" if guard.get("blocked") else "AVAILABLE"
        message = str(guard.get("message") or message)

    return success_response(
        {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "status": "ok" if coverage_status == "AVAILABLE" else "error",
            "available": coverage_status == "AVAILABLE",
            "coverage_status": coverage_status,
            "message": message,
            "candle_count": _to_int(summary.count),
            "total_candles": _to_int(summary.count),
            "matched_candles": _to_int(requested_count, 0),
            "min_timestamp": summary.min_ts.isoformat() if summary.min_ts else None,
            "max_timestamp": summary.max_ts.isoformat() if summary.max_ts else None,
            "available_start": range_min.isoformat() if range_min else None,
            "available_end": range_max.isoformat() if range_max else None,
            "requested_start": datetime.combine(parsed_start_date, time.min).isoformat() if parsed_start_date else None,
            "requested_end": datetime.combine(parsed_end_date, time.max).isoformat() if parsed_end_date else None,
            "missing_before": missing_before,
            "missing_after": missing_after,
            "requested_candle_count": _to_int(requested_count, 0),
        }
    )


@router.post("/cost-preview")
async def preview_backtest_cost(
    payload: BacktestCostPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements),
):
    plan_code = str(entitlements.get("plan_code") or "").upper() if entitlements else None
    estimate = await _quote_backtest_cost(
        db,
        plan_code=plan_code,
        strategy_id=payload.strategy_id,
        instrument_id=payload.instrument_id,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
        use_actual_candle_count=False,
    )

    capacity = await CreditManagementService.get_credit_capacity(db, str(current_user["user_id"]), for_update=False)
    total_available = int(capacity.get("total_available") or 0)
    return success_response(
        {
            "total_cost": estimate["total_cost"],
            "breakdown": estimate["breakdown"],
            "pricing_rule_set": {
                "id": estimate.get("breakdown", {}).get("rule_set_id"),
                "name": estimate.get("breakdown", {}).get("rule_set_name"),
                "version": estimate.get("breakdown", {}).get("pricing_version"),
            },
            "current_balance": float(total_available),
            "wallet_balance": int(capacity.get("wallet_balance") or 0),
            "included_balance": int(capacity.get("included_balance") or 0),
            "balances": {
                "wallet_balance": int(capacity.get("wallet_balance") or 0),
                "included_balance": int(capacity.get("included_balance") or 0),
                "total_available": int(capacity.get("total_available") or 0),
            },
            "subscription_state": capacity.get("subscription_state"),
            "can_run": float(total_available) >= estimate["total_cost"],
        }
    )


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_backtest(
    payload: BacktestRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements),
):
    strategy = await db.get(Strategy, payload.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    instrument = await db.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    availability = await _get_market_data_availability_guard(
        db,
        instrument_id=payload.instrument_id,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    if availability.get("blocked"):
        _raise_market_data_unavailable(availability)

    plan_code = str(entitlements.get("plan_code") or "").upper() if entitlements else None
    estimate = await _quote_backtest_cost(
        db,
        plan_code=plan_code,
        strategy_id=payload.strategy_id,
        instrument_id=payload.instrument_id,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
        use_actual_candle_count=True,
    )
    cost = Decimal(str(estimate["total_cost"]))

    capacity = await CreditManagementService.get_credit_capacity(db, str(current_user["user_id"]), for_update=False)
    total_available = int(capacity.get("total_available") or 0)
    if total_available < _to_int(cost):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "INSUFFICIENT_CREDITS",
                "message": "Insufficient credits for backtest. Upgrade plan or top-up wallet credits to continue.",
                "needed": _to_int(cost),
                "balance": float(total_available),
                "wallet_balance": int(capacity.get("wallet_balance") or 0),
                "included_balance": int(capacity.get("included_balance") or 0),
                "subscription_state": capacity.get("subscription_state"),
                "action": {
                    "upgrade_url": "/pricing",
                    "topup_url": "/credits",
                },
            },
        )

    if not await _column_exists(db, "job_status", "debit_txn_id"):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DB_MIGRATION_REQUIRED",
                "message": "Database schema is missing job_status.debit_txn_id required for backtest credit tracking. Run scripts/backtest_job_status_credit_link_safe_migration.sql and retry.",
                "migration": "scripts/backtest_job_status_credit_link_safe_migration.sql",
            },
        )

    if not await _column_exists(db, "performance_metrics", "instrument_id"):
        logger.warning(
            "performance_metrics.instrument_id missing; history/detail pages will be limited until scripts/backtest_performance_metrics_safe_migration.sql is applied"
        )

    job_id = str(uuid4())
    job = JobStatus(
        id=job_id,
        user_id=as_uuid_or_str(current_user["user_id"]),
        job_type="backtest",
        status="running",
        progress=10,
        message="Running backtest",
        job_data=json.dumps(payload.model_dump(mode="json")),
        started_at=datetime.utcnow(),
    )
    db.add(job)
    await db.flush()

    debit_txn = None
    included_txn = None
    consumption = None
    try:
        consumption = await CreditManagementService.consume_credits_for_backtest(
            db=db,
            user_id=str(current_user["user_id"]),
            total_cost=cost,
            description=(
                f"Backtest run: {payload.timeframe} | {payload.start_date.isoformat()} to "
                f"{payload.end_date.isoformat()}"
            ),
            job_id=job_id,
            auto_commit=False,
        )

        included_txn = consumption.get("included_transaction")
        debit_txn = consumption.get("wallet_transaction")

        if debit_txn is not None:
            job.debit_txn_id = str(debit_txn.id)
        elif included_txn is not None:
            job.debit_txn_id = str(included_txn.id)
        job.progress = 40
        job.message = "Executing strategy"

        service_response = await BacktestService.run_backtest(
            db=db,
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.timeframe,
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_capital=payload.capital,
        )

        trade_df = _trade_df_from_service(service_response)
        equity_df = _equity_df_from_service(service_response, payload.start_date)
        metrics = MetricsCalculator.calculate_all_metrics(
            equity_curve=equity_df,
            trades=trade_df,
            initial_capital=_to_float(payload.capital),
        )

        backtest_id = await _save_backtest_payload(
            db,
            user_id=str(current_user["user_id"]),
            payload=payload,
            service_response=service_response,
            metrics=metrics,
        )

        for txn in [included_txn, debit_txn]:
            if txn is None:
                continue
            await db.execute(
                update(CreditTransaction)
                .where(CreditTransaction.id == txn.id)
                .values(backtest_id=backtest_id)
            )

        result_data = {
            "backtest_id": backtest_id,
            "strategy_name": service_response.strategy_name,
            "instrument_symbol": service_response.instrument_symbol,
            "timeframe": service_response.timeframe,
            "start_date": service_response.start_date.isoformat(),
            "end_date": service_response.end_date.isoformat(),
            "initial_capital": _to_float(service_response.initial_capital),
            "final_capital": _to_float(service_response.final_capital),
            "net_profit": _to_float(metrics.get("net_profit")),
            "max_drawdown": _to_float(metrics.get("max_drawdown")),
            "sharpe_ratio": _to_float(metrics.get("sharpe_ratio")),
            "win_rate": _to_float(metrics.get("win_rate")),
            "profit_factor": _to_float(metrics.get("profit_factor")),
            "return_pct": _to_float(metrics.get("return_pct")),
            "avg_win": _to_float(metrics.get("avg_win")),
            "avg_loss": _to_float(metrics.get("avg_loss")),
            "expectancy": _to_float(metrics.get("expectancy")),
            "total_trades": _to_int(service_response.total_trades),
            "credit_cost": _to_float(cost),
            "included_credits_used": int((consumption or {}).get("effective_included_debited") or 0),
            "wallet_credits_used": int((consumption or {}).get("effective_wallet_debited") or 0),
            "charge_idempotent": bool((consumption or {}).get("idempotent", False)),
            "included_debit_transaction_id": str(included_txn.id) if included_txn is not None else None,
            "debit_transaction_id": str(debit_txn.id) if debit_txn is not None else None,
            "pricing": estimate.get("breakdown", {}),
            "saved": True,
        }

        job.status = "completed"
        job.progress = 100
        job.message = "Backtest completed"
        job.result_data = json.dumps(result_data)
        job.completed_at = datetime.utcnow()
        await db.commit()

        try:
            await NotificationService.create_notification(
                db,
                user_id=str(current_user["user_id"]),
                title="Backtest completed",
                message=f"{service_response.strategy_name} backtest completed on {service_response.instrument_symbol} ({service_response.timeframe}).",
                notification_type="BACKTEST_COMPLETED",
                severity="success",
                entity_type="backtest",
                entity_id=str(backtest_id),
                action_url=f"/backtest-history?backtestId={backtest_id}",
                metadata={"job_id": str(job_id), "net_profit": _to_float(metrics.get("net_profit")), "total_trades": _to_int(service_response.total_trades)},
                auto_commit=True,
            )
        except Exception:
            await db.rollback()
            logger.exception("Failed to create backtest completion notification for %s", backtest_id)

        return success_response(
            {
                "job_id": job_id,
                "status": "completed",
                "backtest_id": backtest_id,
                "result": result_data,
                "credits": {
                    "debited": _to_int(cost),
                    "included_debited": int((consumption or {}).get("effective_included_debited") or 0),
                    "wallet_debited": int((consumption or {}).get("effective_wallet_debited") or 0),
                    "charge_idempotent": bool((consumption or {}).get("idempotent", False)),
                    "included_debit_transaction_id": str(included_txn.id) if included_txn is not None else None,
                    "wallet_debit_transaction_id": str(debit_txn.id) if debit_txn is not None else None,
                    "balance_after": float((consumption or {}).get("wallet_balance_after") or 0),
                    "included_balance_after": int((consumption or {}).get("included_balance_after") or 0),
                    "total_balance_after": float(
                        int((consumption or {}).get("wallet_balance_after") or 0)
                        + int((consumption or {}).get("included_balance_after") or 0)
                    ),
                    "subscription_state": (consumption or {}).get("subscription_state"),
                    "deduction_order": ["subscription", "wallet"],
                },
            },
            "Backtest completed successfully",
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=402,
            detail={
                "code": "INSUFFICIENT_CREDITS",
                "message": str(exc) or "Insufficient credits for backtest. Upgrade plan or top-up wallet credits.",
                "needed": _to_int(cost),
                "balance": float((await CreditManagementService.get_credit_capacity(db, str(current_user["user_id"]), for_update=False)).get("total_available") or 0),
                "action": {
                    "upgrade_url": "/pricing",
                    "topup_url": "/credits",
                },
            },
        )
    except Exception as exc:
        logger.exception("Backtest run failed for user %s", current_user["user_id"])
        rollback_ok = True
        try:
            await db.rollback()
        except Exception:
            rollback_ok = False
            logger.exception("Rollback failed after backtest error for job %s", job_id)

        if consumption is not None and not rollback_ok:
            try:
                refund_result = await CreditManagementService.restore_consumed_credits(
                    db=db,
                    user_id=str(current_user["user_id"]),
                    included_amount=0,
                    wallet_amount=0,
                    description=f"Refund for failed backtest job {job_id}",
                    job_id=job_id,
                    auto_commit=False,
                )
                logger.info(
                    "Refunded failed backtest credits for job %s (included=%s, wallet=%s)",
                    job_id,
                    int((refund_result or {}).get("included_refunded") or 0),
                    int((refund_result or {}).get("wallet_refunded") or 0),
                )
            except Exception as refund_exc:
                logger.error("Failed to refund credits for job %s: %s", job_id, refund_exc)

        try:
            await db.execute(
                update(JobStatus)
                .where(JobStatus.id == job_id)
                .values(
                    status="failed",
                    progress=0,
                    message=str(exc),
                    completed_at=datetime.utcnow(),
                )
            )
            await db.commit()
            try:
                await NotificationService.create_notification(
                    db,
                    user_id=str(current_user["user_id"]),
                    title="Backtest failed",
                    message="Your backtest could not be completed. Please review the error and try again.",
                    notification_type="BACKTEST_FAILED",
                    severity="error",
                    entity_type="backtest_job",
                    entity_id=str(job_id),
                    action_url="/backtest",
                    metadata={"job_id": str(job_id), "error": str(exc)},
                    auto_commit=True,
                )
            except Exception:
                await db.rollback()
                logger.exception("Failed to create backtest failure notification for job %s", job_id)
        except Exception:
            await db.rollback()
            logger.exception("Failed to persist failed job status for job %s", job_id)

        detail = str(exc)
        if "performance_metrics" in detail:
            detail = (
                "Backtest execution failed because performance_metrics schema is outdated or has legacy NOT NULL columns. "
                "Run scripts/backtest_performance_metrics_safe_migration.sql and retry."
            )
        raise HTTPException(status_code=500, detail=detail)


@router.get("/")
async def get_backtests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await get_backtest_history(page=page, page_size=page_size, db=db, current_user=current_user)


@router.get("/history")
async def get_backtest_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    strategy_id: str | None = Query(default=None),
    instrument_id: int | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    start_date_from: date | None = Query(default=None),
    start_date_to: date | None = Query(default=None),
    min_profit: float | None = Query(default=None),
    max_drawdown: float | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = str(current_user["user_id"])
    filters = [cast(PerformanceMetric.user_id, String) == uid]
    if strategy_id:
        filters.append(PerformanceMetric.strategy_id == strategy_id)
    if instrument_id is not None:
        filters.append(PerformanceMetric.instrument_id == instrument_id)
    if timeframe:
        filters.append(PerformanceMetric.timeframe == timeframe)
    if status_filter:
        filters.append(func.lower(PerformanceMetric.status) == status_filter.lower())
    if start_date_from:
        filters.append(PerformanceMetric.start_date >= start_date_from)
    if start_date_to:
        filters.append(PerformanceMetric.end_date <= start_date_to)
    if min_profit is not None:
        filters.append(PerformanceMetric.net_profit >= min_profit)
    if max_drawdown is not None:
        filters.append(PerformanceMetric.max_drawdown <= max_drawdown)

    base_stmt = (
        select(PerformanceMetric, Strategy.name.label("strategy_name"), Instrument.symbol.label("instrument_symbol"))
        .options(load_only(PerformanceMetric.id, PerformanceMetric.user_id, PerformanceMetric.strategy_id, PerformanceMetric.instrument_id, PerformanceMetric.timeframe, PerformanceMetric.start_date, PerformanceMetric.end_date, PerformanceMetric.initial_capital, PerformanceMetric.final_capital, PerformanceMetric.net_profit, PerformanceMetric.max_drawdown, PerformanceMetric.sharpe_ratio, PerformanceMetric.sortino_ratio, PerformanceMetric.calmar_ratio, PerformanceMetric.win_rate, PerformanceMetric.total_trades, PerformanceMetric.winning_trades, PerformanceMetric.losing_trades, PerformanceMetric.profit_factor, PerformanceMetric.period, PerformanceMetric.return_pct, PerformanceMetric.avg_win, PerformanceMetric.avg_loss, PerformanceMetric.expectancy, PerformanceMetric.status, PerformanceMetric.created_at))
        .outerjoin(Strategy, Strategy.id == PerformanceMetric.strategy_id)
        .outerjoin(Instrument, Instrument.id == PerformanceMetric.instrument_id)
        .where(and_(*filters))
    )

    total = (
        await db.execute(
            select(func.count()).select_from(PerformanceMetric).where(and_(*filters))
        )
    ).scalar() or 0

    offset = (page - 1) * page_size
    rows = (
        await db.execute(base_stmt.order_by(desc(PerformanceMetric.created_at)).offset(offset).limit(page_size))
    ).all()

    backtest_ids = [str(row.id) for row, _, _ in rows]
    debit_map = await _get_backtest_debit_map(db, backtest_ids)

    items = []
    for row, strategy_name, instrument_symbol in rows:
        debit = debit_map.get(str(row.id), {})
        items.append(
            await _serialize_summary(
                db,
                row,
                strategy_name,
                instrument_symbol,
                credit_cost=debit.get("effective_credit_cost", debit.get("credit_cost")),
                debit_transaction_id=debit.get("debit_transaction_id"),
            )
        )

    total_pages = ceil(total / page_size) if total > 0 else 1
    return success_response(
        {
            "backtests": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": int(total),
                "total_pages": int(total_pages),
            },
        }
    )


@router.get("/{backtest_id}")
async def get_backtest_by_id(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = (await db.execute(select(PerformanceMetric).options(load_only(PerformanceMetric.id, PerformanceMetric.user_id, PerformanceMetric.strategy_id, PerformanceMetric.instrument_id, PerformanceMetric.timeframe, PerformanceMetric.start_date, PerformanceMetric.end_date, PerformanceMetric.initial_capital, PerformanceMetric.final_capital, PerformanceMetric.net_profit, PerformanceMetric.max_drawdown, PerformanceMetric.sharpe_ratio, PerformanceMetric.sortino_ratio, PerformanceMetric.calmar_ratio, PerformanceMetric.win_rate, PerformanceMetric.total_trades, PerformanceMetric.winning_trades, PerformanceMetric.losing_trades, PerformanceMetric.profit_factor, PerformanceMetric.period, PerformanceMetric.return_pct, PerformanceMetric.avg_win, PerformanceMetric.avg_loss, PerformanceMetric.expectancy, PerformanceMetric.status, PerformanceMetric.created_at)).where(PerformanceMetric.id == backtest_id))).scalars().first()
    if not row or str(row.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Backtest not found")
    debit = (await _get_backtest_debit_map(db, [str(row.id)])).get(str(row.id), {})
    return success_response(
        await _serialize_summary(
            db,
            row,
            credit_cost=debit.get("effective_credit_cost", debit.get("credit_cost")),
            debit_transaction_id=debit.get("debit_transaction_id"),
        )
    )


@router.get("/{backtest_id}/detail")
async def get_backtest_detail(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = (await db.execute(select(PerformanceMetric).options(load_only(PerformanceMetric.id, PerformanceMetric.user_id, PerformanceMetric.strategy_id, PerformanceMetric.instrument_id, PerformanceMetric.timeframe, PerformanceMetric.start_date, PerformanceMetric.end_date, PerformanceMetric.initial_capital, PerformanceMetric.final_capital, PerformanceMetric.net_profit, PerformanceMetric.max_drawdown, PerformanceMetric.sharpe_ratio, PerformanceMetric.sortino_ratio, PerformanceMetric.calmar_ratio, PerformanceMetric.win_rate, PerformanceMetric.total_trades, PerformanceMetric.winning_trades, PerformanceMetric.losing_trades, PerformanceMetric.profit_factor, PerformanceMetric.period, PerformanceMetric.return_pct, PerformanceMetric.avg_win, PerformanceMetric.avg_loss, PerformanceMetric.expectancy, PerformanceMetric.status, PerformanceMetric.created_at)).where(PerformanceMetric.id == backtest_id))).scalars().first()
    if not row or str(row.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Backtest not found")

    trades_data = []
    equity_data = []
    pnl_data = []

    try:
        trades = (
            await db.execute(
                select(Trade)
                .where(cast(Trade.backtest_id, String) == str(backtest_id))
                .order_by(Trade.entry_time.asc())
            )
        ).scalars().all()
        trades_data = [
            {
                "id": str(t.id),
                "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "side": t.side,
                "quantity": _to_int(t.quantity),
                "entry_price": _to_float(t.entry_price),
                "exit_price": _to_float(t.exit_price),
                "pnl": _to_float(t.pnl),
                "exit_type": t.exit_type,
            }
            for t in trades
        ]
    except Exception as exc:
        logger.warning("Unable to load trades for backtest %s: %s", backtest_id, exc)

    try:
        equity_rows = (
            await db.execute(
                select(EquityCurve)
                .where(cast(EquityCurve.backtest_id, String) == str(backtest_id))
                .order_by(EquityCurve.timestamp.asc())
            )
        ).scalars().all()
        equity_data = [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "equity": _to_float(e.equity),
            }
            for e in equity_rows
        ]
    except Exception as exc:
        logger.warning("Unable to load equity for backtest %s: %s", backtest_id, exc)

    try:
        pnl_rows = (
            await db.execute(
                select(PnLCalendar)
                .where(cast(PnLCalendar.backtest_id, String) == str(backtest_id))
                .order_by(PnLCalendar.date.asc())
            )
        ).scalars().all()
        pnl_data = [
            {
                "date": p.date.isoformat() if p.date else None,
                "pnl": _to_float(p.pnl),
            }
            for p in pnl_rows
        ]
    except Exception as exc:
        logger.warning("Unable to load pnl calendar for backtest %s: %s", backtest_id, exc)

    debit = (await _get_backtest_debit_map(db, [str(row.id)])).get(str(row.id), {})
    summary = await _serialize_summary(
        db,
        row,
        credit_cost=debit.get("effective_credit_cost", debit.get("credit_cost")),
        debit_transaction_id=debit.get("debit_transaction_id"),
    )
    return success_response(
        {
            "summary": summary,
            "trades": trades_data,
            "equity_curve": equity_data,
            "pnl_calendar": pnl_data,
        }
    )
