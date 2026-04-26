from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ...db.models import BrokerAccount
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _safe_obj(value: Any) -> Any:
    if hasattr(value, "_asdict"):
        return {k: _safe_obj(v) for k, v in value._asdict().items()}
    if isinstance(value, (list, tuple)):
        return [_safe_obj(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_obj(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    return value


class MT5Adapter(BrokerAdapter):
    """MetaTrader 5 demo adapter.

    MetaTrader5 Python package needs the MT5 terminal installed on the same Windows
    machine/server. This adapter keeps failures explicit and never logs passwords.
    """

    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account
        self.mt5 = None
        self.import_error: Optional[str] = None
        try:
            import MetaTrader5 as mt5  # type: ignore
            self.mt5 = mt5
        except Exception as exc:  # pragma: no cover - depends on Windows terminal
            self.import_error = str(exc)

    def _missing_mt5(self) -> Optional[BrokerConnectionResult]:
        if self.mt5 is None:
            return BrokerConnectionResult(
                connected=False,
                message=(
                    "MetaTrader5 Python package or terminal is not available. "
                    "Install MetaTrader 5 terminal on this Windows machine and install the MetaTrader5 Python package."
                ),
                server=self.broker_account.server_name,
                account_login=self.broker_account.login_id,
                raw={"import_error": self.import_error},
            )
        return None

    def _password(self) -> Optional[str]:
        return self.broker_account.encrypted_password or self.broker_account.encrypted_token

    def _login(self) -> Optional[int]:
        if not self.broker_account.login_id:
            return None
        try:
            return int(str(self.broker_account.login_id).strip())
        except Exception:
            return None

    def _last_error(self) -> Any:
        try:
            return _safe_obj(self.mt5.last_error()) if self.mt5 else None
        except Exception:
            return None

    def _initialize(self) -> tuple[bool, str]:
        if self.mt5 is None:
            return False, "MetaTrader5 package is not available"

        login = self._login()
        password = self._password()
        server = self.broker_account.server_name

        try:
            if login and password and server:
                ok = self.mt5.initialize(login=login, password=password, server=server)
            else:
                ok = self.mt5.initialize()
            if ok:
                return True, "MT5 initialized"
            return False, f"MT5 initialize failed: {self._last_error()}"
        except Exception as exc:
            return False, f"MT5 initialize error: {exc}"

    async def test_connection(self) -> BrokerConnectionResult:
        missing = self._missing_mt5()
        if missing:
            return missing
        ok, message = self._initialize()
        if not ok:
            return BrokerConnectionResult(
                connected=False,
                message=message,
                account_login=self.broker_account.login_id,
                server=self.broker_account.server_name,
                raw={"last_error": self._last_error()},
            )
        try:
            info = self.mt5.account_info()
            if info is None:
                return BrokerConnectionResult(
                    connected=False,
                    message=f"MT5 terminal initialized but account info is unavailable: {self._last_error()}",
                    account_login=self.broker_account.login_id,
                    server=self.broker_account.server_name,
                    raw={"last_error": self._last_error()},
                )
            data = _safe_obj(info)
            return BrokerConnectionResult(
                connected=True,
                message="MT5 demo account connected",
                account_login=str(data.get("login") or self.broker_account.login_id or ""),
                server=str(data.get("server") or self.broker_account.server_name or ""),
                balance=_decimal(data.get("balance")),
                equity=_decimal(data.get("equity")),
                currency=data.get("currency"),
                raw=data,
            )
        except Exception as exc:
            return BrokerConnectionResult(
                connected=False,
                message=f"MT5 account info error: {exc}",
                account_login=self.broker_account.login_id,
                server=self.broker_account.server_name,
                raw={"last_error": self._last_error()},
            )

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

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        ok, message = self._initialize()
        if not ok:
            return {"success": False, "message": message, "symbol": symbol}
        try:
            self.mt5.symbol_select(symbol, True)
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"success": False, "message": f"No quote for {symbol}: {self._last_error()}", "symbol": symbol}
            data = _safe_obj(tick)
            return {
                "success": True,
                "symbol": symbol,
                "bid": data.get("bid"),
                "ask": data.get("ask"),
                "last": data.get("last") or data.get("bid") or data.get("ask"),
                "raw": data,
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "symbol": symbol}

    async def place_market_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResult:
        ok, message = self._initialize()
        if not ok:
            return BrokerOrderResult(False, "ERROR", message, raw_response={"last_error": self._last_error()})
        try:
            symbol = order_request.symbol
            self.mt5.symbol_select(symbol, True)
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return BrokerOrderResult(False, "ERROR", f"No quote found for {symbol}", raw_response={"last_error": self._last_error()})

            side = order_request.side.upper()
            order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
            price = _decimal(getattr(tick, "ask", None) if side == "BUY" else getattr(tick, "bid", None))
            if price <= 0 and order_request.price:
                price = order_request.price

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(order_request.qty),
                "type": order_type,
                "price": float(price),
                "deviation": order_request.deviation,
                "magic": 260426,
                "comment": order_request.comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            if order_request.stop_loss:
                request["sl"] = float(order_request.stop_loss)
            if order_request.target:
                request["tp"] = float(order_request.target)

            response = self.mt5.order_send(request)
            raw = _safe_obj(response)
            retcode = raw.get("retcode") if isinstance(raw, dict) else None
            success_codes = {
                getattr(self.mt5, "TRADE_RETCODE_DONE", 10009),
                getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008),
            }
            if response is not None and retcode in success_codes:
                return BrokerOrderResult(
                    success=True,
                    status="FILLED",
                    message="MT5 demo market order filled/placed",
                    broker_order_id=str(raw.get("order") or raw.get("deal") or ""),
                    executed_price=_decimal(raw.get("price"), str(price)),
                    raw_response=raw,
                )
            return BrokerOrderResult(False, "ERROR", f"MT5 order rejected: {raw}", raw_response=raw if isinstance(raw, dict) else {"response": raw})
        except Exception as exc:
            return BrokerOrderResult(False, "ERROR", f"MT5 order error: {exc}", raw_response={"last_error": self._last_error()})

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        ok, message = self._initialize()
        if not ok:
            return BrokerOrderResult(False, "ERROR", message, raw_response={"last_error": self._last_error()})
        try:
            positions = self.mt5.positions_get(symbol=position_id_or_symbol) or self.mt5.positions_get()
            if positions is None:
                return BrokerOrderResult(False, "ERROR", f"Unable to fetch MT5 positions: {self._last_error()}")
            target = None
            for pos in positions:
                data = _safe_obj(pos)
                if str(data.get("ticket")) == str(position_id_or_symbol) or data.get("symbol") == position_id_or_symbol:
                    target = data
                    break
            if not target:
                return BrokerOrderResult(False, "ERROR", "No matching MT5 position found")
            symbol = target.get("symbol")
            volume = min(float(qty), float(target.get("volume") or qty))
            close_side = "SELL" if side.upper() == "LONG" else "BUY"
            request = BrokerOrderRequest(symbol=symbol, side=close_side, qty=Decimal(str(volume)), comment="AlgoAgentX Demo Close")
            return await self.place_market_order(request)
        except Exception as exc:
            return BrokerOrderResult(False, "ERROR", f"MT5 close position error: {exc}", raw_response={"last_error": self._last_error()})

    async def get_positions(self) -> list[dict[str, Any]]:
        ok, message = self._initialize()
        if not ok:
            return [{"success": False, "message": message}]
        try:
            positions = self.mt5.positions_get()
            return [_safe_obj(p) for p in positions] if positions else []
        except Exception as exc:
            return [{"success": False, "message": str(exc)}]

    async def get_orders(self) -> list[dict[str, Any]]:
        ok, message = self._initialize()
        if not ok:
            return [{"success": False, "message": message}]
        try:
            orders = self.mt5.orders_get()
            return [_safe_obj(o) for o in orders] if orders else []
        except Exception as exc:
            return [{"success": False, "message": str(exc)}]
