"""Read-only local Docker diagnostics. Never sends requests to a broker.

Run from the repository with Python; only sanitized grouping/counts are printed.
"""
import collections
import re
import subprocess


def main():
    for service in ('api', 'live_reconcile_worker', 'live_strategy_worker',
                    'live_legacy_runner_worker', 'live_position_manager_worker',
                    'live_tradelocker_candle_worker', 'live_history_worker', 'alert_worker'):
        result = subprocess.run(['docker', 'logs', '--since', '12h', '--tail', '30000',
                                 'algoagentx_' + service], capture_output=True, text=True,
                                encoding='utf-8', errors='replace')
        counts = collections.Counter()
        for line in (result.stdout + result.stderr).splitlines():
            match = re.search(r'TRADELOCKER_REQUEST account=(\S+) method=(\S+) path=(\S+) status=(\d+)', line)
            if match:
                counts[match.groups()] += 1
        print(service, dict(counts))
    code = '''
import asyncio, hashlib, json
from sqlalchemy import select, text
from app.db.session import async_session
from app.db.models import BrokerAccount
from app.utils.credential_crypto import decrypt_credential
async def main():
    async with async_session() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        rows = (await db.execute(select(BrokerAccount.id, BrokerAccount.broker_code,
            BrokerAccount.status, BrokerAccount.login_id, BrokerAccount.server_name,
            BrokerAccount.encrypted_password, BrokerAccount.metadata_json).where(
            BrokerAccount.broker_code == 'TRADELOCKER'))).all()
        for row in rows:
            meta = row.metadata_json or {}
            identity = '\\0'.join((str(meta.get('tradelocker_environment')), str(row.login_id),
                str(row.server_name), decrypt_credential(row.encrypted_password) or ''))
            print(json.dumps({'account':str(row.id), 'status':row.status,
                'credential_group':hashlib.sha256(identity.encode()).hexdigest()[:12],
                'selected_account':meta.get('tradelocker_account_id')}))
        await db.rollback()
asyncio.run(main())
'''
    result = subprocess.run(['docker', 'exec', '-i', 'algoagentx_api', 'python', '-'],
                            input=code, capture_output=True, text=True)
    if result.returncode:
        print('Read-only credential grouping failed (details withheld to protect configuration).')
    else:
        print(result.stdout)


if __name__ == '__main__':
    main()