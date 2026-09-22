import asyncio

from sqlalchemy.dialects import postgresql

from app.services.live import auto_runner_service


class _Result:
    def scalars(self):
        return self

    def all(self):
        return []


class _Session:
    def __init__(self):
        self.query = None

    async def execute(self, query):
        self.query = query
        return _Result()


def test_event_enabled_legacy_scan_keeps_other_brokers(monkeypatch):
    monkeypatch.setattr(auto_runner_service.settings, "live_event_pipeline_enabled", True)
    monkeypatch.setattr(auto_runner_service.settings, "live_market_worker_enabled", True)
    db = _Session()
    result = asyncio.run(auto_runner_service.run_due_deployments(db))
    statement = str(db.query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert result["success"] is True
    assert "broker_providers" in statement
    assert "CTRADER" in statement and "CTRADER_API" in statement
    assert "NOT IN" in statement


def test_legacy_scan_still_covers_all_brokers_after_rollback(monkeypatch):
    monkeypatch.setattr(auto_runner_service.settings, "live_event_pipeline_enabled", False)
    db = _Session()
    asyncio.run(auto_runner_service.run_due_deployments(db))
    statement = str(db.query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert "broker_providers" not in statement
    assert "CTRADER" not in statement
