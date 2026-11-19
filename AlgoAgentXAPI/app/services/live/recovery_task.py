"""Recovery-only Celery parent hook for hard timeouts (not task_failure)."""
from celery import Task
from celery.worker.request import Request
from billiard.exceptions import TimeLimitExceeded


class RecoveryRequest(Request):
    def on_timeout(self, soft, timeout):
        try:
            super().on_timeout(soft, timeout)
        finally:
            if not soft:
                from ...tasks import _hold_lost_verified_gap_reseed
                _hold_lost_verified_gap_reseed(sender=self.task, task_id=self.id,
                    exception=TimeLimitExceeded(timeout), args=self.args)


class RecoveryTask(Task):
    Request = 'app.services.live.recovery_task:RecoveryRequest'