"""Read-only, bounded deployment audit. Never prints credentials or strategy source."""
import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def main():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            queries = {
                "migration": "SELECT * FROM alembic_version",
                "equity_columns": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'equity_curve' ORDER BY ordinal_position",
                "equity_constraints": "SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conrelid = 'equity_curve'::regclass",
                "active_backtests": "SELECT id, status, progress, retry_count, started_at, updated_at FROM job_status WHERE job_type = 'backtest' AND status IN ('pending','queued','running','retry') ORDER BY created_at LIMIT 30",
                "strategies": "SELECT id, name FROM strategies WHERE name ILIKE '%V8.2%' OR name ILIKE '%NAS100%V1.8%' LIMIT 10",
            }
            output = {}
            for name, sql in queries.items():
                try:
                    async with conn.begin_nested():
                        output[name] = [dict(row) for row in (await conn.execute(text(sql))).mappings()]
                except Exception as exc:
                    output[name] = {"unavailable": type(exc).__name__}
            output["source_hashes"] = {
                name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                for name in ("app/tasks.py", "app/celery_app.py", "app/api/v1/backtests.py", "engine/backtest_engine.py")
            }
            print(json.dumps(output, default=str, indent=2))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())