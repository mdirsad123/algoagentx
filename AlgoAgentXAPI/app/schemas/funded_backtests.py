from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .backtests import BacktestAdvancedFilters

DAILY_DD_MODES = {"STATIC_INITIAL_BALANCE", "START_OF_DAY_BALANCE", "START_OF_DAY_EQUITY"}
MAX_DD_MODES = {"STATIC_INITIAL_BALANCE", "TRAILING_BALANCE", "TRAILING_EQUITY", "HIGH_WATER_MARK"}
QUALIFYING_MODES = {"ANY_TRADE_DAY", "MIN_PROFIT_DAY"}
KNOWN_CHALLENGE_TYPES = {"ONE_STEP", "TWO_STEP", "INSTANT", "CUSTOM"}
SYSTEM_MAX_RISK = Decimal("0.10")


class FundedPayoutConfig(BaseModel):
    profit_target_pct: Optional[Decimal] = Field(default=None, ge=0)
    profit_target_amount: Optional[Decimal] = Field(default=None, ge=0)
    minimum_payout_amount: Optional[Decimal] = Field(default=None, ge=0)
    minimum_trading_days: Optional[int] = Field(default=None, ge=0)
    minimum_qualifying_profitable_days: Optional[int] = Field(default=None, ge=0)
    qualifying_day_minimum_profit_pct: Optional[Decimal] = Field(default=None, ge=0, lt=1)
    consistency_rule_enabled: bool = False
    consistency_maximum_pct: Optional[Decimal] = Field(default=None, gt=0, le=1)
    consistency_calculation_mode: str = "BEST_DAY_OVER_TOTAL_POSITIVE_PROFIT"
    payout_waiting_calendar_days: Optional[int] = Field(default=None, ge=0)
    payout_profit_split_pct: Optional[Decimal] = Field(default=None, gt=0, le=1)
    stop_simulation_when_payout_ready: bool = False

    @model_validator(mode="after")
    def validate_consistency(self):
        if self.consistency_rule_enabled and self.consistency_maximum_pct is None:
            raise ValueError("consistency_maximum_pct is required when consistency_rule_enabled is true")
        return self


class FundedPhaseInput(BaseModel):
    phase_number: int = Field(..., ge=1)
    phase_name: str = Field(..., min_length=1, max_length=120)
    profit_target_pct: Optional[Decimal] = Field(default=None, ge=0, lt=1)
    daily_drawdown_pct: Decimal = Field(..., gt=0, lt=1)
    daily_drawdown_mode: str
    max_drawdown_pct: Decimal = Field(..., gt=0, lt=1)
    max_drawdown_mode: str
    minimum_trading_days: int = Field(default=0, ge=0)
    minimum_qualifying_day_profit_pct: Optional[Decimal] = Field(default=None, ge=0, lt=1)
    qualifying_day_mode: str = "ANY_TRADE_DAY"
    profit_target_required: bool = True
    reset_balance_after_pass: bool = False
    sequence: int = Field(..., ge=1)

    @field_validator("daily_drawdown_mode")
    @classmethod
    def validate_daily_mode(cls, value):
        value = str(value).upper()
        if value not in DAILY_DD_MODES:
            raise ValueError(f"daily_drawdown_mode must be one of {sorted(DAILY_DD_MODES)}")
        return value

    @field_validator("max_drawdown_mode")
    @classmethod
    def validate_max_mode(cls, value):
        value = str(value).upper()
        if value not in MAX_DD_MODES:
            raise ValueError(f"max_drawdown_mode must be one of {sorted(MAX_DD_MODES)}")
        return value

    @field_validator("qualifying_day_mode")
    @classmethod
    def validate_qualifying_mode(cls, value):
        value = str(value).upper()
        if value not in QUALIFYING_MODES:
            raise ValueError(f"qualifying_day_mode must be one of {sorted(QUALIFYING_MODES)}")
        return value

    @model_validator(mode="after")
    def validate_phase(self):
        if self.profit_target_required and (self.profit_target_pct is None or self.profit_target_pct <= 0):
            raise ValueError("profit_target_pct must be greater than 0 when profit_target_required is true")
        if self.qualifying_day_mode == "MIN_PROFIT_DAY" and self.minimum_qualifying_day_profit_pct is None:
            raise ValueError("minimum_qualifying_day_profit_pct is required for MIN_PROFIT_DAY")
        return self


class FundedRiskTierInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    sort_order: int = Field(..., ge=1)
    min_account_return_pct: Optional[Decimal] = None
    max_account_return_pct: Optional[Decimal] = None
    risk_percent: Decimal = Field(..., gt=0, le=SYSTEM_MAX_RISK)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_range(self):
        if self.min_account_return_pct is not None and self.max_account_return_pct is not None:
            if self.min_account_return_pct >= self.max_account_return_pct:
                raise ValueError("risk tier min_account_return_pct must be less than max_account_return_pct")
        return self


class FundedProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider_name: Optional[str] = Field(default=None, max_length=255)
    challenge_type: str
    account_size: Decimal = Field(..., gt=0)
    account_currency: str = Field(default="USD", min_length=3, max_length=12)
    is_template: bool = False
    is_active: bool = True
    description: Optional[str] = None
    payout_config: Optional[FundedPayoutConfig] = None
    rules_json: Optional[dict[str, Any]] = None
    phases: list[FundedPhaseInput] = Field(default_factory=list)
    risk_tiers: list[FundedRiskTierInput] = Field(default_factory=list)

    @field_validator("challenge_type")
    @classmethod
    def normalize_challenge_type(cls, value):
        # Extensible string: normalize but do not reject future provider-specific values.
        return str(value).strip().upper()

    @field_validator("account_currency")
    @classmethod
    def normalize_currency(cls, value):
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_profile_rules(self):
        phase_numbers = [p.phase_number for p in self.phases]
        sequences = [p.sequence for p in self.phases]
        if len(phase_numbers) != len(set(phase_numbers)):
            raise ValueError("duplicate phase numbers are not allowed")
        if len(sequences) != len(set(sequences)):
            raise ValueError("duplicate phase sequence values are not allowed")
        if self.challenge_type == "ONE_STEP" and (len(self.phases) < 1 or 1 not in phase_numbers):
            raise ValueError("ONE_STEP requires Phase 1")
        if self.challenge_type == "TWO_STEP" and (len(self.phases) < 2 or 1 not in phase_numbers or 2 not in phase_numbers):
            raise ValueError("TWO_STEP requires at least Phase 1 and Phase 2")
        if self.challenge_type == "INSTANT" and self.phases:
            # Instant may have zero challenge phases; custom provider phase constructs should use CUSTOM.
            raise ValueError("INSTANT profiles must not define challenge phases in foundation version")
        self._validate_risk_tiers()
        return self

    def _validate_risk_tiers(self):
        active = sorted((t for t in self.risk_tiers if t.is_active), key=lambda x: x.sort_order)
        orders = [t.sort_order for t in active]
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate risk tier sort_order values are not allowed")
        if active:
            if active[0].min_account_return_pct is not None:
                raise ValueError(f"first active risk tier '{active[0].name}' must have an open lower bound (min_account_return_pct = null)")
            if active[-1].max_account_return_pct is not None:
                raise ValueError(f"last active risk tier '{active[-1].name}' must have an open upper bound (max_account_return_pct = null)")
        for idx, tier in enumerate(active):
            if idx > 0:
                prev = active[idx - 1]
                if prev.max_account_return_pct is None:
                    raise ValueError(f"risk tier '{prev.name}' has an open upper bound before the last tier")
                if tier.min_account_return_pct is None:
                    raise ValueError(f"risk tier '{tier.name}' has an open lower bound after the first tier")
                if tier.min_account_return_pct < prev.max_account_return_pct:
                    raise ValueError(f"risk tiers '{prev.name}' and '{tier.name}' overlap")
                if tier.min_account_return_pct > prev.max_account_return_pct:
                    raise ValueError(f"risk tiers '{prev.name}' and '{tier.name}' leave an uncovered gap")
        return self


class FundedProfileCreate(FundedProfileBase):
    pass


class FundedProfileUpdate(FundedProfileBase):
    pass


class FundedProfileResponse(FundedProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: Optional[UUID] = None


class FundedRunRequest(BaseModel):
    profile_id: UUID
    strategy_id: str
    instrument_id: int
    timeframe: str
    start_date: date
    end_date: date
    runtime_config: Optional[dict[str, Any]] = None
    strategy_preset_id: Optional[str] = None
    advanced_filters: Optional[BacktestAdvancedFilters] = None
    risk_mode: str = "DYNAMIC"
    fixed_risk_pct: Optional[Decimal] = Field(default=None, gt=0, le=SYSTEM_MAX_RISK)
    safety_buffer_pct: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    configured_max_risk_pct: Optional[Decimal] = Field(default=None, gt=0, le=SYSTEM_MAX_RISK)

    @field_validator("risk_mode")
    @classmethod
    def normalize_risk_mode(cls, value):
        value = str(value or "DYNAMIC").strip().upper()
        if value not in {"DYNAMIC", "FIXED"}:
            raise ValueError("risk_mode must be DYNAMIC or FIXED")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.risk_mode == "FIXED" and self.fixed_risk_pct is None:
            raise ValueError("fixed_risk_pct is required when risk_mode is FIXED")
        return self
