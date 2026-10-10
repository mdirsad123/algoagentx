"""Offline contract checks for TradeLocker positions and account-specific copies.

No broker credentials, network calls, live orders, or database are needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from app.services.brokers.tradelocker import TradeLockerAdapter
from app.services.live.broker_sync_service import _tradelocker_position_values


@pytest.fixture
def instrument():
    return {"name": "XAUUSD.X", "tradableInstrumentId": 6310,
            "routes": [{"type": "TRADE", "id": 974771}, {"type": "INFO", "id": 974770}]}


@pytest.fixture
def adapter(instrument):
    instance = TradeLockerAdapter.__new__(TradeLockerAdapter)
    instance.account_id = "2540480"
    instance.acc_num = 28
    instance._instrument_cache = [instrument]
    instance._config_cache = None
    return instance


@pytest.mark.asyncio
async def test_alias_chooses_unique_broker_symbol(adapter):
    assert (await adapter._instrument("XAUUSD"))["name"] == "XAUUSD.X"
    assert (await adapter._instrument("XAUUSD.X"))["name"] == "XAUUSD.X"


@pytest.mark.asyncio
async def test_alias_ambiguity_is_blocking(adapter):
    adapter._instrument_cache.append({"name": "XAUUSDm", "tradableInstrumentId": 6311})
    with pytest.raises(ValueError, match="multiple suffixed matches"):
        await adapter._instrument("XAUUSD")


@pytest.mark.asyncio
async def test_positions_have_account_broker_ids_and_symbols(adapter):
    adapter._table = AsyncMock(return_value=[
        {"id": "888", "tradableInstrumentId": "6310", "side": "buy", "qty": "0.28",
         "avgPrice": "4196.35", "openDate": "1791580500000", "unrealizedPl": "-25.5"},
        {"id": "889", "tradableInstrumentId": "6310", "side": "sell", "qty": "0.01",
         "avgPrice": "4196.35", "openDate": "1791580500000", "unrealizedPl": "2.5"},
    ])
    positions = await adapter.get_positions()
    assert len(positions) == 2
    assert {x['broker_position_id'] for x in positions} == {"888", "889"}
    assert {x['symbol'] for x in positions} == {"XAUUSD.X"}
    values = [_tradelocker_position_values(row, SimpleNamespace(instrument='XAUUSD')) for row in positions]
    assert [x['qty'] for x in values] == [Decimal('0.28'), Decimal('0.01')]
    assert [x['side'] for x in values] == ['LONG', 'SHORT']
    assert values[0]['unrealized'] == Decimal('-25.5')
    assert values[0]['opened_at'].tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_missing_position_fields_fail_closed(adapter):
    adapter._table = AsyncMock(return_value=[
        {"id": "888", "tradableInstrumentId": "6310", "side": "buy"},
    ])
    with pytest.raises(RuntimeError, match='missing id, instrument id or quantity'):
        await adapter.get_positions()


def test_stop_loss_ids_are_not_prices():
    raw = {"id": "888", "symbol": "XAUUSD.X", "side": "buy", "qty": "0.01",
           "avgPrice": "4196.35", "stopLossId": "999000", "takeProfitId": "999001"}
    position = _tradelocker_position_values(raw, SimpleNamespace(instrument='XAUUSD.X'))
    assert position['stop_loss'] is None
    assert position['target'] is None


@pytest.mark.asyncio
async def test_schema_mapping_rejects_truncated_rows(adapter):
    adapter._request = AsyncMock(side_effect=[
        {'d': {'positionsConfig': {'columns': [{'id': 'id'}, {'id': 'qty'}]}}},
        {'d': {'positions': [['123']]}}
    ])
    with pytest.raises(RuntimeError, match='row/schema length mismatch'):
        await adapter._table('positions', 'positionsConfig')

@pytest.mark.asyncio
async def test_account_state_exposes_syncable_financials(adapter):
    adapter.server = 'GFTTL'
    adapter._request = AsyncMock(side_effect=[
        {'d': [{'id': 2540480, 'currency': 'USD'}]},
        {'d': {'accountDetailsData': [5000, 4973.20, 779.31]}},
    ])
    adapter._config_cache = {
        'accountDetailsConfig': {'columns': [
            {'id': 'balance'}, {'id': 'equity'}, {'id': 'freeMargin'},
        ]}
    }
    account = await adapter.get_account_info()
    assert account['connected'] is True
    assert account['balance'] == Decimal('5000')
    assert account['equity'] == Decimal('4973.20')
    assert account['free_margin'] == Decimal('779.31')


@pytest.mark.asyncio
async def test_order_history_only_returns_requested_broker_ids(adapter):
    adapter._table = AsyncMock(return_value=[
        {'id': 'accepted-1', 'status': 'Filled', 'positionId': '888'},
        {'id': 'another-account-entry', 'status': 'Filled', 'positionId': '889'},
    ])
    records = await adapter.get_order_history(['accepted-1'])
    assert len(records) == 1
    assert records[0]['positionId'] == '888'
    assert adapter._table.await_args.kwargs['params']['from'] < adapter._table.await_args.kwargs['params']['to']
