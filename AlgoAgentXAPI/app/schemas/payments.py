from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum as PyEnum


class PaymentPurpose(PyEnum):
    SUBSCRIPTION = "SUBSCRIPTION"
    CREDITS_TOPUP = "CREDITS_TOPUP"


class PaymentStatus(PyEnum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class CreateOrderRequest(BaseModel):
    credits_to_buy: int = Field(..., gt=0, description="Number of credits to buy")


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int  # Amount in paise
    currency: str
    razorpay_key_id: str


class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    payment_id: str
    credits_granted: int
    message: str


class WebhookRequest(BaseModel):
    event: str
    payload: Dict[str, Any]
    signature: str


class WebhookResponse(BaseModel):
    status: str
    payment_id: Optional[str] = None
    credits_granted: Optional[int] = None
    message: Optional[str] = None


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
