"""Read-only UI enrichment from existing broker events; no broker I/O/schema change."""
from datetime import datetime, timezone
from sqlalchemy import select
from ...db.models import BrokerOrderEvent


async def attach_protection(db, deployment_id, positions):
    accounts = {str(p['broker_account_id']) for p in positions
                if p.get('broker_code') == 'TRADELOCKER' and p.get('broker_account_id')}
    for account in accounts:
        event = (await db.execute(select(BrokerOrderEvent).where(
            BrokerOrderEvent.deployment_id == deployment_id,
            BrokerOrderEvent.broker_account_id == account,
            BrokerOrderEvent.event_type == 'BROKER_POSITION_SYNC',
        ).order_by(BrokerOrderEvent.created_at.desc()).limit(1))).scalar_one_or_none()
        payload = event.raw_payload if event else None
        rows = payload.get('positions', []) if isinstance(payload, dict) else []
        by_id = {str(p.get('broker_position_id') or p.get('id')): p
                 for p in (rows if isinstance(rows, list) else []) if isinstance(p, dict)}
        for position in positions:
            if str(position.get('broker_account_id')) != account:
                continue
            protection = by_id.get(str(position.get('broker_position_id')), {}).get('protection') or {}
            if not isinstance(protection, dict):
                protection = {}
            verified = False
            try:
                checked = datetime.fromisoformat(protection['checked_at'])
                verified = protection.get('status') == 'VERIFIED' and 0 <= (datetime.now(timezone.utc) - checked).total_seconds() <= 120
            except (KeyError, ValueError, TypeError):
                pass
            position['protection_status'] = 'VERIFIED' if verified else 'UNVERIFIED'
            position['protection_checked_at'] = protection.get('checked_at')
            position['protection_warning'] = None if verified else 'Broker-side SL/TP is unverified or stale. Check TradeLocker; entry history is not proof of active protection.'
            # Report only current broker evidence, not a management fallback.
            position['stop_loss'] = protection.get('stop_loss') if verified else None
            position['target'] = protection.get('target') if verified else None