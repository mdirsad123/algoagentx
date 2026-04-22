from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from math import ceil
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, and_, cast, desc, func, or_, select, text, update
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
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
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

    performance = PerformanceMetric(
        id=backtest_id,
        user_id=as_uuid_or_str(user_id),
        strategy_id=payload.strategy_id,
        instrument_id=payload.instrument_id,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=_decimal(payload.capital),
        final_capital=_decimal(service_response.final_capital),
        net_profit=_decimal(metrics.get("net_profit")),
        max_drawdown=_decimal(metrics.get("max_drawdown")),
        sharpe_ratio=_decimal(metrics.get("sharpe_ratio")),
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        profit_factor=_decimal(metrics.get("profit_factor")),
        status="completed",
    )
    db.add(performance)
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
                            entry_time=trade.entry_datetime,
                            exit_time=trade.exit_datetime,
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
                            timestamp=base + timedelta(minutes=idx),
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
        balance = await CreditManagementService.get_user_balance(db, str(user_id))
    except Exception:
        balance = Decimal("0")

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
                "balance": _to_float(balance),
                "included": _to_int(entitlements.get("included_credits", 0)),
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
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
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
                "available": False,
                "candle_count": 0,
                "min_timestamp": None,
                "max_timestamp": None,
                "requested_candle_count": 0,
            }
        )

    requested_count = None
    if start_date and end_date:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        requested_count = (
            await db.execute(
                select(func.count()).select_from(MarketData).where(
                    MarketData.instrument_id == instrument_id,
                    MarketData.timeframe == timeframe,
                    MarketData.timestamp >= start_dt,
                    MarketData.timestamp <= end_dt,
                )
            )
        ).scalar() or 0

    return success_response(
        {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "available": True,
            "candle_count": _to_int(summary.count),
            "min_timestamp": summary.min_ts.isoformat() if summary.min_ts else None,
            "max_timestamp": summary.max_ts.isoformat() if summary.max_ts else None,
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

    availability = (
        await db.execute(
            select(func.count()).select_from(MarketData).where(
                MarketData.instrument_id == payload.instrument_id,
                MarketData.timeframe == payload.timeframe,
                MarketData.timestamp >= datetime.combine(payload.start_date, time.min),
                MarketData.timestamp <= datetime.combine(payload.end_date, time.max),
            )
        )
    ).scalar() or 0

    if availability <= 0:
        raise HTTPException(status_code=400, detail="No market data available for requested filters")

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
                    "subscription_state": (consumption or {}).get("subscription_state"),
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
        if consumption is not None:
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

        job.status = "failed"
        job.progress = 0
        job.message = str(exc)
        job.completed_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {exc}")


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
    row = await db.get(PerformanceMetric, backtest_id)
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
    row = await db.get(PerformanceMetric, backtest_id)
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
