from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, and_, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import (
    BrokerAccount,
    CreditTransaction,
    Instrument,
    LiveOrder,
    LivePosition,
    LiveTradeLog,
    Notification,
    Payment,
    PerformanceMetric,
    Strategy,
    StrategyDeployment,
    UserCredit,
    UserSubscription,
)
from ...utils.api_response import success_response

router = APIRouter()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _iso(value: Any) -> str | None:
    try:
        return value.isoformat() if value else None
    except Exception:
        return None


def _currency_symbol_for_code(code: str | None) -> str:
    normalized = str(code or "").upper()
    if normalized == "USD":
        return "$"
    if normalized == "INR":
        return "₹"
    if normalized == "EUR":
        return "€"
    if normalized == "GBP":
        return "£"
    return code or "₹"


def _parse_optional_date(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min)


def _end_of_day(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max)


def _period_card(key: str, label: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "net_profit": 0.0,
        "total_trades": 0,
        "win_rate": 0.0,
        "max_drawdown": 0.0,
        "backtest_count": 0,
    }


def _weighted_win_rate(rows: list[Any]) -> float:
    weighted_total = 0.0
    trade_total = 0
    available_rates: list[float] = []
    for row in rows:
        win_rate = _to_float(getattr(row, "win_rate", None), 0.0)
        trades = _to_int(getattr(row, "total_trades", None), 0)
        available_rates.append(win_rate)
        if trades > 0:
            weighted_total += win_rate * trades
            trade_total += trades
    if trade_total > 0:
        return round(weighted_total / trade_total, 4)
    if available_rates:
        return round(sum(available_rates) / len(available_rates), 4)
    return 0.0


def _naive_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    try:
        return value.replace(tzinfo=None) if getattr(value, "tzinfo", None) is not None else value
    except Exception:
        return None


def _aggregate_card(key: str, label: str, rows: list[Any]) -> dict[str, Any]:
    if not rows:
        return _period_card(key, label)
    return {
        "key": key,
        "label": label,
        "net_profit": round(sum(_to_float(getattr(row, "net_profit", None), 0.0) for row in rows), 2),
        "total_trades": sum(_to_int(getattr(row, "total_trades", None), 0) for row in rows),
        "win_rate": _weighted_win_rate(rows),
        "max_drawdown": round(max(abs(_to_float(getattr(row, "max_drawdown", None), 0.0)) for row in rows), 2),
        "backtest_count": len(rows),
    }


def _infer_currency(rows: list[tuple[PerformanceMetric, str | None, Instrument | None]]) -> tuple[str, str]:
    for metric, _, instrument in rows:
        if instrument is None:
            continue
        account_currency = getattr(instrument, "account_currency", None)
        currency_symbol = getattr(instrument, "currency_symbol", None)
        if account_currency or currency_symbol:
            code = str(account_currency or "INR").upper()
            return code, currency_symbol or _currency_symbol_for_code(code)
    return "INR", "₹"


def _recent_item(metric: PerformanceMetric, strategy_name: str | None, instrument: Instrument | None, default_currency: str, default_symbol: str) -> dict[str, Any]:
    account_currency = (getattr(instrument, "account_currency", None) if instrument is not None else None) or default_currency
    currency_symbol = (getattr(instrument, "currency_symbol", None) if instrument is not None else None) or default_symbol or _currency_symbol_for_code(account_currency)
    return {
        "id": str(metric.id),
        "created_at": _iso(metric.created_at),
        "strategy_name": strategy_name or "Unknown Strategy",
        "instrument_symbol": (getattr(instrument, "symbol", None) if instrument is not None else None) or "Unknown",
        "timeframe": metric.timeframe,
        "net_profit": _to_float(metric.net_profit),
        "win_rate": _to_float(metric.win_rate),
        "max_drawdown": abs(_to_float(metric.max_drawdown)),
        "max_drawdown_type": "amount",
        "total_trades": _to_int(metric.total_trades),
        "status": metric.status or "unknown",
        "account_currency": account_currency,
        "currency_symbol": currency_symbol,
    }


def _empty_live_summary() -> dict[str, Any]:
    return {
        "total_net_profit": 0.0,
        "today_profit": 0.0,
        "open_positions": 0,
        "closed_trades": 0,
        "win_rate": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_type": "amount",
        "active_deployments": 0,
        "connected_brokers": 0,
        "last_trade_at": None,
    }


async def _safe_scalar(db: AsyncSession, statement: Any, default: Any = 0) -> Any:
    try:
        value = (await db.execute(statement)).scalar()
        return default if value is None else value
    except Exception:
        await db.rollback()
        return default


async def _safe_all(db: AsyncSession, statement: Any) -> list[Any]:
    try:
        return list((await db.execute(statement)).all())
    except Exception:
        await db.rollback()
        return []


async def _build_live_summary(db: AsyncSession, uid: str, today_start: datetime) -> tuple[dict[str, Any], bool]:
    live = _empty_live_summary()

    active_deployments = await _safe_scalar(
        db,
        select(func.count(StrategyDeployment.id)).where(
            cast(StrategyDeployment.user_id, String) == uid,
            func.lower(StrategyDeployment.status).in_(["active", "running", "deployed", "live"]),
        ),
        0,
    )
    connected_brokers = await _safe_scalar(
        db,
        select(func.count(BrokerAccount.id)).where(
            cast(BrokerAccount.user_id, String) == uid,
            func.lower(BrokerAccount.status).in_(["connected", "active"]),
        ),
        0,
    )
    open_positions = await _safe_scalar(
        db,
        select(func.count(LivePosition.id)).where(cast(LivePosition.user_id, String) == uid, func.lower(LivePosition.status) == "open"),
        0,
    )
    closed_positions = await _safe_all(
        db,
        select(LivePosition).where(cast(LivePosition.user_id, String) == uid, func.lower(LivePosition.status).in_(["closed", "exit", "exited"])),
    )

    closed_trades = len(closed_positions)
    total_net_profit = round(sum(_to_float(getattr(row[0] if isinstance(row, tuple) else row, "realized_pnl", None)) for row in closed_positions), 2)
    today_profit = round(
        sum(
            _to_float(getattr(row[0] if isinstance(row, tuple) else row, "realized_pnl", None))
            for row in closed_positions
            if _naive_dt(getattr(row[0] if isinstance(row, tuple) else row, "closed_at", None))
            and _naive_dt(getattr(row[0] if isinstance(row, tuple) else row, "closed_at", None)) >= today_start
        ),
        2,
    )
    wins = sum(1 for row in closed_positions if _to_float(getattr(row[0] if isinstance(row, tuple) else row, "realized_pnl", None)) > 0)
    last_trade_at = None
    if closed_positions:
        last_dates = [_naive_dt(getattr(row[0] if isinstance(row, tuple) else row, "closed_at", None)) for row in closed_positions]
        last_dates = [value for value in last_dates if value is not None]
        if last_dates:
            last_trade_at = max(last_dates).isoformat()

    live.update(
        {
            "total_net_profit": total_net_profit,
            "today_profit": today_profit,
            "open_positions": _to_int(open_positions),
            "closed_trades": closed_trades,
            "win_rate": round((wins / closed_trades) if closed_trades else 0.0, 4),
            "max_drawdown": 0.0,
            "max_drawdown_type": "amount",
            "active_deployments": _to_int(active_deployments),
            "connected_brokers": _to_int(connected_brokers),
            "last_trade_at": last_trade_at,
        }
    )

    has_live_data = bool(active_deployments or connected_brokers or open_positions or closed_trades or abs(total_net_profit) > 0)
    return live, has_live_data


@router.get("/user-summary")
async def get_user_report_summary(
    range_from: date | None = Query(default=None),
    range_to: date | None = Query(default=None),
    page_size: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = str(current_user["user_id"])
    range_start = _parse_optional_date(range_from)
    range_end = _end_of_day(range_to)

    filters = [cast(PerformanceMetric.user_id, String) == uid]
    if range_start is not None:
        filters.append(PerformanceMetric.created_at >= range_start)
    if range_end is not None:
        filters.append(PerformanceMetric.created_at <= range_end)

    rows = (
        await db.execute(
            select(PerformanceMetric, Strategy.name.label("strategy_name"), Instrument)
            .outerjoin(Strategy, Strategy.id == PerformanceMetric.strategy_id)
            .outerjoin(Instrument, Instrument.id == PerformanceMetric.instrument_id)
            .where(and_(*filters))
            .order_by(desc(PerformanceMetric.created_at))
            .limit(page_size)
        )
    ).all()

    completed_filters = [cast(PerformanceMetric.user_id, String) == uid, func.lower(PerformanceMetric.status) == "completed"]
    if range_start is not None:
        completed_filters.append(PerformanceMetric.created_at >= range_start)
    if range_end is not None:
        completed_filters.append(PerformanceMetric.created_at <= range_end)

    completed_rows = (
        await db.execute(
            select(PerformanceMetric, Strategy.name.label("strategy_name"), Instrument)
            .outerjoin(Strategy, Strategy.id == PerformanceMetric.strategy_id)
            .outerjoin(Instrument, Instrument.id == PerformanceMetric.instrument_id)
            .where(and_(*completed_filters))
        )
    ).all()

    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    year_start = today_start.replace(month=1, day=1)

    metrics_only = [metric for metric, _, _ in completed_rows]

    def period_rows(start: datetime) -> list[PerformanceMetric]:
        return [metric for metric in metrics_only if _naive_dt(metric.created_at) and _naive_dt(metric.created_at) >= start]

    performance_cards = [
        _aggregate_card("today", "Today", period_rows(today_start)),
        _aggregate_card("week", "This Week", period_rows(week_start)),
        _aggregate_card("month", "This Month", period_rows(month_start)),
        _aggregate_card("year", "This Year", period_rows(year_start)),
    ]

    ytd_rows = period_rows(year_start)
    ytd_ids = {str(metric.id) for metric in ytd_rows}
    ytd_joined = [(metric, strategy_name, instrument) for metric, strategy_name, instrument in completed_rows if str(metric.id) in ytd_ids]
    account_currency, currency_symbol = _infer_currency(ytd_joined or completed_rows or rows)

    strategy_profit: defaultdict[str, float] = defaultdict(float)
    instrument_profit: defaultdict[str, float] = defaultdict(float)
    for metric, strategy_name, instrument in ytd_joined:
        profit = _to_float(metric.net_profit)
        if strategy_name:
            strategy_profit[strategy_name] += profit
        if instrument is not None and getattr(instrument, "symbol", None):
            instrument_profit[str(instrument.symbol)] += profit

    year_card = performance_cards[-1]
    backtest_summary = {
        "total_net_profit_ytd": year_card["net_profit"],
        "average_win_rate_ytd": year_card["win_rate"],
        "max_drawdown_ytd": year_card["max_drawdown"],
        "max_drawdown_type": "amount",
        "total_backtests_ytd": year_card["backtest_count"],
        "total_trades_ytd": year_card["total_trades"],
        "best_strategy_name": max(strategy_profit.items(), key=lambda item: item[1])[0] if strategy_profit else None,
        "best_instrument_symbol": max(instrument_profit.items(), key=lambda item: item[1])[0] if instrument_profit else None,
    }
    summary = {
        **backtest_summary,
        "account_currency": account_currency,
        "currency_symbol": currency_symbol,
    }

    recent_backtests = [_recent_item(metric, strategy_name, instrument, account_currency, currency_symbol) for metric, strategy_name, instrument in rows]
    live_summary, has_live_data = await _build_live_summary(db, uid, today_start)
    has_backtest_data = bool(completed_rows or rows)

    return success_response(
        {
            "report_mode": "live" if has_live_data else "backtest_research",
            "has_live_data": has_live_data,
            "has_backtest_data": has_backtest_data,
            "currency_symbol": currency_symbol,
            "account_currency": account_currency,
            "live_summary": live_summary,
            "backtest_summary": backtest_summary,
            "summary": summary,
            "performance_cards": performance_cards,
            "recent_backtests": recent_backtests,
        }
    )


@router.get("/activity")
async def get_user_report_activity(
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = str(current_user["user_id"])
    items: list[dict[str, Any]] = []

    notification_rows = await _safe_all(
        db,
        select(Notification).where(cast(Notification.user_id, String) == uid).order_by(desc(Notification.created_at)).limit(page_size),
    )
    for row in notification_rows:
        item = row[0] if isinstance(row, tuple) else row
        severity = str(getattr(item, "severity", None) or "info").lower()
        items.append(
            {
                "id": str(getattr(item, "id", "")),
                "type": str(getattr(item, "type", None) or getattr(item, "entity_type", None) or "notification"),
                "title": getattr(item, "title", None) or "Notification",
                "message": getattr(item, "message", None) or "",
                "created_at": _iso(getattr(item, "created_at", None)),
                "status": severity if severity in {"info", "success", "warning", "error"} else "info",
                "source": "Notifications",
            }
        )

    if len(items) < page_size:
        backtest_rows = await _safe_all(
            db,
            select(PerformanceMetric).where(cast(PerformanceMetric.user_id, String) == uid).order_by(desc(PerformanceMetric.created_at)).limit(page_size - len(items)),
        )
        for row in backtest_rows:
            metric = row[0] if isinstance(row, tuple) else row
            status = str(getattr(metric, "status", None) or "").lower()
            items.append(
                {
                    "id": str(getattr(metric, "id", "")),
                    "type": "backtest",
                    "title": "Backtest completed" if status == "completed" else "Backtest updated",
                    "message": f"Report generated for {getattr(metric, 'timeframe', None) or 'selected timeframe'}.",
                    "created_at": _iso(getattr(metric, "created_at", None)),
                    "status": "success" if status == "completed" else "info",
                    "source": "Backtests",
                }
            )

    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return success_response({"items": items[:page_size]})


@router.get("/billing-credits")
async def get_user_billing_credits_report(
    page_size: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = str(current_user["user_id"])
    now = datetime.now()
    month_start = datetime.combine(now.date().replace(day=1), time.min)

    credit_balance = await _safe_scalar(db, select(UserCredit.balance).where(cast(UserCredit.user_id, String) == uid), 0)
    credit_events_rows = await _safe_all(
        db,
        select(CreditTransaction).where(cast(CreditTransaction.user_id, String) == uid).order_by(desc(CreditTransaction.created_at)).limit(page_size),
    )
    month_credit_rows = await _safe_all(
        db,
        select(CreditTransaction).where(cast(CreditTransaction.user_id, String) == uid, CreditTransaction.created_at >= month_start),
    )

    def tx_type(value: Any) -> str:
        raw = getattr(value, "value", value)
        return str(raw or "").lower()

    credits_used_this_month = 0.0
    credits_added_this_month = 0.0
    for row in month_credit_rows:
        tx = row[0] if isinstance(row, tuple) else row
        amount = abs(_to_float(getattr(tx, "amount", None)))
        kind = tx_type(getattr(tx, "transaction_type", None))
        if kind == "debit":
            credits_used_this_month += amount
        elif kind in {"credit", "refund"}:
            credits_added_this_month += amount

    recent_credit_events = []
    for row in credit_events_rows:
        tx = row[0] if isinstance(row, tuple) else row
        kind = tx_type(getattr(tx, "transaction_type", None))
        recent_credit_events.append(
            {
                "id": str(getattr(tx, "id", "")),
                "type": "debit" if kind == "debit" else "credit",
                "amount": _to_float(getattr(tx, "amount", None)),
                "reason": getattr(tx, "description", None) or getattr(tx, "source", None) or "Credit transaction",
                "created_at": _iso(getattr(tx, "created_at", None)),
            }
        )

    subscription_row = (
        await _safe_all(
            db,
            select(UserSubscription)
            .where(cast(UserSubscription.user_id, String) == uid)
            .order_by(desc(UserSubscription.created_at))
            .limit(1),
        )
    )
    active_plan = None
    subscription_status = None
    if subscription_row:
        sub = subscription_row[0][0] if isinstance(subscription_row[0], tuple) else subscription_row[0]
        active_plan = getattr(sub, "plan_code_snapshot", None)
        subscription_status = getattr(sub, "status", None)

    payment_rows = await _safe_all(
        db,
        select(Payment).where(cast(Payment.user_id, String) == uid).order_by(desc(Payment.created_at)).limit(page_size),
    )
    recent_payments = []
    for row in payment_rows:
        payment = row[0] if isinstance(row, tuple) else row
        recent_payments.append(
            {
                "id": str(getattr(payment, "id", "")),
                "amount": _to_float(getattr(payment, "amount_inr", None)),
                "currency": getattr(payment, "currency", None) or "INR",
                "status": getattr(payment, "status", None) or "unknown",
                "created_at": _iso(getattr(payment, "created_at", None)),
            }
        )

    return success_response(
        {
            "credit_balance": _to_float(credit_balance),
            "credits_used_this_month": round(credits_used_this_month, 2),
            "credits_added_this_month": round(credits_added_this_month, 2),
            "active_plan": active_plan,
            "subscription_status": subscription_status,
            "recent_credit_events": recent_credit_events,
            "recent_payments": recent_payments,
        }
    )
