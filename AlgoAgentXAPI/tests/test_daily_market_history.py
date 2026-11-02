"""Offline tests for the isolated daily historical candle subsystem."""
import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType

import pytest

from app.db.models import BrokerAccount, BrokerProvider
from app.db.models.market_data_sync import MarketDataSyncConfig, MarketDataFeedCandle
from app.services.market_data.daily_sync import (
    TIMEFRAMES, enabled_globally, fetch_window, last_expected_closed, next_daily_run,
    safe_error, subaccounts, verify_source,
)


def account(provider="CTRADER", connected=True):
    broker = BrokerProvider(code=provider, is_enabled=True)
    if provider == "CTRADER":
        metadata = {"ctrader_accounts": [
            {"ctrader_account_id": 12345, "account_type": "DEMO"},
            {"ctrader_account_id": 67890, "account_type": "LIVE"},
        ], "ctrader_selected_account": {"ctrader_account_id": 12345, "account_type": "DEMO"}}
    else:
        metadata = {"tradelocker_account_id": "abc-100", "tradelocker_acc_num": 14,
                    "tradelocker_environment": "demo"}
    return BrokerAccount(broker_code=provider, broker_name=provider, status="CONNECTED" if connected else "DISCONNECTED",
                         broker_provider=broker, metadata_json=metadata, mode="DEMO")


def test_schedule_is_three_am_ist(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_SYNC_TIMEZONE", "Asia/Kolkata")
    monkeypatch.setenv("MARKET_DATA_SYNC_LOCAL_TIME", "03:00")
    now = datetime(2026, 10, 30, 21, 10, tzinfo=timezone.utc)  # 02:40 IST the 31st
    assert next_daily_run(now) == "2026-10-31T03:00:00+05:30"
    assert next_daily_run(now + timedelta(minutes=30)) == "2026-11-01T03:00:00+05:30"


def test_feature_off_default(monkeypatch):
    monkeypatch.delenv("MARKET_DATA_DAILY_SYNC_ENABLED", raising=False)
    assert not enabled_globally()
    monkeypatch.setenv("MARKET_DATA_DAILY_SYNC_ENABLED", "true")
    assert enabled_globally()


def test_latest_open_is_closed_candle_not_forming():
    dt = datetime(2026, 10, 31, 3, 7, tzinfo=timezone.utc)
    assert last_expected_closed(dt, "5m") == datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc)
    assert last_expected_closed(dt, "1h") == datetime(2026, 10, 31, 2, 0, tzinfo=timezone.utc)


def test_ctrader_subaccounts_are_distinct_and_authorized():
    row = account()
    found = subaccounts(row)
    assert [x["id"] for x in found] == ["12345", "67890"]
    assert verify_source(row, subaccount_id="67890", provider="CTRADER")["environment"] == "LIVE"
    with pytest.raises(ValueError, match="not discovered"):
        verify_source(row, subaccount_id="00000", provider="CTRADER")
    with pytest.raises(ValueError, match="does not match"):
        verify_source(row, subaccount_id="12345", provider="TRADELOCKER")


def test_disconnected_account_cannot_be_enabled():
    with pytest.raises(ValueError, match="not connected"):
        verify_source(account(connected=False), subaccount_id="12345", provider="CTRADER")


def test_tradelocker_selected_account_requires_exact_accnum():
    row = account("TRADELOCKER")
    assert subaccounts(row)[0]["id"] == "abc-100"
    row.metadata_json = {"tradelocker_account_id": "abc-100"}
    assert subaccounts(row) == []


def test_no_tokens_in_sanitized_worker_errors():
    status, msg = safe_error(ValueError("secret_token=xyz_abcdef unauthorized https://broker.com/api?token=xxxx"))
    assert status == "AUTH_EXPIRED"
    assert "abcdef" not in msg and "xxxx" not in msg


def test_primary_feed_partial_unique_constraint():
    ix = next(x for x in MarketDataSyncConfig.__table__.indexes if x.name == "uq_market_sync_primary")
    assert ix.unique
    assert str(ix.dialect_options["postgresql"]["where"]) == "is_primary = true"
    assert [x.name for x in MarketDataFeedCandle.__table__.primary_key.columns] == ["feed_id", "timestamp"]


@pytest.mark.asyncio
async def test_ctrader_native_timeframe_and_exact_account(monkeypatch):
    row = account()
    calls = []
    class FakeAdapter:
        async def get_rates_history(self, symbol, tf, count, before):
            calls.append((symbol, tf, count, before))
            return [
                {"candle_time": datetime(2026, 10, 30, 11, 55, tzinfo=timezone.utc)},
                {"candle_time": datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)},
                {"candle_time": datetime(2026, 10, 30, 12, 5, tzinfo=timezone.utc)},
                {"candle_time": datetime(2026, 10, 30, 12, 10, tzinfo=timezone.utc)},
            ]
    def create_adapter(broker, db):
        assert broker.metadata_json["ctrader_selected_account"]["ctrader_account_id"] == 67890
        # Live selection on original ORM record must remain 12345.
        assert row.metadata_json["ctrader_selected_account"]["ctrader_account_id"] == 12345
        return FakeAdapter()
    fake_factory = ModuleType("app.services.brokers.factory")
    fake_factory.get_broker_adapter = create_adapter
    monkeypatch.setitem(sys.modules, "app.services.brokers.factory", fake_factory)
    cfg = MarketDataSyncConfig(provider="CTRADER", timeframe="5m", broker_symbol="XAUUSD", subaccount_id="67890")
    start = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 30, 12, 10, tzinfo=timezone.utc)
    result = await fetch_window(None, row, cfg, start=start, end=end)
    assert len(result) == 2
    assert calls[0][0] == "XAUUSD" and calls[0][1] == "M5"
    assert calls[0][3] == end
