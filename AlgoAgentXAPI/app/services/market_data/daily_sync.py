"""Read-only, account-scoped historical candle sync; intentionally isolated from live trading."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import (
    BrokerAccount, Instrument, MarketData, MarketDataFeedCandle, MarketDataSyncConfig, MarketDataSyncRun
)
from ...services.market_data.normalizer import normalize_candles
from ...services.market_data.validator import validate_and_prepare_candles

logger = logging.getLogger(__name__)
TIMEFRAMES = {"1m": ("M1", 1), "2m": ("M2", 2), "3m": ("M3", 3), "4m": ("M4", 4), "5m": ("M5", 5), "10m": ("M10", 10), "15m": ("M15", 15), "30m": ("M30", 30), "1h": ("H1", 60), "4h": ("H4", 240), "12h": ("H12", 720), "1d": ("D1", 1440)}
HISTORY_CODES = {"CTRADER", "CTRADER_API", "TRADELOCKER"}


def get_broker_code(account) -> str:
    provider = getattr(account, "broker_provider", None)
    return str(getattr(provider, "code", None) or getattr(account, "broker_code", None) or
               getattr(account, "broker_name", None) or "MT5").upper().strip()


def enabled_globally() -> bool:
    return os.getenv("MARKET_DATA_DAILY_SYNC_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def next_daily_run(now=None) -> str:
    tz = ZoneInfo(os.getenv("MARKET_DATA_SYNC_TIMEZONE", "Asia/Kolkata"))
    local = (now or datetime.now(timezone.utc)).astimezone(tz)
    hour, minute = [int(x) for x in os.getenv("MARKET_DATA_SYNC_LOCAL_TIME", "03:00").split(":")]
    next_at = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_at <= local:
        next_at += timedelta(days=1)
    return next_at.isoformat()


class HistoryFetchError(RuntimeError):
    """Credential-free stage and diagnostic code for admin history failures."""

    def __init__(self, stage: str, code: str, hint: str):
        super().__init__(f"{code}: {hint}")
        self.stage, self.code, self.hint = stage, code, hint


def safe_error(exc: Exception) -> tuple[str, str]:
    """Structured, actionable errors without storing broker exception bodies or URLs."""
    original = getattr(exc, "orig", exc)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if sqlstate == "42P01":
        return "FAILED", "DB_SCHEMA_MISSING: Required history/provenance table missing; apply the V5 market data migration"
    if sqlstate == "42703":
        return "FAILED", "DB_SCHEMA_MISSING: Required history/provenance column missing; check V5 migration"
    if sqlstate == "23503":
        return "FAILED", "DB_FOREIGN_KEY: Feed/instrument reference is inconsistent; check source config and migration"
    if isinstance(exc, HistoryFetchError):
        status = ("AUTH_EXPIRED" if exc.code in {"CTRADER_AUTH", "BROKER_AUTH"}
                  else "UNSUPPORTED" if exc.code in {"BROKER_UNSUPPORTED", "TIMEFRAME_UNSUPPORTED"}
                  else "PARTIAL" if exc.code == "BROKER_RATE_LIMIT" else "FAILED")
        return status, f"{exc.stage}: {exc.code} - {exc.hint}"[:300]
    message = str(exc).lower()
    if any(x in message for x in ("token", "unauthorized", "401", "403", "expired", "invalid_grant")):
        return "AUTH_EXPIRED", "BROKER_AUTH: Broker token expired/rejected; reconnect the selected account"
    if "agent" in message or "terminal" in message:
        return "AGENT_OFFLINE", "AGENT_OFFLINE: Broker agent/terminal is offline"
    if "unsupported" in message:
        return "UNSUPPORTED", "BROKER_UNSUPPORTED: Provider or timeframe unsupported"
    if "rate limit" in message or "429" in message or "too many requests" in message:
        return "PARTIAL", "BROKER_RATE_LIMIT: Broker rate limit; retry after cooldown"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timed out" in message or "timeout" in message:
        return "FAILED", "BROKER_TIMEOUT: cTrader history request timed out; check network access from history worker"
    if isinstance(exc, socket.gaierror) or "name resolution" in message or "getaddrinfo" in message:
        return "FAILED", "BROKER_DNS: History worker cannot resolve broker API host"
    if isinstance(exc, (ConnectionError, OSError)) or "connection refused" in message or "websocket" in message:
        return "FAILED", "BROKER_CONNECTION: History worker cannot connect to broker API"
    if "symbol" in message or "instrument" in message:
        return "FAILED", "BROKER_SYMBOL: Check exact symbol mapping in the selected broker subaccount"
    return "FAILED", f"HISTORY_INTERNAL: Worker {type(exc).__name__}; inspect server's sanitized stage logs"


def _history_failure(stage: str, exc: Exception) -> HistoryFetchError:
    """Produce a broker-safe stage code. Never copy raw upstream errors or URLs."""
    _, message = safe_error(exc)
    code, _, hint = message.partition(": ")
    if not hint:
        code, hint = "HISTORY_INTERNAL", f"{type(exc).__name__}; check worker diagnostics"
    return HistoryFetchError(stage, code, hint)


def subaccounts(account: BrokerAccount) -> list[dict]:
    """Only persisted, provider-discovered account ids; never infer IDs from UI input."""
    code = get_broker_code(account)
    meta = account.metadata_json or {}
    if code in {"CTRADER", "CTRADER_API"}:
        rows = meta.get("ctrader_accounts") or []
        selected = meta.get("ctrader_selected_account") or {}
        if not rows and selected:
            rows = [selected]
        result = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            key = item.get("ctrader_account_id") or item.get("account_number")
            if key is None:
                continue
            result.append({"id": str(key), "label": f"cTrader •••{str(key)[-4:]}", "environment": "LIVE" if item.get("is_live") or str(item.get("account_type", "")).upper() == "LIVE" else "DEMO"})
        return result
    if code == "TRADELOCKER":
        key = meta.get("tradelocker_account_id")
        if key and meta.get("tradelocker_acc_num") is not None:
            return [{"id": str(key), "label": f"TradeLocker •••{str(key)[-4:]}", "environment": str(meta.get("tradelocker_environment") or account.mode).upper()}]
        return []
    return [{"id": str(account.login_id or account.id), "label": f"{code} •••{str(account.login_id or account.id)[-4:]}", "environment": account.mode}]


def verify_source(account: BrokerAccount, *, subaccount_id: str, provider: str):
    actual = get_broker_code(account)
    if actual == "CTRADER_API":
        actual = "CTRADER"
    if provider == "CTRADER_API":
        provider = "CTRADER"
    if actual != provider:
        raise ValueError("Provider does not match the connected broker account")
    if str(account.status).upper() != "CONNECTED" or (account.broker_provider and not account.broker_provider.is_enabled):
        raise ValueError("Broker account is not connected or provider is disabled")
    available = subaccounts(account)
    if subaccount_id not in [row["id"] for row in available]:
        raise ValueError("Subaccount was not discovered on the selected connected broker")
    if provider in {"CTRADER", "TRADELOCKER"} and not available:
        raise ValueError("Select/sync a trading subaccount in Broker Connections first")
    return next(x for x in available if x["id"] == subaccount_id)


def _clone_account(account: BrokerAccount, subaccount_id: str):
    """An in-memory snapshot: switching cTrader subaccount must never change live-trade selection."""
    values = {c.name: getattr(account, c.name) for c in BrokerAccount.__table__.columns}
    values["broker_provider"] = account.broker_provider
    if get_broker_code(account) in {"CTRADER", "CTRADER_API"}:
        meta = dict(account.metadata_json or {})
        matches = [row for row in (meta.get("ctrader_accounts") or [meta.get("ctrader_selected_account") or {}])
                   if isinstance(row, dict) and str(row.get("ctrader_account_id") or row.get("account_number")) == subaccount_id]
        if len(matches) != 1:
            raise ValueError("cTrader subaccount selection is missing or ambiguous")
        existing = meta.get("ctrader_selected_account") or {}
        meta["ctrader_selected_account"] = matches[0]
        # Cached symbol previews belong to the old selected cTrader account.
        # Never reuse a different subaccount's symbol IDs for research imports.
        if str(existing.get("ctrader_account_id") or existing.get("account_number")) != subaccount_id:
            meta.pop("ctrader_symbols_preview", None)
        values["metadata_json"] = meta
    return SimpleNamespace(**values)



async def broker_symbol_catalog(db: AsyncSession, account: BrokerAccount, subaccount_id: str) -> list[dict]:
    """Provider-authoritative, exact symbols for ONE authorized trading subaccount.

    Only used by admin history configuration, never changes the live account selection.
    """
    provider = get_broker_code(account).replace("CTRADER_API", "CTRADER")
    if provider not in {"CTRADER", "TRADELOCKER"}:
        raise ValueError("Historical broker symbol discovery is not supported for this provider")
    verify_source(account, subaccount_id=subaccount_id, provider=provider)
    if provider == "CTRADER":
        from ...api.v1.broker_accounts import _refresh_ctrader_token_if_needed
        await _refresh_ctrader_token_if_needed(account, db)
    from ...services.brokers.factory import get_broker_adapter
    adapter = get_broker_adapter(_clone_account(account, subaccount_id), db)
    if provider == "CTRADER":
        raw = await adapter.fetch_symbols(subaccount_id, 2000)
    else:
        raw = await adapter.get_symbols(limit=2000)
    result = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("symbol_name") or item.get("symbol") or item.get("trading_symbol") or "").strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        raw_meta = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        description = str(item.get("description") or raw_meta.get("description") or "")[:140]
        result.append({"symbol": name, "symbol_id": str(item.get("symbol_id") or item.get("instrument_key") or ""),
                       "description": description})
    return result


def broker_exact_match(rows: list[dict], requested: str) -> str | None:
    """Never translate MT5 suffixes by assumption: exact provider list is the truth."""
    return next((row["symbol"] for row in rows if row["symbol"].casefold() == requested.strip().casefold()), None)

def last_expected_closed(now: datetime, timeframe: str) -> datetime:
    _, minutes = TIMEFRAMES[timeframe]
    # UTC candle OPEN only; never persist the forming candle.
    seconds = minutes * 60
    return datetime.fromtimestamp(int(now.timestamp()) // seconds * seconds - seconds, tz=timezone.utc)


async def fetch_window(db: AsyncSession, account: BrokerAccount, config: MarketDataSyncConfig, *, start: datetime, end: datetime) -> list[dict]:
    """Fetch a bounded wall-clock window, not an unrestricted full broker history."""
    code = get_broker_code(account)
    if code not in HISTORY_CODES:
        raise ValueError("Unsupported broker history adapter for daily sync")
    verify_source(account, subaccount_id=config.subaccount_id, provider=config.provider)
    if config.timeframe not in TIMEFRAMES:
        raise ValueError("Unsupported timeframe")
    native, minutes = TIMEFRAMES[config.timeframe]
    # Import the provider only inside the worker, never on admin API startup.
    from ...services.brokers.factory import get_broker_adapter
    adapter = get_broker_adapter(_clone_account(account, config.subaccount_id), db)
    # Validate the symbol against the selected account only, before retrieving bars.
    if not getattr(config, "_history_symbol_verified", False):
        try:
            instrument_meta = None
            if code in {"CTRADER", "CTRADER_API"} and hasattr(adapter, "_resolve_symbol_meta"):
                instrument_meta = await adapter._resolve_symbol_meta(config.broker_symbol)
                actual_symbol = str(instrument_meta.get("symbol_name") or instrument_meta.get("trading_symbol")
                                    or instrument_meta.get("symbol") or instrument_meta.get("name") or "")
                if actual_symbol.strip().casefold() != config.broker_symbol.strip().casefold():
                    # Cached preview / fuzzy resolution can belong to an older account
                    # selection or match XAUUSDm instead of XAUUSD. Ask THIS subaccount's
                    # live symbol list and only accept an exact provider symbol.
                    live_rows = await adapter.fetch_symbols(config.subaccount_id, 2000)
                    instrument_meta = next((item for item in live_rows
                        if str(item.get("symbol_name") or item.get("symbol") or "").strip().casefold()
                        == config.broker_symbol.strip().casefold()), None)
                    actual_symbol = str((instrument_meta or {}).get("symbol_name") or "")
            elif code == "TRADELOCKER" and hasattr(adapter, "_instrument"):
                instrument_meta = await adapter._instrument(config.broker_symbol)
                actual_symbol = str(instrument_meta.get("name") or instrument_meta.get("symbol") or "")
            else:
                actual_symbol = config.broker_symbol
            if actual_symbol.strip().casefold() != config.broker_symbol.strip().casefold():
                raise HistoryFetchError("resolve-symbol", "BROKER_SYMBOL", "Choose the exact symbol shown for this trading subaccount")
            config._history_symbol_verified = True
            if code in {"CTRADER", "CTRADER_API"} and instrument_meta is not None:
                config._history_symbol_meta = instrument_meta
        except HistoryFetchError:
            raise
        except Exception as exc:
            raise _history_failure("resolve-symbol", exc) from None
    # Use an exact UTC range for history instead of asking the live warmup adapter
    # for an unrestricted backwards-count and then throwing away out-of-range bars.
    count = min(6000, max(10, int((end - start).total_seconds() / (minutes * 60)) + 10))
    try:
        if code in {"CTRADER", "CTRADER_API"} and hasattr(adapter, "get_rates_history_window"):
            rows = await adapter.get_rates_history_window(config.broker_symbol, native, start=start, end=end,
                                                         symbol_meta=getattr(config, "_history_symbol_meta", None))
        else:
            rows = await adapter.get_rates_history(config.broker_symbol, native, count=count, before=end)
    except Exception as exc:
        raise _history_failure("fetch-candles", exc) from None
    if not isinstance(rows, list):
        raise HistoryFetchError("fetch-candles", "BROKER_PAYLOAD", "Broker returned an invalid candle response")
    return [row for row in rows if start <= _row_time(row) < end]


def _row_time(row) -> datetime:
    value = row.get("candle_time") or row.get("timestamp")
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("Provider supplied a candle without a timestamp")
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def run_sync(db: AsyncSession, config: MarketDataSyncConfig, run: MarketDataSyncRun):
    """Caller owns the run lease. Commit each small page so interrupted work is resumable."""
    account = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == config.broker_account_id))).scalar_one()
    verify_source(account, subaccount_id=config.subaccount_id, provider=config.provider)
    if get_broker_code(account) in {"CTRADER", "CTRADER_API"}:
        # cTrader OAuth access tokens can expire between daily runs. Refresh only the
        # exact account's credentials using the existing secure backend path.
        from ...api.v1.broker_accounts import _refresh_ctrader_token_if_needed
        await _refresh_ctrader_token_if_needed(account, db)
    if get_broker_code(account) not in HISTORY_CODES:
        return "UNSUPPORTED"
    now = datetime.now(timezone.utc)
    expected = last_expected_closed(now, config.timeframe)
    interval = timedelta(minutes=TIMEFRAMES[config.timeframe][1])
    latest = (await db.execute(select(func.max(MarketDataFeedCandle.timestamp)).where(MarketDataFeedCandle.feed_id == config.id))).scalar_one()
    run.last_before = latest
    manual = bool(run.requested_start and run.requested_end)
    if not manual and latest is None and config.initial_start is None:
        return "NEEDS_INITIAL_IMPORT"
    if manual:
        cursor = run.requested_start
        expected = min(expected, run.requested_end - interval)
    elif latest is not None:
        cursor = latest - interval * 2
    else:
        cursor = config.initial_start
    if cursor.tzinfo is None:
        cursor = cursor.replace(tzinfo=timezone.utc)
    # A single history task cannot monopolize CPU/API for arbitrarily many missing years.
    limit = (max(1, min(int(os.getenv("MARKET_DATA_SYNC_MANUAL_MAX_WINDOWS", "60")), 120)) if manual
             else max(1, min(int(os.getenv("MARKET_DATA_SYNC_MAX_WINDOWS", "15")), 60)))
    windows = 0
    saw_rows = False
    unverified_gap = False
    watermark = latest
    while cursor <= expected and windows < limit:
        windows += 1
        end = min(cursor + timedelta(days=2), expected + interval)
        rows = await fetch_window(db, account, config, start=cursor, end=end)
        normalized, errors, total = normalize_candles(rows)
        prepared, summary = validate_and_prepare_candles(normalized, total_input_rows=total, normalize_errors=errors)
        # Drop incomplete/future/misaligned bars even if the provider returned them.
        safe_rows = [c for c in prepared if c.timestamp + interval <= now and c.timestamp <= expected and
                     (TIMEFRAMES[config.timeframe][1] >= 1440 or int(c.timestamp.timestamp()) % int(interval.total_seconds()) == 0) and
                     c.open > 0 and c.low > 0]
        run.fetched += len(rows)
        if not safe_rows and cursor < expected and cursor.weekday() < 5:
            # A 2-day weekday no-data window might be a session break or provider outage.
            # Do not call the history fully verified; the admin can explicitly repair it.
            unverified_gap = True
        run.invalid += summary.invalid_rows + len(prepared) - len(safe_rows)
        run.skipped += summary.duplicate_rows
        if safe_rows:
            saw_rows = True
            if run.dry_run:
                run.skipped += len(safe_rows)
                run.last_after = max(c.timestamp for c in safe_rows)
                cursor = end
                continue
            values = [{"feed_id": config.id, "timestamp": c.timestamp, "open": c.open,
                       "high": c.high, "low": c.low, "close": c.close, "volume": c.volume} for c in safe_rows]
            # Source feed uses DO NOTHING on overlaps; existing OHLCV always wins.
            stmt = pg_insert(MarketDataFeedCandle.__table__).values(values).on_conflict_do_nothing(
                index_elements=["feed_id", "timestamp"])
            result = await db.execute(stmt)
            run.inserted += max(0, int(result.rowcount or 0))
            run.skipped += len(values) - max(0, int(result.rowcount or 0))
            newest = max(c.timestamp for c in safe_rows)
            if watermark is None or newest > watermark:
                watermark = newest
            # After explicit admin approval, publish only absent canonical timestamps.
            # Existing MT5/OHLCV is immutable on overlap. Provenance is retained per insert.
            if config.is_primary and config.publish_approved and not config.is_archived:
                from .feed_publish import publish_selected_candles
                run.updated += await publish_selected_candles(db, config, [c.timestamp for c in safe_rows])
            run.last_after = watermark
            config.checkpoint = watermark
            await db.commit()
        if end <= cursor:
            raise RuntimeError("History cursor did not advance")
        cursor = end
        # Avoid a burst of 100s requests for cTrader/tradelocker, even with one worker.
        if cursor <= expected:
            await asyncio.sleep(max(0.0, float(os.getenv("MARKET_DATA_SYNC_PAGE_DELAY_SECONDS", "0.6"))))
    if not run.dry_run:
        config.last_synced_at = datetime.now(timezone.utc)
    if cursor <= expected or (unverified_gap and not manual):
        return "PARTIAL"
    if not saw_rows:
        return "NO_NEW_CANDLE"
    if run.dry_run:
        return "PREVIEW"
    if manual:
        return "UP_TO_DATE"
    return "UP_TO_DATE" if watermark and watermark >= expected - interval * 3 else "PARTIAL"
