from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.models.notifications import Notification
from app.schemas.notifications import NotificationCreate
from app.services.notifications import NotificationService
from app.db.models.user_credits import UserCredit
from app.db.models.credit_transactions import CreditTransaction
from app.db.models.payments import Payment
from app.db.models.job_status import JobStatus
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for creating notifications in a safe background way."""
    
    NOTIFICATION_TYPES = {
        'CREDITS_LOW': 'CREDITS_LOW',
        'PAYMENT_SUCCESS': 'PAYMENT_SUCCESS', 
        'BACKTEST_DONE': 'BACKTEST_DONE',
        'SUBSCRIPTION_EXPIRE_SOON': 'SUBSCRIPTION_EXPIRE_SOON',
        'ERROR': 'ERROR'
    }
    
    CREDITS_LOW_THRESHOLD = 10
    CREDITS_LOW_COOLDOWN_HOURS = 24  # Only notify once per day

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = NotificationService(db)

    async def create_notification_safe(
        self, 
        user_id: str, 
        notification_type: str, 
        title: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a notification safely in the background."""
        try:
            notification_data = NotificationCreate(
                type=notification_type,
                title=title,
                message=message,
                metadata=metadata
            )
            
            # Create notification
            await self.service.create_notification(user_id, notification_data)
            logger.info(f"Notification created for user {user_id}: {notification_type}")
            
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            # Don't raise exception to avoid blocking the main operation

    async def check_and_notify_credits_low(self, user_id: str):
        """Check if user has low credits and send notification if needed."""
        try:
            # Get user's current credits
            result = await self.db.execute(
                select(UserCredit).where(UserCredit.user_id == user_id)
            )
            user_credit = result.scalar_one_or_none()
            
            if not user_credit or user_credit.credits >= self.CREDITS_LOW_THRESHOLD:
                return
            
            # Check if we've already sent a low credits notification today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            existing_notification = await self.db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.type == self.NOTIFICATION_TYPES['CREDITS_LOW'],
                        Notification.created_at >= today_start,
                        Notification.created_at < today_end
                    )
                )
            )
            
            if existing_notification.scalar_one_or_none():
                return  # Already notified today
            
            # Send low credits notification
            await self.create_notification_safe(
                user_id=user_id,
                notification_type=self.NOTIFICATION_TYPES['CREDITS_LOW'],
                title="Low Credits Alert",
                message=f"You have {user_credit.credits} credits remaining. Please top up to continue using our services.",
                metadata={
                    "current_credits": user_credit.credits,
                    "threshold": self.CREDITS_LOW_THRESHOLD
                }
            )
            
        except Exception as e:
            logger.error(f"Error checking credits for user {user_id}: {e}")

    async def notify_payment_success(self, payment_id: str):
        """Send notification when payment is successful."""
        try:
            # Get payment details
            result = await self.db.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                return
            
            await self.create_notification_safe(
                user_id=payment.user_id,
                notification_type=self.NOTIFICATION_TYPES['PAYMENT_SUCCESS'],
                title="Payment Successful",
                message=f"Your payment of {payment.amount} {payment.currency} has been processed successfully.",
                metadata={
                    "payment_id": payment.id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "payment_method": payment.payment_method
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating payment success notification for payment {payment_id}: {e}")

    async def notify_backtest_done(self, job_id: str):
        """Send notification when backtest job is completed."""
        try:
            # Get job status details
            result = await self.db.execute(
                select(JobStatus).where(JobStatus.job_id == job_id)
            )
            job_status = result.scalar_one_or_none()
            
            if not job_status:
                return
            
            status_text = "completed successfully" if job_status.status == "completed" else "failed"
            await self.create_notification_safe(
                user_id=job_status.user_id,
                notification_type=self.NOTIFICATION_TYPES['BACKTEST_DONE'],
                title="Backtest Completed",
                message=f"Your backtest job {job_id} has {status_text}.",
                metadata={
                    "job_id": job_id,
                    "status": job_status.status,
                    "strategy_id": job_status.strategy_id,
                    "timeframe": job_status.timeframe,
                    "start_date": job_status.start_date.isoformat() if job_status.start_date else None,
                    "end_date": job_status.end_date.isoformat() if job_status.end_date else None
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating backtest completion notification for job {job_id}: {e}")

    async def notify_subscription_expiring(self, user_id: str, days_until_expiry: int):
        """Send notification when subscription is about to expire."""
        try:
            await self.create_notification_safe(
                user_id=user_id,
                notification_type=self.NOTIFICATION_TYPES['SUBSCRIPTION_EXPIRE_SOON'],
                title="Subscription Expiring Soon",
                message=f"Your subscription will expire in {days_until_expiry} days. Please renew to continue enjoying premium features.",
                metadata={
                    "days_until_expiry": days_until_expiry
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating subscription expiry notification for user {user_id}: {e}")

    async def notify_error(self, user_id: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Send error notification."""
        try:
            await self.create_notification_safe(
                user_id=user_id,
                notification_type=self.NOTIFICATION_TYPES['ERROR'],
                title="System Error",
                message=error_message,
                metadata=context
            )
            
        except Exception as e:
            logger.error(f"Error creating error notification for user {user_id}: {e}")


# Background task functions that can be called from various services
async def notify_credits_low_background(db: AsyncSession, user_id: str):
    """Background task to check and notify low credits."""
    manager = NotificationManager(db)
    await manager.check_and_notify_credits_low(user_id)


async def notify_payment_success_background(db: AsyncSession, payment_id: str):
    """Background task to notify payment success."""
    manager = NotificationManager(db)
    await manager.notify_payment_success(payment_id)


async def notify_backtest_done_background(db: AsyncSession, job_id: str):
    """Background task to notify backtest completion."""
    manager = NotificationManager(db)
    await manager.notify_backtest_done(job_id)


async def notify_subscription_expiring_background(db: AsyncSession, user_id: str, days_until_expiry: int):
    """Background task to notify subscription expiry."""
    manager = NotificationManager(db)
    await manager.notify_subscription_expiring(user_id, days_until_expiry)


async def notify_error_background(db: AsyncSession, user_id: str, error_message: str, context: Optional[Dict[str, Any]] = None):
    """Background task to notify error."""
    manager = NotificationManager(db)
    await manager.notify_error(user_id, error_message, context)