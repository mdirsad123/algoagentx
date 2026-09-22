import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.services.live.broker_sync_service import replay_pending_ctrader_execution_events


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class _DB:
    def __init__(self, *results):
        self.results = iter(results)

    async def execute(self, _statement):
        return _Rows(next(self.results))


def test_fill_that_arrived_before_local_commit_repairs_order_and_signal():
    deployment = SimpleNamespace(id=uuid4())
    signal = SimpleNamespace(id=uuid4(), status="ACCEPTED")
    order = SimpleNamespace(
        id=uuid4(), signal_id=signal.id, status="PLACED",
        broker_order_id="101", executed_price=None, raw_response={}, trace_id=None,
    )
    event = SimpleNamespace(
        id=uuid4(), broker_order_id="101", processed=False,
        raw_payload={
            "executionType": 3,
            "order": {"clientOrderId": "AX-example"},
            "deal": {"executionPrice": "1.103"},
        },
    )
    count = asyncio.run(replay_pending_ctrader_execution_events(
        _DB([event], [order], [signal]), deployment,
    ))
    assert count == 1
    assert event.processed is True
    assert order.status == "FILLED"
    assert signal.status == "EXECUTED"
    assert str(order.executed_price) == "1.103"
    assert order.raw_response["replayed_execution_event_id"] == str(event.id)


def test_late_ack_cannot_downgrade_a_filled_order():
    deployment = SimpleNamespace(id=uuid4())
    order = SimpleNamespace(
        id=uuid4(), signal_id=None, status="FILLED",
        broker_order_id="102", executed_price=None, raw_response={}, trace_id=None,
    )
    event = SimpleNamespace(
        id=uuid4(), broker_order_id="102", processed=False,
        raw_payload={"executionType": 2, "order": {"clientOrderId": "AX-example"}},
    )
    count = asyncio.run(replay_pending_ctrader_execution_events(
        _DB([event], [order]), deployment,
    ))
    assert count == 1
    assert order.status == "FILLED"
