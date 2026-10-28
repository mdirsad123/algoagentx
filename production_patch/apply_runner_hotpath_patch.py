"""Deterministic source transformation for the 2026-10-27 base patch.

Run only against the approved release ZIP. The changed files are checked into the
resulting package; this script is included for an auditable record, not run at boot.
"""
from pathlib import Path
base=Path(__file__).resolve().parents[1]
runner=base/'AlgoAgentXAPI/app/services/live/strategy_runner.py'
scheduler=base/'AlgoAgentXAPI/app/services/live/auto_runner_service.py'
config=base/'AlgoAgentXAPI/app/core/config.py'

def once(old,new, path):
    s=path.read_text()
    n=s.count(old)
    assert n==1, f'{path.name}: expected one anchor, found {n}: {old[:120]}'
    path.write_text(s.replace(old,new,1))

# Separate diagnostic module is pure and has no impact on signals/orders.
d=(base/'AlgoAgentXAPI/app/services/live/runner_diagnostics.py')
d.write_text('''"""Wall time and CPU-time breakdown for long-running live strategy runs.

Logging uses only safe metadata, never broker tokens, user code, or candle rows.
This intentionally does NOT modify strategy calculations or trading decisions.
"""
from __future__ import annotations
import cProfile
import io
import logging
import pstats
import time
from dataclasses import dataclass, field

@dataclass
class StageClock:
    deployment_id: str
    logger: logging.Logger
    stages: dict[str, float] = field(default_factory=dict)
    cpu_stages: dict[str, float] = field(default_factory=dict)

    def start(self, stage: str) -> tuple[float, float]:
        self.logger.info("RUNNER_STAGE_START deployment=%s stage=%s", self.deployment_id, stage)
        return time.perf_counter(), time.process_time()

    def stop(self, stage: str, marker: tuple[float, float], *, bars: int | None = None) -> None:
        wall = round(time.perf_counter() - marker[0], 3)
        cpu = round(time.process_time() - marker[1], 3)
        self.stages[stage] = wall
        self.cpu_stages[stage] = cpu
        args = (self.deployment_id, stage, wall, cpu, bars if bars is not None else -1)
        if wall >= 30:
            self.logger.warning("RUNNER_STAGE_DONE deployment=%s stage=%s wall_s=%.3f cpu_s=%.3f bars=%d", *args)
        else:
            self.logger.info("RUNNER_STAGE_DONE deployment=%s stage=%s wall_s=%.3f cpu_s=%.3f bars=%d", *args)

    def summary(self) -> None:
        self.logger.warning(
            "RUNNER_STAGE_SUMMARY deployment=%s wall_by_stage=%s cpu_by_stage=%s",
            self.deployment_id, self.stages, self.cpu_stages,
        )


def profile_generate(func, instance, logger: logging.Logger, deployment_id: str):
    """Explicit opt-in only: cProfile adds overhead and must not run by default."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        return func(instance)
    finally:
        profiler.disable()
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(20)
        logger.warning("RUNNER_CPROFILE deployment=%s\\n%s", deployment_id, stream.getvalue())
''')

once('import hashlib\n', 'import hashlib\nimport time\n', runner)
once('from .history_warmup_queue import enqueue_history_warmup\n', 'from .history_warmup_queue import enqueue_history_warmup\nfrom .runner_diagnostics import StageClock, profile_generate\nfrom ...core.config import settings\nfrom .runner_scheduler import parse_timeframe_to_seconds\n', runner)
once('    latency_trace = LiveLatencyTraceService(redis_manager.client if redis_manager.is_available else None)\n', '    latency_trace = LiveLatencyTraceService(redis_manager.client if redis_manager.is_available else None)\n    stage_clock = StageClock(str(deployment_id), logger)\n    runner_total_started = time.perf_counter()\n', runner)

# A transaction lock is still held: we DO NOT change lock lifetime until multi-process
# correctness and broker idempotency are integration-tested.
once('        strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()\n', '        timer = stage_clock.start("resolve_strategy_and_runtime")\n        strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()\n', runner)
once('        authoritative_candle_time = _normalize_dt(candle_time) if candle_time is not None else None\n', '        stage_clock.stop("resolve_strategy_and_runtime", timer)\n        timer = stage_clock.start("history_readiness_check")\n        authoritative_candle_time = _normalize_dt(candle_time) if candle_time is not None else None\n', runner)
once('        refresh_warning = None\n', '        stage_clock.stop("history_readiness_check", timer)\n        refresh_warning = None\n', runner)
once('        candles = await load_live_candles_for_runner(\n            db,\n            deployment,\n            limit=profile.required_history_bars,\n            through_candle_time=authoritative_candle_time,\n        )\n', '        timer = stage_clock.start("load_closed_candles")\n        candles = await load_live_candles_for_runner(\n            db,\n            deployment,\n            limit=profile.required_history_bars,\n            through_candle_time=authoritative_candle_time,\n        )\n        stage_clock.stop("load_closed_candles", timer, bars=len(candles))\n', runner)
once('        df = _candles_to_dataframe(candles)\n        delay_seconds = 1\n', '        timer = stage_clock.start("build_dataframe")\n        df = _candles_to_dataframe(candles)\n        stage_clock.stop("build_dataframe", timer, bars=len(df))\n        delay_seconds = 1\n', runner)
once('        strategy_instance = strategy_class(df, **params)\n        generated = _run_strategy_generate(strategy_instance)\n', '''        timer = stage_clock.start("strategy_class_init")
        strategy_instance = strategy_class(df, **params)
        stage_clock.stop("strategy_class_init", timer, bars=len(df))
        timer = stage_clock.start("strategy_generate")
        # Optional sampling profiler. Disabled by default because it adds overhead.
        if bool(getattr(settings, "live_strategy_cprofile_enabled", False)):
            generated = profile_generate(_run_strategy_generate, strategy_instance, logger, str(deployment_id))
        else:
            generated = _run_strategy_generate(strategy_instance)
        stage_clock.stop("strategy_generate", timer, bars=len(df))
        stage_clock.summary()
        logger.warning("RUNNER_GENERATE_COMPLETE deployment=%s candle_open=%s total_wall_s=%.3f",
                       deployment_id, latest_candle_time.isoformat(), time.perf_counter() - runner_total_started)
''', runner)
once('        signal_payload = extract_latest_signal_payload(generated)\n', '        timer = stage_clock.start("extract_latest_signal")\n        signal_payload = extract_latest_signal_payload(generated)\n        stage_clock.stop("extract_latest_signal", timer)\n', runner)

# Optional trade freshness safety guard: preserve existing behavior unless opted in.
# Bar timestamps represent OPEN, so stale cutoff = candle_time + timeframe + max_age_after_close.
# This guard returns a transparent skipped result, never sends a stale broker order.
anchor='''        # Do not persist HOLD noise into live_signals. HOLD is a heartbeat/result,
'''
addition='''        if execute and bool(getattr(settings, "live_runner_stale_order_guard_enabled", False)):
            candle_closes_at = latest_candle_time + __import__("datetime").timedelta(
                seconds=parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))
            )
            max_stale_age = max(0, int(getattr(settings, "live_runner_max_order_age_after_close_seconds", 60)))
            age = (datetime.now(timezone.utc) - candle_closes_at).total_seconds()
            if age > max_stale_age:
                deployment.last_heartbeat_at = datetime.now(timezone.utc)
                _mark_candle_processed(deployment, latest_candle_time)
                await _log(db, deployment, "RUNNER_STALE_SIGNAL_BLOCKED",
                           "Stale candle evaluated; skipped live order to avoid executing a delayed signal",
                           "WARNING", {"signal_type": signal_type, "candle_time": latest_candle_time.isoformat(),
                                       "age_after_close_seconds": round(age, 3), "max_age_seconds": max_stale_age,
                                       "generate_seconds": stage_clock.stages.get("strategy_generate")})
                await db.commit()
                return StrategyRunnerResult(
                    success=True, deployment_id=str(deployment.id), strategy_name=canonical_name,
                    latest_candle_time=latest_candle_time.isoformat(), signal=signal_type,
                    executed=False, order_id=None, broker_order_id=None, signal_id=None,
                    duplicate=False, message="HOLD - stale candle; order blocked by configured guard",
                    latest_runner_log="Stale candle order blocked", symbol=latest_symbol,
                    final_action="HOLD_STALE_CANDLE",
                ).to_dict()

'''
once(anchor,addition+anchor,runner)

# Prevent unsuccessful runtime contract/history results from advancing cursor in scheduler.
once('''        # If another request (for example Run Strategy Once) owned the per-deployment
''','''        if not runner_result.get("success", False):
            deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
            return await _schedule_retry(
                db, deployment, utc_now(),
                "Strategy result unsuccessful (history/contract/other HOLD); candle NOT marked processed",
                result,
            )
        # If another request (for example Run Strategy Once) owned the per-deployment
''',scheduler)

# Log candle age, compute time, and processed cursor gap before launching strategy.
once('''        runner_result = await run_strategy_for_deployment(
''','''        logger.warning(
            "RUNNER_DISPATCH deployment=%s candle_open=%s last_processed_open=%s age_since_close_s=%.3f",
            deployment_id, latest_closed_candle_time.isoformat(),
            last_processed.isoformat() if last_processed else None,
            max(0.0, (utc_now() - (latest_closed_candle_time + timedelta(seconds=__import__(
                "app.services.live.runner_scheduler", fromlist=["parse_timeframe_to_seconds"]
            ).parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))))).total_seconds()),
        )
        dispatch_started = time.monotonic()
        runner_result = await run_strategy_for_deployment(
''',scheduler)
once('''        # If another request (for example Run Strategy Once) owned the per-deployment
''','''        logger.warning(
            "RUNNER_DISPATCH_FINISHED deployment=%s candle_open=%s elapsed_s=%.3f action=%s success=%s",
            deployment_id, latest_closed_candle_time.isoformat(),
            time.monotonic() - dispatch_started, runner_result.get("final_action"), runner_result.get("success"),
        )
        # If another request (for example Run Strategy Once) owned the per-deployment
''',scheduler)

once('''    live_strategy_history_default_bars: int = Field(default=80000, description="Default closed-candle history passed to live dynamic strategies")
''','''    live_strategy_cprofile_enabled: bool = Field(default=False, description="Opt-in strategy generate cProfile logging; adds CPU overhead")
    live_runner_stale_order_guard_enabled: bool = Field(default=False, description="Opt-in fail-closed broker-order guard for late candle evaluations")
    live_runner_max_order_age_after_close_seconds: int = Field(default=60, description="When stale guard enabled, max seconds from candle close to order decision")
    live_strategy_history_default_bars: int = Field(default=80000, description="Default closed-candle history passed to live dynamic strategies")
''',config)

print('Applied deterministic profiling, dispatch, opt-in stale-order safety, and cursor patches.')
