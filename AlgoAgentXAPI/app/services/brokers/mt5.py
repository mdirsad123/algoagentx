from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Optional

from ...db.models import BrokerAccount
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult
from ...utils.credential_crypto import decrypt_credential


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _safe_obj(value: Any) -> Any:
    if hasattr(value, "dtype") and getattr(value.dtype, "names", None):
        return {str(k): _safe_obj(value[k]) for k in value.dtype.names}
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return _safe_obj(value.item())
        except Exception:
            pass
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

    def _timeframe_constant(self, timeframe: str):
        value = str(timeframe or "").strip().upper()
        mapping = {
            "M1": "TIMEFRAME_M1", "1M": "TIMEFRAME_M1", "1MIN": "TIMEFRAME_M1", "1MINUTE": "TIMEFRAME_M1",
            "M5": "TIMEFRAME_M5", "5M": "TIMEFRAME_M5", "5MIN": "TIMEFRAME_M5", "5MINUTE": "TIMEFRAME_M5",
            "M15": "TIMEFRAME_M15", "15M": "TIMEFRAME_M15", "15MIN": "TIMEFRAME_M15", "15MINUTE": "TIMEFRAME_M15",
            "M30": "TIMEFRAME_M30", "30M": "TIMEFRAME_M30", "30MIN": "TIMEFRAME_M30", "30MINUTE": "TIMEFRAME_M30",
            "H1": "TIMEFRAME_H1", "1H": "TIMEFRAME_H1", "1HR": "TIMEFRAME_H1", "1HOUR": "TIMEFRAME_H1",
            "H4": "TIMEFRAME_H4", "4H": "TIMEFRAME_H4", "4HR": "TIMEFRAME_H4", "4HOUR": "TIMEFRAME_H4",
            "D1": "TIMEFRAME_D1", "1D": "TIMEFRAME_D1", "1DAY": "TIMEFRAME_D1",
        }
        attr = mapping.get(value)
        if not attr or self.mt5 is None:
            return None
        return getattr(self.mt5, attr, None)

    def _rate_count(self, rates: Any) -> int:
        if rates is None:
            return 0
        try:
            return int(len(rates))
        except Exception:
            return 0

    def _timeframe_history_days(self, timeframe: str, count: int) -> int:
        value = str(timeframe or "").strip().upper()
        # Wide enough to cover closed candles without pulling too much history.
        if value in {"M1", "1M", "1MIN", "1MINUTE"}:
            return max(2, min(14, int(count / 600) + 2))
        if value in {"M5", "5M", "5MIN", "5MINUTE"}:
            return max(5, min(30, int(count / 250) + 5))
        if value in {"M15", "15M", "15MIN", "15MINUTE"}:
            return max(10, min(60, int(count / 100) + 10))
        if value in {"M30", "30M", "30MIN", "30MINUTE"}:
            return max(20, min(90, int(count / 50) + 20))
        if value in {"H1", "1H", "1HR", "1HOUR"}:
            return max(30, min(180, int(count / 24) + 30))
        if value in {"H4", "4H", "4HR", "4HOUR"}:
            return max(90, min(365, int(count / 6) + 90))
        if value in {"D1", "1D", "1DAY"}:
            return max(365, min(1200, count + 60))
        return 60

    def _symbol_name(self, item: Any) -> Optional[str]:
        data = _safe_obj(item)
        if isinstance(data, dict):
            value = data.get("name") or data.get("symbol")
            return str(value) if value else None
        return None

    def _candidate_symbols(self, symbol: str) -> list[str]:
        requested = str(symbol or "").strip()
        if not requested or self.mt5 is None:
            return [requested]

        candidates: list[str] = []

        def add(name: Optional[str]) -> None:
            if not name:
                return
            clean = str(name).strip()
            if clean and clean not in candidates:
                candidates.append(clean)

        add(requested)
        upper_requested = requested.upper()
        compact_requested = upper_requested.replace(".", "").replace("-", "").replace("_", "")
        base6 = compact_requested[:6]
        patterns = [requested, f"{requested}*", f"*{requested}*", f"{base6}*", f"*{base6}*"]

        for pattern in patterns:
            try:
                for item in self.mt5.symbols_get(pattern) or []:
                    name = self._symbol_name(item)
                    if not name:
                        continue
                    upper_name = name.upper()
                    compact_name = upper_name.replace(".", "").replace("-", "").replace("_", "")
                    if upper_requested in upper_name or (base6 and compact_name.startswith(base6)):
                        add(name)
            except Exception:
                continue

        return candidates[:12]

    def _symbol_debug(self, symbol: str) -> dict[str, Any]:
        try:
            info = self.mt5.symbol_info(symbol) if self.mt5 else None
            data = _safe_obj(info) if info is not None else None
            if isinstance(data, dict):
                return {
                    "name": data.get("name"),
                    "visible": data.get("visible"),
                    "select": data.get("select"),
                    "trade_mode": data.get("trade_mode"),
                    "digits": data.get("digits"),
                    "path": data.get("path"),
                }
        except Exception:
            pass
        return {"name": symbol, "info": None}

    def _copy_rates_attempts(self, symbol: str, timeframe_constant: Any, timeframe: str, count: int) -> tuple[Any, list[dict[str, Any]]]:
        attempts: list[dict[str, Any]] = []
        safe_count = max(1, min(int(count or 300), 2000))
        count_candidates: list[int] = []
        for value in (safe_count, min(safe_count, 300), min(safe_count, 100), min(safe_count, 50), 10):
            if value > 0 and value not in count_candidates:
                count_candidates.append(value)

        def remember(method: str, used_count: int, rates: Any) -> None:
            attempts.append({
                "method": method,
                "count": used_count,
                "returned": self._rate_count(rates),
                "last_error": self._last_error(),
            })

        # Latest closed candles first. start_pos=1 skips the forming candle; start_pos=0 is a fallback.
        for used_count in count_candidates:
            for start_pos in (1, 0):
                try:
                    rates = self.mt5.copy_rates_from_pos(symbol, timeframe_constant, start_pos, used_count)
                    remember(f"copy_rates_from_pos(start_pos={start_pos})", used_count, rates)
                    if self._rate_count(rates) > 0:
                        return rates, attempts
                except Exception as exc:
                    attempts.append({"method": f"copy_rates_from_pos(start_pos={start_pos})", "count": used_count, "exception": str(exc), "last_error": self._last_error()})

        utc_to = datetime.now(timezone.utc)
        for used_count in count_candidates:
            try:
                rates = self.mt5.copy_rates_from(symbol, timeframe_constant, utc_to, used_count)
                remember("copy_rates_from(now)", used_count, rates)
                if self._rate_count(rates) > 0:
                    return rates, attempts
            except Exception as exc:
                attempts.append({"method": "copy_rates_from(now)", "count": used_count, "exception": str(exc), "last_error": self._last_error()})

        history_days = self._timeframe_history_days(timeframe, safe_count)
        utc_from = utc_to - timedelta(days=history_days)
        try:
            rates = self.mt5.copy_rates_range(symbol, timeframe_constant, utc_from, utc_to)
            remember(f"copy_rates_range({history_days}d)", safe_count, rates)
            if self._rate_count(rates) > 0:
                try:
                    return rates[-safe_count:], attempts
                except Exception:
                    return rates, attempts
        except Exception as exc:
            attempts.append({"method": f"copy_rates_range({history_days}d)", "count": safe_count, "exception": str(exc), "last_error": self._last_error()})

        return None, attempts

    async def get_rates(self, symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
        ok, message = self._initialize()
        if not ok:
            return [{"success": False, "message": message, "symbol": symbol, "timeframe": timeframe}]

        tf = self._timeframe_constant(timeframe)
        if tf is None:
            return [{"success": False, "message": f"Unsupported MT5 timeframe: {timeframe}", "symbol": symbol, "timeframe": timeframe}]

        requested_symbol = str(symbol or "").strip()
        if not requested_symbol:
            return [{"success": False, "message": "Symbol is required for MT5 candle snapshot", "symbol": symbol, "timeframe": timeframe}]

        all_attempts: list[dict[str, Any]] = []
        candidates = self._candidate_symbols(requested_symbol)
        try:
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    selected = bool(self.mt5.symbol_select(candidate, True))
                except Exception:
                    selected = False
                symbol_debug = self._symbol_debug(candidate)
                if not selected:
                    all_attempts.append({
                        "symbol": candidate,
                        "selected": False,
                        "symbol_info": symbol_debug,
                        "last_error": self._last_error(),
                    })
                    continue

                rates, attempts = self._copy_rates_attempts(candidate, tf, timeframe, count)
                all_attempts.append({
                    "symbol": candidate,
                    "selected": True,
                    "symbol_info": symbol_debug,
                    "attempts": attempts[-8:],
                })

                if self._rate_count(rates) <= 0:
                    continue

                candles: list[dict[str, Any]] = []
                for rate in rates:
                    raw = _safe_obj(rate)
                    if not isinstance(raw, dict):
                        continue
                    timestamp = raw.get("time")
                    candle_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat() if timestamp is not None else None
                    candles.append({
                        "success": True,
                        "symbol": candidate,
                        "requested_symbol": requested_symbol,
                        "timeframe": timeframe,
                        "candle_time": candle_time,
                        "open": raw.get("open"),
                        "high": raw.get("high"),
                        "low": raw.get("low"),
                        "close": raw.get("close"),
                        "volume": raw.get("tick_volume") or raw.get("real_volume") or raw.get("volume"),
                        "raw_payload": raw,
                    })
                if candles:
                    return candles

            clean_attempts = all_attempts[-6:]
            return [{
                "success": False,
                "message": (
                    f"No MT5 candle data returned for {requested_symbol} {timeframe}. "
                    "The MT5 terminal is connected, but historical rates were not available for this symbol/timeframe. "
                    "Open Market Watch in MT5, right-click Show All, open the exact symbol's chart once, then retry. "
                    "If your broker uses a suffix such as XAUUSDm, set the deployment instrument to that exact MT5 symbol."
                ),
                "symbol": requested_symbol,
                "timeframe": timeframe,
                "candidates_tried": candidates,
                "attempts": clean_attempts,
                "last_error": self._last_error(),
            }]
        except Exception as exc:
            return [{"success": False, "message": f"MT5 rates error: {exc}", "symbol": requested_symbol, "timeframe": timeframe, "last_error": self._last_error()}]
