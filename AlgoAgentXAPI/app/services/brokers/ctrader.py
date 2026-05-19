from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ...core.config import settings
from ...db.models import BrokerAccount
from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult

DEFAULT_CTRADER_AUTH_URL = "https://openapi.ctrader.com/apps/auth"
DEFAULT_CTRADER_TOKEN_URL = "https://openapi.ctrader.com/apps/token"


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


class CTraderAdapter(BrokerAdapter):
    """OAuth scaffold for cTrader Open API.

    BROKER-PRO/CTRADER-PRO-1 enables provider setup and OAuth token storage only.
    Order execution remains disabled until the execution phase is implemented.
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

    def build_login_url(self, state: str, scope: str = "accounts") -> str:
        self.validate_config()
        query = urlencode({
            "client_id": self._client_id(),
            "redirect_uri": self._redirect_uri(),
            "scope": scope,
            "state": state,
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
        login = _first_value(item, "accountNumber", "login", "accountLogin", "accountNo", "accountId", "ctidTraderAccountId")
        return {
            "ctrader_account_id": str(account_id) if account_id is not None else None,
            "account_number": str(login) if login is not None else None,
            "broker_name": _first_value(item, "brokerName", "broker", "brokerTitle", "whiteLabelName"),
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
        if "not configured" in lower or "bridge" in lower:
            return "cTrader demo order bridge is not configured. OAuth/sync is ready, but order transport must be configured before placing demo orders."
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
        stop_loss: Any = None,
        take_profit: Any = None,
        client_order_id: str | None = None,
        comment: str | None = None,
    ) -> BrokerOrderResult:
        self.validate_demo_mode(selected_account)
        url = self._demo_order_url()
        if not url:
            return BrokerOrderResult(
                False,
                "FAILED",
                "cTrader demo order bridge is not configured. OAuth/sync is ready, but order transport must be configured before placing demo orders.",
                raw_response={"provider": "CTRADER", "bridge_configured": False},
            )
        token = self._access_token()
        if not token:
            return BrokerOrderResult(False, "FAILED", "cTrader OAuth token is missing. Please reconnect cTrader.", raw_response={"provider": "CTRADER"})
        clean_symbol = str(symbol or "").strip().upper()
        clean_side = str(side or "").strip().upper()
        if not clean_symbol:
            raise ValueError("Symbol is required.")
        if clean_side not in {"BUY", "SELL"}:
            raise ValueError("Side must be BUY or SELL.")
        dec_volume = self._as_decimal(volume, "volume")
        self.validate_volume_against_symbol(dec_volume, symbol_meta)
        account_id = selected_account.get("ctrader_account_id") or selected_account.get("account_number")
        payload = {
            "account_id": str(account_id),
            "ctidTraderAccountId": str(account_id),
            "symbol": clean_symbol,
            "symbol_id": (symbol_meta or {}).get("symbol_id"),
            "side": clean_side,
            "order_type": "MARKET",
            "volume": str(dec_volume),
            "stop_loss": str(stop_loss) if stop_loss not in (None, "") else None,
            "take_profit": str(take_profit) if take_profit not in (None, "") else None,
            "client_order_id": client_order_id,
            "comment": comment or "AlgoAgentX cTrader DEMO test order",
            "demo_only": True,
        }

        def _call() -> dict[str, Any]:
            response = requests.post(url, headers=self._auth_headers(), json=payload, timeout=30)
            data = _safe_json(response)
            if response.status_code >= 400:
                raise ValueError(self._safe_order_error(f"{response.status_code}: {data}"))
            return data

        try:
            data = await asyncio.to_thread(_call)
            success = bool(data.get("success", True)) and str(data.get("status", "SUCCESS")).upper() not in {"FAILED", "ERROR", "REJECTED"}
            order_id = data.get("order_id") or data.get("broker_order_id") or data.get("position_id") or data.get("deal_id")
            return BrokerOrderResult(
                success,
                str(data.get("status") or ("SUCCESS" if success else "FAILED")).upper(),
                str(data.get("message") or ("cTrader demo order placed." if success else "cTrader demo order failed.")),
                broker_order_id=str(order_id) if order_id is not None else None,
                executed_price=data.get("executed_price") or data.get("price"),
                raw_response=_without_secret(data),
            )
        except Exception as exc:
            return BrokerOrderResult(False, "FAILED", self._safe_order_error(exc), raw_response={"provider": "CTRADER", "error": self._safe_order_error(exc)})

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

    async def fetch_accounts(self) -> list[dict[str, Any]]:
        url = self._accounts_url()
        if not url:
            raise ValueError("cTrader account sync endpoint is not configured. OAuth token is saved; set CTRADER_ACCOUNTS_URL or implement the Open API protobuf transport bridge to fetch linked trading accounts.")
        payload = await self._get_json(url)
        accounts = [self.normalize_account(item) for item in self._unwrap_list(payload)]
        return [item for item in accounts if item.get("ctrader_account_id") or item.get("account_number")]

    async def fetch_account_info(self, account_id: str) -> dict[str, Any]:
        url = self._account_info_url()
        if not url:
            accounts = await self.fetch_accounts()
            for account in accounts:
                if str(account.get("ctrader_account_id") or account.get("account_number")) == str(account_id):
                    return account
            raise ValueError("Selected cTrader account was not found. Please reconnect or sync accounts again.")
        payload = await self._get_json(url, {"account_id": account_id, "ctidTraderAccountId": account_id})
        if isinstance(payload, dict):
            return self.normalize_account(payload.get("data") if isinstance(payload.get("data"), dict) else payload)
        raise ValueError("cTrader account info response was empty.")

    async def fetch_symbols(self, account_id: Optional[str] = None, limit: int = 500) -> list[dict[str, Any]]:
        url = self._symbols_url()
        if not url:
            return []
        payload = await self._get_json(url, {"account_id": account_id, "ctidTraderAccountId": account_id, "limit": limit} if account_id else {"limit": limit})
        return [self.normalize_symbol(item) for item in self._unwrap_list(payload)][:limit]

    async def test_connection(self) -> BrokerConnectionResult:
        token = self._access_token()
        if not token:
            return BrokerConnectionResult(False, "cTrader OAuth token is missing. Please reconnect cTrader.", server="cTrader Open API", currency="USD", raw={"provider": "CTRADER"})
        meta = getattr(self.broker_account, "metadata_json", None) or {}
        selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
        raw_result: dict[str, Any] = {"provider": "CTRADER", "orders_enabled": False, "env": str(settings.ctrader_env or "demo").lower()}
        if selected:
            raw_result["selected_account"] = selected
        return BrokerConnectionResult(
            connected=True,
            message="cTrader OAuth token is valid. Use Sync to fetch trading account, balance, and symbols.",
            account_login=(selected or {}).get("account_number") or getattr(self.broker_account, "login_id", None) or "cTrader ID",
            server=f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})",
            balance=(selected or {}).get("balance") if isinstance(selected, dict) else None,
            equity=(selected or {}).get("equity") if isinstance(selected, dict) else None,
            currency=((selected or {}).get("currency") if isinstance(selected, dict) else None) or "USD",
            raw=raw_result,
        )

    async def get_account_info(self) -> dict[str, Any]:
        result = await self.test_connection()
        return {
            "connected": result.connected,
            "message": result.message,
            "account_login": result.account_login,
            "server": result.server,
            "balance": result.balance,
            "equity": result.equity,
            "currency": result.currency,
            "orders_enabled": False,
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
            stop_loss=order_request.stop_loss,
            take_profit=order_request.target,
            client_order_id=order_request.tag,
            comment=order_request.comment,
        )

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        return BrokerOrderResult(False, "REJECTED", "cTrader order execution is disabled in this phase.", raw_response={"provider": "CTRADER"})

    async def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        return []

    async def get_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        return []

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
