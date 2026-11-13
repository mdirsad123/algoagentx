"""Strict per-source V9.32 DEMO hybrid gate (NO implicit parity approval).
Source pin is the UTF-8 stripped DB source SHA displayed in AlgoAgentX.
The bundled original must not be changed when a future strategy is added.
"""
from __future__ import annotations
from hashlib import sha256
from typing import Any

V932_NORMALIZED_SHA256 = "a63659f9b6a4d0302165b94e9889b5da35e6fd2f4020d5893516ba4def9ad512"


def select_v932_hybrid_class(*, settings: Any, source_code: str, mode: str,
                              instrument: str, timeframe_seconds: int,
                              required_history_bars: int) -> tuple[type | None, str]:
    if not bool(getattr(settings, "live_incremental_enabled", False)):
        return None, "live_incremental_globally_disabled"
    if not bool(getattr(settings, "live_incremental_adapter_enabled", False)):
        return None, "adapter_disabled"
    # Exact-source eligibility is established below; the global monitor flag
    # only controls DEMO forward-test order submission after that selection.
    # NOTE: Frozen V9.32 has a documented historical-vs-right-edge BUY
    # discrepancy (2026-11-04 17:30 UTC). Operator-requested DEMO forward
    # testing does not turn that historical mismatch into parity approval.
    if str(mode).upper() != "DEMO":
        return None, "demo_only"
    if str(instrument).upper().strip() not in {"XAUUSD", "XAUUSD.X"}:
        return None, "instrument_not_allowed"
    if int(timeframe_seconds) != 300:
        return None, "m5_only"
    if int(required_history_bars) != 80000:
        return None, "exact_80000_history_required"
    actual = sha256(str(source_code).strip().encode("utf-8")).hexdigest()
    if actual != V932_NORMALIZED_SHA256:
        return None, "v932_db_source_mismatch"
    # The immutable V932_NORMALIZED_SHA256 is the only trusted source pin.
    # No global per-deployment environment SHA authorization is consulted.
    # Double check bundled original to detect accidentally changed research code.
    from strategies import v932_original_db_source as original
    from pathlib import Path
    original_path = Path(original.__file__)
    if sha256(original_path.read_text(encoding="utf8").strip().encode("utf8")).hexdigest() != actual:
        return None, "bundled_source_mismatch"
    from strategies.v932_incremental import Strategy
    # A user can forward-test the exact pinned V9.32 right-edge signals on a
    # DEMO account. This is an operator permission, NOT a parity certification:
    # the frozen historical replay still disagrees on a known old BUY signal.
    # LIVE is rejected above; stale/replay/duplicate order checks remain in the
    # shared runner. No strategy logic or source fingerprint is modified.
    monitor = bool(getattr(settings, "live_incremental_monitor_only", True))
    return Strategy, "selected_monitor_only" if monitor else "selected_demo_forward_test"
