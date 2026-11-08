"""Generic *registry* for known, source-pinned incremental adapters.

A SHA identifies a strategy; it NEVER makes arbitrary Python generate() code
incremental. Registered adapters declare their own source fingerprints and
runtime contract. Other strategies use the original full-history path, or the
explicitly implemented v1 native incremental protocol when separately approved.
No database migrations, broker calls, or strategy-source overwrites.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

from .v64_hybrid_gate import select_v64_hybrid_class


@dataclass(frozen=True)
class AdapterSelection:
    strategy_class: type | None
    adapter_id: str | None
    reason: str
    monitor_only: bool
    source_sha256: str


def source_sha256(source: str) -> str:
    return sha256(source.encode("utf-8")).hexdigest() if source else ""


def select_registered_adapter(*, settings: Any, source_code: str, mode: str,
                              instrument: str, timeframe_seconds: int,
                              required_history_bars: int) -> AdapterSelection:
    source_hash = source_sha256(source_code)
    generic_enabled = bool(getattr(settings, "live_incremental_adapter_enabled", False))
    legacy_enabled = bool(getattr(settings, "live_v64_hybrid_enabled", False))
    if not generic_enabled and not legacy_enabled:
        return AdapterSelection(None, None, "disabled", False, source_hash)
    # Existing V6.4 configuration remains compatible, but operators should
    # remove old LIVE_V64_* flags when switching to generic names.
    use_generic = generic_enabled
    monitor = bool(getattr(settings,
            "live_incremental_monitor_only" if use_generic else "live_v64_hybrid_monitor_only", True))
    approved = bool(getattr(settings,
            "live_incremental_parity_approved" if use_generic else "live_v64_hybrid_parity_approved", False))
    authorized_sha = str(getattr(settings,
            "live_incremental_authorized_source_sha256" if use_generic
            else "live_v64_hybrid_authorized_source_sha256", "") or "")
    # V9.32 is independently pinned to the uploaded, normalized DB source.
    # Merely changing the .env SHA NEVER reuses the V6.4 algorithm.
    from .v932_hybrid_gate import select_v932_hybrid_class, V932_NORMALIZED_SHA256
    if source_code and sha256(source_code.strip().encode("utf-8")).hexdigest() == V932_NORMALIZED_SHA256:
        class_932, reason_932 = select_v932_hybrid_class(
            settings=settings, source_code=source_code, mode=mode,
            instrument=instrument, timeframe_seconds=timeframe_seconds,
            required_history_bars=required_history_bars,
        )
        return AdapterSelection(class_932, "v932_hybrid_v1" if class_932 else None,
                                reason_932, monitor and bool(class_932), source_hash)
    # The pinned V6.4 descriptor is the first registered adapter. Additional
    # algorithms must implement and register their own explicit protocol.
    effective = SimpleNamespace(
        live_incremental_enabled=bool(getattr(settings, "live_incremental_enabled", False)),
        live_v64_hybrid_enabled=True,
        live_v64_hybrid_monitor_only=monitor,
        live_v64_hybrid_parity_approved=approved,
        live_v64_hybrid_authorized_source_sha256=authorized_sha,
    )
    klass, reason = select_v64_hybrid_class(
        settings=effective, source_code=source_code, mode=mode,
        instrument=instrument, timeframe_seconds=timeframe_seconds,
        required_history_bars=required_history_bars,
    )
    return AdapterSelection(klass, "v64_hybrid_v1" if klass else None,
                            reason, monitor and bool(klass), source_hash)


def configured_max_advances(settings: Any) -> int:
    use_generic = bool(getattr(settings, "live_incremental_adapter_enabled", False))
    name = "live_incremental_max_advances" if use_generic else "live_v64_hybrid_max_advances"
    return max(1, min(288, int(getattr(settings, name, 48))))


def adapter_required_for_instrument(settings: Any, *, mode: str, instrument: str) -> bool:
    """Fail-closed opt-in for selected DEMO instruments, not a global kill switch."""
    # This guard is deliberately independent of adapter-enabled/approved flags:
    # turning the adapter off must NOT silently enable old full-history orders.
    if str(mode).upper() != "DEMO":
        return False
    wanted = {x.strip().upper() for x in str(getattr(
        settings, "live_incremental_require_adapter_instruments", "") or "").split(",") if x.strip()}
    return str(instrument).upper().strip() in wanted
