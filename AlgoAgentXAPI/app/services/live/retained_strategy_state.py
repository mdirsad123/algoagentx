"""Optional per-process incremental live strategy state (versioned contract).

No strategy is implicitly made incremental. The strategy must opt in, have its
signal parity independently verified, and implement explicit start/update methods.
The scheduler/database remain authoritative: process restart or gaps cold-start.
Do not share strategy instances across processes or attempt to pickle dynamic code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)
MAX_RETAINED = 8


def utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def signature(*, strategy_id: str, params: dict, runtime: dict, history_bars: int, timeframe: str, instrument: str) -> str:
    payload = {
        'strategy_id': strategy_id, 'parameters': params, 'runtime': runtime,
        'history_bars': history_bars, 'timeframe': timeframe, 'instrument': instrument,
        'interface_version': 1,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(',', ':')).encode()
    return sha256(encoded).hexdigest()


def signal_runtime_identity(runtime: dict, *, capital_independent: bool, configured_capital: Any) -> dict:
    """Only the source-pinned V6.4 adapter is proven independent of broker equity.

    Never mutate execution runtime: order preview/sizing must still resolve current
    broker equity. Preserve explicitly configured capital edits in cache identity.
    Native/unknown incremental strategies retain the original strict fingerprint.
    """
    identity = deepcopy(runtime)
    if capital_independent:
        identity.setdefault('risk', {})['initial_capital'] = str(configured_capital)
    return identity


def fingerprint_fields(*, params: dict, runtime: dict) -> dict[str, str]:
    """Per-field digests for diagnosis, never source code/credentials in logs."""
    result = {}
    def visit(path, value):
        if isinstance(value, dict) and value:
            for key, item in value.items():
                visit(f'{path}.{key}', item)
        else:
            result[path] = sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
    visit('parameters', params)
    visit('runtime', runtime)
    return result


def candle_fingerprint(candle: dict) -> str:
    # Finalized broker OHLCV is authoritative; normalize Decimal/float formatting
    # for checks across cold DB and generated incremental DataFrame paths.
    value = {k: str(float(candle[k] if k in candle else candle[k.lower()]))
             for k in ('Open', 'High', 'Low', 'Close', 'Volume')}
    raw_time = candle.get('Date', candle.get('candle_time'))
    value['Date'] = utc(pd.Timestamp(raw_time).to_pydatetime()).isoformat()
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def is_opted_in(strategy_class: type, params: dict, *, global_enabled: bool) -> bool:
    # A dynamic strategy approval must be bound to its *actual* current source,
    # not inherited accidentally when an admin edits and republishes code.
    source = params.get('source_code')
    if source:
        approved = str(params.get('live_incremental_approved_source_sha256') or '').lower()
        actual = sha256(str(source).encode('utf8')).hexdigest()
        if not approved or approved != actual:
            return False
    return bool(
        global_enabled and params.get('live_incremental_enabled') is True
        and params.get('live_incremental_parity_verified') is True
        and getattr(strategy_class, 'LIVE_INCREMENTAL_VERSION', None) == 1
        and callable(getattr(strategy_class, 'start_live_incremental', None))
        and callable(getattr(strategy_class, 'on_closed_candle', None))
    )


@dataclass
class RetainedEntry:
    fingerprint: str
    candle_time: datetime
    strategy: Any
    candle_count: int
    last_candle_fingerprint: str
    fields: dict[str, str] = field(default_factory=dict)
    last_candle: dict = field(default_factory=dict)
    observed_capital: str | None = None


class RetainedStateCache:
    def __init__(self):
        self._entries: dict[str, RetainedEntry] = {}

    def invalidate(self, deployment_id: str, reason: str = 'invalidated') -> None:
        if self._entries.pop(deployment_id, None) is not None:
            log.info('RUNNER_INCREMENTAL_INVALIDATED deployment=%s reason=%s', deployment_id, reason)

    def rebase_due(self, deployment_id: str, *, history_bars: int, max_advances: int) -> bool:
        entry = self._entries.get(deployment_id)
        return entry is not None and entry.candle_count >= history_bars + max_advances

    def get_for_next_candle(self, deployment_id: str, *, fingerprint: str, last_processed: datetime | None,
                            next_candle_time: datetime, timeframe_seconds: int,
                            previous_candle: dict | None = None, fields: dict | None = None,
                            observed_capital: str | None = None) -> RetainedEntry | None:
        entry = self._entries.get(deployment_id)
        if entry is None:
            log.info('RUNNER_INCREMENTAL_COLD deployment=%s reason=no_process_state cursor=%s next=%s',
                     deployment_id, utc(last_processed), utc(next_candle_time))
            return None
        previous = utc(entry.candle_time)
        expected = previous + timedelta(seconds=timeframe_seconds)
        failures = []
        if entry.fingerprint != fingerprint:
            failures.append('fingerprint_changed')
        if utc(last_processed) != previous:
            failures.append('cursor_mismatch')
        if utc(next_candle_time) != expected:
            failures.append('nonconsecutive_candle')
        actual_candle_fingerprint = None
        if previous_candle is None:
            failures.append('previous_candle_missing')
        else:
            try:
                actual_candle_fingerprint = candle_fingerprint(previous_candle)
                if actual_candle_fingerprint != entry.last_candle_fingerprint:
                    failures.append('previous_ohlcv_revised')
            except (KeyError, TypeError, ValueError, OverflowError):
                failures.append('previous_candle_invalid')
        if failures:
            changed = sorted(key for key in set(entry.fields) | set(fields or {})
                             if entry.fields.get(key) != (fields or {}).get(key))
            ohlcv_changes = {}
            if 'previous_ohlcv_revised' in failures:
                for key in ('Open', 'High', 'Low', 'Close', 'Volume'):
                    old = entry.last_candle.get(key, entry.last_candle.get(key.lower()))
                    new = previous_candle.get(key, previous_candle.get(key.lower()))
                    if old is None or new is None or float(old) != float(new):
                        ohlcv_changes[key] = [str(old), str(new)]
            log.warning('RUNNER_INCREMENTAL_INVALIDATION_DETAIL deployment=%s failures=%s '
                        'changed_fields=%s old_fingerprint=%s new_fingerprint=%s retained_time=%s '
                        'db_cursor=%s next=%s expected_next=%s interval_s=%s previous_time=%s '
                        'old_ohlcv_hash=%s new_ohlcv_hash=%s ohlcv_changes=%s bars=%s',
                        deployment_id, failures, changed, entry.fingerprint, fingerprint, previous,
                        utc(last_processed), utc(next_candle_time), expected, timeframe_seconds,
                        previous_candle.get('Date', previous_candle.get('candle_time')) if previous_candle else None,
                        entry.last_candle_fingerprint, actual_candle_fingerprint, ohlcv_changes, entry.candle_count)
            self.invalidate(deployment_id, ','.join(failures))
            return None
        if observed_capital is not None and entry.observed_capital != observed_capital:
            log.info('RUNNER_INCREMENTAL_CAPITAL_SNAPSHOT_CHANGED deployment=%s old=%s new=%s '
                     'signal_identity_unchanged=true sizing_uses_current_broker_snapshot=true',
                     deployment_id, entry.observed_capital, observed_capital)
            entry.observed_capital = observed_capital
        return entry

    def prime(self, deployment_id: str, *, fingerprint: str, candle_time: datetime, strategy: Any,
              generated: pd.DataFrame, candle_count: int, latest_candle: dict,
              fields: dict | None = None, observed_capital: str | None = None) -> bool:
        self.invalidate(deployment_id, 'new_cold_warmup')
        try:
            accepted = strategy.start_live_incremental(generated)
            if accepted is not True:
                return False
            if len(self._entries) >= MAX_RETAINED:
                victim = next(iter(self._entries))
                self._entries.pop(victim)
                log.warning('RUNNER_INCREMENTAL_STATE_EVICTED deployment=%s new_deployment=%s '
                            'reason=cache_capacity_%s', victim, deployment_id, MAX_RETAINED)
            self._entries[deployment_id] = RetainedEntry(fingerprint, utc(candle_time), strategy, candle_count,
                candle_fingerprint(latest_candle), dict(fields or {}), dict(latest_candle), observed_capital)
            log.info('RUNNER_INCREMENTAL_PRIMED deployment=%s bars=%s', deployment_id, candle_count)
            return True
        except Exception:
            log.exception('RUNNER_INCREMENTAL_PRIME_FAILED deployment=%s', deployment_id)
            return False

    def advance(self, deployment_id: str, *, fingerprint: str, last_processed: datetime | None,
                next_candle_time: datetime, timeframe_seconds: int, candle: dict,
                previous_candle: dict | None = None) -> tuple[pd.DataFrame, int] | None:
        entry = self.get_for_next_candle(deployment_id, fingerprint=fingerprint,
                                         last_processed=last_processed, next_candle_time=next_candle_time,
                                         timeframe_seconds=timeframe_seconds, previous_candle=previous_candle)
        if entry is None:
            return None
        try:
            result = entry.strategy.on_closed_candle(dict(candle))
            if not isinstance(result, pd.DataFrame) or result.empty:
                raise ValueError('on_closed_candle must return a nonempty DataFrame')
            if 'Date' not in result.columns or utc(pd.Timestamp(result.iloc[-1]['Date']).to_pydatetime()) != utc(next_candle_time):
                raise ValueError('Incremental output must contain the exact requested candle Date')
            entry.candle_time = utc(next_candle_time)
            entry.last_candle_fingerprint = candle_fingerprint(candle)
            entry.last_candle = dict(candle)
            entry.candle_count += 1
            return result, entry.candle_count
        except Exception:
            # The strategy instance may have mutated before throwing. Never retry it.
            self.invalidate(deployment_id, 'update_exception_or_invalid_candle')
            log.exception('RUNNER_INCREMENTAL_UPDATE_FAILED deployment=%s; cold calculation required', deployment_id)
            return None


retained_states = RetainedStateCache()
