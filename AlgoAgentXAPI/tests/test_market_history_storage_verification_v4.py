"""Source feed verification never mixes broker and legacy backtest candles."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.services.market_data.feed_inspection import inspect_feed_storage


def config_fixture():
    return SimpleNamespace(
        id=uuid4(), instrument_id=23, provider="CTRADER",
        broker_symbol="BTCUSD", timeframe="5m", is_primary=False, publish_approved=False,
    )


@pytest.mark.asyncio
async def test_source_candles_reported_without_claiming_canonical_backtest_data():
    config = config_fixture()
    ts = datetime(2026, 10, 31, tzinfo=timezone.utc)
    row = SimpleNamespace(timestamp=ts, open=Decimal("111.010"), high=Decimal("112.0"),
                          low=Decimal("110.00"), close=Decimal("111.500"), volume=Decimal("0"))
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(one=lambda: (4140, ts, ts)),
        SimpleNamespace(one=lambda: (0, None, None)),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [row])),
        SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(status="UP_TO_DATE", dry_run=False)),
    ]
    result = await inspect_feed_storage(db, config)
    assert result["source"]["count"] == 4140
    assert result["canonical"]["count"] == 0
    assert result["broker_symbol"] == "BTCUSD"
    assert result["latest_candles"][0]["open"] == "111.01000"
    assert result["last_run_status"] == "UP_TO_DATE"
    assert result["last_run_dry_run"] is False
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_empty_feed_and_preview_status_is_not_mistaken_for_saved_data():
    config = config_fixture()
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(one=lambda: (0, None, None)),
        SimpleNamespace(one=lambda: (198, None, None)),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
        SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(status="PREVIEW", dry_run=True)),
    ]
    result = await inspect_feed_storage(db, config)
    assert result["source"]["count"] == 0
    assert result["canonical"]["count"] == 198
    assert result["last_run_dry_run"] is True
    assert result["latest_candles"] == []


def test_client_and_controller_use_admin_only_storage_verification():
    root = Path(__file__).parents[2]
    controller = (root / "AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py").read_text()
    client = (root / "AlgoAgentXApp/lib/api/admin.ts").read_text()
    assert '@router.get("/configs/{config_id}/verification")' in controller
    assert 'router = APIRouter(dependencies=[Depends(get_admin_user)])' in controller
    assert 'await inspect_feed_storage(db, config)' in controller
    assert '${historyBase}/configs/${id}/verification' in client


def test_frontend_history_select_is_always_controlled_and_shows_labels():
    root = Path(__file__).parents[2]
    select = (root / "AlgoAgentXApp/app/(admin)/admin/market-data/HistorySelect.tsx").read_text()
    panel = (root / "AlgoAgentXApp/app/(admin)/admin/market-data/DailyHistoryPanel.tsx").read_text()
    assert "Primitive.Root value={value}" in select
    assert "value={value || undefined}" not in select
    assert "Selection unavailable" in select
    assert "Verify Stored Data" in panel
    assert "Connected broker account" in panel and "Trading subaccount" in panel
