"""Fail-closed *runtime-only* V6.4 adapter gate for local TradeLocker DEMO.

The real DB Strategy source stays authoritative and unchanged. This gate ONLY
selects a trusted, bundled research candidate when an operator has approved
independent real-broker 80K parity testing and intentionally configured all
three environment flags. Default is the original FULL_HISTORY implementation.

This is NOT a claim that the candidate has achieved exact rolling parity.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

# Frozen research source provided by the user on Oct 28, 2026. Never accept
# 'same strategy name' or a loosely similar code body as verification.
BASELINE_SHA256 = '7122bb951cd867f3cd57f66d2fef6b6307e708c7c4a5547d42aaab79a2bbb5cb'
BASELINE_STRIPPED_SHA256 = 'c50b77c72656ce76ec69b87cca07254520f88d181545a3ee4c60d161a25b2747'


def _true(value: Any) -> bool:
    return value is True or str(value).lower() in {'true', '1', 'yes', 'on'}


def select_v64_hybrid_class(*, settings: Any, source_code: str, mode: str,
                            instrument: str, timeframe_seconds: int,
                            required_history_bars: int) -> tuple[type | None, str]:
    if not _true(getattr(settings, 'live_v64_hybrid_enabled', False)):
        return None, 'disabled'
    monitor_only = _true(getattr(settings, 'live_v64_hybrid_monitor_only', False))
    if not monitor_only and not _true(getattr(settings, 'live_v64_hybrid_parity_approved', False)):
        return None, 'parity_not_approved'
    if not _true(getattr(settings, 'live_incremental_enabled', False)):
        return None, 'live_incremental_globally_disabled'
    if str(mode).upper() != 'DEMO':
        return None, 'demo_only'
    if str(instrument).upper().strip() not in {'XAUUSD.X', 'XAUUSD'}:
        return None, 'instrument_not_allowed'
    if timeframe_seconds != 300:
        return None, 'm5_only'
    if required_history_bars != 80000:
        return None, 'exact_80000_history_required'
    if not source_code.strip():
        return None, 'db_source_missing'
    raw_hash = sha256(source_code.encode('utf8')).hexdigest()
    normalized_hash = sha256(source_code.strip().encode('utf8')).hexdigest()
    if raw_hash != BASELINE_SHA256 and normalized_hash != BASELINE_STRIPPED_SHA256:
        return None, 'db_source_sha_not_frozen_reference'
    expected = str(getattr(settings, 'live_v64_hybrid_authorized_source_sha256', '') or '').strip().lower()
    if not expected or expected != raw_hash:
        return None, 'authorized_source_sha_missing_or_mismatch'
    # Imported only on genuinely approved DEMO deployments; no other strategy
    # sees this large research code or changes behavior.
    from strategies.v64_hybrid_incremental import Strategy
    return Strategy, ('selected_monitor_only' if monitor_only else 'selected')
