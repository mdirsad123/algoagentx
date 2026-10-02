from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, Instrument, LiveOrder, LivePosition, LivePositionManagementState, LiveTradeLog, StrategyDeployment, MT5AgentCommand
from ..brokers.factory import get_broker_adapter, get_broker_code
from ..trading.partial_exit_engine import calculate_broker_partial_split
from .broker_sync_service import sync_copy_target_positions, sync_ctrader_account_positions_via_gateway, sync_ctrader_deployment_via_gateway, sync_deployment_broker_state

TERMINAL = {"SKIPPED_MIN_SIZE", "DONE", "FAILED_TERMINAL", "BROKER_POSITION_CLOSED"}
IN_FLIGHT = {"CLOSE_SENT", "AWAITING_RECONCILE"}

def D(v: Any) -> Decimal:
    return Decimal(str(v or 0))

def norm_symbol(v: Any) -> str:
    return str(v or "").upper().replace(".", "").replace("_", "").replace("-", "")

async def log_event(db: AsyncSession, deployment: StrategyDeployment | SimpleNamespace, event: str, message: str, level: str="INFO", meta: dict[str,Any]|None=None):
    db.add(LiveTradeLog(deployment_id=deployment.id, user_id=deployment.user_id, event_type=event, level=level, message=message, metadata_json=meta or {}))

def make_idempotency_key(deployment_id, account_id, broker_position_id, state_id, at_r, percent):
    raw=f"{deployment_id}:{account_id}:{broker_position_id}:{state_id}:{at_r}:{percent}"
    return "AXPX-"+hashlib.sha256(raw.encode()).hexdigest()[:40]

async def _instrument_snapshot(db: AsyncSession, deployment: StrategyDeployment, position: LivePosition, entry: LiveOrder|None) -> dict[str,Any]:
    if entry and isinstance(entry.instrument_spec_snapshot, dict) and entry.instrument_spec_snapshot:
        return dict(entry.instrument_spec_snapshot)
    rows=(await db.execute(select(Instrument).where(Instrument.is_active.is_(True)))).scalars().all()
    wanted={norm_symbol(position.symbol), norm_symbol(deployment.instrument), norm_symbol(deployment.broker_symbol)}
    inst=next((x for x in rows if norm_symbol(x.symbol) in wanted or norm_symbol(x.broker_symbol) in wanted),None)
    if not inst: return {}
    return {k:(float(getattr(inst,k)) if getattr(inst,k,None) is not None and k not in {"quantity_mode"} else getattr(inst,k,None)) for k in ("quantity_mode","min_lot","max_lot","lot_step","min_quantity","max_quantity","quantity_step","quantity_precision") }

async def ensure_management_state(db: AsyncSession, deployment: StrategyDeployment, position: LivePosition) -> LivePositionManagementState|None:
    existing=(await db.execute(select(LivePositionManagementState).where(LivePositionManagementState.live_position_id==position.id))).scalar_one_or_none()
    if existing: return existing
    if not deployment.partial_exit_enabled or position.status != "OPEN" or not position.broker_account_id or not position.broker_position_id:
        return None
    if position.stop_loss is None:
        await log_event(db,deployment,"PARTIAL_EXIT_ERROR","Cannot create management state without original strategy stop loss","ERROR",{"position_id":str(position.id)})
        return None
    entry=(await db.execute(select(LiveOrder).where(LiveOrder.deployment_id==deployment.id,LiveOrder.broker_account_id==position.broker_account_id,LiveOrder.action=="ENTRY",LiveOrder.status.in_(["FILLED","PLACED","ACCEPTED","RECONCILED"])).order_by(LiveOrder.created_at.desc()).limit(20))).scalars().all()
    entry=next((o for o in entry if norm_symbol(o.symbol)==norm_symbol(position.symbol)), None)
    spec=await _instrument_snapshot(db,deployment,position,entry)
    mode=str((entry.quantity_mode if entry else None) or spec.get("quantity_mode") or "LOTS").upper()
    risk=abs(D(position.avg_entry_price)-D(position.stop_loss))
    if risk<=0: return None
    at_r=D(deployment.partial_exit_at_r); pct=D(deployment.partial_exit_percent)
    trigger=D(position.avg_entry_price)+(risk*at_r if str(position.side).upper()=="LONG" else -(risk*at_r))
    state_id=uuid.uuid4()
    idempotency=make_idempotency_key(deployment.id, position.broker_account_id, position.broker_position_id, state_id, at_r, pct)
    state=LivePositionManagementState(id=state_id,live_position_id=position.id,deployment_id=deployment.id,broker_account_id=position.broker_account_id,entry_order_id=(entry.id if entry else None),entry_signal_id=(entry.signal_id if entry else None),broker_position_id=str(position.broker_position_id),symbol=position.symbol,side=position.side,initial_size=D(position.qty),initial_entry_price=D(position.avg_entry_price),initial_stop_loss=D(position.stop_loss),initial_target=(D(position.target) if position.target is not None else None),initial_risk_points=risk,quantity_mode=mode,instrument_spec_snapshot=spec,runtime_config_snapshot=(dict(entry.runtime_config_snapshot) if entry and isinstance(entry.runtime_config_snapshot,dict) else {"rr_ratio":str(deployment.rr_ratio),"partial_exit_enabled":True,"partial_exit_at_r":str(at_r),"partial_exit_percent":str(pct)}),partial_exit_enabled=True,partial_exit_at_r=at_r,partial_exit_percent=pct,partial_trigger_price=trigger,partial_status="PENDING",idempotency_key=idempotency)
    db.add(state); await db.flush()
    await log_event(db,deployment,"PARTIAL_EXIT_STATE_CREATED","Frozen live partial-exit contract created",meta={"position_id":str(position.id),"broker_position_id":str(position.broker_position_id),"broker_account_id":str(position.broker_account_id),"is_copy_account":str(position.broker_account_id)!=str(deployment.broker_account_id),"trigger_price":str(trigger),"partial_r":str(at_r),"partial_percent":str(pct)})
    return state

async def refresh_account_truth(db: AsyncSession, deployment: StrategyDeployment, broker_account_id) -> None:
    broker=(await db.execute(select(BrokerAccount).where(BrokerAccount.id==broker_account_id))).scalar_one()
    code=get_broker_code(broker)
    if code in {"CTRADER","CTRADER_API"} and settings.ctrader_persistent_connection_enabled:
        # Primary and copy cTrader accounts both refresh over the already-running
        # persistent market/gateway connection. Never open a second WebSocket just
        # because this position belongs to a copy account.
        await sync_ctrader_account_positions_via_gateway(db, deployment, broker_account_id)
        return
    # Account-scoped refresh deliberately avoids the normal primary sync because that
    # helper may commit internally and release our transaction-scoped advisory lock.
    proxy=SimpleNamespace(**{c.name:getattr(deployment,c.name) for c in StrategyDeployment.__table__.columns})
    proxy.broker_account_id=broker_account_id
    await sync_copy_target_positions(db,proxy)

async def finalize_from_broker_truth(db: AsyncSession, state: LivePositionManagementState, deployment: StrategyDeployment) -> bool:
    pos=(await db.execute(select(LivePosition).where(LivePosition.id==state.live_position_id))).scalar_one_or_none()
    if pos is None or pos.status!="OPEN":
        state.partial_status="BROKER_POSITION_CLOSED"; state.filled_at=datetime.now(timezone.utc)
        await log_event(db,deployment,"PARTIAL_EXIT_POSITION_ALREADY_CLOSED","Broker position is closed; no partial retry",meta={"management_state_id":str(state.id)})
        return True
    if state.planned_runner_size is None: return False
    tol=D((state.instrument_spec_snapshot or {}).get("lot_step") or (state.instrument_spec_snapshot or {}).get("quantity_step") or "0.00000001")
    if abs(D(pos.qty)-D(state.planned_runner_size)) <= max(tol/Decimal("2"),Decimal("0.00000001")):
        # Require original protection to remain before declaring success.
        if state.initial_stop_loss is not None and pos.stop_loss is None:
            state.partial_status="FAILED_RETRYABLE"; state.last_error="Runner stop loss missing after partial close"
            await log_event(db,deployment,"PARTIAL_EXIT_ERROR","Runner protection missing after partial close","ERROR",{"position_id":str(pos.id)})
            return False
        if state.initial_target is not None and pos.target is None:
            state.partial_status="FAILED_RETRYABLE"; state.last_error="Runner target missing after partial close"
            await log_event(db,deployment,"PARTIAL_EXIT_ERROR","Runner target missing after partial close","ERROR",{"position_id":str(pos.id)})
            return False
        state.partial_status="DONE"; state.filled_at=datetime.now(timezone.utc); state.last_error=None
        await log_event(db,deployment,"PARTIAL_EXIT_RECONCILED","Broker confirmed partial runner quantity",meta={"position_id":str(pos.id),"actual_runner":str(pos.qty),"expected_runner":str(state.planned_runner_size)})
        return True
    return False

async def execute_partial_close(db: AsyncSession, deployment: StrategyDeployment, state: LivePositionManagementState, position: LivePosition, quote_price: Decimal, quote_side: str) -> LiveOrder|None:
    broker=(await db.execute(select(BrokerAccount).where(BrokerAccount.id==state.broker_account_id))).scalar_one_or_none()
    if broker is None or str(broker.status or "").upper()!="CONNECTED":
        state.partial_status="FAILED_RETRYABLE"; state.last_error="Broker account not connected"; return None
    if settings.live_position_manager_demo_only and str(broker.mode or "").upper()!="DEMO":
        state.partial_status="FAILED_TERMINAL"; state.last_error="Partial-exit sending restricted to DEMO"; return None
    split=calculate_broker_partial_split(total_size=float(position.qty),percent=float(state.partial_exit_percent),quantity_mode=state.quantity_mode,instrument_spec=dict(state.instrument_spec_snapshot or {}))
    if not split.get("eligible"):
        state.partial_status="SKIPPED_MIN_SIZE"; state.last_error=split.get("reason")
        await log_event(db,deployment,"PARTIAL_EXIT_SKIPPED_MIN_SIZE","Partial exit skipped because broker-valid runner cannot be preserved",meta={"position_id":str(position.id),"broker_position_id":state.broker_position_id,**split})
        return None
    close_size=D(split["partial_close_size"]); runner=D(split["runner_size"]); state.planned_close_size=close_size; state.planned_runner_size=runner; state.effective_partial_percent=D(split["effective_partial_percent"]); state.trigger_quote_price=quote_price; state.trigger_quote_side=quote_side
    existing=(await db.execute(select(LiveOrder).where(LiveOrder.idempotency_key==state.idempotency_key,LiveOrder.action=="PARTIAL_EXIT"))).scalar_one_or_none()
    if existing:
        existing_status = str(existing.status or "").upper()
        if existing_status == "DRY_RUN" and not settings.live_position_manager_broker_send_enabled:
            state.partial_close_order_id = existing.id
            return existing
        if existing_status not in {"ERROR", "RETRYABLE", "DRY_RUN"}:
            state.partial_close_order_id=existing.id
            return existing
    close_side="SELL" if str(position.side).upper()=="LONG" else "BUY"
    order=existing or LiveOrder(deployment_id=deployment.id,signal_id=state.entry_signal_id,user_id=deployment.user_id,broker_account_id=state.broker_account_id,client_order_id=state.idempotency_key,idempotency_key=state.idempotency_key,symbol=position.symbol,side=close_side,order_type="MARKET",action="PARTIAL_EXIT",qty=close_size,entry_price=quote_price,status="PENDING",quantity_mode=state.quantity_mode,instrument_spec_snapshot=state.instrument_spec_snapshot,runtime_config_snapshot=state.runtime_config_snapshot,raw_response={"action":"PARTIAL_EXIT","position_management_state_id":str(state.id),"parent_entry_order_id":str(state.entry_order_id) if state.entry_order_id else None,"local_position_id":str(position.id),"broker_position_id":state.broker_position_id,"expected_runner_size":str(runner),"partial_exit_at_r":str(state.partial_exit_at_r),"partial_exit_percent_requested":str(state.partial_exit_percent)})
    if existing is None:
        db.add(order)
    else:
        order.qty=close_size; order.entry_price=quote_price; order.status="PENDING"; order.error_message=None
        order.raw_response={**(order.raw_response or {}), "retry": True, "expected_runner_size": str(runner)}
    await db.flush(); state.partial_close_order_id=order.id; state.partial_status="TRIGGERED"; state.triggered_at=state.triggered_at or datetime.now(timezone.utc); state.attempt_count=int(state.attempt_count or 0)+1
    if state.attempt_count > 1:
        await log_event(db,deployment,"PARTIAL_EXIT_RETRY","Retrying partial-exit broker action",meta={"management_state_id":str(state.id),"attempt_count":state.attempt_count})
    await log_event(db,deployment,"PARTIAL_EXIT_TRIGGERED","Partial-exit trigger crossed",meta={"position_id":str(position.id),"broker_account_id":str(state.broker_account_id),"is_copy_account":str(state.broker_account_id)!=str(deployment.broker_account_id),"close_size":str(close_size),"runner_size":str(runner),"quote":str(quote_price),"quote_side":quote_side})
    if not settings.live_position_manager_broker_send_enabled:
        order.status="DRY_RUN"; order.raw_response={**(order.raw_response or {}),"dry_run":True}; state.partial_status="PENDING"
        await log_event(db,deployment,"PARTIAL_EXIT_DRY_RUN","Partial exit planned but broker sending is disabled",meta={"position_id":str(position.id),"close_size":str(close_size),"runner_size":str(runner)})
        return order
    code=get_broker_code(broker)
    try:
        if code in {"CTRADER","CTRADER_API"}:
            from ..brokers.ctrader_order_gateway import submit_close_position
            result=await submit_close_position(broker_account_id=str(broker.id),deployment_id=str(deployment.id),broker_position_id=str(state.broker_position_id),qty=close_size,client_order_id=state.idempotency_key,idempotency_key=state.idempotency_key,trace_id=None)
        else:
            adapter=get_broker_adapter(broker,db); result=await adapter.close_position(str(state.broker_position_id),position.side,close_size)
            if code=="MT5" and result.broker_order_id:
                cmd=(await db.execute(select(MT5AgentCommand).where(MT5AgentCommand.id==result.broker_order_id))).scalar_one_or_none()
                if cmd:
                    cmd.request_payload={**(cmd.request_payload or {}),"action":"PARTIAL_EXIT","local_position_id":str(position.id),"position_management_state_id":str(state.id),"expected_runner_size":str(runner),"parent_live_order_id":str(order.id),"idempotency_key":state.idempotency_key}
        order.broker_order_id=result.broker_order_id; order.status=("FILLED" if result.success and str(result.status).upper()=="FILLED" else "PLACED" if result.success else "ERROR"); order.executed_price=result.executed_price if result.success else None; order.error_message=None if result.success else result.message; order.raw_response={**(order.raw_response or {}),**(result.raw_response or {}),"provider":code}
        if result.success:
            state.partial_close_broker_order_id=result.broker_order_id; state.sent_at=datetime.now(timezone.utc); state.partial_status="AWAITING_RECONCILE"
            await log_event(db,deployment,"PARTIAL_EXIT_CLOSE_REQUESTED","Broker partial-close request submitted",meta={"position_id":str(position.id),"broker_position_id":state.broker_position_id,"broker_account_id":str(state.broker_account_id),"is_copy_account":str(state.broker_account_id)!=str(deployment.broker_account_id),"close_size":str(close_size),"provider":code})
            if str(result.status or "").upper() == "FILLED":
                await log_event(db,deployment,"PARTIAL_EXIT_CLOSE_FILLED","Broker reported partial-close command filled; awaiting position reconciliation",meta={"position_id":str(position.id),"broker_position_id":state.broker_position_id,"broker_account_id":str(state.broker_account_id),"is_copy_account":str(state.broker_account_id)!=str(deployment.broker_account_id),"close_size":str(close_size),"provider":code})
            await log_event(db,deployment,"PARTIAL_EXIT_AWAITING_RECONCILE","Waiting for broker runner quantity confirmation",meta={"management_state_id":str(state.id)})
        else:
            state.partial_status="FAILED_RETRYABLE"; state.last_error=result.message
            await log_event(db,deployment,"PARTIAL_EXIT_ERROR",str(result.message or "Partial close failed"),"ERROR",{"management_state_id":str(state.id)})
        return order
    except Exception as exc:
        order.status="ERROR"; order.error_message=str(exc); state.partial_status="FAILED_RETRYABLE"; state.last_error=str(exc)
        await log_event(db,deployment,"PARTIAL_EXIT_ERROR",str(exc),"ERROR",{"management_state_id":str(state.id)})
        return order
