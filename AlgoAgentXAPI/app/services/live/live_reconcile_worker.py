"""Slow safety/repair reconciliation isolated from the order hot path."""

from __future__ import annotations

import asyncio
import logging
import signal
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.models import BrokerAccount, StrategyDeployment
from ...db.session import async_session
from ..brokers.factory import get_broker_code
from .broker_sync_service import (
    sync_copy_target_positions,
    sync_ctrader_account_positions_via_gateway,
    sync_ctrader_deployment_via_gateway,
    sync_deployment_broker_state,
)
from .live_event_bus import LiveEventBus, worker_identity
from .deployment_lock import try_deployment_xact_lock

logger = logging.getLogger(__name__)


class LiveReconcileWorker:
    def __init__(self, redis_client: Any):
        self.bus = LiveEventBus(redis_client)
        self.worker_id = worker_identity("live-reconcile")
        self._stop = asyncio.Event()
        self._semaphore = asyncio.Semaphore(max(1, int(settings.live_worker_concurrency)))
        self._last_error: str | None = None
        self._last_result: dict[str, Any] = {}

    async def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        health_task = asyncio.create_task(self._health_loop())
        try:
            while not self._stop.is_set():
                await self._run_cycle()
                try:
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=max(5, int(settings.live_reconcile_interval_seconds)),
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            health_task.cancel()
            await asyncio.gather(health_task, return_exceptions=True)

    async def _run_cycle(self) -> None:
        async with async_session() as db:
            rows = (
                await db.execute(
                    select(StrategyDeployment.id, BrokerAccount)
                    .join(BrokerAccount, BrokerAccount.id == StrategyDeployment.broker_account_id)
                    .where(
                        StrategyDeployment.status == "RUNNING",
                        StrategyDeployment.broker_account_id.is_not(None),
                        BrokerAccount.status == "CONNECTED",
                    )
                )
            ).all()
        tasks = [
            asyncio.create_task(self._sync_one(deployment_id, get_broker_code(broker)))
            for deployment_id, broker in rows
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [str(result) for result in results if isinstance(result, Exception)]
        self._last_error = errors[-1] if errors else None
        self._last_result = {
            "checked": len(rows),
            "synced": len(rows) - len(errors),
            "errors": errors[:20],
        }

    async def _sync_one(self, deployment_id: Any, broker_code: str) -> dict[str, Any]:
        async with self._semaphore:
            # 1) Primary account keeps the existing reconciliation path.
            async with async_session() as db:
                if not await try_deployment_xact_lock(db, deployment_id):
                    await db.rollback()
                    return {
                        "success": True,
                        "deployment_id": str(deployment_id),
                        "synced": False,
                        "skipped": "DEPLOYMENT_BUSY",
                    }
                if broker_code in {"CTRADER", "CTRADER_API"} and settings.ctrader_persistent_connection_enabled:
                    primary = await sync_ctrader_deployment_via_gateway(db, deployment_id)
                else:
                    primary = await sync_deployment_broker_state(db, deployment_id)

            # 2) Copy accounts are reconciled independently AFTER primary truth is
            # safely committed. This is essential for asynchronous MT5 copies:
            # the MT5 entry command may fill at the terminal after execute_signal
            # returns, so only broker reconciliation can create its LivePosition.
            copy_results: list[dict[str, Any]] = []
            async with async_session() as db:
                if not await try_deployment_xact_lock(db, deployment_id):
                    await db.rollback()
                    return {**primary, "copy_accounts": copy_results, "copy_sync_skipped": "DEPLOYMENT_BUSY"}

                deployment = (await db.execute(
                    select(StrategyDeployment).where(StrategyDeployment.id == deployment_id)
                )).scalar_one_or_none()
                if deployment is None:
                    return {**primary, "copy_accounts": copy_results}

                copy_enabled = bool(
                    settings.live_copy_trading_enabled
                    and bool(getattr(deployment, "copy_trading_enabled", False))
                    and str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "STANDARD"
                )
                raw_ids = list(getattr(deployment, "copy_broker_account_ids", None) or []) if copy_enabled else []
                seen = {str(deployment.broker_account_id)} if deployment.broker_account_id else set()
                for raw_id in raw_ids:
                    if not raw_id or str(raw_id) in seen:
                        continue
                    seen.add(str(raw_id))
                    broker = (await db.execute(
                        select(BrokerAccount).where(
                            BrokerAccount.id == raw_id,
                            BrokerAccount.user_id == deployment.user_id,
                        )
                    )).scalar_one_or_none()
                    if broker is None or str(broker.status or "").upper() != "CONNECTED":
                        copy_results.append({"broker_account_id": str(raw_id), "synced": False, "skipped": "DISCONNECTED"})
                        continue
                    if str(getattr(broker, "mode", "") or "").upper() != str(getattr(deployment, "mode", "") or "").upper():
                        copy_results.append({"broker_account_id": str(raw_id), "synced": False, "skipped": "MODE_MISMATCH"})
                        continue

                    try:
                        code = get_broker_code(broker)
                        if code in {"CTRADER", "CTRADER_API"} and settings.ctrader_persistent_connection_enabled:
                            result = await sync_ctrader_account_positions_via_gateway(db, deployment, broker.id)
                        else:
                            snapshot = {c.name: getattr(deployment, c.name) for c in StrategyDeployment.__table__.columns}
                            proxy = SimpleNamespace(**snapshot)
                            proxy.broker_account_id = broker.id
                            result = await sync_copy_target_positions(db, proxy)
                        copy_results.append({"broker_account_id": str(broker.id), "synced": True, **result})
                    except Exception as exc:
                        logger.warning("Copy-account reconcile failed deployment=%s account=%s: %s", deployment_id, raw_id, exc)
                        copy_results.append({"broker_account_id": str(raw_id), "synced": False, "error": str(exc)})

                await db.commit()

            return {**primary, "copy_accounts": copy_results}

    async def _health_loop(self) -> None:
        while not self._stop.is_set():
            await self.bus.heartbeat(
                "live_reconcile_worker",
                self.worker_id,
                {
                    "status": "DEGRADED" if self._last_error else "HEALTHY",
                    "last_error": self._last_error,
                    "last_result": self._last_result,
                },
            )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    if not (settings.live_event_pipeline_enabled and settings.live_reconcile_worker_enabled):
        logger.warning("Live reconcile worker is idle because its feature flags are disabled")
        while True:
            await asyncio.sleep(3600)
    if not await redis_manager.initialize():
        raise RuntimeError("Redis is required by live_reconcile_worker")
    worker = LiveReconcileWorker(redis_manager.client)
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signame, lambda: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            pass
    try:
        await worker.run()
    finally:
        await redis_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
