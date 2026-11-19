"""Test-only real prefork fault injection; never accesses broker or database."""
import asyncio
import os
import signal

assert os.environ.get('RECOVERY_FAULT_TEST') == '1'
assert os.environ.get('REDIS_URL', '').endswith('/15')
from app import tasks


async def fault(deployment_id, missing_iso, target_iso):
    assert deployment_id.startswith('test-recovery-')
    if target_iso == 'crash':
        os.kill(os.getpid(), signal.SIGKILL)
    if target_iso == 'timeout':
        await asyncio.sleep(30)
    return {'success': True, 'recovery_cursor_valid': True, 'final_action': 'RECOVERY_VALIDATED'}


tasks._verified_gap_reseed_async = fault
tasks.verified_gap_reseed_task.time_limit = 2
tasks.verified_gap_reseed_task.soft_time_limit = None
tasks.celery_app.worker_main(['worker', '--loglevel=info', '--concurrency=1',
    '--without-gossip', '--without-mingle', '-Q', os.environ['RECOVERY_FAULT_QUEUE'],
    '-n', 'fault_recovery@%h'])