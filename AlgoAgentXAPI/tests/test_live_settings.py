"""Settings saves are configuration operations, never strategy evaluations."""
import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1 import live_deployments as routes
from app.schemas.live_trading import StrategyDeploymentUpdate
from app.services.live import settings_validation as validation
from app.services.live import dry_test_jobs as jobs


def setup_route(monkeypatch, state='STOPPED', **overrides):
    row = SimpleNamespace(id=uuid4(), user_id=uuid4(), status=state, mode='DEMO',
        name='Original', strategy_id='existing', broker_account_id=uuid4(),
        instrument='BTCUSD', timeframe='M5', account_policy_type='STANDARD',
        auto_trade_enabled=True, copy_trading_enabled=False, copy_broker_account_ids=[],
        risk_per_trade=Decimal('.01'), rr_ratio=Decimal('2'), price_risk_pct=Decimal('.002'),
        max_daily_loss=None, max_trades_per_day=None, max_open_positions=1, mt5_demo_max_lot=None)
    row.__dict__.update(overrides)
    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock(), add=Mock())
    monkeypatch.setattr(routes, 'get_deployment_or_404', AsyncMock(return_value=row))
    monkeypatch.setattr(routes, 'dump_one', lambda _, value: {'name': value.name, 'status': value.status})
    for name in ('run_live_compatibility_check', '_resolve_and_validate_broker_mapping', '_validate_broker_for_user', 'get_deployable_strategy_or_400'):
        monkeypatch.setattr(routes, name, AsyncMock(side_effect=AssertionError(f'{name} is not a normal save dependency')))
    return row, db


@pytest.mark.parametrize('state', ['RUNNING', 'PAUSED', 'STOPPED'])
def test_normal_save_never_evaluates_strategy(monkeypatch, state):
    row, db = setup_route(monkeypatch, state)
    payload = StrategyDeploymentUpdate(name='Renamed', mode='DEMO', instrument='BTCUSD',
        broker_account_id=row.broker_account_id, auto_trade_enabled=True, risk_per_trade='.01', max_daily_loss=100)
    asyncio.run(routes.update_deployment(row.id, payload, db, {'user_id': str(row.user_id)}))
    assert row.name == 'Renamed' and row.max_daily_loss == 100 and row.status == state
    db.commit.assert_awaited_once()


@pytest.mark.parametrize('state', ['RUNNING', 'PAUSED', 'STOPPED'])
def test_copy_targets_save_without_readiness(monkeypatch, state):
    row, db = setup_route(monkeypatch, state)
    target = uuid4()
    monkeypatch.setattr(routes, 'get_broker_account_or_404', AsyncMock(return_value=SimpleNamespace(mode='DEMO', status='CONNECTED')))
    asyncio.run(routes.update_deployment(row.id, StrategyDeploymentUpdate(copy_trading_enabled=True,
        copy_broker_account_ids=[target, target, row.broker_account_id]), db, {}))
    assert row.copy_trading_enabled and row.copy_broker_account_ids == [str(target)]
    assert row.status == state


def test_enabling_copy_validates_existing_targets(monkeypatch):
    row, db = setup_route(monkeypatch)
    monkeypatch.setattr(routes, 'get_broker_account_or_404', AsyncMock(return_value=SimpleNamespace(mode='DEMO', status='CONNECTED')))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.update_deployment(row.id, StrategyDeploymentUpdate(copy_trading_enabled=True), db, {}))
    assert 'at least one' in exc.value.detail
    db.commit.assert_not_awaited()


@pytest.mark.parametrize('target_mode,target_status', [('LIVE','CONNECTED'), ('DEMO','DISCONNECTED')])
def test_copy_validation_preserved(monkeypatch, target_mode, target_status):
    row, db = setup_route(monkeypatch)
    monkeypatch.setattr(routes, 'get_broker_account_or_404', AsyncMock(side_effect=[
        SimpleNamespace(mode='DEMO', status='CONNECTED'), SimpleNamespace(mode=target_mode, status=target_status)]))
    with pytest.raises(HTTPException):
        asyncio.run(routes.update_deployment(row.id, StrategyDeploymentUpdate(copy_broker_account_ids=[uuid4()]), db, {}))
    db.commit.assert_not_awaited()


def test_structural_running_guard_preserved(monkeypatch):
    row, db = setup_route(monkeypatch, 'RUNNING')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.update_deployment(row.id, StrategyDeploymentUpdate(timeframe='M15'), db, {}))
    assert 'Stop' in exc.value.detail


def test_enabling_auto_trade_needs_evidence_not_sync_compute(monkeypatch):
    row, db = setup_route(monkeypatch, auto_trade_enabled=False)
    gate = AsyncMock(side_effect=HTTPException(409, 'Run Check separately'))
    monkeypatch.setattr(routes, 'require_compatibility_evidence', gate)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.update_deployment(row.id, StrategyDeploymentUpdate(auto_trade_enabled=True), db, {}))
    assert exc.value.status_code == 409
    routes.run_live_compatibility_check.assert_not_awaited()
    db.commit.assert_not_awaited()


def test_unchanged_values_are_removed():
    account = uuid4()
    row = SimpleNamespace(risk=Decimal('.010000'), account=account, ids=[str(account)], cap=None)
    assert validation.changed_settings(row, {'risk': Decimal('.01'), 'account': account, 'ids': [account], 'cap': None}) == {}
    assert validation.changed_settings(row, {'cap': 3}) == {'cap': 3}


@pytest.mark.parametrize('evidence', [None, 'invalid', '[]', 'null', '{}', '{"fingerprint":"old","status":"PASS"}', '{"fingerprint":"current","status":"FAIL"}'])
def test_evidence_fails_closed(monkeypatch, evidence):
    monkeypatch.setattr(validation, 'configuration_fingerprint', AsyncMock(return_value='current'))
    monkeypatch.setattr(validation, 'redis_manager', SimpleNamespace(client=SimpleNamespace(get=AsyncMock(return_value=evidence))))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(validation.require_compatibility_evidence(None, SimpleNamespace(id=uuid4()), {}))
    assert exc.value.status_code == 409


def test_evidence_accepts_matching_recent_result(monkeypatch):
    monkeypatch.setattr(validation, 'configuration_fingerprint', AsyncMock(return_value='current'))
    monkeypatch.setattr(validation, 'redis_manager', SimpleNamespace(client=SimpleNamespace(get=AsyncMock(return_value=json.dumps({'fingerprint':'current','status':'PASS'})))))
    asyncio.run(validation.require_compatibility_evidence(None, SimpleNamespace(id=uuid4()), {}))


def test_compatibility_endpoint_queues_after_authorization(monkeypatch):
    auth, enqueue = AsyncMock(), AsyncMock(return_value={'job_id':'job','status':'PENDING'})
    monkeypatch.setattr(routes, 'get_deployment_or_404', auth)
    monkeypatch.setattr(routes, 'enqueue_dry_test', enqueue)
    monkeypatch.setattr(routes, 'run_live_compatibility_check', AsyncMock(side_effect=AssertionError('No synchronous strategy')))
    deployment = uuid4()
    asyncio.run(routes.check_deployment_live_compatibility(deployment, None, {}))
    auth.assert_awaited_once()
    enqueue.assert_awaited_once_with(str(deployment), kind='compatibility')


def test_unauthorized_job_never_reads_results(monkeypatch):
    monkeypatch.setattr(routes, 'get_deployment_or_404', AsyncMock(side_effect=HTTPException(404)))
    status = AsyncMock()
    monkeypatch.setattr(routes, 'dry_test_status', status)
    with pytest.raises(HTTPException):
        asyncio.run(routes.get_deployment_compatibility_job(uuid4(), uuid4(), None, {}))
    status.assert_not_awaited()


def test_compatibility_queue_deduplicates(monkeypatch):
    client = SimpleNamespace(set=AsyncMock(return_value=False), get=AsyncMock(return_value='existing'))
    monkeypatch.setattr(jobs, 'redis_manager', SimpleNamespace(client=client))
    send = Mock()
    monkeypatch.setattr(jobs.celery_app, 'send_task', send)
    result = asyncio.run(jobs.enqueue('deployment', kind='compatibility'))
    assert result['job_id'] == 'existing' and result['deduplicated']
    send.assert_not_called()


def test_fingerprint_canonical_and_sensitive_to_runtime(monkeypatch):
    strategy = SimpleNamespace(name='Saved strategy', parameters={'source_code': 'v1'},
                               default_runtime_config={'risk': {}}, config_version=1)
    preset = SimpleNamespace(config_json={'sl_tp': {'sl_mode': 'ATR'}})
    db = SimpleNamespace(execute=AsyncMock(side_effect=lambda *args: SimpleNamespace(
        scalar_one_or_none=lambda: strategy if 'strategies' in str(args[0]) else preset)))
    row = SimpleNamespace(id=uuid4(), strategy_id='existing', risk_per_trade=Decimal('.010000'))
    monkeypatch.setattr(validation, 'bundled_strategy_digest', lambda: 'image-v1')
    baseline = asyncio.run(validation.configuration_fingerprint(db, row))
    assert baseline == asyncio.run(validation.configuration_fingerprint(db, row, {'risk_per_trade': Decimal('.01')}))
    assert baseline == asyncio.run(validation.configuration_fingerprint(db, row, {'name': 'New name'}))
    assert baseline != asyncio.run(validation.configuration_fingerprint(db, row, {'risk_per_trade': Decimal('.02')}))
    strategy.parameters['source_code'] = 'v2'
    assert baseline != asyncio.run(validation.configuration_fingerprint(db, row))


def test_bundled_strategy_digest_reads_actual_sources():
    assert len(validation.bundled_strategy_digest()) == 64