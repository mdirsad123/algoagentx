from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .base import MarketDataProvider
from .errors import ProviderFetchError


def _safe_obj(value: Any) -> Any:
    """Convert MetaTrader5/numpy objects into JSON-safe Python values."""
    if hasattr(value, "dtype") and getattr(value.dtype, "names", None):
        return {str(key): _safe_obj(value[key]) for key in value.dtype.names}
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return _safe_obj(value.item())
        except Exception:
            pass
    if hasattr(value, "_asdict"):
        return {str(key): _safe_obj(val) for key, val in value._asdict().items()}
    if isinstance(value, dict):
        return {str(key): _safe_obj(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_obj(item) for item in value]
    return value


class MT5MarketDataProvider(MarketDataProvider):
    """Historical candle provider for MetaTrader 5.

    Important production rule: MT5 broker symbols are broker-specific and often
    case-sensitive. For example, Exness demo accounts often use XAUUSDm/XAGUSDm/BTCUSDm, while other brokers may use XAUUSDc or XAUUSD.m. This provider therefore always gives priority to the
    exact symbol sent by the UI / Market Master broker_symbol.
    """

    name = "MT5"

    _TIMEFRAME_MAP = {
        "1m": "TIMEFRAME_M1",
        "m1": "TIMEFRAME_M1",
        "5m": "TIMEFRAME_M5",
        "m5": "TIMEFRAME_M5",
        "15m": "TIMEFRAME_M15",
        "m15": "TIMEFRAME_M15",
        "30m": "TIMEFRAME_M30",
        "m30": "TIMEFRAME_M30",
        "1h": "TIMEFRAME_H1",
        "h1": "TIMEFRAME_H1",
        "60m": "TIMEFRAME_H1",
        "4h": "TIMEFRAME_H4",
        "h4": "TIMEFRAME_H4",
        "1d": "TIMEFRAME_D1",
        "d1": "TIMEFRAME_D1",
    }

    _TIMEFRAME_MINUTES = {
        "1m": 1,
        "m1": 1,
        "5m": 5,
        "m5": 5,
        "15m": 15,
        "m15": 15,
        "30m": 30,
        "m30": 30,
        "1h": 60,
        "h1": 60,
        "60m": 60,
        "4h": 240,
        "h4": 240,
        "1d": 1440,
        "d1": 1440,
    }

    _KNOWN_SUFFIXES = ("c", "m", ".m", ".c", "_m", "_c", "-m", "-c", "pro", ".pro", "#")

    def __init__(self) -> None:
        self.mt5 = None
        self.import_error: str | None = None
        try:  # pragma: no cover - depends on local Windows/MT5 installation
            import MetaTrader5 as mt5  # type: ignore

            self.mt5 = mt5
        except Exception as exc:  # pragma: no cover
            self.import_error = str(exc)

    def _last_error(self) -> Any:
        try:
            return _safe_obj(self.mt5.last_error()) if self.mt5 else None
        except Exception:
            return None

    def _terminal_info(self) -> Any:
        try:
            return _safe_obj(self.mt5.terminal_info()) if self.mt5 else None
        except Exception:
            return None

    def _timeframe_constant(self, timeframe: str) -> Any:
        tf = str(timeframe or "").strip().lower()
        attr = self._TIMEFRAME_MAP.get(tf)
        if not attr or self.mt5 is None:
            return None
        return getattr(self.mt5, attr, None)

    def _ensure_package_available(self) -> None:
        if self.mt5 is None:
            raise ProviderFetchError(
                "MT5 package not installed or MetaTrader 5 terminal not available. "
                "Install the MetaTrader5 Python package and MetaTrader 5 terminal on this machine."
            )

    def _initialize(self) -> None:
        self._ensure_package_available()
        try:
            ok = bool(self.mt5.initialize())
        except Exception as exc:
            raise ProviderFetchError(f"MT5 initialize failed: {exc}") from exc
        if not ok:
            raise ProviderFetchError(
                f"MT5 initialize failed. Start the MT5 terminal, login to the demo account, then retry. Last error: {self._last_error()}"
            )

    def _symbol_name(self, item: Any) -> str | None:
        data = _safe_obj(item)
        if isinstance(data, dict):
            value = data.get("name") or data.get("symbol")
            return str(value) if value else None
        return None

    def _compact(self, value: str) -> str:
        return str(value or "").upper().replace(".", "").replace("-", "").replace("_", "")

    def _base6(self, value: str) -> str:
        return self._compact(value)[:6]

    def _looks_like_exact_broker_symbol(self, symbol: str) -> bool:
        requested = str(symbol or "").strip()
        compact = self._compact(requested)
        # XAUUSDc / XAGUSDm / GBPUSD.pro etc. should be treated as exact.
        if len(compact) > 6 and compact[:6].isalpha():
            return True
        lower = requested.lower()
        return any(lower.endswith(s) for s in self._KNOWN_SUFFIXES)

    def _candidate_symbols(self, symbol: str, *, exact_first: bool = True) -> list[str]:
        requested = str(symbol or "").strip()
        if not requested or self.mt5 is None:
            return [requested]

        candidates: list[str] = []

        def add(value: str | None) -> None:
            clean = str(value or "").strip()
            if clean and clean not in candidates:
                candidates.append(clean)

        add(requested)
        base6 = self._base6(requested)
        requested_is_exact = self._looks_like_exact_broker_symbol(requested)

        # First discover symbols that are the exact requested value or close aliases.
        exact_patterns = [requested, f"{requested}*"]
        for pattern in exact_patterns:
            try:
                for item in self.mt5.symbols_get(pattern) or []:
                    name = self._symbol_name(item)
                    if name and name.lower() == requested.lower():
                        add(name)
            except Exception:
                continue

        # If Market Master sent an exact broker symbol (XAUUSDc), do NOT silently
        # switch to another broker suffix (XAUUSDm). That creates fake success with
        # 1 candle and saves data under the wrong instrument.
        if requested_is_exact and exact_first:
            return candidates[:10]

        # For clean internal symbols (XAUUSD), try common broker suffixes.
        suffixes = ["c", "m", ".m", ".c", "_m", "_c", "-m", "-c", "pro", ".pro", "#"]
        for suffix in suffixes:
            add(f"{requested}{suffix}")
            if base6:
                add(f"{base6}{suffix}")

        patterns = [requested, f"{requested}*", f"*{requested}*", f"{base6}*", f"*{base6}*"]
        for pattern in patterns:
            try:
                for item in self.mt5.symbols_get(pattern) or []:
                    name = self._symbol_name(item)
                    if not name:
                        continue
                    compact_name = self._compact(name)
                    if self._compact(requested) in compact_name or (base6 and compact_name.startswith(base6)):
                        add(name)
            except Exception:
                continue
        return candidates[:40]

    def _rate_count(self, rates: Any) -> int:
        if rates is None:
            return 0
        try:
            return int(len(rates))
        except Exception:
            return 0

    def _copy_rates_range_safe(self, symbol: str, tf_constant: Any, utc_from: datetime, utc_to: datetime) -> tuple[Any, str | None]:
        try:
            return self.mt5.copy_rates_range(symbol, tf_constant, utc_from, utc_to), None
        except Exception as exc:
            return None, str(exc)

    def _copy_rates_from_safe(self, symbol: str, tf_constant: Any, utc_to: datetime, count: int) -> tuple[Any, str | None]:
        try:
            return self.mt5.copy_rates_from(symbol, tf_constant, utc_to, count), None
        except Exception as exc:
            return None, str(exc)

    def _copy_rates_from_pos_safe(self, symbol: str, tf_constant: Any, start_pos: int, count: int) -> tuple[Any, str | None]:
        try:
            return self.mt5.copy_rates_from_pos(symbol, tf_constant, int(max(start_pos, 0)), int(max(count, 1))), None
        except Exception as exc:
            return None, str(exc)

    def _dedupe_sort_rates(self, rates: list[Any]) -> list[Any]:
        by_ts: dict[int, Any] = {}
        for rate in rates:
            raw = _safe_obj(rate)
            if not isinstance(raw, dict):
                continue
            try:
                ts = int(raw.get("time"))
            except Exception:
                continue
            by_ts[ts] = rate
        return [by_ts[key] for key in sorted(by_ts)]

    def _copy_rates_chunked_safe(
        self,
        symbol: str,
        tf_constant: Any,
        utc_from: datetime,
        utc_to: datetime,
        timeframe_minutes: int,
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        """Fetch MT5 history in smaller windows.

        Some terminals/brokers return 0/1 candle for a large copy_rates_range call
        even though smaller ranges are available from the server cache. Chunking also
        avoids freezing slow local terminals.
        """
        if timeframe_minutes <= 1:
            chunk_days = 3
        elif timeframe_minutes <= 5:
            chunk_days = 7
        elif timeframe_minutes <= 15:
            chunk_days = 21
        elif timeframe_minutes <= 60:
            chunk_days = 60
        else:
            chunk_days = 180

        rows: list[Any] = []
        attempts: list[dict[str, Any]] = []
        cursor = utc_from
        max_chunks = 250
        chunks = 0
        while cursor < utc_to and chunks < max_chunks:
            chunk_end = min(cursor + timedelta(days=chunk_days), utc_to)
            rates, exc = self._copy_rates_range_safe(symbol, tf_constant, cursor, chunk_end)
            count = self._rate_count(rates)
            attempts.append({
                "method": "copy_rates_range_chunk",
                "from": cursor.isoformat(),
                "to": chunk_end.isoformat(),
                "candles": count,
                "exception": exc,
                "last_error": self._last_error(),
            })
            if count > 0:
                try:
                    rows.extend(list(rates))
                except Exception:
                    pass
            cursor = chunk_end + timedelta(seconds=1)
            chunks += 1

        return self._dedupe_sort_rates(rows), attempts

    def _filter_rates_between(self, rates: Any, utc_from: datetime, utc_to: datetime) -> list[Any]:
        if rates is None:
            return []
        filtered: list[Any] = []
        start_ts = int(utc_from.timestamp())
        end_ts = int(utc_to.timestamp())
        for rate in rates:
            raw = _safe_obj(rate)
            if not isinstance(raw, dict):
                continue
            ts = raw.get("time")
            try:
                ts_int = int(ts)
            except Exception:
                continue
            if start_ts <= ts_int <= end_ts:
                filtered.append(rate)
        return filtered

    def _convert_rate(self, rate: Any, resolved_symbol: str, requested_symbol: str, timeframe: str) -> dict[str, Any]:
        raw = _safe_obj(rate)
        if not isinstance(raw, dict):
            raw = {}
        ts = raw.get("time")
        if ts is None:
            raise ValueError("MT5 rate row missing time")
        timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        volume = raw.get("real_volume") or raw.get("tick_volume") or raw.get("volume") or 0
        return {
            "timestamp": timestamp,
            "open": raw.get("open"),
            "high": raw.get("high"),
            "low": raw.get("low"),
            "close": raw.get("close"),
            "volume": volume,
            "symbol": resolved_symbol,
            "requested_symbol": requested_symbol,
            "timeframe": timeframe,
        }

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self._initialize()

        tf_constant = self._timeframe_constant(timeframe)
        if tf_constant is None:
            raise ProviderFetchError(
                f"Unsupported timeframe for MT5: {timeframe}. Supported: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
            )

        utc_from = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
        utc_to = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)
        utc_from = utc_from.astimezone(timezone.utc)
        utc_to = utc_to.astimezone(timezone.utc)
        if utc_to <= utc_from:
            raise ProviderFetchError("end_date must be greater than start_date")

        minutes = self._TIMEFRAME_MINUTES.get(str(timeframe or "").strip().lower(), 60)
        expected_rough = max(1, int((utc_to - utc_from).total_seconds() // max(minutes * 60, 60)))
        # Keep count bounded so a very large range does not overload a slow terminal.
        fallback_count = min(max(expected_rough + 500, 500), 120_000)

        best_symbol: str | None = None
        best_rates: list[Any] | Any = None
        attempts: list[dict[str, Any]] = []
        exact_requested = self._looks_like_exact_broker_symbol(str(symbol or ""))

        for candidate in self._candidate_symbols(symbol, exact_first=True):
            try:
                selected = bool(self.mt5.symbol_select(candidate, True))
                info = _safe_obj(self.mt5.symbol_info(candidate))
                if not selected:
                    attempts.append({"symbol": candidate, "selected": False, "symbol_info_exists": bool(info), "last_error": self._last_error()})
                    continue

                range_rates, range_exc = self._copy_rates_range_safe(candidate, tf_constant, utc_from, utc_to)
                range_count = self._rate_count(range_rates)
                rates_for_candidate: Any = range_rates
                method = "copy_rates_range"

                # Some MT5 terminals return 0/1 row from range until history is cached.
                # Fallback to copy_rates_from(end, count), then filter by requested range.
                from_count = 0
                from_exc = None
                if range_count <= 1 and fallback_count > range_count:
                    from_rates, from_exc = self._copy_rates_from_safe(candidate, tf_constant, utc_to, fallback_count)
                    filtered = self._filter_rates_between(from_rates, utc_from, utc_to)
                    from_count = len(filtered)
                    if from_count > range_count:
                        rates_for_candidate = filtered
                        method = f"copy_rates_from_filtered({fallback_count})"

                chunk_count = 0
                chunk_attempts: list[dict[str, Any]] = []
                if self._rate_count(rates_for_candidate) <= 1:
                    chunk_rates, chunk_attempts = self._copy_rates_chunked_safe(candidate, tf_constant, utc_from, utc_to, minutes)
                    chunk_count = len(chunk_rates)
                    if chunk_count > self._rate_count(rates_for_candidate):
                        rates_for_candidate = chunk_rates
                        method = "copy_rates_range_chunked"

                pos_count = 0
                pos_exception = None
                pos_start = None
                pos_request_count = None
                if self._rate_count(rates_for_candidate) <= 1:
                    # Last fallback: ask MT5 by bar position instead of by date.
                    # This can work after the user increases Terminal max bars/history.
                    tf_seconds = max(minutes * 60, 60)
                    now_utc = datetime.now(timezone.utc)
                    bars_back_to_end = max(0, int((now_utc - utc_to).total_seconds() // tf_seconds))
                    pos_start = max(0, bars_back_to_end - 500)
                    pos_request_count = min(max(expected_rough + 1500, 2500), 150_000)
                    pos_rates, pos_exception = self._copy_rates_from_pos_safe(candidate, tf_constant, pos_start, pos_request_count)
                    pos_filtered = self._filter_rates_between(pos_rates, utc_from, utc_to)
                    pos_count = len(pos_filtered)
                    if pos_count > self._rate_count(rates_for_candidate):
                        rates_for_candidate = pos_filtered
                        method = f"copy_rates_from_pos_filtered(start={pos_start}, count={pos_request_count})"

                count = self._rate_count(rates_for_candidate)
                attempts.append(
                    {
                        "symbol": candidate,
                        "selected": True,
                        "method": method,
                        "candles": count,
                        "range_candles": range_count,
                        "from_filtered_candles": from_count,
                        "chunked_candles": chunk_count,
                        "pos_filtered_candles": pos_count,
                        "pos_start": pos_start,
                        "pos_request_count": pos_request_count,
                        "range_exception": range_exc,
                        "from_exception": from_exc,
                        "pos_exception": pos_exception,
                        "chunk_attempts_tail": chunk_attempts[-5:],
                        "last_error": self._last_error(),
                    }
                )
                if count > self._rate_count(best_rates):
                    best_symbol = candidate
                    best_rates = rates_for_candidate
            except Exception as exc:
                attempts.append({"symbol": candidate, "exception": str(exc), "last_error": self._last_error()})

        resolved_symbol = best_symbol or str(symbol).strip()
        rates = best_rates
        rate_count = self._rate_count(rates)

        if rate_count <= 0:
            help_text = (
                "No candles returned from MT5. Use the exact broker symbol shown in MT5 Market Watch "
                "(for your Exness account screenshots it is XAUUSDm/XAGUSDm/BTCUSDm, not XAUUSDc). "
                "Also check MT5 Tools → Options → Charts → Max bars in chart; for multi-year 5m imports set a very high value, "
                "restart/open the chart, right-click Market Watch → Show All, open the exact symbol chart, set the same timeframe, "
                "then press Home/scroll left to download history before retrying."
            )
            raise ProviderFetchError(
                f"No candles returned from MT5 for {symbol} {timeframe} between {utc_from.isoformat()} and {utc_to.isoformat()}. "
                f"{help_text} Terminal: {self._terminal_info()}. Attempts: {attempts[-10:]}"
            )

        if expected_rough > 10 and rate_count <= 1:
            if exact_requested:
                symbol_hint = (
                    f"Exact symbol {symbol} was used, but MT5 returned only {rate_count} candle. "
                    "This is usually not an AlgoAgentX database issue; the MT5 terminal has not downloaded historical candles "
                    "for this symbol/timeframe/range, MT5 Max bars in chart is too low for this old date range, "
                    "or the exact suffix in Market Master is different from your MT5 account."
                )
            else:
                symbol_hint = (
                    f"MT5 resolved {symbol} to {resolved_symbol}, but only {rate_count} candle was available. "
                    "Set the exact broker_symbol in Market Master instead of using the clean symbol."
                )
            raise ProviderFetchError(
                f"MT5 returned only {rate_count} candle for {symbol} ({resolved_symbol}) {timeframe}, although this date range should contain many candles. "
                f"{symbol_hint} In MT5 set Tools → Options → Charts → Max bars in chart to a very high value, restart MT5 if needed, then Market Watch → Show All → open the exact resolved symbol {resolved_symbol} chart → select {timeframe} → scroll left/press Home to load history, then retry. "
                f"Attempts: {attempts[-10:]}"
            )

        candles: list[dict[str, Any]] = []
        for rate in rates:
            try:
                candles.append(self._convert_rate(rate, resolved_symbol, str(symbol).strip(), timeframe))
            except Exception:
                continue

        if not candles:
            raise ProviderFetchError("MT5 returned rates, but no valid candle rows could be converted")
        return candles
