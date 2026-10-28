"""No production DB/broker side effects: test fail-closed V6.4 selection."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
from app.services.live.v64_hybrid_gate import select_v64_hybrid_class, BASELINE_SHA256

ROOT=Path(__file__).resolve().parents[2]
SOURCE=(ROOT/'production_patch/v64/V64_BASELINE_RESEARCH_ONLY.py')

def switches(**kwargs):
    return SimpleNamespace(live_incremental_enabled=kwargs.get('global_enabled', True),
        live_v64_hybrid_enabled=kwargs.get('enabled', False),
        live_v64_hybrid_parity_approved=kwargs.get('approved', False),
        live_v64_hybrid_monitor_only=kwargs.get('monitor', False),
        live_v64_hybrid_authorized_source_sha256=kwargs.get('sha',''))

def choose(cfg, src, **kw):
    return select_v64_hybrid_class(settings=cfg,source_code=src,mode=kw.get('mode','DEMO'),
       instrument=kw.get('instrument','XAUUSD.X'),timeframe_seconds=kw.get('timeframe',300),
       required_history_bars=kw.get('bars',80000))

def test_default_is_disabled():
    assert choose(switches(), 'irrelevant')==(None,'disabled')

def test_flags_are_independent():
    assert choose(switches(enabled=True),'foo')[1]=='parity_not_approved'
    assert choose(switches(enabled=True,approved=True,global_enabled=False),'foo')[1]=='live_incremental_globally_disabled'

def test_exact_source_mandatory():
    cfg=switches(enabled=True,approved=True,sha=BASELINE_SHA256)
    assert choose(cfg,'modified strategy')[1]=='db_source_sha_not_frozen_reference'

def test_restrictions():
    cfg=switches(enabled=True,approved=True,sha=BASELINE_SHA256)
    assert choose(cfg,'unused',mode='LIVE')[1]=='demo_only'
    assert choose(cfg,'unused',timeframe=60)[1]=='m5_only'
    assert choose(cfg,'unused',bars=79000)[1]=='exact_80000_history_required'

def test_matching_frozen_source_can_select():
    src=(ROOT/'production_patch/v64/V64_BASELINE_RESEARCH_ONLY.py').read_text(encoding='utf-8')
    actual_sha=hashlib.sha256(src.encode()).hexdigest()
    assert actual_sha == BASELINE_SHA256
    cfg=switches(enabled=True,approved=True,sha=actual_sha)
    klass, reason=choose(cfg,src)
    assert reason=='selected' and klass.LIVE_INCREMENTAL_VERSION==1
    assert choose(switches(enabled=True,approved=True,sha='0'*64),src)[1]=='authorized_source_sha_missing_or_mismatch'

def test_unapproved_monitor_can_only_select_monitor_mode():
    src=SOURCE.read_text(encoding='utf-8')
    cfg=switches(enabled=True,approved=False,monitor=True,sha=BASELINE_SHA256)
    klass, reason=choose(cfg,src)
    assert reason == 'selected_monitor_only' and klass.LIVE_INCREMENTAL_VERSION==1
