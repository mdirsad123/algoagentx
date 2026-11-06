"""Run bounded isolated checks outside the tool's 30-second command window."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "backtest_private"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    name = sys.argv[1]
    commands = {
        "unit": [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
                 "tests/test_backtest_reliability.py", "tests/test_backtest_warmup_window.py",
                 "tests/test_backtest_partial_exit_90_at_1_7r.py", "tests/test_dynamic_loader_base_regression.py"],
        "integration": [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
                        "tests/test_backtest_postgres_recovery.py"],
        "regression": [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
                       "tests/test_copy_shared_login_20261105.py", "tests/test_copy_execution_reliability.py",
                       "tests/test_live_partial_exit_management.py", "tests/test_runtime_partial_exit_config.py",
                       "tests/test_live_order_dedupe_claim.py"],
    }
    if len(sys.argv) == 2:
        with (OUT / f"{name}.log").open("w", encoding="utf-8") as output:
            process = subprocess.Popen([sys.executable, "-u", __file__, name, "--run"], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        print(f"Started {name} validation pid={process.pid}")
    else:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                   BACKTEST_TEST_DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:55439/backtest_repair_test")
        code = subprocess.call(commands[name], cwd=ROOT, env=env)
        (OUT / f"{name}.exit").write_text(str(code), encoding="utf-8")
        sys.exit(code)