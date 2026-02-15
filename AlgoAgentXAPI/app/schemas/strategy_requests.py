from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class StrategyRequestBase(BaseModel):
    title: str = Field(..., description="Title of the strategy request")
    strategy_type: Optional[str] = Field(None, description="Type of strategy (e.g., trend, mean reversion)")
    market: Optional[str] = Field(None, description="Market type (e.g., equity, forex, crypto)")
    timeframe: Optional[str] = Field(None, description="Timeframe for the strategy (e.g., 1m, 5m, 1h, 1d)")
    indicators: Optional[Dict[str, Any]] = Field(None, description="Indicators configuration as JSON")
    entry_rules: str = Field(..., description="Entry rules for the strategy")
    exit_rules: str = Field(..., description="Exit rules for the strategy")
    risk_rules: str = Field(..., description="Risk management rules")
    notes: Optional[str] = Field(None, description="Additional notes")


class StrategyRequestCreate(StrategyRequestBase):
    pass


class StrategyRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the strategy request")
    strategy_type: Optional[str] = Field(None, description="Type of strategy")
    market: Optional[str] = Field(None, description="Market type")
    timeframe: Optional[str] = Field(None, description="Timeframe for the strategy")
    indicators: Optional[Dict[str, Any]] = Field(None, description="Indicators configuration as JSON")
    entry_rules: Optional[str] = Field(None, description="Entry rules for the strategy")
    exit_rules: Optional[str] = Field(None, description="Exit rules for the strategy")
    risk_rules: Optional[str] = Field(None, description="Risk management rules")
    notes: Optional[str] = Field(None, description="Additional notes")


class StrategyRequestAdminUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Status of the strategy request")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    assigned_to: Optional[str] = Field(None, description="User assigned to handle this request")
    deployed_strategy_id: Optional[UUID] = Field(None, description="ID of the deployed strategy")


class StrategyRequestAdminListResponse(BaseModel):
    id: UUID
    title: str
    strategy_type: Optional[str]
    market: Optional[str]
    timeframe: Optional[str]
    status: str
    user_id: str
    user_email: Optional[str] = Field(None, description="User email for admin reference")
    user_name: Optional[str] = Field(None, description="User name for admin reference")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRequestAdminDetailResponse(StrategyRequestBase):
    id: UUID
    user_id: str
    user_email: Optional[str] = Field(None, description="User email for admin reference")
    user_name: Optional[str] = Field(None, description="User name for admin reference")
    status: str
    admin_notes: Optional[str]
    assigned_to: Optional[str]
    deployed_strategy_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRequestResponse(StrategyRequestBase):
    id: UUID
    user_id: str
    status: str
    admin_notes: Optional[str]
    assigned_to: Optional[str]
    deployed_strategy_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRequestListResponse(BaseModel):
    id: UUID
    title: str
    strategy_type: Optional[str]
    market: Optional[str]
    timeframe: Optional[str]
    status: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRequestOut(StrategyRequestBase):
    id: UUID
    user_id: str
    status: str
    admin_notes: Optional[str]
    assigned_to: Optional[str]
    deployed_strategy_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
