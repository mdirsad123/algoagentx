from __future__ import annotations


class MarketDataProviderError(Exception):
    """Base exception for market data provider adapter failures."""


class ProviderNotFoundError(MarketDataProviderError):
    """Raised when a requested provider is not registered."""


class ProviderNotImplementedError(MarketDataProviderError):
    """Raised for provider names reserved for future phases."""


class ProviderFetchError(MarketDataProviderError):
    """Raised when a provider cannot fetch candles safely."""
