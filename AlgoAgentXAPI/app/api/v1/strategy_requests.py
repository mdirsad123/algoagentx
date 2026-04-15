from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import StrategyRequest
from ...schemas.strategy_requests import StrategyRequestCreate
from ...utils.api_response import success_response

router = APIRouter()


def _serialize(req: StrategyRequest, has_deployed: bool = True) -> dict:
    return {
        'id': str(req.id), 'user_id': str(req.user_id), 'title': req.title, 'strategy_type': req.strategy_type, 'market': req.market, 'timeframe': req.timeframe,
        'indicators': req.indicators, 'entry_rules': req.entry_rules, 'exit_rules': req.exit_rules, 'risk_rules': req.risk_rules, 'notes': req.notes, 'status': req.status,
        'admin_notes': req.admin_notes, 'assigned_to': req.assigned_to,
        'deployed_strategy_id': str(req.deployed_strategy_id) if has_deployed and getattr(req, 'deployed_strategy_id', None) else None,
        'created_at': req.created_at.isoformat() if req.created_at else None, 'updated_at': req.updated_at.isoformat() if req.updated_at else None,
    }


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_strategy_request(request_data: StrategyRequestCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = StrategyRequest(user_id=as_uuid_or_str(current_user['user_id']), title=request_data.title, strategy_type=request_data.strategy_type, market=request_data.market, timeframe=request_data.timeframe, indicators=request_data.indicators, entry_rules=request_data.entry_rules, exit_rules=request_data.exit_rules, risk_rules=request_data.risk_rules, notes=request_data.notes, status='UNDER_DEVELOPMENT')
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize(row, await table_has_column(db, 'strategy_requests', 'deployed_strategy_id')), 'Strategy request submitted successfully')


@router.get('/me')
async def get_user_strategy_requests(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(StrategyRequest).where(column_text(StrategyRequest.user_id) == str(current_user['user_id'])).order_by(StrategyRequest.created_at.desc()))).scalars().all()
    has_deployed = await table_has_column(db, 'strategy_requests', 'deployed_strategy_id')
    data = [_serialize(r, has_deployed) for r in rows]
    return success_response(data, 'No data found' if not data else None)
