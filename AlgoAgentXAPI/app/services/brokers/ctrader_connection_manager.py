"""Persistent cTrader Open API JSON/WebSocket sessions.

The latency-sensitive worker owns this manager.  There is one socket per
environment (DEMO/LIVE), one receive coroutine per socket, and all request
responses are routed by ``clientMsgId``.  REST/API processes do not import or
own these sessions; they continue to use the legacy adapter unless the event
pipeline explicitly routes an order through Redis to the market worker.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable

from ...core.config import settings

logger = logging.getLogger(__name__)

CTRADER_DEMO_WS = "wss://demo.ctraderapi.com:5036"
CTRADER_LIVE_WS = "wss://live.ctraderapi.com:5036"

PT_APPLICATION_AUTH_REQ = 2100
PT_APPLICATION_AUTH_RES = 2101
PT_ACCOUNT_AUTH_REQ = 2102
PT_ACCOUNT_AUTH_RES = 2103
PT_NEW_ORDER_REQ = 2106
PT_CLOSE_POSITION_REQ = 2111
PT_SYMBOLS_LIST_REQ = 2114
PT_SYMBOLS_LIST_RES = 2115
PT_SYMBOL_BY_ID_REQ = 2116
PT_SYMBOL_BY_ID_RES = 2117
PT_TRADER_REQ = 2121
PT_TRADER_RES = 2122
PT_RECONCILE_REQ = 2124
PT_RECONCILE_RES = 2125
PT_EXECUTION_EVENT = 2126
PT_SUBSCRIBE_SPOTS_REQ = 2127
PT_SUBSCRIBE_SPOTS_RES = 2128
PT_SPOT_EVENT = 2131
PT_ORDER_ERROR_EVENT = 2132
PT_SUBSCRIBE_LIVE_TRENDBAR_REQ = 2135
PT_UNSUBSCRIBE_LIVE_TRENDBAR_REQ = 2136
PT_GET_TRENDBARS_REQ = 2137
PT_GET_TRENDBARS_RES = 2138
PT_ERROR_RES = 2142
PT_SUBSCRIBE_LIVE_TRENDBAR_RES = 2165
PT_UNSUBSCRIBE_LIVE_TRENDBAR_RES = 2166
PT_ACCOUNT_DISCONNECT_EVENT = 2164
PT_ACCOUNTS_TOKEN_INVALIDATED_EVENT = 2147
PT_GET_POSITION_UNREALIZED_PNL_REQ = 2187
PT_GET_POSITION_UNREALIZED_PNL_RES = 2188
PT_COMMON_ERROR_RES = 50
PT_HEARTBEAT_EVENT = 51

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]
ReconnectHandler = Callable[[bool], Awaitable[None] | None]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _error_message(message: dict[str, Any]) -> str:
    payload = message.get("payload") if isinstance(message, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    code = payload.get("errorCode") or payload.get("code") or message.get("errorCode")
    description = payload.get("description") or payload.get("errorDescription") or payload.get("message")
    return " - ".join(str(item) for item in (code, description) if item not in (None, "")) or "Unknown cTrader Open API error"


async def _maybe_await(value: Any) -> None:
    if inspect.isawaitable(value):
        await value


@dataclass
class _PendingRequest:
    future: asyncio.Future
    expected_types: set[int]
    account_id: int | None = None
    trade: bool = False
    client_order_id: str | None = None
    accepted_payload: dict[str, Any] | None = None
    on_sent: EventHandler | None = None
    on_ack: EventHandler | None = None
    on_fill: EventHandler | None = None
    callback_tasks: list[asyncio.Task] = field(default_factory=list)


@dataclass(frozen=True)
class TrendbarSubscription:
    account_id: int
    symbol_id: int
    period: int


@dataclass
class ConnectionHealth:
    environment: str
    state: str = "STOPPED"
    connected_at: datetime | None = None
    last_rx_at: datetime | None = None
    last_tx_at: datetime | None = None
    last_heartbeat_sent_at: datetime | None = None
    last_heartbeat_received_at: datetime | None = None
    reconnect_count: int = 0
    last_connection_error: str | None = None

    def to_dict(self, *, pending_requests: int, authorized_accounts: int, subscriptions: int) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "state": self.state,
            "connected": self.state == "CONNECTED",
            "connected_at": _iso(self.connected_at),
            "last_rx_at": _iso(self.last_rx_at),
            "last_tx_at": _iso(self.last_tx_at),
            "last_heartbeat_sent_at": _iso(self.last_heartbeat_sent_at),
            "last_heartbeat_received_at": _iso(self.last_heartbeat_received_at),
            "reconnect_count": self.reconnect_count,
            "last_connection_error": self.last_connection_error,
            "pending_requests": pending_requests,
            "authorized_accounts": authorized_accounts,
            "trendbar_subscriptions": subscriptions,
        }


class PersistentCTraderConnection:
    """One resilient cTrader socket for one broker environment."""

    _BACKOFF_SECONDS = (1, 2, 5, 10, 20, 30)

    def __init__(
        self,
        *,
        environment: str,
        client_id: str,
        client_secret: str,
        request_timeout: float | None = None,
        heartbeat_seconds: float | None = None,
    ) -> None:
        environment = str(environment or "DEMO").strip().upper()
        if environment not in {"DEMO", "LIVE"}:
            raise ValueError("cTrader environment must be DEMO or LIVE")
        if not str(client_id or "").strip() or not str(client_secret or "").strip():
            raise ValueError("cTrader application client id/secret are required")

        self.environment = environment
        self.url = CTRADER_LIVE_WS if environment == "LIVE" else CTRADER_DEMO_WS
        self._client_id = str(client_id).strip()
        self._client_secret = str(client_secret).strip()
        self.credential_fingerprint = hashlib.sha256(f"{self._client_id}\0{self._client_secret}".encode()).hexdigest()
        self.request_timeout = float(request_timeout or settings.ctrader_request_timeout_seconds)
        self.heartbeat_seconds = max(2.0, float(heartbeat_seconds or settings.ctrader_heartbeat_seconds))

        self._ws: Any = None
        self._supervisor_task: asyncio.Task | None = None
        self._sender_task: asyncio.Task | None = None
        self._receiver_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._pending: dict[str, _PendingRequest] = {}
        self._pending_by_client_order_id: dict[str, str] = {}
        self._pending_lock = asyncio.Lock()
        self._socket_ready = asyncio.Event()
        self._connected = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._start_lock = asyncio.Lock()

        # Account tokens never leave this process or appear in health payloads.
        # Desired account tokens and authorization state are deliberately
        # separate.  A rejected/failed auth request must never be mistaken for
        # a successfully authorized account on the next call.
        self._account_tokens: dict[int, str] = {}
        self._authorized_accounts: set[int] = set()
        self._account_auth_locks: dict[int, asyncio.Lock] = {}
        self._spot_subscriptions: dict[int, set[int]] = {}
        self._trendbar_subscriptions: set[TrendbarSubscription] = set()
        self._active_spot_subscriptions: set[tuple[int, int]] = set()
        self._active_trendbar_subscriptions: set[TrendbarSubscription] = set()
        self._subscription_locks: dict[tuple[int, int, int], asyncio.Lock] = {}
        self._event_handlers: dict[int, list[EventHandler]] = {}
        self._reconnect_handlers: list[ReconnectHandler] = []
        self._symbol_cache: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
        self.health = ConnectionHealth(environment=environment)

    async def start(self) -> None:
        async with self._start_lock:
            if self._supervisor_task and not self._supervisor_task.done():
                await self.wait_until_connected()
                return
            self._stop_event.clear()
            self.health.state = "CONNECTING"
            self._supervisor_task = asyncio.create_task(
                self._supervise(), name=f"ctrader-{self.environment.lower()}-supervisor"
            )
        await self.wait_until_connected()

    async def stop(self) -> None:
        self._stop_event.set()
        self._connected.clear()
        self._socket_ready.clear()
        self.health.state = "STOPPING"
        tasks = [self._heartbeat_task, self._sender_task, self._receiver_task, self._supervisor_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        await asyncio.gather(*(task for task in tasks if task), return_exceptions=True)
        await self._fail_all_pending(RuntimeError("cTrader connection stopped"))
        self.health.state = "STOPPED"

    async def wait_until_connected(self, timeout: float | None = None) -> None:
        await asyncio.wait_for(self._connected.wait(), timeout=timeout or self.request_timeout + 5)

    def add_event_handler(self, payload_type: int, handler: EventHandler) -> None:
        handlers = self._event_handlers.setdefault(int(payload_type), [])
        if handler not in handlers:
            handlers.append(handler)

    def remove_event_handler(self, payload_type: int, handler: EventHandler) -> None:
        handlers = self._event_handlers.get(int(payload_type), [])
        if handler in handlers:
            handlers.remove(handler)

    def add_reconnect_handler(self, handler: ReconnectHandler) -> None:
        if handler not in self._reconnect_handlers:
            self._reconnect_handlers.append(handler)

    async def request(
        self,
        payload_type: int,
        payload: dict[str, Any],
        expected_type: int | Iterable[int],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        await self.wait_until_connected(timeout=timeout)
        return await self._request_connected(payload_type, payload, expected_type, timeout=timeout)

    async def _request_connected(
        self,
        payload_type: int,
        payload: dict[str, Any],
        expected_type: int | Iterable[int],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        await asyncio.wait_for(self._socket_ready.wait(), timeout=timeout or self.request_timeout)
        expected_types = {int(expected_type)} if isinstance(expected_type, int) else {int(item) for item in expected_type}
        client_msg_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        async with self._pending_lock:
            account_value = payload.get("ctidTraderAccountId")
            account_id = int(account_value) if account_value not in (None, "") else None
            self._pending[client_msg_id] = _PendingRequest(future=future, expected_types=expected_types, account_id=account_id)
        await self._send_queue.put({
            "clientMsgId": client_msg_id,
            "payloadType": int(payload_type),
            "payload": payload,
        })
        try:
            result = await asyncio.wait_for(asyncio.shield(future), timeout=timeout or self.request_timeout)
            return result if isinstance(result, dict) else {}
        finally:
            async with self._pending_lock:
                self._pending.pop(client_msg_id, None)

    async def submit_trade(
        self,
        *,
        payload_type: int,
        payload: dict[str, Any],
        timeout: float | None = None,
        on_sent: EventHandler | None = None,
        on_ack: EventHandler | None = None,
        on_fill: EventHandler | None = None,
    ) -> dict[str, Any]:
        await self.wait_until_connected(timeout=timeout)
        client_msg_id = str(uuid.uuid4())
        client_order_id = str(payload.get("clientOrderId") or payload.get("label") or "").strip() or None
        future = asyncio.get_running_loop().create_future()
        pending = _PendingRequest(
            future=future,
            expected_types={PT_EXECUTION_EVENT, PT_ORDER_ERROR_EVENT},
            account_id=int(payload["ctidTraderAccountId"]),
            trade=True,
            client_order_id=client_order_id,
            on_sent=on_sent,
            on_ack=on_ack,
            on_fill=on_fill,
        )
        async with self._pending_lock:
            self._pending[client_msg_id] = pending
            if client_order_id:
                self._pending_by_client_order_id[client_order_id] = client_msg_id
        await self._send_queue.put({
            "clientMsgId": client_msg_id,
            "payloadType": int(payload_type),
            "payload": payload,
        })
        try:
            result = await asyncio.wait_for(
                asyncio.shield(future), timeout=timeout or settings.ctrader_order_timeout_seconds
            )
            if pending.callback_tasks:
                await asyncio.gather(*pending.callback_tasks)
            return result if isinstance(result, dict) else {}
        except asyncio.TimeoutError:
            if pending.accepted_payload is not None:
                accepted = dict(pending.accepted_payload)
                accepted["_accepted_timeout"] = True
                return accepted
            raise TimeoutError("Timed out waiting for cTrader order acknowledgement/fill")
        finally:
            async with self._pending_lock:
                self._pending.pop(client_msg_id, None)
                if client_order_id:
                    self._pending_by_client_order_id.pop(client_order_id, None)

    async def authorize_account(self, account_id: int, access_token: str) -> dict[str, Any]:
        numeric_id = int(account_id)
        token = str(access_token or "").strip()
        if not token:
            raise ValueError("cTrader account access token is required")
        lock = self._account_auth_locks.setdefault(numeric_id, asyncio.Lock())
        async with lock:
            if (
                self._account_tokens.get(numeric_id) == token
                and numeric_id in self._authorized_accounts
                and self._connected.is_set()
            ):
                return {"alreadyAuthorized": True, "ctidTraderAccountId": numeric_id}
            self._account_tokens[numeric_id] = token
            try:
                response = await self.request(
                    PT_ACCOUNT_AUTH_REQ,
                    {"ctidTraderAccountId": numeric_id, "accessToken": token},
                    PT_ACCOUNT_AUTH_RES,
                )
            except Exception:
                self._authorized_accounts.discard(numeric_id)
                raise
            self._authorized_accounts.add(numeric_id)
            return response

    async def subscribe_spots(self, account_id: int, symbol_ids: Iterable[int]) -> dict[str, Any]:
        numeric_id = int(account_id)
        symbols = {int(symbol_id) for symbol_id in symbol_ids}
        if not symbols:
            return {}
        current = self._spot_subscriptions.setdefault(numeric_id, set())
        current.update(symbols)
        result: dict[str, Any] = {}
        for symbol_id in sorted(symbols):
            lock = self._subscription_locks.setdefault((numeric_id, symbol_id, 0), asyncio.Lock())
            async with lock:
                if (numeric_id, symbol_id) in self._active_spot_subscriptions:
                    continue
                result = await self.request(
                    PT_SUBSCRIBE_SPOTS_REQ,
                    {
                        "ctidTraderAccountId": numeric_id,
                        "symbolId": [symbol_id],
                        "subscribeToSpotTimestamp": True,
                    },
                    PT_SUBSCRIBE_SPOTS_RES,
                )
                self._active_spot_subscriptions.add((numeric_id, symbol_id))
        return result

    async def subscribe_live_trendbar(self, account_id: int, symbol_id: int, period: int) -> dict[str, Any]:
        subscription = TrendbarSubscription(int(account_id), int(symbol_id), int(period))
        self._trendbar_subscriptions.add(subscription)
        lock = self._subscription_locks.setdefault(
            (subscription.account_id, subscription.symbol_id, subscription.period), asyncio.Lock()
        )
        async with lock:
            if subscription in self._active_trendbar_subscriptions:
                return {}
            response = await self.request(
                PT_SUBSCRIBE_LIVE_TRENDBAR_REQ,
                {
                    "ctidTraderAccountId": subscription.account_id,
                    "symbolId": subscription.symbol_id,
                    "period": subscription.period,
                },
                PT_SUBSCRIBE_LIVE_TRENDBAR_RES,
            )
            self._active_trendbar_subscriptions.add(subscription)
            return response

    async def unsubscribe_live_trendbar(self, account_id: int, symbol_id: int, period: int) -> None:
        subscription = TrendbarSubscription(int(account_id), int(symbol_id), int(period))
        self._trendbar_subscriptions.discard(subscription)
        self._active_trendbar_subscriptions.discard(subscription)
        if self._connected.is_set():
            await self.request(
                PT_UNSUBSCRIBE_LIVE_TRENDBAR_REQ,
                {
                    "ctidTraderAccountId": subscription.account_id,
                    "symbolId": subscription.symbol_id,
                    "period": subscription.period,
                },
                PT_UNSUBSCRIBE_LIVE_TRENDBAR_RES,
            )

    async def get_trendbars(self, payload: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
        return await self.request(PT_GET_TRENDBARS_REQ, payload, PT_GET_TRENDBARS_RES, timeout=timeout)

    async def get_symbols(self, account_id: int) -> dict[str, Any]:
        return await self.request(
            PT_SYMBOLS_LIST_REQ,
            {"ctidTraderAccountId": int(account_id), "includeArchivedSymbols": False},
            PT_SYMBOLS_LIST_RES,
        )

    async def get_full_symbol(self, account_id: int, symbol_id: int) -> dict[str, Any]:
        key = (int(account_id), int(symbol_id))
        cached = self._symbol_cache.get(key)
        now = asyncio.get_running_loop().time()
        if cached and cached[0] > now:
            return cached[1]
        payload = await self.request(
            PT_SYMBOL_BY_ID_REQ,
            {"ctidTraderAccountId": int(account_id), "symbolId": [int(symbol_id)]},
            PT_SYMBOL_BY_ID_RES,
        )
        self._symbol_cache[key] = (
            now + max(30, int(settings.ctrader_metadata_cache_seconds)),
            payload,
        )
        return payload

    async def reconcile(self, account_id: int) -> dict[str, Any]:
        return await self.request(
            PT_RECONCILE_REQ,
            {"ctidTraderAccountId": int(account_id), "returnProtectionOrders": False},
            PT_RECONCILE_RES,
        )

    async def get_trader(self, account_id: int) -> dict[str, Any]:
        return await self.request(
            PT_TRADER_REQ,
            {"ctidTraderAccountId": int(account_id)},
            PT_TRADER_RES,
        )

    async def get_position_unrealized_pnl(self, account_id: int) -> dict[str, Any]:
        return await self.request(
            PT_GET_POSITION_UNREALIZED_PNL_REQ,
            {"ctidTraderAccountId": int(account_id)},
            PT_GET_POSITION_UNREALIZED_PNL_RES,
        )

    def health_payload(self) -> dict[str, Any]:
        return self.health.to_dict(
            pending_requests=len(self._pending),
            authorized_accounts=len(self._authorized_accounts),
            subscriptions=len(self._trendbar_subscriptions),
        )

    async def _connect_websocket(self) -> Any:
        try:
            from websockets.asyncio.client import connect
        except Exception:
            from websockets import connect
        return await asyncio.wait_for(
            connect(self.url, ping_interval=None, close_timeout=5, max_queue=4096),
            timeout=self.request_timeout,
        )

    async def _supervise(self) -> None:
        attempt = 0
        ever_connected = False
        while not self._stop_event.is_set():
            try:
                self.health.state = "CONNECTING" if not ever_connected else "RECONNECTING"
                self._ws = await self._connect_websocket()
                self._socket_ready.set()
                self._sender_task = asyncio.create_task(self._sender_loop(), name=f"ctrader-{self.environment.lower()}-sender")
                self._receiver_task = asyncio.create_task(self._receiver_loop(), name=f"ctrader-{self.environment.lower()}-receiver")
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name=f"ctrader-{self.environment.lower()}-heartbeat")

                await self._request_connected(
                    PT_APPLICATION_AUTH_REQ,
                    {"clientId": self._client_id, "clientSecret": self._client_secret},
                    PT_APPLICATION_AUTH_RES,
                )
                is_reconnect = ever_connected
                if is_reconnect:
                    self.health.reconnect_count += 1
                    self._symbol_cache.clear()
                await self._restore_registry()
                self._connected.set()
                self.health.state = "CONNECTED"
                self.health.connected_at = utc_now()
                self.health.last_connection_error = None
                for handler in tuple(self._reconnect_handlers):
                    try:
                        await _maybe_await(handler(is_reconnect))
                    except Exception:
                        logger.exception("cTrader %s reconnect handler failed", self.environment)
                ever_connected = True
                attempt = 0

                active_io = [task for task in (self._sender_task, self._receiver_task, self._heartbeat_task) if task]
                done, _ = await asyncio.wait(active_io, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    if task.exception() is not None:
                        raise task.exception()
                raise ConnectionError("cTrader send/receive/heartbeat loop stopped")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self.health.last_connection_error = str(exc)[:500]
                self.health.state = "RECONNECTING"
                logger.warning("cTrader %s connection lost: %s", self.environment, exc)
            finally:
                self._connected.clear()
                self._socket_ready.clear()
                for task in (self._sender_task, self._receiver_task, self._heartbeat_task):
                    if task and not task.done():
                        task.cancel()
                await asyncio.gather(
                    *(task for task in (self._sender_task, self._receiver_task, self._heartbeat_task) if task),
                    return_exceptions=True,
                )
                self._sender_task = self._receiver_task = self._heartbeat_task = None
                if self._ws is not None:
                    try:
                        await self._ws.close()
                    except Exception:
                        pass
                    self._ws = None
                self._authorized_accounts.clear()
                self._active_spot_subscriptions.clear()
                self._active_trendbar_subscriptions.clear()
                await self._fail_all_pending(ConnectionError("cTrader connection interrupted; request can be retried idempotently"))
                self._drain_send_queue()

            if self._stop_event.is_set():
                break
            delay = self._BACKOFF_SECONDS[min(attempt, len(self._BACKOFF_SECONDS) - 1)]
            attempt += 1
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
        self.health.state = "STOPPED"

    async def _restore_registry(self) -> None:
        self._authorized_accounts.clear()
        self._active_spot_subscriptions.clear()
        self._active_trendbar_subscriptions.clear()
        for account_id, token in tuple(self._account_tokens.items()):
            await self._request_connected(
                PT_ACCOUNT_AUTH_REQ,
                {"ctidTraderAccountId": account_id, "accessToken": token},
                PT_ACCOUNT_AUTH_RES,
            )
            self._authorized_accounts.add(account_id)
        for account_id, symbol_ids in tuple(self._spot_subscriptions.items()):
            if symbol_ids:
                await self._request_connected(
                    PT_SUBSCRIBE_SPOTS_REQ,
                    {
                        "ctidTraderAccountId": account_id,
                        "symbolId": sorted(symbol_ids),
                        "subscribeToSpotTimestamp": True,
                    },
                    PT_SUBSCRIBE_SPOTS_RES,
                )
                self._active_spot_subscriptions.update((account_id, symbol_id) for symbol_id in symbol_ids)
        for subscription in tuple(self._trendbar_subscriptions):
            await self._request_connected(
                PT_SUBSCRIBE_LIVE_TRENDBAR_REQ,
                {
                    "ctidTraderAccountId": subscription.account_id,
                    "symbolId": subscription.symbol_id,
                    "period": subscription.period,
                },
                PT_SUBSCRIBE_LIVE_TRENDBAR_RES,
            )
            self._active_trendbar_subscriptions.add(subscription)

    async def _sender_loop(self) -> None:
        while not self._stop_event.is_set():
            message = await self._send_queue.get()
            try:
                if self._ws is None:
                    raise ConnectionError("cTrader socket is unavailable")
                pending = None
                client_msg_id = str(message.get("clientMsgId") or "")
                if client_msg_id:
                    async with self._pending_lock:
                        pending = self._pending.get(client_msg_id)
                await self._ws.send(json.dumps(message, separators=(",", ":")))
                sent_at = utc_now()
                self.health.last_tx_at = sent_at
                if pending is not None and pending.on_sent is not None:
                    pending.callback_tasks.append(asyncio.create_task(
                        _maybe_await(pending.on_sent({"sent_at": sent_at.isoformat()}))
                    ))
            finally:
                self._send_queue.task_done()

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self.heartbeat_seconds)
            if self._ws is None:
                continue
            await self._send_queue.put({"clientMsgId": str(uuid.uuid4()), "payloadType": PT_HEARTBEAT_EVENT, "payload": {}})
            self.health.last_heartbeat_sent_at = utc_now()

    async def _receiver_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._ws is None:
                raise ConnectionError("cTrader socket is unavailable")
            raw = await self._ws.recv()
            self.health.last_rx_at = utc_now()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                message = json.loads(raw)
            except Exception:
                logger.warning("Ignored invalid cTrader JSON frame")
                continue
            if not isinstance(message, dict):
                continue
            payload_type = int(message.get("payloadType") or 0)
            if payload_type == PT_HEARTBEAT_EVENT:
                self.health.last_heartbeat_received_at = utc_now()
                continue
            if payload_type == PT_ACCOUNT_DISCONNECT_EVENT:
                payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
                account_id = payload.get("ctidTraderAccountId")
                if account_id not in (None, ""):
                    self._authorized_accounts.discard(int(account_id))
                self.health.last_connection_error = "cTrader account session disconnected; pending re-authorization"
            elif payload_type == PT_ACCOUNTS_TOKEN_INVALIDATED_EVENT:
                payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
                for account_id in payload.get("ctidTraderAccountIds") or []:
                    self._authorized_accounts.discard(int(account_id))
                    self._account_tokens.pop(int(account_id), None)
                self.health.last_connection_error = "cTrader access token invalidated; reconnect account credentials"
            await self._route_message(
                {**message, "_received_at": self.health.last_rx_at.isoformat()},
                payload_type,
            )

    async def _route_message(self, message: dict[str, Any], payload_type: int) -> None:
        payload = message.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        client_msg_id = str(message.get("clientMsgId") or "").strip() or None
        pending: _PendingRequest | None = None
        pending_id = client_msg_id

        async with self._pending_lock:
            if client_msg_id:
                pending = self._pending.get(client_msg_id)
            if pending is None and payload_type in {PT_EXECUTION_EVENT, PT_ORDER_ERROR_EVENT}:
                client_order_id = self._extract_client_order_id(payload)
                pending_id = self._pending_by_client_order_id.get(client_order_id or "")
                pending = self._pending.get(pending_id or "")
            if pending is None and not client_msg_id:
                account_value = payload.get("ctidTraderAccountId")
                account_id = int(account_value) if account_value not in (None, "") else None
                candidates = [
                    (candidate_id, candidate)
                    for candidate_id, candidate in self._pending.items()
                    if payload_type in candidate.expected_types
                    and (account_id is None or candidate.account_id in (None, account_id))
                ]
                if len(candidates) == 1:
                    pending_id, pending = candidates[0]

        if pending is not None:
            if payload_type in {PT_ERROR_RES, PT_COMMON_ERROR_RES, PT_ORDER_ERROR_EVENT}:
                if not pending.future.done():
                    pending.future.set_exception(ValueError(_error_message(message)))
            elif pending.trade and payload_type == PT_EXECUTION_EVENT:
                received_at = self.health.last_rx_at or utc_now()
                await self._route_trade_payload(
                    pending,
                    {**payload, "_received_at": received_at.isoformat()},
                )
            elif payload_type in pending.expected_types and not pending.future.done():
                pending.future.set_result(payload)

        # Execution, spot and trendbar messages are also state events. Handlers
        # observe them even when they completed a correlated request.
        for handler in tuple(self._event_handlers.get(payload_type, ())):
            try:
                await _maybe_await(handler({**message, "payload": payload}))
            except Exception:
                logger.exception("cTrader %s event handler failed for payload %s", self.environment, payload_type)

    async def _route_trade_payload(self, pending: _PendingRequest, payload: dict[str, Any]) -> None:
        execution_type = int(payload.get("executionType") or 0)
        if execution_type == 7 or payload.get("errorCode"):
            if not pending.future.done():
                code = payload.get("errorCode") or "ORDER_REJECTED"
                description = payload.get("description") or "cTrader rejected the order"
                pending.future.set_exception(ValueError(f"{code}: {description}"))
            return
        if execution_type == 2:
            pending.accepted_payload = dict(payload)
            if pending.on_ack:
                pending.callback_tasks.append(asyncio.create_task(_maybe_await(pending.on_ack(payload))))
            return
        if execution_type in {5, 6, 8}:
            if not pending.future.done():
                pending.future.set_exception(ValueError(f"cTrader order ended with executionType={execution_type}"))
            return
        if execution_type in {3, 11}:
            if pending.on_ack and pending.accepted_payload is None:
                pending.callback_tasks.append(asyncio.create_task(_maybe_await(pending.on_ack(payload))))
            if execution_type == 3 and pending.on_fill:
                pending.callback_tasks.append(asyncio.create_task(_maybe_await(pending.on_fill(payload))))
            if execution_type == 11:
                pending.accepted_payload = dict(payload)
                return
            if not pending.future.done():
                pending.future.set_result(payload)

    @staticmethod
    def _extract_client_order_id(payload: dict[str, Any]) -> str | None:
        order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
        trade_data = order.get("tradeData") if isinstance(order.get("tradeData"), dict) else {}
        value = order.get("clientOrderId") or trade_data.get("label") or payload.get("clientOrderId")
        return str(value) if value not in (None, "") else None

    async def _fail_all_pending(self, exc: Exception) -> None:
        async with self._pending_lock:
            pending = list(self._pending.values())
            self._pending.clear()
            self._pending_by_client_order_id.clear()
        for request in pending:
            if not request.future.done():
                request.future.set_exception(exc)

    def _drain_send_queue(self) -> None:
        while True:
            try:
                self._send_queue.get_nowait()
                self._send_queue.task_done()
            except asyncio.QueueEmpty:
                return


class CTraderConnectionManager:
    """Own the single DEMO and single LIVE persistent cTrader sessions."""

    def __init__(self) -> None:
        self._connections: dict[str, PersistentCTraderConnection] = {}
        self._lock = asyncio.Lock()

    async def get_connection(
        self,
        *,
        environment: str,
        client_id: str,
        client_secret: str,
    ) -> PersistentCTraderConnection:
        env = str(environment or "DEMO").strip().upper()
        fingerprint = hashlib.sha256(f"{str(client_id).strip()}\0{str(client_secret).strip()}".encode()).hexdigest()
        async with self._lock:
            connection = self._connections.get(env)
            if connection is None:
                connection = PersistentCTraderConnection(
                    environment=env,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                self._connections[env] = connection
            elif connection.credential_fingerprint != fingerprint:
                raise RuntimeError(
                    f"The {env} cTrader persistent session is already bound to a different Open API application. "
                    "All active accounts in one environment must use the same cTrader application credentials."
                )
        await connection.start()
        return connection

    def connection(self, environment: str) -> PersistentCTraderConnection | None:
        return self._connections.get(str(environment or "DEMO").strip().upper())

    def health(self) -> dict[str, Any]:
        return {
            env: connection.health_payload()
            for env, connection in sorted(self._connections.items())
        }

    async def stop(self) -> None:
        connections = list(self._connections.values())
        self._connections.clear()
        await asyncio.gather(*(connection.stop() for connection in connections), return_exceptions=True)


ctrader_connection_manager = CTraderConnectionManager()
