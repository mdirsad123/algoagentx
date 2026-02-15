from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ...core.dependencies import get_db
from ...services.read_only import ReadOnlyService
from ...schemas import Instrument

router = APIRouter()


@router.get("/", response_model=List[Instrument])
async def get_instruments(db: AsyncSession = Depends(get_db)):
    """
    Get all instruments (read-only)
    """
    return await ReadOnlyService.get_all_instruments(db)