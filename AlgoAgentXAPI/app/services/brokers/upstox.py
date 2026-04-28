from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode, quote

import requests

from ...core.config import settings
from ...db.models import BrokerAccount
from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult

UPSTOX_AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
UPSTOX_PROFILE_URL = "https://api.upstox.com/v2/user/profile"
UPSTOX_MARKET_STATUS_URL = "https://api.upstox.com/v2/market/status/NSE"
UPSTOX_QUOTES_URL = "https://api.upstox.com/v2/market-quote/quotes"
UPSTOX_INTRADAY_CANDLE_V3_URL = "https://api.upstox.com/v3/historical-candle/intraday"
UPSTOX_HISTORICAL_CANDLE_V3_URL = "https://api.upstox.com/v3/historical-candle"
UPSTOX_PLACE_ORDER_URL = "https://api.upstox.com/v2/order/place"
UPSTOX_ORDER_BOOK_URL = "https://api.upstox.com/v2/order/retrieve-all"
UPSTOX_POSITIONS_URL = "https://api.upstox.com/v2/portfolio/short-term-positions"
UPSTOX_HOLDINGS_URL = "https://api.upstox.com/v2/portfolio/long-term-holdings"


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        return {"status_code": response.status_code, "text": response.text[:500]}


def _without_token(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload or {})
    for key in ("access_token", "refresh_token", "token", "client_secret", "clientSecret"):
        if key in redacted:
            redacted[key] = "***redacted***"
    return redacted


class UpstoxAdapter(BrokerAdapter):
    """Upstox OAuth adapter.

    Supports SaaS BYO app credentials per broker account and keeps platform
    UPSTOX_* env credentials as fallback only.
    """

    def __init__(self, broker_account: Optional[BrokerAccount] = None):
        self.broker_account = broker_account

    @staticmethod
    def _clean(value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _client_id(self) -> Optional[str]:
        return self._clean(getattr(self.broker_account, "oauth_client_id", None)) or self._clean(settings.upstox_client_id)

    def _client_secret(self) -> Optional[str]:
        account_secret = decrypt_credential(getattr(self.broker_account, "encrypted_client_secret", None)) if self.broker_account else None
        return self._clean(account_secret) or self._clean(settings.upstox_client_secret)

    def _redirect_uri(self) -> Optional[str]:
        return self._clean(getattr(self.broker_account, "oauth_redirect_uri", None)) or self._clean(settings.upstox_redirect_uri)

    def validate_config(self) -> None:
        missing = []
        if not self._client_id():
            missing.append("client_id / UPSTOX_CLIENT_ID")
        if not self._client_secret():
            missing.append("client_secret / UPSTOX_CLIENT_SECRET")
        if not self._redirect_uri():
            missing.append("redirect_uri / UPSTOX_REDIRECT_URI")
        if missing:
            raise ValueError(f"Missing Upstox OAuth config: {', '.join(missing)}")

    def build_login_url(self, state: str) -> str:
        self.validate_config()
        query = urlencode({
            "response_type": "code",
            "client_id": self._client_id(),
            "redirect_uri": self._redirect_uri(),
            "state": state,
        })
        return f"{UPSTOX_AUTH_URL}?{query}"

    @classmethod
    def build_platform_login_url(cls, state: str) -> str:
        return cls().build_login_url(state)

    async def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        self.validate_config()
        client_id = self._client_id()
        client_secret = self._client_secret()
        redirect_uri = self._redirect_uri()

        def _call() -> dict[str, Any]:
            response = requests.post(
                UPSTOX_TOKEN_URL,
                headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30,
            )
            payload = _safe_json(response)
            if response.status_code >= 400 or not payload.get("access_token"):
                raise ValueError(f"Upstox token exchange failed: {_without_token(payload)}")
            return payload

        return await asyncio.to_thread(_call)

    @classmethod
    async def exchange_code_for_token_with_platform(cls, code: str) -> dict[str, Any]:
        return await cls().exchange_code_for_token(code)

    def _access_token(self) -> Optional[str]:
        if not self.broker_account:
            return None
        return decrypt_credential(self.broker_account.encrypted_token)

    def _is_expired(self) -> bool:
        if not self.broker_account or not self.broker_account.token_expires_at:
            return False
        expiry = self.broker_account.token_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry <= datetime.now(timezone.utc) + timedelta(minutes=2)

    async def _authorized_get(self, url: str) -> dict[str, Any]:
        token = self._access_token()
        if not token:
            raise ValueError("Upstox access token is missing. Please reconnect Upstox.")
        if self._is_expired():
            raise ValueError("Upstox access token expired. Please reconnect Upstox.")

        def _call() -> dict[str, Any]:
            response = requests.get(url, headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}, timeout=30)
            payload = _safe_json(response)
            if response.status_code == 401:
                raise ValueError("Upstox access token expired or unauthorized. Please reconnect Upstox.")
            if response.status_code == 429:
                raise ValueError("Upstox rate limit reached. Please wait and try again.")
            if response.status_code >= 400:
                raise ValueError(f"Upstox API error: {_without_token(payload)}")
            return payload

        return await asyncio.to_thread(_call)


    async def _authorized_post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = self._access_token()
        if not token:
            raise ValueError("Upstox access token is missing. Please reconnect Upstox.")
        if self._is_expired():
            raise ValueError("Upstox access token expired. Please reconnect Upstox.")

        def _call() -> dict[str, Any]:
            response = requests.post(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30,
            )
            data = _safe_json(response)
            if response.status_code == 401:
                raise ValueError("Upstox access token expired or unauthorized. Please reconnect Upstox.")
            if response.status_code == 429:
                raise ValueError("Upstox rate limit reached. Please wait and try again.")
            if response.status_code >= 400:
                raise ValueError(f"Upstox order API error: {_without_token(data)}")
            return data

        return await asyncio.to_thread(_call)

    @staticmethod
    def _map_timeframe(timeframe: str) -> tuple[str, int, bool]:
        value = (timeframe or "").strip().lower().replace(" ", "")
        aliases = {"m1":"1m","1min":"1m","1minute":"1m","m5":"5m","5min":"5m","5minute":"5m","m15":"15m","15min":"15m","15minute":"15m","m30":"30m","30min":"30m","30minute":"30m","h1":"1h","1hour":"1h","d1":"1d","day":"1d","daily":"1d"}
        value = aliases.get(value, value)
        mapping = {"1m": ("minutes", 1, True), "5m": ("minutes", 5, True), "15m": ("minutes", 15, True), "30m": ("minutes", 30, True), "1h": ("hours", 1, True), "1d": ("days", 1, False)}
        if value not in mapping:
            raise ValueError("Unsupported Upstox timeframe. Supported: 1m, 5m, 15m, 30m, 1h, 1d")
        return mapping[value]

    @staticmethod
    def _normalize_candles(payload: dict[str, Any], symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        candles = ((payload or {}).get("data") or {}).get("candles") or []
        rows: list[dict[str, Any]] = []
        for candle in candles:
            if not isinstance(candle, (list, tuple)) or len(candle) < 5:
                continue
            rows.append({
                "symbol": symbol, "timeframe": timeframe, "candle_time": candle[0],
                "open": candle[1], "high": candle[2], "low": candle[3], "close": candle[4],
                "volume": candle[5] if len(candle) > 5 else None,
                "open_interest": candle[6] if len(candle) > 6 else None,
                "source": "UPSTOX", "is_closed": True, "raw_payload": {"candle": list(candle)},
            })
        rows.sort(key=lambda x: str(x.get("candle_time") or ""))
        if count and len(rows) > count:
            rows = rows[-count:]
        return rows

    async def test_connection(self) -> BrokerConnectionResult:
        try:
            payload = await self._authorized_get(UPSTOX_PROFILE_URL)
            profile = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            user_id = profile.get("user_id") or profile.get("email") or "Upstox"
            return BrokerConnectionResult(
                connected=True,
                message="Upstox account connected",
                account_login=str(user_id),
                server="Upstox API v2",
                currency="INR",
                raw={"profile": self.safe_profile(profile)},
            )
        except Exception as exc:
            return BrokerConnectionResult(connected=False, message=str(exc), server="Upstox API v2", raw={"error": str(exc)})

    @staticmethod
    def safe_profile(profile: dict[str, Any]) -> dict[str, Any]:
        allowed = {"email", "exchanges", "products", "broker", "user_id", "user_name", "order_types", "user_type", "poa", "ddpi", "is_active"}
        return {k: v for k, v in (profile or {}).items() if k in allowed}

    async def get_account_info(self) -> dict[str, Any]:
        result = await self.test_connection()
        return {"connected": result.connected, "message": result.message, "account_login": result.account_login, "server": result.server, "currency": result.currency, "raw": result.raw}

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        instrument_key = self._clean(symbol)
        if not instrument_key:
            raise ValueError("Upstox instrument_key is required for quote lookup")
        url = f"{UPSTOX_QUOTES_URL}?instrument_key={quote(instrument_key, safe='')}"
        return await self._authorized_get(url)

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        instrument_key = self._clean(symbol)
        if not instrument_key:
            raise ValueError("Upstox instrument_key is required for candle refresh")
        safe_count = max(1, min(int(count or 300), 2000))
        unit, interval, intraday = self._map_timeframe(timeframe)
        encoded = quote(instrument_key, safe="")
        if intraday:
            url = f"{UPSTOX_INTRADAY_CANDLE_V3_URL}/{encoded}/{unit}/{interval}"
        else:
            to_date = datetime.now(timezone.utc).date()
            from_date = to_date - timedelta(days=max(30, min(750, safe_count * 3)))
            url = f"{UPSTOX_HISTORICAL_CANDLE_V3_URL}/{encoded}/{unit}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        payload = await self._authorized_get(url)
        rows = self._normalize_candles(payload, instrument_key, timeframe, safe_count)
        if not rows:
            raise ValueError("No candle data returned from Upstox. Check instrument_key, timeframe, market hours, and API permissions.")
        return rows

    @staticmethod
    def _upstox_status(raw_status: str | None) -> str:
        value = str(raw_status or "").lower()
        if value in {"complete", "completed", "filled"}:
            return "FILLED"
        if value in {"open", "trigger pending", "validation pending", "put order req received"}:
            return "PLACED"
        if value in {"cancelled", "canceled"}:
            return "CANCELLED"
        if value in {"rejected", "failed"}:
            return "REJECTED"
        return "PLACED"

    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        instrument_key = self._clean(order_request.instrument_key) or self._clean(order_request.symbol)
        if not instrument_key:
            return BrokerOrderResult(success=False, status="REJECTED", message="Upstox instrument_key is required for order placement")
        qty = int(Decimal(str(order_request.qty or 0)))
        if qty <= 0:
            return BrokerOrderResult(success=False, status="REJECTED", message="Upstox quantity must be a positive whole number")
        product = (order_request.product_type or "I").upper()
        product = "I" if product in {"MIS", "INTRADAY", "I"} else "D"
        payload = {
            "quantity": qty,
            "product": product,
            "validity": "DAY",
            "price": 0,
            "tag": (order_request.tag or "AlgoAgentX")[:40],
            "instrument_token": instrument_key,
            "order_type": "MARKET",
            "transaction_type": str(order_request.side or "BUY").upper(),
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": False,
        }
        try:
            response = await self._authorized_post(UPSTOX_PLACE_ORDER_URL, payload)
            data = response.get("data") if isinstance(response.get("data"), dict) else {}
            order_id = str(data.get("order_id") or data.get("orderId") or "") or None
            status_value = data.get("status") or response.get("status") or "placed"
            status = self._upstox_status(str(status_value))
            return BrokerOrderResult(success=status not in {"REJECTED", "ERROR"}, status=status, message="Upstox order placed", broker_order_id=order_id, executed_price=order_request.price, raw_response=_without_token(response))
        except Exception as exc:
            return BrokerOrderResult(success=False, status="ERROR", message=str(exc), raw_response={"error": str(exc), "request": {**payload, "tag": payload.get("tag")}})

    async def place_limit_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        instrument_key = self._clean(order_request.instrument_key) or self._clean(order_request.symbol)
        price = Decimal(str(order_request.price or 0))
        if price <= 0:
            return BrokerOrderResult(success=False, status="REJECTED", message="Limit order requires a positive price")
        qty = int(Decimal(str(order_request.qty or 0)))
        if qty <= 0:
            return BrokerOrderResult(success=False, status="REJECTED", message="Upstox quantity must be a positive whole number")
        product = (order_request.product_type or "I").upper()
        product = "I" if product in {"MIS", "INTRADAY", "I"} else "D"
        payload = {
            "quantity": qty, "product": product, "validity": "DAY", "price": float(price),
            "tag": (order_request.tag or "AlgoAgentX")[:40], "instrument_token": instrument_key,
            "order_type": "LIMIT", "transaction_type": str(order_request.side or "BUY").upper(),
            "disclosed_quantity": 0, "trigger_price": 0, "is_amo": False,
        }
        try:
            response = await self._authorized_post(UPSTOX_PLACE_ORDER_URL, payload)
            data = response.get("data") if isinstance(response.get("data"), dict) else {}
            return BrokerOrderResult(success=True, status="PLACED", message="Upstox limit order placed", broker_order_id=str(data.get("order_id") or "") or None, executed_price=price, raw_response=_without_token(response))
        except Exception as exc:
            return BrokerOrderResult(success=False, status="ERROR", message=str(exc), raw_response={"error": str(exc), "request": payload})

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        close_side = "SELL" if str(side).upper() == "LONG" else "BUY"
        return await self.place_market_order(BrokerOrderRequest(symbol=position_id_or_symbol, instrument_key=position_id_or_symbol, side=close_side, qty=qty, product_type="MIS", tag="AlgoAgentXExit"))

    async def get_positions(self) -> list[dict[str, Any]]:
        try:
            payload = await self._authorized_get(UPSTOX_POSITIONS_URL)
            data = payload.get("data")
            return data if isinstance(data, list) else []
        except Exception as exc:
            return [{"success": False, "message": str(exc)}]

    async def get_orders(self) -> list[dict[str, Any]]:
        try:
            payload = await self._authorized_get(UPSTOX_ORDER_BOOK_URL)
            data = payload.get("data")
            return data if isinstance(data, list) else []
        except Exception as exc:
            return [{"success": False, "message": str(exc)}]

    async def get_holdings(self) -> list[dict[str, Any]]:
        try:
            payload = await self._authorized_get(UPSTOX_HOLDINGS_URL)
            data = payload.get("data")
            return data if isinstance(data, list) else []
        except Exception as exc:
            return [{"success": False, "message": str(exc)}]

    async def get_symbols(self, query: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return []
