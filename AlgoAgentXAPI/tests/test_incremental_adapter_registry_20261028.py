"""Registry semantics, source pinning and safe fallback; offline only."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from app.services.live.incremental_adapter_registry import (
    configured_max_advances, select_registered_adapter, source_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / 'production_patch/v64/V64_BASELINE_RESEARCH_ONLY.py').read_text(encoding='utf-8')
SHA = sha256(SRC.encode()).hexdigest()


def cfg(**kwargs):
    return SimpleNamespace(live_incremental_enabled=kwargs.get('global_enabled', True),
        live_incremental_adapter_enabled=kwargs.get('enabled', True),
        live_incremental_monitor_only=kwargs.get('monitor', True),
        live_incremental_parity_approved=kwargs.get('approved', False),
        live_incremental_authorized_source_sha256=kwargs.get('sha', SHA),
        live_incremental_max_advances=kwargs.get('advances', 48),
        live_v64_hybrid_enabled=False)


def select(src=SRC, settings=None, **kwargs):
    return select_registered_adapter(settings=settings or cfg(), source_code=src,
        mode=kwargs.get('mode', 'DEMO'), instrument=kwargs.get('instrument', 'XAUUSD.X'),
        timeframe_seconds=kwargs.get('tf', 300), required_history_bars=kwargs.get('bars', 80000))


def test_sha_identifies_not_converts():
    assert source_sha256(SRC) == SHA
    result = select(SRC + '\n# new strategy code')
    assert result.strategy_class is None
    assert result.reason == 'db_source_sha_not_frozen_reference'


def test_generic_frozen_v64_monitor_selection():
    result = select()
    assert result.adapter_id == 'v64_hybrid_v1'
    assert result.monitor_only
    assert result.strategy_class.LIVE_INCREMENTAL_VERSION == 1


def test_demos_order_mode_requires_operator_approval():
    result = select(settings=cfg(monitor=False, approved=False))
    assert result.strategy_class is None
    assert result.reason == 'parity_not_approved'
    approved = select(settings=cfg(monitor=False, approved=True))
    assert approved.strategy_class is not None
    assert not approved.monitor_only


def test_wrong_authorized_sha_blocks_even_when_approved():
    result = select(settings=cfg(monitor=False, approved=True, sha='0'*64))
    assert result.strategy_class is None
    assert result.reason == 'authorized_source_sha_missing_or_mismatch'


def test_runtime_contract_blocks_wrong_instrument_window_and_live():
    assert select(mode='LIVE').strategy_class is None
    assert select(instrument='EURUSD').strategy_class is None
    assert select(bars=5000).strategy_class is None
    assert select(tf=60).strategy_class is None


def test_disabled_global_or_registry_fails_closed():
    assert select(settings=cfg(enabled=False)).reason == 'disabled'
    assert select(settings=cfg(global_enabled=False)).reason == 'live_incremental_globally_disabled'


def test_bounded_rebase_setting():
    assert configured_max_advances(cfg(advances=288)) == 288
    assert configured_max_advances(cfg(advances=1000)) == 288
    assert configured_max_advances(cfg(advances=0)) == 1


def test_native_dynamic_incremental_approval_must_match_current_source():
    from app.services.live.retained_strategy_state import is_opted_in
    class Native:
        LIVE_INCREMENTAL_VERSION = 1
        def start_live_incremental(self, generated): return True
        def on_closed_candle(self, candle): return candle
    original = 'class Strategy: pass'
    params = dict(source_code=original, live_incremental_enabled=True,
                  live_incremental_parity_verified=True,
                  live_incremental_approved_source_sha256=source_sha256(original))
    assert is_opted_in(Native, params, global_enabled=True)
    params['source_code'] += '\n# edited'
    assert not is_opted_in(Native, params, global_enabled=True)
