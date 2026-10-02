from __future__ import annotations
import asyncio, json, logging, signal
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.models import LivePosition, LivePositionManagementState, StrategyDeployment
from ...db.session import async_session
from ..alerts.quote_bus import QUOTE_CHANNEL
from .deployment_lock import try_deployment_xact_lock
from .live_event_bus import LiveEventBus, worker_identity
from .live_partial_exit_service import TERMINAL, IN_FLIGHT, ensure_management_state, execute_partial_close, finalize_from_broker_truth, norm_symbol, refresh_account_truth
logger=logging.getLogger(__name__)

def parse_dt(v):
    try:
        s=str(v or '').replace('Z','+00:00'); d=datetime.fromisoformat(s); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception: return None

class LivePositionManagerWorker:
    def __init__(self, redis): self.redis=redis; self.bus=LiveEventBus(redis); self.worker_id=worker_identity('live-position-manager'); self.stop_event=asyncio.Event(); self.last_error=None; self.last_result={}
    async def stop(self): self.stop_event.set()
    async def run(self):
        pub=self.redis.pubsub(); await pub.subscribe(QUOTE_CHANNEL)
        health=asyncio.create_task(self._health()); recovery=asyncio.create_task(self._recovery())
        try:
            while not self.stop_event.is_set():
                msg=await pub.get_message(ignore_subscribe_messages=True,timeout=1.0)
                if msg and msg.get('data'): await self._quote(msg['data'])
        finally:
            health.cancel(); recovery.cancel(); await asyncio.gather(health,recovery,return_exceptions=True); await pub.unsubscribe(QUOTE_CHANNEL); await pub.close()
    async def _recovery(self):
        while not self.stop_event.is_set():
            try:
                async with async_session() as db:
                    deps=(await db.execute(select(StrategyDeployment).where(StrategyDeployment.status=='RUNNING',StrategyDeployment.partial_exit_enabled.is_(True)))).scalars().all()
                    created=0; repaired=0
                    for dep in deps:
                        positions=(await db.execute(select(LivePosition).where(LivePosition.deployment_id==dep.id,LivePosition.status=='OPEN'))).scalars().all()
                        for p in positions:
                            st=await ensure_management_state(db,dep,p); created += 1 if st and st.created_at==st.updated_at else 0
                    # Repair stale states for positions that SL/TP/manual/full-close already removed.
                    # This applies independently to the primary and every copy account.
                    stale_closed = (await db.execute(
                        select(LivePositionManagementState, LivePosition)
                        .join(LivePosition, LivePosition.id == LivePositionManagementState.live_position_id)
                        .where(
                            LivePosition.status != 'OPEN',
                            LivePositionManagementState.partial_status.notin_([
                                'DONE','SKIPPED_MIN_SIZE','FAILED_TERMINAL','BROKER_POSITION_CLOSED'
                            ]),
                        )
                    )).all()
                    closed_repaired = 0
                    for st, pos in stale_closed:
                        st.partial_status='BROKER_POSITION_CLOSED'
                        st.filled_at=st.filled_at or datetime.now(timezone.utc)
                        st.last_error=None
                        closed_repaired += 1

                    states=(await db.execute(select(LivePositionManagementState).where(LivePositionManagementState.partial_status.in_(['TRIGGERED','CLOSE_SENT','AWAITING_RECONCILE','FAILED_RETRYABLE'])))).scalars().all()
                    for st in states:
                        dep=(await db.execute(select(StrategyDeployment).where(StrategyDeployment.id==st.deployment_id))).scalar_one_or_none()
                        if not dep: continue
                        if not await try_deployment_xact_lock(db,dep.id): await db.rollback(); continue
                        await refresh_account_truth(db,dep,st.broker_account_id); repaired += 1 if await finalize_from_broker_truth(db,st,dep) else 0
                    await db.commit(); self.last_result={'states_created_or_seen':created,'reconciled':repaired,'closed_states_repaired':closed_repaired}
            except Exception as exc: self.last_error=str(exc); logger.exception('Position-manager recovery failed')
            try: await asyncio.wait_for(self.stop_event.wait(),timeout=max(1,int(settings.live_position_manager_recovery_scan_seconds)))
            except asyncio.TimeoutError: pass
    async def _quote(self,data):
        try:
            raw=data.decode() if isinstance(data,(bytes,bytearray)) else str(data); q=json.loads(raw); account=str(q.get('broker_account_id') or ''); symbol=norm_symbol(q.get('symbol'));
            if not account or not symbol: return
            market=parse_dt(q.get('market_timestamp')); received=parse_dt(q.get('server_received_at')) or datetime.now(timezone.utc); stamp=market or received
            if (datetime.now(timezone.utc)-stamp).total_seconds()>max(1,int(settings.live_position_manager_quote_max_age_seconds)): return
            async with async_session() as db:
                account_uuid=UUID(account)
                rows=(await db.execute(select(LivePositionManagementState,LivePosition,StrategyDeployment).join(LivePosition,LivePosition.id==LivePositionManagementState.live_position_id).join(StrategyDeployment,StrategyDeployment.id==LivePositionManagementState.deployment_id).where(LivePositionManagementState.broker_account_id==account_uuid,LivePositionManagementState.partial_status.in_(['PENDING','TRIGGERED','FAILED_RETRYABLE']),LivePosition.status=='OPEN',StrategyDeployment.status=='RUNNING'))).all()
                for st,pos,dep in rows:
                    if norm_symbol(pos.symbol)!=symbol: continue
                    side=str(pos.side).upper(); bid=q.get('bid'); ask=q.get('ask'); last=q.get('price')
                    qp=Decimal(str(bid if side=='LONG' and bid is not None else ask if side=='SHORT' and ask is not None else last)); qside='BID' if side=='LONG' and bid is not None else 'ASK' if side=='SHORT' and ask is not None else 'LAST'
                    crossed=qp>=Decimal(str(st.partial_trigger_price)) if side=='LONG' else qp<=Decimal(str(st.partial_trigger_price))
                    if not crossed: continue
                    if st.partial_status == 'FAILED_RETRYABLE':
                        backoffs = (1, 2, 5, 10, 30)
                        wait_s = backoffs[min(max(int(st.attempt_count or 1) - 1, 0), len(backoffs) - 1)]
                        updated = st.updated_at or st.triggered_at or datetime.now(timezone.utc)
                        if updated.tzinfo is None: updated = updated.replace(tzinfo=timezone.utc)
                        if (datetime.now(timezone.utc) - updated).total_seconds() < wait_s:
                            continue
                    if not await try_deployment_xact_lock(db,dep.id): await db.rollback(); continue
                    st=(await db.execute(select(LivePositionManagementState).where(LivePositionManagementState.id==st.id).with_for_update())).scalar_one()
                    if st.partial_status in TERMINAL or st.partial_status in IN_FLIGHT: continue
                    await refresh_account_truth(db,dep,st.broker_account_id)
                    pos=(await db.execute(select(LivePosition).where(LivePosition.id==st.live_position_id))).scalar_one_or_none()
                    if not pos or pos.status!='OPEN': st.partial_status='BROKER_POSITION_CLOSED'; continue
                    await execute_partial_close(db,dep,st,pos,qp,qside)
                    await db.commit()
        except Exception as exc: self.last_error=str(exc); logger.exception('Position-manager quote handling failed')
    async def _health(self):
        while not self.stop_event.is_set():
            await self.bus.heartbeat('live_position_manager_worker',self.worker_id,{'status':'DEGRADED' if self.last_error else 'HEALTHY','last_error':self.last_error,'last_result':self.last_result,'broker_send_enabled':settings.live_position_manager_broker_send_enabled,'demo_only':settings.live_position_manager_demo_only})
            try: await asyncio.wait_for(self.stop_event.wait(),timeout=5)
            except asyncio.TimeoutError: pass

async def main():
    if not await redis_manager.initialize(): raise RuntimeError('Redis is required by live_position_manager_worker')
    if not settings.live_position_manager_worker_enabled:
        logger.warning('live_position_manager_worker is disabled')
        bus = LiveEventBus(redis_manager.client)
        wid = worker_identity('live-position-manager')
        try:
            while True:
                await bus.heartbeat('live_position_manager_worker', wid, {'status':'DISABLED','broker_send_enabled':False})
                await asyncio.sleep(5)
        finally:
            await redis_manager.close()
    w=LivePositionManagerWorker(redis_manager.client); loop=asyncio.get_running_loop()
    for s in (signal.SIGINT,signal.SIGTERM):
        try: loop.add_signal_handler(s,lambda: asyncio.create_task(w.stop()))
        except NotImplementedError: pass
    try: await w.run()
    finally: await redis_manager.close()
if __name__=='__main__': asyncio.run(main())
