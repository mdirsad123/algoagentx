"""Allocation benchmark: baseline ORM accumulation vs bounded 401K writes.

No DB is contacted. Times are serialization/preparation, NOT PostgreSQL latency.
"""
import asyncio
import gc
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db.models import EquityCurve
from app.services.backtest_equity import persist_equity_events


def main(mode):
    count = 401014
    data = SimpleNamespace(equity_curve=[100.] * count,
                           equity_timestamps=[datetime(2020, 1, 1) + timedelta(minutes=i * 5) for i in range(count)])
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    if mode == "before":
        rows = [{"timestamp": stamp.isoformat(), "equity": value} for stamp, value in zip(data.equity_timestamps, data.equity_curve)]
        objects = [EquityCurve(backtest_id="benchmark", timestamp=datetime.fromisoformat(row["timestamp"]), equity=Decimal(str(row["equity"]))) for row in rows]
        assert len(objects) == count
    else:
        class DB:
            async def execute(self, stmt, rows=None):
                if rows is None:
                    return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [
                        {"column_name": "event_sequence", "data_type": "integer"},
                        {"column_name": "timestamp", "data_type": "timestamp without time zone"}]))
                assert len(rows) <= 1000
        asyncio.run(persist_equity_events(DB(), "benchmark", data))
    _, peak = tracemalloc.get_traced_memory()
    print(json.dumps({"mode": mode, "points": count, "preparation_seconds": time.perf_counter() - start,
                      "peak_incremental_python_bytes": peak}), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1]
    if "--launch" in sys.argv:
        out = ROOT.parent / "artifacts/backtest_private" / f"persistence_{mode}.log"
        with out.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-u", __file__, mode], stdout=log, stderr=subprocess.STDOUT)
        print(f"Started persistence {mode} benchmark pid={process.pid}")
    else:
        main(mode)