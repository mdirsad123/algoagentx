from __future__ import annotations

from datetime import datetime, timezone
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

    This provider only reads historical rates from the local MT5 terminal. It does
    not place orders and does not touch live-trading execution logic. Credentials
    remain managed by the existing broker connection flow; this provider relies on
    either an already logged-in terminal or the existing terminal session.
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

    def _candidate_symbols(self, symbol: str) -> list[str]:
        requested = str(symbol or "").strip()
        if not requested or self.mt5 is None:
            return [requested]

        candidates: list[str] = []

        def add(value: str | None) -> None:
            clean = str(value or "").strip()
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

    def _select_symbol(self, symbol: str) -> str:
        requested = str(symbol or "").strip()
        if not requested:
            raise ProviderFetchError("Symbol is required")
        attempts: list[dict[str, Any]] = []
        for candidate in self._candidate_symbols(requested):
            try:
                selected = bool(self.mt5.symbol_select(candidate, True))
                info = _safe_obj(self.mt5.symbol_info(candidate))
                attempts.append({"symbol": candidate, "selected": selected, "symbol_info": info, "last_error": self._last_error()})
                if selected:
                    return candidate
            except Exception as exc:
                attempts.append({"symbol": candidate, "exception": str(exc), "last_error": self._last_error()})
        raise ProviderFetchError(
            f"Symbol not found or not selectable in MT5: {requested}. "
            "Open Market Watch in MT5, right-click Show All, or use the exact broker symbol suffix. "
            f"Attempts: {attempts[-3:]}"
        )

    def _rate_count(self, rates: Any) -> int:
        if rates is None:
            return 0
        try:
            return int(len(rates))
        except Exception:
            return 0

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

        resolved_symbol = self._select_symbol(symbol)

        utc_from = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
        utc_to = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)
        utc_from = utc_from.astimezone(timezone.utc)
        utc_to = utc_to.astimezone(timezone.utc)
        if utc_to <= utc_from:
            raise ProviderFetchError("end_date must be greater than start_date")

        try:
            rates = self.mt5.copy_rates_range(resolved_symbol, tf_constant, utc_from, utc_to)
        except Exception as exc:
            raise ProviderFetchError(f"MT5 historical candle fetch failed: {exc}. Last error: {self._last_error()}") from exc

        if self._rate_count(rates) <= 0:
            raise ProviderFetchError(
                f"No candles returned from MT5 for {symbol} ({resolved_symbol}) {timeframe} "
                f"between {utc_from.isoformat()} and {utc_to.isoformat()}. Last error: {self._last_error()}. "
                "Open the symbol chart in MT5 once and verify the broker has history for this range."
            )

        candles: list[dict[str, Any]] = []
        for rate in rates:
            try:
                candles.append(self._convert_rate(rate, resolved_symbol, str(symbol).strip(), timeframe))
            except Exception:
                # Let MD-2 validation handle row-level issues where possible; skip
                # completely malformed MT5 rows here so one bad rate does not crash.
                continue

        if not candles:
            raise ProviderFetchError("MT5 returned rates, but no valid candle rows could be converted")
        return candles
