"""Exact-source capability registry; not a strategy parity bypass."""
from __future__ import annotations

from hashlib import sha256


def approved_for_gap_reseed(*, selection, source_code: str, mode: str,
                            suppressed: bool, enabled: bool) -> bool:
    if str(mode).upper() not in {'DEMO', 'LIVE'} or not suppressed or not enabled or selection is None:
        return False
    if selection.strategy_class is None:
        return False
    # Only explicitly reviewed adapters, with independently verified pins.
    if selection.adapter_id == 'nas100_v48_native_v1':
        from strategies.nas100_v48_incremental import source_matches_frozen
        return bool(source_matches_frozen(source_code))
    if selection.adapter_id == 'v932_hybrid_v1':
        from .v932_hybrid_gate import V932_NORMALIZED_SHA256
        from strategies.v932_incremental import Strategy
        return (selection.strategy_class is Strategy and
                sha256(source_code.strip().encode()).hexdigest() == V932_NORMALIZED_SHA256)
    return False
