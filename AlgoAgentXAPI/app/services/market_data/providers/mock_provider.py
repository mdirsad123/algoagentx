from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .base import MarketDataProvider
from .errors import ProviderFetchError

_TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "45m": 45,
    "1h": 60,
    "60m": 60,
    "2h": 120,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
    "day": 1440,
    "daily": 1440,
}


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic dev/test-only provider for MD smoke testing.

    This provider never talks to a broker and must not be used as real market
    data. It gives predictable candles so admin fetch-preview/fetch-import can
    be verified safely before MT5/Upstox adapters are enabled.
    """

    name = "MOCK"

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        normalized_tf = (timeframe or "").strip().lower()
        minutes = _TIMEFRAME_MINUTES.get(normalized_tf)
        if not minutes:
            raise ProviderFetchError(f"Unsupported MOCK timeframe '{timeframe}'")

        start = _to_utc(start_date)
        end = _to_utc(end_date)
        if end <= start:
            raise ProviderFetchError("end_date must be greater than start_date")

        max_rows = int(kwargs.get("max_rows") or 2000)
        max_rows = max(1, min(max_rows, 5000))
        step = timedelta(minutes=minutes)
        rows: list[dict[str, Any]] = []
        ts = start
        index = 0
        base = Decimal("100.00")

        while ts < end and len(rows) < max_rows:
            wave = Decimal(index % 20) / Decimal("10")
            open_price = base + Decimal(index) * Decimal("0.05") + wave
            close_price = open_price + (Decimal("0.20") if index % 2 == 0 else Decimal("-0.10"))
            high_price = max(open_price, close_price) + Decimal("0.50")
            low_price = min(open_price, close_price) - Decimal("0.50")
            rows.append(
                {
                    "timestamp": ts,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": Decimal(1000 + index),
                    "provider": self.name,
                    "symbol": symbol,
                    "is_mock": True,
                }
            )
            ts += step
            index += 1

        return rows
