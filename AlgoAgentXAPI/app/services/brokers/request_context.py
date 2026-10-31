"""Task-local order deadline, shared by broker adapters without sharing clients."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time


@dataclass
class OrderRequestContext:
    deadline: float
    signal_id: str
    account_id: str
    primary_completed_at: float
    metrics: dict = field(default_factory=dict)

    def check(self):
        if time.time() >= self.deadline:
            raise TimeoutError('Fresh signal execution deadline expired; no catch-up order permitted')

    def mark_submission(self):
        self.check()
        verified = self.metrics.get('risk_verified_at_epoch')
        if verified is not None and time.time() - verified > 10:
            raise TimeoutError('Account risk snapshot aged during submission wait; new entry blocked')
        now = time.time()
        self.metrics.update(submitted_at=datetime.now(timezone.utc).isoformat(),
                            primary_to_submission_ms=round((now - self.primary_completed_at) * 1000, 3))


order_request_context: ContextVar[OrderRequestContext | None] = ContextVar('order_request_context', default=None)


def check_order_deadline():
    context = order_request_context.get()
    if context is not None:
        context.check()


def mark_order_submission():
    context = order_request_context.get()
    if context is not None:
        context.mark_submission()