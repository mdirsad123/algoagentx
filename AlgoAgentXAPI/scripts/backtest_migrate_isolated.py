"""Apply only this revision to an explicitly named isolated verification DB.

Production has no Alembic stamp; this is deliberately NOT an auto-stamp tool.
"""
import importlib.util
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic.migration import MigrationContext
from alembic.operations import Operations


def main():
    url = os.environ["BACKTEST_TEST_DATABASE_URL"]
    if "backtest_repair_test" not in url:
        raise RuntimeError("Refusing any database other than backtest_repair_test")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS job_status (id text PRIMARY KEY, user_id text NOT NULL, job_type text DEFAULT 'backtest', status text NOT NULL, progress integer DEFAULT 0, retry_count integer DEFAULT 0, started_at timestamptz, completed_at timestamptz, updated_at timestamptz DEFAULT now(), created_at timestamptz DEFAULT now(), job_data text, result_data text, message text)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS equity_curve (backtest_id text NOT NULL, timestamp timestamp NOT NULL, equity numeric, PRIMARY KEY(backtest_id,timestamp))"))
        path = Path(__file__).resolve().parents[1] / "alembic/versions/20261106_backtest_reliability.py"
        spec = importlib.util.spec_from_file_location("backtest_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()
    engine.dispose()
    print("Isolated migration applied successfully")


if __name__ == "__main__":
    main()