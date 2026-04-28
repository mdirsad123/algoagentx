from __future__ import annotations

from ...db.models import BrokerAccount
from .base import BrokerAdapter
from .mt5 import MT5Adapter
from .upstox import UpstoxAdapter


def get_broker_code(broker_account: BrokerAccount) -> str:
    provider = getattr(broker_account, "broker_provider", None)
    return str(
        getattr(provider, "code", None)
        or getattr(broker_account, "broker_code", None)
        or getattr(broker_account, "broker_name", None)
        or "MT5"
    ).upper().strip()


def get_broker_adapter(broker_account: BrokerAccount) -> BrokerAdapter:
    broker_code = get_broker_code(broker_account)
    if broker_code == "MT5":
        return MT5Adapter(broker_account)
    if broker_code == "UPSTOX":
        return UpstoxAdapter(broker_account)
    raise ValueError(f"Unsupported broker adapter: {broker_code}")
