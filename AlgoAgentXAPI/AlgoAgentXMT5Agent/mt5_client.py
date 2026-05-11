from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class MT5Status:
    terminal_connected: bool
    terminal_status: str
    mt5_account_login: str | None = None
    server_name: str | None = None
    balance: float | None = None
    equity: float | None = None
    currency: str | None = None
    trading_allowed: bool | None = None
    metadata: dict[str, Any] | None = None

    def to_payload(self, agent_version: str) -> dict[str, Any]:
        payload = asdict(self)
        payload["agent_version"] = agent_version
        payload["metadata"] = payload.get("metadata") or {}
        return payload


class MT5Client:
    def __init__(self, mt5_path: str = "", default_deviation: int = 20):
        self.mt5_path = (mt5_path or "").strip()
        self.default_deviation = int(default_deviation or 20)
        self.mt5 = None
        self._import_error: str | None = None
        try:
            import MetaTrader5 as mt5  # type: ignore
            self.mt5 = mt5
        except Exception as exc:  # pragma: no cover - only happens on machines without MT5 package
            self._import_error = str(exc)

    def initialize(self) -> bool:
        if self.mt5 is None:
            return False
        try:
            if self.mt5_path:
                return bool(self.mt5.initialize(path=self.mt5_path))
            return bool(self.mt5.initialize())
        except Exception:
            return False

    def status(self) -> MT5Status:
        if self.mt5 is None:
            return MT5Status(False, "MT5_PYTHON_PACKAGE_MISSING", metadata={"error": self._import_error or "MetaTrader5 package is not installed"})

        if not self.initialize():
            last_error = None
            try:
                last_error = self.mt5.last_error()
            except Exception:
                pass
            return MT5Status(False, "TERMINAL_NOT_FOUND_OR_NOT_STARTED", metadata={"last_error": str(last_error)})

        try:
            terminal = self.mt5.terminal_info()
            account = self.mt5.account_info()
            if account is None:
                return MT5Status(True, "TERMINAL_CONNECTED_LOGIN_REQUIRED", metadata={"terminal": str(terminal)})

            trading_allowed = bool(getattr(terminal, "trade_allowed", False) or getattr(account, "trade_allowed", False))
            return MT5Status(
                terminal_connected=True,
                terminal_status="TERMINAL_CONNECTED",
                mt5_account_login=str(getattr(account, "login", "")) or None,
                server_name=getattr(account, "server", None),
                balance=float(getattr(account, "balance", 0.0)),
                equity=float(getattr(account, "equity", 0.0)),
                currency=getattr(account, "currency", None),
                trading_allowed=trading_allowed,
                metadata={
                    "company": getattr(account, "company", None),
                    "name": getattr(account, "name", None),
                    "leverage": getattr(account, "leverage", None),
                    "terminal_build": getattr(terminal, "build", None) if terminal else None,
                    "terminal_company": getattr(terminal, "company", None) if terminal else None,
                },
            )
        except Exception as exc:
            return MT5Status(False, "TERMINAL_STATUS_ERROR", metadata={"error": str(exc)})

    def place_order(self, command: dict[str, Any], enable_order_execution: bool = False) -> dict[str, Any]:
        if not enable_order_execution:
            return {"success": False, "message": "Order execution is disabled in agent config. Set ENABLE_ORDER_EXECUTION=true only after demo testing.", "raw": {}}
        if self.mt5 is None or not self.initialize():
            return {"success": False, "message": "MT5 terminal is not connected.", "raw": {}}

        payload = command.get("request_payload") or {}
        symbol = str(payload.get("symbol") or "").strip()
        side = str(payload.get("side") or "BUY").upper()
        volume = float(payload.get("qty") or payload.get("volume") or 0)
        if not symbol or volume <= 0:
            return {"success": False, "message": "Invalid MT5 order command: symbol and qty are required.", "raw": payload}

        self.mt5.symbol_select(symbol, True)
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "message": f"No MT5 tick found for {symbol}.", "raw": payload}

        order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        price = float(payload.get("price") or (tick.ask if side == "BUY" else tick.bid))
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": int(payload.get("deviation") or self.default_deviation),
            "magic": 260510,
            "comment": str(payload.get("comment") or "AlgoAgentX MT5 Agent")[:31],
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        if payload.get("stop_loss") is not None:
            request["sl"] = float(payload["stop_loss"])
        if payload.get("target") is not None:
            request["tp"] = float(payload["target"])

        result = self.mt5.order_send(request)
        raw = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        retcode = raw.get("retcode")
        ok_codes = {getattr(self.mt5, "TRADE_RETCODE_DONE", 10009), getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008)}
        success = retcode in ok_codes
        return {
            "success": bool(success),
            "message": raw.get("comment") or ("Order sent" if success else "MT5 order failed"),
            "raw": raw,
            "broker_order_id": str(raw.get("order") or raw.get("deal") or "") or None,
            "executed_price": raw.get("price"),
        }
