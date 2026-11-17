"""Verified TradeLocker session-gap classification; unknown data NEVER authorizes a skip.

A historic candle can be omitted only when the *broker's own* trade-session
calendar describes every missing M5 slot as closed. Session data is fetched
from the authenticated instrument's tradeSessionId and /trade/sessions/{id}.
No fixed XAUUSD/IST weekend/daily schedules are embedded in AlgoAgentX.
"""
from __future__ import annotations

import re
import logging
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
DAY_LOOKUP = {name: i for i, name in enumerate(WEEKDAYS)}
DAY_LOOKUP.update({name[:3]: i for i, name in enumerate(WEEKDAYS)})
logger = logging.getLogger(__name__)
SESSION_FIELDS = ('session_preopen', 'session_beforemarket', 'session_regular',
                  'session_aftermarket', 'session_postclose')


class CalendarIncompatible(ValueError):
    """Only fixed diagnostic codes, never raw broker values or credentials."""


def _native_periods(payload: dict, *, shortened: bool = False):
    """TradeLocker SessionPeriod.sub_type; documented Sun..Sat, shortened day.

    Zero-length entries are placeholders, not 24-hour OPEN declarations.
    PAUSE/CLOSED do not override an overlapping OPEN (conservative union).
    """
    schedule = {day: [] for day in range(7)}
    recognized = False
    for field in SESSION_FIELDS:
        section = payload.get(field)
        if section is None:
            continue
        if not isinstance(section, dict) or not isinstance(section.get('sub_type'), list):
            raise CalendarIncompatible('unsupported_session_period_shape')
        for subtype in section['sub_type']:
            if not isinstance(subtype, dict) or subtype.get('name') not in {'OPEN', 'CLOSED', 'PAUSE'}:
                raise CalendarIncompatible('unsupported_session_subtype')
            times = subtype.get('sessionTime')
            if not isinstance(times, list) or len(times) not in (7, 8):
                raise CalendarIncompatible('session_time_requires_seven_or_eight_days')
            if shortened and len(times) != 8:
                raise CalendarIncompatible('shortened_day_hours_unavailable')
            recognized = True
            for index in range(7):
                item = times[7 if shortened else index]
                if not isinstance(item, dict):
                    raise CalendarIncompatible('invalid_session_time')
                a, b = _minutes(item.get('startTime')), _minutes(item.get('endTime'))
                if a is None or b is None:
                    raise CalendarIncompatible('invalid_session_clock')
                if subtype['name'] == 'OPEN' and a != b:
                    schedule[(index + 6) % 7].append((a, b))
    if not recognized:
        raise CalendarIncompatible('empty_session_calendar')
    return schedule


def _is_native(payload):
    return any(isinstance(payload.get(k), dict) and 'sub_type' in payload[k] for k in SESSION_FIELDS)


def _holiday_day(value):
    if not isinstance(value, str):
        raise CalendarIncompatible('invalid_holiday_date')
    for fmt in ('%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise CalendarIncompatible('invalid_holiday_date')


def _calendar_days(calendar):
    """Return weekly hours and explicit local-date overrides, never infer holidays."""
    weekly = _native_periods(calendar) if _is_native(calendar) else _extract_periods(calendar)
    if weekly is None:
        raise CalendarIncompatible('unsupported_weekly_calendar')
    holidays = calendar.get('holidays') or []
    if not isinstance(holidays, list):
        raise CalendarIncompatible('unsupported_holidays_shape')
    overrides = {}
    seen_states = {}
    for item in holidays:
        if isinstance(item, str):
            day, hours = _holiday_day(item), {d: [] for d in range(7)}
        elif isinstance(item, dict):
            day = _holiday_day(item.get('date'))
            state = item.get('workingState')
            if day in seen_states and seen_states[day] != state:
                raise CalendarIncompatible('conflicting_holiday_overrides')
            seen_states[day] = state
            if state == 'OPEN':
                if any(item.get(k) is not None for k in SESSION_FIELDS):
                    raise CalendarIncompatible('open_holiday_with_override_ambiguous')
                # OPEN means ordinary hours, including previous-day overnight
                # carry. Do not create a date override that removes that carry.
                if day in overrides:
                    raise CalendarIncompatible('conflicting_holiday_overrides')
                continue
            elif state == 'CLOSE':
                hours = {d: [] for d in range(7)}
            elif state == 'SHORTENED_DAY':
                # Partial holidays must supply the documented eighth day, or
                # remain UNKNOWN. Never convert a partial holiday to all-day closed.
                source = item if _is_native(item) else calendar
                hours = _native_periods(source, shortened=True)
            else:
                raise CalendarIncompatible('unsupported_holiday_working_state')
        else:
            raise CalendarIncompatible('invalid_holiday_entry')
        if day in overrides and overrides[day] != hours:
            raise CalendarIncompatible('conflicting_holiday_overrides')
        overrides[day] = hours
    return weekly, overrides


def _zone(value: Any):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value in {'UTC', 'Etc/UTC', 'GMT', 'Z'}:
        return timezone.utc
    # Fixed offsets are supported ONLY when explicitly provided by broker.
    # Prefer IANA regions to preserve broker-local DST transitions.
    m = re.fullmatch(r'(?:UTC|GMT)([+-])(\d{1,2})(?::?(\d{2}))?', value, re.I)
    if m:
        minutes = 60 * int(m.group(2)) + int(m.group(3) or 0)
        if minutes >= 24 * 60 or int(m.group(3) or 0) >= 60:
            return None
        return timezone(timedelta(minutes=minutes * (1 if m.group(1) == '+' else -1)))
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _minutes(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', value.strip())
    if not m:
        return None
    h, minute, sec = map(int, (m.group(1), m.group(2), m.group(3) or 0))
    if h == 24 and minute == sec == 0:
        return 1440
    if h >= 24 or minute >= 60 or sec >= 60:
        return None
    # Trading session has minute precision; do not truncate seconds and risk a false closure.
    if sec:
        return None
    return h * 60 + minute


def _parse_day(value: Any) -> int | None:
    if isinstance(value, str):
        key = value.strip().lower()
        if key in DAY_LOOKUP:
            return DAY_LOOKUP[key]
        if key.isdigit():
            value = int(key)
        else:
            return None
    # ISO weekday 1(Mon)-7(Sun) in a structured broker period.
    if isinstance(value, int) and 1 <= value <= 7:
        return value - 1
    return None


def _period(item: dict) -> tuple[int, int] | None:
    start = next((item[k] for k in ('startTime', 'start', 'from', 'open', 'openTime') if k in item), None)
    end = next((item[k] for k in ('endTime', 'end', 'to', 'close', 'closeTime') if k in item), None)
    a, b = _minutes(start), _minutes(end)
    return (a, b) if a is not None and b is not None and a != b else None


def _extract_periods(payload: dict[str, Any]) -> dict[int, list[tuple[int, int]]] | None:
    """Accept explicit weekday calendars only. Unknown sections fail closed."""
    schedule: dict[int, list[tuple[int, int]]] = {x: [] for x in range(7)}
    recognized = False
    for key in ('session_preopen', 'session_beforemarket', 'session_regular',
                'session_aftermarket', 'session_postclose'):
        raw = payload.get(key)
        if raw in (None, [], {}):
            continue
        if isinstance(raw, dict):
            day_keys = [(key_name, entries) for key_name, entries in raw.items()
                        if isinstance(key_name, str) and key_name.lower() in DAY_LOOKUP]
            if day_keys:
                if len(day_keys) != len(raw):
                    return None
                for day_name, entries in day_keys:
                    recognized = True
                    day = DAY_LOOKUP[day_name.lower()]
                    if isinstance(entries, dict):
                        entries = [entries]
                    if not isinstance(entries, list):
                        return None
                    for item in entries:
                        if not isinstance(item, dict) or (period := _period(item)) is None:
                            return None
                        schedule[day].append(period)
                continue
            raw = raw.get('periods')
            if not isinstance(raw, list):
                return None
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    return None
                day = _parse_day(item.get('dayOfWeek', item.get('weekday', item.get('day'))))
                if day is None or (period := _period(item)) is None:
                    return None
                schedule[day].append(period)
                recognized = True
        else:
            return None
    return schedule if recognized else None


def _holiday_dates(payload: dict[str, Any]) -> set[date] | None:
    raw = payload.get('holidays')
    if raw in (None, [], {}):
        return set()
    if not isinstance(raw, list):
        return None
    result = set()
    for item in raw:
        if isinstance(item, str):
            val = item
        elif isinstance(item, dict) and isinstance(item.get('date'), str):
            # Don't interpret partial-session holidays as all-day closures.
            if any(key in item for key in ('open', 'close', 'start', 'end', 'from', 'to', 'periods')):
                return None
            val = item['date']
        else:
            return None
        try:
            result.add(date.fromisoformat(val[:10]))
        except (ValueError, TypeError):
            return None
    return result


def classify_missing_slots(*, calendar: dict[str, Any], missing_open: datetime,
                           first_pending: datetime, timeframe_seconds: int = 300) -> str:
    """CLOSED, OPEN, UNKNOWN. Classification is strict and read-only."""
    tz = _zone(calendar.get('timeZone'))
    try:
        periods, overrides = _calendar_days(calendar)
    except CalendarIncompatible as exc:
        logger.warning('BROKER_SESSION_UNKNOWN reason=%s', exc)
        return 'UNKNOWN'
    if tz is None or timeframe_seconds < 60 or timeframe_seconds % 60:
        logger.warning('BROKER_SESSION_UNKNOWN reason=invalid_timezone_or_timeframe')
        return 'UNKNOWN'
    if calendar.get('blockTrading') is not False:
        # A current administrative trading block is not historic market closure.
        logger.warning('BROKER_SESSION_UNKNOWN reason=administrative_block_or_missing_flag')
        return 'UNKNOWN'
    if missing_open.tzinfo is None or first_pending.tzinfo is None:
        return 'UNKNOWN'
    start = missing_open.astimezone(timezone.utc)
    end = first_pending.astimezone(timezone.utc)
    if end <= start or (end - start).total_seconds() > 7 * 86400:
        return 'UNKNOWN'
    if (start.timestamp() % timeframe_seconds or end.timestamp() % timeframe_seconds):
        return 'UNKNOWN'
    # A slot is considered open if even one minute of its actual time range
    # intersects an eligible trading window. This is deliberately conservative.
    slot = start
    while slot < end:
        minute = slot
        while minute < slot + timedelta(seconds=timeframe_seconds):
            local = minute.astimezone(tz)
            minute_of_day = local.hour * 60 + local.minute
            today = local.weekday()
            yesterday = (today - 1) % 7
            current = overrides.get(local.date(), periods)
            prior = overrides.get(local.date() - timedelta(days=1), periods)
            active = any(a <= minute_of_day < b for a, b in current[today] if a < b)
            active |= any(minute_of_day >= a for a, b in current[today] if a > b)
            # A date-specific override replaces the entire local day.
            if local.date() not in overrides:
                active |= any(minute_of_day < b for a, b in prior[yesterday] if a > b)
            if active:
                return 'OPEN'
            minute += timedelta(minutes=1)
        slot += timedelta(seconds=timeframe_seconds)
    return 'CLOSED'


async def verified_tradelocker_gap_status(adapter, symbol: str, missing_open: datetime,
                                           first_pending: datetime, *, timeframe_seconds: int = 300) -> str:
    """Read broker-owned metadata, never infer market closure from absent bars."""
    calendar = await fetch_tradelocker_calendar(adapter, symbol)
    if calendar is None:
        return 'UNKNOWN'
    return classify_missing_slots(calendar=calendar, missing_open=missing_open,
                                  first_pending=first_pending, timeframe_seconds=timeframe_seconds)


async def fetch_tradelocker_calendar(adapter, symbol: str) -> dict | None:
    stage, instrument_id, trade_route, session_id = 'instrument', None, None, None
    try:
        info = await adapter._instrument(symbol)
        instrument_id = info.get('tradableInstrumentId')
        routes = info.get('routes') or []
        trade_route = next((item.get('id', item.get('routeId')) for item in routes
                            if isinstance(item, dict) and str(item.get('type') or item.get('routeType') or item.get('name') or '').upper() == 'TRADE'), None)
        if instrument_id is None or trade_route is None:
            raise CalendarIncompatible('instrument_or_trade_route_missing')
        stage = 'instrument_details'
        details = await adapter._request('GET', f'/trade/instruments/{instrument_id}',
                                         params={'routeId': trade_route})
        session_id = (details.get('d') or {}).get('tradeSessionId')
        if session_id is None:
            raise CalendarIncompatible('trade_session_id_missing')
        stage = 'session'
        session = await adapter._request('GET', f'/trade/sessions/{session_id}')
        calendar = session.get('d') or {}
        if not isinstance(calendar, dict) or calendar.get('blockTrading') is None:
            raise CalendarIncompatible('session_payload_missing_required_fields')
        _calendar_days(calendar)
        if calendar.get('blockTrading') is not False:
            raise CalendarIncompatible('administrative_block_not_historical_closure')
        if _zone(calendar.get('timeZone')) is None:
            raise CalendarIncompatible('unsupported_broker_timezone')
        digest = hashlib.sha256(json.dumps(calendar, sort_keys=True).encode()).hexdigest()
        logger.info('BROKER_SESSION_LOADED instrument=%s route=%s session=%s timezone=%s schema=%s sha256=%s',
                    instrument_id, trade_route, session_id, calendar.get('timeZone'),
                    'sub_type' if _is_native(calendar) else 'weekday', digest)
        return calendar
    except Exception as exc:
        # Never emit exception text/HTTP bodies: they can include authentication data.
        reason = str(exc) if isinstance(exc, CalendarIncompatible) else 'broker_metadata_request_failed'
        status = re.search(r'HTTP (\d{3})', str(exc))
        logger.warning('BROKER_SESSION_UNKNOWN stage=%s reason=%s error_type=%s http_status=%s '
                       'instrument=%s route=%s session=%s', stage, reason, type(exc).__name__,
                       status.group(1) if status else None, instrument_id, trade_route, session_id)
        return None
