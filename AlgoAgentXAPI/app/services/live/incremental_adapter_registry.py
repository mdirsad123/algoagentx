"""Generic *registry* for known, source-pinned incremental adapters.

A SHA identifies a strategy; it NEVER makes arbitrary Python generate() code
incremental. Registered adapters declare their own immutable source fingerprints
and runtime contract. The runtime computes the fingerprint automatically from
DB strategy code; no manual .env SHA is needed. Unregistered strategies use
full-history evaluation, or the native incremental v1 protocol when separately
verified and approved for their exact DB source.
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
    # Source is checked against the immutable, bundled adapter fingerprint in
    # each strategy gate. No mutable process-wide .env SHA authorization exists;
    # this lets multiple independently registered strategies run concurrently.
    # Recognize the exact frozen NAS100 V4.8 source BEFORE dispatching to the
    # XAUUSD-only V6.4 fallback. A different NAS100 version cannot inherit
    # compatibility merely by matching the instrument name.
    from strategies.nas100_v48_incremental import source_matches_frozen
    if source_code and source_matches_frozen(source_code):
        from .nas100_v48_gate import select_nas100_v48_class
        klass, reason = select_nas100_v48_class(
            settings=settings, source_code=source_code, mode=mode,
            instrument=instrument, timeframe_seconds=timeframe_seconds,
            required_history_bars=required_history_bars,
        )
        return AdapterSelection(
            klass, "nas100_v48_native_v1" if klass else None,
            reason, monitor and klass is not None, source_hash,
        )
    # Do not misdiagnose an unrecognized NAS100 source as an XAUUSD instrument
    # error. Its exact V4.8 source pin must be examined before selecting code.
    if use_generic and str(instrument).upper().strip() in {
        "NAS100", "NAS100.X", "USTECH", "USTECH.X", "USTEC", "USTEC.X",
        "USTECH100", "USTECH100.X", "US100", "US100.X"
    }:
        return AdapterSelection(None, None, "nas100_v48_logic_mismatch_or_unsupported_version", False, source_hash)
    # Recognize the Gold V9.33 *causal-source research fork* by the exact
    # normalized source identity. This is deliberately NOT a native adapter:
    # routing it to V6.4, old V9.32 hybrid, or generic order mode would be
    # unsafe. A separate verified native conversion is required.
    from .v933_causal_gate import matches_v933_causal_source, select_v933_causal_hybrid
    if source_code and matches_v933_causal_source(source_code):
        klass, reason = select_v933_causal_hybrid(
            settings=settings, source_code=source_code, mode=mode,
            instrument=instrument, timeframe_seconds=timeframe_seconds,
            required_history_bars=required_history_bars,
        )
        return AdapterSelection(klass, 'v933_causal_hybrid_monitor_v1' if klass else None,
                                reason, bool(klass), source_hash)
    # V9.32 is independently pinned to the uploaded, normalized DB source.
    # Merely changing the .env SHA NEVER reuses the V6.4 algorithm.
    from .v932_hybrid_gate import select_v932_hybrid_class, V932_NORMALIZED_SHA256
    if source_code and sha256(source_code.strip().encode("utf-8")).hexdigest() == V932_NORMALIZED_SHA256:
        class_932, reason_932 = select_v932_hybrid_class(
            settings=settings, source_code=source_code, mode=mode,
            instrument=instrument, timeframe_seconds=timeframe_seconds,
            required_history_bars=required_history_bars,
        )
        # DEMO operator mode uses the *same* global MONITOR_ONLY toggle as
        # NAS100. No extra Gold-specific .env key or per-version SHA approval.
        # The gate still requires the exact frozen source, XAUUSD, M5 and 80K.
        return AdapterSelection(class_932, "v932_hybrid_v1" if class_932 else None,
                                reason_932, bool(class_932) and monitor, source_hash)
    # The pinned V6.4 descriptor is the first registered adapter. Additional
    # algorithms must implement and register their own explicit protocol.
    effective = SimpleNamespace(
        live_incremental_enabled=bool(getattr(settings, "live_incremental_enabled", False)),
        live_v64_hybrid_enabled=True,
        live_v64_hybrid_monitor_only=monitor,
        live_v64_hybrid_parity_approved=approved,
        # Bundled source hash pin is the authority, not a global env SHA.
    )
    klass, reason = select_v64_hybrid_class(
        settings=effective, source_code=source_code, mode=mode,
        instrument=instrument, timeframe_seconds=timeframe_seconds,
        required_history_bars=required_history_bars,
    )
    return AdapterSelection(klass, "v64_hybrid_v1" if klass else None,
                            reason, monitor and bool(klass), source_hash)


def v932_demo_forward_test_orders_permitted(*, source_code: str, mode: str,
                                            selection: AdapterSelection | None) -> bool:
    """Operator-requested DEMO permission, **not** historical parity certification.

    Requires an actual eligible exact-source V9.32 adapter. Unknown source,
    full-history fallback, monitor mode, and LIVE accounts never inherit it.
    """
    from .v932_hybrid_gate import V932_NORMALIZED_SHA256
    return bool(
        selection is not None and selection.strategy_class is not None
        and selection.adapter_id == 'v932_hybrid_v1'
        and not selection.monitor_only
        and str(mode).upper() == 'DEMO'
        and sha256(str(source_code).strip().encode('utf-8')).hexdigest() == V932_NORMALIZED_SHA256
    )


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
    current = str(instrument).upper().strip()
    # TradeLocker may append .X to NAS100/USTECH and XAUUSD instruments.
    # An explicit base-symbol opt-in must still fail closed for the same
    # broker-suffixed instrument; this never grants adapter compatibility.
    if current in wanted:
        return True
    if current.endswith(".X") and current[:-2] in wanted:
        return True
    if current + ".X" in wanted:
        return True
    return False
