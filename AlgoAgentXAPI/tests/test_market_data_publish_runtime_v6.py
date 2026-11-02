"""Regression tests that EXECUTE the V5-broken API path and publisher.

Do not replace these with text-only grep/assert tests: the original V5 NameError
was not found by static compilation or source-string assertions.
"""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import dialect

from app.services.market_data.feed_publish import (insert_with_provenance,
    preview_publication, publish_selected_candles)
from app.services.market_data.feed_inspection import display_price



def test_broken_v5_endpoint_dependencies_are_explicitly_imported():
    """Source-level regression even when API runtime deps are not installed."""
    import ast
    from pathlib import Path
    tree = ast.parse((Path(__file__).parents[1] / "app/api/v1/admin_market_data_sync.py").read_text())
    loaded = {name.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for name in node.names}
    assert {"preview_publication", "process_market_canonical_publish"} <= loaded

def cfg():
    return SimpleNamespace(id=uuid4(), instrument_id=7, timeframe="5m",
                           is_primary=True, publish_approved=True, is_archived=False,
                           provider="CTRADER", broker_symbol="BTCUSD")


@pytest.mark.asyncio
async def test_actual_preview_endpoint_callable(monkeypatch):
    # Full FastAPI API module needs python-jose; present in production image.
    # Avoid falsely reporting it as executed on a lean offline test runner.
    pytest.importorskip("jose")
    from app.api.v1 import admin_market_data_sync as admin
    feed = cfg()
    db = AsyncMock()
    db.get.return_value = feed
    implementation = AsyncMock(return_value={"missing_rows": 16, "overwrites": 0})
    monkeypatch.setattr(admin, "preview_publication", implementation)
    response = await admin.publish_preview(feed.id, db=db)
    assert response["data"]["missing_rows"] == 16
    implementation.assert_awaited_once_with(db, feed)


@pytest.mark.asyncio
async def test_actual_publish_endpoint_enqueues_registered_task(monkeypatch):
    pytest.importorskip("jose")
    from app.api.v1 import admin_market_data_sync as admin
    feed = cfg()
    feed.publish_approved = False
    db = AsyncMock()
    db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: feed),
                              SimpleNamespace(scalar_one=lambda: 4150)]
    db.add.side_effect = lambda run: setattr(run, "id", uuid4())
    apply_async = Mock()
    monkeypatch.setattr(admin.process_market_canonical_publish, "apply_async", apply_async)
    response = await admin.publish_missing(
        feed.id, admin.PublishMissingRequest(confirm_insert_missing_only=True), db=db)
    assert response["data"]["status"] == "QUEUED"
    assert feed.publish_approved is True
    assert response["data"]["overwrites"] == 0
    assert apply_async.call_args.kwargs["queue"] == "market_data_daily"
    assert db.commit.await_count == 1


@pytest.mark.asyncio
async def test_preview_sets_local_utc_before_join():
    db = AsyncMock()
    feed = cfg()
    ts = datetime(2026, 10, 31, tzinfo=timezone.utc)
    db.execute.side_effect = [None, SimpleNamespace(one=lambda: (51, 30, 21, 2, ts, ts))]
    result = await preview_publication(db, feed)
    assert result["missing_rows"] == 21
    assert "SET LOCAL TIME ZONE 'UTC'" in str(db.execute.await_args_list[0].args[0])
    sql = str(db.execute.await_args_list[1].args[0].compile(dialect=dialect()))
    assert "LEFT OUTER JOIN market_data" in sql


@pytest.mark.asyncio
async def test_canonical_insert_is_utc_rounded_insert_only_and_audited():
    db = AsyncMock()
    feed = cfg()
    naive = datetime(2026, 10, 31, 18, 5)
    db.execute.side_effect = [None, None,
                              SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [naive])), None]
    added = await publish_selected_candles(db, feed, [naive.replace(tzinfo=timezone.utc)])
    assert added == 1
    canonical_stmt = db.execute.await_args_list[2].args[0]
    audit_stmt = db.execute.await_args_list[3].args[0]
    sql = str(canonical_stmt.compile(dialect=dialect()))
    assert "round(market_data_feed_candles.open" in sql
    assert "ON CONFLICT (instrument_id, timeframe, timestamp) DO NOTHING" in sql
    assert " UPDATE " not in sql
    assert "market_data_canonical_provenance" in str(audit_stmt)
    stamped = [v for v in audit_stmt.compile(dialect=dialect()).params.values() if isinstance(v, datetime)]
    assert stamped and stamped[0].tzinfo == timezone.utc
    assert stamped[0].hour == 18
    db.commit.assert_not_awaited()  # exactly one caller-owned commit


@pytest.mark.asyncio
async def test_unapproved_or_secondary_feed_never_writes():
    db = AsyncMock()
    for primary, approved in [(False, True), (True, False)]:
        feed = cfg()
        feed.is_primary, feed.publish_approved = primary, approved
        assert await publish_selected_candles(db, feed, [datetime.now(timezone.utc)]) == 0
    db.execute.assert_not_awaited()


def test_display_only_five_decimals_without_float_conversion():
    assert display_price(Decimal("81502.1400000000000000000000")) == "81502.14000"
    assert display_price(Decimal("1.234567")) == "1.23457"
