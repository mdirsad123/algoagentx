"""Pure recovery validation. No broker writes, cursor updates or invented bars."""
from datetime import timedelta, timezone

from .broker_session_gap import classify_missing_slots
from .retained_strategy_state import canonical_candle
import pandas as pd


def validate_recovery_candles(*, candles, cursor, target, calendar, now, step=300):
    """Validate EVERY real row and gap before permitting a cold history replay.

    Return real timestamps only. The runner must use this same sequence and
    validate its generated state before committing the target cursor.
    """
    if step != 300 or any(t.tzinfo is None for t in (cursor, target, now)):
        raise ValueError('invalid_recovery_clock')
    if target <= cursor or target + timedelta(seconds=step) > now:
        raise ValueError('recovery_target_not_closed')
    previous, opens = cursor, []
    for row in candles:
        bar = canonical_candle(row)
        if (bar['Low'] > min(bar['Open'], bar['Close'])
                or bar['High'] < max(bar['Open'], bar['Close'])
                or bar['Low'] > bar['High'] or bar['Volume'] < 0):
            raise ValueError('recovery_invalid_ohlcv')
        current = bar['Date'].astimezone(timezone.utc)
        if (str(row.get('source', '')).upper() != 'TRADELOCKER'
                or row.get('is_closed') is not True):
            raise ValueError('recovery_requires_real_closed_broker_candles')
        if current <= previous or current.timestamp() % step or current > target:
            raise ValueError('recovery_candles_not_strictly_ordered')
        expected = previous + timedelta(seconds=step)
        if current != expected:
            status = classify_missing_slots(calendar=calendar, missing_open=expected,
                                            first_pending=current, timeframe_seconds=step)
            if status != 'CLOSED':
                raise ValueError(f'recovery_gap_{status.lower()}:{expected.isoformat()}')
        opens.append(current)
        previous = current
    if not opens or opens[-1] != target:
        raise ValueError('recovery_target_missing')
    return tuple(opens)


# A broker calendar read, advisory-lock conflict, or infrastructure timeout is
# not evidence of invalid market history. These may be retried after a durable
# cooldown. Parity, history validation, source pinning, and prime failures MUST
# remain operator-held. In particular, no retry changes a deployment cursor or
# sends an order: the queued worker independently re-verifies the broker session
# and runs with historical orders suppressed.
TRANSIENT_RECOVERY_REASONS = frozenset({
    'broker_session_unknown', 'LOCK_SKIPPED', 'TimeoutError',
    'ConnectionError', 'OSError', 'OperationalError', 'InterfaceError',
})


def recovery_retry_delay_seconds(attempts: int) -> int:
    """Broker-metadata retries only; independent of the 3-history-fetch cap."""
    return min(1800, 300 * (2 ** min(max(0, int(attempts) - 1), 3)))


def recovery_status_blocks(status, *, now):
    """Respect in-flight locks and fail-closed checks; heal only transient stalls.

    Legacy celery tasks could persist REQUIRES_ATTENTION after a third 429/
    unknown-calendar attempt. That stranded even a newly broker-confirmed
    CLOSED NAS100 session. Those known transient statuses now re-arm after
    a cooldown, but any invalid source/state/parity outcome stays blocked.
    The caller must verify the CLOSED session before it may queue again.
    """
    stage = str(status.get('status') or '')
    reason = str(status.get('reason') or '')
    started = float(status.get('started_at') or 0)
    retry_at = float(status.get('retry_at') or 0)
    attempts = int(status.get('attempts') or 0)
    if stage == 'RUNNING':
        return now < started + 2500
    if stage == 'RECOVERED':
        # The scheduler checks the actual database cursor separately. Never
        # replay a task whose successful commit might already have happened.
        return True
    if stage == 'REQUIRES_ATTENTION':
        if reason in TRANSIENT_RECOVERY_REASONS:
            return now < (retry_at or (started + 2500))
        return True
    if stage == 'RETRYABLE':
        if reason and reason not in TRANSIENT_RECOVERY_REASONS:
            return True
        # Support legacy RETRYABLE hashes without retry_at: a 3-attempt cap
        # formerly indicated terminal attention. New task writes retry_at.
        if not retry_at and attempts >= 3:
            return True
        return now < retry_at
    return False


def validate_recovery_state(*, generated, entry, fingerprint, opens, previous):
    dates = tuple(pd.Timestamp(t).to_pydatetime() for t in generated['Date'])
    if (entry is None or entry.fingerprint != fingerprint or entry.candle_time != opens[-1]
            or entry.candle_count != len(generated)
            or tuple(t for t in dates if t > previous) != opens
            or any(a >= b for a, b in zip(dates, dates[1:]))):
        raise ValueError('RECOVERY_STATE_VALIDATION_FAILED')