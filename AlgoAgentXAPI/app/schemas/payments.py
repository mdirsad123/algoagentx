from __future__ import annotations

from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator


class PaymentPurpose(PyEnum):
    SUBSCRIPTION = "SUBSCRIPTION"
    CREDITS_TOPUP = "CREDITS_TOPUP"


class PaymentStatus(PyEnum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class CreateOrderRequest(BaseModel):
    pack_code: Optional[str] = Field(default=None, description="Configured credit pack code")
    credits_to_buy: Optional[int] = Field(default=None, gt=0, le=1_000_000, description="Custom credits to buy")

    @model_validator(mode="after")
    def validate_input(self) -> "CreateOrderRequest":
        has_pack = bool(self.pack_code)
        has_custom = self.credits_to_buy is not None
        if has_pack and has_custom:
            raise ValueError("Provide either pack_code or credits_to_buy, not both")
        if not has_pack and not has_custom:
            raise ValueError("Either pack_code or credits_to_buy is required")
        return self


class CreateOrderResponse(BaseModel):
    order_id: str  # Razorpay order id (legacy compatibility)
    billing_order_id: str
    payment_record_id: str
    credits: int
    amount: int  # Amount in paise (legacy compatibility)
    amount_inr: int
    currency: str
    razorpay_key_id: str
    key_id: str
    status: str


class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    payment_id: str
    order_id: str
    billing_order_id: Optional[str] = None
    credits_granted: int
    balance: int
    status: str
    idempotent: bool = False
    message: str


class PaymentFailureRequest(BaseModel):
    order_id: str
    reason: Optional[str] = None
    code: Optional[str] = None


class WebhookRequest(BaseModel):
    event: str
    payload: Dict[str, Any]


class WebhookResponse(BaseModel):
    status: str
    payment_id: Optional[str] = None
    credits_granted: Optional[int] = None
    message: Optional[str] = None


class CreditPack(BaseModel):
    code: str
    credits: int
    amount_inr: int
    label: str
    popular: bool = False


class RazorpayConfigResponse(BaseModel):
    key_id: str
    currency: str = "INR"
    configured: bool = False
    allow_custom_topup: bool
    min_custom_credits: int
    max_custom_credits: int
    packs: list[CreditPack]


class PaymentInfo(BaseModel):
    id: str
    user_id: str
    provider: str
    purpose: PaymentPurpose
    amount_inr: int
    currency: str
    status: PaymentStatus
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    created_at: str


class ValidateCouponRequest(BaseModel):
    code: str
    plan_id: str


class ValidateCouponResponse(BaseModel):
    valid: bool
    discount_percent: int
    final_amount: int
    message: str
