from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class PlanBase(BaseModel):
    code: str = Field(..., description="Plan code (FREE, PRO, PREMIUM, ULTIMATE)")
    billing_period: str = Field(..., description="Billing period (MONTHLY, YEARLY, NONE)")
    price_inr: int = Field(..., description="Price in INR")
    included_credits: int = Field(..., description="Included credits per billing period")
    features: Dict[str, Any] = Field(..., description="Plan features and limits")


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    code: Optional[str] = None
    billing_period: Optional[str] = None
    price_inr: Optional[int] = None
    included_credits: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Plan(PlanBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionBase(BaseModel):
    user_id: str
    plan_id: str
    status: str = Field(..., description="TRIALING, ACTIVE, CANCELED, EXPIRED")
    start_at: datetime
    end_at: datetime
    trial_end_at: Optional[datetime] = None
    renews: bool = True
    razorpay_subscription_id: Optional[str] = None
    razorpay_customer_id: Optional[str] = None


class UserSubscriptionCreate(UserSubscriptionBase):
    pass


class UserSubscriptionUpdate(BaseModel):
    status: Optional[str] = None
    end_at: Optional[datetime] = None
    trial_end_at: Optional[datetime] = None
    renews: Optional[bool] = None
    razorpay_subscription_id: Optional[str] = None
    razorpay_customer_id: Optional[str] = None


class UserSubscription(UserSubscriptionBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreditBase(BaseModel):
    user_id: str
    balance: int


class UserCreditCreate(UserCreditBase):
    pass


class UserCreditUpdate(BaseModel):
    balance: int


class UserCredit(UserCreditBase):
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    user_id: str
    provider: str = Field(..., description="Payment provider (RAZORPAY)")
    purpose: str = Field(..., description="SUBSCRIPTION, CREDITS_TOPUP")
    amount_inr: int
    currency: str = "INR"
    status: str = Field(..., description="CREATED, PAID, FAILED, REFUNDED")
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class Payment(PaymentBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True