"""Execute the REAL V6 endpoint functions with a fake DB/task queue.

Offline runner intentionally has no Celery/python-jose/asyncpg. Only optional
infrastructure imports are stubbed; route implementations and publishing logic
are real. This catches the missing imports that V5's string-only tests missed.
"""
import os
import subprocess
import sys
from pathlib import Path


def test_actual_api_publish_endpoints_execute_offline():
    source = r'''
import sys,types,asyncio
from unittest.mock import AsyncMock,Mock
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime,timezone
fake=types.ModuleType('app.core.dependencies')
def get_admin_user():return {'user_id':'test'}
def get_db():return None
fake.get_admin_user=get_admin_user;fake.get_db=get_db
sys.modules['app.core.dependencies']=fake
fake=types.ModuleType('app.services.market_data.daily_tasks')
fake.process_market_history=SimpleNamespace(apply_async=Mock())
fake.process_market_canonical_publish=SimpleNamespace(apply_async=Mock())
sys.modules['app.services.market_data.daily_tasks']=fake
from app.api.v1 import admin_market_data_sync as api
feed=SimpleNamespace(id=uuid4(),instrument_id=7,timeframe='5m',is_archived=False,is_primary=True,publish_approved=False)
db=AsyncMock();db.get.return_value=feed
now=datetime(2026,10,31,tzinfo=timezone.utc)
db.execute.side_effect=[None,SimpleNamespace(one=lambda:(100,80,20,1,now,now))]
r=asyncio.run(api.publish_preview(feed.id,db=db))
assert r['data']['missing_rows']==20
DB2=AsyncMock();DB2.add=Mock(side_effect=lambda run:setattr(run,'id',uuid4()))
DB2.execute.side_effect=[SimpleNamespace(scalar_one_or_none=lambda:feed),SimpleNamespace(scalar_one=lambda:100)]
r=asyncio.run(api.publish_missing(feed.id,api.PublishMissingRequest(confirm_insert_missing_only=True),db=DB2))
assert r['data']['status']=='QUEUED' and r['data']['publish_approved']
assert fake.process_market_canonical_publish.apply_async.call_count==1
assert DB2.commit.await_count==1
print('PUBLISH_ENDPOINTS_OK')
'''
    cwd = Path(__file__).parents[1]
    env = dict(os.environ, PYTHONPATH=str(cwd))
    result = subprocess.run([sys.executable, '-c', source], cwd=cwd, env=env,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, f'{result.stdout}\n{result.stderr}'
    assert 'PUBLISH_ENDPOINTS_OK' in result.stdout
