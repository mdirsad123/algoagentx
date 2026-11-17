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


def recovery_status_blocks(status, *, now):
    """A dead history worker's RUNNING marker must not permanently wedge a gap.

    Queue lease exceeds Celery's hard time limit. Absence of a start timestamp
    in legacy RUNNING records is conservatively treated as expired; the runner
    advisory lock still prevents overlapping strategy evaluation.
    """
    stage = status.get('status')
    if stage == 'RUNNING':
        return now < float(status.get('started_at') or 0) + 2500
    if stage in {'REQUIRES_ATTENTION', 'RECOVERED'}:
        return True
    if stage == 'RETRYABLE':
        return (int(status.get('attempts') or 0) >= 3
                or now < float(status.get('retry_at') or 0))
    return False


def validate_recovery_state(*, generated, entry, fingerprint, opens, previous):
    dates = tuple(pd.Timestamp(t).to_pydatetime() for t in generated['Date'])
    if (entry is None or entry.fingerprint != fingerprint or entry.candle_time != opens[-1]
            or entry.candle_count != len(generated)
            or tuple(t for t in dates if t > previous) != opens
            or any(a >= b for a, b in zip(dates, dates[1:]))):
        raise ValueError('RECOVERY_STATE_VALIDATION_FAILED')