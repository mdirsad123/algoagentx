"""Wall time and CPU-time breakdown for long-running live strategy runs.

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
        logger.warning("RUNNER_CPROFILE deployment=%s\n%s", deployment_id, stream.getvalue())
