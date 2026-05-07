from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _upper(value: Any) -> str | None:
    text_value = str(value or "").strip().upper()
    return text_value or None


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _ceil_decimal(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _has_advanced_filters(advanced_filters: Any) -> bool:
    if not advanced_filters:
        return False
    if isinstance(advanced_filters, dict):
        return bool(advanced_filters.get("enabled"))
    return bool(getattr(advanced_filters, "enabled", False))


class CreditCostService:
    DEFAULT_RULE_NAME = "Default Backtest Candle Rule"

    @staticmethod
    async def ensure_table(db: AsyncSession) -> None:
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS billing_credit_expense_rules (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                operation_type TEXT NOT NULL DEFAULT 'BACKTEST',
                market TEXT NULL,
                instrument_symbol TEXT NULL,
                timeframe TEXT NULL,
                base_credits INTEGER NOT NULL DEFAULT 1,
                per_1000_candles_credits NUMERIC(12, 4) NOT NULL DEFAULT 1,
                min_credits INTEGER NOT NULL DEFAULT 1,
                max_credits INTEGER NULL,
                advanced_filter_multiplier NUMERIC(12, 4) NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                priority INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        exists = (await db.execute(text("""
            SELECT 1 FROM billing_credit_expense_rules
            WHERE operation_type = 'BACKTEST' AND market = 'ALL'
              AND instrument_symbol IS NULL AND timeframe IS NULL
            LIMIT 1
        """))).scalar()
        if not exists:
            await db.execute(text("""
                INSERT INTO billing_credit_expense_rules (
                    id, name, operation_type, market, instrument_symbol, timeframe,
                    base_credits, per_1000_candles_credits, min_credits, max_credits,
                    advanced_filter_multiplier, is_active, priority, created_at, updated_at
                ) VALUES (
                    :id, :name, 'BACKTEST', 'ALL', NULL, NULL,
                    1, 1, 1, NULL, 1, TRUE, 1000, NOW(), NOW()
                )
            """), {"id": str(uuid4()), "name": CreditCostService.DEFAULT_RULE_NAME})

    @staticmethod
    async def get_instrument_context(db: AsyncSession, instrument_id: int | None = None, instrument_symbol: str | None = None) -> dict[str, str | None]:
        if instrument_id is None and not instrument_symbol:
            return {"symbol": _upper(instrument_symbol), "market": None}
        where = "id = :instrument_id" if instrument_id is not None else "UPPER(symbol) = :symbol"
        params = {"instrument_id": instrument_id, "symbol": _upper(instrument_symbol)}
        row = (await db.execute(text(f"""
            SELECT symbol, market, asset_class, exchange, instrument_type
            FROM instruments
            WHERE {where}
            LIMIT 1
        """), params)).mappings().first()
        if not row:
            return {"symbol": _upper(instrument_symbol), "market": None}
        market = _upper(row.get("market") or row.get("asset_class") or row.get("exchange") or row.get("instrument_type"))
        if market in {"NSE", "BSE", "INDIA", "INDIAN_STOCK", "INDIAN_MARKET"}:
            market = "INDIAN"
        elif market in {"FX", "FOREX", "CURRENCY"}:
            market = "FOREX"
        elif market in {"CRYPTO", "CRYPTOCURRENCY"}:
            market = "CRYPTO"
        return {"symbol": _upper(row.get("symbol") or instrument_symbol), "market": market}

    @staticmethod
    async def find_best_rule(db: AsyncSession, *, operation_type: str, market: str | None, instrument_symbol: str | None, timeframe: str | None) -> dict[str, Any]:
        await CreditCostService.ensure_table(db)
        operation_type = _upper(operation_type) or "BACKTEST"
        market = _upper(market)
        instrument_symbol = _upper(instrument_symbol)
        timeframe = _upper(timeframe)
        rows = (await db.execute(text("""
            SELECT *
            FROM billing_credit_expense_rules
            WHERE is_active = TRUE
              AND operation_type = :operation_type
              AND (market IS NULL OR market = 'ALL' OR market = :market)
              AND (instrument_symbol IS NULL OR UPPER(instrument_symbol) = :instrument_symbol)
              AND (timeframe IS NULL OR UPPER(timeframe) = :timeframe)
            ORDER BY priority ASC, updated_at DESC
        """), {
            "operation_type": operation_type,
            "market": market,
            "instrument_symbol": instrument_symbol,
            "timeframe": timeframe,
        })).mappings().all()
        if not rows:
            return {
                "id": None,
                "name": CreditCostService.DEFAULT_RULE_NAME,
                "operation_type": "BACKTEST",
                "market": "ALL",
                "instrument_symbol": None,
                "timeframe": None,
                "base_credits": 1,
                "per_1000_candles_credits": Decimal("1"),
                "min_credits": 1,
                "max_credits": None,
                "advanced_filter_multiplier": Decimal("1"),
                "priority": 9999,
            }

        def score(row: Any) -> int:
            if _upper(row.get("instrument_symbol")) == instrument_symbol and _upper(row.get("timeframe")) == timeframe:
                return 1
            if (_upper(row.get("market")) in {market, "ALL"}) and _upper(row.get("timeframe")) == timeframe:
                return 2
            if _upper(row.get("timeframe")) == timeframe:
                return 3
            if _upper(row.get("market")) in {market, "ALL"} and row.get("timeframe") is None:
                return 4
            return 5

        return dict(sorted(rows, key=lambda row: (score(row), int(row.get("priority") or 100)))[0])

    @staticmethod
    async def calculate_backtest_credit_cost(
        db: AsyncSession,
        *,
        user_id: str | None = None,
        instrument_id: int | None = None,
        instrument: str | None = None,
        timeframe: str,
        start_date: date | None = None,
        end_date: date | None = None,
        candle_count: int | None = None,
        advanced_filters: Any = None,
    ) -> dict[str, Any]:
        context = await CreditCostService.get_instrument_context(db, instrument_id=instrument_id, instrument_symbol=instrument)
        symbol = context.get("symbol") or _upper(instrument)
        market = context.get("market")
        rule = await CreditCostService.find_best_rule(
            db,
            operation_type="BACKTEST",
            market=market,
            instrument_symbol=symbol,
            timeframe=timeframe,
        )
        candles = max(int(candle_count or 0), 0)
        candle_units = _ceil_decimal(Decimal(candles) / Decimal("1000")) if candles > 0 else 0
        base = int(rule.get("base_credits") or 0)
        per_1000 = _to_decimal(rule.get("per_1000_candles_credits"), "1")
        raw_cost = Decimal(base) + (Decimal(candle_units) * per_1000)
        filters_used = _has_advanced_filters(advanced_filters)
        multiplier = _to_decimal(rule.get("advanced_filter_multiplier"), "1") if filters_used else Decimal("1")
        raw_cost = raw_cost * multiplier
        min_credits = int(rule.get("min_credits") or 0)
        max_credits = rule.get("max_credits")
        rounded_cost = max(_ceil_decimal(raw_cost), min_credits)
        if max_credits is not None:
            rounded_cost = min(rounded_cost, int(max_credits))
        return {
            "credit_cost": int(rounded_cost),
            "total_cost": int(rounded_cost),
            "estimated_candles": candles,
            "candle_count": candles,
            "candle_units": int(candle_units),
            "advanced_filters_used": filters_used,
            "pricing_rule": rule.get("name") or CreditCostService.DEFAULT_RULE_NAME,
            "pricing_rule_id": str(rule.get("id")) if rule.get("id") else None,
            "rule": {k: (float(v) if isinstance(v, Decimal) else v) for k, v in dict(rule).items()},
            "breakdown": {
                "pricing_version": "PAY-BILL-5",
                "rule_set_id": str(rule.get("id")) if rule.get("id") else None,
                "rule_set_name": rule.get("name") or CreditCostService.DEFAULT_RULE_NAME,
                "operation_type": "BACKTEST",
                "market": market,
                "instrument_symbol": symbol,
                "timeframe": _upper(timeframe),
                "date_range_days": (end_date - start_date).days + 1 if start_date and end_date else None,
                "candle_count": candles,
                "candle_count_mode": "actual",
                "base_cost": base,
                "per_1000_candles_credits": float(per_1000),
                "candle_units": int(candle_units),
                "advanced_filter_multiplier": float(multiplier),
                "min_credits": min_credits,
                "max_credits": int(max_credits) if max_credits is not None else None,
                "total_cost": int(rounded_cost),
            },
        }
