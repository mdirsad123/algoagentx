from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..backtest_service import BacktestService
from ..backtest_advanced_filters import apply_advanced_filters
from ..billing.credit_cost_service import CreditCostService
from ..credits.management import CreditManagementService


def _json_safe(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


async def build_funded_credit_quote(
    db: AsyncSession,
    *,
    payload: Any,
    instrument: Any,
    user_id: str,
) -> tuple[dict[str, Any], Any]:
    """Quote a funded simulation with the same PAY-BILL candle rule as Standard Backtest.

    Billing is based on the actual selected candle scope after the same advanced-filter
    path used by a backtest run. This helper never debits credits; the funded run
    endpoint performs the authoritative subscription-then-wallet debit.
    """
    market_df = await BacktestService._fetch_market_data(
        db,
        payload.instrument_id,
        payload.timeframe,
        payload.start_date,
        payload.end_date,
    )
    if market_df.empty:
        raise ValueError(
            f"No market data available for {getattr(instrument, 'symbol', payload.instrument_id)} "
            f"{payload.timeframe} in selected range."
        )

    symbol = str(getattr(instrument, "symbol", "") or payload.instrument_id)
    market = str(
        getattr(instrument, "market", None)
        or getattr(instrument, "asset_class", None)
        or getattr(instrument, "instrument_type", None)
        or ""
    )
    _, filter_impact = apply_advanced_filters(
        market_df,
        payload.advanced_filters,
        timeframe=payload.timeframe,
        instrument_symbol=symbol,
        instrument_market=market,
    )

    candles_before = int(filter_impact.get("total_candles_before_filter") or len(market_df))
    billable_candles = int(filter_impact.get("total_candles_after_filter") or 0)
    candles_removed = int(
        filter_impact.get("candles_removed")
        or max(candles_before - billable_candles, 0)
    )

    estimate = await CreditCostService.calculate_backtest_credit_cost(
        db,
        user_id=str(user_id),
        instrument_id=payload.instrument_id,
        instrument=symbol,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
        candle_count=billable_candles,
        advanced_filters=payload.advanced_filters,
    )
    capacity = await CreditManagementService.get_credit_capacity(
        db,
        str(user_id),
        for_update=False,
    )

    total_available = int(capacity.get("total_available") or 0)
    credit_cost = int(estimate.get("credit_cost") or estimate.get("total_cost") or 0)
    has_enough = total_available >= credit_cost
    data_valid = billable_candles > 0

    return {
        "credit_policy": "STANDARD_BACKTEST_CANDLE_PRICING",
        "credit_cost": credit_cost,
        "estimated_run_cost": credit_cost,
        "candles_before_filters": candles_before,
        "billable_candles": billable_candles,
        "candles_removed": candles_removed,
        "advanced_filters": _json_safe(filter_impact),
        "pricing_rule": estimate.get("pricing_rule")
        or (estimate.get("breakdown") or {}).get("rule_set_name"),
        "breakdown": _json_safe(estimate.get("breakdown") or {}),
        "has_enough_credits": has_enough,
        "can_run": bool(has_enough and data_valid),
        "subscription_state": capacity.get("subscription_state"),
        "deduction_order": ["subscription", "wallet"],
        "balances": {
            "included_balance": int(capacity.get("included_balance") or 0),
            "wallet_balance": int(capacity.get("wallet_balance") or 0),
            "total_available": total_available,
            "balance_after_run": max(total_available - credit_cost, 0)
            if has_enough
            else total_available,
        },
    }, market_df
