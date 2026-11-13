"""Pure source-pinned Gold hybrid order-readiness marker for UI and tests.

Do not equate the global Auto Trade toggle with broker-order authorization.
"""
from __future__ import annotations
from hashlib import sha256
from .v932_hybrid_gate import V932_NORMALIZED_SHA256
from .v933_causal_gate import V933_CAUSAL_SOURCE_NORMALIZED_SHA256


def gold_monitor_only_adapter(*, strategy_params: object, mode: str) -> str | None:
    if str(mode).upper() != 'DEMO' or not isinstance(strategy_params, dict):
        return None
    source=str(strategy_params.get('source_code') or '')
    if not source:
        return None
    digest=sha256(source.strip().encode('utf-8')).hexdigest()
    if digest==V932_NORMALIZED_SHA256:
        return 'v932_hybrid_v1'
    if digest==V933_CAUSAL_SOURCE_NORMALIZED_SHA256:
        return 'v933_causal_hybrid_monitor_v1'
    return None


def gold_v932_is_monitor_only(*, strategy_params: object, mode: str) -> bool:
    """Backward-compatible standalone V9.32 probe for existing callers."""
    return gold_monitor_only_adapter(strategy_params=strategy_params,mode=mode)=='v932_hybrid_v1'
