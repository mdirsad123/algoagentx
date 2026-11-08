"""Offline-only V9.32 source pin, safety gates and signal parity smoke test.
For definitive 80K parity, run app/tools/verify_v932_incremental_parity.py.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import pandas as pd
import numpy as np

from app.services.live.incremental_adapter_registry import select_registered_adapter
from app.services.live.v932_hybrid_gate import V932_NORMALIZED_SHA256
from strategies.v932_original_db_source import Strategy as FrozenStrategy
from strategies.v932_incremental import Strategy as HybridStrategy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "strategies/v932_original_db_source.py").read_text(encoding="utf8")


def cfg(**kw):
    return SimpleNamespace(
        live_incremental_enabled=kw.get("global_enabled", True),
        live_incremental_adapter_enabled=kw.get("enabled", True),
        live_incremental_monitor_only=kw.get("monitor", True),
        live_incremental_parity_approved=kw.get("approved", False),
        live_incremental_authorized_source_sha256=kw.get("authorized", V932_NORMALIZED_SHA256),
        live_v64_hybrid_enabled=False,
    )


def pick(source=SOURCE, settings=None, **kw):
    return select_registered_adapter(
        settings=settings or cfg(), source_code=source,
        mode=kw.get("mode", "DEMO"), instrument=kw.get("instrument", "XAUUSD.X"),
        timeframe_seconds=kw.get("seconds", 300),
        required_history_bars=kw.get("bars", 80000),
    )


def test_exact_source_and_settings():
    assert hashlib.sha256(SOURCE.strip().encode()).hexdigest() == V932_NORMALIZED_SHA256
    choice = pick()
    assert choice.strategy_class is HybridStrategy
    assert choice.adapter_id == "v932_hybrid_v1"
    assert choice.monitor_only
    assert pick(SOURCE + "\n# edit").strategy_class is None
    assert pick(settings=cfg(authorized="0" * 64)).strategy_class is None
    assert pick(settings=cfg(monitor=False, approved=False)).reason == "v932_right_edge_mismatch_orders_blocked"
    assert pick(mode="LIVE").reason == "demo_only"
    assert pick(instrument="GBPUSD").reason == "instrument_not_allowed"
    assert pick(seconds=900).reason == "m5_only"
    assert pick(bars=79000).reason == "exact_80000_history_required"
    assert pick(settings=cfg(enabled=False)).strategy_class is None
    assert pick(settings=cfg(monitor=False, approved=True)).strategy_class is None
    assert pick(settings=cfg(monitor=False, approved=True)).reason == "v932_right_edge_mismatch_orders_blocked"


def assert_row_equal(expected, actual):
    assert pd.Timestamp(expected['Date']) == pd.Timestamp(actual['Date'])
    for k in ('Position','signal_reason'):
        assert expected[k] == actual[k], (k, expected[k], actual[k])
    for k in ('strategy_stop_loss', 'strategy_target'):
        a,b = float(expected[k]),float(actual[k])
        assert (np.isnan(a) and np.isnan(b)) or abs(a-b) < 1e-7, (k,a,b)


def test_realtime_market_parity_short_window():
    data = pd.read_csv(ROOT.parent / 'artifacts/backtest_private/xauusd.csv')
    data['Date'] = pd.to_datetime(data['Date'], utc=True)
    # Last portion is genuine 5-minute broker-like history, with a known
    # contiguous tail for repeated incremental trials.
    candidates = data[data['Date'] >= pd.Timestamp('2026-10-27', tz='UTC')].reset_index(drop=True)
    n=720
    start=None
    for i in range(n, len(candidates)-3):
        if (candidates['Date'].iloc[i+3] - candidates['Date'].iloc[i]) == pd.Timedelta(minutes=15):
            start=i
            break
    assert start is not None
    sample = candidates.iloc[start-n:start+4].copy().reset_index(drop=True)
    cold=sample.iloc[:n].copy()
    before=FrozenStrategy(cold).generate().iloc[-1]
    hybrid=HybridStrategy(cold)
    priming_frame=hybrid.generate()
    pre=priming_frame.iloc[-1]
    assert_row_equal(before,pre)
    assert hybrid.start_live_incremental(pd.DataFrame([pre])) is False  # must include full history
    assert hybrid.start_live_incremental(priming_frame) is True  # same count and not empty
    for i in range(n,n+4):
        row=sample.iloc[i].to_dict()
        actual=hybrid.on_closed_candle(row).iloc[-1]
        expected=FrozenStrategy(sample.iloc[:i+1].copy().reset_index(drop=True)).generate().iloc[-1]
        assert_row_equal(expected,actual)


def test_fail_closed_instrument_scope():
    from app.services.live.incremental_adapter_registry import adapter_required_for_instrument
    settings=cfg()
    settings.live_incremental_require_adapter_instruments = "XAUUSD,XAUUSD.X"
    assert adapter_required_for_instrument(settings,mode="DEMO",instrument="XAUUSD.X")
    assert not adapter_required_for_instrument(settings,mode="DEMO",instrument="GBPUSD")
    assert not adapter_required_for_instrument(settings,mode="LIVE",instrument="XAUUSD.X")
    settings.live_incremental_adapter_enabled=False
    assert adapter_required_for_instrument(settings,mode="DEMO",instrument="XAUUSD.X")
