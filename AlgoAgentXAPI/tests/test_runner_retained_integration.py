"""Runner/cache wiring tests with isolated I/O, not strategy or execution parity.

The HOLD-only test strategy cannot submit orders. All DB, tracing and broker
boundaries are replaced; production strategy/source and configuration are untouched.
"""
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pandas as pd
import pytest

from app.services.live import strategy_runner as runner
from app.services.live.capital_service import get_effective_trading_capital
from app.services.live.retained_strategy_state import RetainedStateCache


class HoldOnlyContractStrategy:
    def __init__(self, frame, **params):
        self.frame = frame

    def generate(self):
        return self.frame.assign(Position=0)

    def start_live_incremental(self, generated):
        return True

    def on_closed_candle(self, candle):
        return pd.DataFrame([dict(candle, Position=0)])


@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(equity=Decimal('10000'), risk=.01, index=79999,
                            loads=[], runtime=None, adapter_id='v64_hybrid_v1', parameters={})
    dates = pd.date_range('2025-01-01', periods=80100, freq='5min', tz='UTC')
    deployment = SimpleNamespace(id=uuid4(), user_id=uuid4(), strategy_id=uuid4(),
        broker_account_id=uuid4(), mode='DEMO', status='RUNNING', capital=Decimal('10000'),
        instrument='XAUUSD.X', instrument_key='XAUUSD.X', broker_symbol='XAUUSD.X',
        timeframe='M5', last_processed_candle_time=None)
    strategy = SimpleNamespace(id=deployment.strategy_id, name='offline-contract', parameters=state.parameters)
    async def execute(statement):
        entity = statement.column_descriptions[0]['entity']
        value = deployment if entity is runner.StrategyDeployment else strategy
        return SimpleNamespace(scalar_one_or_none=lambda: value)
    db = SimpleNamespace(execute=AsyncMock(side_effect=execute), commit=AsyncMock(),
                         rollback=AsyncMock(), add=Mock())
    async def runtime(*args, **kwargs):
        broker = SimpleNamespace(metadata_json={'account_info': {'equity': str(state.equity)}})
        capital = get_effective_trading_capital(deployment, broker)
        state.runtime = {'risk': {'initial_capital': float(capital.effective_capital),
                                  'risk_percent': state.risk}}
        return state.runtime
    async def candles(*args, limit, through_candle_time):
        assert through_candle_time == dates[state.index]
        state.loads.append(limit)
        return [dict(candle_time=dates[i], open=100., high=101., low=99., close=100.,
                     volume=1., symbol='XAUUSD.X')
                for i in range(state.index, state.index-limit, -1)]
    monkeypatch.setattr(runner, 'settings', SimpleNamespace(live_incremental_enabled=True,
        live_incremental_adapter_enabled=True, live_incremental_monitor_only=True,
        live_incremental_max_advances=48))
    monkeypatch.setattr(runner, 'redis_manager', SimpleNamespace(is_available=False))
    monkeypatch.setattr(runner, 'LiveLatencyTraceService', lambda *args: SimpleNamespace(mark=AsyncMock()))
    monkeypatch.setattr(runner, '_log', AsyncMock())
    monkeypatch.setattr(runner, 'try_deployment_xact_lock', AsyncMock(return_value=True))
    monkeypatch.setattr(runner, '_validate_strategy_gate', Mock())
    monkeypatch.setattr(runner, 'resolve_strategy', lambda *args: (HoldOnlyContractStrategy, {}, strategy.name))
    monkeypatch.setattr(runner, 'resolve_live_strategy_profile', lambda *args: SimpleNamespace(required_history_bars=80000))
    monkeypatch.setattr(runner, 'runtime_contract_violations', lambda *args: [])
    monkeypatch.setattr(runner, 'resolve_live_runtime_config', runtime)
    monkeypatch.setattr(runner, 'select_registered_adapter', lambda **kwargs: SimpleNamespace(
        strategy_class=HoldOnlyContractStrategy, reason='test-contract', monitor_only=True,
        adapter_id=state.adapter_id, source_sha256='offline-test-only'))
    monkeypatch.setattr(runner, 'history_ready_cache', SimpleNamespace(
        can_reuse=lambda *args, **kwargs: True, invalidate=Mock()))
    monkeypatch.setattr(runner, 'load_live_candles_for_runner', candles)
    monkeypatch.setattr(runner, 'retained_states', RetainedStateCache())
    order = AsyncMock(side_effect=AssertionError('Order execution forbidden in this test'))
    monkeypatch.setattr(runner, 'execute_signal', order)
    async def cycle():
        state.loads.clear()
        result = await runner.run_strategy_for_deployment(db, deployment.id, execute=True,
            refresh_broker_candles=False, candle_time=dates[state.index])
        assert result['success'] and result['final_action'] == 'HOLD_IGNORED', result
        assert deployment.last_processed_candle_time == dates[state.index]
        assert state.runtime['risk']['initial_capital'] == float(state.equity)
        order.assert_not_awaited()
        return list(state.loads)
    return state, deployment, cycle


def test_equity_churn_stop_start_and_48_advances(harness):
    state, deployment, cycle = harness
    async def scenario():
        assert await cycle() == [2, 80000]
        for step in range(1, 49):
            if step == 3:
                # Mimics scheduler exclusion while stopped: no runner invocation.
                deployment.status = 'STOPPED'
                cursor = deployment.last_processed_candle_time
                deployment.status = 'RUNNING'
                assert deployment.last_processed_candle_time == cursor
            state.index += 1
            state.equity += Decimal('7.25')
            assert await cycle() == [2]
        state.index += 1
        assert await cycle() == [2, 80000]
    asyncio.run(scenario())


@pytest.mark.parametrize('change', ['risk', 'capital', 'account', 'symbol', 'parameters', 'gap', 'restart', 'cursor'])
def test_real_identity_or_continuity_changes_cold_start(harness, monkeypatch, change):
    state, deployment, cycle = harness
    async def scenario():
        assert await cycle() == [2, 80000]
        state.index += 1
        if change == 'risk': state.risk = .02
        if change == 'capital': deployment.capital += 100
        if change == 'account': deployment.broker_account_id = uuid4()
        if change == 'symbol': deployment.broker_symbol = 'changed-routing'
        if change == 'parameters': state.parameters['changed'] = True
        if change == 'gap': state.index += 1
        if change == 'restart': monkeypatch.setattr(runner, 'retained_states', RetainedStateCache())
        if change == 'cursor': deployment.last_processed_candle_time = None
        assert await cycle() == [2, 80000]
    asyncio.run(scenario())


def test_unknown_adapter_keeps_equity_sensitive_identity(harness):
    state, deployment, cycle = harness
    state.adapter_id = 'unknown_adapter'
    async def scenario():
        assert await cycle() == [2, 80000]
        state.equity += 10
        state.index += 1
        assert await cycle() == [2, 80000]
    asyncio.run(scenario())