"""NAS100 V4.8-only adapter authorization (DEMO, M5, 80K, source pinned).

Do not mutate the DB strategy; avoid approving variants by title/symbol.
Monitor-only is diagnostic; explicit parity approval is required for orders.
Source approval is derived automatically from the immutable frozen reference.
"""
from __future__ import annotations

from typing import Any

from strategies.nas100_v48_incremental import source_matches_frozen


def select_nas100_v48_class(*, settings: Any, source_code: str, mode: str,
                            instrument: str, timeframe_seconds: int,
                            required_history_bars: int) -> tuple[type | None, str]:
    if not bool(getattr(settings, "live_incremental_enabled", False)):
        return None, "live_incremental_globally_disabled"
    if not bool(getattr(settings, "live_incremental_adapter_enabled", False)):
        return None, "adapter_disabled"
    if str(mode).upper() != "DEMO":
        return None, "demo_only"
    if str(instrument).upper().strip() not in {"NAS100", "NAS100.X", "USTECH", "USTECH.X", "USTEC", "USTEC.X", "USTECH100", "USTECH100.X", "US100", "US100.X"}:
        return None, "nas100_instrument_not_allowed"
    if int(timeframe_seconds) != 300:
        return None, "m5_only"
    if int(required_history_bars) != 80000:
        return None, "exact_80000_history_required"
    if not source_matches_frozen(str(source_code or "")):
        return None, "nas100_v48_db_source_mismatch"
    # Accept exact frozen bytes or the same Python AST (comments/formatting only).
    # A real code-logic change, even with the same name, remains blocked.
    monitor = bool(getattr(settings, "live_incremental_monitor_only", True))
    if not monitor and not bool(getattr(settings, "live_incremental_parity_approved", False)):
        return None, "nas100_v48_parity_not_approved"
    # A caller's writable environment is not evidence of parity. This gate is
    # source/operational authorization only; independent tests are mandatory.
    from strategies.nas100_v48_incremental import make_strategy
    return make_strategy(source_code), "selected_monitor_only" if monitor else "selected"
