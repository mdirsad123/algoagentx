from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ...core.dependencies import get_current_user, get_db

router = APIRouter()


@router.get("/")
async def get_signals(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI signals (placeholder - signals table not yet implemented)
    """
    # Placeholder implementation
    # In future, this would query signals table
    return {
        "message": "Signals endpoint - table not yet implemented",
        "signals": []
    }