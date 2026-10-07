from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.config import settings


@dataclass(frozen=True)
class LiveStrategyProfile:
    required_history_bars: int
    runtime_contract: dict[str, Any] | None = None


def _clamp_history_bars(value: Any) -> int:
    # One universal live-history default keeps every strategy on the same runtime
    # behavior. A strategy may explicitly request more/less history through its
    # DB parameters or class attributes; the platform never guesses from its name.
    default_bars = max(50, int(getattr(settings, "live_strategy_history_default_bars", 2_000) or 2_000))
    max_bars = max(default_bars, int(getattr(settings, "live_strategy_history_max_bars", 100_000) or 100_000))
    try:
        parsed = int(value)
    except Exception:
        parsed = default_bars
    return max(20, min(parsed, max_bars))


def resolve_live_strategy_profile(strategy_class: Any, db_parameters: dict[str, Any] | None = None) -> LiveStrategyProfile:
    params = db_parameters if isinstance(db_parameters, dict) else {}

    # Explicit strategy metadata can override the universal history amount when
    # a future strategy genuinely requires a different warm-up. Otherwise every
    # strategy receives the same platform default.
    explicit = params.get("live_history_bars") or params.get("required_history_bars")
    class_required = getattr(strategy_class, "LIVE_HISTORY_BARS", None) or getattr(strategy_class, "REQUIRED_HISTORY_BARS", None)

    # Dynamic DB strategies may not yet declare LIVE_HISTORY_BARS in their
    # uploaded class. Infer a conservative minimum from the actual source code
    # only when no explicit/class contract exists. Daily HTF feature stacks need
    # roughly 50+ completed trading days; 20k M5 bars gives a safe buffer for
    # XAUUSD sessions/weekends. 4H-only stacks need much less.
    inferred_required = None
    source_code = str(params.get("source_code") or "")
    source_lower = source_code.lower()
    if source_code:
        uses_daily = (
            '("1d", "1d", 1440)' in source_lower
            or "1d_atr14_50_ratio" in source_lower
            or "daily atr14/atr50" in source_lower
            or "completed-daily" in source_lower
        )
        uses_4h_long = (
            '("4h", "4h", 240)' in source_lower
            and ("atr100" in source_lower or "pre_range48" in source_lower or "ema50_100" in source_lower)
        )
        if uses_daily:
            inferred_required = 20_000
        elif uses_4h_long:
            inferred_required = 6_000

    selected = explicit if explicit not in (None, "") else class_required
    if selected in (None, ""):
        selected = inferred_required
    required = _clamp_history_bars(selected)

    # Operational escape hatch for constrained local/VM environments. This does
    # not alter strategy code; it only caps the amount of history supplied to
    # the live runner while diagnosing infrastructure pressure. Keep it at 0 in
    # normal production so each strategy receives its authored requirement.
    override = int(getattr(settings, "live_strategy_history_override_bars", 0) or 0)
    if override > 0:
        required = _clamp_history_bars(override)

    # Runtime settings are NOT inferred from a strategy name/class. RR, SL mode,
    # partial exit, BE/trailing, etc. stay controlled by the saved Admin/runtime
    # preset and live deployment settings. Only an explicit strategy-authored
    # contract is honored. This prevents one strategy profile from breaking
    # another strategy that intentionally uses different runtime settings.
    class_contract = getattr(strategy_class, "LIVE_RUNTIME_CONTRACT", None)
    db_contract = params.get("live_runtime_contract")
    if isinstance(db_contract, dict):
        contract = db_contract
    elif isinstance(class_contract, dict):
        contract = class_contract
    else:
        contract = None
    return LiveStrategyProfile(required_history_bars=required, runtime_contract=contract)


def _read_path(config: dict[str, Any], dotted: str) -> Any:
    value: Any = config
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _equivalent(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return bool(actual) is expected
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return abs(float(actual) - float(expected)) <= 1e-9
        except Exception:
            return False
    return str(actual or "").strip().upper() == str(expected or "").strip().upper()


def runtime_contract_violations(strategy_class: Any, runtime_config: dict[str, Any] | None, db_parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    profile = resolve_live_strategy_profile(strategy_class, db_parameters)
    if not profile.runtime_contract:
        return []
    config = runtime_config if isinstance(runtime_config, dict) else {}
    violations: list[dict[str, Any]] = []
    for path, expected in profile.runtime_contract.items():
        actual = _read_path(config, path)
        if not _equivalent(actual, expected):
            violations.append({"path": path, "expected": expected, "actual": actual})
    return violations
