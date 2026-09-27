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
            trade_mode_raw = getattr(account, "trade_mode", None)
            account_mode = None
            try:
                trade_mode_int = int(trade_mode_raw) if trade_mode_raw is not None else None
                demo_const = getattr(self.mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
                contest_const = getattr(self.mt5, "ACCOUNT_TRADE_MODE_CONTEST", 1)
                real_const = getattr(self.mt5, "ACCOUNT_TRADE_MODE_REAL", 2)
                if trade_mode_int == int(demo_const):
                    account_mode = "DEMO"
                elif trade_mode_int == int(contest_const):
                    account_mode = "CONTEST"
                elif trade_mode_int == int(real_const):
                    account_mode = "LIVE"
            except Exception:
                trade_mode_int = None
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
                    "account_trade_mode": trade_mode_int,
                    "account_mode": account_mode,
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
    def _symbol_pair_root(cls, value: Any) -> str:
        key = cls._symbol_key(value)
        if len(key) >= 6 and key[:6].isalpha():
            return key[:6]
        return key

    @classmethod
    def _symbol_match_score(cls, requested: Any, actual: Any) -> int | None:
        req = cls._symbol_key(requested)
        act = cls._symbol_key(actual)
        if not req or not act:
            return None
        if req == act:
            return 0
        req_root = cls._symbol_pair_root(req)
        act_root = cls._symbol_pair_root(act)
        if req_root and act_root and req_root == act_root and len(req_root) >= 6:
            return 10 + abs(len(req) - len(act))
        if min(len(req), len(act)) >= 5 and (req.startswith(act) or act.startswith(req)):
            return 30 + abs(len(req) - len(act))
        return None

    def _resolve_trade_symbol(self, requested: Any) -> str | None:
        """Resolve a canonical symbol to a tradable terminal symbol with a live tick.

        Some brokers expose both ``XAUUSD`` and ``XAUUSDm`` while only the
        suffixed symbol has an active quote. ``symbol_select(XAUUSD)`` may still
        succeed, so accepting the first selectable symbol can later fail with
        ``No MT5 tick found``. Rank exact/alias candidates and require a live tick
        before selecting the execution symbol.
        """
        symbol = str(requested or "").strip()
        if not symbol or self.mt5 is None:
            return None

        ranked: list[tuple[int, int, str]] = []
        seen: set[str] = set()

        def add_candidate(name: str, score: int) -> None:
            clean = str(name or "").strip()
            key = clean.upper()
            if clean and key not in seen:
                seen.add(key)
                ranked.append((score, len(clean), clean))

        add_candidate(symbol, 0)
        try:
            for item in self.mt5.symbols_get() or []:
                name = str(getattr(item, "name", "") or "").strip()
                if not name:
                    continue
                score = self._symbol_match_score(symbol, name)
                if score is not None:
                    add_candidate(name, score)
        except Exception:
            pass

        ranked.sort(key=lambda row: (row[0], row[1]))
        fallback_selected: str | None = None
        for _score, _length, candidate in ranked:
            try:
                if not self.mt5.symbol_select(candidate, True):
                    continue
                fallback_selected = fallback_selected or candidate
                tick_getter = getattr(self.mt5, "symbol_info_tick", None)
                # Real MetaTrader5 exposes symbol_info_tick(). Keep compatibility
                # with lightweight/offline harnesses that only provide symbol_select.
                if not callable(tick_getter):
                    return candidate
                tick = tick_getter(candidate)
                if tick is not None:
                    return candidate
            except Exception:
                continue

        # A selected symbol with no tick is not safe for market execution.
        # Returning None makes the failure explicit instead of sending at stale/zero price.
        return None

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

    def get_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        if self.mt5 is None or not symbols:
            return []
        if not self.initialize():
            return []
        rows: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for requested in symbols:
            symbol = str(requested or "").strip()
            if not symbol:
                continue
            try:
                resolved = self._resolve_trade_symbol(symbol)
                if not resolved:
                    continue
                symbol = resolved
                tick = self.mt5.symbol_info_tick(symbol)
                if tick is None:
                    continue
                raw = self._safe_obj(tick)
                bid = raw.get("bid")
                ask = raw.get("ask")
                last = raw.get("last") or bid or ask
                if last is None:
                    continue
                time_msc = raw.get("time_msc")
                market_time = None
                if time_msc:
                    market_time = datetime.fromtimestamp(float(time_msc) / 1000.0, tz=timezone.utc)
                elif raw.get("time"):
                    market_time = datetime.fromtimestamp(int(raw.get("time")), tz=timezone.utc)
                rows.append({
                    "symbol": str(requested).upper(),
                    "resolved_symbol": symbol,
                    "bid": float(bid) if bid is not None else None,
                    "ask": float(ask) if ask is not None else None,
                    "last": float(last),
                    "market_timestamp": (market_time or now).isoformat(),
                    "raw": {"resolved_symbol": symbol, "time_msc": time_msc},
                })
            except Exception:
                continue
        return rows

    def fetch_symbols(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.mt5 is None:
            return {"success": False, "message": f"MetaTrader5 Python package is not available: {self._import_error or 'not installed'}", "symbols": [], "raw": {"symbols": []}}
        if not self.initialize():
            last_error = None
            try:
                last_error = self.mt5.last_error()
            except Exception:
                pass
            return {"success": False, "message": "MT5 terminal is not connected.", "symbols": [], "raw": {"symbols": [], "last_error": str(last_error)}}

        payload = command.get("request_payload") or {}
        query = str(payload.get("query") or "").strip().upper()
        limit = max(1, min(int(payload.get("limit") or 200), 500))
        try:
            symbols = self.mt5.symbols_get() or []
            rows: list[dict[str, Any]] = []
            for item in symbols:
                raw = self._safe_obj(item)
                name = str(raw.get("name") or "").strip()
                path = str(raw.get("path") or "").strip()
                description = str(raw.get("description") or "").strip()
                if not name:
                    continue
                if query and query not in name.upper() and query not in path.upper() and query not in description.upper():
                    continue
                rows.append({
                    "symbol": name,
                    "name": name,
                    "path": path or None,
                    "description": description or None,
                    "visible": raw.get("visible"),
                    "trade_mode": raw.get("trade_mode"),
                    "volume_min": raw.get("volume_min"),
                    "volume_max": raw.get("volume_max"),
                    "volume_step": raw.get("volume_step"),
                    "digits": raw.get("digits"),
                    "point": raw.get("point"),
                })
                if len(rows) >= limit:
                    break
            return {"success": True, "message": f"Fetched {len(rows)} MT5 symbols", "symbols": rows, "raw": {"symbols": rows, "count": len(rows)}}
        except Exception as exc:
            return {"success": False, "message": f"MT5 FETCH_SYMBOLS failed: {exc}", "symbols": [], "raw": {"symbols": []}}

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
            requested_symbol = symbol
            resolved_symbol = self._resolve_trade_symbol(requested_symbol)
            if not resolved_symbol:
                return {"success": False, "message": f"MT5 symbol resolution failed for {requested_symbol}. In Market Watch, right click → Show All, then try again.", "raw": {"last_error": str(self.mt5.last_error()), "requested_symbol": requested_symbol}}
            symbol = resolved_symbol
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

    def close_position(self, command: dict[str, Any], enable_order_execution: bool = False) -> dict[str, Any]:
        """Close an existing MT5 position ticket without requiring SL/TP.

        On hedging accounts an opposite market order can create a second position;
        the ``position`` field is therefore sent whenever a ticket is available.
        """
        if not enable_order_execution:
            return {"success": False, "message": "Order execution is disabled in agent config. Set ENABLE_ORDER_EXECUTION=true only after demo testing.", "raw": {}}
        if self.mt5 is None or not self.initialize():
            return {"success": False, "message": "MT5 terminal is not connected.", "raw": {}}

        payload = command.get("request_payload") or {}
        ticket_raw = str(payload.get("position_ticket") or "").strip()
        requested_symbol = str(payload.get("symbol") or "").strip()
        requested_qty = float(payload.get("qty") or 0)

        positions = []
        try:
            if ticket_raw.isdigit():
                positions = list(self.mt5.positions_get(ticket=int(ticket_raw)) or [])
            elif requested_symbol:
                # Use all positions then alias-match locally so XAUUSD can match XAUUSDm.
                positions = [
                    p for p in (self.mt5.positions_get() or [])
                    if self._symbols_match(requested_symbol, getattr(p, "symbol", None))
                ]
        except Exception as exc:
            return {"success": False, "message": f"MT5 position lookup failed: {exc}", "raw": {"payload": payload}}

        if not positions:
            return {"success": False, "message": f"MT5 position was not found for ticket/symbol {ticket_raw or requested_symbol}.", "raw": {"payload": payload}}

        # Ticket lookups should return exactly one row. Symbol fallback intentionally
        # closes one position per command; the backend queues one command per tracked row.
        pos = positions[0]
        raw_pos = self._safe_obj(pos)
        ticket = int(raw_pos.get("ticket") or 0)
        symbol = str(raw_pos.get("symbol") or requested_symbol).strip()
        if not ticket or not symbol:
            return {"success": False, "message": "MT5 position ticket/symbol is unavailable.", "raw": {"payload": payload, "position": raw_pos}}

        try:
            self.mt5.symbol_select(symbol, True)
            tick = self.mt5.symbol_info_tick(symbol)
        except Exception:
            tick = None
        if tick is None:
            resolved = self._resolve_trade_symbol(symbol)
            if resolved:
                symbol = resolved
                tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "message": f"No MT5 tick found for {symbol}.", "raw": {"payload": payload, "position": raw_pos}}

        pos_type = int(raw_pos.get("type") or 0)
        is_buy_position = pos_type == getattr(self.mt5, "POSITION_TYPE_BUY", 0)
        order_type = self.mt5.ORDER_TYPE_SELL if is_buy_position else self.mt5.ORDER_TYPE_BUY
        price = float(tick.bid if is_buy_position else tick.ask)
        position_volume = float(raw_pos.get("volume") or 0)
        volume = min(requested_qty if requested_qty > 0 else position_volume, position_volume)
        if volume <= 0:
            return {"success": False, "message": "MT5 close volume is zero.", "raw": {"payload": payload, "position": raw_pos}}

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": int(payload.get("deviation") or self.default_deviation),
            "magic": 260510,
            "comment": str(payload.get("comment") or "AlgoAgentX MT5 close")[:31],
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        result = self.mt5.order_send(request)
        raw = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        if isinstance(raw, dict):
            raw.setdefault("request", request)
            raw.setdefault("position_ticket", str(ticket))
            raw.setdefault("resolved_symbol", symbol)
        retcode = raw.get("retcode")
        ok_codes = {getattr(self.mt5, "TRADE_RETCODE_DONE", 10009), getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008)}
        success = retcode in ok_codes
        broker_order_id = raw.get("order") or raw.get("deal")
        executed_price = raw.get("price") or price
        return {
            "success": bool(success),
            "message": raw.get("comment") or ("Position closed" if success else "MT5 close failed"),
            "broker_order_id": str(broker_order_id) if broker_order_id not in (None, "", 0) else None,
            "executed_price": executed_price,
            "raw": raw,
        }

    def place_order(self, command: dict[str, Any], enable_order_execution: bool = False) -> dict[str, Any]:
        if not enable_order_execution:
            return {"success": False, "message": "Order execution is disabled in agent config. Set ENABLE_ORDER_EXECUTION=true only after demo testing.", "raw": {}}
        if self.mt5 is None or not self.initialize():
            return {"success": False, "message": "MT5 terminal is not connected.", "raw": {}}

        payload = command.get("request_payload") or {}
        requested_symbol = str(payload.get("symbol") or "").strip()
        side = str(payload.get("side") or "BUY").upper()
        volume = float(payload.get("qty") or payload.get("volume") or 0)
        if not requested_symbol or volume <= 0:
            return {"success": False, "message": "Invalid MT5 order command: symbol and qty are required.", "raw": payload}

        symbol = self._resolve_trade_symbol(requested_symbol)
        if not symbol:
            return {"success": False, "message": f"MT5 symbol {requested_symbol} was not found on this terminal.", "raw": {"payload": payload, "requested_symbol": requested_symbol}}
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "message": f"No MT5 tick found for {symbol}.", "raw": {"payload": payload, "requested_symbol": requested_symbol, "resolved_symbol": symbol}}

        order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        sl = payload.get("stop_loss")
        tp = payload.get("target")
        if sl in (None, "", 0, "0") or tp in (None, "", 0, "0"):
            return {"success": False, "message": "SL/TP missing or zero. Agent blocked order for safety.", "raw": {"payload": payload}}

        try:
            source_sl = float(sl)
            source_tp = float(tp)
        except (TypeError, ValueError):
            return {"success": False, "message": "SL/TP is not numeric. Agent blocked order for safety.", "raw": {"payload": payload}}

        is_copy_execution = bool(payload.get("is_copy_execution"))
        source_broker_code = str(payload.get("source_broker_code") or "").upper() or None
        client_order_id = str(payload.get("client_order_id") or payload.get("idempotency_key") or "")
        comment = str(payload.get("comment") or ("AX-" + client_order_id[-12:] if client_order_id else "AlgoAgentX MT5 Agent"))[:31]

        info = None
        info_getter = getattr(self.mt5, "symbol_info", None)
        if callable(info_getter):
            try:
                info = info_getter(symbol)
            except Exception:
                info = None
        try:
            digits = max(0, int(getattr(info, "digits", 5) if info is not None else 5))
        except Exception:
            digits = 5
        default_point = 10 ** (-digits) if digits > 0 else 1.0
        try:
            point = float(getattr(info, "point", default_point) if info is not None else default_point) or default_point
        except Exception:
            point = default_point
        try:
            trade_stops_level = max(0, int(getattr(info, "trade_stops_level", 0) if info is not None else 0))
        except Exception:
            trade_stops_level = 0
        min_stop_distance = float(trade_stops_level) * point

        def _build_request(live_tick: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
            bid = float(getattr(live_tick, "bid", 0) or 0)
            ask = float(getattr(live_tick, "ask", 0) or 0)
            if bid <= 0 or ask <= 0:
                return None, {"message": f"Invalid MT5 live quote for {symbol}.", "bid": bid, "ask": ask}

            live_price = ask if side == "BUY" else bid
            try:
                source_price = float(payload.get("price") or live_price)
            except (TypeError, ValueError):
                source_price = live_price

            # For a copy target, preserve the strategy's SL/TP distances instead
            # of forwarding absolute levels from a different broker quote.  This
            # is the narrow cross-broker fix for cTrader -> MT5 (and is also safe
            # for MT5 -> MT5 accounts with slightly different quotes).
            price_offset = (live_price - source_price) if is_copy_execution else 0.0
            sl_f = round(source_sl + price_offset, digits)
            tp_f = round(source_tp + price_offset, digits)
            request_price = round(live_price, digits)

            # MT5 validates protection from the side on which the position would
            # be closed: BUY protection is triggered on Bid, SELL on Ask.
            trigger_price = bid if side == "BUY" else ask
            if side == "BUY" and not (sl_f < trigger_price < tp_f):
                return None, {
                    "message": "Invalid BUY SL/TP against current MT5 Bid after copy-price translation.",
                    "trigger_price": trigger_price, "price": request_price, "sl": sl_f, "tp": tp_f,
                    "source_price": source_price, "price_offset": price_offset,
                }
            if side == "SELL" and not (tp_f < trigger_price < sl_f):
                return None, {
                    "message": "Invalid SELL SL/TP against current MT5 Ask after copy-price translation.",
                    "trigger_price": trigger_price, "price": request_price, "sl": sl_f, "tp": tp_f,
                    "source_price": source_price, "price_offset": price_offset,
                }

            sl_distance = (trigger_price - sl_f) if side == "BUY" else (sl_f - trigger_price)
            tp_distance = (tp_f - trigger_price) if side == "BUY" else (trigger_price - tp_f)
            # Do not silently widen strategy protection: if the target broker's
            # minimum stop level is larger, fail this copy account safely and
            # report the exact required distance.
            if min_stop_distance > 0 and (sl_distance + (point / 10.0) < min_stop_distance or tp_distance + (point / 10.0) < min_stop_distance):
                return None, {
                    "message": (
                        f"MT5 broker minimum stop distance is {min_stop_distance:.{digits}f} for {symbol}; "
                        f"translated SL distance={sl_distance:.{digits}f}, TP distance={tp_distance:.{digits}f}."
                    ),
                    "trigger_price": trigger_price, "price": request_price, "sl": sl_f, "tp": tp_f,
                    "sl_distance": sl_distance, "tp_distance": tp_distance,
                    "trade_stops_level": trade_stops_level, "point": point,
                    "source_price": source_price, "price_offset": price_offset,
                }

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                # MARKET orders must use the target terminal's current executable
                # price, never a candle/source-broker reference price.
                "price": request_price,
                "deviation": int(payload.get("deviation") or self.default_deviation),
                "magic": 260510,
                "comment": comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
                "sl": sl_f,
                "tp": tp_f,
            }
            debug = {
                "is_copy_execution": is_copy_execution,
                "source_broker_code": source_broker_code,
                "source_price": source_price,
                "source_stop_loss": source_sl,
                "source_target": source_tp,
                "target_live_price": live_price,
                "target_bid": bid,
                "target_ask": ask,
                "price_offset": price_offset,
                "translated_stop_loss": sl_f,
                "translated_target": tp_f,
                "digits": digits,
                "point": point,
                "trade_stops_level": trade_stops_level,
                "min_stop_distance": min_stop_distance,
            }
            return request, debug

        request, protection_debug = _build_request(tick)
        if request is None:
            return {
                "success": False,
                "message": str(protection_debug.get("message") or "MT5 SL/TP validation failed."),
                "raw": {
                    "payload": payload,
                    "requested_symbol": requested_symbol,
                    "resolved_symbol": symbol,
                    "protection_debug": protection_debug,
                },
            }

        result = self.mt5.order_send(request)
        raw = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        if not isinstance(raw, dict):
            raw = {"result": str(raw)}

        invalid_stops_code = getattr(self.mt5, "TRADE_RETCODE_INVALID_STOPS", 10016)
        first_attempt_raw = dict(raw)
        retried_invalid_stops = False

        # A broker rejection with INVALID_STOPS means no trade was opened, so one
        # copy-only refresh/rebuild retry is safe and cannot duplicate a fill.
        if is_copy_execution and raw.get("retcode") == invalid_stops_code:
            retry_tick = self.mt5.symbol_info_tick(symbol)
            retry_request, retry_debug = _build_request(retry_tick) if retry_tick is not None else (None, {"message": "No fresh MT5 tick for invalid-stops retry."})
            if retry_request is not None:
                retried_invalid_stops = True
                retry_result = self.mt5.order_send(retry_request)
                retry_raw = retry_result._asdict() if hasattr(retry_result, "_asdict") else {"result": str(retry_result)}
                raw = dict(retry_raw) if isinstance(retry_raw, dict) else {"result": str(retry_raw)}
                request = retry_request
                protection_debug = retry_debug

        raw.setdefault("request", request)
        raw.setdefault("client_order_id", client_order_id or None)
        raw.setdefault("requested_symbol", requested_symbol)
        raw.setdefault("resolved_symbol", symbol)
        raw.setdefault("protection_debug", protection_debug)
        if retried_invalid_stops:
            raw.setdefault("invalid_stops_retry", {"attempted": True, "first_attempt": first_attempt_raw})

        retcode = raw.get("retcode")
        ok_codes = {getattr(self.mt5, "TRADE_RETCODE_DONE", 10009), getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008)}
        success = retcode in ok_codes
        return {
            "success": bool(success),
            "message": raw.get("comment") or ("Order sent" if success else "MT5 order failed"),
            "raw": raw,
            "broker_order_id": str(raw.get("order") or raw.get("deal") or "") or None,
            "executed_price": raw.get("price") or request.get("price"),
        }
