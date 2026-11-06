"""Pure/unit checks; generated cases are test fixtures, never production data."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

from app.services.backtest_control import ExecutionControl, BacktestInterrupted, current_control
from app.services.backtest_equity import iter_equity_events, equity_preview, persist_equity_events
from app.services.backtest_jobs import lock_key


def result(values, timestamps):
    return SimpleNamespace(equity_curve=values, equity_timestamps=timestamps)


def test_same_timestamp_events_preserve_every_value_and_order():
    timestamp = datetime(2026, 1, 1)
    rows = list(iter_equity_events(result([100, 100, 90, 110], [timestamp] * 4)))
    assert [r["equity"] for r in rows] == [100, 100, 90, 110]
    assert [r["event_sequence"] for r in rows] == [0, 1, 2, 3]
    assert len({r["timestamp"] for r in rows}) == 1


def test_equivalent_timezones_share_sequence():
    utc = datetime(2026, 1, 1, tzinfo=timezone.utc)
    other = utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert [r["event_sequence"] for r in iter_equity_events(result([10, 20], [utc, other]))] == [0, 1]


@pytest.mark.parametrize("values,timestamps", [([1], []), ([1], [None]), ([float("nan")], [datetime(2026, 1, 1)]),
    ([1, 2], [datetime(2026, 1, 2), datetime(2026, 1, 1)])])
def test_invalid_equity_is_not_silently_discarded(values, timestamps):
    with pytest.raises(ValueError):
        list(iter_equity_events(result(values, timestamps)))


def test_preview_preserves_endpoints_without_losing_events_in_source():
    dates = pd.date_range("2026-01-01", periods=10001, freq="5min")
    data = result(list(range(len(dates))), dates)
    preview = equity_preview(data, 11)
    assert len(preview) == 11
    assert preview[0]["equity"] == 0
    assert preview[-1]["equity"] == 10000
    assert len(data.equity_curve) == 10001


def test_bounded_401k_persistence_uses_no_orm_collection():
    class Metadata:
        def mappings(self):
            return self

        def all(self):
            return [{"column_name": "timestamp", "data_type": "timestamp without time zone"},
                    {"column_name": "backtest_id", "data_type": "text"},
                    {"column_name": "event_sequence", "data_type": "integer"}]

    class DB:
        count = 0
        largest = 0

        async def execute(self, statement, rows=None):
            if rows is None:
                return Metadata()
            assert "ON CONFLICT" not in str(statement)
            assert all(row["timestamp"].tzinfo is None for row in rows)
            self.count += len(rows)
            self.largest = max(self.largest, len(rows))

    db = DB()
    count = 401_014
    data = result([100.] * count, pd.date_range("2020-01-01", periods=count, freq="5min"))
    assert asyncio.run(persist_equity_events(db, "test", data, batch_size=1000)) == count
    assert db.count == count
    assert db.largest == 1000


def test_persistence_conflict_propagates_for_atomic_rollback():
    class DB:
        async def execute(self, statement, rows=None):
            if rows is None:
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [
                    {"column_name": "event_sequence", "data_type": "integer"}]))
            raise RuntimeError("conflicting equity")
    with pytest.raises(RuntimeError, match="conflicting equity"):
        asyncio.run(persist_equity_events(DB(), "test", result([10.], [datetime(2026, 1, 1)])))


def test_control_is_cooperative_and_context_local():
    control = ExecutionControl()
    control.checkpoint("replay", 1024, 400000)
    assert control.snapshot()["processed"] == 1024
    control.stopped.set()
    with pytest.raises(BacktestInterrupted):
        control.checkpoint()
    assert current_control.get() is None


def test_lock_key_is_stable_signed_64_bit():
    assert lock_key("job-a") == lock_key("job-a")
    assert lock_key("job-a") != lock_key("job-b")
    assert -(2**63) <= lock_key("job-a") < 2**63


def test_queue_isolation_and_no_api_fallback():
    from app.backtest_celery import backtest_app
    assert backtest_app.conf.task_default_queue == "backtest"
    assert backtest_app.conf.worker_concurrency == 1
    assert backtest_app.conf.worker_max_tasks_per_child == 1
    root = Path(__file__).resolve().parents[1]
    route = (root / "app/api/v1/backtests.py").read_text(encoding="utf-8")
    submit = route.split('@router.post("/run"', 1)[1].split('@router.get', 1)[0]
    assert "background_tasks.add_task" not in submit
    assert "await register_job(db, job_id)" in submit
    assert "await dispatch_job(job_id)" in submit
    compose = (root.parent / "docker-compose.yml").read_text(encoding="utf-8")
    worker = compose.split("  backtest_worker:")[1].split("  backtest_dispatcher:")[0]
    assert '"-Q", "backtest"' in worker
    assert 'mem_limit:' in worker


def test_frozen_strategy_and_risk_files_unchanged():
    import subprocess
    root = Path(__file__).resolve().parents[2]
    changed = subprocess.check_output(["git", "diff", "--name-only"], cwd=root, text=True).splitlines()
    assert not any(name.startswith("AlgoAgentXAPI/strategies/") for name in changed)
    assert not any(name.startswith("AlgoAgentXAPI/app/services/trading/") for name in changed)