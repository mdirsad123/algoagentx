"""Real Celery SIGKILL, duplicate delivery and isolated Redis restart checks.

The effect ledger below is a transaction test, not a substitute for exercising
the production subscription/credit accounting integration.
"""
import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from celery import Celery
from sqlalchemy import create_engine, text

OUT = Path(__file__).resolve().parents[2] / "artifacts/backtest_private"


def main():
    engine = create_engine("postgresql+psycopg2://postgres@127.0.0.1:55439/backtest_repair_test")
    app = Celery("fault_test_producer", broker="redis://127.0.0.1:55440/0")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS backtest_test_effect (job_id text PRIMARY KEY, amount integer NOT NULL)"))

    def create(payload):
        job = str(uuid4())
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO job_status (id,user_id,status,job_data) VALUES (:job,'isolated-test','queued',:payload)"),
                         {"job": job, "payload": json.dumps(payload)})
            conn.execute(text("INSERT INTO backtest_execution (job_id) VALUES (:job)"), {"job": job})
        return job

    def send(job):
        app.send_task("backtest_test.execute", args=[job], queue="backtest", retry=False)

    def wait(job, desired):
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            with engine.connect() as conn:
                status = conn.execute(text("SELECT status FROM job_status WHERE id=:job"), {"job": job}).scalar()
            if status == desired:
                return
            if status == "failed":
                raise AssertionError(f"Isolated job {job} failed")
            time.sleep(1)
        raise TimeoutError(f"Isolated job did not reach {desired}")

    killed = create({"kill_first": True})
    send(killed)
    wait(killed, "completed")
    send(killed)
    send(killed)
    reconnect = create({"delay": 20})
    send(reconnect)
    wait(reconnect, "running")
    subprocess.run(["docker", "restart", "algoagentx_backtest_repair_test_redis"], check=True)
    time.sleep(3)
    send(reconnect)
    wait(reconnect, "completed")
    time.sleep(5)
    with engine.connect() as conn:
        for job, attempts in ((killed, 2), (reconnect, 1)):
            assert conn.execute(text("SELECT attempts FROM backtest_execution WHERE job_id=:job"), {"job": job}).scalar() == attempts
            assert conn.execute(text("SELECT count(*) FROM backtest_test_effect WHERE job_id=:job"), {"job": job}).scalar() == 1
    print("PASS: actual worker child SIGKILL recovered; duplicates had one committed effect; isolated Redis restart retained running execution", flush=True)
    engine.dispose()


if __name__ == "__main__":
    if "--launch" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "fault.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-u", __file__], stdout=log, stderr=subprocess.STDOUT)
        print(f"Started fault verification pid={process.pid}")
    else:
        try:
            main()
        except BaseException:
            (OUT / "fault.exit").write_text("1")
            raise
        (OUT / "fault.exit").write_text("0")