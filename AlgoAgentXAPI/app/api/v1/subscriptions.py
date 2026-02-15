from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging
import uuid

from app.db.session import get_db_session
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.services.payments.razorpay_subscription_service import RazorpaySubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/razorpay/create", response_model=Dict[str, Any])
async def create_subscription(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a Razorpay subscription for a plan.
    """
    try:
        # Validate Razorpay configuration
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay not configured"
            )
        
        # Validate request
        plan_code = request.get('plan_code')
        billing_period = request.get('billing_period')
        
        if not plan_code or not billing_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="plan_code and billing_period are required"
            )
        
        # Create subscription service
        subscription_service = RazorpaySubscriptionService()
        
        # Create subscription
        result = await subscription_service.create_subscription(
            session=db,
            user_id=current_user['user_id'],
            plan_code=plan_code,
            billing_period=billing_period
        )
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )


@router.post("/razorpay/webhook")
async def razorpay_subscription_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle Razorpay subscription webhook events.
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
        
        # Create subscription service
        subscription_service = RazorpaySubscriptionService()
        
        # Handle webhook
        result = await subscription_service.handle_webhook(
            session=db,
            payload=payload,
            signature=signature
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error handling subscription webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.post("/cancel/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Cancel a Razorpay subscription.
    """
    try:
        # Create subscription service
        subscription_service = RazorpaySubscriptionService()
        
        # Cancel subscription
        result = await subscription_service.cancel_subscription(
            session=db,
            user_id=current_user['user_id'],
            subscription_id=subscription_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.get("/me", response_model=Optional[Dict[str, Any]])
async def get_my_subscription(
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current user's subscription status.
    """
    try:
        # Create subscription service
        subscription_service = RazorpaySubscriptionService()
        
        # Get subscription status
        result = await subscription_service.get_subscription_status(
            session=db,
            user_id=current_user['user_id']
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription status"
        )


@router.get("/plans")
async def get_available_plans():
    """
    Get all available subscription plans.
    """
    try:
        from app.billing.plan_catalog import PlanCatalog
        
        plans = PlanCatalog.get_all_plans()
        
        return {
            "plans": plans,
            "message": "Available subscription plans"
        }
        
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plans"
        )


@router.get("/razorpay/config")
async def get_razorpay_subscription_config():
    """
    Get Razorpay subscription configuration for frontend.
    """
    try:
        if not settings.razorpay_key_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay not configured"
            )
        
        return {
            "key_id": settings.razorpay_key_id,
            "configured": True,
            "webhook_configured": bool(settings.razorpay_webhook_secret)
        }
        
    except Exception as e:
        logger.error(f"Error getting Razorpay subscription config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration"
        )