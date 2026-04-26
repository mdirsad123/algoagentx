from __future__ import annotations

from ...db.models import BrokerAccount
from .base import BrokerAdapter
from .mt5 import MT5Adapter


def get_broker_adapter(broker_account: BrokerAccount) -> BrokerAdapter:
    broker_name = (broker_account.broker_name or "MT5").upper()
    if broker_name == "MT5":
        return MT5Adapter(broker_account)
    raise ValueError(f"Unsupported broker adapter: {broker_account.broker_name}")
