"""
Billing-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class PlanResponse(BaseModel):
    """Response schema for plan information"""
    code: str = Field(..., description="Plan code (FREE, PRO, PREMIUM, ULTIMATE)")
    billing_period: str = Field(..., description="Billing period (NONE, MONTHLY, YEARLY)")
    price_inr: int = Field(..., description="Price in INR")
    included_credits: int = Field(..., description="Included credits per billing period")
    features: Dict[str, Any] = Field(..., description="Plan features and limits")
    is_active: bool = Field(..., description="Whether plan is active")
    
    class Config:
        from_attributes = True


class CostPreviewRequest(BaseModel):
    """Request schema for cost preview"""
    type: str = Field(..., description="Cost type: backtest or ai_screener")
    start_date: Optional[datetime] = Field(None, description="Backtest start date")
    end_date: Optional[datetime] = Field(None, description="Backtest end date")
    timeframe: Optional[str] = Field(None, description="Chart timeframe")
    mode: Optional[str] = Field(None, description="AI screener mode")
    depth: Optional[str] = Field(None, description="AI screener depth")
    
    @validator('type')
    def validate_cost_type(cls, v):
        if v not in ['backtest', 'ai_screener']:
            raise ValueError('Cost type must be backtest or ai_screener')
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        if v:
            valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
            if v.lower() not in valid_timeframes:
                raise ValueError(f'Invalid timeframe. Must be one of: {", ".join(valid_timeframes)}')
        return v
    
    @validator('mode')
    def validate_mode(cls, v):
        if v:
            valid_modes = ['basic', 'advanced', 'deep']
            if v.lower() not in valid_modes:
                raise ValueError(f'Invalid mode. Must be one of: {", ".join(valid_modes)}')
        return v
    
    @validator('depth')
    def validate_depth(cls, v):
        if v:
            valid_depths = ['light', 'medium', 'deep']
            if v.lower() not in valid_depths:
                raise ValueError(f'Invalid depth. Must be one of: {", ".join(valid_depths)}')
        return v


class CostPreviewResponse(BaseModel):
    """Response schema for cost preview"""
    type: str = Field(..., description="Cost type")
    total_cost: int = Field(..., description="Total cost in credits")
    breakdown: Dict[str, Any] = Field(..., description="Detailed cost breakdown")
    
    class Config:
        from_attributes = True


class CostBreakdown(BaseModel):
    """Cost breakdown details"""
    type: str
    base_cost: int
    multipliers: Dict[str, Any]
    total_cost: int
    details: Dict[str, Any]