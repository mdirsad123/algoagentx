from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from datetime import datetime

from ...core.dependencies import get_db, get_current_user
from ...services.read_only import ReadOnlyService
from ...schemas import Strategy, StrategyTemplateResponse, StrategyMyResponse

router = APIRouter()


@router.get("/", response_model=List[Strategy])
async def get_strategies(db: AsyncSession = Depends(get_db)):
    """
    Get all strategies (read-only)
    """
    return await ReadOnlyService.get_all_strategies(db)


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy_by_id(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get strategy by ID (read-only)
    """
    strategies = await ReadOnlyService.get_all_strategies(db)
    for strategy in strategies:
        if strategy.id == strategy_id:
            return strategy
    raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/templates", response_model=List[StrategyTemplateResponse])
async def get_strategy_templates(db: AsyncSession = Depends(get_db)):
    """
    Get all template strategies (no auth required)
    Returns strategies used on Templates tab
    Filter: template strategies only (is_template=true OR owner_user_id is null)
    """
    try:
        # Query template strategies - strategies with no owner (template strategies)
        # or strategies marked as templates
        stmt = text("""
            SELECT s.id, s.name, s.description, s.created_at as last_updated,
                   NULL as win_rate, NULL as sharpe_ratio, NULL as total_trades,
                   NULL as max_drawdown, NULL as profit_factor
            FROM strategies s
            WHERE s.created_by IS NULL OR s.created_by = 0
            ORDER BY s.created_at DESC
        """)
        
        result = await db.execute(stmt)
        template_strategies = result.fetchall()
        
        # Convert to response models
        return [
            StrategyTemplateResponse(
                id=strategy.id,
                name=strategy.name,
                description=strategy.description,
                status="active",
                win_rate=strategy.win_rate,
                sharpe_ratio=strategy.sharpe_ratio,
                total_trades=strategy.total_trades,
                max_drawdown=strategy.max_drawdown,
                profit_factor=strategy.profit_factor,
                last_updated=strategy.last_updated
            )
            for strategy in template_strategies
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve template strategies: {str(e)}"
        )


@router.get("/my", response_model=List[StrategyMyResponse])
async def get_user_strategies(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get deployed strategies for current user only (auth required)
    Definition: strategies where owner_user_id = current user AND deployed_at not null
    """
    try:
        # Query user's deployed strategies
        # Note: The current schema doesn't have deployed_at field, so we'll return
        # all strategies owned by the user for now
        stmt = text("""
            SELECT s.id, s.name, s.description, s.created_at as last_updated,
                   NULL as win_rate, NULL as sharpe_ratio, NULL as total_trades,
                   NULL as max_drawdown, NULL as profit_factor
            FROM strategies s
            WHERE s.created_by = :user_id
            ORDER BY s.created_at DESC
        """)
        
        result = await db.execute(stmt, {"user_id": current_user["user_id"]})
        user_strategies = result.fetchall()
        
        # Convert to response models
        return [
            StrategyMyResponse(
                id=strategy.id,
                name=strategy.name,
                description=strategy.description,
                status="active",
                win_rate=strategy.win_rate,
                sharpe_ratio=strategy.sharpe_ratio,
                total_trades=strategy.total_trades,
                max_drawdown=strategy.max_drawdown,
                profit_factor=strategy.profit_factor,
                last_updated=strategy.last_updated
            )
            for strategy in user_strategies
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user strategies: {str(e)}"
        )
