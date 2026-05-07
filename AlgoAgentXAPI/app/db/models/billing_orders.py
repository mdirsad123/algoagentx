from sqlalchemy import Column, String, Integer, DateTime, Text, Index, func, Numeric

from ..base import Base


class BillingOrder(Base):
    __tablename__ = "billing_orders"
    __table_args__ = (
        Index("idx_billing_orders_user_created", "user_id", "created_at"),
        Index("idx_billing_orders_billing_order_id", "billing_order_id"),
        Index("idx_billing_orders_payment_id", "payment_id"),
        Index("idx_billing_orders_purpose", "purpose"),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(String(36), nullable=False)
    payment_id = Column(String(64), nullable=True)
    subscription_id = Column(String(64), nullable=True)

    billing_order_id = Column(String(64), nullable=False)
    provider = Column(String(50), nullable=False)
    purpose = Column(String(50), nullable=False)
    amount_inr = Column(Integer, nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(String(20), nullable=False)  # CREATED, PAID, FAILED, REFUNDED

    plan_id = Column(String(64), nullable=True)
    plan_code = Column(String(50), nullable=True)
    billing_period = Column(String(20), nullable=True)

    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)

    # PAY-BILL-4 unified billing checkout fields. Existing legacy fields stay readable.
    purchase_type = Column(String(30), nullable=True)
    credit_amount = Column(Integer, nullable=True)
    subtotal_usd = Column(Numeric(12, 2), nullable=True)
    coupon_code = Column(String(80), nullable=True)
    discount_usd = Column(Numeric(12, 2), nullable=True)
    final_usd = Column(Numeric(12, 2), nullable=True)
    payment_method = Column(String(30), nullable=True)
    payment_currency = Column(String(3), nullable=True)
    payment_amount = Column(Numeric(14, 2), nullable=True)
    inr_conversion_rate = Column(Numeric(12, 4), nullable=True)
    gst_percent = Column(Numeric(6, 2), nullable=True)
    gst_amount_inr = Column(Numeric(14, 2), nullable=True)
    final_amount_inr = Column(Numeric(14, 2), nullable=True)
    provider_order_id = Column(String(100), nullable=True)

    failure_reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
