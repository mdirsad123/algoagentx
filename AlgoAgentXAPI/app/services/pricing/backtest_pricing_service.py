from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BacktestPricingRuleSet, MarketData


class BacktestPricingService:
    """DB-driven pricing service for backtest estimation and execution-time pricing."""

    PRICING_VERSION = "db-v1"

    DEFAULT_RULES = {
        "name": "Default Backtest Pricing",
        "version": "v1",
        "description": "Fallback rules when DB config is unavailable",
        "base_cost": Decimal("2.00"),
        "range_days_step": 30,
        "min_credit_charge": 1,
        "max_credit_charge": None,
        "date_range_buckets": [
            {"max_days": 30, "multiplier": 1.00},
            {"max_days": 90, "multiplier": 1.35},
            {"max_days": 365, "multiplier": 1.90},
            {"max_days": None, "multiplier": 2.60},
        ],
        "timeframe_multipliers": [
            {"max_minutes": 15, "multiplier": 1.60},
            {"max_minutes": 60, "multiplier": 1.30},
            {"max_minutes": 240, "multiplier": 1.05},
            {"max_minutes": None, "multiplier": 0.85},
        ],
        "strategy_complexity_enabled": False,
        "strategy_complexity_step": Decimal("0.0100"),
        "strategy_complexity_cap": Decimal("0.2000"),
        "plan_discounts": {},
    }

    TIMEFRAME_TO_MINUTES = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "10m": 10,
        "15m": 15,
        "30m": 30,
        "45m": 45,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "1d": 1440,
        "1w": 10080,
        "1mo": 43200,
    }

    @classmethod
    def _timeframe_minutes(cls, timeframe: str) -> int:
        normalized = (timeframe or "").strip().lower()
        if normalized in cls.TIMEFRAME_TO_MINUTES:
            return cls.TIMEFRAME_TO_MINUTES[normalized]

        if normalized.endswith("m") and normalized[:-1].isdigit():
            return max(1, int(normalized[:-1]))
        if normalized.endswith("h") and normalized[:-1].isdigit():
            return max(1, int(normalized[:-1]) * 60)
        if normalized.endswith("d") and normalized[:-1].isdigit():
            return max(1, int(normalized[:-1]) * 1440)
        if normalized.endswith("w") and normalized[:-1].isdigit():
            return max(1, int(normalized[:-1]) * 10080)
        return 60

    @classmethod
    def _pick_tier_multiplier(cls, value: int, tiers: list[dict[str, Any]], key: str) -> Decimal:
        sorted_tiers = sorted(
            tiers,
            key=lambda item: (10**12 if item.get(key) is None else int(item.get(key))),
        )
        for tier in sorted_tiers:
            upper_bound = tier.get(key)
            if upper_bound is None or value <= int(upper_bound):
                return Decimal(str(tier.get("multiplier", 1) or 1)).quantize(Decimal("0.0001"))
        return Decimal("1.00")

    @classmethod
    def _complexity_multiplier(cls, strategy_parameters: dict[str, Any] | None) -> tuple[Decimal, dict[str, Any]]:
        if not isinstance(strategy_parameters, dict):
            return Decimal("1.00"), {"parameter_count": 0, "complexity_score": 0}

        parameter_count = len(strategy_parameters.keys())
        complexity_score = min(20, parameter_count)
        multiplier = Decimal("1.00") + (Decimal(complexity_score) / Decimal("100"))
        return multiplier.quantize(Decimal("0.01")), {
            "parameter_count": parameter_count,
            "complexity_score": complexity_score,
        }

    @classmethod
    def _complexity_multiplier_from_rules(
        cls,
        strategy_parameters: dict[str, Any] | None,
        *,
        enabled: bool,
        step: Decimal,
        cap: Decimal,
    ) -> tuple[Decimal, dict[str, Any]]:
        if not enabled:
            return Decimal("1.00"), {"parameter_count": 0, "complexity_score": 0, "enabled": False}

        if not isinstance(strategy_parameters, dict):
            return Decimal("1.00"), {"parameter_count": 0, "complexity_score": 0, "enabled": True}

        parameter_count = len(strategy_parameters.keys())
        complexity_score = min(parameter_count, 100)
        multiplier = Decimal("1.00") + min(cap, step * Decimal(complexity_score))
        return multiplier.quantize(Decimal("0.0001")), {
            "parameter_count": parameter_count,
            "complexity_score": complexity_score,
            "enabled": True,
            "step": float(step),
            "cap": float(cap),
        }

    @classmethod
    async def _table_exists(cls, db: AsyncSession, table_name: str) -> bool:
        try:
            bind = db.get_bind()
            dialect = bind.dialect.name if bind is not None else ""
            if dialect == "sqlite":
                result = await db.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
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

    @classmethod
    def _normalize_date_buckets(cls, buckets: Any) -> list[dict[str, Any]]:
        fallback = cls.DEFAULT_RULES["date_range_buckets"]
        if not isinstance(buckets, list):
            return list(fallback)

        normalized: list[dict[str, Any]] = []
        for item in buckets:
            if not isinstance(item, dict):
                continue
            max_days = item.get("max_days")
            max_days = None if max_days is None else max(1, int(max_days))
            multiplier = float(item.get("multiplier", 1.0) or 1.0)
            if multiplier <= 0:
                continue
            normalized.append({"max_days": max_days, "multiplier": multiplier})

        if not normalized:
            return list(fallback)
        return sorted(normalized, key=lambda row: (10**12 if row["max_days"] is None else int(row["max_days"])))

    @classmethod
    def _normalize_timeframe_buckets(cls, buckets: Any) -> list[dict[str, Any]]:
        fallback = cls.DEFAULT_RULES["timeframe_multipliers"]
        if not isinstance(buckets, list):
            return list(fallback)

        normalized: list[dict[str, Any]] = []
        for item in buckets:
            if not isinstance(item, dict):
                continue
            max_minutes = item.get("max_minutes")
            max_minutes = None if max_minutes is None else max(1, int(max_minutes))
            multiplier = float(item.get("multiplier", 1.0) or 1.0)
            if multiplier <= 0:
                continue
            normalized.append({"max_minutes": max_minutes, "multiplier": multiplier})

        if not normalized:
            return list(fallback)
        return sorted(normalized, key=lambda row: (10**12 if row["max_minutes"] is None else int(row["max_minutes"])))

    @classmethod
    def _normalize_plan_discounts(cls, payload: Any) -> dict[str, float]:
        if not isinstance(payload, dict):
            return {}
        out: dict[str, float] = {}
        for key, value in payload.items():
            try:
                pct = float(value)
            except Exception:
                continue
            if pct < 0:
                pct = 0.0
            if pct > 0.95:
                pct = 0.95
            out[str(key).upper()] = pct
        return out

    @classmethod
    async def get_active_pricing_config(cls, db: AsyncSession) -> dict[str, Any]:
        if not await cls._table_exists(db, "backtest_pricing_rule_sets"):
            return {
                "id": None,
                "is_db_configured": False,
                **cls.DEFAULT_RULES,
            }

        row = (
            await db.execute(
                select(BacktestPricingRuleSet)
                .where(BacktestPricingRuleSet.is_active == True)
                .order_by(BacktestPricingRuleSet.updated_at.desc(), BacktestPricingRuleSet.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if row is None:
            row = (
                await db.execute(
                    select(BacktestPricingRuleSet)
                    .order_by(BacktestPricingRuleSet.updated_at.desc(), BacktestPricingRuleSet.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        if row is None:
            return {
                "id": None,
                "is_db_configured": False,
                **cls.DEFAULT_RULES,
            }

        return {
            "id": str(row.id),
            "name": row.name,
            "version": row.version,
            "description": row.description,
            "is_active": bool(row.is_active),
            "is_locked": bool(getattr(row, "is_locked", False)),
            "base_cost": Decimal(str(row.base_cost or cls.DEFAULT_RULES["base_cost"])),
            "range_days_step": int(row.range_days_step or cls.DEFAULT_RULES["range_days_step"]),
            "min_credit_charge": int(row.min_credit_charge or 1),
            "max_credit_charge": int(row.max_credit_charge) if row.max_credit_charge is not None else None,
            "date_range_buckets": cls._normalize_date_buckets(row.date_range_buckets),
            "timeframe_multipliers": cls._normalize_timeframe_buckets(row.timeframe_multipliers),
            "strategy_complexity_enabled": bool(getattr(row, "strategy_complexity_enabled", False)),
            "strategy_complexity_step": Decimal(str(getattr(row, "strategy_complexity_step", 0) or 0)),
            "strategy_complexity_cap": Decimal(str(getattr(row, "strategy_complexity_cap", 0) or 0)),
            "plan_discounts": cls._normalize_plan_discounts(getattr(row, "plan_discounts", None)),
            "is_db_configured": True,
            "updated_at": row.updated_at,
        }

    @classmethod
    async def list_rule_sets(cls, db: AsyncSession) -> list[dict[str, Any]]:
        if not await cls._table_exists(db, "backtest_pricing_rule_sets"):
            return []
        rows = (
            await db.execute(
                select(BacktestPricingRuleSet)
                .order_by(BacktestPricingRuleSet.is_active.desc(), BacktestPricingRuleSet.updated_at.desc())
            )
        ).scalars().all()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": str(row.id),
                    "name": row.name,
                    "version": row.version,
                    "description": row.description,
                    "is_active": bool(row.is_active),
                    "is_locked": bool(getattr(row, "is_locked", False)),
                    "base_cost": float(row.base_cost or 0),
                    "min_credit_charge": int(row.min_credit_charge or 1),
                    "max_credit_charge": int(row.max_credit_charge) if row.max_credit_charge is not None else None,
                    "updated_at": row.updated_at,
                    "created_at": row.created_at,
                }
            )
        return out

    @classmethod
    async def update_or_create_active_rule_set(
        cls,
        db: AsyncSession,
        payload: dict[str, Any],
        *,
        actor_user_id: str | None = None,
    ) -> BacktestPricingRuleSet:
        active = None
        if await cls._table_exists(db, "backtest_pricing_rule_sets"):
            active = (
                await db.execute(
                    select(BacktestPricingRuleSet)
                    .where(BacktestPricingRuleSet.is_active == True)
                    .order_by(BacktestPricingRuleSet.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        if active is None:
            active = BacktestPricingRuleSet(
                name=str(payload.get("name") or cls.DEFAULT_RULES["name"]),
                version=str(payload.get("version") or cls.DEFAULT_RULES["version"]),
                description=payload.get("description"),
                is_active=True,
                is_locked=False,
                date_range_buckets=cls._normalize_date_buckets(payload.get("date_range_buckets")),
                timeframe_multipliers=cls._normalize_timeframe_buckets(payload.get("timeframe_multipliers")),
                created_by=str(actor_user_id) if actor_user_id else None,
            )
            db.add(active)

        active.name = str(payload.get("name") or active.name or cls.DEFAULT_RULES["name"])
        active.version = str(payload.get("version") or active.version or cls.DEFAULT_RULES["version"])
        active.description = payload.get("description")
        active.base_cost = Decimal(str(payload.get("base_cost") if payload.get("base_cost") is not None else active.base_cost or cls.DEFAULT_RULES["base_cost"]))
        active.range_days_step = max(1, int(payload.get("range_days_step") if payload.get("range_days_step") is not None else active.range_days_step or cls.DEFAULT_RULES["range_days_step"]))
        active.min_credit_charge = max(1, int(payload.get("min_credit_charge") if payload.get("min_credit_charge") is not None else active.min_credit_charge or 1))
        if "max_credit_charge" in payload:
            max_charge = payload.get("max_credit_charge")
            if max_charge is None:
                active.max_credit_charge = None
            else:
                active.max_credit_charge = max(active.min_credit_charge, int(max_charge))
        active.date_range_buckets = cls._normalize_date_buckets(payload.get("date_range_buckets") or active.date_range_buckets)
        active.timeframe_multipliers = cls._normalize_timeframe_buckets(payload.get("timeframe_multipliers") or active.timeframe_multipliers)
        active.strategy_complexity_enabled = bool(payload.get("strategy_complexity_enabled", active.strategy_complexity_enabled))
        active.strategy_complexity_step = Decimal(str(payload.get("strategy_complexity_step") if payload.get("strategy_complexity_step") is not None else active.strategy_complexity_step or 0))
        active.strategy_complexity_cap = Decimal(str(payload.get("strategy_complexity_cap") if payload.get("strategy_complexity_cap") is not None else active.strategy_complexity_cap or 0))
        if payload.get("plan_discounts") is not None:
            active.plan_discounts = cls._normalize_plan_discounts(payload.get("plan_discounts"))
        active.is_active = True
        active.updated_by = str(actor_user_id) if actor_user_id else active.updated_by

        await db.flush()

        if await cls._table_exists(db, "backtest_pricing_rule_sets"):
            await db.execute(
                text("UPDATE backtest_pricing_rule_sets SET is_active = FALSE WHERE id <> :rule_id"),
                {"rule_id": active.id},
            )
        return active

    @classmethod
    async def activate_rule_set(cls, db: AsyncSession, rule_set_id: str) -> BacktestPricingRuleSet | None:
        if not await cls._table_exists(db, "backtest_pricing_rule_sets"):
            return None
        target = await db.get(BacktestPricingRuleSet, rule_set_id)
        if not target:
            return None
        await db.execute(text("UPDATE backtest_pricing_rule_sets SET is_active = FALSE"))
        target.is_active = True
        await db.flush()
        return target

    @classmethod
    async def _actual_candle_count(
        cls,
        db: AsyncSession,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
    ) -> int:
        result = await db.execute(
            select(func.count()).select_from(MarketData).where(
                MarketData.instrument_id == instrument_id,
                MarketData.timeframe == timeframe,
                MarketData.timestamp >= datetime.combine(start_date, time.min),
                MarketData.timestamp <= datetime.combine(end_date, time.max),
            )
        )
        return int(result.scalar() or 0)

    @classmethod
    def _estimated_candle_count(cls, timeframe_minutes: int, start_date: date, end_date: date) -> int:
        total_days = max((end_date - start_date).days, 1)
        total_minutes = total_days * 24 * 60
        return max(int(total_minutes / max(timeframe_minutes, 1)), 1)

    @classmethod
    async def quote_backtest_cost(
        cls,
        db: AsyncSession,
        *,
        timeframe: str,
        start_date: date,
        end_date: date,
        instrument_id: int | None = None,
        strategy_parameters: dict[str, Any] | None = None,
        premium_multiplier: Decimal | float | int = Decimal("1.00"),
        use_actual_candle_count: bool = False,
        plan_code: str | None = None,
        candle_count_override: int | None = None,
        candle_count_mode_override: str | None = None,
    ) -> dict[str, Any]:
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        rules = await cls.get_active_pricing_config(db)

        range_days = max((end_date - start_date).days, 1)
        timeframe_minutes = cls._timeframe_minutes(timeframe)
        date_range_multiplier = cls._pick_tier_multiplier(range_days, rules["date_range_buckets"], "max_days")
        timeframe_multiplier = cls._pick_tier_multiplier(timeframe_minutes, rules["timeframe_multipliers"], "max_minutes")

        if candle_count_override is not None:
            candle_count = max(int(candle_count_override or 0), 0)
            candle_count_mode = str(candle_count_mode_override or "override")
        elif use_actual_candle_count and instrument_id is not None:
            candle_count = await cls._actual_candle_count(db, instrument_id, timeframe, start_date, end_date)
            candle_count_mode = "actual"
        else:
            candle_count = cls._estimated_candle_count(timeframe_minutes, start_date, end_date)
            candle_count_mode = "estimated"

        volume_multiplier = Decimal("1.00")
        complexity_multiplier, complexity_details = cls._complexity_multiplier_from_rules(
            strategy_parameters,
            enabled=bool(rules.get("strategy_complexity_enabled", False)),
            step=Decimal(str(rules.get("strategy_complexity_step", 0) or 0)),
            cap=Decimal(str(rules.get("strategy_complexity_cap", 0) or 0)),
        )

        premium = Decimal(str(premium_multiplier or 1)).quantize(Decimal("0.01"))
        if premium <= 0:
            premium = Decimal("1.00")

        plan_discounts = rules.get("plan_discounts") or {}
        plan_discount = Decimal("0")
        if plan_code and isinstance(plan_discounts, dict):
            plan_discount = Decimal(str(plan_discounts.get(str(plan_code).upper(), 0) or 0)).quantize(Decimal("0.0001"))
            if plan_discount < 0:
                plan_discount = Decimal("0")
            if plan_discount > Decimal("0.95"):
                plan_discount = Decimal("0.95")

        discount_multiplier = Decimal("1.00") - plan_discount
        if discount_multiplier <= 0:
            discount_multiplier = Decimal("1.00")

        raw_cost = (
            Decimal(str(rules["base_cost"]))
            * date_range_multiplier
            * timeframe_multiplier
            * volume_multiplier
            * complexity_multiplier
            * premium
            * discount_multiplier
        )

        rounded = int(raw_cost.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        min_charge = int(rules.get("min_credit_charge") or 1)
        max_charge = rules.get("max_credit_charge")
        if rounded < min_charge:
            rounded = min_charge
        if max_charge is not None and rounded > int(max_charge):
            rounded = int(max_charge)
        total_cost = max(1, rounded)

        return {
            "total_cost": total_cost,
            "breakdown": {
                "pricing_version": str(rules.get("version") or cls.PRICING_VERSION),
                "rule_set_id": rules.get("id"),
                "rule_set_name": rules.get("name"),
                "date_range_days": range_days,
                "timeframe": timeframe,
                "timeframe_minutes": timeframe_minutes,
                "candle_count": candle_count,
                "candle_count_mode": candle_count_mode,
                "base_cost": float(Decimal(str(rules["base_cost"]))),
                "min_credit_charge": min_charge,
                "max_credit_charge": int(max_charge) if max_charge is not None else None,
                "multipliers": {
                    "date_range": float(date_range_multiplier),
                    "timeframe": float(timeframe_multiplier),
                    "volume": float(volume_multiplier),
                    "complexity": float(complexity_multiplier),
                    "premium": float(premium),
                    "plan_discount": float(plan_discount),
                    "discount_multiplier": float(discount_multiplier),
                },
                "complexity": complexity_details,
                "date_range_buckets": rules.get("date_range_buckets"),
                "timeframe_buckets": rules.get("timeframe_multipliers"),
                "plan_code": plan_code,
            },
        }
