from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount
from .base import BrokerAdapter
from .mt5 import MT5Adapter
from .mt5_agent import MT5AgentAdapter
from .upstox import UpstoxAdapter
from .crypto_api import CryptoApiAdapter, CRYPTO_BROKERS


def get_broker_code(broker_account: BrokerAccount) -> str:
    provider = getattr(broker_account, "broker_provider", None)
    return str(
        getattr(provider, "code", None)
        or getattr(broker_account, "broker_code", None)
        or getattr(broker_account, "broker_name", None)
        or "MT5"
    ).upper().strip()


def get_broker_adapter(broker_account: BrokerAccount, db: AsyncSession | None = None) -> BrokerAdapter:
    broker_code = get_broker_code(broker_account)
    if broker_code == "MT5":
        if str(getattr(settings, "mt5_execution_mode", "AGENT") or "AGENT").upper() == "LOCAL":
            return MT5Adapter(broker_account)
        return MT5AgentAdapter(broker_account, db)
    if broker_code == "UPSTOX":
        return UpstoxAdapter(broker_account)
    if broker_code in CRYPTO_BROKERS:
        return CryptoApiAdapter(broker_account)
    raise ValueError(f"Unsupported broker adapter: {broker_code}")
