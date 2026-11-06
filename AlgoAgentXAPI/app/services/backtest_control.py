"""Cooperative execution control. No database access from the compute engine."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Event, Lock
from time import perf_counter


class BacktestInterrupted(RuntimeError):
    pass


@dataclass
class ExecutionControl:
    stopped: Event = field(default_factory=Event)
    mutex: Lock = field(default_factory=Lock)
    stage: str = "initializing"
    processed: int = 0
    total: int = 0
    started: float = field(default_factory=perf_counter)
    stage_started: float = field(default_factory=perf_counter)
    timings: dict = field(default_factory=dict)
    reason: str = "Execution ownership lost"

    def checkpoint(self, stage=None, processed=None, total=None):
        if self.stopped.is_set():
            raise BacktestInterrupted(self.reason)
        with self.mutex:
            now = perf_counter()
            if stage is not None and stage != self.stage:
                self.timings[self.stage] = self.timings.get(self.stage, 0) + now - self.stage_started
                self.stage_started = now
                self.stage = stage
            if processed is not None:
                self.processed = processed
            if total is not None:
                self.total = total

    def snapshot(self):
        with self.mutex:
            now = perf_counter()
            timings = dict(self.timings)
            timings[self.stage] = timings.get(self.stage, 0) + now - self.stage_started
            return {"stage": self.stage, "processed": self.processed, "total": self.total,
                    "elapsed_seconds": now - self.started, "stage_seconds": timings}


current_control = ContextVar("backtest_execution_control", default=None)


def checkpoint(stage=None, processed=None, total=None):
    control = current_control.get()
    if control is not None:
        control.checkpoint(stage, processed, total)