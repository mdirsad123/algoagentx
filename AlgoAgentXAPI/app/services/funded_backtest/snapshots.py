from copy import deepcopy
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from . import FUNDED_RULE_ENGINE_VERSION


def _json_value(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if hasattr(value, "__table__"):
        return {column.name: _json_value(getattr(value, column.name)) for column in value.__table__.columns}
    return value


def build_profile_snapshot(profile, phases, risk_tiers) -> dict:
    return deepcopy(_json_value({
        "profile": profile,
        "phases": list(phases),
        "risk_tiers": list(risk_tiers),
        "rule_engine_version": FUNDED_RULE_ENGINE_VERSION,
    }))


def build_run_snapshots(*, profile, phases, risk_tiers, runtime_config, instrument_spec) -> dict:
    profile_snapshot = build_profile_snapshot(profile, phases, risk_tiers)
    return {
        "funded_profile_snapshot": profile_snapshot,
        "risk_plan_snapshot": deepcopy(profile_snapshot["risk_tiers"]),
        "runtime_config_snapshot": deepcopy(_json_value(runtime_config or {})),
        "instrument_spec_snapshot": deepcopy(_json_value(instrument_spec or {})),
        "rule_engine_version": FUNDED_RULE_ENGINE_VERSION,
    }
