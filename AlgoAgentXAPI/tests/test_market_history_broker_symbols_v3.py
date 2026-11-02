"""Broker symbol resolution must be exact/account-scoped, never MT5 suffix copying."""
import sys
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

from app.db.models import BrokerAccount, BrokerProvider
from app.services.market_data.daily_sync import broker_exact_match, broker_symbol_catalog


def test_provider_suffixes_are_not_guessed():
    names = [{"symbol": "XAUUSD"}, {"symbol": "BTCUSD"}]
    assert broker_exact_match(names, "XAUUSD") == "XAUUSD"
    assert broker_exact_match(names, "XAUUSDm") is None
    names = [{"symbol": "XAUUSD.x"}]
    assert broker_exact_match(names, "XAUUSD.x") == "XAUUSD.x"
    assert broker_exact_match(names, "XAUUSDm") is None


@pytest.mark.asyncio
async def test_ctrader_symbols_from_requested_subaccount_only(monkeypatch):
    broker_api = ModuleType("app.api.v1.broker_accounts")
    async def refresh(*args):
        return None
    broker_api._refresh_ctrader_token_if_needed = refresh
    monkeypatch.setitem(sys.modules, "app.api.v1.broker_accounts", broker_api)
    class FakeAdapter:
        async def fetch_symbols(self, subaccount_id, limit):
            assert subaccount_id == "202"
            assert limit == 2000
            return [{"symbol_name": "XAUUSD", "symbol_id": 999},
                    {"symbol_name": "BTCUSD", "symbol_id": 111}]
    def make_adapter(account, db):
        assert account.metadata_json["ctrader_selected_account"]["ctrader_account_id"] == 202
        assert "ctrader_symbols_preview" not in account.metadata_json
        return FakeAdapter()
    factory = ModuleType("app.services.brokers.factory")
    factory.get_broker_adapter = make_adapter
    monkeypatch.setitem(sys.modules, "app.services.brokers.factory", factory)
    provider = BrokerProvider(code="CTRADER", is_enabled=True)
    original = BrokerAccount(broker_code="CTRADER", broker_name="CTRADER", broker_provider=provider,
        status="CONNECTED", metadata_json={
            "ctrader_accounts":[{"ctrader_account_id":101},{"ctrader_account_id":202}],
            "ctrader_selected_account":{"ctrader_account_id":101},
            "ctrader_symbols_preview":[{"symbol_name":"XAUUSDm","symbol_id":123}],
        })
    rows = await broker_symbol_catalog(AsyncMock(), original, "202")
    assert [x["symbol"] for x in rows] == ["XAUUSD", "BTCUSD"]
    assert original.metadata_json["ctrader_selected_account"]["ctrader_account_id"] == 101


@pytest.mark.asyncio
async def test_tradelocker_exact_suffix_and_deduplicated_symbols(monkeypatch):
    class FakeAdapter:
        async def get_symbols(self, limit):
            return [{"symbol":"XAUUSD.x", "instrument_key":"44"}, {"symbol":"XAUUSD.x"},
                    {"symbol":"BTCUSD.x", "instrument_key":"45"}]
    factory = ModuleType("app.services.brokers.factory")
    factory.get_broker_adapter = lambda account, db: FakeAdapter()
    monkeypatch.setitem(sys.modules, "app.services.brokers.factory", factory)
    provider = BrokerProvider(code="TRADELOCKER", is_enabled=True)
    account = BrokerAccount(broker_code="TRADELOCKER", broker_name="TRADELOCKER", broker_provider=provider,
        status="CONNECTED", metadata_json={"tradelocker_account_id":"a-12", "tradelocker_acc_num":42,
          "tradelocker_environment":"DEMO"})
    rows = await broker_symbol_catalog(AsyncMock(), account, "a-12")
    assert [x["symbol"] for x in rows] == ["XAUUSD.x", "BTCUSD.x"]
    assert broker_exact_match(rows, "XAUUSDm") is None
