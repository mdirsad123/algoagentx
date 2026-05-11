from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, MT5Agent, MT5AgentCommand
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult

FRIENDLY_DISCONNECTED = "MT5 Agent is not connected. Please start AlgoAgentX MT5 Agent on your Windows PC or VPS."


def _is_fresh(agent: MT5Agent | None) -> bool:
    if not agent or agent.status != "CONNECTED" or not agent.last_heartbeat_at:
        return False
    last = agent.last_heartbeat_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last <= timedelta(seconds=int(settings.mt5_agent_heartbeat_stale_seconds or 90))


class MT5AgentAdapter(BrokerAdapter):
    def __init__(self, broker_account: BrokerAccount, db: AsyncSession | None = None):
        self.broker_account = broker_account
        self.db = db

    async def _latest_agent(self) -> MT5Agent | None:
        if self.db is None:
            return None
        return (await self.db.execute(
            select(MT5Agent)
            .where(MT5Agent.broker_account_id == self.broker_account.id)
            .order_by(MT5Agent.last_heartbeat_at.desc().nullslast(), MT5Agent.created_at.desc())
        )).scalars().first()

    async def test_connection(self) -> BrokerConnectionResult:
        agent = await self._latest_agent()
        if not _is_fresh(agent):
            return BrokerConnectionResult(False, FRIENDLY_DISCONNECTED, raw={"execution_mode": "AGENT", "agent_status": getattr(agent, "status", None)})
        terminal_ok = str(agent.terminal_status or "").upper() in {"CONNECTED", "OK", "READY", "TERMINAL_CONNECTED"}
        if not terminal_ok:
            return BrokerConnectionResult(False, "MT5 terminal is not connected inside the AlgoAgentX MT5 Agent.", account_login=agent.mt5_account_login, server=agent.server_name, balance=agent.balance, equity=agent.equity, currency=agent.currency, raw={"terminal_status": agent.terminal_status})
        return BrokerConnectionResult(True, "MT5 Agent connected and terminal is ready.", account_login=agent.mt5_account_login, server=agent.server_name, balance=agent.balance, equity=agent.equity, currency=agent.currency, raw={"execution_mode": "AGENT", "agent_id": str(agent.id), "algo_trading_enabled": agent.algo_trading_enabled})

    async def get_account_info(self) -> dict[str, Any]:
        result = await self.test_connection()
        return {"connected": result.connected, "message": result.message, "account_login": result.account_login, "server": result.server, "balance": str(result.balance) if result.balance is not None else None, "equity": str(result.equity) if result.equity is not None else None, "currency": result.currency, "raw": result.raw}

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return {"success": False, "message": "MT5 Agent quote streaming is prepared but not enabled in this phase.", "symbol": symbol}

    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        agent = await self._latest_agent()
        if not _is_fresh(agent):
            return BrokerOrderResult(False, "ERROR", FRIENDLY_DISCONNECTED, raw_response={"execution_mode": "AGENT"})
        payload = {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "qty": str(order_request.qty),
            "order_type": order_request.order_type,
            "price": str(order_request.price) if order_request.price is not None else None,
            "stop_loss": str(order_request.stop_loss) if order_request.stop_loss is not None else None,
            "target": str(order_request.target) if order_request.target is not None else None,
            "deviation": order_request.deviation,
            "comment": order_request.comment,
            "max_lot": str(order_request.max_lot) if order_request.max_lot is not None else None,
        }
        command = MT5AgentCommand(agent_id=agent.id, user_id=self.broker_account.user_id, broker_account_id=self.broker_account.id, command_type="PLACE_ORDER", status="PENDING", request_payload=payload)
        self.db.add(command)
        await self.db.flush()
        return BrokerOrderResult(True, "PLACED", "MT5 order command queued for AlgoAgentX MT5 Agent.", broker_order_id=str(command.id), raw_response={"agent_command_id": str(command.id), "execution_mode": "AGENT"})

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        return await self.place_market_order(BrokerOrderRequest(symbol=position_id_or_symbol, side=side, qty=qty, comment="AlgoAgentX MT5 Agent close"))

    async def get_positions(self) -> list[dict[str, Any]]:
        agent = await self._latest_agent()
        meta = agent.metadata_json if agent else {}
        positions = meta.get("positions") if isinstance(meta, dict) else None
        return positions if isinstance(positions, list) else []

    async def get_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        return []

    async def get_symbols(self, query: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return []
