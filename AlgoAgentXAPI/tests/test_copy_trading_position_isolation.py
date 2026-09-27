import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.services.live.broker_sync_service import reconcile_positions


class _Scalars:
    def all(self):
        return []


class _Result:
    def scalars(self):
        return _Scalars()


class _FakeDB:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result()


def test_reconcile_positions_is_scoped_to_copy_broker_account():
    db = _FakeDB()
    deployment = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        broker_account_id=uuid4(),
        broker_symbol="XAUUSD",
        instrument="XAUUSD",
    )

    result = asyncio.run(reconcile_positions(db, deployment, [], "CTRADER"))

    assert result["open_positions_count"] == 0
    assert db.statements
    sql = str(db.statements[0])
    assert "live_positions.deployment_id" in sql
    assert "live_positions.broker_account_id" in sql
    assert "live_positions.status" in sql
