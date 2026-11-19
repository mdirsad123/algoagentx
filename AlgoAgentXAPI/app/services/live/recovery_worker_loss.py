"""No-order diagnostics for lost market-gap recovery workers."""
from __future__ import annotations

from pathlib import Path


def worker_loss_reason(exception_text: str) -> str:
    """Classify a lost Celery worker without assuming the host was OOM."""
    message = str(exception_text).lower()
    return ('WORKER_LOST_SIGKILL' if 'sigkill' in message or 'signal 9' in message
            else 'WORKER_LOST')


def worker_loss_cgroup_memory_events() -> str:
    """Read-only cgroup memory evidence; absence cannot rule out OOM."""
    for path in ('/sys/fs/cgroup/memory.events',
                 '/sys/fs/cgroup/memory/memory.oom_control'):
        try:
            result = Path(path).read_text(encoding='utf-8').strip()
            if result:
                return ' '.join(result.split())[:300]
        except OSError:
            pass
    return 'unavailable'
