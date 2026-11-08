"""No TradeLocker candle is not necessarily a broker failure or market closure.

Run in project backend with pytest. Uses mocked I/O: no DB/HTTP requests.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID
import pytest
from fastapi import HTTPException
from app.services.live import broker_candle_service as svc

DEPLOYMENT_ID = UUID('0349cc95-6677-4a7e-b7d1-e4c8cbd46b88')

@pytest.mark.asyncio
async def test_live_no_candle_is_normal_response(monkeypatch):
    deployment = SimpleNamespace(id=DEPLOYMENT_ID, instrument='XAUUSD.X', broker_symbol='XAUUSD.X', timeframe='M5')
    broker = SimpleNamespace(id=UUID(int=2))
    monkeypatch.setattr(svc, '_get_deployment_and_broker', AsyncMock(return_value=(deployment, broker, 'TRADELOCKER')))
    monkeypatch.setattr(svc, '_write_log', AsyncMock())
    monkeypatch.setattr(svc, 'get_broker_adapter', lambda *args: SimpleNamespace(get_rates=AsyncMock(return_value=[])))
    db = SimpleNamespace(commit=AsyncMock())
    result = await svc.refresh_deployment_candles(db, DEPLOYMENT_ID, count=12, allow_empty=True)
    assert result['no_new_candle'] is True
    assert result['latest_candle_time'] is None
    assert result['upserted_count'] == 0
    db.commit.assert_awaited_once()
    assert svc._write_log.await_args.args[2] == 'CANDLE_REFRESH_NO_NEW_CANDLE'

@pytest.mark.asyncio
async def test_default_empty_still_raises_for_other_callers(monkeypatch):
    deployment = SimpleNamespace(id=DEPLOYMENT_ID, instrument='XAUUSD.X', broker_symbol='XAUUSD.X', timeframe='M5')
    broker = SimpleNamespace(id=UUID(int=2))
    monkeypatch.setattr(svc, '_get_deployment_and_broker', AsyncMock(return_value=(deployment, broker, 'TRADELOCKER')))
    monkeypatch.setattr(svc, '_write_log', AsyncMock())
    monkeypatch.setattr(svc, 'get_broker_adapter', lambda *args: SimpleNamespace(get_rates=AsyncMock(return_value=[])))
    db = SimpleNamespace(commit=AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await svc.refresh_deployment_candles(db, DEPLOYMENT_ID, count=12)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_broker_error_not_swallowed(monkeypatch):
    deployment = SimpleNamespace(id=DEPLOYMENT_ID, instrument='XAUUSD.X', broker_symbol='XAUUSD.X', timeframe='M5')
    broker = SimpleNamespace(id=UUID(int=2))
    monkeypatch.setattr(svc, '_get_deployment_and_broker', AsyncMock(return_value=(deployment, broker, 'TRADELOCKER')))
    monkeypatch.setattr(svc, '_write_log', AsyncMock())
    monkeypatch.setattr(svc, 'get_broker_adapter', lambda *args: SimpleNamespace(get_rates=AsyncMock(side_effect=RuntimeError('Broker 429'))))
    db = SimpleNamespace(commit=AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await svc.refresh_deployment_candles(db, DEPLOYMENT_ID, count=12, allow_empty=True)
    assert exc.value.status_code == 400
