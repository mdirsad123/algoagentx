from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ...core.dependencies import get_current_user, get_db
from ...services.read_only import ReadOnlyService
from ...schemas import Metric

router = APIRouter()


@router.get("/{backtest_id}", response_model=List[Metric])
async def get_backtest_metrics(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get metrics for a backtest
    """
    # First verify ownership
    backtest = await ReadOnlyService.get_backtest_by_id(db, backtest_id)
    if not backtest or str(backtest.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return await ReadOnlyService.get_metrics_by_backtest(db, backtest_id)