"""Read-only deployment/session diagnostic; pipe into the API container's Python.

Never prints credentials, account metadata, HTTP bodies or exception messages.
"""
import asyncio
import json
import logging
from uuid import UUID

from sqlalchemy import select, text
from app.db.session import async_session
from app.db.models import BrokerAccount, StrategyDeployment
from app.services.brokers.factory import get_broker_adapter


async def main():
    logging.disable(logging.CRITICAL)
    async with async_session() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        deployment = (await db.execute(select(StrategyDeployment).where(
            StrategyDeployment.id == UUID('75daebe6-ccb4-4197-af61-e8048ca6eb60')))).scalar_one()
        broker = (await db.execute(select(BrokerAccount).where(
            BrokerAccount.id == deployment.broker_account_id))).scalar_one()
        adapter = get_broker_adapter(broker, db)
        stage = 'instrument'
        output = {'deployment': str(deployment.id), 'cursor': str(deployment.last_processed_candle_time)}
        try:
            info = await adapter._instrument(str(deployment.broker_symbol or deployment.instrument))
            output['instrument'] = {k: info.get(k) for k in ('tradableInstrumentId', 'name', 'routes')}
            stage = 'details'
            details = await adapter._request('GET', f'/trade/instruments/{info["tradableInstrumentId"]}',
                                             params={'routeId': adapter._route(info, 'TRADE')})
            data = details.get('d') or {}
            output['detail_keys'] = sorted(data)
            output['tradeSessionId'] = data.get('tradeSessionId')
            stage = 'session'
            session = await adapter._request('GET', f'/trade/sessions/{data["tradeSessionId"]}')
            calendar = session.get('d') or {}
            output['session_keys'] = sorted(calendar)
            allowed = ('timeZone', 'blockTrading', 'holidays', 'session_preopen',
                       'session_beforemarket', 'session_regular', 'session_aftermarket', 'session_postclose')
            output['calendar'] = {k: calendar[k] for k in allowed if k in calendar}
        except Exception as exc:
            output['error'] = {'stage': stage, 'type': type(exc).__name__}
        finally:
            await db.rollback()
            await adapter._http_client().aclose()
        print(json.dumps(output, default=str, indent=2))


asyncio.run(main())