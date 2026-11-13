"""Versioned data contracts for the registry; no database or broker side effects.

Structural interface checks are not trading approval or a security sandbox.
Only trusted, published source may be executed by a supervised worker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
import math
from typing import Any, Protocol

import pandas as pd

INTERFACE_VERSION = 1


class IncrementalContractError(ValueError):
    pass


class IncrementalStrategy(Protocol):
    def initialize(self, history: pd.DataFrame, context: dict[str, Any]) -> Any: ...
    def on_closed_bar(self, bar: dict[str, Any]) -> Any: ...
    def snapshot(self) -> dict[str, Any]: ...
    def restore(self, snapshot: dict[str, Any], context: dict[str, Any]) -> Any: ...


def canonical_json(value: Any) -> str:
    """Reject lossy coercions (tuple, non-string key, NaN, Decimal, datetime)."""
    def validate(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child)
            return
        raise IncrementalContractError(f"State/configuration is not lossless JSON: {type(item).__name__}")

    validate(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True)


def digest_json(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def source_digest(source: str) -> str:
    if not isinstance(source, str) or not source.strip():
        raise IncrementalContractError("Database strategy source is missing")
    # Do not strip: even whitespace edits are new immutable source revisions.
    return sha256(source.encode("utf-8")).hexdigest()


def positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 1:
        raise IncrementalContractError(f"{name} must be a positive integer")
    return value


def utc_timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IncrementalContractError("Candle cursor must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def validate_native_class(strategy_class: type) -> int:
    """Validate actual resolved methods, including inherited async methods."""
    arity = {"generate": 0, "initialize": 2, "on_closed_bar": 1, "snapshot": 0, "restore": 2}
    for name, count in arity.items():
        method = getattr(strategy_class, name, None)
        if not callable(method) or inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(method):
            raise IncrementalContractError(f"{name} must be a synchronous method")
        if inspect.isgeneratorfunction(method):
            raise IncrementalContractError(f"{name} must return a value, not a generator")
        try:
            descriptor = inspect.getattr_static(strategy_class, name)
            args = [None] * count
            if not isinstance(descriptor, (staticmethod, classmethod)):
                args.insert(0, None)
            inspect.signature(method).bind(*args)
        except (TypeError, ValueError) as exc:
            raise IncrementalContractError(f"Invalid {name} signature") from exc
    version = getattr(strategy_class, "LIVE_INCREMENTAL_VERSION", INTERFACE_VERSION)
    if type(version) is not int or version != INTERFACE_VERSION:
        raise IncrementalContractError("Unsupported incremental interface version")
    return positive_int(getattr(strategy_class, "LIVE_INCREMENTAL_STATE_SCHEMA_VERSION", 1), "state schema version")


@dataclass(frozen=True)
class ExecutionIdentity:
    deployment_id: str
    revision_id: str
    source_sha256: str
    configuration_json: str = field(repr=False)
    state_schema_version: int = 1

    def __post_init__(self):
        positive_int(self.state_schema_version, "state schema version")
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise IncrementalContractError("Invalid source SHA256")
        configuration = json.loads(self.configuration_json)
        if not isinstance(configuration, dict) or canonical_json(configuration) != self.configuration_json:
            raise IncrementalContractError("Configuration must be a canonical JSON object")

    @property
    def fingerprint(self) -> str:
        return digest_json({
            "deployment_id": self.deployment_id, "revision_id": self.revision_id,
            "source_sha256": self.source_sha256, "configuration": json.loads(self.configuration_json),
            "interface_version": INTERFACE_VERSION, "state_schema_version": self.state_schema_version,
        })


def checkpoint_payload(identity: ExecutionIdentity, *, generation: int, sequence: int,
                       candle_open: datetime, candle_count: int, last_candle: dict,
                       state: dict) -> dict:
    positive_int(generation, "generation")
    positive_int(sequence, "sequence")
    positive_int(candle_count, "candle count")
    if type(state) is not dict:
        raise IncrementalContractError("snapshot() must return a JSON object")
    cursor = utc_timestamp(candle_open).isoformat()
    if last_candle.get("Date") != cursor:
        raise IncrementalContractError("Last candle Date must equal the UTC cursor ISO timestamp")
    for name in ("Open", "High", "Low", "Close", "Volume"):
        value = last_candle.get(name)
        if type(value) not in (float, int) or not math.isfinite(value):
            raise IncrementalContractError(f"Last candle {name} must be finite")
    payload = {
        "deployment_id": identity.deployment_id, "revision_id": identity.revision_id,
        "source_sha256": identity.source_sha256, "fingerprint": identity.fingerprint,
        "interface_version": INTERFACE_VERSION, "state_schema_version": identity.state_schema_version,
        "generation": generation, "sequence": sequence, "candle_open": cursor,
        "candle_count": candle_count, "last_candle": last_candle, "state": state,
    }
    # Detach nested objects so subsequent strategy mutations cannot change the envelope.
    return json.loads(canonical_json(payload))