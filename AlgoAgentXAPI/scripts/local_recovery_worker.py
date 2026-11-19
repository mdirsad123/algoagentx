"""Order-isolated local Celery worker. Never use as a production runner.

Allow broker GETs and token authentication only; deny order transports and
high-level execution before they can submit or queue a broker request.
"""
import json
import os
from urllib.parse import urlsplit

import httpx

AUDIT = '/tmp/recovery-order-guard.jsonl'


def install_guard():
    original = httpx.AsyncClient.send

    async def guarded(self, request, *args, **kwargs):
        url = request.url
        allowed = (url.host in {'demo.tradelocker.com', 'live.tradelocker.com'} and
                   (request.method in {'GET', 'HEAD'} or
                    (request.method == 'POST' and str(url.path).startswith('/backend-api/auth/'))))
        with open(AUDIT, 'a') as out:
            out.write(json.dumps({'method': request.method, 'path': url.path,
                                  'allowed': allowed, 'pid': os.getpid()}) + '\n')
        if not allowed:
            raise RuntimeError('LOCAL_RECOVERY_NETWORK_WRITE_BLOCKED')
        return await original(self, request, *args, **kwargs)

    httpx.AsyncClient.send = guarded
    import app.services.live.execution_engine as execution
    import app.services.live.strategy_runner as runner

    async def forbidden(*args, **kwargs):
        with open(AUDIT, 'a') as out:
            out.write(json.dumps({'execution_attempt': True, 'allowed': False}) + '\n')
        raise RuntimeError('LOCAL_RECOVERY_EXECUTION_BLOCKED')

    execution.execute_signal = forbidden
    runner.execute_signal = forbidden
    from app.services.brokers.tradelocker import TradeLockerAdapter
    for name in ('place_order', 'close_position', 'cancel_order', 'modify_position'):
        if hasattr(TradeLockerAdapter, name):
            setattr(TradeLockerAdapter, name, forbidden)


def main():
    from app.core.config import settings
    assert urlsplit(settings.database_url).hostname == 'postgres_prod'
    assert urlsplit(settings.redis_url).hostname == 'redis'
    install_guard()
    from app.celery_app import celery_app
    celery_app.worker_main(['worker', '--loglevel=info', '--concurrency=1',
                           '--prefetch-multiplier=1', '--without-gossip', '--without-mingle',
                           '-Q', 'local_verified_recovery', '-n', 'local_recovery@%h'])


if __name__ == '__main__':
    main()