"""Reuse a verified dynamic-output check without relaxing live order guardrails.

Only expensive strategy output checks are cached. Instrument specification,
capital, source resolution, runtime contracts and candle coverage MUST still be
re-evaluated on every explicit compatibility request.

The cache is keyed by configuration_fingerprint (which includes the DB strategy
source/parameters and bundled strategy binary digest); Redis separately expires
it after a bounded interval. The enabling approval remains short-lived.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEEP_CACHE_VERSION = 1
DEEP_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
DEEP_CHECK_NAMES = frozenset({
    "Strategy generates DataFrame", "Signal contract", "Strategy SL output",
})
ALLOWED_STATUSES = frozenset({"PASS", "WARNING"})


def create_deep_cache(fingerprint: str, result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("status") not in ALLOWED_STATUSES:
        return None
    checks = {c.get("name"): c for c in (result.get("checks") or []) if isinstance(c, dict)}
    if not DEEP_CHECK_NAMES.issubset(checks):
        return None
    if any(checks[name].get("status") not in ALLOWED_STATUSES for name in DEEP_CHECK_NAMES):
        return None
    return {
        "version": DEEP_CACHE_VERSION,
        "fingerprint": fingerprint,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "deep_checks": {name: checks[name] for name in DEEP_CHECK_NAMES},
    }


def reuse_deep_cache(
    fingerprint: str, lightweight: dict[str, Any], stored: Any,
) -> dict[str, Any] | None:
    """Return a fresh eligibility result only for the exact approved fingerprint.

    A failed lightweight check always wins; no old output can revive an invalid
    broker, instrument, runtime contract, strategy, or missing warmup history.
    """
    if lightweight.get("status") not in ALLOWED_STATUSES or not isinstance(stored, dict):
        return None
    if stored.get("version") != DEEP_CACHE_VERSION or stored.get("fingerprint") != fingerprint:
        return None
    checked = stored.get("deep_checks")
    if not isinstance(checked, dict) or not DEEP_CHECK_NAMES.issubset(checked):
        return None
    if any(not isinstance(checked[name], dict) or checked[name].get("status") not in ALLOWED_STATUSES for name in DEEP_CHECK_NAMES):
        return None
    result_checks = []
    seen = set()
    for original in lightweight.get("checks") or []:
        if not isinstance(original, dict):
            return None
        name = original.get("name")
        if name in DEEP_CHECK_NAMES:
            evidence = checked[name]
            info = dict(evidence.get("data") or {})
            info.update({"reused_verified_output": True, "verified_at_utc": stored.get("verified_at_utc")})
            result_checks.append({**evidence, "message": f"{evidence.get('message', '')} (previous verified output reused; current broker/runtime rechecked)", "data": info})
            seen.add(name)
        else:
            result_checks.append(original)
    if seen != DEEP_CHECK_NAMES:
        return None
    statuses = {str(check.get("status")) for check in result_checks}
    if not statuses.issubset(ALLOWED_STATUSES):
        return None
    status = "WARNING" if "WARNING" in statuses else "PASS"
    return {
        "status": status,
        "summary": "Live compatible (verified strategy output reused)" if status == "PASS" else "Live compatible with warnings (verified output reused)",
        "checks": result_checks,
        "verification_mode": "cached_deep_source_pinned_and_fresh_lightweight",
        "deep_verified_at_utc": stored.get("verified_at_utc"),
    }
