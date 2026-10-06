from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.live.live_latency_trace_service import LiveLatencyTraceService


class _Result:
    def scalar_one_or_none(self):
        return None


class _DB:
    def __init__(self):
        self.execute_calls = 0

    async def execute(self, _stmt):
        self.execute_calls += 1
        return _Result()


@pytest.mark.asyncio
async def test_trace_persist_skips_deleted_deployment_fk():
    deployment_id = uuid4()
    trace_id = f"{deployment_id}:2026-10-06T18:40:00+00:00"
    svc = LiveLatencyTraceService(redis_client=object())
    now = datetime(2026, 10, 6, 18, 40, tzinfo=timezone.utc)

    async def _snapshot(_trace_id):
        assert _trace_id == trace_id
        return {
            "trace_id": trace_id,
            "deployment_id": str(deployment_id),
            "broker_account_id": str(uuid4()),
            "candle_open_time": now.isoformat(),
            "expected_close_at": now.isoformat(),
            "t0_expected_close_at": now.isoformat(),
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "status": "DEPLOYMENT_NOT_FOUND",
        }

    svc.snapshot = _snapshot
    db = _DB()
    result = await svc.persist(db, trace_id)

    assert result["persisted"] is False
    assert result["deployment_missing"] is True
    assert result["deployment_id"] == str(deployment_id)
    assert db.execute_calls == 1
