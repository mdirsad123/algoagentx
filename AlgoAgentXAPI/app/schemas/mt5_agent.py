from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MT5AgentRegisterIn(BaseModel):
    broker_account_id: UUID
    trading_mode: str = Field(default="DEMO", pattern="^(DEMO|LIVE)$")


class MT5AgentOut(BaseModel):
    id: UUID
    user_id: UUID
    broker_account_id: UUID
    status: str
    last_heartbeat_at: Optional[datetime] = None
    terminal_status: Optional[str] = None
    mt5_account_login: Optional[str] = None
    server_name: Optional[str] = None
    trading_mode: str
    balance: Optional[Decimal] = None
    equity: Optional[Decimal] = None
    currency: Optional[str] = None
    algo_trading_enabled: Optional[bool] = None
    agent_version: Optional[str] = None
    metadata_json: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MT5AgentRegisterOut(BaseModel):
    agent: MT5AgentOut
    agent_token: str
    message: str


class MT5AgentHeartbeatIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_token: Optional[str] = None
    terminal_connected: bool = False
    terminal_status: Optional[str] = None
    # Agent supports both old API naming (account_login/algo_trading_enabled)
    # and Windows-agent naming from BROKER-PRO-5A (mt5_account_login/trading_allowed).
    account_login: Optional[str] = None
    mt5_account_login: Optional[str] = None
    server_name: Optional[str] = None
    balance: Optional[Decimal] = None
    equity: Optional[Decimal] = None
    currency: Optional[str] = None
    algo_trading_enabled: Optional[bool] = None
    trading_allowed: Optional[bool] = None
    agent_version: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MT5AgentCommandOut(BaseModel):
    id: UUID
    command_type: str
    status: str
    request_payload: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class MT5AgentOrderResultIn(BaseModel):
    agent_token: Optional[str] = None
    command_id: UUID
    success: bool
    status: str = "COMPLETED"
    broker_order_id: Optional[str] = None
    executed_price: Optional[Decimal] = None
    message: Optional[str] = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
