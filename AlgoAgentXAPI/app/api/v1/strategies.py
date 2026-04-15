from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import PerformanceMetric, Strategy, StrategyRequest, User
from ...utils.api_response import success_response

router = APIRouter()


class StrategyRequestIn(BaseModel):
    title: str = Field(..., min_length=3)
    strategy_type: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None
    indicators: Optional[dict] = None
    entry_rules: str
    exit_rules: str
    risk_rules: str
    notes: Optional[str] = None


def _serialize_strategy(row: Strategy, metrics: Optional[dict] = None) -> dict:
    return {
        'id': str(row.id),
        'name': row.name,
        'description': row.description,
        'parameters': row.parameters or {},
        'created_by': str(row.created_by) if row.created_by else None,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'metrics': metrics or {},
    }


async def _strategy_metrics_map(db: AsyncSession, strategy_ids: list[str]) -> dict[str, dict]:
    if not strategy_ids:
        return {}
    result = await db.execute(
        select(
            PerformanceMetric.strategy_id,
            func.avg(PerformanceMetric.win_rate),
            func.avg(PerformanceMetric.sharpe_ratio),
            func.avg(PerformanceMetric.max_drawdown),
            func.avg(PerformanceMetric.total_trades),
            func.count(PerformanceMetric.id),
        )
        .where(PerformanceMetric.strategy_id.in_(strategy_ids))
        .group_by(PerformanceMetric.strategy_id)
    )
    return {
        str(sid): {
            'win_rate': float(win_rate) if win_rate is not None else None,
            'sharpe_ratio': float(sharpe_ratio) if sharpe_ratio is not None else None,
            'max_drawdown': float(max_drawdown) if max_drawdown is not None else None,
            'total_trades': int(total_trades) if total_trades is not None else None,
            'runs': int(runs or 0),
        }
        for sid, win_rate, sharpe_ratio, max_drawdown, total_trades, runs in result.all()
    }


@router.get('/')
async def get_strategies(approved_only: bool = Query(True), db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stmt = select(Strategy).order_by(Strategy.created_at.desc())
    if approved_only and await table_has_column(db, 'strategy_requests', 'deployed_strategy_id'):
        deployed_ids_stmt = select(StrategyRequest.deployed_strategy_id).where(
            StrategyRequest.status == 'DEPLOYED', StrategyRequest.deployed_strategy_id.is_not(None)
        )
        deployed_ids = [str(row[0]) for row in (await db.execute(deployed_ids_stmt)).all() if row[0] is not None]
        if deployed_ids:
            stmt = stmt.where(Strategy.id.in_(deployed_ids))
    rows = (await db.execute(stmt)).scalars().all()
    metrics_map = await _strategy_metrics_map(db, [str(row.id) for row in rows])
    data = [_serialize_strategy(row, metrics_map.get(str(row.id))) for row in rows]
    return success_response(data, 'No data found' if not data else None)


@router.get('/templates')
async def get_strategy_templates(db: AsyncSession = Depends(get_db)):
    stmt = select(Strategy).where(or_(Strategy.created_by.is_(None), column_text(Strategy.created_by) == '0')).order_by(Strategy.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    metrics_map = await _strategy_metrics_map(db, [str(row.id) for row in rows])
    data = [_serialize_strategy(row, metrics_map.get(str(row.id))) for row in rows]
    return success_response(data, 'No data found' if not data else None)


@router.get('/my')
async def get_my_strategies(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Strategy).where(column_text(Strategy.created_by) == str(current_user['user_id'])).order_by(Strategy.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    metrics_map = await _strategy_metrics_map(db, [str(row.id) for row in rows])
    data = [_serialize_strategy(row, metrics_map.get(str(row.id))) for row in rows]
    return success_response(data, 'No data found' if not data else None)


@router.post('/request', status_code=status.HTTP_201_CREATED)
async def request_strategy(payload: StrategyRequestIn, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = StrategyRequest(
        user_id=as_uuid_or_str(current_user['user_id']),
        title=payload.title,
        strategy_type=payload.strategy_type,
        market=payload.market,
        timeframe=payload.timeframe,
        indicators=payload.indicators,
        entry_rules=payload.entry_rules,
        exit_rules=payload.exit_rules,
        risk_rules=payload.risk_rules,
        notes=payload.notes,
        status='UNDER_DEVELOPMENT',
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response({'id': str(row.id), 'status': row.status}, 'Strategy request submitted successfully')


@router.get('/admin')
async def get_admin_strategies(skip: int = 0, limit: int = Query(20, ge=1, le=100), search: Optional[str] = None, status_filter: Optional[str] = Query(None, alias='status'), db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    stmt = select(StrategyRequest, User.email, User.fullname).join(User, User.id == StrategyRequest.user_id)
    count_stmt = select(func.count()).select_from(StrategyRequest).join(User, User.id == StrategyRequest.user_id)
    filters = []
    if search:
        like = f'%{search}%'; filters.append(or_(StrategyRequest.title.ilike(like), User.email.ilike(like), User.fullname.ilike(like)))
    if status_filter:
        filters.append(StrategyRequest.status == status_filter)
    if filters:
        stmt = stmt.where(*filters); count_stmt = count_stmt.where(*filters)
    rows = (await db.execute(stmt.order_by(StrategyRequest.created_at.desc()).offset(skip).limit(limit))).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    has_deployed = await table_has_column(db, 'strategy_requests', 'deployed_strategy_id')
    data = [{
        'id': str(req.id),
        'title': req.title,
        'strategy_type': req.strategy_type,
        'market': req.market,
        'timeframe': req.timeframe,
        'status': req.status,
        'user_id': str(req.user_id),
        'user_email': email,
        'user_name': fullname or email,
        'admin_notes': req.admin_notes,
        'deployed_strategy_id': str(req.deployed_strategy_id) if has_deployed and getattr(req, 'deployed_strategy_id', None) else None,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'updated_at': req.updated_at.isoformat() if req.updated_at else None,
    } for req, email, fullname in rows]
    return success_response({'items': data, 'total': total, 'skip': skip, 'limit': limit}, 'No data found' if not data else None)


@router.patch('/admin/{request_id}')
async def update_admin_strategy(request_id: str, payload: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    req = (await db.execute(select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id)))).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail='Strategy request not found')
    status_value = payload.get('status')
    admin_notes = payload.get('admin_notes')
    if status_value:
        req.status = status_value
    if admin_notes is not None:
        req.admin_notes = admin_notes
    has_deployed = await table_has_column(db, 'strategy_requests', 'deployed_strategy_id')
    deployed_val = getattr(req, 'deployed_strategy_id', None) if has_deployed else None
    if status_value == 'DEPLOYED' and not deployed_val:
        strategy = Strategy(
            id=str(req.id),
            name=req.title,
            description=req.notes or req.entry_rules,
            parameters={
                'strategy_type': req.strategy_type, 'market': req.market, 'timeframe': req.timeframe,
                'indicators': req.indicators, 'entry_rules': req.entry_rules, 'exit_rules': req.exit_rules, 'risk_rules': req.risk_rules,
            },
            created_by=req.user_id,
        )
        db.add(strategy)
        await db.flush()
        if has_deployed:
            req.deployed_strategy_id = as_uuid_or_str(strategy.id)
    await db.commit()
    return success_response({'id': str(req.id), 'status': req.status}, 'Strategy updated successfully')
