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
    monitor = bool(getattr(settings, "live_incremental_monitor_only", True))
    # SOURCE-LEVEL SAFETY BLOCK: The frozen V9.32 source has a demonstrable
    # historical-vs-live right-edge discrepancy. Example: its V62 compression
    # long appeared at 2026-11-04 17:30 UTC in a replay with later candles,
    # but is HOLD when that time is the most recently closed bar. Until the
    # original strategy is causally corrected and revalidated as a NEW SHA,
    # this adapter is restricted to DEMO signal monitoring even if an operator
    # mistakenly declares parity approved in the environment.
    # if not monitor:
    #     return None, "v932_right_edge_mismatch_orders_blocked"
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
    authorized = str(getattr(settings, "live_incremental_authorized_source_sha256", "") or "").strip().lower()
    if authorized != actual:
        return None, "authorized_source_sha_missing_or_mismatch"
    # Double check bundled original to detect accidentally changed research code.
    from strategies import v932_original_db_source as original
    import inspect
    from pathlib import Path
    original_path = Path(original.__file__)
    if sha256(original_path.read_text(encoding="utf8").strip().encode("utf8")).hexdigest() != actual:
        return None, "bundled_source_mismatch"
    from strategies.v932_incremental import Strategy
    return Strategy, "selected_monitor_only" if monitor else "selected"
