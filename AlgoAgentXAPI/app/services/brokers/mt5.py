from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN
import os
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




def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    units = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step


def _decimal_places(value: Decimal) -> int:
    try:
        exponent = value.normalize().as_tuple().exponent
        return max(0, abs(int(exponent)))
    except Exception:
        return 2


def _fmt_decimal(value: Decimal, places: int = 8) -> Decimal:
    quant = Decimal('1').scaleb(-max(0, places))
    return value.quantize(quant, rounding=ROUND_DOWN).normalize()

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
        # Values are stored encrypted by broker_accounts routes. decrypt_credential also
        # keeps backward compatibility with older plaintext Phase 5 credentials.
        return decrypt_credential(self.broker_account.encrypted_password or self.broker_account.encrypted_token)

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

    def _env_decimal(self, name: str, default: str) -> Decimal:
        try:
            return Decimal(str(os.getenv(name, default)).strip())
        except Exception:
            return Decimal(default)

    def _demo_max_lot(self, override: Any = None) -> Decimal:
        if override not in (None, ""):
            value = _decimal(override, os.getenv("MT5_DEMO_MAX_LOT", "0.01"))
            if value > 0:
                return value
        metadata = self.broker_account.metadata_json or {}
        for key in ("mt5_demo_max_lot", "demo_max_lot", "max_lot"):
            if key in metadata and metadata.get(key) not in (None, ""):
                return _decimal(metadata.get(key), os.getenv("MT5_DEMO_MAX_LOT", "0.01"))
        return self._env_decimal("MT5_DEMO_MAX_LOT", "0.01")

    def _symbol_volume_limits(self, symbol: str) -> dict[str, Any]:
        info = self.mt5.symbol_info(symbol) if self.mt5 else None
        data = _safe_obj(info) if info is not None else {}
        if not isinstance(data, dict):
            data = {}
        volume_min = _decimal(data.get("volume_min"), "0.01")
        volume_max = _decimal(data.get("volume_max"), "100")
        volume_step = _decimal(data.get("volume_step"), "0.01")
        if volume_min <= 0:
            volume_min = Decimal("0.01")
        if volume_step <= 0:
            volume_step = Decimal("0.01")
        if volume_max <= 0:
            volume_max = volume_min
        return {
            "volume_min": volume_min,
            "volume_max": volume_max,
            "volume_step": volume_step,
            "raw": data,
        }

    def _normalize_market_volume(self, symbol: str, requested_qty: Decimal, max_lot: Any = None, apply_demo_cap: bool = True) -> tuple[Optional[Decimal], dict[str, Any]]:
        limits = self._symbol_volume_limits(symbol)
        volume_min: Decimal = limits["volume_min"]
        volume_max: Decimal = limits["volume_max"]
        volume_step: Decimal = limits["volume_step"]
        demo_max_lot = self._demo_max_lot(max_lot)

        # Phase 12 is DEMO-only execution. Entry orders are capped by deployment/env.
        # Close orders pass apply_demo_cap=False so they can close the exact MT5 open lot.
        effective_max = volume_max
        if apply_demo_cap and demo_max_lot > 0:
            effective_max = min(volume_max, max(demo_max_lot, volume_min))

        requested = requested_qty if requested_qty and requested_qty > 0 else volume_min
        clamped = min(max(requested, volume_min), effective_max)
        normalized = _floor_to_step(clamped, volume_step)
        if normalized < volume_min:
            normalized = volume_min
        if normalized > effective_max:
            normalized = _floor_to_step(effective_max, volume_step)

        places = max(2, _decimal_places(volume_step))
        normalized = _fmt_decimal(normalized, places)
        debug = {
            "requested_volume": str(requested_qty),
            "normalized_volume": str(normalized),
            "volume_min": str(volume_min),
            "volume_max": str(volume_max),
            "volume_step": str(volume_step),
            "demo_max_lot": str(demo_max_lot),
            "effective_max": str(effective_max),
        }
        if normalized <= 0 or normalized < volume_min:
            return None, debug
        return normalized, debug

    def _resolve_trade_symbol(self, symbol: str) -> tuple[Optional[str], dict[str, Any]]:
        requested = str(symbol or "").strip()
        debug: dict[str, Any] = {"requested_symbol": requested, "candidates": []}
        if not requested or self.mt5 is None:
            return None, debug
        candidates = self._candidate_symbols(requested)
        debug["candidates"] = candidates
        for candidate in candidates:
            if not candidate:
                continue
            try:
                selected = bool(self.mt5.symbol_select(candidate, True))
                symbol_debug = self._symbol_debug(candidate)
                debug.setdefault("attempts", []).append({"symbol": candidate, "selected": selected, "symbol_info": symbol_debug, "last_error": self._last_error()})
                if selected:
                    return candidate, debug
            except Exception as exc:
                debug.setdefault("attempts", []).append({"symbol": candidate, "exception": str(exc), "last_error": self._last_error()})
        return None, debug

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
            resolved_symbol, debug = self._resolve_trade_symbol(symbol)
            if not resolved_symbol:
                return {"success": False, "message": f"No tradable MT5 symbol found for {symbol}", "symbol": symbol, "debug": debug, "last_error": self._last_error()}
            tick = self.mt5.symbol_info_tick(resolved_symbol)
            if tick is None:
                return {"success": False, "message": f"No quote for {resolved_symbol}: {self._last_error()}", "symbol": resolved_symbol, "debug": debug}
            data = _safe_obj(tick)
            return {
                "success": True,
                "symbol": resolved_symbol,
                "requested_symbol": symbol,
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
            resolved_symbol, symbol_debug = self._resolve_trade_symbol(order_request.symbol)
            if not resolved_symbol:
                return BrokerOrderResult(False, "ERROR", f"No tradable MT5 symbol found for {order_request.symbol}", raw_response={"symbol_debug": symbol_debug, "last_error": self._last_error()})

            tick = self.mt5.symbol_info_tick(resolved_symbol)
            if tick is None:
                return BrokerOrderResult(False, "ERROR", f"No quote found for {resolved_symbol}", raw_response={"symbol_debug": symbol_debug, "last_error": self._last_error()})

            side = order_request.side.upper()
            if side not in {"BUY", "SELL"}:
                return BrokerOrderResult(False, "ERROR", f"Unsupported MT5 order side: {order_request.side}", raw_response={"side": order_request.side})
            order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
            price = _decimal(getattr(tick, "ask", None) if side == "BUY" else getattr(tick, "bid", None))
            if price <= 0 and order_request.price:
                price = order_request.price
            if price <= 0:
                return BrokerOrderResult(False, "ERROR", f"No executable price for {resolved_symbol}", raw_response={"symbol_debug": symbol_debug, "tick": _safe_obj(tick), "last_error": self._last_error()})

            normalized_volume, volume_debug = self._normalize_market_volume(resolved_symbol, order_request.qty, max_lot=order_request.max_lot, apply_demo_cap=True)
            if normalized_volume is None:
                return BrokerOrderResult(
                    False,
                    "ERROR",
                    f"Invalid MT5 volume for {resolved_symbol}. Requested {order_request.qty}",
                    raw_response={"symbol_debug": symbol_debug, "volume_debug": volume_debug, "last_error": self._last_error()},
                )

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": resolved_symbol,
                "volume": float(normalized_volume),
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
            if isinstance(raw, dict):
                raw.setdefault("request", {**request, "price": str(price)})
                raw.setdefault("requested_symbol", order_request.symbol)
                raw.setdefault("resolved_symbol", resolved_symbol)
                raw.setdefault("volume_debug", volume_debug)
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

    def _symbol_key(self, value: Any) -> str:
        return str(value or "").strip().upper().replace(".", "").replace("_", "")

    def _symbol_matches(self, requested: str, resolved: str | None, actual: str) -> bool:
        req = self._symbol_key(requested)
        res = self._symbol_key(resolved)
        act = self._symbol_key(actual)
        if not act:
            return False
        if req and (act == req or act.startswith(req) or req.startswith(act)):
            return True
        if res and (act == res or act.startswith(res) or res.startswith(act)):
            return True
        return False

    def _position_matches_side(self, position: dict[str, Any], side: str) -> bool:
        side = str(side or "").upper()
        pos_type = position.get("type")
        try:
            pos_type_int = int(pos_type)
        except Exception:
            pos_type_int = -1
        # MT5: 0 = BUY position, 1 = SELL position.
        if side == "LONG":
            return pos_type_int == 0
        if side == "SHORT":
            return pos_type_int == 1
        return True

    async def close_position(self, position_id_or_symbol: str, side: str, qty: Decimal) -> BrokerOrderResult:
        ok, message = self._initialize()
        if not ok:
            return BrokerOrderResult(False, "ERROR", message, raw_response={"last_error": self._last_error()})
        try:
            requested = str(position_id_or_symbol or "").strip()
            resolved_symbol, symbol_debug = self._resolve_trade_symbol(requested)
            search_symbol = resolved_symbol or requested

            # Try the resolved MT5 symbol first (for XAUUSD -> XAUUSDm), then all positions.
            positions = self.mt5.positions_get(symbol=search_symbol) if search_symbol else None
            if not positions:
                positions = self.mt5.positions_get()
            if positions is None:
                return BrokerOrderResult(False, "ERROR", f"Unable to fetch MT5 positions: {self._last_error()}", raw_response={"last_error": self._last_error(), "requested": requested, "resolved_symbol": resolved_symbol, "symbol_debug": symbol_debug})

            target = None
            safe_positions = [_safe_obj(p) for p in positions]
            for data in safe_positions:
                ticket_matches = str(data.get("ticket")) == requested
                symbol_matches = self._symbol_matches(requested, resolved_symbol, str(data.get("symbol") or ""))
                side_matches = self._position_matches_side(data, side)
                if (ticket_matches or symbol_matches) and side_matches:
                    target = data
                    break

            if not target:
                return BrokerOrderResult(
                    False,
                    "ERROR",
                    "No matching MT5 position found",
                    raw_response={
                        "requested": requested,
                        "resolved_symbol": resolved_symbol,
                        "side": side,
                        "positions": safe_positions,
                        "symbol_debug": symbol_debug,
                    },
                )

            symbol = str(target.get("symbol") or search_symbol or requested)
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return BrokerOrderResult(False, "ERROR", f"No quote found for {symbol}", raw_response={"last_error": self._last_error(), "position": target, "requested": requested, "resolved_symbol": resolved_symbol})

            requested_close_qty = min(_decimal(qty, "0"), _decimal(target.get("volume"), "0"))
            if requested_close_qty <= 0:
                requested_close_qty = _decimal(target.get("volume"), "0")
            normalized_volume, volume_debug = self._normalize_market_volume(symbol, requested_close_qty, apply_demo_cap=False)
            if normalized_volume is None:
                return BrokerOrderResult(False, "ERROR", f"Invalid MT5 close volume for {symbol}", raw_response={"position": target, "volume_debug": volume_debug})

            close_side = "SELL" if side.upper() == "LONG" else "BUY"
            order_type = self.mt5.ORDER_TYPE_SELL if close_side == "SELL" else self.mt5.ORDER_TYPE_BUY
            price = _decimal(getattr(tick, "bid", None) if close_side == "SELL" else getattr(tick, "ask", None))
            if price <= 0:
                return BrokerOrderResult(False, "ERROR", f"No executable close price for {symbol}", raw_response={"tick": _safe_obj(tick), "position": target, "last_error": self._last_error()})

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(normalized_volume),
                "type": order_type,
                "position": int(target.get("ticket")),
                "price": float(price),
                "deviation": 20,
                "magic": 260426,
                "comment": "AlgoAgentX Demo Close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            response = self.mt5.order_send(request)
            raw = _safe_obj(response)
            if isinstance(raw, dict):
                raw.setdefault("request", {**request, "price": str(price)})
                raw.setdefault("position", target)
                raw.setdefault("requested_symbol", requested)
                raw.setdefault("resolved_symbol", resolved_symbol)
                raw.setdefault("volume_debug", volume_debug)
            retcode = raw.get("retcode") if isinstance(raw, dict) else None
            success_codes = {
                getattr(self.mt5, "TRADE_RETCODE_DONE", 10009),
                getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008),
            }
            if response is not None and retcode in success_codes:
                return BrokerOrderResult(
                    success=True,
                    status="FILLED",
                    message="MT5 demo position close order filled/placed",
                    broker_order_id=str(raw.get("order") or raw.get("deal") or ""),
                    executed_price=_decimal(raw.get("price"), str(price)),
                    raw_response=raw,
                )
            return BrokerOrderResult(False, "ERROR", f"MT5 close rejected: {raw}", raw_response=raw if isinstance(raw, dict) else {"response": raw})
        except Exception as exc:
            return BrokerOrderResult(False, "ERROR", f"MT5 close position error: {exc}", raw_response={"last_error": self._last_error()})

    async def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        ok, message = self._initialize()
        if not ok:
            return [{"success": False, "message": message}]
        try:
            requested_symbol = str(symbol or "").strip()
            resolved_symbol = None
            if requested_symbol:
                resolved_symbol, _debug = self._resolve_trade_symbol(requested_symbol)
            positions = self.mt5.positions_get(symbol=resolved_symbol) if resolved_symbol else self.mt5.positions_get()
            rows = [_safe_obj(p) for p in positions] if positions else []
            if requested_symbol:
                rows = [row for row in rows if isinstance(row, dict) and self._symbol_matches(requested_symbol, resolved_symbol, str(row.get("symbol") or ""))]
            return rows
        except Exception as exc:
            return [{"success": False, "message": str(exc), "last_error": self._last_error()}]

    async def get_deals_pnl(self, symbol: str | None = None, since: datetime | None = None) -> dict[str, Any]:
        ok, message = self._initialize()
        if not ok:
            return {"success": False, "message": message, "realized_pnl": "0", "deal_count": 0}
        try:
            now = datetime.now(timezone.utc)
            start = since or (now - timedelta(days=30))
            requested_symbol = str(symbol or "").strip()
            resolved_symbol = None
            if requested_symbol:
                resolved_symbol, _debug = self._resolve_trade_symbol(requested_symbol)
            deals = self.mt5.history_deals_get(start, now)
            safe_deals = [_safe_obj(d) for d in deals] if deals else []
            realized = Decimal("0")
            matched: list[dict[str, Any]] = []
            for deal in safe_deals:
                if not isinstance(deal, dict):
                    continue
                deal_symbol = str(deal.get("symbol") or "")
                if requested_symbol and not self._symbol_matches(requested_symbol, resolved_symbol, deal_symbol):
                    continue
                value = _decimal(deal.get("profit"), "0") + _decimal(deal.get("swap"), "0") + _decimal(deal.get("commission"), "0") + _decimal(deal.get("fee"), "0")
                realized += value
                matched.append(deal)
            return {
                "success": True,
                "requested_symbol": requested_symbol or None,
                "resolved_symbol": resolved_symbol,
                "realized_pnl": str(realized),
                "deal_count": len(matched),
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "realized_pnl": "0", "deal_count": 0, "last_error": self._last_error()}

    async def get_symbols(self, query: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        ok, message = self._initialize()
        if not ok:
            return [{"success": False, "message": message}]
        try:
            query_value = str(query or "").strip().upper()
            raw_symbols = self.mt5.symbols_get()
            rows: list[dict[str, Any]] = []
            for sym in raw_symbols or []:
                data = _safe_obj(sym)
                name = str(data.get("name") or "")
                path = str(data.get("path") or "")
                if query_value and query_value not in name.upper() and query_value not in path.upper():
                    continue
                # Prefer visible/selectable trade symbols and skip empty names.
                if not name:
                    continue
                rows.append({
                    "symbol": name,
                    "name": name,
                    "path": path,
                    "description": data.get("description"),
                    "visible": data.get("visible"),
                    "trade_mode": data.get("trade_mode"),
                    "volume_min": data.get("volume_min"),
                    "volume_max": data.get("volume_max"),
                    "volume_step": data.get("volume_step"),
                })
                if len(rows) >= max(1, min(int(limit or 200), 500)):
                    break
            return rows
        except Exception as exc:
            return [{"success": False, "message": str(exc), "last_error": self._last_error()}]

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
