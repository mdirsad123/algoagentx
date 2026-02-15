from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class ScreenerNewsBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    stock_name: str = Field(..., description="Stock name")
    news_date: date = Field(..., description="News date")
    title: str = Field(..., description="News title")
    summary: Optional[str] = Field(None, description="News summary")
    url: str = Field(..., description="News URL")
    source: str = Field(..., description="News source")
    sentiment_label: str = Field(..., description="Sentiment label (VERY_POSITIVE/POSITIVE/NEUTRAL/NEGATIVE/VERY_NEGATIVE)")
    sentiment_score: float = Field(..., description="Sentiment score")
    confidence: Optional[float] = Field(None, description="Confidence score")


class ScreenerNewsCreate(ScreenerNewsBase):
    pass


class ScreenerNewsResponse(ScreenerNewsBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ScreenerAnnouncementsBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    stock_name: str = Field(..., description="Stock name")
    exchange: str = Field(..., description="Exchange (NSE/BSE)")
    announce_date: date = Field(..., description="Announcement date")
    title: str = Field(..., description="Announcement title")
    url: str = Field(..., description="Announcement URL")
    category: Optional[str] = Field(None, description="Announcement category")


class ScreenerAnnouncementsCreate(ScreenerAnnouncementsBase):
    pass


class ScreenerAnnouncementsResponse(ScreenerAnnouncementsBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ScreenerRunsBase(BaseModel):
    run_type: str = Field(..., description="Run type (NEWS/ANNOUNCEMENTS)")
    status: str = Field(..., description="Run status (RUNNING/SUCCESS/FAILED)")
    error: Optional[str] = Field(None, description="Error message if failed")
    meta: Optional[dict] = Field(None, description="Additional metadata")


class ScreenerRunsCreate(ScreenerRunsBase):
    pass


class ScreenerRunsResponse(ScreenerRunsBase):
    id: UUID
    started_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True