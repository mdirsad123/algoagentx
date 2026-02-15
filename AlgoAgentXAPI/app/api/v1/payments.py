from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.db.session import get_db_session
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.services.payments.razorpay_service import RazorpayService
from app.schemas.payments import (
    CreateOrderRequest, CreateOrderResponse, 
    VerifyPaymentRequest, VerifyPaymentResponse,
    WebhookRequest, WebhookResponse,
    ValidateCouponRequest, ValidateCouponResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/razorpay/create-order", response_model=CreateOrderResponse)
async def create_razorpay_order(
    request: CreateOrderRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a Razorpay order for credit topup.
    """
    try:
        # Validate Razorpay configuration
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay not configured"
            )
        
        # Validate credits amount
        if request.credits_to_buy <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credits to buy must be greater than 0"
            )
        
        # Create Razorpay service
        razorpay_service = RazorpayService()
        
        # Create order
        order_data = await razorpay_service.create_order(
            session=db,
            user_id=current_user['user_id'],
            credits_to_buy=request.credits_to_buy
        )
        
        return CreateOrderResponse(**order_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment order"
        )


@router.post("/razorpay/verify", response_model=VerifyPaymentResponse)
async def verify_razorpay_payment(
    request: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Verify Razorpay payment and grant credits.
    """
    try:
        # Validate Razorpay configuration
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay not configured"
            )
        
        # Create Razorpay service
        razorpay_service = RazorpayService()
        
        # Verify payment
        result = await razorpay_service.verify_payment(
            session=db,
            order_id=request.order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        
        return VerifyPaymentResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error verifying Razorpay payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify payment"
        )


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle Razorpay webhook for payment captured events.
    """
    try:
        # Validate Razorpay webhook secret
        if not settings.razorpay_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay webhook not configured"
            )
        
        # Get raw payload and signature
        payload = await request.json()
        signature = request.headers.get('X-Razorpay-Signature')
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook signature missing"
            )
        
        # Create Razorpay service
        razorpay_service = RazorpayService()
        
        # Handle webhook
        result = await razorpay_service.handle_webhook(
            session=db,
            payload=payload,
            signature=signature
        )
        
        return WebhookResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error handling Razorpay webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.get("/razorpay/config")
async def get_razorpay_config():
    """
    Get Razorpay configuration for frontend.
    """
    try:
        if not settings.razorpay_key_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay not configured"
            )
        
        return {
            "key_id": settings.razorpay_key_id,
            "configured": True
        }
        
    except Exception as e:
        logger.error(f"Error getting Razorpay config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration"
        )


@router.post("/validate-coupon", response_model=ValidateCouponResponse)
async def validate_coupon(
    request: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Validate coupon code for subscription purchase.
    
    Rules:
    - FIRST30: 30% discount for first-time subscription purchase only
    - Checks if user has never had an active subscription before
    """
    try:
        # Check if user has existing subscription history
        from sqlalchemy import text
        
        subscription_query = text("""
            SELECT COUNT(*) as subscription_count 
            FROM user_subscriptions 
            WHERE user_id = :user_id 
            AND status = 'ACTIVE'
        """)
        
        result = await db.execute(subscription_query, {"user_id": current_user["user_id"]})
        active_subscriptions = result.scalar() or 0
        
        # Check if user has ever had any subscription (including expired)
        history_query = text("""
            SELECT COUNT(*) as total_subscriptions 
            FROM user_subscriptions 
            WHERE user_id = :user_id
        """)
        
        result = await db.execute(history_query, {"user_id": current_user["user_id"]})
        total_subscriptions = result.scalar() or 0
        
        # Get plan details
        plan_query = text("""
            SELECT price_inr, code 
            FROM plans 
            WHERE id = :plan_id
        """)
        
        result = await db.execute(plan_query, {"plan_id": request.plan_id})
        plan = result.fetchone()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        plan_price = plan.price_inr
        plan_code = plan.code
        
        # Validate coupon
        if request.code == "FIRST30":
            # Check if this is the user's first subscription
            if total_subscriptions > 0:
                return ValidateCouponResponse(
                    valid=False,
                    discount_percent=0,
                    final_amount=plan_price,
                    message="Coupon is only valid for first-time subscription purchases"
                )
            
            # Apply 30% discount
            discount_percent = 30
            discount_amount = int(plan_price * 0.30)
            final_amount = plan_price - discount_amount
            
            return ValidateCouponResponse(
                valid=True,
                discount_percent=discount_percent,
                final_amount=final_amount,
                message=f"30% discount applied for first-time subscription"
            )
        
        else:
            # Invalid coupon code
            return ValidateCouponResponse(
                valid=False,
                discount_percent=0,
                final_amount=plan_price,
                message="Invalid coupon code"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating coupon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate coupon"
        )
