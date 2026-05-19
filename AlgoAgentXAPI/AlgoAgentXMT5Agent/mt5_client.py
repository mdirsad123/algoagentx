from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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
                    **self._positions_metadata_safe(),
                },
            )
        except Exception as exc:
            return MT5Status(False, "TERMINAL_STATUS_ERROR", metadata={"error": str(exc)})


    def _safe_obj(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "_asdict"):
            try:
                return dict(value._asdict())
            except Exception:
                pass
        if isinstance(value, dict):
            return dict(value)
        try:
            return {name: getattr(value, name) for name in dir(value) if not name.startswith("_") and not callable(getattr(value, name, None))}
        except Exception:
            return {"raw": str(value)}

    @staticmethod
    def _symbol_key(value: Any) -> str:
        return str(value or "").strip().upper().replace(".", "").replace("_", "").replace("-", "")

    @classmethod
    def _symbols_match(cls, requested: Any, actual: Any) -> bool:
        req = cls._symbol_key(requested)
        act = cls._symbol_key(actual)
        if not req or not act:
            return False
        return req == act or act.startswith(req) or req.startswith(act)

    @staticmethod
    def _parse_iso_datetime(value: Any, default: datetime) -> datetime:
        if not value:
            return default
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return default

    def get_open_positions(self) -> list[dict[str, Any]]:
        if self.mt5 is None:
            return []
        if not self.initialize():
            return []
        try:
            positions = self.mt5.positions_get()
            rows: list[dict[str, Any]] = []
            for pos in positions or []:
                raw = self._safe_obj(pos)
                pos_type = int(raw.get("type") or 0)
                rows.append({
                    "ticket": str(raw.get("ticket") or ""),
                    "symbol": raw.get("symbol"),
                    "type": pos_type,
                    "side": "BUY" if pos_type == getattr(self.mt5, "POSITION_TYPE_BUY", 0) else "SELL",
                    "volume": float(raw.get("volume") or 0),
                    "price_open": float(raw.get("price_open") or 0),
                    "price_current": float(raw.get("price_current") or 0),
                    "sl": float(raw.get("sl") or 0),
                    "tp": float(raw.get("tp") or 0),
                    "profit": float(raw.get("profit") or 0),
                    "swap": float(raw.get("swap") or 0),
                    "commission": float(raw.get("commission") or 0),
                    "magic": int(raw.get("magic") or 0),
                    "comment": raw.get("comment"),
                    "time": int(raw.get("time") or 0),
                    "time_msc": int(raw.get("time_msc") or 0),
                    "raw": raw,
                })
            return rows
        except Exception:
            return []



    def _positions_metadata_safe(self) -> dict[str, Any]:
        try:
            positions = self.get_open_positions()
            return {"positions": positions, "positions_count": len(positions)}
        except Exception as exc:
            return {"positions": [], "positions_count": 0, "positions_error": str(exc)}

    def fetch_rates(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.mt5 is None:
            return {"success": False, "message": f"MetaTrader5 Python package is not available: {self._import_error or 'not installed'}", "raw": {}}
        if not self.initialize():
            last_error = None
            try:
                last_error = self.mt5.last_error()
            except Exception:
                pass
            return {"success": False, "message": "MT5 terminal is not connected.", "raw": {"last_error": str(last_error)}}

        payload = command.get("request_payload") or {}
        symbol = str(payload.get("symbol") or "").strip()
        timeframe = str(payload.get("timeframe") or "").strip().upper()
        count = max(1, min(int(payload.get("count") or 300), 5000))
        skip_forming = bool(payload.get("skip_forming", True))

        if not symbol:
            return {"success": False, "message": "FETCH_RATES requires symbol.", "raw": payload}

        timeframe_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "1M": self.mt5.TIMEFRAME_M1,
            "M5": self.mt5.TIMEFRAME_M5,
            "5M": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15,
            "15M": self.mt5.TIMEFRAME_M15,
            "M30": self.mt5.TIMEFRAME_M30,
            "30M": self.mt5.TIMEFRAME_M30,
            "H1": self.mt5.TIMEFRAME_H1,
            "1H": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4,
            "4H": self.mt5.TIMEFRAME_H4,
            "D1": self.mt5.TIMEFRAME_D1,
            "1D": self.mt5.TIMEFRAME_D1,
        }
        timeframe_const = timeframe_map.get(timeframe)
        if timeframe_const is None:
            return {"success": False, "message": f"Unsupported MT5 timeframe: {timeframe}", "raw": payload}

        try:
            if not self.mt5.symbol_select(symbol, True):
                return {"success": False, "message": f"MT5 symbol_select failed for {symbol}. In Market Watch, right click → Show All, then try again.", "raw": {"last_error": str(self.mt5.last_error())}}
            start_pos = 1 if skip_forming else 0
            rates = self.mt5.copy_rates_from_pos(symbol, timeframe_const, start_pos, count)
            if rates is None or len(rates) == 0:
                return {
                    "success": False,
                    "message": f"No MT5 candles returned for {symbol} {timeframe}. In MT5, open Market Watch, Show All, open the symbol chart once, then try again.",
                    "raw": {"symbol": symbol, "timeframe": timeframe, "count": count, "last_error": str(self.mt5.last_error())},
                }

            candles: list[dict[str, Any]] = []
            for rate in rates:
                raw = {}
                try:
                    raw = {name: rate[name].item() if hasattr(rate[name], "item") else rate[name] for name in rate.dtype.names}
                except Exception:
                    raw = dict(rate) if isinstance(rate, dict) else {"rate": str(rate)}
                timestamp = int(raw.get("time") or 0)
                candle_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp else None
                volume = raw.get("tick_volume") or raw.get("real_volume") or 0
                candles.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candle_time": candle_time,
                    "open": float(raw.get("open") or 0),
                    "high": float(raw.get("high") or 0),
                    "low": float(raw.get("low") or 0),
                    "close": float(raw.get("close") or 0),
                    "volume": float(volume or 0),
                    "raw_payload": raw,
                })

            return {
                "success": True,
                "message": f"Fetched {len(candles)} MT5 candles",
                "candles": candles,
                "raw": {"candles": candles, "count": len(candles), "symbol": symbol, "timeframe": timeframe},
            }
        except Exception as exc:
            return {"success": False, "message": f"MT5 FETCH_RATES failed: {exc}", "raw": payload}


    def fetch_deals_pnl(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.mt5 is None:
            return {"success": False, "message": f"MetaTrader5 Python package is not available: {self._import_error or 'not installed'}", "raw": {"realized_pnl": 0, "deal_count": 0, "deals": []}}
        if not self.initialize():
            last_error = None
            try:
                last_error = self.mt5.last_error()
            except Exception:
                pass
            return {"success": False, "message": "MT5 terminal is not connected.", "raw": {"last_error": str(last_error), "realized_pnl": 0, "deal_count": 0, "deals": []}}

        payload = command.get("request_payload") or {}
        symbol = str(payload.get("symbol") or "").strip()
        now = datetime.now(timezone.utc)
        since = self._parse_iso_datetime(payload.get("since"), datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc))
        until = self._parse_iso_datetime(payload.get("until"), now)
        magic = int(payload.get("magic") or 260510)
        comment_prefix = str(payload.get("comment_prefix") or "AlgoAgentX")
        allow_symbol_only = bool(payload.get("allow_symbol_only_fallback", True))

        try:
            deals = self.mt5.history_deals_get(since, until)
            raw_deals = [self._safe_obj(d) for d in deals] if deals else []
            matched: list[dict[str, Any]] = []
            gross_profit = 0.0
            commission_total = 0.0
            swap_total = 0.0
            fee_total = 0.0

            for deal in raw_deals:
                deal_symbol = str(deal.get("symbol") or "").strip()
                if symbol and not self._symbols_match(symbol, deal_symbol):
                    continue
                has_symbol = bool(deal_symbol)
                if not has_symbol:
                    # Balance/deposit/credit rows do not belong to a deployment symbol.
                    continue
                deal_magic = int(deal.get("magic") or 0)
                comment = str(deal.get("comment") or "")
                is_algo = (deal_magic == magic) or (comment_prefix.lower() in comment.lower())
                if not is_algo and not allow_symbol_only:
                    continue

                profit = float(deal.get("profit") or 0)
                commission = float(deal.get("commission") or 0)
                swap = float(deal.get("swap") or 0)
                fee = float(deal.get("fee") or 0)
                net = profit + commission + swap + fee
                gross_profit += profit
                commission_total += commission
                swap_total += swap
                fee_total += fee
                matched.append({
                    "ticket": str(deal.get("ticket") or ""),
                    "order": str(deal.get("order") or ""),
                    "position_id": str(deal.get("position_id") or ""),
                    "symbol": deal_symbol,
                    "type": deal.get("type"),
                    "entry": deal.get("entry"),
                    "volume": float(deal.get("volume") or 0),
                    "price": float(deal.get("price") or 0),
                    "profit": profit,
                    "commission": commission,
                    "swap": swap,
                    "fee": fee,
                    "net_profit": net,
                    "magic": deal_magic,
                    "comment": comment,
                    "time": int(deal.get("time") or 0),
                    "time_msc": int(deal.get("time_msc") or 0),
                    "raw": deal,
                })

            net_total = gross_profit + commission_total + swap_total + fee_total
            raw = {
                "realized_pnl": net_total,
                "gross_profit": gross_profit,
                "commission": commission_total,
                "swap": swap_total,
                "fee": fee_total,
                "net_profit": net_total,
                "deal_count": len(matched),
                "deals": matched,
                "symbol": symbol,
                "since": since.isoformat(),
                "until": until.isoformat(),
            }
            return {
                "success": True,
                "message": f"Fetched {len(matched)} MT5 deals",
                "realized_pnl": net_total,
                "gross_profit": gross_profit,
                "commission": commission_total,
                "swap": swap_total,
                "fee": fee_total,
                "net_profit": net_total,
                "deal_count": len(matched),
                "deals": matched,
                "raw": raw,
            }
        except Exception as exc:
            return {"success": False, "message": f"MT5 FETCH_DEALS_PNL failed: {exc}", "raw": {"realized_pnl": 0, "deal_count": 0, "deals": []}}

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
