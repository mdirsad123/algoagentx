from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.live.execution_engine import _ctrader_client_order_id


def test_ctrader_client_order_id_is_deterministic_short_and_candle_specific():
    deployment = SimpleNamespace(id=uuid4())
    signal = SimpleNamespace(
        id=uuid4(),
        strategy_id="strategy-1",
        candle_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        signal_type="BUY",
    )
    first = _ctrader_client_order_id(deployment, signal, "ENTRY")
    second = _ctrader_client_order_id(deployment, signal, "ENTRY")
    exit_id = _ctrader_client_order_id(deployment, signal, "EXIT")
    close_first = _ctrader_client_order_id(deployment, signal, "EXIT", scope="broker-position-1")
    close_second = _ctrader_client_order_id(deployment, signal, "EXIT", scope="broker-position-2")
    assert first == second
    assert first != exit_id
    assert close_first != close_second
    assert close_first == _ctrader_client_order_id(deployment, signal, "EXIT", scope="broker-position-1")
    assert len(first) <= 50

    retry_signal = SimpleNamespace(
        id=uuid4(),
        strategy_id="strategy-1",
        candle_time=signal.candle_time,
        signal_type=signal.signal_type,
    )
    assert _ctrader_client_order_id(deployment, retry_signal, "ENTRY") == first
