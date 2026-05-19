from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ...db.models import BrokerAccount
from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult

CRYPTO_BROKERS = {"BINANCE", "BYBIT", "OKX"}


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        return {"status_code": response.status_code, "text": response.text[:500]}


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload or {})
    for key in ("apiKey", "api_key", "apiSecret", "api_secret", "secret", "passphrase", "signature", "sign"):
        if key in redacted:
            redacted[key] = "***redacted***"
    return redacted


def _as_decimal(value: Any) -> Optional[Decimal]:
    try:
        if value in (None, ""):
            return None
        return Decimal(str(value))
    except Exception:
        return None


class CryptoApiAdapter(BrokerAdapter):
    """Read-only/test crypto exchange adapter for Binance, Bybit, and OKX.

    BROKER-PRO-4 only validates account/balance access. Live order methods
    intentionally stay disabled until a later explicit execution phase.
    """

    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account
        self.code = str(broker_account.broker_code or broker_account.broker_name or "").upper().strip()

    def _api_key(self) -> str:
        value = decrypt_credential(getattr(self.broker_account, "encrypted_api_key", None)) or getattr(self.broker_account, "oauth_client_id", None) or getattr(self.broker_account, "login_id", None)
        value = str(value or "").strip()
        if not value:
            raise ValueError(f"{self.code} API Key is missing. Please reconnect and save the API Key again.")
        return value

    def _api_secret(self) -> str:
        value = decrypt_credential(getattr(self.broker_account, "encrypted_api_secret", None)) or decrypt_credential(getattr(self.broker_account, "encrypted_client_secret", None))
        value = str(value or "").strip()
        if not value:
            raise ValueError(f"{self.code} API Secret is missing. Please reconnect and save the API Secret again.")
        return value

    def _passphrase(self) -> str:
        value = decrypt_credential(getattr(self.broker_account, "encrypted_api_passphrase", None))
        value = str(value or "").strip()
        if self.code == "OKX" and not value:
            raise ValueError("OKX API Passphrase is required. Please reconnect and save the passphrase again.")
        return value

    @staticmethod
    def _classify_error(code: str, status_code: int, payload: dict[str, Any]) -> str:
        text = str(payload or "").lower()
        if status_code in {401, 403} or "invalid" in text or "signature" in text or "api-key" in text or "apikey" in text:
            return f"{code} API key/secret is invalid or the signature check failed. Please verify both values."
        if "permission" in text or "unauthorized" in text or "scope" in text:
            return f"{code} API permission is missing. Enable read/trade permission only; never enable withdrawal permission."
        if "ip" in text or "restricted" in text or "whitelist" in text:
            return f"{code} API key has an IP restriction mismatch. Add this server IP in the exchange API settings or remove the restriction for testing."
        if status_code in {429, 418} or "rate" in text:
            return f"{code} API rate limit reached. Please wait and try again."
        if status_code >= 500:
            return f"{code} exchange is temporarily unavailable. Please try again later."
        return f"{code} account test failed. Please verify API permissions and credentials."

    async def _test_binance(self) -> BrokerConnectionResult:
        api_key = self._api_key()
        secret = self._api_secret().encode()
        params = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
        query = urlencode(params)
        signature = hmac.new(secret, query.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{query}&signature={signature}"

        def _call() -> BrokerConnectionResult:
            response = requests.get(url, headers={"X-MBX-APIKEY": api_key}, timeout=30)
            payload = _safe_json(response)
            if response.status_code >= 400:
                raise ValueError(self._classify_error("Binance", response.status_code, payload))
            balances = payload.get("balances") if isinstance(payload.get("balances"), list) else []
            non_zero = []
            total_assets = 0
            for item in balances:
                free = _as_decimal(item.get("free")) or Decimal("0")
                locked = _as_decimal(item.get("locked")) or Decimal("0")
                if free or locked:
                    total_assets += 1
                    non_zero.append({"asset": item.get("asset"), "free": str(free), "locked": str(locked)})
            return BrokerConnectionResult(
                connected=True,
                message="Binance API connection verified. No live orders were placed.",
                account_login=str(payload.get("uid") or "Binance API"),
                server="Binance Spot API",
                currency="USDT",
                raw={"exchange": "BINANCE", "total_non_zero_assets": total_assets, "sample_balances": non_zero[:10]},
            )
        return await asyncio.to_thread(_call)

    async def _test_bybit(self) -> BrokerConnectionResult:
        api_key = self._api_key()
        secret = self._api_secret()
        recv_window = "5000"
        query = "accountType=UNIFIED"
        timestamp = str(int(time.time() * 1000))
        sign_payload = f"{timestamp}{api_key}{recv_window}{query}"
        signature = hmac.new(secret.encode(), sign_payload.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.bybit.com/v5/account/wallet-balance?{query}"
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature,
        }

        def _call() -> BrokerConnectionResult:
            response = requests.get(url, headers=headers, timeout=30)
            payload = _safe_json(response)
            if response.status_code >= 400 or str(payload.get("retCode", "0")) not in {"0", "None"}:
                raise ValueError(self._classify_error("Bybit", response.status_code, payload))
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            rows = result.get("list") if isinstance(result.get("list"), list) else []
            first = rows[0] if rows and isinstance(rows[0], dict) else {}
            equity = _as_decimal(first.get("totalEquity"))
            balance = _as_decimal(first.get("totalWalletBalance"))
            return BrokerConnectionResult(
                connected=True,
                message="Bybit API connection verified. No live orders were placed.",
                account_login="Bybit API",
                server="Bybit V5 API",
                balance=balance,
                equity=equity,
                currency="USDT",
                raw={"exchange": "BYBIT", "account_type": first.get("accountType"), "coin_count": len(first.get("coin") or [])},
            )
        return await asyncio.to_thread(_call)

    async def _test_okx(self) -> BrokerConnectionResult:
        api_key = self._api_key()
        secret = self._api_secret()
        passphrase = self._passphrase()
        request_path = "/api/v5/account/balance"
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        prehash = f"{timestamp}GET{request_path}"
        signature = base64.b64encode(hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()).decode()
        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": passphrase,
        }
        url = f"https://www.okx.com{request_path}"

        def _call() -> BrokerConnectionResult:
            response = requests.get(url, headers=headers, timeout=30)
            payload = _safe_json(response)
            if response.status_code >= 400 or str(payload.get("code", "0")) != "0":
                raise ValueError(self._classify_error("OKX", response.status_code, payload))
            data = payload.get("data") if isinstance(payload.get("data"), list) else []
            first = data[0] if data and isinstance(data[0], dict) else {}
            equity = _as_decimal(first.get("totalEq"))
            details = first.get("details") if isinstance(first.get("details"), list) else []
            return BrokerConnectionResult(
                connected=True,
                message="OKX API connection verified. No live orders were placed.",
                account_login="OKX API",
                server="OKX API v5",
                equity=equity,
                currency="USD",
                raw={"exchange": "OKX", "detail_count": len(details)},
            )
        return await asyncio.to_thread(_call)

    async def test_connection(self) -> BrokerConnectionResult:
        if self.code == "BINANCE":
            return await self._test_binance()
        if self.code == "BYBIT":
            return await self._test_bybit()
        if self.code == "OKX":
            return await self._test_okx()
        raise ValueError(f"Unsupported crypto broker adapter: {self.code}")

    async def get_account_info(self) -> dict[str, Any]:
        result = await self.test_connection()
        return {
            "connected": result.connected,
            "message": result.message,
            "account_login": result.account_login,
            "server": result.server,
            "balance": str(result.balance) if result.balance is not None else None,
            "equity": str(result.equity) if result.equity is not None else None,
            "currency": result.currency,
            "raw": result.raw,
        }

    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        return BrokerOrderResult(success=False, status="DISABLED", message="Crypto live order execution is disabled in BROKER-PRO-4.")

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        return BrokerOrderResult(success=False, status="DISABLED", message="Crypto live order execution is disabled in BROKER-PRO-4.")

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return {"success": False, "message": "Crypto quote adapter is not enabled in this phase."}

    async def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        return []

    async def get_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        return []
