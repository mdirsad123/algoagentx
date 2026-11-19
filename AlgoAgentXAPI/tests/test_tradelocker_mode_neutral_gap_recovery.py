"""Mode-neutral TradeLocker session recovery gate regressions (no brokers/network)."""
from __future__ import annotations

import ast
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'app' / 'services' / 'live'


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('mode,expected', [('DEMO', True), ('LIVE', True), ('PAPER', False)])
def test_observed_gap_policy_identical_across_real_broker_modes(mode, expected):
    policy = _load('test_gap_resume_policy', LIVE / 'gap_resume_policy.py')
    assert policy.eligible_for_demo_cold_reseed(
        mode=mode, enabled=True, timeframe_seconds=300,
        missing_slots=4, min_missing_slots=2, attempts=3,
        successful_refetches=2, broker_source_verified=True,
        last_two_broker_bars_consecutive=True,
    ) is expected


@pytest.mark.parametrize('mode', ['DEMO', 'LIVE'])
def test_observed_gap_requires_broker_evidence(mode):
    policy = _load('test_gap_resume_policy', LIVE / 'gap_resume_policy.py')
    assert not policy.eligible_for_demo_cold_reseed(
        mode=mode, enabled=True, timeframe_seconds=300,
        missing_slots=4, min_missing_slots=2, attempts=3,
        successful_refetches=2, broker_source_verified=False,
        last_two_broker_bars_consecutive=True,
    )


@pytest.mark.parametrize('mode,expected', [('DEMO', True), ('LIVE', True), ('PAPER', False)])
def test_exact_source_nas100_recovery_capability_mode_independent(monkeypatch, mode, expected):
    # Approval logic imports the frozen-source checker at call time. Supply an
    # exact-source stub to test the policy without executing 80K-bar strategy code.
    strategies = ModuleType('strategies')
    strategies.__path__ = []
    nas = ModuleType('strategies.nas100_v48_incremental')
    nas.source_matches_frozen = lambda source: source == 'exact-source'
    monkeypatch.setitem(sys.modules, 'strategies', strategies)
    monkeypatch.setitem(sys.modules, 'strategies.nas100_v48_incremental', nas)
    cap = _load('test_gap_reseed_capability', LIVE / 'gap_reseed_capability.py')
    chosen = SimpleNamespace(adapter_id='nas100_v48_native_v1', strategy_class=object)
    assert cap.approved_for_gap_reseed(selection=chosen, source_code='exact-source',
        mode=mode, suppressed=True, enabled=True) is expected
    assert not cap.approved_for_gap_reseed(selection=chosen, source_code='changed',
        mode=mode, suppressed=True, enabled=True)
    assert not cap.approved_for_gap_reseed(selection=chosen, source_code='exact-source',
        mode=mode, suppressed=False, enabled=True)


def test_v932_source_pin_required_for_both_broker_modes(monkeypatch):
    # Stub only imports; preserve the exact-source SHA and class identity logic.
    strategies = ModuleType('strategies')
    strategies.__path__ = []
    gold = ModuleType('strategies.v932_incremental')
    gold.Strategy = type('Strategy', (), {})
    monkeypatch.setitem(sys.modules, 'strategies', strategies)
    monkeypatch.setitem(sys.modules, 'strategies.v932_incremental', gold)

    app = ModuleType('app'); app.__path__ = []
    services = ModuleType('app.services'); services.__path__ = []
    pkg = ModuleType('app.services.live'); pkg.__path__ = []
    pin = ModuleType('app.services.live.v932_hybrid_gate')
    pin.V932_NORMALIZED_SHA256 = sha256(b'gold-source').hexdigest()
    for name, obj in [('app', app), ('app.services', services), ('app.services.live', pkg),
                      ('app.services.live.v932_hybrid_gate', pin)]:
        monkeypatch.setitem(sys.modules, name, obj)
    cap = _load('app.services.live.test_gold_gap_reseed_capability', LIVE / 'gap_reseed_capability.py')
    chosen = SimpleNamespace(adapter_id='v932_hybrid_v1', strategy_class=gold.Strategy)
    for mode in ('DEMO', 'LIVE'):
        assert cap.approved_for_gap_reseed(selection=chosen, source_code='gold-source',
            mode=mode, suppressed=True, enabled=True)
        assert not cap.approved_for_gap_reseed(selection=chosen, source_code='wrong',
            mode=mode, suppressed=True, enabled=True)
        assert not cap.approved_for_gap_reseed(selection=chosen, source_code='gold-source',
            mode=mode, suppressed=True, enabled=False)


def test_source_pin_adapter_required_matches_demo_and_live():
    path = LIVE / 'incremental_adapter_registry.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'adapter_required_for_instrument')
    code = compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec')
    names = {}
    exec(code, names)
    required = names['adapter_required_for_instrument']
    settings = SimpleNamespace(live_incremental_require_adapter_instruments='NAS100,XAUUSD')
    for mode in ('DEMO', 'LIVE'):
        assert required(settings, mode=mode, instrument='NAS100.X')
        assert required(settings, mode=mode, instrument='XAUUSD.X')
    assert not required(settings, mode='PAPER', instrument='NAS100.X')
    assert not required(settings, mode='LIVE', instrument='GBPUSD.X')


def test_runtime_recovery_and_celery_accept_real_broker_modes():
    # Static integration guard for two entry points; no broker or DB side effects.
    task = (ROOT / 'app/tasks.py').read_text()
    runner = (LIVE / 'auto_runner_service.py').read_text()
    strategy = (LIVE / 'strategy_runner.py').read_text()
    assert "str(deployment.mode or '').upper() not in {'DEMO', 'LIVE'}" in task
    assert "if (not force and str(deployment.mode or '').upper() in {'DEMO', 'LIVE'}" in runner
    assert "str(deployment.mode or '').upper() in {'DEMO', 'LIVE'}" in strategy
    assert 'suppress_broker_order_for_catchup=True' in task
    assert 'recovery_cursor_valid' in task
    assert 'broker_calendar_result=CLOSED' in runner


def test_essential_execution_guards_remain():
    strategy = (LIVE / 'strategy_runner.py').read_text()
    cap = (LIVE / 'gap_reseed_capability.py').read_text()
    assert 'HOLD_CANDLE_GAP' in strategy
    assert 'HOLD_RECOVERY_EVIDENCE_MISMATCH' in strategy
    assert 'not suppressed' in cap
    assert 'source_matches_frozen' in cap
    assert 'v932_demo_forward_test_orders_permitted' in strategy
