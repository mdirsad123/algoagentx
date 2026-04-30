from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class ProfileStats(BaseModel):
    total_backtests: int = 0
    connected_brokers: int = 0
    active_subscription: str | None = None
    credit_balance: int = 0
    admin_console_access: bool = False

class ProfileResponse(BaseModel):
    id: UUID
    email: str
    role: str
    full_name: str | None = None
    fullname: str | None = None
    mobile: str | None = None
    company: str | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    account_status: str = "active"
    stats: ProfileStats = Field(default_factory=ProfileStats)

class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    fullname: str | None = Field(default=None, max_length=150)
    mobile: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

class SettingsResponse(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    notifications: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=dict)
    admin_alerts: dict[str, Any] = Field(default_factory=dict)

class SettingsUpdate(BaseModel):
    preferences: dict[str, Any] | None = None
    notifications: dict[str, Any] | None = None
    safety: dict[str, Any] | None = None
    admin_alerts: dict[str, Any] | None = None
