from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_timeframe_to_seconds(timeframe: str) -> int:
    tf = str(timeframe or '').strip().upper()
    aliases = {
        'M1': 60, '1M': 60,
        'M3': 180, '3M': 180,
        'M5': 300, '5M': 300,
        'M10': 600, '10M': 600,
        'M15': 900, '15M': 900,
        'M30': 1800, '30M': 1800,
        'H1': 3600, '1H': 3600,
        'H4': 14400, '4H': 14400,
        'D1': 86400, '1D': 86400, 'DAY': 86400, 'DAILY': 86400,
    }
    if tf in aliases:
        return aliases[tf]
    raise ValueError(f'Unsupported live runner timeframe: {timeframe}')


def latest_expected_closed_candle_open(now_utc: datetime, timeframe: str) -> datetime:
    """Return the OPEN timestamp of the candle that should already be closed.

    Example for M5:
      now = 21:00:01  -> expected closed candle opened at 20:55:00
      now = 21:04:59  -> expected closed candle opened at 20:55:00
      now = 21:05:00  -> expected closed candle opened at 21:00:00

    LiveMarketCandle.candle_time stores candle OPEN time.
    """
    now = ensure_utc(now_utc) or utc_now()
    seconds = parse_timeframe_to_seconds(timeframe)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = int((now - midnight).total_seconds())
    current_bucket = (elapsed // seconds) * seconds
    expected_open = current_bucket - seconds
    if expected_open < 0:
        expected_open += 86400
        midnight = midnight - timedelta(days=1)
    return midnight + timedelta(seconds=expected_open)

def calculate_next_candle_close(now_utc: datetime, timeframe: str) -> datetime:
    now = ensure_utc(now_utc) or utc_now()
    seconds = parse_timeframe_to_seconds(timeframe)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = int((now - midnight).total_seconds())
    next_elapsed = ((elapsed // seconds) + 1) * seconds
    return midnight + timedelta(seconds=next_elapsed)


def calculate_next_runner_at(now_utc: datetime, timeframe: str, delay_seconds: int | None = 3) -> datetime:
    delay = max(0, int(delay_seconds if delay_seconds is not None else 3))
    return calculate_next_candle_close(now_utc, timeframe) + timedelta(seconds=delay)


def calculate_next_runner_after_candle(
    latest_closed_candle_at: datetime,
    timeframe: str,
    delay_seconds: int | None = 3,
    *,
    now_utc: datetime | None = None,
) -> datetime:
    """Return the wake-up for the candle *after* the one just processed.

    LiveMarketCandle.candle_time stores broker candle OPEN time. If an M5 row
    has candle_time=19:10, that candle closes at 19:15. After processing it,
    the next new closed candle is the 19:15 row, which closes at 19:20. The
    old implementation added only one timeframe and therefore woke again at
    19:15, one full candle too early, creating a retry storm.
    """
    latest_open = ensure_utc(latest_closed_candle_at) or utc_now()
    now = ensure_utc(now_utc) or utc_now()
    seconds = parse_timeframe_to_seconds(timeframe)
    delay = max(0, int(delay_seconds if delay_seconds is not None else 3))
    next_run = latest_open + timedelta(seconds=(seconds * 2) + delay)
    if next_run <= now:
        return calculate_next_runner_at(now, timeframe, delay_seconds)
    return next_run
