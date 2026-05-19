from __future__ import annotations

import asyncio
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
            "client_order_id": order_request.idempotency_key or order_request.tag,
            "idempotency_key": order_request.idempotency_key or order_request.tag,
        }
        if order_request.idempotency_key:
            existing = (await self.db.execute(
                select(MT5AgentCommand)
                .where(MT5AgentCommand.command_type == "PLACE_ORDER")
                .where(MT5AgentCommand.request_payload["idempotency_key"].astext == order_request.idempotency_key)
                .order_by(MT5AgentCommand.created_at.desc())
            )).scalars().first()
            if existing is not None:
                return BrokerOrderResult(
                    True,
                    "PLACED",
                    "Duplicate MT5 command blocked by idempotency key; returning existing command.",
                    broker_order_id=str(existing.id),
                    raw_response={"agent_command_id": str(existing.id), "execution_mode": "AGENT", "idempotency_key": order_request.idempotency_key, "duplicate_command": True},
                )
        command = MT5AgentCommand(agent_id=agent.id, user_id=self.broker_account.user_id, broker_account_id=self.broker_account.id, command_type="PLACE_ORDER", status="PENDING", request_payload=payload)
        self.db.add(command)
        await self.db.flush()
        return BrokerOrderResult(True, "PLACED", "MT5 order command queued for AlgoAgentX MT5 Agent.", broker_order_id=str(command.id), raw_response={"agent_command_id": str(command.id), "execution_mode": "AGENT"})

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        return await self.place_market_order(BrokerOrderRequest(symbol=position_id_or_symbol, side=side, qty=qty, comment="AlgoAgentX MT5 Agent close"))

    async def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        agent = await self._latest_agent()
        meta = agent.metadata_json if agent else {}
        positions = meta.get("positions") if isinstance(meta, dict) else None
        rows = positions if isinstance(positions, list) else []
        if not symbol:
            return [row for row in rows if isinstance(row, dict)]

        def normalize(value: object) -> str:
            return str(value or "").strip().upper().replace(".", "").replace("_", "").replace("-", "")

        requested = normalize(symbol)
        if not requested:
            return [row for row in rows if isinstance(row, dict)]

        filtered: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            candidates = [
                row.get("symbol"),
                row.get("broker_symbol"),
                row.get("instrument"),
                row.get("instrument_key"),
                row.get("tradingsymbol"),
            ]
            if any((actual := normalize(candidate)) and (actual == requested or actual.startswith(requested) or requested.startswith(actual)) for candidate in candidates):
                filtered.append(row)
        return filtered

    async def get_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        if self.db is None:
            raise RuntimeError("MT5 Agent database session is not available for candle requests.")

        agent = await self._latest_agent()
        if not _is_fresh(agent):
            raise RuntimeError(FRIENDLY_DISCONNECTED)

        safe_count = max(1, min(int(count or 300), 2000))
        requested_timeframe = str(timeframe or "").strip().upper()
        payload = {
            "symbol": str(symbol or "").strip(),
            "timeframe": requested_timeframe,
            "count": safe_count,
            "skip_forming": True,
        }
        if not payload["symbol"]:
            raise RuntimeError("MT5 Agent candle request requires a symbol.")
        if not payload["timeframe"]:
            raise RuntimeError("MT5 Agent candle request requires a timeframe.")

        command = MT5AgentCommand(
            agent_id=agent.id,
            user_id=self.broker_account.user_id,
            broker_account_id=self.broker_account.id,
            command_type="FETCH_RATES",
            status="PENDING",
            request_payload=payload,
        )
        self.db.add(command)
        await self.db.flush()
        # Commit so the Windows MT5 Agent, which polls using a separate request/session,
        # can see the command immediately. The caller continues with a clean transaction.
        await self.db.commit()

        timeout_seconds = 30
        for _ in range(timeout_seconds):
            await asyncio.sleep(1)
            await self.db.refresh(command)
            status = str(command.status or "").upper()
            if status == "COMPLETED":
                result = command.result_payload or {}
                candles = self._extract_candles_from_result(result)
                return [row for row in candles if isinstance(row, dict)]
            if status == "ERROR":
                result = command.result_payload or {}
                message = command.error_message or result.get("message") or (result.get("raw_response") or {}).get("message")
                raise RuntimeError(str(message or "MT5 Agent candle fetch failed."))

        command.status = "TIMEOUT"
        command.error_message = "MT5 Agent candle request timed out. Check agent is running and polling commands."
        await self.db.commit()
        raise RuntimeError(command.error_message)

    @staticmethod
    def _extract_candles_from_result(result_payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(result_payload, dict):
            return []
        direct = result_payload.get("candles")
        if isinstance(direct, list):
            return direct
        raw_response = result_payload.get("raw_response")
        if isinstance(raw_response, dict):
            raw_candles = raw_response.get("candles")
            if isinstance(raw_candles, list):
                return raw_candles
            nested_raw = raw_response.get("raw")
            if isinstance(nested_raw, dict) and isinstance(nested_raw.get("candles"), list):
                return nested_raw["candles"]
        raw = result_payload.get("raw")
        if isinstance(raw, dict) and isinstance(raw.get("candles"), list):
            return raw["candles"]
        return []


    @staticmethod
    def _extract_raw_response(result_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result_payload, dict):
            return {}
        raw_response = result_payload.get("raw_response")
        if isinstance(raw_response, dict):
            return raw_response
        raw = result_payload.get("raw")
        if isinstance(raw, dict):
            return raw
        return result_payload

    async def get_deals_pnl(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, Any]:
        if self.db is None:
            raise RuntimeError("MT5 Agent database session is not available for PnL requests.")

        agent = await self._latest_agent()
        if not _is_fresh(agent):
            raise RuntimeError(FRIENDLY_DISCONNECTED)

        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
        safe_since = since or today_start
        safe_until = until or now
        payload = {
            "symbol": str(symbol or "").strip() or None,
            "since": safe_since.isoformat(),
            "until": safe_until.isoformat(),
            "magic": 260510,
            "comment_prefix": "AlgoAgentX",
            "allow_symbol_only_fallback": True,
        }
        command = MT5AgentCommand(
            agent_id=agent.id,
            user_id=self.broker_account.user_id,
            broker_account_id=self.broker_account.id,
            command_type="FETCH_DEALS_PNL",
            status="PENDING",
            request_payload=payload,
        )
        self.db.add(command)
        await self.db.flush()
        await self.db.commit()

        timeout_seconds = 30
        for _ in range(timeout_seconds):
            await asyncio.sleep(1)
            await self.db.refresh(command)
            status = str(command.status or "").upper()
            if status == "COMPLETED":
                result = command.result_payload or {}
                raw = self._extract_raw_response(result)
                return self._normalize_deals_pnl(raw)
            if status == "ERROR":
                result = command.result_payload or {}
                raw = self._extract_raw_response(result)
                message = command.error_message or result.get("message") or raw.get("message")
                raise RuntimeError(str(message or "MT5 Agent deals PnL fetch failed."))

        command.status = "TIMEOUT"
        command.error_message = "MT5 Agent PnL request timed out. Check agent is running and polling commands."
        await self.db.commit()
        raise RuntimeError(command.error_message)

    @staticmethod
    def _normalize_deals_pnl(raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raw = {}
        # The agent may send the values directly or inside raw_response/raw.
        nested = raw.get("raw") if isinstance(raw.get("raw"), dict) else None
        source = nested or raw
        realized = source.get("realized_pnl", source.get("net_profit", "0"))
        gross_profit = source.get("gross_profit", "0")
        commission = source.get("commission", "0")
        swap = source.get("swap", "0")
        fee = source.get("fee", "0")
        deals = source.get("deals") if isinstance(source.get("deals"), list) else []
        return {
            "success": bool(source.get("success", True)),
            "realized_pnl": str(realized or "0"),
            "net_profit": str(source.get("net_profit", realized or "0")),
            "gross_profit": str(gross_profit or "0"),
            "commission": str(commission or "0"),
            "swap": str(swap or "0"),
            "fee": str(fee or "0"),
            "deal_count": int(source.get("deal_count") or len(deals) or 0),
            "currency": source.get("currency") or raw.get("currency"),
            "deals": deals,
        }

    async def get_symbols(self, query: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return []
