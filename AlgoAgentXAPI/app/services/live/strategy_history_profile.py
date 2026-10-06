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
    default_bars = max(50, int(getattr(settings, "live_strategy_history_default_bars", 20_000) or 20_000))
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
    required = _clamp_history_bars(explicit if explicit not in (None, "") else class_required)

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
