from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass
class BrokerConnectionResult:
    connected: bool
    message: str
    account_login: Optional[str] = None
    server: Optional[str] = None
    balance: Optional[Decimal] = None
    equity: Optional[Decimal] = None
    currency: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerOrderRequest:
    symbol: str
    side: str
    qty: Decimal
    order_type: str = "MARKET"
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    deviation: int = 20
    comment: str = "AlgoAgentX Demo"


@dataclass
class BrokerOrderResult:
    success: bool
    status: str
    message: str
    broker_order_id: Optional[str] = None
    executed_price: Optional[Decimal] = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class BrokerAdapter:
    async def test_connection(self) -> BrokerConnectionResult:
        raise NotImplementedError

    async def get_account_info(self) -> dict[str, Any]:
        raise NotImplementedError

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        raise NotImplementedError

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        raise NotImplementedError

    async def get_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def get_orders(self) -> list[dict[str, Any]]:
        raise NotImplementedError
