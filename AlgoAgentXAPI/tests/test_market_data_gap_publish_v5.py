"""V5 regression checks for explicit canonical gap publication and UI wiring."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import insert as pg_insert, dialect
from sqlalchemy import select

from app.db.models import MarketData, MarketDataCanonicalProvenance, MarketDataFeedCandle
from app.services.market_data.feed_publish import (
    preview_publication, publish_selected_candles, publish_all_missing,
    insert_with_provenance,
)

ROOT = Path(__file__).parents[2]


def config(primary=True, approved=True, archived=False):
    return SimpleNamespace(id=uuid4(), instrument_id=42, timeframe="5m", provider="CTRADER",
                           broker_symbol="XAUUSD", is_primary=primary,
                           publish_approved=approved, is_archived=archived)


def test_sql_is_insert_only_and_keys_are_canonical():
    feed = config()
    stmt = pg_insert(MarketData.__table__).from_select(
        ["instrument_id", "timeframe", "timestamp", "open", "high", "low", "close", "volume"],
        select(MarketDataFeedCandle.feed_id, MarketDataFeedCandle.feed_id,
               MarketDataFeedCandle.timestamp, MarketDataFeedCandle.open, MarketDataFeedCandle.high,
               MarketDataFeedCandle.low, MarketDataFeedCandle.close, MarketDataFeedCandle.volume),
    ).on_conflict_do_nothing(index_elements=["instrument_id", "timeframe", "timestamp"])
    sql = str(stmt.compile(dialect=dialect()))
    assert "ON CONFLICT (instrument_id, timeframe, timestamp) DO NOTHING" in sql
    assert "UPDATE" not in sql.upper()
    assert "market_data_canonical_provenance" in MarketDataCanonicalProvenance.__table__.name
    assert "is_archived" in __import__("app.db.models", fromlist=["MarketDataSyncConfig"]).MarketDataSyncConfig.__table__.columns


@pytest.mark.asyncio
async def test_secondary_or_archived_source_never_publishes():
    db = AsyncMock()
    for feed in (config(primary=False), config(approved=False), config(archived=True)):
        count = await publish_selected_candles(db, feed, [datetime(2026, 10, 31, tzinfo=timezone.utc)])
        assert count == 0
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_published_candles_get_provenance_in_same_transaction():
    db = AsyncMock()
    ts = datetime(2026, 10, 31, tzinfo=timezone.utc)
    db.execute.side_effect = [None, SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [ts])), None]
    feed = config()
    stmt = select(MarketDataFeedCandle.timestamp)
    count = await insert_with_provenance(db, feed, stmt)
    assert count == 1
    assert db.execute.await_count == 3
    assert "SET LOCAL TIME ZONE 'UTC'" in str(db.execute.await_args_list[0].args[0])
    canonical_sql = str(db.execute.await_args_list[1].args[0].compile(dialect=dialect()))
    audit_sql = str(db.execute.await_args_list[2].args[0].compile(dialect=dialect()))
    assert "DO NOTHING RETURNING" in canonical_sql
    assert "market_data_canonical_provenance" in audit_sql
    assert "DO NOTHING" in audit_sql
    db.commit.assert_not_awaited()  # caller owns the single transaction


@pytest.mark.asyncio
async def test_preview_reports_missing_overlaps_and_difference_without_writes():
    db = AsyncMock()
    ts = datetime(2026, 10, 31, tzinfo=timezone.utc)
    db.execute.side_effect = [None, SimpleNamespace(one=lambda: (120, 100, 20, 17, ts-timedelta(days=1), ts))]
    result = await preview_publication(db, config())
    assert result["missing_rows"] == 20
    assert result["overlapping_rows"] == 100
    assert result["different_ohlc_overlaps_preserved"] == 17
    assert result["overwrites"] == 0
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_bounded_publisher_paginates_and_commits_progress():
    feed = config()
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    times = [now-timedelta(minutes=5), now]
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: now-timedelta(days=2)),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: times)),
        SimpleNamespace(scalar_one_or_none=lambda: now),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
    ]
    run = SimpleNamespace(last_before=None, last_after=None, inserted=0, skipped=0, fetched=0)
    with patch("app.services.market_data.feed_publish.publish_selected_candles", new_callable=AsyncMock, return_value=1):
        status = await publish_all_missing(db, feed, run)
    assert status == "UP_TO_DATE"
    assert (run.fetched, run.inserted, run.skipped) == (2, 1, 1)
    assert run.last_after == now
    assert db.commit.await_count == 1


def test_admin_routes_are_explicit_and_old_provider_refresh_no_longer_selected_for_cloud():
    api = (ROOT / "AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py").read_text()
    ui = (ROOT / "AlgoAgentXApp/app/(admin)/admin/market-data/page.tsx").read_text()
    for path in ('/canonical-source', '/configs/{config_id}/publish-preview',
                 '/configs/{config_id}/publish-missing', '/configs/{config_id}/archive'):
        assert path in api
    assert "marketHistoryApi.canonicalSource" in ui
    assert 'provider === "CTRADER" || provider === "TRADELOCKER"' in ui
    assert "Refresh Coverage" in ui


def test_dropdown_unmount_blank_and_oversized_layout_regressions():
    selector = (ROOT / "AlgoAgentXApp/app/(admin)/admin/market-data/HistorySelect.tsx").read_text()
    panel = (ROOT / "AlgoAgentXApp/app/(admin)/admin/market-data/DailyHistoryPanel.tsx").read_text()
    assert '<span aria-hidden="true"' in selector
    assert '<Primitive.Value' not in selector  # No duplicate selected-label rendering
    assert 'items-start gap-1' in selector
    assert 'className="!h-10 !min-h-10"' in panel
    assert 'Publish Missing' in panel and '>Delete</Button>' in panel
    assert 'sessionStorage' in panel
