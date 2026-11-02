"""Regression coverage for cTrader history worker and safe errors (no live trades)."""
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.models import BrokerAccount, BrokerProvider
from app.services.market_data.daily_sync import _clone_account, safe_error, HistoryFetchError
from app.services.brokers.ctrader import CTraderAdapter, PT_ACCOUNT_AUTH_REQ, PT_GET_TRENDBARS_REQ


def test_safe_error_is_actionable_without_leaking_token():
    e = HistoryFetchError("fetch-candles", "BROKER_TIMEOUT", "Check broker network access")
    assert safe_error(e) == ("FAILED", "fetch-candles: BROKER_TIMEOUT - Check broker network access")
    assert safe_error(ValueError("token=123456 unauthorized"))[0] == "AUTH_EXPIRED"
    assert "123456" not in safe_error(ValueError("token=123456 unauthorized"))[1]
    assert "BROKER_DNS" in safe_error(socket.gaierror("failed"))[1]


def test_ctrader_preview_is_removed_only_when_subaccount_changes():
    broker = BrokerProvider(code="CTRADER", is_enabled=True)
    sub_a = {"ctrader_account_id": 101, "account_type": "DEMO"}
    sub_b = {"ctrader_account_id": 202, "account_type": "DEMO"}
    account = BrokerAccount(broker_code="CTRADER", broker_name="CTRADER", broker_provider=broker,
        status="CONNECTED", metadata_json={"ctrader_accounts": [sub_a, sub_b],
        "ctrader_selected_account": sub_a, "ctrader_symbols_preview": [{"symbol_name": "XAUUSDm", "symbol_id": 456}]})
    own = _clone_account(account, "101")
    other = _clone_account(account, "202")
    assert own.metadata_json.get("ctrader_symbols_preview")
    assert not other.metadata_json.get("ctrader_symbols_preview")
    assert account.metadata_json["ctrader_selected_account"] == sub_a


@pytest.mark.asyncio
async def test_ctrader_window_fetch_uses_bounded_exact_utc_and_decodes_relative_prices(monkeypatch):
    start = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=13)
    requests = []
    class FakeClient:
        async def request(self, typ, payload, expected):
            requests.append((typ, payload))
            if typ == PT_ACCOUNT_AUTH_REQ:
                return {}
            assert typ == PT_GET_TRENDBARS_REQ
            assert payload["symbolId"] == 999
            assert payload["period"] == 5
            return {"trendbar": [{"utcTimestampInMinutes": int(start.timestamp() // 60),
                "low": 435000000, "deltaOpen": 20000, "deltaHigh": 30000, "deltaClose": 10000, "volume": 2}]}
        async def __aexit__(self, *args):
            pass
    broker = BrokerAccount(broker_code="CTRADER", broker_name="CTRADER", status="CONNECTED",
        metadata_json={"ctrader_selected_account": {"ctrader_account_id": 123, "account_type": "DEMO"}})
    adapter = CTraderAdapter(broker)
    async def fake_authorize(*, is_live):
        assert not is_live
        return FakeClient()
    monkeypatch.setattr(adapter, "_openapi_authorized_client", fake_authorize)
    monkeypatch.setattr(adapter, "_access_token", lambda: "not-really-a-token")
    bars = await adapter.get_rates_history_window("XAUUSDm", "M5", start=start, end=end,
              symbol_meta={"symbol_name": "XAUUSDm", "symbol_id": 999})
    assert len(bars) == 1
    assert bars[0]["low"] == Decimal("4350")
    assert bars[0]["high"] == Decimal("4350.3")
    history = [p for typ, p in requests if typ == PT_GET_TRENDBARS_REQ]
    assert len(history) == 2  # 12h and 1h windows, never a multiweek request
    assert history[0]["fromTimestamp"] == int(start.timestamp() * 1000)
    assert history[-1]["toTimestamp"] == int(end.timestamp() * 1000) - 1


@pytest.mark.asyncio
async def test_ctrader_window_rejects_imprecise_symbol(monkeypatch):
    account = BrokerAccount(broker_code="CTRADER", broker_name="CTRADER",
        metadata_json={"ctrader_selected_account": {"ctrader_account_id": 123}})
    adapter = CTraderAdapter(account)
    monkeypatch.setattr(adapter, "_access_token", lambda: "fake")
    with pytest.raises(ValueError, match="not exact"):
        await adapter.get_rates_history_window("XAUUSDm", "M5", start=datetime.now(timezone.utc) - timedelta(days=1),
              end=datetime.now(timezone.utc), symbol_meta={"symbol_name": "XAUUSD", "symbol_id": 999})
