from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.models import BrokerAccount, Instrument
from ...brokers.upstox import UPSTOX_HISTORICAL_CANDLE_V3_URL, UpstoxAdapter
from .base import MarketDataProvider
from .errors import ProviderFetchError


class UpstoxMarketDataProvider(MarketDataProvider):
    """Historical candle provider for Upstox.

    This provider only reads historical candles and imports them into the normal
    market_data ingestion path. It does not place orders and does not touch live
    trading execution logic.
    """

    name = "UPSTOX"

    _TIMEFRAME_MAP: dict[str, tuple[str, int]] = {
        "1m": ("minutes", 1),
        "m1": ("minutes", 1),
        "1min": ("minutes", 1),
        "1minute": ("minutes", 1),
        "5m": ("minutes", 5),
        "m5": ("minutes", 5),
        "5min": ("minutes", 5),
        "5minute": ("minutes", 5),
        "15m": ("minutes", 15),
        "m15": ("minutes", 15),
        "15min": ("minutes", 15),
        "15minute": ("minutes", 15),
        "30m": ("minutes", 30),
        "m30": ("minutes", 30),
        "30min": ("minutes", 30),
        "30minute": ("minutes", 30),
        "1h": ("hours", 1),
        "h1": ("hours", 1),
        "60m": ("hours", 1),
        "1hour": ("hours", 1),
        "1d": ("days", 1),
        "d1": ("days", 1),
        "day": ("days", 1),
        "daily": ("days", 1),
    }

    def _timeframe(self, timeframe: str) -> tuple[str, int]:
        key = str(timeframe or "").strip().lower().replace(" ", "")
        value = self._TIMEFRAME_MAP.get(key)
        if not value:
            raise ProviderFetchError(
                f"Unsupported timeframe for Upstox: {timeframe}. Supported: 1m, 5m, 15m, 30m, 1h, 1d"
            )
        return value

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _clean(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    async def _load_broker_account(self, db: AsyncSession | None, broker_account_id: Any = None) -> BrokerAccount:
        if db is None:
            raise ProviderFetchError(
                "Database session is required to load the connected Upstox broker account. "
                "Please call UPSTOX provider through the admin market-data endpoint."
            )

        stmt = select(BrokerAccount).where(
            ((BrokerAccount.broker_code == "UPSTOX") | (BrokerAccount.broker_name == "UPSTOX"))
        )
        if broker_account_id:
            
            try:
                parsed_account_id = UUID(str(broker_account_id))
            except Exception as exc:
                raise ProviderFetchError("Invalid Upstox broker_account_id") from exc
            stmt = stmt.where(BrokerAccount.id == parsed_account_id)
        else:
            stmt = stmt.where(BrokerAccount.status.in_(["CONNECTED", "ACTIVE"]))
        stmt = stmt.order_by(BrokerAccount.last_connected_at.desc().nullslast(), BrokerAccount.updated_at.desc()).limit(1)
        account = (await db.execute(stmt)).scalar_one_or_none()
        if not account:
            raise ProviderFetchError(
                "Upstox access token is missing. Connect/test an Upstox broker account first, then retry."
            )
        return account

    async def _instrument_key_from_db(self, db: AsyncSession | None, instrument_id: int | None, symbol: str | None) -> str | None:
        if db is None or not instrument_id:
            return None
        try:
            row = (await db.execute(select(Instrument).where(Instrument.id == instrument_id))).scalar_one_or_none()
        except Exception:
            return None
        if not row:
            return None

        # Current instruments table has symbol/exchange only. Future phases may add
        # broker_symbol or upstox_instrument_key; use them if present without making
        # this phase depend on a schema migration.
        for attr in ("upstox_instrument_key", "instrument_key", "broker_symbol"):
            value = self._clean(getattr(row, attr, None))
            if value:
                return value

        row_symbol = self._clean(getattr(row, "symbol", None)) or symbol
        row_exchange = (self._clean(getattr(row, "exchange", None)) or "").upper()
        if row_symbol and "|" in row_symbol:
            return row_symbol
        if row_symbol and row_exchange in {"NSE_INDEX", "BSE_INDEX"}:
            return f"{row_exchange}|{row_symbol}"
        return None

    def _resolve_instrument_key(self, symbol: str, kwargs: dict[str, Any], fallback_from_db: str | None) -> str:
        explicit = self._clean(kwargs.get("instrument_key")) or self._clean(kwargs.get("trading_symbol"))
        candidate = explicit or fallback_from_db or self._clean(symbol)
        if not candidate:
            raise ProviderFetchError("Upstox instrument_key is required. Example: NSE_INDEX|Nifty 50")
        if "|" not in candidate:
            raise ProviderFetchError(
                "Upstox requires instrument_key format, not only trading symbol. "
                "Example: NSE_INDEX|Nifty 50 or NSE_EQ|INE002A01018."
            )
        return candidate

    @staticmethod
    def _normalize_candles(payload: dict[str, Any], instrument_key: str, symbol: str, timeframe: str) -> list[dict[str, Any]]:
        candles = ((payload or {}).get("data") or {}).get("candles") or []
        rows: list[dict[str, Any]] = []
        for candle in candles:
            if not isinstance(candle, (list, tuple)) or len(candle) < 5:
                continue
            rows.append(
                {
                    "timestamp": candle[0],
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5] if len(candle) > 5 else 0,
                    "open_interest": candle[6] if len(candle) > 6 else None,
                    "symbol": symbol,
                    "instrument_key": instrument_key,
                    "timeframe": timeframe,
                }
            )
        rows.sort(key=lambda item: str(item.get("timestamp") or ""))
        return rows

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        unit, interval = self._timeframe(timeframe)
        start_dt = self._as_utc(start_date)
        end_dt = self._as_utc(end_date)
        if end_dt <= start_dt:
            raise ProviderFetchError("end_date must be greater than start_date")

        db: AsyncSession | None = kwargs.get("db")
        broker_account = await self._load_broker_account(db, kwargs.get("broker_account_id"))
        adapter = UpstoxAdapter(broker_account)

        db_key = await self._instrument_key_from_db(db, kwargs.get("instrument_id"), symbol)
        instrument_key = self._resolve_instrument_key(symbol, kwargs, db_key)
        encoded_key = quote(instrument_key, safe="")
        from_date = start_dt.date().isoformat()
        to_date = end_dt.date().isoformat()
        url = f"{UPSTOX_HISTORICAL_CANDLE_V3_URL}/{encoded_key}/{unit}/{interval}/{to_date}/{from_date}"

        try:
            payload = await adapter._authorized_get(url)
        except ValueError as exc:
            message = str(exc)
            if "rate limit" in message.lower() or "429" in message:
                raise ProviderFetchError("Upstox API rate limit reached. Please wait and try again.") from exc
            if "expired" in message.lower() or "unauthorized" in message.lower() or "401" in message:
                raise ProviderFetchError("Upstox access token missing/expired. Please reconnect Upstox.") from exc
            raise ProviderFetchError(message) from exc
        except Exception as exc:
            raise ProviderFetchError(f"Upstox historical candle fetch failed: {exc}") from exc

        rows = self._normalize_candles(payload, instrument_key, symbol, timeframe)
        if not rows:
            raise ProviderFetchError(
                f"No candles returned from Upstox for {instrument_key} {timeframe} between {from_date} and {to_date}. "
                "Check instrument_key, timeframe, market holidays, and Upstox API permissions."
            )
        return rows
