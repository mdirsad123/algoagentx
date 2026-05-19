from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .base import MarketDataProvider
from .errors import ProviderFetchError


class BinanceMarketDataProvider(MarketDataProvider):
    """Historical Binance spot klines provider.

    Binance spot symbols use USDT for the common BTC quote pair. AlgoAgentX may
    keep a user-facing instrument as BTCUSD, so this provider automatically tries
    BTCUSDT when the requested symbol ends with USD and the exact symbol returns
    no klines.
    """

    name = "BINANCE"
    base_url = "https://api.binance.com/api/v3/klines"

    _INTERVAL_MAP = {
        "1m": "1m",
        "m1": "1m",
        "3m": "3m",
        "5m": "5m",
        "m5": "5m",
        "15m": "15m",
        "m15": "15m",
        "30m": "30m",
        "m30": "30m",
        "1h": "1h",
        "h1": "1h",
        "60m": "1h",
        "4h": "4h",
        "h4": "4h",
        "1d": "1d",
        "d1": "1d",
    }

    _INTERVAL_MS = {
        "1m": 60_000,
        "3m": 180_000,
        "5m": 300_000,
        "15m": 900_000,
        "30m": 1_800_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }

    def _interval(self, timeframe: str) -> str:
        interval = self._INTERVAL_MAP.get(str(timeframe or "").strip().lower())
        if not interval:
            raise ProviderFetchError(
                f"Unsupported timeframe for Binance: {timeframe}. Supported: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
            )
        return interval

    def _candidate_symbols(self, symbol: str) -> list[str]:
        requested = str(symbol or "").strip().upper().replace("-", "").replace("/", "")
        candidates: list[str] = []

        def add(value: str | None) -> None:
            clean = str(value or "").strip().upper().replace("-", "").replace("/", "")
            if clean and clean not in candidates:
                candidates.append(clean)

        add(requested)
        if requested.endswith("USD") and not requested.endswith("USDT"):
            add(f"{requested[:-3]}USDT")
        if requested.endswith("USDT"):
            add(f"{requested[:-4]}USD")
        return candidates

    @staticmethod
    def _as_utc_ms(value: datetime) -> int:
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp() * 1000)

    async def _request_klines(
        self,
        session: aiohttp.ClientSession,
        *,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[Any]:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": max(1, min(int(limit or 1000), 1000)),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            text = await response.text()
            if response.status >= 400:
                raise ProviderFetchError(f"Binance returned HTTP {response.status} for {symbol}: {text[:300]}")
            try:
                data = await response.json()
            except Exception as exc:
                raise ProviderFetchError(f"Unable to parse Binance response for {symbol}: {text[:300]}") from exc
            if not isinstance(data, list):
                raise ProviderFetchError(f"Unexpected Binance response for {symbol}: {str(data)[:300]}")
            return data

    async def _fetch_for_symbol(
        self,
        session: aiohttp.ClientSession,
        *,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> list[dict[str, Any]]:
        interval_ms = self._INTERVAL_MS[interval]
        cursor = start_ms
        candles: list[dict[str, Any]] = []
        empty_pages = 0

        while cursor < end_ms:
            page = await self._request_klines(
                session,
                symbol=symbol,
                interval=interval,
                start_ms=cursor,
                end_ms=end_ms,
                limit=1000,
            )
            if not page:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                cursor += interval_ms * 1000
                continue

            empty_pages = 0
            last_open_ms = cursor
            for row in page:
                if not isinstance(row, list) or len(row) < 6:
                    continue
                open_ms = int(row[0])
                last_open_ms = max(last_open_ms, open_ms)
                if open_ms < start_ms or open_ms >= end_ms:
                    continue
                candles.append(
                    {
                        "timestamp": datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc),
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "volume": row[5],
                        "symbol": symbol,
                        "timeframe": interval,
                    }
                )

            next_cursor = last_open_ms + interval_ms
            if next_cursor <= cursor:
                next_cursor = cursor + interval_ms
            cursor = next_cursor

            # A small cooperative yield keeps the API responsive during long imports.
            await asyncio.sleep(0)

        # Binance may return duplicates at page boundaries for some intervals.
        unique: dict[int, dict[str, Any]] = {}
        for candle in candles:
            unique[int(candle["timestamp"].timestamp())] = candle
        return [unique[key] for key in sorted(unique)]

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        interval = self._interval(timeframe)
        start_ms = self._as_utc_ms(start_date)
        end_ms = self._as_utc_ms(end_date)
        if end_ms <= start_ms:
            raise ProviderFetchError("end_date must be greater than start_date")

        attempts: list[str] = []
        async with aiohttp.ClientSession(headers={"User-Agent": "AlgoAgentX/market-data"}) as session:
            for candidate in self._candidate_symbols(symbol):
                try:
                    candles = await self._fetch_for_symbol(
                        session,
                        symbol=candidate,
                        interval=interval,
                        start_ms=start_ms,
                        end_ms=end_ms,
                    )
                except ProviderFetchError as exc:
                    attempts.append(str(exc))
                    continue
                if candles:
                    return candles
                attempts.append(f"No klines returned for {candidate}")

        raise ProviderFetchError(
            f"No Binance candles returned for {symbol} {timeframe} between "
            f"{datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat()} and "
            f"{datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat()}. "
            f"Attempts: {attempts[-3:]}"
        )
