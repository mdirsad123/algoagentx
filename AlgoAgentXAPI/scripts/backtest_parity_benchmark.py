"""Read-only production fixture export and isolated, exact engine parity.

Exports stay under ignored artifacts/backtest_private. No task submission,
billing, live broker access, or production writes are performed.
"""
import argparse
import asyncio
import cProfile
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PRIVATE = ROOT.parent / "artifacts" / "backtest_private"


async def export():
    from dotenv import dotenv_values
    from sqlalchemy import URL, text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.services import backtest_service as service
    from app.schemas.backtests import BacktestRunRequest
    from engine.backtest_engine import BacktestResult

    env = dotenv_values(ROOT.parent / ".env.prod")
    url = URL.create("postgresql+asyncpg", username=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"],
                     host="127.0.0.1", port=5432, database=env["POSTGRES_DB"])
    engine = create_async_engine(url, connect_args={"server_settings": {"default_transaction_read_only": "on"}})
    PRIVATE.mkdir(parents=True, exist_ok=True)
    try:
        for label, job in (("xauusd", "b9378f66-9188-4bda-8dd3-5bd0c5715c22"), ("nas100", "e1c23f4a-5eff-4f70-9261-da2ad77670a2")):
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                payload = json.loads((await db.execute(text("SELECT job_data FROM job_status WHERE id=:id"), {"id": job})).scalar_one())
                request = BacktestRunRequest.model_validate(payload)
                strategy = (await db.execute(text("SELECT parameters FROM strategies WHERE id=:id"), {"id": request.strategy_id})).scalar_one()
                def capture(frame, strategy_class, params, backtest_params):
                    path = PRIVATE / f"{label}.csv"
                    frame.to_csv(path, index=False, float_format="%.17g")
                    metadata = {"label": label, "candles": len(frame), "params": params,
                                "backtest_params": dataclasses.asdict(backtest_params),
                                "strategy_parameters": strategy,
                                "strategy_id": request.strategy_id,
                                "source_sha256": hashlib.sha256(strategy["source_code"].encode()).hexdigest(),
                                "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    (PRIVATE / f"{label}.json").write_text(json.dumps(metadata, default=str), encoding="utf-8")
                    print(json.dumps({k: metadata[k] for k in ("label", "candles", "source_sha256", "dataset_sha256")}), flush=True)
                    return BacktestResult([], [], float(backtest_params.initial_capital), 0., 0, 0., 0., 0.)
                original = service.run_backtest_engine
                service.run_backtest_engine = capture
                try:
                    await service.BacktestService.run_backtest(
                        db, request.strategy_id, request.instrument_id, request.timeframe,
                        request.start_date, request.end_date, request.capital,
                        advanced_filters=request.advanced_filters, runtime_config=request.runtime_config,
                        strategy_preset_id=request.strategy_preset_id, timeframe_id=request.timeframe_id,
                        warmup_candles=80000,
                    )
                finally:
                    service.run_backtest_engine = original
    finally:
        await engine.dispose()


def benchmark(label, version):
    import pandas as pd
    from datetime import date
    from app.services.dynamic_strategy_loader import build_dynamic_strategy_entry
    from app.services.backtest_control import ExecutionControl, current_control
    from engine import backtest_engine
    meta = json.loads((PRIVATE / f"{label}.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(PRIVATE / f"{label}.csv", float_precision="round_trip", parse_dates=["Date"])
    strategy, _, _ = build_dynamic_strategy_entry(meta["strategy_id"], label, meta["strategy_parameters"])
    module = backtest_engine
    if version == "before":
        source = subprocess.check_output(["git", "show", "HEAD:AlgoAgentXAPI/engine/backtest_engine.py"], cwd=ROOT.parent)
        baseline = PRIVATE / "baseline_engine.py"
        baseline.write_bytes(source)
        spec = importlib.util.spec_from_file_location("baseline_backtest_engine", baseline)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    params = meta["backtest_params"]
    if params.get("report_start_date"):
        params["report_start_date"] = date.fromisoformat(params["report_start_date"])
    control = ExecutionControl()
    token = current_control.set(control)
    profile = cProfile.Profile()
    start = time.perf_counter()
    try:
        profile.enable()
        output = module.run_backtest_engine(frame, strategy, meta["params"], module.BacktestParams(**params))
        profile.disable()
    finally:
        current_control.reset(token)
    elapsed = time.perf_counter() - start
    serialized = json.dumps(dataclasses.asdict(output), default=str, sort_keys=True, separators=(",", ":"))
    (PRIVATE / f"{label}_{version}_result.json").write_text(serialized, encoding="utf-8")
    profile.dump_stats(str(PRIVATE / f"{label}_{version}.prof"))
    report = {"label": label, "version": version, "candles": len(frame), "engine_seconds_profiled": elapsed,
              "trades": output.total_trades, "result_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
              "stages": control.snapshot()}
    (PRIVATE / f"{label}_{version}_timing.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--label", choices=["xauusd", "nas100"])
    parser.add_argument("--version", choices=["before", "after"])
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    if args.launch:
        PRIVATE.mkdir(parents=True, exist_ok=True)
        name = "export" if args.export else f"{args.label}_{args.version}"
        command = [sys.executable, "-u", str(Path(__file__).resolve())] + [a for a in sys.argv[1:] if a != "--launch"]
        with (PRIVATE / f"{name}.log").open("w", encoding="utf-8") as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, cwd=ROOT)
        print(f"Started isolated {name} process pid={process.pid}")
    elif args.export:
        asyncio.run(export())
    else:
        benchmark(args.label, args.version)