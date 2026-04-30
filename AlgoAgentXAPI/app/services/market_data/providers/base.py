from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class MarketDataProvider(ABC):
    """Provider adapter contract for historical candle fetch.

    Real provider implementations must return mapping-like candle rows that can
    be passed directly into the MD-2 normalizer/upsert service.
    """

    name: str = "BASE"

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
