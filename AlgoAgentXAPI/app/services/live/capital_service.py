from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from ...db.models import BrokerAccount, StrategyDeployment


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _positive_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = _decimal(value)
    return parsed if parsed > 0 else None


def _flatten_account_sources(broker_account: BrokerAccount | None, broker_metrics: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    if isinstance(broker_metrics, dict):
        account_info = broker_metrics.get("account_info")
        if isinstance(account_info, dict):
            sources.append(account_info)
        sources.append(broker_metrics)

    meta = getattr(broker_account, "metadata_json", None) or {}
    if isinstance(meta, dict):
        for key in (
            "account_info",
            "last_test",
            "selected_account",
            "mt5_selected_account",
            "ctrader_selected_account",
            "upstox_account_info",
        ):
            value = meta.get(key)
            if isinstance(value, dict):
                sources.append(value)
        raw = meta.get("raw")
        if isinstance(raw, dict):
            sources.append(raw)

    return sources


@dataclass(frozen=True)
class EffectiveTradingCapital:
    effective_capital: Decimal
    effective_capital_source: str
    balance: Decimal | None = None
    equity: Decimal | None = None
    free_margin: Decimal | None = None
    account_currency: str | None = None


def get_effective_trading_capital(
    deployment: StrategyDeployment,
    broker_account: BrokerAccount | None = None,
    broker_metrics: dict[str, Any] | None = None,
) -> EffectiveTradingCapital:
    """Resolve live-trading capital from broker account state first.

    Priority:
    1. Broker equity
    2. Broker balance
    3. Broker free margin
    4. Existing deployment.capital fallback for backward compatibility
    """
    equity: Decimal | None = None
    balance: Decimal | None = None
    free_margin: Decimal | None = None
    currency: str | None = None

    for source in _flatten_account_sources(broker_account, broker_metrics):
        if equity is None:
            equity = _positive_decimal(source.get("equity") or source.get("netEquity") or source.get("account_equity"))
        if balance is None:
            balance = _positive_decimal(source.get("balance") or source.get("cash") or source.get("account_balance"))
        if free_margin is None:
            free_margin = _positive_decimal(source.get("free_margin") or source.get("freeMargin") or source.get("margin_free"))
        if not currency:
            raw_currency = source.get("currency") or source.get("account_currency")
            if raw_currency:
                currency = str(raw_currency).upper()

    if equity is not None:
        return EffectiveTradingCapital(equity, "BROKER_EQUITY", balance=balance, equity=equity, free_margin=free_margin, account_currency=currency)
    if balance is not None:
        return EffectiveTradingCapital(balance, "BROKER_BALANCE", balance=balance, equity=equity, free_margin=free_margin, account_currency=currency)
    if free_margin is not None:
        return EffectiveTradingCapital(free_margin, "BROKER_FREE_MARGIN", balance=balance, equity=equity, free_margin=free_margin, account_currency=currency)

    fallback = _positive_decimal(getattr(deployment, "capital", None)) or Decimal("100000")
    return EffectiveTradingCapital(fallback, "FALLBACK_DEPLOYMENT_CAPITAL", balance=balance, equity=equity, free_margin=free_margin, account_currency=currency)
