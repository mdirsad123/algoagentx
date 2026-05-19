from __future__ import annotations

from typing import Callable

from .base import MarketDataProvider
from .errors import ProviderNotFoundError, ProviderNotImplementedError
from .mock_provider import MockMarketDataProvider
from .mt5_provider import MT5MarketDataProvider
from .upstox_provider import UpstoxMarketDataProvider
from .binance_provider import BinanceMarketDataProvider


class _ReservedProvider(MarketDataProvider):
    def __init__(self, name: str) -> None:
        self.name = name.upper()

    async def fetch_candles(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise ProviderNotImplementedError(f"Provider {self.name} is reserved for a future phase")


ProviderFactory = Callable[[], MarketDataProvider]

_PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "MOCK": MockMarketDataProvider,
    "MT5": MT5MarketDataProvider,
    "UPSTOX": UpstoxMarketDataProvider,
    "BINANCE": BinanceMarketDataProvider,
    "CSV": lambda: _ReservedProvider("CSV"),
}


def normalize_provider_name(provider: str) -> str:
    return (provider or "").strip().upper()


def list_supported_providers() -> list[str]:
    return sorted(_PROVIDER_FACTORIES.keys())


def get_market_data_provider(provider: str) -> MarketDataProvider:
    name = normalize_provider_name(provider)
    factory = _PROVIDER_FACTORIES.get(name)
    if factory is None:
        raise ProviderNotFoundError(f"Unknown market data provider '{provider}'. Supported: {', '.join(list_supported_providers())}")
    return factory()
