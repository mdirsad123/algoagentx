from __future__ import annotations

import logging
import secrets
from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount, BrokerInstrument, BrokerOrderEvent, LiveEquityPoint, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyDeployment
from ...db.models.instruments import Instrument
from ...schemas.live_trading import BrokerOrderEventOut, LiveOrderOut, LivePositionOut, LiveSignalOut, LiveTradeLogOut, ManualDeploymentSignalIn, RunStrategyOnceIn, StrategyDeploymentCreate, StrategyDeploymentOut, StrategyDeploymentUpdate
from ...services.brokers.factory import get_broker_adapter, get_broker_code
from ...services.live.execution_engine import execute_signal
from ...services.live.pnl_service import to_decimal
from ...services.live.capital_service import get_effective_trading_capital
from ...services.live.live_approval_service import check_broker_deployment_approval, enforce_approval_limits
from ...services.live.broker_candle_service import get_candle_snapshot, refresh_deployment_candles
from ...services.live.strategy_runner import run_strategy_for_deployment, run_full_dry_test_for_deployment
from ...services.live.compatibility_service import run_live_compatibility_check, compatibility_failed
from ...services.live.auto_runner_service import run_deployment_if_due
from ...services.live.broker_sync_service import clamp_live_sync_interval, sync_deployment_broker_state
from ...services.live.trading_safety import check_platform_mode_allowed, get_platform_trading_settings, mark_heartbeat
from ...services.live_trading.readiness_service import build_live_deployment_readiness
from ...services.live_trading.paper_position_manager import process_paper_positions_for_deployment
from ...services.live_trading.final_qa_service import build_final_live_qa, run_paper_order_test, run_demo_micro_order_test
from ...services.billing.live_subscription_gate import build_live_trading_access_status, require_active_subscription_for_live_trading
from ...utils.api_response import success_response
from .live_common import (
    dump_list,
    dump_one,
    get_broker_account_or_404,
    get_deployment_or_404,
    get_deployable_strategy_or_400,
    get_published_strategy_or_400,
    is_admin,
    update_from_payload,
    user_id_from,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class LiveSyncSettingsIn(BaseModel):
    interval_seconds: int | None = Field(default=None, ge=1, le=3600)

class QaOrderTestIn(BaseModel):
    side: str | None = Field(default="BUY")
    confirm_demo_micro_order: bool | None = Field(default=False)



def _ensure_tradingview_secret(row: StrategyDeployment) -> None:
    if not row.tradingview_secret:
        row.tradingview_secret = secrets.token_urlsafe(32)


def _dec(value: object, default: str = "0") -> Decimal:
    return to_decimal(value, default)


def _as_money(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return _dec(value)


def _broker_safe(row: BrokerAccount | None) -> dict | None:
    if row is None:
        return None
    meta = row.metadata_json or {}
    last_test = meta.get("last_test") if isinstance(meta, dict) else {}
    if not isinstance(last_test, dict):
        last_test = {}
    return {
        "id": str(row.id),
        "broker_account_id": str(row.id),
        "broker_name": row.broker_name,
        "account_label": row.account_label,
        "mode": row.mode,
        "status": row.status,
        "login_id": row.login_id,
        "server_name": row.server_name or last_test.get("server"),
        "balance": _as_money(last_test.get("balance")),
        "equity": _as_money(last_test.get("equity")),
        "currency": last_test.get("currency"),
        "last_connected_at": row.last_connected_at,
        "broker_code": row.broker_code,
        "selected_account": _selected_ctrader_account(row),
    }




async def _deployment_currency(db: AsyncSession, row: StrategyDeployment, broker: dict | None) -> str:
    broker_currency = broker.get("currency") if isinstance(broker, dict) else None
    if broker_currency:
        return str(broker_currency).upper()

    instrument_row = (await db.execute(
        select(Instrument.account_currency)
        .where(Instrument.symbol == row.instrument)
        .order_by(Instrument.is_active.desc(), Instrument.updated_at.desc().nullslast())
        .limit(1)
    )).scalar_one_or_none()
    if instrument_row:
        return str(instrument_row).upper()

    for attr in ("account_currency", "currency"):
        value = getattr(row, attr, None)
        if value:
            return str(value).upper()
    return "USD"

def _selected_ctrader_account(row: BrokerAccount | None) -> dict | None:
    meta = getattr(row, "metadata_json", None) or {}
    selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
    return selected if isinstance(selected, dict) else None

def _is_ctrader(row: BrokerAccount | None) -> bool:
    return str((getattr(row, "broker_code", None) or getattr(row, "broker_name", None) or "")).upper() in {"CTRADER", "CTRADER_API"}


def _broker_code_value(row: BrokerAccount | None) -> str:
    return str((getattr(row, "broker_code", None) or getattr(row, "broker_name", None) or "")).upper()


def _is_upstox(row: BrokerAccount | None) -> bool:
    return _broker_code_value(row) == "UPSTOX"


def _is_indian_market(instrument_row: Instrument | None, exchange: str | None = None, segment: str | None = None) -> bool:
    values = [exchange, segment]
    if instrument_row is not None:
        values.extend([instrument_row.exchange, instrument_row.market, instrument_row.asset_class, instrument_row.instrument_type])
    return any("INDIAN" in str(v or "").upper() or str(v or "").upper() in {"NSE", "NSE_EQ", "NSE_FO", "BSE", "BSE_EQ"} for v in values)


async def _instrument_row_for_symbol(db: AsyncSession, symbol: str | None) -> Instrument | None:
    if not symbol:
        return None
    return (await db.execute(
        select(Instrument)
        .where(Instrument.symbol == str(symbol).strip())
        .order_by(Instrument.is_active.desc(), Instrument.updated_at.desc().nullslast())
        .limit(1)
    )).scalar_one_or_none()


async def _resolve_and_validate_broker_mapping(db: AsyncSession, values: dict, broker: BrokerAccount | None) -> None:
    symbol = str(values.get("instrument") or "").strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Instrument is required.")
    instrument_row = await _instrument_row_for_symbol(db, symbol)
    if instrument_row is not None:
        values["instrument"] = instrument_row.symbol
        values["exchange"] = values.get("exchange") or instrument_row.exchange
        values["segment"] = values.get("segment") or instrument_row.market or instrument_row.asset_class
        resolved_symbol = values.get("broker_symbol") or values.get("instrument_key") or instrument_row.broker_symbol or instrument_row.symbol
        values["broker_symbol"] = values.get("broker_symbol") or resolved_symbol
        values["instrument_key"] = values.get("instrument_key") or resolved_symbol
    else:
        values["broker_symbol"] = values.get("broker_symbol") or symbol
        values["instrument_key"] = values.get("instrument_key") or values.get("broker_symbol") or symbol

    broker_code = _broker_code_value(broker)
    is_indian = _is_indian_market(instrument_row, values.get("exchange"), values.get("segment"))
    if broker_code == "UPSTOX" or is_indian:
        if not str(values.get("instrument_key") or "").strip():
            raise HTTPException(status_code=400, detail="Instrument key is required for this broker/instrument.")
        if not str(values.get("exchange") or "").strip() or not str(values.get("segment") or "").strip():
            raise HTTPException(status_code=400, detail="Exchange and segment are required for Indian/Upstox instruments.")
    elif broker_code in {"MT5", "MT5_AGENT", "CTRADER", "CTRADER_API"}:
        if not str(values.get("broker_symbol") or values.get("instrument_key") or "").strip():
            raise HTTPException(status_code=400, detail="Broker symbol is required for this broker/instrument.")


def _strategy_name(row: StrategyDeployment) -> str:
    strategy = getattr(row, "strategy", None)
    return getattr(strategy, "name", None) or row.strategy_id


async def _validate_broker_for_user(db: AsyncSession, broker_account_id: UUID | None, current_user: dict, mode: str | None = None, instrument: str | None = None, broker_symbol: str | None = None, instrument_key: str | None = None) -> None:
    if broker_account_id is None:
        return
    broker = await get_broker_account_or_404(db, broker_account_id, current_user)
    if str(mode or "").upper() == "LIVE" and _is_ctrader(broker) and not bool(getattr(settings, "ctrader_live_trading_enabled", False)):
        raise HTTPException(status_code=400, detail="cTrader LIVE execution is disabled by platform configuration.")
    if str(mode or "").upper() in {"DEMO", "LIVE"} and _is_ctrader(broker):
        if str(mode or "").upper() == "DEMO" and not bool(getattr(settings, "ctrader_demo_trading_enabled", True)):
            raise HTTPException(status_code=400, detail="cTrader demo trading is disabled by platform configuration.")
        if str(broker.status or "").upper() != "CONNECTED":
            raise HTTPException(status_code=400, detail="cTrader broker account must be CONNECTED before creating a demo deployment.")
        selected = _selected_ctrader_account(broker)
        if not selected:
            raise HTTPException(status_code=400, detail="Select a cTrader trading account before creating a demo deployment.")
        account_mode = str(selected.get("account_type") or broker.mode or "").upper()
        requested_mode = str(mode or "").upper()
        if requested_mode == "LIVE" and not bool(getattr(settings, "ctrader_live_trading_enabled", False)):
            raise HTTPException(status_code=400, detail="cTrader LIVE execution is disabled by platform configuration.")
        if account_mode and account_mode != requested_mode:
            raise HTTPException(status_code=400, detail=f"cTrader selected account is not {requested_mode}.")
        symbol = str(broker_symbol or instrument_key or instrument or "").strip().upper()
        if not symbol:
            raise HTTPException(status_code=400, detail="cTrader deployment requires broker symbol or instrument.")
        meta = broker.metadata_json or {}
        symbols_preview = meta.get("ctrader_symbols_preview") if isinstance(meta, dict) else []
        has_preview_match = any(str((item or {}).get("symbol_name") or (item or {}).get("trading_symbol") or (item or {}).get("symbol") or "").upper() == symbol for item in symbols_preview if isinstance(item, dict))
        has_db_mapping = (await db.execute(select(BrokerInstrument.id).where(BrokerInstrument.broker_provider_code == "CTRADER", BrokerInstrument.is_active == True, ((BrokerInstrument.trading_symbol == symbol) | (BrokerInstrument.instrument_key == symbol))).limit(1))).scalar_one_or_none() is not None
        if not (has_preview_match or has_db_mapping):
            # Do not hard-block old symbols when sync bridge is not configured; log/metadata still tells user to sync symbols.
            return




def _validate_safe_deployment_values(values: dict, current: StrategyDeployment | None = None) -> None:
    merged = {}
    if current is not None:
        for key in ["capital", "risk_per_trade", "rr_ratio", "price_risk_pct", "max_daily_loss", "max_trades_per_day", "max_open_positions", "mt5_demo_max_lot"]:
            merged[key] = getattr(current, key, None)
    merged.update(values)
    def dec(key: str, default: str = "0") -> Decimal:
        return _dec(merged.get(key), default)
    if "capital" in merged and merged.get("capital") is not None and dec("capital") <= 0:
        raise HTTPException(status_code=400, detail="Capital must be greater than 0.")
    if "risk_per_trade" in merged:
        risk = dec("risk_per_trade")
        if risk <= 0:
            raise HTTPException(status_code=400, detail="Risk per trade must be greater than 0%.")
        if risk > Decimal("0.10"):
            raise HTTPException(status_code=400, detail="Risk per trade cannot be more than 10%.")
    if "rr_ratio" in merged and dec("rr_ratio") <= 0:
        raise HTTPException(status_code=400, detail="RR ratio must be greater than 0.")
    if "price_risk_pct" in merged and dec("price_risk_pct") <= 0:
        raise HTTPException(status_code=400, detail="Fixed price risk percent must be greater than 0.")
    if "max_daily_loss" in merged and dec("max_daily_loss") < 0:
        raise HTTPException(status_code=400, detail="Max daily loss cannot be negative.")
    if "max_trades_per_day" in merged and int(merged.get("max_trades_per_day") or 0) < 1:
        raise HTTPException(status_code=400, detail="Max trades per day must be at least 1.")
    if "max_open_positions" in merged and int(merged.get("max_open_positions") or 0) < 1:
        raise HTTPException(status_code=400, detail="Max open positions must be at least 1.")
    if merged.get("mt5_demo_max_lot") is not None and dec("mt5_demo_max_lot") <= 0:
        raise HTTPException(status_code=400, detail="MT5 demo max lot must be greater than 0.")


async def _guard_running_deployment_update(db: AsyncSession, row: StrategyDeployment, values: dict) -> None:
    if str(row.status or "").upper() != "RUNNING":
        return
    locked = {"strategy_id", "instrument", "timeframe", "broker_account_id", "mode", "quantity_mode"}
    changed = [key for key in locked if key in values and str(values.get(key)) != str(getattr(row, key, None))]
    if changed:
        raise HTTPException(status_code=400, detail="Stop this deployment first or clone it with new settings.")
    if "risk_per_trade" in values and _dec(values.get("risk_per_trade")) != _dec(getattr(row, "risk_per_trade", None)):
        open_count = int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalar() or 0)
        if open_count > 0:
            raise HTTPException(status_code=400, detail="Risk percent cannot be changed while an open position exists. Close or stop first.")

async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {"status": deployment.status, "mode": deployment.mode},
    ))


async def _recent(db: AsyncSession, model, deployment_id: UUID, limit: int = 20):
    result = await db.execute(select(model).where(model.deployment_id == deployment_id).order_by(model.created_at.desc()).limit(limit))
    return list(result.scalars().all())


def _symbol_key(value: object) -> str:
    return str(value or "").strip().upper().replace(".", "").replace("_", "").replace("-", "")


def _symbols_match(requested: object, actual: object) -> bool:
    req = _symbol_key(requested)
    act = _symbol_key(actual)
    if not req or not act:
        return False
    return act == req or act.startswith(req) or req.startswith(act)


def _mt5_position_side(position: dict) -> str:
    try:
        return "LONG" if int(position.get("type", 0)) == 0 else "SHORT"
    except Exception:
        return "LONG"


def _mt5_position_time(position: dict) -> datetime:
    value = position.get("time") or position.get("time_msc")
    try:
        if value is not None:
            ivalue = int(value)
            if ivalue > 10_000_000_000:
                ivalue = int(ivalue / 1000)
            return datetime.fromtimestamp(ivalue, tz=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)


async def _refresh_demo_broker_state(db: AsyncSession, row: StrategyDeployment, broker_row: BrokerAccount | None) -> dict | None:
    """Refresh DEMO account/position/PnL from brokers that support position sync."""
    if row.mode not in {"DEMO", "LIVE"} or broker_row is None or broker_row.status != "CONNECTED":
        return None
    broker_code = get_broker_code(broker_row)
    if broker_code != "MT5":
        return None

    adapter = get_broker_adapter(broker_row, db)
    account_info = await adapter.get_account_info()
    if account_info.get("connected"):
        broker_row.last_connected_at = datetime.now(timezone.utc)
        broker_row.status = "CONNECTED"
        broker_row.metadata_json = {
            **(broker_row.metadata_json or {}),
            "last_test": {
                "connected": True,
                "message": account_info.get("message"),
                "account_login": account_info.get("account_login"),
                "server": account_info.get("server"),
                "balance": account_info.get("balance"),
                "equity": account_info.get("equity"),
                "currency": account_info.get("currency"),
            },
            "safe_message": account_info.get("message"),
            "provider": broker_row.broker_name,
        }

    raw_positions = []
    if hasattr(adapter, "get_positions"):
        try:
            raw_positions = await adapter.get_positions(getattr(row, "broker_symbol", None) or row.instrument)
        except TypeError:
            raw_positions = await adapter.get_positions()
    raw_positions = [p for p in (raw_positions or []) if isinstance(p, dict) and not (p.get("success") is False)]

    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    deals_pnl = {"realized_pnl": "0", "deal_count": 0}
    if hasattr(adapter, "get_deals_pnl"):
        deals_pnl = await adapter.get_deals_pnl(getattr(row, "broker_symbol", None) or row.instrument, since=today_start)

    db_open_positions = (await db.execute(
        select(LivePosition).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN")
    )).scalars().all()
    matched_db_ids: set[str] = set()
    changed = False

    for broker_pos in raw_positions:
        actual_symbol = str(broker_pos.get("symbol") or row.instrument)
        broker_position_id = str(broker_pos.get("ticket") or broker_pos.get("position_id") or broker_pos.get("identifier") or "") or None
        broker_opened_at = _mt5_position_time(broker_pos)
        broker_opened_at_raw = str(broker_pos.get("time") or broker_pos.get("time_msc") or "") or None
        side = _mt5_position_side(broker_pos)
        qty = _dec(broker_pos.get("volume"), "0")
        avg_entry = _dec(broker_pos.get("price_open"), "0")
        current_price = _dec(broker_pos.get("price_current"), str(avg_entry))
        profit = _dec(broker_pos.get("profit"), "0")
        sl = _as_money(broker_pos.get("sl"))
        tp = _as_money(broker_pos.get("tp"))

        existing = None
        if broker_position_id:
            existing = next((p for p in db_open_positions if str(p.id) not in matched_db_ids and str(getattr(p, "broker_position_id", "") or "") == broker_position_id), None)
        if existing is None:
            existing = next((p for p in db_open_positions if str(p.id) not in matched_db_ids and p.side == side and _symbols_match(p.symbol, actual_symbol) and not getattr(p, "broker_position_id", None)), None)
        if existing is None:
            existing = LivePosition(
                deployment_id=row.id,
                user_id=row.user_id,
                broker_account_id=row.broker_account_id,
                broker_position_id=broker_position_id,
                broker_opened_at=broker_opened_at,
                broker_opened_at_raw=broker_opened_at_raw,
                symbol=actual_symbol,
                side=side,
                qty=qty,
                avg_entry_price=avg_entry,
                current_price=current_price,
                stop_loss=sl,
                target=tp,
                unrealized_pnl=profit,
                realized_pnl=Decimal("0"),
                status="OPEN",
                opened_at=broker_opened_at,
            )
            db.add(existing)
            await db.flush()
            db_open_positions.append(existing)
            changed = True
        else:
            for field, value in {
                "symbol": actual_symbol,
                "broker_account_id": row.broker_account_id,
                "broker_position_id": broker_position_id or getattr(existing, "broker_position_id", None),
                "broker_opened_at": broker_opened_at,
                "broker_opened_at_raw": broker_opened_at_raw,
                "qty": qty,
                "avg_entry_price": avg_entry,
                "current_price": current_price,
                "stop_loss": sl,
                "target": tp,
                "unrealized_pnl": profit,
            }.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
        matched_db_ids.add(str(existing.id))

    now = datetime.now(timezone.utc)
    for db_pos in db_open_positions:
        if str(db_pos.id) not in matched_db_ids:
            db_pos.status = "CLOSED"
            db_pos.closed_at = db_pos.closed_at or now
            db_pos.unrealized_pnl = Decimal("0")
            changed = True

    if changed:
        await _write_log(db, row, "BROKER_POSITION_SYNCED", f"MT5 {row.mode} positions synced from broker", "INFO", {"broker_open_positions": len(raw_positions), "symbol": row.instrument})
        await db.flush()

    unrealized = sum((_dec(p.get("profit"), "0") for p in raw_positions), Decimal("0"))
    realized = _dec(deals_pnl.get("realized_pnl"), "0") if isinstance(deals_pnl, dict) else Decimal("0")
    today_pnl = realized + unrealized
    if get_broker_code(broker_row) == "MT5":
        await _write_log(db, row, "BROKER_PNL_SYNCED", "MT5 broker PnL synced", "INFO", {
            "unrealized_pnl": str(unrealized),
            "today_realized_pnl": str(realized),
            "today_pnl": str(today_pnl),
            "deal_count": int(deals_pnl.get("deal_count") or 0) if isinstance(deals_pnl, dict) else 0,
            "positions_count": len(raw_positions),
            "source": "MT5_AGENT_POSITIONS_AND_DEALS",
        })
        await db.flush()
    # Persist broker account snapshot and position reconciliation before summary metrics are queried.
    await db.commit()
    return {
        "account_info": account_info,
        "open_positions_count": len(raw_positions),
        "unrealized_pnl": unrealized,
        "realized_pnl": realized,
        "today_pnl": today_pnl,
        "position_rows": raw_positions,
        "deals_pnl": deals_pnl,
        "broker_pnl_source": "MT5_AGENT_POSITIONS_AND_DEALS" if get_broker_code(broker_row) == "MT5" else "BROKER_POSITIONS",
    }


async def _sync_upstox_broker_state(db: AsyncSession, row: StrategyDeployment, broker_row: BrokerAccount | None) -> dict | None:
    if row.mode not in {"DEMO", "LIVE"} or broker_row is None or broker_row.status != "CONNECTED" or get_broker_code(broker_row) != "UPSTOX":
        return None
    adapter = get_broker_adapter(broker_row, db)
    raw_orders = await adapter.get_orders() if hasattr(adapter, "get_orders") else []
    raw_positions = await adapter.get_positions() if hasattr(adapter, "get_positions") else []
    if raw_orders and isinstance(raw_orders[0], dict) and raw_orders[0].get("success") is False:
        await _write_log(db, row, "UPSTOX_SYNC_WARNING", raw_orders[0].get("message") or "Could not fetch Upstox orders", "WARNING")
        raw_orders = []
    if raw_positions and isinstance(raw_positions[0], dict) and raw_positions[0].get("success") is False:
        await _write_log(db, row, "UPSTOX_SYNC_WARNING", raw_positions[0].get("message") or "Could not fetch Upstox positions", "WARNING")
        raw_positions = []

    def norm_status(value: object) -> str:
        v = str(value or "").lower()
        if v in {"complete", "completed", "filled"}: return "FILLED"
        if v in {"cancelled", "canceled"}: return "CANCELLED"
        if v in {"rejected", "failed"}: return "REJECTED"
        if v: return "PLACED"
        return "PENDING"

    changed = False
    for broker_order in raw_orders:
        if not isinstance(broker_order, dict):
            continue
        broker_order_id = str(broker_order.get("order_id") or broker_order.get("orderId") or "")
        if not broker_order_id:
            continue
        existing = (await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == row.id, LiveOrder.broker_order_id == broker_order_id))).scalar_one_or_none()
        if existing is not None:
            existing.status = norm_status(broker_order.get("status") or broker_order.get("order_status"))
            if broker_order.get("average_price") not in (None, ""):
                existing.executed_price = _dec(broker_order.get("average_price"), str(existing.executed_price or existing.entry_price or 0))
            existing.raw_response = {**(existing.raw_response or {}), "broker_sync": broker_order}
            changed = True

    db_open_positions = (await db.execute(select(LivePosition).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalars().all()
    matched: set[str] = set()
    for pos in raw_positions:
        if not isinstance(pos, dict):
            continue
        qty = _dec(pos.get("quantity") or pos.get("net_quantity") or pos.get("day_buy_quantity") or 0, "0")
        if qty == 0:
            continue
        instrument_key = str(pos.get("instrument_token") or pos.get("instrument_key") or pos.get("tradingsymbol") or row.instrument_key or row.instrument)
        side = "LONG" if qty > 0 else "SHORT"
        qty_abs = abs(qty)
        avg = _dec(pos.get("average_price") or pos.get("buy_price") or pos.get("sell_price") or 0, "0")
        ltp = _dec(pos.get("last_price") or pos.get("ltp") or avg, str(avg))
        pnl = _dec(pos.get("pnl") or pos.get("unrealised") or pos.get("unrealized_pnl") or 0, "0")
        existing = next((p for p in db_open_positions if str(p.id) not in matched and _symbols_match(p.symbol, instrument_key) and p.side == side), None)
        if existing is None:
            existing = LivePosition(deployment_id=row.id, user_id=row.user_id, broker_account_id=row.broker_account_id, symbol=instrument_key, side=side, qty=qty_abs, avg_entry_price=avg, current_price=ltp, unrealized_pnl=pnl, realized_pnl=Decimal("0"), status="OPEN", opened_at=datetime.now(timezone.utc))
            db.add(existing)
            await db.flush()
            db_open_positions.append(existing)
        else:
            existing.qty = qty_abs
            existing.avg_entry_price = avg
            existing.current_price = ltp
            existing.unrealized_pnl = pnl
            existing.broker_account_id = row.broker_account_id
        matched.add(str(existing.id))
        changed = True

    if changed:
        await _write_log(db, row, "UPSTOX_BROKER_SYNCED", "Upstox broker orders/positions synced", "INFO", {"orders": len(raw_orders), "positions": len(raw_positions)})
        await db.flush()
    return {"orders_count": len(raw_orders), "positions_count": len(raw_positions), "position_rows": raw_positions}


async def _summary(db: AsyncSession, row: StrategyDeployment) -> dict:
    day_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)

    broker = None
    broker_row = None
    broker_metrics = None
    broker_sync_warning = None
    if row.broker_account_id:
        broker_row = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
        broker = _broker_safe(broker_row)
        try:
            broker_metrics = await _refresh_demo_broker_state(db, row, broker_row)
            if broker_metrics is not None and broker_row is not None:
                broker = _broker_safe(broker_row)
        except Exception as exc:
            await db.rollback()
            logger.warning("Live deployment broker refresh failed for %s: %s", row.id, exc, exc_info=True)
            broker_sync_warning = str(exc)
            broker_row = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
            broker = _broker_safe(broker_row)

    realized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == row.id))).scalar())
    unrealized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.unrealized_pnl), 0)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalar())
    today_realized_pnl = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == row.id, LivePosition.closed_at >= day_start))).scalar())
    today_unrealized_pnl = unrealized
    today_pnl = today_realized_pnl + today_unrealized_pnl
    open_positions_count = int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalar() or 0)
    orders_count_today = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id, LiveOrder.created_at >= day_start))).scalar() or 0)
    tradeable_signal_filter = LiveSignal.signal_type.in_(["BUY", "SELL", "EXIT"])
    signals_count_today = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == row.id, LiveSignal.created_at >= day_start, tradeable_signal_filter))).scalar() or 0)
    total_orders = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id))).scalar() or 0)
    total_signals = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == row.id, tradeable_signal_filter))).scalar() or 0)

    latest_equity = (await db.execute(select(LiveEquityPoint.equity).where(LiveEquityPoint.deployment_id == row.id).order_by(LiveEquityPoint.timestamp.desc()).limit(1))).scalar_one_or_none()
    equity = _dec(latest_equity, str(_dec(row.capital, "100000") + realized + unrealized))

    latest_signal = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id, tradeable_signal_filter).order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()
    latest_order = (await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == row.id).order_by(LiveOrder.created_at.desc()).limit(1))).scalar_one_or_none()
    open_positions = (await db.execute(select(LivePosition).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN").order_by(LivePosition.opened_at.desc()).limit(20))).scalars().all()
    recent_orders = await _recent(db, LiveOrder, row.id)
    recent_signals = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id, tradeable_signal_filter).order_by(LiveSignal.created_at.desc()).limit(20))).scalars().all()
    recent_logs = await _recent(db, LiveTradeLog, row.id)
    position_events = (await db.execute(
        select(LiveTradeLog)
        .where(LiveTradeLog.deployment_id == row.id, LiveTradeLog.event_type.in_([
            "POSITION_OPENED", "STOP_LOSS_HIT", "TAKE_PROFIT_HIT", "POSITION_CLOSED", "BROKER_SYNC_UPDATE",
            "BROKER_POSITION_SYNCED", "MANUAL_CLOSE", "PAPER_POSITION_MANAGER_UPDATED", "MAX_DAILY_LOSS", "ERROR_EXIT", "OPPOSITE_SIGNAL", "SQUARE_OFF"
        ]))
        .order_by(LiveTradeLog.created_at.desc())
        .limit(20)
    )).scalars().all()
    latest_engine_signal = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id, LiveSignal.source == "ENGINE", tradeable_signal_filter).order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()
    latest_runner_log = (await db.execute(select(LiveTradeLog).where(LiveTradeLog.deployment_id == row.id, LiveTradeLog.event_type.ilike("RUNNER_%")).order_by(LiveTradeLog.created_at.desc()).limit(1))).scalar_one_or_none()

    if broker_metrics is not None:
        # Broker deal PnL is requested only from the UTC day start, so keep lifetime
        # realized PnL from local deployment records and use broker values for Today PnL.
        unrealized = _dec(broker_metrics.get("unrealized_pnl"), str(unrealized))
        today_realized_pnl = _dec(broker_metrics.get("realized_pnl"), str(today_realized_pnl))
        today_unrealized_pnl = _dec(broker_metrics.get("unrealized_pnl"), str(today_unrealized_pnl))
        today_pnl = _dec(broker_metrics.get("today_pnl"), str(today_realized_pnl + today_unrealized_pnl))
        open_positions_count = int(broker_metrics.get("open_positions_count") or 0)

    capital_snapshot = get_effective_trading_capital(row, broker_row, broker_metrics)
    capital_value = capital_snapshot.effective_capital
    if capital_snapshot.equity is not None:
        equity = capital_snapshot.equity
    elif latest_equity is None:
        equity = capital_snapshot.effective_capital + realized + unrealized
    currency = (capital_snapshot.account_currency or await _deployment_currency(db, row, broker) or "USD").upper()

    return {
        "deployment": {
            "id": str(row.id),
            "name": row.name,
            "strategy_id": row.strategy_id,
            "strategy_name": _strategy_name(row),
            "instrument": row.instrument,
            "broker_symbol": getattr(row, "broker_symbol", None),
            "instrument_key": getattr(row, "instrument_key", None),
            "exchange": getattr(row, "exchange", None),
            "segment": getattr(row, "segment", None),
            "product_type": getattr(row, "product_type", "MIS"),
            "order_variety": getattr(row, "order_variety", "REGULAR"),
            "quantity_mode": getattr(row, "quantity_mode", "RISK_BASED"),
            "fixed_quantity": getattr(row, "fixed_quantity", None),
            "max_quantity": getattr(row, "max_quantity", None),
            "max_order_value": getattr(row, "max_order_value", None),
            "square_off_time": getattr(row, "square_off_time", None),
            "upstox_order_confirmed": getattr(row, "upstox_order_confirmed", False),
            "timeframe": row.timeframe,
            "mode": row.mode,
            "status": row.status,
            "auto_trade_enabled": row.auto_trade_enabled,
            "auto_runner_enabled": getattr(row, "auto_runner_enabled", False),
            "last_runner_at": getattr(row, "last_runner_at", None),
            "last_processed_candle_time": getattr(row, "last_processed_candle_time", None),
            "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
            "live_sync_enabled": getattr(row, "live_sync_enabled", False),
            "live_sync_interval_seconds": getattr(row, "live_sync_interval_seconds", 10),
            "last_live_sync_at": getattr(row, "last_live_sync_at", None),
            "live_sync_error_count": getattr(row, "live_sync_error_count", 0),
            "live_sync_last_error": getattr(row, "live_sync_last_error", None),
            "live_approved": getattr(row, "live_approved", False),
            "live_approved_at": getattr(row, "live_approved_at", None),
            "runner_error_count": getattr(row, "runner_error_count", 0),
            "runner_last_error": getattr(row, "runner_last_error", None),
            "last_signal_at": row.last_signal_at,
            "last_heartbeat_at": row.last_heartbeat_at,
            "heartbeat_stale": bool(row.last_heartbeat_at and (datetime.now(timezone.utc) - row.last_heartbeat_at).total_seconds() > 180),
            "webhook_url": row.webhook_url,
            "tradingview_secret": row.tradingview_secret,
            "example_payload": row.example_payload,
        },
        "broker": broker,
        "account": {
            "account_currency": currency,
            "balance": capital_snapshot.balance,
            "equity": capital_snapshot.equity,
            "free_margin": capital_snapshot.free_margin,
            "effective_capital": capital_snapshot.effective_capital,
            "effective_capital_source": capital_snapshot.effective_capital_source,
        },
        "metrics": {
            "capital": capital_value,
            "currency": currency,
            "account_currency": currency,
            "balance": capital_snapshot.balance,
            "equity": equity,
            "free_margin": capital_snapshot.free_margin,
            "effective_capital": capital_snapshot.effective_capital,
            "effective_capital_source": capital_snapshot.effective_capital_source,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "today_realized_pnl": today_realized_pnl,
            "today_unrealized_pnl": today_unrealized_pnl,
            "today_pnl": today_pnl,
            "open_positions": open_positions_count,
            "open_positions_count": open_positions_count,
            "orders_today": orders_count_today,
            "orders_count_today": orders_count_today,
            "signals_today": signals_count_today,
            "signals_count_today": signals_count_today,
            "total_orders": total_orders,
            "total_signals": total_signals,
            "source": "MT5_BROKER" if broker_metrics is not None and (broker_metrics or {}).get("broker_pnl_source") == "MT5_AGENT_POSITIONS_AND_DEALS" else ("MT5" if broker_metrics is not None else "DATABASE"),
            "broker_synced": bool(broker_metrics is not None),
            "broker_pnl_source": (broker_metrics or {}).get("broker_pnl_source") if broker_metrics is not None else "LOCAL_DEPLOYMENT_RECORDS",
            "broker_deal_count": (broker_metrics or {}).get("deals_pnl", {}).get("deal_count") if isinstance((broker_metrics or {}).get("deals_pnl"), dict) else None,
        },
        "broker_sync": {
            "mode": row.mode,
            "managed_by": "Deprecated Paper Engine" if row.mode == "PAPER" else "Broker SL/TP Sync",
            "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
            "last_live_sync_at": getattr(row, "last_live_sync_at", None),
            "live_sync_enabled": getattr(row, "live_sync_enabled", False),
            "live_sync_interval_seconds": getattr(row, "live_sync_interval_seconds", 10),
            "live_sync_error_count": getattr(row, "live_sync_error_count", 0),
            "live_sync_last_error": getattr(row, "live_sync_last_error", None),
            "broker_connection_status": broker.get("status") if isinstance(broker, dict) else None,
            "open_broker_positions": (broker_metrics or {}).get("open_positions_count") if broker_metrics is not None else None,
            "local_tracked_positions": open_positions_count,
            "sync_mismatch_warning": (broker_metrics is not None and int((broker_metrics or {}).get("open_positions_count") or 0) != int(open_positions_count or 0)),
            "latest_sync_error": broker_sync_warning or getattr(row, "live_sync_last_error", None),
            "warning": broker_sync_warning,
        },
        "runner": {
            "last_run_at": getattr(row, "last_runner_at", None) or (latest_runner_log.created_at if latest_runner_log else None),
            "last_processed_candle_time": getattr(row, "last_processed_candle_time", None),
            "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
            "live_sync_enabled": getattr(row, "live_sync_enabled", False),
            "live_sync_interval_seconds": getattr(row, "live_sync_interval_seconds", 10),
            "last_live_sync_at": getattr(row, "last_live_sync_at", None),
            "live_sync_error_count": getattr(row, "live_sync_error_count", 0),
            "live_sync_last_error": getattr(row, "live_sync_last_error", None),
            "auto_runner_enabled": getattr(row, "auto_runner_enabled", False),
            "runner_error_count": getattr(row, "runner_error_count", 0),
            "runner_last_error": getattr(row, "runner_last_error", None),
            # Last processed candle must show the actual candle processed by the runner.
            # Do not derive it from the latest tradeable ENGINE signal, because HOLD cycles are not saved.
            "last_candle_time": getattr(row, "last_processed_candle_time", None) or (latest_engine_signal.candle_time if latest_engine_signal else None),
            "last_signal": latest_engine_signal.signal_type if latest_engine_signal else None,
            "latest_runner_log": latest_runner_log.message if latest_runner_log else None,
            "latest_runner_status": latest_runner_log.level if latest_runner_log else None,
            "latest_order_status": latest_order.status if latest_order else None,
            "latest_order_error": latest_order.error_message if latest_order else None,
            "latest_broker_order_id": latest_order.broker_order_id if latest_order else None,
            "last_entry_plan": ({
                "entry_price": float(latest_order.entry_price) if latest_order.entry_price is not None else None,
                "stop_loss": float(latest_order.stop_loss) if latest_order.stop_loss is not None else None,
                "target": float(latest_order.target) if latest_order.target is not None else None,
                "side": latest_order.side,
                "symbol": latest_order.symbol,
            } if latest_order else None),
            "last_risk_preview": (
                ((latest_order.raw_response or {}).get("audit_preview") or (latest_order.raw_response or {}).get("sizing"))
                if latest_order and isinstance(latest_order.raw_response, dict) else None
            ),
            "last_execution_decision": (
                f"Last cycle: {latest_engine_signal.signal_type} signal {latest_engine_signal.status.lower()}" if latest_engine_signal else None
            ),
        },
        "latest_signal": dump_one(LiveSignalOut, latest_signal) if latest_signal else None,
        "latest_order": dump_one(LiveOrderOut, latest_order) if latest_order else None,
        "open_positions": dump_list(LivePositionOut, open_positions),
        "position_events": dump_list(LiveTradeLogOut, position_events),
        "recent_orders": dump_list(LiveOrderOut, recent_orders),
        "recent_signals": dump_list(LiveSignalOut, recent_signals),
        "recent_logs": dump_list(LiveTradeLogOut, recent_logs),
    }


@router.get("")
async def list_deployments(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stmt = select(StrategyDeployment).order_by(StrategyDeployment.created_at.desc())
    if not is_admin(current_user):
        stmt = stmt.where(StrategyDeployment.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(StrategyDeploymentOut, rows))


@router.get("/access-status")
async def get_live_trading_access_status(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payload = await build_live_trading_access_status(db, user_id_from(current_user))
    await db.commit()
    return success_response(payload, payload.get("message") or "Live trading access checked")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_deployment(payload: StrategyDeploymentCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    payload_values = payload.model_dump()
    mode = str(payload_values.get("mode") or "DEMO").upper()
    payload_values["mode"] = mode
    if mode == "PAPER":
        raise HTTPException(status_code=400, detail="PAPER deployments are deprecated. Use DEMO or LIVE broker deployment.")
    if mode not in {"DEMO", "LIVE"}:
        raise HTTPException(status_code=400, detail="Deployment mode must be DEMO or LIVE.")
    if not payload.broker_account_id:
        raise HTTPException(status_code=400, detail="Broker account is required for DEMO and LIVE deployments.")

    # New broker-only deployments must use broker account capital/equity. Keep the
    # legacy DB column populated only as a safe fallback for older code paths.
    payload_values["capital"] = Decimal("100000")
    _validate_safe_deployment_values(payload_values)
    await get_deployable_strategy_or_400(db, payload.strategy_id, mode)

    broker = await get_broker_account_or_404(db, payload.broker_account_id, current_user)
    await _resolve_and_validate_broker_mapping(db, payload_values, broker)
    await _validate_broker_for_user(db, payload.broker_account_id, current_user, mode, payload_values.get("instrument"), payload_values.get("broker_symbol"), payload_values.get("instrument_key"))
    approval = await check_broker_deployment_approval(
        db, user_id_from(current_user), payload.broker_account_id, mode,
        instrument=payload_values.get("instrument"), exchange=payload_values.get("exchange"), segment=payload_values.get("segment"), broker_symbol=payload_values.get("broker_symbol"), instrument_key=payload_values.get("instrument_key"),
    )
    enforce_approval_limits(approval, payload_values)
    row = StrategyDeployment(user_id=user_id_from(current_user), status="DRAFT", **payload_values)
    if approval is not None:
        row.live_approved = True
        row.live_approved_at = approval.approved_at if hasattr(approval, "approved_at") else datetime.now(timezone.utc)
    _ensure_tradingview_secret(row)
    db.add(row)
    await db.flush()
    await _write_log(db, row, "DEPLOYMENT_CREATED", f"{mode} broker deployment created", metadata={"effective_capital_source": "BROKER_ACCOUNT_ON_EXECUTION"})
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment created")



@router.delete("/{deployment_id}")
async def delete_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    status_value = str(row.status or "").upper()
    if status_value not in {"DRAFT", "STOPPED", "ERROR"}:
        raise HTTPException(status_code=400, detail="Only DRAFT, STOPPED, or ERROR deployments can be deleted. Stop the deployment before deleting it.")

    open_positions_count = int((await db.execute(
        select(func.count(LivePosition.id)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN")
    )).scalar() or 0)
    if open_positions_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete deployment while open live positions exist.")

    active_orders_count = int((await db.execute(
        select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id, LiveOrder.status.in_(["PENDING", "PLACED"]))
    )).scalar() or 0)
    if active_orders_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete deployment while pending or placed live orders exist.")

    deleted_id = str(row.id)
    await _write_log(db, row, "DEPLOYMENT_DELETED", "Deployment deleted by user/admin", "INFO", {"status": row.status, "mode": row.mode, "deleted_by_role": current_user.get("role")})
    await db.flush()
    await db.delete(row)
    await db.commit()
    return success_response({"deleted": True, "deployment_id": deleted_id}, "Deployment deleted")


@router.get("/{deployment_id}/readiness")
async def get_deployment_readiness(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await build_live_deployment_readiness(db, deployment_id, current_user)
    return success_response(result, result.get("summary") or "Live readiness checked")


@router.post("/{deployment_id}/compatibility-check")
async def check_deployment_live_compatibility(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await run_live_compatibility_check(db, deployment_id)
    return success_response(result, result.get("summary") or "Live compatibility checked")


@router.get("/{deployment_id}/positions")
async def get_deployment_positions(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    rows = (await db.execute(
        select(LivePosition).where(LivePosition.deployment_id == deployment_id).order_by(LivePosition.opened_at.desc(), LivePosition.created_at.desc()).limit(100)
    )).scalars().all()
    return success_response(dump_list(LivePositionOut, rows), "Deployment positions loaded")


@router.get("/{deployment_id}/position-events")
async def get_deployment_position_events(deployment_id: UUID, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    lifecycle_events = [
        "POSITION_OPENED", "STOP_LOSS_HIT", "TAKE_PROFIT_HIT", "POSITION_CLOSED", "BROKER_SYNC_UPDATE",
        "BROKER_POSITION_SYNCED", "MANUAL_CLOSE", "PAPER_POSITION_MANAGER_UPDATED", "PAPER_POSITION_MANAGER_SKIPPED",
        "MAX_DAILY_LOSS", "ERROR_EXIT", "OPPOSITE_SIGNAL", "SQUARE_OFF",
    ]
    rows = (await db.execute(
        select(LiveTradeLog)
        .where(LiveTradeLog.deployment_id == deployment_id, LiveTradeLog.event_type.in_(lifecycle_events))
        .order_by(LiveTradeLog.created_at.desc())
        .limit(max(1, min(int(limit or 100), 300)))
    )).scalars().all()
    return success_response(dump_list(LiveTradeLogOut, rows), "Position events loaded")


@router.post("/{deployment_id}/process-paper-positions")
async def process_deployment_paper_positions(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    try:
        result = await process_paper_positions_for_deployment(db, deployment_id)
        await db.commit()
        return success_response(result, result.get("message") or "Paper positions processed")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{deployment_id}/summary")
async def get_deployment_summary(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    return success_response(await _summary(db, row))


@router.get("/{deployment_id}/broker-status")
async def get_deployment_broker_status(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if not row.broker_account_id:
        return success_response({"connected": False, "message": "No broker account connected to this deployment", "broker": None})
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
    if broker is None:
        return success_response({"connected": False, "message": "Broker account not found", "broker": None})
    adapter = get_broker_adapter(broker, db)
    info = await adapter.get_account_info()
    connected = bool(info.get("connected"))
    broker.status = "CONNECTED" if connected else "ERROR"
    if connected:
        broker.last_connected_at = datetime.now(timezone.utc)
    broker.metadata_json = {
        **(broker.metadata_json or {}),
        "last_test": {
            "connected": connected,
            "message": info.get("message"),
            "account_login": info.get("account_login"),
            "server": info.get("server"),
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "currency": info.get("currency"),
        },
        "safe_message": info.get("message"),
        "provider": broker.broker_name,
    }
    await _write_log(db, row, "BROKER_STATUS_REFRESHED", info.get("message") or "Broker status refreshed", "INFO" if connected else "WARNING")
    await db.commit()
    await db.refresh(broker)
    return success_response({"connected": connected, "message": info.get("message"), "broker": _broker_safe(broker), "account_info": {k: v for k, v in info.items() if k != "raw"}})


@router.post("/{deployment_id}/sync-broker")
async def sync_deployment_broker(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    try:
        result = await sync_deployment_broker_state(db, deployment_id)
        return success_response(result, f"{result.get('provider_code', 'Broker')} broker synced")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{deployment_id}/broker-events")
async def list_deployment_broker_events(deployment_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    rows = (await db.execute(
        select(BrokerOrderEvent)
        .where(BrokerOrderEvent.deployment_id == deployment_id)
        .order_by(BrokerOrderEvent.created_at.desc())
        .limit(max(1, min(int(limit or 50), 200)))
    )).scalars().all()
    return success_response(dump_list(BrokerOrderEventOut, rows))



async def _set_live_sync(db: AsyncSession, row: StrategyDeployment, enabled: bool, interval_seconds: int | None = None) -> StrategyDeployment:
    settings = await get_platform_trading_settings(db)
    row.live_sync_interval_seconds = clamp_live_sync_interval(settings, interval_seconds or getattr(row, "live_sync_interval_seconds", None))
    row.live_sync_enabled = enabled
    if enabled:
        row.live_sync_error_count = 0
        row.live_sync_last_error = None
    await _write_log(db, row, "LIVE_SYNC_ENABLED" if enabled else "LIVE_SYNC_DISABLED", f"Live broker auto-sync {'enabled' if enabled else 'disabled'}", metadata={"interval_seconds": row.live_sync_interval_seconds})
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/{deployment_id}/live-sync/enable")
async def enable_deployment_live_sync(deployment_id: UUID, payload: LiveSyncSettingsIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    row = await get_deployment_or_404(db, deployment_id, current_user)
    return success_response(dump_one(StrategyDeploymentOut, await _set_live_sync(db, row, True, (payload.interval_seconds if payload else None))), "Live broker auto-sync enabled")


@router.post("/{deployment_id}/live-sync/disable")
async def disable_deployment_live_sync(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    return success_response(dump_one(StrategyDeploymentOut, await _set_live_sync(db, row, False)), "Live broker auto-sync disabled")


@router.patch("/{deployment_id}/live-sync/settings")
async def update_deployment_live_sync_settings(deployment_id: UUID, payload: LiveSyncSettingsIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    settings = await get_platform_trading_settings(db)
    row.live_sync_interval_seconds = clamp_live_sync_interval(settings, payload.interval_seconds)
    await _write_log(db, row, "LIVE_SYNC_INTERVAL_CHANGED", "Live broker auto-sync interval changed", metadata={"interval_seconds": row.live_sync_interval_seconds})
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Live broker auto-sync interval updated")


@router.get("/{deployment_id}/live-sync/status")
async def get_deployment_live_sync_status(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    settings = await get_platform_trading_settings(db)
    return success_response({
        "live_sync_enabled": bool(getattr(row, "live_sync_enabled", False)),
        "live_sync_interval_seconds": int(getattr(row, "live_sync_interval_seconds", 10) or 10),
        "last_live_sync_at": getattr(row, "last_live_sync_at", None),
        "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
        "live_sync_error_count": int(getattr(row, "live_sync_error_count", 0) or 0),
        "live_sync_last_error": getattr(row, "live_sync_last_error", None),
        "platform_auto_sync_enabled": bool(getattr(settings, "broker_auto_sync_enabled", True)),
    })

@router.post("/{deployment_id}/manual-signal")
async def create_deployment_manual_signal(deployment_id: UUID, payload: ManualDeploymentSignalIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    row = await get_deployment_or_404(db, deployment_id, current_user)
    signal_type = payload.signal_type
    side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
    now = datetime.now(timezone.utc)
    signal = LiveSignal(
        deployment_id=row.id,
        user_id=row.user_id,
        strategy_id=row.strategy_id,
        source="MANUAL",
        symbol=row.instrument,
        timeframe=row.timeframe,
        signal_type=signal_type,
        side=side,
        price=payload.price,
        candle_time=payload.candle_time or now,
        confidence=None,
        reason=payload.reason or "Manual signal test",
        raw_payload={"source": "manual-signal-panel", "price": str(payload.price), "signal_type": signal_type},
        status="RECEIVED",
    )
    row.last_signal_at = now
    db.add(signal)
    await db.flush()
    await _write_log(db, row, "SIGNAL_RECEIVED", f"Manual {signal_type} signal received", metadata={"signal_id": str(signal.id), "price": str(payload.price)})

    latest_order = None
    message = "Signal saved"
    if row.status != "RUNNING":
        signal.status = "REJECTED"
        signal.rejection_reason = f"Deployment is {row.status}"
        message = signal.rejection_reason
        await _write_log(db, row, "RISK_REJECTED", message, "WARNING", {"signal_id": str(signal.id)})
    elif not row.auto_trade_enabled:
        signal.status = "ACCEPTED"
        message = "Auto trade is disabled; signal saved without execution"
        await _write_log(db, row, "EXECUTION_SKIPPED", message, metadata={"signal_id": str(signal.id)})
    else:
        latest_order = await execute_signal(db, row, signal)
        message = signal.rejection_reason or ("Signal executed" if signal.status == "EXECUTED" else f"Signal {signal.status.lower()}")

    await db.commit()
    await db.refresh(signal)
    if latest_order is not None:
        await db.refresh(latest_order)
    return success_response({
        "signal": dump_one(LiveSignalOut, signal),
        "order": dump_one(LiveOrderOut, latest_order) if latest_order else None,
        "message": message,
        "status": signal.status,
    }, message)



@router.get("/{deployment_id}/final-qa")
async def get_deployment_final_qa(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await build_final_live_qa(db, deployment_id, current_user)
    return success_response(result, result.get("summary") or "Final QA checked")


@router.post("/{deployment_id}/test-paper-order")
async def test_deployment_paper_order(deployment_id: UUID, payload: QaOrderTestIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    raise HTTPException(status_code=400, detail="PAPER order tests are deprecated. Use DEMO micro order verification with an approved broker account.")
    try:
        result = await run_paper_order_test(db, row, side=(payload.side if payload else "BUY"))
        return success_response(result, result.get("message") or "Paper order test completed")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{deployment_id}/test-demo-micro-order")
async def test_deployment_demo_micro_order(deployment_id: UUID, payload: QaOrderTestIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    row = await get_deployment_or_404(db, deployment_id, current_user)
    try:
        result = await run_demo_micro_order_test(db, row, confirm_demo_micro_order=bool(payload.confirm_demo_micro_order), side=payload.side or "BUY")
        return success_response(result, result.get("message") or "Demo micro order test completed")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{deployment_id}/run-full-dry-test")
async def run_live_deployment_full_dry_test(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await run_full_dry_test_for_deployment(db, deployment_id)
    return success_response(result, result.get("message") or "Full dry test completed")

@router.post("/{deployment_id}/run-strategy-once")
async def run_live_strategy_once(deployment_id: UUID, payload: RunStrategyOnceIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if payload is None or payload.execute:
        await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await run_strategy_for_deployment(db, deployment_id, execute=(payload.execute if payload else True))
    return success_response(result, result.get("message") or "Strategy runner completed")

@router.post("/{deployment_id}/auto-runner/enable")
async def enable_deployment_auto_runner(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.auto_runner_enabled = True
    row.runner_error_count = 0
    row.runner_last_error = None
    await _write_log(db, row, "AUTO_RUNNER_ENABLED", "Auto runner enabled")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Auto runner enabled")


@router.post("/{deployment_id}/auto-runner/disable")
async def disable_deployment_auto_runner(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.auto_runner_enabled = False
    await _write_log(db, row, "AUTO_RUNNER_DISABLED", "Auto runner disabled")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Auto runner disabled")


@router.post("/{deployment_id}/auto-runner/run-now")
async def run_deployment_auto_runner_now(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await run_deployment_if_due(db, deployment_id)
    return success_response(result, result.get("message") or result.get("reason") or "Auto runner checked")


@router.post("/{deployment_id}/refresh-candles")
async def refresh_deployment_broker_candles(deployment_id: UUID, count: int = 300, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Access check first; candle service validates linked broker and stores rates in live_market_candles.
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await refresh_deployment_candles(db, deployment_id, count=count)
    return success_response(result, f"Stored {result.get('upserted_count', 0)} broker candles")


@router.get("/{deployment_id}/candles")
async def get_deployment_broker_candles(deployment_id: UUID, limit: int = 300, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await get_candle_snapshot(db, deployment_id, limit=limit)
    return success_response(result)


@router.get("/{deployment_id}")
async def get_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if not row.tradingview_secret:
        _ensure_tradingview_secret(row)
        await db.commit()
        await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row))


@router.patch("/{deployment_id}")
async def update_deployment(deployment_id: UUID, payload: StrategyDeploymentUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    values = payload.model_dump(exclude_unset=True)

    def _locked_value_changed(field: str, incoming) -> bool:
        current = getattr(row, field, None)
        if incoming is None and current is None:
            return False
        if field == "broker_account_id":
            return str(incoming or "") != str(current or "")
        return str(incoming or "").strip().upper() != str(current or "").strip().upper()

    locked_fields = ["mode", "broker_account_id", "instrument", "broker_symbol", "instrument_key", "exchange", "segment", "timeframe"]
    if any(field in values and _locked_value_changed(field, values.get(field)) for field in locked_fields):
        raise HTTPException(
            status_code=400,
            detail="Mode, broker account, instrument, and timeframe are locked after deployment creation. Create a new deployment to change them.",
        )

    _validate_safe_deployment_values(values, row)
    if values.get("auto_trade_enabled") is True and not bool(getattr(row, "auto_trade_enabled", False)):
        compatibility = await run_live_compatibility_check(db, row.id)
        if compatibility_failed(compatibility):
            failing = [c for c in compatibility.get("checks", []) if c.get("status") == "FAIL"]
            detail = failing[0].get("message") if failing else "Live compatibility check failed. Fix compatibility before enabling Auto Trade."
            raise HTTPException(status_code=400, detail=detail)
    await _guard_running_deployment_update(db, row, values)
    target_mode = str(values.get("mode", row.mode) or "DEMO").upper()
    target_broker_account_id = values.get("broker_account_id", row.broker_account_id)
    if "mode" in values:
        if target_mode == "PAPER":
            raise HTTPException(status_code=400, detail="PAPER deployments are deprecated. Use DEMO or LIVE broker deployment.")
        await get_deployable_strategy_or_400(db, row.strategy_id, target_mode)
        if target_mode in {"DEMO", "LIVE"} and not target_broker_account_id:
            raise HTTPException(status_code=400, detail="Broker account is required for DEMO and LIVE deployments.")
    if any(k in values for k in ["broker_account_id", "mode", "instrument", "exchange", "segment", "broker_symbol", "instrument_key", "max_daily_loss", "max_trades_per_day", "max_order_value"]):
        broker = await get_broker_account_or_404(db, target_broker_account_id, current_user) if target_broker_account_id else None
        merged_mapping = {
            "instrument": values.get("instrument", row.instrument),
            "exchange": values.get("exchange", row.exchange),
            "segment": values.get("segment", row.segment),
            "broker_symbol": values.get("broker_symbol", row.broker_symbol),
            "instrument_key": values.get("instrument_key", row.instrument_key),
        }
        if target_mode in {"DEMO", "LIVE"}:
            await _resolve_and_validate_broker_mapping(db, merged_mapping, broker)
            for key, value in merged_mapping.items():
                if key in values or not getattr(row, key, None):
                    values[key] = value
        await _validate_broker_for_user(db, target_broker_account_id, current_user, target_mode, values.get("instrument", row.instrument), values.get("broker_symbol", row.broker_symbol), values.get("instrument_key", row.instrument_key))
        approval = await check_broker_deployment_approval(
            db, row.user_id, target_broker_account_id, target_mode,
            instrument=values.get("instrument", row.instrument), exchange=values.get("exchange", row.exchange), segment=values.get("segment", row.segment), broker_symbol=values.get("broker_symbol", row.broker_symbol), instrument_key=values.get("instrument_key", row.instrument_key),
        )
        merged_values = {"max_daily_loss": values.get("max_daily_loss", row.max_daily_loss), "max_trades_per_day": values.get("max_trades_per_day", row.max_trades_per_day), "max_order_value": values.get("max_order_value", row.max_order_value)}
        enforce_approval_limits(approval, merged_values)
        if approval is not None:
            row.live_approved = True
            row.live_approved_at = datetime.now(timezone.utc)
    for key, value in values.items():
        if key != "status" and hasattr(row, key):
            setattr(row, key, value)
    await _write_log(db, row, "DEPLOYMENT_UPDATED", "Deployment updated")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment updated")


@router.post("/{deployment_id}/start")
async def start_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await require_active_subscription_for_live_trading(db, user_id_from(current_user))
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if str(row.mode or "").upper() == "PAPER":
        raise HTTPException(status_code=400, detail="PAPER deployments are deprecated. Please create a DEMO or LIVE broker deployment.")
    platform_check = await check_platform_mode_allowed(db, row.mode)
    if not platform_check.allowed:
        raise HTTPException(status_code=400, detail=platform_check.reason)
    await get_deployable_strategy_or_400(db, row.strategy_id, row.mode)
    if row.mode in {"DEMO", "LIVE"}:
        approval = await check_broker_deployment_approval(
            db, row.user_id, row.broker_account_id, row.mode,
            instrument=row.instrument, exchange=row.exchange, segment=row.segment, broker_symbol=row.broker_symbol, instrument_key=row.instrument_key,
        )
        enforce_approval_limits(approval, {"max_daily_loss": row.max_daily_loss, "max_trades_per_day": row.max_trades_per_day, "max_order_value": row.max_order_value})
        if approval is not None:
            row.live_approved = True
            row.live_approved_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    row.status = "RUNNING"
    row.started_at = now
    row.stopped_at = None
    row.last_heartbeat_at = now
    await _write_log(db, row, "DEPLOYMENT_STARTED", "Deployment started")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment started")


@router.post("/{deployment_id}/pause")
async def pause_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "PAUSED"
    await _write_log(db, row, "DEPLOYMENT_PAUSED", "Deployment paused")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment paused")


@router.post("/{deployment_id}/stop")
async def stop_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "STOPPED"
    row.stopped_at = datetime.now(timezone.utc)
    await _write_log(db, row, "DEPLOYMENT_STOPPED", "Deployment stopped")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment stopped")
