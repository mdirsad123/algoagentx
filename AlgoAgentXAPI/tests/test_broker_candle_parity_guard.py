"""Offline broker candle parity guards. No real broker or database access."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.brokers.ctrader import CTraderAdapter
from app.services.live import mt5_candle_service


def _ctrader_bar(close_delta):
    bar = {
        "low": 4_100_00000,
        "deltaOpen": 60000,
        "deltaHigh": 120000,
        "utcTimestampInMinutes": 29855000,
        "volume": 100,
    }
    if close_delta is not None:
        bar["deltaClose"] = close_delta
    return bar


@pytest.mark.asyncio
async def test_ctrader_history_rejects_missing_delta_close_but_accepts_real_zero(monkeypatch):
    adapter = CTraderAdapter.__new__(CTraderAdapter)
    adapter._selected_account = lambda: {"ctrader_account_id": "12345", "account_type": "DEMO"}
    adapter._access_token = lambda: "test-token"
    adapter._resolve_symbol_meta = AsyncMock(return_value={"symbol_id": 42})
    client = SimpleNamespace(
        request=AsyncMock(side_effect=[{}, {"trendbar": [_ctrader_bar(None), _ctrader_bar(0), _ctrader_bar(90000)]}]),
        __aexit__=AsyncMock(),
    )
    adapter._openapi_authorized_client = AsyncMock(return_value=client)
    rows = await adapter.get_rates("XAUUSD", "M5", 5)
    assert len(rows) == 2  # Missing deltaClose row was skipped; zero is a valid delta.
    assert rows[0]["close"] == rows[0]["low"]
    assert rows[1]["close"] > rows[1]["low"]


@pytest.mark.asyncio
async def test_mt5_snapshot_never_persists_current_forming_bar(monkeypatch):
    from app.services.live.mt5_candle_service import refresh_deployment_candles
    deployment = SimpleNamespace(id=uuid4(), instrument="XAUUSD", timeframe="M5", user_id=uuid4())
    broker = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(mt5_candle_service, "_get_deployment_and_broker", AsyncMock(return_value=(deployment, broker)))
    monkeypatch.setattr(mt5_candle_service, "_write_log", AsyncMock())
    monkeypatch.setattr(mt5_candle_service, "get_latest_closed_candles", AsyncMock(return_value=[]))

    now = datetime.now(timezone.utc)
    forming = now.replace(second=0, microsecond=0) - timedelta(minutes=now.minute % 5)
    closed = forming - timedelta(minutes=10)

    def rate(ts, close):
        return {"candle_time": ts.isoformat(), "symbol": "XAUUSD", "open": close, "high": close + 1,
                "low": close - 1, "close": close, "volume": 100}

    broker_adapter = SimpleNamespace(get_rates=AsyncMock(return_value=[rate(forming, 4200), rate(closed, 4199)]))
    monkeypatch.setattr(mt5_candle_service, "get_broker_adapter", lambda *_args: broker_adapter)
    count_response = MagicMock()
    count_response.scalar.return_value = 1
    db = SimpleNamespace(execute=AsyncMock(side_effect=[MagicMock(), count_response]), commit=AsyncMock())
    result = await refresh_deployment_candles(db, deployment.id, count=3)
    assert result["upserted_count"] == 1
    assert result["skipped_forming"] == 1
    # One INSERT for the completed candle and one SELECT count.
    assert db.execute.await_count == 2
