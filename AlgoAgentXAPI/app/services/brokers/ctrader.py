from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ...core.config import settings
from ...db.models import BrokerAccount
from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult

DEFAULT_CTRADER_AUTH_URL = "https://openapi.ctrader.com/apps/auth"
DEFAULT_CTRADER_TOKEN_URL = "https://openapi.ctrader.com/apps/token"
DEFAULT_CTRADER_DEMO_WS = "wss://demo.ctraderapi.com:5036"
DEFAULT_CTRADER_LIVE_WS = "wss://live.ctraderapi.com:5036"

# cTrader Open API payload types used by AlgoAgentX.
PT_APPLICATION_AUTH_REQ = 2100
PT_APPLICATION_AUTH_RES = 2101
PT_ACCOUNT_AUTH_REQ = 2102
PT_ACCOUNT_AUTH_RES = 2103
PT_NEW_ORDER_REQ = 2106
PT_CLOSE_POSITION_REQ = 2111
PT_ASSET_LIST_REQ = 2112
PT_ASSET_LIST_RES = 2113
PT_SYMBOLS_LIST_REQ = 2114
PT_SYMBOLS_LIST_RES = 2115
PT_SYMBOL_BY_ID_REQ = 2116
PT_SYMBOL_BY_ID_RES = 2117
PT_TRADER_REQ = 2121
PT_TRADER_RES = 2122
PT_RECONCILE_REQ = 2124
PT_RECONCILE_RES = 2125
PT_EXECUTION_EVENT = 2126
PT_ERROR_RES = 2142
PT_GET_ACCOUNTS_REQ = 2149
PT_GET_ACCOUNTS_RES = 2150
PT_SUBSCRIBE_SPOTS_REQ = 2127
PT_SUBSCRIBE_SPOTS_RES = 2128
PT_SPOT_EVENT = 2131
PT_ORDER_ERROR_EVENT = 2132
PT_GET_TRENDBARS_REQ = 2137
PT_GET_TRENDBARS_RES = 2138
PT_GET_POSITION_UNREALIZED_PNL_REQ = 2187
PT_GET_POSITION_UNREALIZED_PNL_RES = 2188
PT_COMMON_ERROR_RES = 50
PT_HEARTBEAT_EVENT = 51


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
        return payload if isinstance(payload, dict) else {"raw": payload}
    except Exception:
        return {"text": response.text[:500]}


def _without_secret(payload: dict[str, Any]) -> dict[str, Any]:
    blocked = {"accessToken", "access_token", "refreshToken", "refresh_token", "client_secret", "secret"}
    return {k: ("***" if k in blocked else v) for k, v in (payload or {}).items()}




def _coerce_number(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return value


def _first_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload.get(key) not in (None, ""):
            return payload.get(key)
    return None


def _safe_ctrader_sync_error(exc: Exception | str) -> str:
    text = str(exc or "").strip()
    lower = text.lower()
    if "401" in lower or "unauthorized" in lower or "token" in lower and "expired" in lower:
        return "cTrader token expired. Please reconnect cTrader and try again."
    if "404" in lower or "not found" in lower:
        return "cTrader account sync endpoint is not available. OAuth is connected; configure a cTrader Open API sync bridge or run the next transport phase."
    if "timeout" in lower:
        return "cTrader API is not responding. Please try again later."
    if "connection" in lower or "temporarily" in lower:
        return "cTrader API is temporarily unavailable. Please try again later."
    return text or "cTrader account sync failed."

def _money_value(value: Any, money_digits: Any = 0) -> float | None:
    """Decode cTrader monetary integers using moneyDigits."""
    if value in (None, ""):
        return None
    try:
        digits = max(0, int(money_digits or 0))
        return float(Decimal(str(value)) / (Decimal(10) ** digits))
    except Exception:
        return None


def _safe_oauth_error(payload: dict[str, Any], status_code: int | None = None) -> str:
    raw_error = str(payload.get("error") or payload.get("errorCode") or payload.get("code") or "").lower()
    raw_description = str(payload.get("error_description") or payload.get("description") or payload.get("message") or payload.get("text") or "")
    combined = f"{raw_error} {raw_description}".lower()
    if "invalid_client" in combined or "unauthorized" in combined:
        return "Invalid cTrader Client ID or Client Secret. Please verify your cTrader Open API application credentials."
    if "redirect" in combined or "invalid_redirect_uri" in combined:
        return "Redirect URI mismatch. Use the exact Redirect URI shown in AlgoAgentX inside your cTrader Open API application."
    if "expired" in combined or "invalid_grant" in combined:
        return "The cTrader authorization code expired. Please reconnect and approve the OAuth request again."
    if "access_denied" in combined or "denied" in combined:
        return "cTrader authorization was denied. Please approve access to connect your account."
    if status_code and status_code >= 500:
        return "cTrader OAuth service is temporarily unavailable. Please try again later."
    return raw_description or raw_error or "cTrader token exchange failed. Please check your credentials and redirect URI."



class _CTraderJsonWsClient:
    """Minimal cTrader Open API JSON/WebSocket transport.

    cTrader exposes JSON on port 5036. This helper keeps the FastAPI adapter
    asyncio-native and avoids the old, unconfigured REST bridge placeholders.
    """

    def __init__(self, *, is_live: bool, timeout: float = 15.0):
        self.url = DEFAULT_CTRADER_LIVE_WS if is_live else DEFAULT_CTRADER_DEMO_WS
        self.timeout = timeout
        self._ws = None

    async def __aenter__(self):
        try:
            from websockets.asyncio.client import connect
        except Exception:
            try:
                from websockets import connect
            except Exception as exc:
                raise RuntimeError(
                    "Python package 'websockets' is required for cTrader Open API JSON transport."
                ) from exc
        self._ws = await asyncio.wait_for(connect(self.url, ping_interval=20, ping_timeout=20), timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    @staticmethod
    def _error_message(message: dict[str, Any]) -> str:
        payload = message.get("payload") if isinstance(message, dict) else {}
        payload = payload if isinstance(payload, dict) else {}
        code = payload.get("errorCode") or payload.get("code") or message.get("errorCode")
        description = payload.get("description") or payload.get("errorDescription") or payload.get("message")
        text = " - ".join(str(x) for x in (code, description) if x not in (None, ""))
        return text or "Unknown cTrader Open API error"

    async def request(self, payload_type: int, payload: dict[str, Any], expected_type: int) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("cTrader transport is not connected")
        client_msg_id = str(uuid.uuid4())
        message = {"clientMsgId": client_msg_id, "payloadType": payload_type, "payload": payload}
        await self._ws.send(json.dumps(message, separators=(",", ":")))
        deadline = asyncio.get_running_loop().time() + self.timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for cTrader payload type {expected_type}")
            raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                incoming = json.loads(raw)
            except Exception:
                continue
            if not isinstance(incoming, dict):
                continue
            incoming_type = incoming.get("payloadType")
            if incoming_type in {PT_ERROR_RES, PT_COMMON_ERROR_RES}:
                raise ValueError(self._error_message(incoming))
            if incoming_type == PT_HEARTBEAT_EVENT:
                continue
            # cTrader normally echoes clientMsgId. Matching expected payload type is
            # also accepted because some server messages omit the id.
            if incoming_type == expected_type and (not incoming.get("clientMsgId") or incoming.get("clientMsgId") == client_msg_id):
                payload_obj = incoming.get("payload")
                return payload_obj if isinstance(payload_obj, dict) else {}


    async def receive_payload(self, expected_type: int, timeout: float | None = None) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("cTrader transport is not connected")
        deadline = asyncio.get_running_loop().time() + (timeout or self.timeout)
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for cTrader payload type {expected_type}")
            raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                incoming = json.loads(raw)
            except Exception:
                continue
            if not isinstance(incoming, dict):
                continue
            incoming_type = int(incoming.get("payloadType") or 0)
            if incoming_type in {PT_ERROR_RES, PT_COMMON_ERROR_RES}:
                raise ValueError(self._error_message(incoming))
            if incoming_type == PT_HEARTBEAT_EVENT:
                continue
            if incoming_type != expected_type:
                continue
            payload = incoming.get("payload")
            return payload if isinstance(payload, dict) else {}


class CTraderAdapter(BrokerAdapter):
    """cTrader Open API adapter.

    OAuth is handled over HTTPS while account discovery/account data/symbols use
    cTrader's official cloud JSON WebSocket transport on port 5036. MT5 remains
    completely separate and unchanged.
    """

    def __init__(self, broker_account: Optional[BrokerAccount] = None):
        self.broker_account = broker_account

    @staticmethod
    def _clean(value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _client_id(self) -> Optional[str]:
        return self._clean(getattr(self.broker_account, "oauth_client_id", None)) or self._clean(settings.ctrader_client_id)

    def _client_secret(self) -> Optional[str]:
        account_secret = decrypt_credential(getattr(self.broker_account, "encrypted_client_secret", None)) if self.broker_account else None
        return self._clean(account_secret) or self._clean(settings.ctrader_client_secret)

    def _redirect_uri(self) -> Optional[str]:
        return self._clean(getattr(self.broker_account, "oauth_redirect_uri", None)) or self._clean(settings.ctrader_redirect_uri)

    def _authorize_url(self) -> str:
        return self._clean(getattr(settings, "ctrader_oauth_authorize_url", None)) or DEFAULT_CTRADER_AUTH_URL

    def _token_url(self) -> str:
        return self._clean(getattr(settings, "ctrader_oauth_token_url", None)) or DEFAULT_CTRADER_TOKEN_URL

    def validate_config(self) -> None:
        missing: list[str] = []
        if not self._client_id():
            missing.append("client_id / CTRADER_CLIENT_ID")
        if not self._client_secret():
            missing.append("client_secret / CTRADER_CLIENT_SECRET")
        if not self._redirect_uri():
            missing.append("redirect_uri / CTRADER_REDIRECT_URI")
        if missing:
            raise ValueError(f"Missing cTrader OAuth config: {', '.join(missing)}")

    def build_login_url(self, state: str, scope: str = "trading") -> str:
        self.validate_config()
        # cTrader's documented granting-access URL accepts client_id,
        # redirect_uri, scope and optional product=web. It returns `code` to
        # redirect_uri but does not reliably echo arbitrary OAuth `state`.
        # AlgoAgentX keeps `state` server-side and binds it to the initiating
        # browser using a short-lived HttpOnly callback cookie.
        query = urlencode({
            "client_id": self._client_id(),
            "redirect_uri": self._redirect_uri(),
            "scope": scope,
            "product": "web",
        })
        return f"{self._authorize_url()}?{query}"

    async def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        self.validate_config()
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri(),
            "client_id": self._client_id(),
            "client_secret": self._client_secret(),
        }

        def _call() -> dict[str, Any]:
            response = requests.get(self._token_url(), params=params, timeout=30)
            payload = _safe_json(response)
            access_token = payload.get("accessToken") or payload.get("access_token")
            if response.status_code >= 400 or not access_token:
                raise ValueError(_safe_oauth_error(payload, response.status_code))
            return payload

        return await asyncio.to_thread(_call)

    async def refresh_access_token(self) -> dict[str, Any]:
        if not self.broker_account:
            raise ValueError("cTrader broker account is required for token refresh.")
        refresh_token = decrypt_credential(getattr(self.broker_account, "encrypted_refresh_token", None))
        if not refresh_token:
            raise ValueError("cTrader refresh token is missing. Please reconnect cTrader.")
        self.validate_config()
        params = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._client_id(),
            "client_secret": self._client_secret(),
        }

        def _call() -> dict[str, Any]:
            response = requests.get(self._token_url(), params=params, timeout=30)
            payload = _safe_json(response)
            access_token = payload.get("accessToken") or payload.get("access_token")
            if response.status_code >= 400 or not access_token:
                raise ValueError(_safe_oauth_error(payload, response.status_code))
            return payload

        return await asyncio.to_thread(_call)

    @staticmethod
    def token_expiry_from_payload(payload: dict[str, Any]) -> Optional[datetime]:
        raw = payload.get("expiresIn") or payload.get("expires_in")
        try:
            return datetime.now(timezone.utc) + timedelta(seconds=int(raw)) if raw else None
        except Exception:
            return None

    def _access_token(self) -> Optional[str]:
        if not self.broker_account:
            return None
        return decrypt_credential(getattr(self.broker_account, "encrypted_token", None))

    def _accounts_url(self) -> Optional[str]:
        return self._clean(getattr(settings, "ctrader_accounts_url", None))

    def _account_info_url(self) -> Optional[str]:
        return self._clean(getattr(settings, "ctrader_account_info_url", None))

    def _symbols_url(self) -> Optional[str]:
        return self._clean(getattr(settings, "ctrader_symbols_url", None))

    def _auth_headers(self) -> dict[str, str]:
        token = self._access_token()
        return {"Accept": "application/json", "Authorization": f"Bearer {token}"} if token else {"Accept": "application/json"}

    @staticmethod
    def _unwrap_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("accounts", "tradingAccounts", "traderAccounts", "data", "items", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = CTraderAdapter._unwrap_list(value)
                if nested:
                    return nested
        return []

    @staticmethod
    def normalize_account(item: dict[str, Any]) -> dict[str, Any]:
        account_id = _first_value(item, "ctidTraderAccountId", "accountId", "id", "traderAccountId")
        login = _first_value(item, "accountNumber", "login", "accountLogin", "accountNo", "traderLogin", "accountId", "ctidTraderAccountId")
        return {
            "ctrader_account_id": str(account_id) if account_id is not None else None,
            "account_number": str(login) if login is not None else None,
            "broker_name": _first_value(item, "brokerName", "broker", "brokerTitle", "brokerTitleShort", "whiteLabelName"),
            "account_type": str(_first_value(item, "accountType", "environment", "type") or "").upper() or None,
            "balance": _coerce_number(_first_value(item, "balance", "cash", "deposit")),
            "equity": _coerce_number(_first_value(item, "equity", "netEquity")),
            "margin": _coerce_number(_first_value(item, "margin", "usedMargin")),
            "free_margin": _coerce_number(_first_value(item, "freeMargin", "free_margin")),
            "currency": _first_value(item, "currency", "depositCurrency", "moneyDigitsCurrency"),
            "leverage": _first_value(item, "leverage", "preciseLeverage"),
            "raw": _without_secret(item),
        }

    @staticmethod
    def normalize_symbol(item: dict[str, Any]) -> dict[str, Any]:
        symbol_id = _first_value(item, "symbolId", "id", "symbol_id")
        name = _first_value(item, "symbolName", "name", "symbol", "tradingSymbol")
        return {
            "symbol_id": str(symbol_id) if symbol_id is not None else None,
            "symbol_name": str(name or symbol_id or "").upper(),
            "base_asset": _first_value(item, "baseAsset", "baseAssetName", "base", "baseCurrency"),
            "quote_asset": _first_value(item, "quoteAsset", "quoteAssetName", "quote", "quoteCurrency"),
            "pip_size": _coerce_number(_first_value(item, "pipSize", "pip_size")),
            "tick_size": _coerce_number(_first_value(item, "tickSize", "tick_size")),
            "min_volume": _coerce_number(_first_value(item, "minVolume", "min_volume", "volumeMin")),
            "max_volume": _coerce_number(_first_value(item, "maxVolume", "max_volume", "volumeMax")),
            "volume_step": _coerce_number(_first_value(item, "stepVolume", "volumeStep", "volume_step")),
            "raw": _without_secret(item),
        }


    @staticmethod
    def _as_decimal(value: Any, field_name: str) -> Decimal:
        try:
            dec = Decimal(str(value))
        except Exception as exc:
            raise ValueError(f"Invalid {field_name}.") from exc
        if dec <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")
        return dec

    @staticmethod
    def _safe_order_error(exc: Exception | str) -> str:
        text = str(exc or "").strip()
        lower = text.lower()
        if "live" in lower:
            return "cTrader live order execution is disabled in this phase."
        if "token" in lower or "401" in lower or "unauthorized" in lower:
            return "cTrader token expired or unauthorized. Please reconnect cTrader and try again."
        if "symbol" in lower:
            return text or "Invalid cTrader symbol mapping. Sync symbols and try again."
        if "volume" in lower or "quantity" in lower:
            return text or "Invalid cTrader order volume."
        if "permission" in lower or "scope" in lower or "not_authorized" in lower or "not authorized" in lower or "no_trading" in lower:
            return "cTrader trading permission is missing. Reconnect cTrader and approve Trading access, then Sync again."
        if "not configured" in lower or "bridge" in lower:
            return "cTrader native order transport is unavailable. Reconnect cTrader with Trading permission and try again."
        if "timeout" in lower:
            return "cTrader order API timed out. Please try again later."
        if "connection" in lower or "temporarily" in lower:
            return "cTrader order API is temporarily unavailable. Please try again later."
        return text or "cTrader demo order failed."

    def _demo_order_url(self) -> Optional[str]:
        return self._clean(getattr(settings, "ctrader_demo_order_url", None))

    @staticmethod
    def validate_demo_mode(selected_account: dict[str, Any] | None) -> None:
        mode = str((selected_account or {}).get("account_type") or settings.ctrader_env or "demo").upper()
        if "LIVE" in mode or mode == "REAL":
            raise ValueError("cTrader live order execution is disabled in this phase.")

    @staticmethod
    def validate_volume_against_symbol(volume: Decimal, symbol_meta: dict[str, Any] | None) -> None:
        if not symbol_meta:
            return
        def _dec(value: Any) -> Decimal | None:
            if value in (None, ""):
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None
        min_v = _dec(symbol_meta.get("min_volume") or symbol_meta.get("volume_min"))
        max_v = _dec(symbol_meta.get("max_volume") or symbol_meta.get("volume_max"))
        step = _dec(symbol_meta.get("volume_step") or symbol_meta.get("step_volume"))
        if min_v is not None and volume < min_v:
            raise ValueError(f"Volume is below cTrader minimum volume {min_v} for this symbol.")
        if max_v is not None and volume > max_v:
            raise ValueError(f"Volume is above cTrader maximum volume {max_v} for this symbol.")
        if step is not None and step > 0 and min_v is not None:
            remainder = (volume - min_v) % step
            if remainder != 0:
                raise ValueError(f"Volume must follow cTrader step {step} for this symbol.")

    async def place_demo_market_order(
        self,
        *,
        selected_account: dict[str, Any],
        symbol_meta: dict[str, Any] | None,
        symbol: str,
        side: str,
        volume: Any,
        entry_price: Any = None,
        stop_loss: Any = None,
        take_profit: Any = None,
        client_order_id: str | None = None,
        comment: str | None = None,
    ) -> BrokerOrderResult:
        """Place a cTrader DEMO market order using the native Open API transport.

        AlgoAgentX's live engine supplies `volume` as lots for MT5/cTrader.
        cTrader requires volume in 0.01 units, so the symbol's full `lotSize`
        is fetched and used for an exact conversion.
        """
        try:
            self.validate_demo_mode(selected_account)
            token = self._access_token()
            if not token:
                return BrokerOrderResult(False, "FAILED", "cTrader OAuth token is missing. Please reconnect cTrader.", raw_response={"provider": "CTRADER"})

            trading_enabled = selected_account.get("trading_enabled")
            if trading_enabled is False:
                return BrokerOrderResult(
                    False,
                    "REJECTED",
                    "cTrader trading permission is missing. Reconnect cTrader and approve Trading access, then Sync again.",
                    raw_response={"provider": "CTRADER", "permission_scope": selected_account.get("permission_scope")},
                )

            clean_symbol = str(symbol or "").strip().upper()
            clean_side = str(side or "").strip().upper()
            if not clean_symbol:
                raise ValueError("Symbol is required.")
            if clean_side not in {"BUY", "SELL"}:
                raise ValueError("Side must be BUY or SELL.")
            lots = self._as_decimal(volume, "volume")

            account_id = selected_account.get("ctrader_account_id") or selected_account.get("account_number")
            if not account_id:
                raise ValueError("Selected cTrader account does not contain an account id.")
            numeric_id = int(account_id)

            if not symbol_meta or not (symbol_meta.get("symbol_id") or symbol_meta.get("id")):
                symbol_meta = await self._resolve_symbol_meta(clean_symbol)
            symbol_id = int(symbol_meta.get("symbol_id") or symbol_meta.get("id"))

            is_live, discovered = await self._resolve_account_environment(str(account_id))
            if is_live:
                raise ValueError("cTrader live order execution is disabled in this phase.")

            client = await self._openapi_authorized_client(is_live=False)
            try:
                await client.request(
                    PT_ACCOUNT_AUTH_REQ,
                    {"ctidTraderAccountId": numeric_id, "accessToken": token},
                    PT_ACCOUNT_AUTH_RES,
                )
                full_symbol = await self._fetch_full_symbol_with_client(client, numeric_id, symbol_id)
                protocol_volume = self._lots_to_protocol_volume(lots, full_symbol)

                payload: dict[str, Any] = {
                    "ctidTraderAccountId": numeric_id,
                    "symbolId": symbol_id,
                    "orderType": 1,  # MARKET
                    "tradeSide": 1 if clean_side == "BUY" else 2,
                    "volume": protocol_volume,
                }
                if client_order_id:
                    payload["clientOrderId"] = str(client_order_id)[:50]
                    payload["label"] = str(client_order_id)[:100]
                if comment:
                    payload["comment"] = str(comment)[:512]

                # cTrader does not allow absolute SL/TP in a MARKET request.
                # Preserve the strategy's intended distance by using relative protection.
                entry = Decimal(str(entry_price)) if entry_price not in (None, "") else None
                if stop_loss not in (None, ""):
                    if entry is None or entry <= 0:
                        raise ValueError("Entry price is required to attach cTrader market-order stop loss.")
                    distance = abs(entry - Decimal(str(stop_loss)))
                    rel = int((distance * Decimal("100000")).to_integral_value(rounding=ROUND_DOWN))
                    if rel > 0:
                        payload["relativeStopLoss"] = rel
                if take_profit not in (None, ""):
                    if entry is None or entry <= 0:
                        raise ValueError("Entry price is required to attach cTrader market-order take profit.")
                    distance = abs(Decimal(str(take_profit)) - entry)
                    rel = int((distance * Decimal("100000")).to_integral_value(rounding=ROUND_DOWN))
                    if rel > 0:
                        payload["relativeTakeProfit"] = rel

                execution = await self._send_trade_request(
                    client,
                    payload_type=PT_NEW_ORDER_REQ,
                    payload=payload,
                    timeout=12.0,
                )
            finally:
                await client.__aexit__(None, None, None)

            order = execution.get("order") if isinstance(execution.get("order"), dict) else {}
            deal = execution.get("deal") if isinstance(execution.get("deal"), dict) else {}
            order_id, position_id = self._execution_ids(execution)
            position = execution.get("position") if isinstance(execution.get("position"), dict) else {}
            executed_price = deal.get("executionPrice") or order.get("executionPrice") or position.get("price")
            execution_type = int(execution.get("executionType") or 0)
            status = "FILLED" if execution_type in {3, 11} else "ACCEPTED"
            message = "cTrader demo market order filled." if status == "FILLED" else "cTrader demo market order accepted."
            return BrokerOrderResult(
                True,
                status,
                message,
                broker_order_id=order_id,
                executed_price=Decimal(str(executed_price)) if executed_price not in (None, "") else None,
                raw_response={
                    "provider": "CTRADER",
                    "transport": "OPEN_API_JSON",
                    "order_id": order_id,
                    "position_id": position_id,
                    "symbol": clean_symbol,
                    "symbol_id": str(symbol_id),
                    "requested_lots": str(lots),
                    "protocol_volume": protocol_volume,
                    "lot_size_protocol": full_symbol.get("lotSize"),
                    "execution": _without_secret(execution),
                },
            )
        except Exception as exc:
            message = self._safe_order_error(exc)
            return BrokerOrderResult(False, "FAILED", message, raw_response={"provider": "CTRADER", "transport": "OPEN_API_JSON", "error": message})

    async def _get_json(self, url: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        query = dict(params or {})
        query.setdefault("access_token", token)
        query.setdefault("accessToken", token)

        def _call() -> dict[str, Any]:
            response = requests.get(url, headers=self._auth_headers(), params=query, timeout=30)
            payload = _safe_json(response)
            if response.status_code >= 400:
                raise ValueError(_safe_ctrader_sync_error(f"{response.status_code}: {payload}"))
            return payload

        return await asyncio.to_thread(_call)

    async def _openapi_authorized_client(self, *, is_live: bool):
        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        self.validate_config()
        client = _CTraderJsonWsClient(is_live=is_live)
        await client.__aenter__()
        try:
            await client.request(
                PT_APPLICATION_AUTH_REQ,
                {"clientId": self._client_id(), "clientSecret": self._client_secret()},
                PT_APPLICATION_AUTH_RES,
            )
        except Exception:
            await client.__aexit__(None, None, None)
            raise
        return client

    async def fetch_accounts(self) -> list[dict[str, Any]]:
        # Preserve optional legacy bridge compatibility, but no bridge is required.
        url = self._accounts_url()
        if url:
            payload = await self._get_json(url)
            accounts = [self.normalize_account(item) for item in self._unwrap_list(payload)]
            return [item for item in accounts if item.get("ctrader_account_id") or item.get("account_number")]

        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        is_live = str(getattr(settings, "ctrader_env", "demo") or "demo").strip().lower() == "live"
        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            payload = await client.request(PT_GET_ACCOUNTS_REQ, {"accessToken": token}, PT_GET_ACCOUNTS_RES)
        finally:
            await client.__aexit__(None, None, None)
        raw_accounts = payload.get("ctidTraderAccount") or payload.get("ctidTraderAccounts") or []
        if not isinstance(raw_accounts, list):
            raw_accounts = []
        permission_scope = payload.get("permissionScope")
        trading_enabled = permission_scope in (1, "1", "SCOPE_TRADE")
        accounts: list[dict[str, Any]] = []
        for item in raw_accounts:
            if not isinstance(item, dict):
                continue
            normalized = self.normalize_account(item)
            normalized["account_type"] = "LIVE" if bool(item.get("isLive")) else "DEMO"
            normalized["is_live"] = bool(item.get("isLive"))
            if not normalized.get("broker_name"):
                normalized["broker_name"] = item.get("brokerTitleShort")
            normalized["permission_scope"] = permission_scope
            normalized["trading_enabled"] = trading_enabled
            accounts.append(normalized)
        return [item for item in accounts if item.get("ctrader_account_id") or item.get("account_number")]

    async def _resolve_account_environment(self, account_id: str) -> tuple[bool, dict[str, Any] | None]:
        accounts = await self.fetch_accounts()
        for account in accounts:
            if str(account.get("ctrader_account_id") or account.get("account_number")) == str(account_id):
                return bool(account.get("is_live") or str(account.get("account_type") or "").upper() == "LIVE"), account
        return str(getattr(settings, "ctrader_env", "demo") or "demo").strip().lower() == "live", None

    async def fetch_account_info(
        self,
        account_id: str,
        *,
        is_live_override: bool | None = None,
        selected_account: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch current cTrader financial state from the selected trading account.

        Balance comes from ProtoOATraderRes.
        Equity is balance + the sum of ProtoOAGetPositionUnrealizedPnLRes.netUnrealizedPnL.
        This is intentionally live data and must not fall back to the stale account
        snapshot returned during OAuth/account selection.
        """
        url = self._account_info_url()
        if url:
            payload = await self._get_json(url, {"account_id": account_id, "ctidTraderAccountId": account_id})
            if isinstance(payload, dict):
                return self.normalize_account(payload.get("data") if isinstance(payload.get("data"), dict) else payload)
            raise ValueError("cTrader account info response was empty.")

        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")

        selected_account = selected_account or self._selected_account() or {}
        if is_live_override is None:
            selected_id = selected_account.get("ctrader_account_id") or selected_account.get("account_number")
            if selected_id is not None and str(selected_id) == str(account_id):
                is_live = bool(
                    selected_account.get("is_live")
                    or str(selected_account.get("account_type") or "").upper() == "LIVE"
                )
                discovered = selected_account
            else:
                is_live, discovered = await self._resolve_account_environment(account_id)
        else:
            is_live = bool(is_live_override)
            discovered = selected_account

        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            numeric_id = int(account_id)
            await client.request(
                PT_ACCOUNT_AUTH_REQ,
                {"ctidTraderAccountId": numeric_id, "accessToken": token},
                PT_ACCOUNT_AUTH_RES,
            )
            trader_payload = await client.request(
                PT_TRADER_REQ,
                {"ctidTraderAccountId": numeric_id},
                PT_TRADER_RES,
            )
            pnl_payload = await client.request(
                PT_GET_POSITION_UNREALIZED_PNL_REQ,
                {"ctidTraderAccountId": numeric_id},
                PT_GET_POSITION_UNREALIZED_PNL_RES,
            )
        finally:
            await client.__aexit__(None, None, None)

        trader = trader_payload.get("trader") if isinstance(trader_payload.get("trader"), dict) else trader_payload
        trader = trader if isinstance(trader, dict) else {}
        money_digits = int(trader.get("moneyDigits") or 0)
        balance = _money_value(trader.get("balance"), money_digits)

        pnl_digits = int(pnl_payload.get("moneyDigits") or money_digits or 0) if isinstance(pnl_payload, dict) else money_digits
        pnl_rows = pnl_payload.get("positionUnrealizedPnL") if isinstance(pnl_payload, dict) else []
        unrealized_net = 0.0
        if isinstance(pnl_rows, list):
            for row in pnl_rows:
                if not isinstance(row, dict):
                    continue
                decoded = _money_value(row.get("netUnrealizedPnL"), pnl_digits)
                if decoded is not None:
                    unrealized_net += decoded

        equity = (float(balance) + float(unrealized_net)) if balance is not None else None
        currency = (
            (discovered or {}).get("currency")
            or selected_account.get("currency")
            or "USD"
        )

        base = dict(discovered or {})
        base.update({
            "ctidTraderAccountId": account_id,
            "traderLogin": trader.get("traderLogin"),
            "brokerName": trader.get("brokerName"),
            "accountType": "LIVE" if is_live else "DEMO",
            "balance": balance,
            "equity": equity,
            "netUnrealizedPnL": unrealized_net,
            "currency": currency,
            "leverage": (float(trader.get("leverageInCents")) / 100.0) if trader.get("leverageInCents") is not None else None,
            "raw": _without_secret(trader),
        })
        normalized = self.normalize_account(base)
        normalized["account_type"] = "LIVE" if is_live else "DEMO"
        normalized["is_live"] = is_live
        normalized["balance"] = balance
        normalized["equity"] = equity if equity is not None else balance
        normalized["unrealized_pnl"] = unrealized_net
        normalized["currency"] = currency
        return normalized


    async def _fetch_full_symbol_with_client(self, client: _CTraderJsonWsClient, account_id: int, symbol_id: int) -> dict[str, Any]:
        payload = await client.request(
            PT_SYMBOL_BY_ID_REQ,
            {"ctidTraderAccountId": int(account_id), "symbolId": [int(symbol_id)]},
            PT_SYMBOL_BY_ID_RES,
        )
        symbols = payload.get("symbol") or []
        if not isinstance(symbols, list) or not symbols:
            raise ValueError(f"cTrader full symbol metadata was not returned for symbol id {symbol_id}.")
        row = symbols[0]
        if not isinstance(row, dict):
            raise ValueError(f"cTrader returned invalid symbol metadata for symbol id {symbol_id}.")
        return row

    @staticmethod
    def _lots_to_protocol_volume(lots: Decimal, full_symbol: dict[str, Any]) -> int:
        lot_size = Decimal(str(full_symbol.get("lotSize") or 0))
        if lot_size <= 0:
            raise ValueError("cTrader symbol lot size is unavailable. Sync the broker and try again.")
        raw = lots * lot_size
        min_v = int(full_symbol.get("minVolume") or 0)
        max_v = int(full_symbol.get("maxVolume") or 0)
        step_v = int(full_symbol.get("stepVolume") or 0)
        protocol = int(raw.to_integral_value(rounding=ROUND_DOWN))
        if step_v > 0:
            protocol = (protocol // step_v) * step_v
        if protocol <= 0:
            raise ValueError("Calculated cTrader order volume is zero.")
        if min_v > 0 and protocol < min_v:
            raise ValueError(
                f"Calculated cTrader volume {protocol} is below broker minimum {min_v}. "
                "Increase risk/lot size or choose a symbol with a smaller minimum."
            )
        if max_v > 0 and protocol > max_v:
            raise ValueError(f"Calculated cTrader volume {protocol} exceeds broker maximum {max_v}.")
        return protocol

    @staticmethod
    def _protocol_volume_to_lots(protocol_volume: Any, full_symbol: dict[str, Any] | None) -> Decimal:
        try:
            value = Decimal(str(protocol_volume or 0))
            lot_size = Decimal(str((full_symbol or {}).get("lotSize") or 0))
            if lot_size > 0:
                return value / lot_size
            return value / Decimal("100")
        except Exception:
            return Decimal("0")

    @staticmethod
    def _execution_ids(payload: dict[str, Any]) -> tuple[str | None, str | None]:
        order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
        position = payload.get("position") if isinstance(payload.get("position"), dict) else {}
        deal = payload.get("deal") if isinstance(payload.get("deal"), dict) else {}
        order_id = order.get("orderId") or deal.get("orderId") or payload.get("orderId")
        position_id = position.get("positionId") or deal.get("positionId") or payload.get("positionId")
        return (
            str(order_id) if order_id not in (None, "") else None,
            str(position_id) if position_id not in (None, "") else None,
        )

    async def _send_trade_request(
        self,
        client: _CTraderJsonWsClient,
        *,
        payload_type: int,
        payload: dict[str, Any],
        timeout: float = 12.0,
    ) -> dict[str, Any]:
        if client._ws is None:
            raise RuntimeError("cTrader transport is not connected")
        client_msg_id = str(uuid.uuid4())
        await client._ws.send(json.dumps({
            "clientMsgId": client_msg_id,
            "payloadType": payload_type,
            "payload": payload,
        }, separators=(",", ":")))
        deadline = asyncio.get_running_loop().time() + timeout
        accepted_payload: dict[str, Any] | None = None
        accepted_order_id: str | None = None
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                if accepted_payload is not None:
                    accepted_payload["_accepted_timeout"] = True
                    return accepted_payload
                raise TimeoutError("Timed out waiting for cTrader order execution event.")
            raw = await asyncio.wait_for(client._ws.recv(), timeout=remaining)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                incoming = json.loads(raw)
            except Exception:
                continue
            if not isinstance(incoming, dict):
                continue
            incoming_type = int(incoming.get("payloadType") or 0)
            if incoming_type == PT_HEARTBEAT_EVENT:
                continue
            body = incoming.get("payload")
            body = body if isinstance(body, dict) else {}
            if incoming_type in {PT_ERROR_RES, PT_COMMON_ERROR_RES}:
                raise ValueError(client._error_message(incoming))
            if incoming_type == PT_ORDER_ERROR_EVENT:
                code = body.get("errorCode") or "ORDER_ERROR"
                desc = body.get("description") or "cTrader rejected the order."
                raise ValueError(f"{code}: {desc}")
            if incoming_type != PT_EXECUTION_EVENT:
                continue

            # For a dedicated short-lived order connection, the matching execution
            # normally echoes clientMsgId. If it is absent, match our clientOrderId/order id.
            incoming_id = incoming.get("clientMsgId")
            order = body.get("order") if isinstance(body.get("order"), dict) else {}
            trade_data = order.get("tradeData") if isinstance(order.get("tradeData"), dict) else {}
            echoed_client_order_id = order.get("clientOrderId") or trade_data.get("label")
            requested_client_order_id = payload.get("clientOrderId") or payload.get("label")
            body_order_id, _ = self._execution_ids(body)
            if incoming_id and incoming_id != client_msg_id:
                if not (requested_client_order_id and echoed_client_order_id == requested_client_order_id):
                    if not (accepted_order_id and body_order_id == accepted_order_id):
                        continue

            execution_type = int(body.get("executionType") or 0)
            if execution_type == 7 or body.get("errorCode"):
                raise ValueError(f"{body.get('errorCode') or 'ORDER_REJECTED'}: {body.get('description') or 'cTrader rejected the order.'}")
            if execution_type in {3, 11}:  # filled / partial fill
                return body
            if execution_type == 2:  # accepted; market fill normally follows immediately
                accepted_payload = body
                accepted_order_id, _ = self._execution_ids(body)
                continue
            # Amend/close flows may return other successful execution events.
            if execution_type in {4, 5}:
                return body

    async def fetch_symbols(self, account_id: Optional[str] = None, limit: int = 2000) -> list[dict[str, Any]]:
        url = self._symbols_url()
        if url:
            payload = await self._get_json(url, {"account_id": account_id, "ctidTraderAccountId": account_id, "limit": limit} if account_id else {"limit": limit})
            return [self.normalize_symbol(item) for item in self._unwrap_list(payload)][:limit]
        if not account_id:
            return []
        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        is_live, _ = await self._resolve_account_environment(account_id)
        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            numeric_id = int(account_id)
            await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": numeric_id, "accessToken": token}, PT_ACCOUNT_AUTH_RES)
            payload = await client.request(PT_SYMBOLS_LIST_REQ, {"ctidTraderAccountId": numeric_id, "includeArchivedSymbols": False}, PT_SYMBOLS_LIST_RES)
        finally:
            await client.__aexit__(None, None, None)
        raw_symbols = payload.get("symbol") or payload.get("symbols") or []
        if not isinstance(raw_symbols, list):
            raw_symbols = []
        return [self.normalize_symbol(item) for item in raw_symbols if isinstance(item, dict)][:limit]

    async def test_connection(self) -> BrokerConnectionResult:
        token = self._access_token()
        if not token:
            return BrokerConnectionResult(False, "cTrader OAuth token is missing. Please reconnect cTrader.", server="cTrader Open API", currency="USD", raw={"provider": "CTRADER"})
        meta = getattr(self.broker_account, "metadata_json", None) or {}
        selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
        try:
            accounts = await self.fetch_accounts()
        except Exception as exc:
            return BrokerConnectionResult(False, _safe_ctrader_sync_error(exc), server="cTrader Open API", currency="USD", raw={"provider": "CTRADER", "transport": "JSON_WEBSOCKET"})
        if not accounts:
            return BrokerConnectionResult(False, "cTrader OAuth is valid, but no linked trading account was returned. Check the OAuth account permission and reconnect.", server="cTrader Open API", currency="USD", raw={"provider": "CTRADER", "transport": "JSON_WEBSOCKET", "account_count": 0})
        if not selected and len(accounts) == 1:
            selected = accounts[0]
        trading_enabled = bool((selected or {}).get("trading_enabled")) if isinstance(selected, dict) else any(bool(a.get("trading_enabled")) for a in accounts)
        raw_result: dict[str, Any] = {
            "provider": "CTRADER",
            "orders_enabled": trading_enabled,
            "env": str(settings.ctrader_env or "demo").lower(),
            "transport": "JSON_WEBSOCKET",
            "account_count": len(accounts),
        }
        if selected:
            raw_result["selected_account"] = selected
        return BrokerConnectionResult(
            connected=True,
            message=f"cTrader Open API connected. {len(accounts)} trading account(s) available.",
            account_login=(selected or {}).get("account_number") or getattr(self.broker_account, "login_id", None) or "cTrader ID",
            server=f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})",
            balance=(selected or {}).get("balance") if isinstance(selected, dict) else None,
            equity=(selected or {}).get("equity") if isinstance(selected, dict) else None,
            currency=((selected or {}).get("currency") if isinstance(selected, dict) else None) or "USD",
            raw=raw_result,
        )

    async def get_account_info(self) -> dict[str, Any]:
        selected = self._selected_account()
        if not selected:
            result = await self.test_connection()
            return {
                "connected": result.connected,
                "message": result.message,
                "account_login": result.account_login,
                "server": result.server,
                "balance": result.balance,
                "equity": result.equity,
                "free_margin": None,
                "currency": result.currency,
                "orders_enabled": bool((result.raw or {}).get("orders_enabled")),
            }

        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        if not account_id:
            raise ValueError("Selected cTrader account does not contain an account id.")

        is_live = bool(
            selected.get("is_live")
            or str(selected.get("account_type") or "").upper() == "LIVE"
        )
        info = await self.fetch_account_info(
            str(account_id),
            is_live_override=is_live,
            selected_account=selected,
        )
        return {
            "connected": True,
            "message": "cTrader account financial state refreshed.",
            "account_login": info.get("account_number") or info.get("ctrader_account_id") or str(account_id),
            "server": f"cTrader Open API ({'live' if is_live else 'demo'})",
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "free_margin": info.get("free_margin"),
            "unrealized_pnl": info.get("unrealized_pnl"),
            "currency": info.get("currency") or selected.get("currency") or "USD",
            "orders_enabled": bool(selected.get("trading_enabled", True)),
        }


    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        meta = getattr(self.broker_account, "metadata_json", None) or {}
        selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
        if not selected:
            return BrokerOrderResult(False, "REJECTED", "cTrader account selection required before placing demo orders.", raw_response={"provider": "CTRADER"})
        symbols = meta.get("ctrader_symbols_preview") if isinstance(meta, dict) else []
        symbol_meta = None
        if isinstance(symbols, list):
            for item in symbols:
                if not isinstance(item, dict):
                    continue
                if str(item.get("symbol_name") or item.get("trading_symbol") or item.get("symbol") or "").upper() == str(order_request.symbol or "").upper():
                    symbol_meta = item
                    break
        return await self.place_demo_market_order(
            selected_account=selected,
            symbol_meta=symbol_meta,
            symbol=order_request.symbol,
            side=order_request.side,
            volume=order_request.qty,
            entry_price=order_request.price,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.target,
            client_order_id=order_request.tag,
            comment=order_request.comment,
        )

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        selected = self._selected_account()
        if not selected:
            return BrokerOrderResult(False, "REJECTED", "Select a cTrader trading account before closing a position.", raw_response={"provider": "CTRADER"})
        self.validate_demo_mode(selected)
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        token = self._access_token()
        if not account_id or not token:
            return BrokerOrderResult(False, "REJECTED", "cTrader account/token is unavailable. Reconnect cTrader.", raw_response={"provider": "CTRADER"})
        try:
            position_id = int(str(position_id_or_symbol))
        except Exception:
            return BrokerOrderResult(False, "REJECTED", "cTrader close requires the broker position id.", raw_response={"provider": "CTRADER"})
        positions = await self.get_positions()
        row = next((p for p in positions if str(p.get("position_id") or p.get("broker_position_id")) == str(position_id)), None)
        if not row:
            return BrokerOrderResult(False, "REJECTED", f"cTrader position {position_id} was not found.", raw_response={"provider": "CTRADER"})
        protocol_volume = int(row.get("protocol_volume") or 0)
        requested_lots = Decimal(str(qty or 0))
        full_symbol = row.get("_full_symbol") if isinstance(row.get("_full_symbol"), dict) else None
        if full_symbol and requested_lots > 0:
            requested_protocol = self._lots_to_protocol_volume(requested_lots, full_symbol)
            protocol_volume = min(protocol_volume, requested_protocol) if protocol_volume > 0 else requested_protocol
        if protocol_volume <= 0:
            return BrokerOrderResult(False, "REJECTED", "cTrader close volume is invalid.", raw_response={"provider": "CTRADER"})
        is_live, _ = await self._resolve_account_environment(str(account_id))
        if is_live:
            return BrokerOrderResult(False, "REJECTED", "cTrader live order execution is disabled in this phase.", raw_response={"provider": "CTRADER"})
        try:
            client = await self._openapi_authorized_client(is_live=False)
            try:
                numeric_id = int(account_id)
                await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": numeric_id, "accessToken": token}, PT_ACCOUNT_AUTH_RES)
                execution = await self._send_trade_request(
                    client,
                    payload_type=PT_CLOSE_POSITION_REQ,
                    payload={"ctidTraderAccountId": numeric_id, "positionId": position_id, "volume": protocol_volume},
                    timeout=12.0,
                )
            finally:
                await client.__aexit__(None, None, None)
            order_id, broker_position_id = self._execution_ids(execution)
            deal = execution.get("deal") if isinstance(execution.get("deal"), dict) else {}
            price = deal.get("executionPrice")
            return BrokerOrderResult(
                True,
                "FILLED" if int(execution.get("executionType") or 0) in {3, 11} else "ACCEPTED",
                "cTrader demo position close accepted.",
                broker_order_id=order_id,
                executed_price=Decimal(str(price)) if price not in (None, "") else None,
                raw_response={"provider": "CTRADER", "position_id": broker_position_id or str(position_id), "execution": _without_secret(execution)},
            )
        except Exception as exc:
            message = self._safe_order_error(exc)
            return BrokerOrderResult(False, "FAILED", message, raw_response={"provider": "CTRADER", "error": message})

    def _selected_account(self) -> dict[str, Any] | None:
        meta = getattr(self.broker_account, "metadata_json", None) or {}
        if not isinstance(meta, dict):
            return None
        selected = meta.get("ctrader_selected_account") or meta.get("selected_account")
        return selected if isinstance(selected, dict) else None

    async def get_symbols(self, query: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        selected = self._selected_account()
        if not selected:
            return [{"success": False, "message": "Select a cTrader trading account before loading symbols."}]
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        if not account_id:
            return [{"success": False, "message": "Selected cTrader account does not contain an account id."}]
        rows = await self.fetch_symbols(str(account_id), max(1, min(int(limit or 200), 2000)))
        needle = str(query or "").strip().upper()
        result: list[dict[str, Any]] = []
        for item in rows:
            name = str(item.get("symbol_name") or "").strip()
            if not name:
                continue
            if needle and needle not in name.upper() and needle not in str(item.get("raw") or "").upper():
                continue
            raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
            result.append({
                "symbol": name,
                "symbol_id": item.get("symbol_id"),
                "name": name,
                "description": raw.get("description") or raw.get("name") or name,
                "visible": True,
                "volume_min": item.get("min_volume"),
                "volume_max": item.get("max_volume"),
                "volume_step": item.get("volume_step"),
                "pip_size": item.get("pip_size"),
                "tick_size": item.get("tick_size"),
                "success": True,
                "raw": raw,
            })
        return result[:limit]

    async def _resolve_symbol_meta(self, symbol: str) -> dict[str, Any]:
        clean = str(symbol or "").strip().upper()
        if not clean:
            raise ValueError("cTrader symbol is required.")
        meta = getattr(self.broker_account, "metadata_json", None) or {}
        preview = meta.get("ctrader_symbols_preview") if isinstance(meta, dict) else []
        for item in preview if isinstance(preview, list) else []:
            if not isinstance(item, dict):
                continue
            candidate = str(item.get("symbol_name") or item.get("trading_symbol") or item.get("symbol") or "").strip().upper()
            if candidate == clean and (item.get("symbol_id") or item.get("id")) is not None:
                return item
        selected = self._selected_account()
        account_id = (selected or {}).get("ctrader_account_id") or (selected or {}).get("account_number")
        if not account_id:
            raise ValueError("Select a cTrader trading account before requesting market data.")
        rows = await self.fetch_symbols(str(account_id), 2000)
        for item in rows:
            if str(item.get("symbol_name") or "").strip().upper() == clean:
                return item
        raise ValueError(f"cTrader symbol {clean} was not found. Sync the selected cTrader account and choose a symbol from its broker list.")

    async def get_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        selected = self._selected_account()
        if not selected:
            raise ValueError("Select a cTrader trading account before requesting quotes.")
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        if not account_id:
            raise ValueError("Selected cTrader account does not contain an account id.")
        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        metas = [await self._resolve_symbol_meta(symbol) for symbol in symbols]
        symbol_ids = [int(meta.get("symbol_id") or meta.get("id")) for meta in metas]
        id_to_name = {int(meta.get("symbol_id") or meta.get("id")): str(meta.get("symbol_name") or symbols[idx]).upper() for idx, meta in enumerate(metas)}
        is_live = bool(
            selected.get("is_live")
            or str(selected.get("account_type") or "").upper() == "LIVE"
        )
        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            numeric_id = int(account_id)
            await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": numeric_id, "accessToken": token}, PT_ACCOUNT_AUTH_RES)
            await client.request(PT_SUBSCRIBE_SPOTS_REQ, {"ctidTraderAccountId": numeric_id, "symbolId": symbol_ids, "subscribeToSpotTimestamp": True}, PT_SUBSCRIBE_SPOTS_RES)
            quotes: dict[int, dict[str, Any]] = {}
            deadline = asyncio.get_running_loop().time() + 6.0
            while len(quotes) < len(symbol_ids):
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    break
                event = await client.receive_payload(PT_SPOT_EVENT, timeout=remaining)
                symbol_id = int(event.get("symbolId") or 0)
                if symbol_id not in id_to_name:
                    continue
                bid = Decimal(str(event.get("bid"))) / Decimal("100000") if event.get("bid") is not None else None
                ask = Decimal(str(event.get("ask"))) / Decimal("100000") if event.get("ask") is not None else None
                price = (bid + ask) / Decimal("2") if bid is not None and ask is not None else (bid if bid is not None else ask)
                if price is None:
                    continue
                raw_ts = event.get("timestamp")
                market_timestamp = None
                if raw_ts not in (None, ""):
                    try:
                        ts = int(raw_ts)
                        market_timestamp = datetime.fromtimestamp(ts / 1000 if ts > 10_000_000_000 else ts, tz=timezone.utc)
                    except Exception:
                        market_timestamp = None
                quotes[symbol_id] = {
                    "success": True,
                    "symbol": id_to_name[symbol_id],
                    "symbol_id": str(symbol_id),
                    "price": price,
                    "bid": bid,
                    "ask": ask,
                    "market_timestamp": market_timestamp,
                    "raw": _without_secret(event),
                }
            return [quotes[sid] for sid in symbol_ids if sid in quotes]
        finally:
            await client.__aexit__(None, None, None)

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        rows = await self.get_quotes([symbol])
        if not rows:
            return {"success": False, "symbol": str(symbol or "").upper(), "message": "No cTrader spot quote was received."}
        return rows[0]

    async def _reconcile(self) -> dict[str, Any]:
        selected = self._selected_account()
        if not selected:
            raise ValueError("Select a cTrader trading account before syncing positions/orders.")
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        token = self._access_token()
        if not account_id or not token:
            raise ValueError("cTrader account/token is unavailable. Reconnect cTrader.")
        is_live = bool(
            selected.get("is_live")
            or str(selected.get("account_type") or "").upper() == "LIVE"
        )
        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            numeric_id = int(account_id)
            await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": numeric_id, "accessToken": token}, PT_ACCOUNT_AUTH_RES)
            return await client.request(
                PT_RECONCILE_REQ,
                {"ctidTraderAccountId": numeric_id, "returnProtectionOrders": False},
                PT_RECONCILE_RES,
            )
        finally:
            await client.__aexit__(None, None, None)

    async def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        payload = await self._reconcile()
        positions = payload.get("position") or []
        if not isinstance(positions, list):
            return []
        selected = self._selected_account() or {}
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        lights = await self.fetch_symbols(str(account_id), 2000) if account_id else []
        symbol_by_id = {str(x.get("symbol_id")): x for x in lights if isinstance(x, dict) and x.get("symbol_id") is not None}
        result: list[dict[str, Any]] = []
        for p in positions:
            if not isinstance(p, dict):
                continue
            trade = p.get("tradeData") if isinstance(p.get("tradeData"), dict) else {}
            sid = str(trade.get("symbolId") or "")
            light = symbol_by_id.get(sid, {})
            name = str(light.get("symbol_name") or sid)
            if symbol and name.upper() != str(symbol).upper():
                continue
            full_symbol = None
            try:
                meta = await self._resolve_symbol_meta(name)
                is_live, _ = await self._resolve_account_environment(str(account_id))
                client = await self._openapi_authorized_client(is_live=is_live)
                try:
                    await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": int(account_id), "accessToken": self._access_token()}, PT_ACCOUNT_AUTH_RES)
                    full_symbol = await self._fetch_full_symbol_with_client(client, int(account_id), int(sid))
                finally:
                    await client.__aexit__(None, None, None)
            except Exception:
                full_symbol = None
            protocol_volume = int(trade.get("volume") or 0)
            lots = self._protocol_volume_to_lots(protocol_volume, full_symbol)
            side = "LONG" if int(trade.get("tradeSide") or 1) == 1 else "SHORT"
            result.append({
                "success": True,
                "position_id": str(p.get("positionId") or ""),
                "broker_position_id": str(p.get("positionId") or ""),
                "symbol": name,
                "side": side,
                "volume": str(lots),
                "protocol_volume": protocol_volume,
                "price_open": p.get("price"),
                "price_current": p.get("price"),
                "sl": p.get("stopLoss"),
                "tp": p.get("takeProfit"),
                "status": p.get("positionStatus"),
                "time": trade.get("openTimestamp"),
                "_full_symbol": full_symbol,
                "raw": _without_secret(p),
            })
        return result

    async def get_orders(self) -> list[dict[str, Any]]:
        payload = await self._reconcile()
        orders = payload.get("order") or []
        if not isinstance(orders, list):
            return []
        selected = self._selected_account() or {}
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        lights = await self.fetch_symbols(str(account_id), 2000) if account_id else []
        symbol_by_id = {str(x.get("symbol_id")): x for x in lights if isinstance(x, dict) and x.get("symbol_id") is not None}
        status_map = {1: "PLACED", 2: "FILLED", 3: "REJECTED", 4: "EXPIRED", 5: "CANCELLED"}
        rows: list[dict[str, Any]] = []
        for order in orders:
            if not isinstance(order, dict):
                continue
            trade = order.get("tradeData") if isinstance(order.get("tradeData"), dict) else {}
            sid = str(trade.get("symbolId") or "")
            name = str((symbol_by_id.get(sid) or {}).get("symbol_name") or sid)
            rows.append({
                "success": True,
                "order_id": str(order.get("orderId") or ""),
                "status": status_map.get(int(order.get("orderStatus") or 0), str(order.get("orderStatus") or "PLACED")),
                "symbol": name,
                "side": "BUY" if int(trade.get("tradeSide") or 1) == 1 else "SELL",
                "price": order.get("executionPrice") or order.get("limitPrice") or order.get("stopPrice"),
                "executed_price": order.get("executionPrice"),
                "protocol_volume": trade.get("volume"),
                "client_order_id": order.get("clientOrderId"),
                "raw": _without_secret(order),
            })
        return rows

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        selected = self._selected_account()
        if not selected:
            raise ValueError("Select a cTrader trading account before requesting candles.")
        account_id = selected.get("ctrader_account_id") or selected.get("account_number")
        if not account_id:
            raise ValueError("Selected cTrader account does not contain an account id.")
        token = self._access_token()
        if not token:
            raise ValueError("cTrader OAuth token is missing. Please reconnect cTrader.")
        period_map = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M10": 6, "M15": 7, "M30": 8, "H1": 9, "H4": 10, "H12": 11, "D1": 12, "W1": 13, "MN1": 14}
        clean_tf = str(timeframe or "M5").strip().upper()
        if clean_tf not in period_map:
            raise ValueError(f"Unsupported cTrader timeframe {timeframe}.")
        symbol_meta = await self._resolve_symbol_meta(symbol)
        symbol_id = int(symbol_meta.get("symbol_id") or symbol_meta.get("id"))
        safe_count = max(1, min(int(count or 300), 2000))
        minutes_map = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M10": 10, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "H12": 720, "D1": 1440, "W1": 10080, "MN1": 43200}
        now = datetime.now(timezone.utc)
        to_ms = int(now.timestamp() * 1000)
        from_ms = int((now - timedelta(minutes=minutes_map[clean_tf] * (safe_count + 5))).timestamp() * 1000)
        # The selected account already contains the DEMO/LIVE environment from
        # account sync. Reusing it avoids an extra GetAccountList websocket round trip
        # on every candle refresh.
        is_live = bool(
            selected.get("is_live")
            or str(selected.get("account_type") or "").upper() == "LIVE"
        )
        client = await self._openapi_authorized_client(is_live=is_live)
        try:
            numeric_id = int(account_id)
            await client.request(PT_ACCOUNT_AUTH_REQ, {"ctidTraderAccountId": numeric_id, "accessToken": token}, PT_ACCOUNT_AUTH_RES)
            payload = await client.request(PT_GET_TRENDBARS_REQ, {
                "ctidTraderAccountId": numeric_id,
                "fromTimestamp": from_ms,
                "toTimestamp": to_ms,
                "period": period_map[clean_tf],
                "symbolId": symbol_id,
                "count": safe_count,
            }, PT_GET_TRENDBARS_RES)
        finally:
            await client.__aexit__(None, None, None)
        bars = payload.get("trendbar") or payload.get("trendbars") or []
        result: list[dict[str, Any]] = []
        for bar in bars if isinstance(bars, list) else []:
            if not isinstance(bar, dict) or bar.get("low") is None:
                continue
            low_rel = int(bar.get("low") or 0)
            open_rel = low_rel + int(bar.get("deltaOpen") or 0)
            high_rel = low_rel + int(bar.get("deltaHigh") or 0)
            close_rel = low_rel + int(bar.get("deltaClose") or 0)
            ts_minutes = int(bar.get("utcTimestampInMinutes") or 0)
            candle_time = datetime.fromtimestamp(ts_minutes * 60, tz=timezone.utc) if ts_minutes else now
            result.append({
                "success": True,
                "symbol": str(symbol).upper(),
                "timeframe": clean_tf,
                "candle_time": candle_time.isoformat(),
                "open": float(Decimal(open_rel) / Decimal("100000")),
                "high": float(Decimal(high_rel) / Decimal("100000")),
                "low": float(Decimal(low_rel) / Decimal("100000")),
                "close": float(Decimal(close_rel) / Decimal("100000")),
                "volume": bar.get("volume"),
                "raw_payload": _without_secret(bar),
            })
        result.sort(key=lambda item: item["candle_time"])
        return result[-safe_count:]

async def place_ctrader_demo_order(
    broker_account: BrokerAccount,
    *,
    selected_account: dict[str, Any],
    symbol_meta: dict[str, Any] | None,
    symbol: str,
    side: str,
    volume: Any,
    stop_loss: Any = None,
    take_profit: Any = None,
    client_order_id: str | None = None,
    comment: str | None = None,
) -> BrokerOrderResult:
    """Internal live-engine integration point for CTRADER-PRO-4 demo-only orders.

    Live orders are blocked by validate_demo_mode and by provider/is_live_enabled checks in API flows.
    This function uses CTRADER_DEMO_ORDER_URL when a verified Open API transport/bridge is configured.
    """
    return await CTraderAdapter(broker_account).place_demo_market_order(
        selected_account=selected_account,
        symbol_meta=symbol_meta,
        symbol=symbol,
        side=side,
        volume=volume,
        stop_loss=stop_loss,
        take_profit=take_profit,
        client_order_id=client_order_id,
        comment=comment,
    )
