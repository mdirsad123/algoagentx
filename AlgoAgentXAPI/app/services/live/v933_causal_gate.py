"""Research-only Gold V9.33 SHA gate. NEVER authorizes broker orders.

V9.33 corrects four as-of-right-edge signal exclusions from frozen V9.32.
Its hybrid adapter still recalculates history; it is NOT a native adapter.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from typing import Any

V933_CAUSAL_SOURCE_NORMALIZED_SHA256 = "c08c6f4b8ff54033e873eabd5faddb9c1ff6bee6a292a91ff485d08c9bed469b"
V933_CAUSAL_SOURCE_RAW_SHA256 = "365b11c1f5bded3b3b7b1d85118f17b3287b5823a1d4986635825f458d9413ba"


def matches_v933_causal_source(source_code: str) -> bool:
    return bool(source_code) and sha256(source_code.strip().encode('utf-8')).hexdigest() == V933_CAUSAL_SOURCE_NORMALIZED_SHA256


def select_v933_causal_hybrid(*, settings: Any, source_code: str, mode: str,
                              instrument: str, timeframe_seconds: int,
                              required_history_bars: int) -> tuple[type | None, str]:
    if not bool(getattr(settings, 'live_incremental_enabled', False)):
        return None, 'live_incremental_globally_disabled'
    if not bool(getattr(settings, 'live_incremental_adapter_enabled', False)):
        return None, 'adapter_disabled'
    # Global monitor=False is a request, never adapter eligibility evidence.
    # This unverified hybrid remains monitor-only in the registry and runner.
    # No Gold-specific environment opt-in is needed to select it safely.
    if mode.upper() != 'DEMO':
        return None, 'demo_only'
    if instrument.strip().upper() not in {'XAUUSD', 'XAUUSD.X'}:
        return None, 'instrument_not_allowed'
    if timeframe_seconds != 300:
        return None, 'm5_only'
    if required_history_bars != 80000:
        return None, 'exact_80000_history_required'
    if not matches_v933_causal_source(source_code):
        return None, 'source_identity_mismatch'
    src = Path(__file__).resolve().parents[3] / 'strategies' / 'v933_causal_gold_source.py'
    if not src.is_file() or sha256(src.read_bytes()).hexdigest() != V933_CAUSAL_SOURCE_RAW_SHA256:
        return None, 'bundled_source_mismatch'
    from strategies.v933_causal_hybrid_incremental import Strategy
    return Strategy, 'selected_monitor_only'
