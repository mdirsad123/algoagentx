from typing import Dict, Optional, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload
import razorpay
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
import uuid

from app.db.models.user_subscriptions import UserSubscription
from app.db.models.plans import Plan
from app.db.models.credit_transactions import CreditTransaction
from app.db.models.user_credits import UserCredit
from app.core.config import settings
from app.schemas.credits import CreditTransactionType
from app.billing.plan_catalog import PlanCatalog

logger = logging.getLogger(__name__)


class RazorpaySubscriptionService:
    def __init__(self):
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise ValueError("Razorpay credentials not configured")
        
        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    def get_razorpay_plan_id(self, plan_code: str, billing_period: str) -> str:
        """
        Get Razorpay plan ID for the given plan and billing period.
        Maps our plan codes to Razorpay plan IDs.
        """
        plan_mapping = {
            ('PRO', 'MONTHLY'): 'plan_pro_monthly',
            ('PRO', 'YEARLY'): 'plan_pro_yearly',
            ('PREMIUM', 'MONTHLY'): 'plan_premium_monthly',
            ('PREMIUM', 'YEARLY'): 'plan_premium_yearly',
            ('ULTIMATE', 'MONTHLY'): 'plan_ultimate_monthly',
            ('ULTIMATE', 'YEARLY'): 'plan_ultimate_yearly',
        }
        
        return plan_mapping.get((plan_code, billing_period), f"plan_{plan_code.lower()}_{billing_period.lower()}")

    async def create_subscription_plan(self, plan_code: str, billing_period: str) -> Dict[str, Any]:
        """
        Create a Razorpay plan (one-time operation, usually done during setup).
        """
        try:
            price_inr = PlanCatalog.get_plan_price(plan_code, billing_period)
            if price_inr == 0:
                raise ValueError("Cannot create Razorpay plan for free plan")
            
            razorpay_plan_id = self.get_razorpay_plan_id(plan_code, billing_period)
            
            plan_data = {
                'period': 'monthly' if billing_period == 'MONTHLY' else 'yearly',
                'interval': 1,
                'item': {
                    'name': f'{plan_code} {billing_period}',
                    'description': f'{plan_code} plan - {billing_period}',
                    'amount': price_inr * 100,  # Razorpay expects amount in paise
                    'currency': 'INR'
                },
                'notes': {
                    'plan_code': plan_code,
                    'billing_period': billing_period
                }
            }
            
            # Check if plan already exists
            try:
                existing_plan = self.client.plan.fetch(razorpay_plan_id)
                logger.info(f"Razorpay plan {razorpay_plan_id} already exists")
                return existing_plan
            except razorpay.errors.BadRequestError:
                # Plan doesn't exist, create it
                razorpay_plan = self.client.plan.create(data=plan_data)
                logger.info(f"Created Razorpay plan: {razorpay_plan_id}")
                return razorpay_plan
                
        except Exception as e:
            logger.error(f"Error creating Razorpay plan: {e}")
            raise

    async def create_subscription(self, session: AsyncSession, user_id: str, plan_code: str, billing_period: str) -> Dict[str, Any]:
        """
        Create a Razorpay subscription and user subscription record.
        """
        try:
            # Validate plan exists
            result = await session.execute(
                select(Plan).where(Plan.code == plan_code)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                raise ValueError(f"Plan {plan_code} not found")
            
            if not PlanCatalog.is_valid_plan(plan_code, billing_period):
                raise ValueError(f"Invalid plan and billing period combination: {plan_code}, {billing_period}")
            
            # Get plan details
            price_inr = PlanCatalog.get_plan_price(plan_code, billing_period)
            included_credits = PlanCatalog.get_included_credits(plan_code, billing_period)
            
            if price_inr == 0:
                raise ValueError("Cannot create subscription for free plan")
            
            # Calculate subscription dates
            start_at = datetime.utcnow()
            if billing_period == 'MONTHLY':
                end_at = start_at + timedelta(days=31)
            else:  # YEARLY
                end_at = start_at + timedelta(days=366)
            
            # Create Razorpay plan if it doesn't exist
            razorpay_plan_id = self.get_razorpay_plan_id(plan_code, billing_period)
            await self.create_subscription_plan(plan_code, billing_period)
            
            # Create Razorpay subscription
            subscription_data = {
                'plan_id': razorpay_plan_id,
                'customer_notify': 1,
                'total_count': None,  # Infinite renewals
                'notes': {
                    'user_id': user_id,
                    'plan_code': plan_code,
                    'billing_period': billing_period
                }
            }
            
            razorpay_subscription = self.client.subscription.create(data=subscription_data)
            razorpay_subscription_id = razorpay_subscription['id']
            
            # Create user subscription record
            user_subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan.id,
                status='TRIALING' if included_credits > 0 else 'PENDING',
                start_at=start_at,
                end_at=end_at,
                trial_end_at=start_at + timedelta(days=7) if included_credits > 0 else None,
                renews=True,
                razorpay_subscription_id=razorpay_subscription_id,
                razorpay_customer_id=user_id  # Use user_id as customer_id for simplicity
            )
            
            session.add(user_subscription)
            await session.commit()
            await session.refresh(user_subscription)
            
            # Grant initial credits if trial period
            if included_credits > 0:
                await self._grant_subscription_credits(session, user_id, included_credits, plan_code, billing_period)
            
            return {
                'subscription_id': user_subscription.id,
                'razorpay_subscription_id': razorpay_subscription_id,
                'razorpay_key_id': settings.razorpay_key_id,
                'status': user_subscription.status,
                'start_at': user_subscription.start_at.isoformat(),
                'end_at': user_subscription.end_at.isoformat(),
                'trial_end_at': user_subscription.trial_end_at.isoformat() if user_subscription.trial_end_at else None,
                'included_credits': included_credits
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise

    async def handle_webhook(self, session: AsyncSession, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Handle Razorpay webhook for subscription events.
        """
        try:
            # Verify webhook signature
            if not self._verify_webhook_signature(payload, signature):
                raise ValueError("Invalid webhook signature")
            
            event_type = payload.get('event')
            subscription_data = payload.get('payload', {}).get('subscription', {}).get('entity', {})
            
            razorpay_subscription_id = subscription_data.get('id')
            if not razorpay_subscription_id:
                raise ValueError("Invalid webhook payload - no subscription ID")
            
            # Get user subscription
            result = await session.execute(
                select(UserSubscription).where(
                    UserSubscription.razorpay_subscription_id == razorpay_subscription_id
                )
            )
            user_subscription = result.scalar_one_or_none()
            
            if not user_subscription:
                raise ValueError("User subscription not found")
            
            user_id = user_subscription.user_id
            plan_code = await self._get_plan_code_from_subscription(session, user_subscription.plan_id)
            
            if event_type == 'subscription.activated':
                # Activate subscription
                await session.execute(
                    update(UserSubscription)
                    .where(UserSubscription.id == user_subscription.id)
                    .values(status='ACTIVE')
                )
                
                # Grant monthly credits if not in trial
                if user_subscription.status != 'TRIALING':
                    billing_period = await self._get_billing_period_from_subscription(session, user_subscription.plan_id)
                    included_credits = PlanCatalog.get_included_credits(plan_code, billing_period)
                    if included_credits > 0:
                        await self._grant_subscription_credits(session, user_id, included_credits, plan_code, billing_period)
                
                await session.commit()
                
                return {
                    'status': 'activated',
                    'subscription_id': user_subscription.id,
                    'user_id': user_id,
                    'plan_code': plan_code
                }
            
            elif event_type == 'subscription.cancelled':
                # Cancel subscription
                await session.execute(
                    update(UserSubscription)
                    .where(UserSubscription.id == user_subscription.id)
                    .values(status='CANCELED')
                )
                await session.commit()
                
                return {
                    'status': 'cancelled',
                    'subscription_id': user_subscription.id,
                    'user_id': user_id,
                    'plan_code': plan_code
                }
            
            elif event_type == 'subscription.charged':
                # Subscription payment successful
                # Grant monthly credits
                billing_period = await self._get_billing_period_from_subscription(session, user_subscription.plan_id)
                included_credits = PlanCatalog.get_included_credits(plan_code, billing_period)
                if included_credits > 0:
                    await self._grant_subscription_credits(session, user_id, included_credits, plan_code, billing_period)
                
                return {
                    'status': 'charged',
                    'subscription_id': user_subscription.id,
                    'user_id': user_id,
                    'plan_code': plan_code,
                    'credits_granted': included_credits
                }
            
            elif event_type == 'subscription.paused':
                # Pause subscription
                await session.execute(
                    update(UserSubscription)
                    .where(UserSubscription.id == user_subscription.id)
                    .values(status='PAUSED')
                )
                await session.commit()
                
                return {
                    'status': 'paused',
                    'subscription_id': user_subscription.id,
                    'user_id': user_id,
                    'plan_code': plan_code
                }
            
            elif event_type == 'subscription.resumed':
                # Resume subscription
                await session.execute(
                    update(UserSubscription)
                    .where(UserSubscription.id == user_subscription.id)
                    .values(status='ACTIVE')
                )
                await session.commit()
                
                return {
                    'status': 'resumed',
                    'subscription_id': user_subscription.id,
                    'user_id': user_id,
                    'plan_code': plan_code
                }
            
            else:
                return {
                    'status': 'ignored',
                    'event': event_type,
                    'subscription_id': user_subscription.id
                }
                
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise

    async def cancel_subscription(self, session: AsyncSession, user_id: str, subscription_id: str) -> Dict[str, Any]:
        """
        Cancel a Razorpay subscription.
        """
        try:
            # Get user subscription
            result = await session.execute(
                select(UserSubscription).where(
                    and_(
                        UserSubscription.id == uuid.UUID(subscription_id),
                        UserSubscription.user_id == user_id
                    )
                )
            )
            user_subscription = result.scalar_one_or_none()
            
            if not user_subscription:
                raise ValueError("Subscription not found or access denied")
            
            if user_subscription.status in ['CANCELED', 'EXPIRED']:
                raise ValueError("Subscription already canceled or expired")
            
            # Cancel Razorpay subscription
            razorpay_subscription_id = user_subscription.razorpay_subscription_id
            if razorpay_subscription_id:
                self.client.subscription.cancel(razorpay_subscription_id, {'cancel_at_cycle_end': True})
            
            # Update subscription status
            await session.execute(
                update(UserSubscription)
                .where(UserSubscription.id == user_subscription.id)
                .values(status='CANCELED')
            )
            await session.commit()
            
            return {
                'success': True,
                'subscription_id': subscription_id,
                'status': 'CANCELED',
                'message': 'Subscription canceled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            raise

    async def get_subscription_status(self, session: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current subscription status for user.
        """
        try:
            result = await session.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(UserSubscription.user_id == user_id)
                .order_by(UserSubscription.created_at.desc())
            )
            user_subscription = result.scalar_one_or_none()
            
            if not user_subscription:
                return None
            
            plan_code = await self._get_plan_code_from_subscription(session, user_subscription.plan_id)
            billing_period = await self._get_billing_period_from_subscription(session, user_subscription.plan_id)
            
            return {
                'subscription_id': str(user_subscription.id),
                'plan_code': plan_code,
                'billing_period': billing_period,
                'status': user_subscription.status,
                'start_at': user_subscription.start_at.isoformat(),
                'end_at': user_subscription.end_at.isoformat(),
                'trial_end_at': user_subscription.trial_end_at.isoformat() if user_subscription.trial_end_at else None,
                'renews': user_subscription.renews,
                'razorpay_subscription_id': user_subscription.razorpay_subscription_id
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription status: {e}")
            raise

    def _verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify Razorpay webhook signature.
        """
        try:
            if not settings.razorpay_webhook_secret:
                raise ValueError("Razorpay webhook secret not configured")
            
            import json
            payload_string = json.dumps(payload, separators=(',', ':'))
            
            expected_signature = hmac.new(
                settings.razorpay_webhook_secret.encode(),
                payload_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature == expected_signature
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def _grant_subscription_credits(self, session: AsyncSession, user_id: str, credits_amount: int, plan_code: str, billing_period: str) -> None:
        """
        Grant credits for subscription.
        """
        try:
            # Get or create user credit record
            result = await session.execute(
                select(UserCredit).where(UserCredit.user_id == user_id)
            )
            user_credit = result.scalar_one_or_none()
            
            if not user_credit:
                user_credit = UserCredit(
                    user_id=user_id,
                    credits=credits_amount,
                    last_updated=datetime.utcnow()
                )
                session.add(user_credit)
            else:
                user_credit.credits += credits_amount
                user_credit.last_updated = datetime.utcnow()
            
            # Create credit transaction
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type=CreditTransactionType.CREDIT,
                amount=credits_amount,
                description=f"Monthly credits for {plan_code} {billing_period} subscription",
                created_at=datetime.utcnow()
            )
            
            session.add(transaction)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error granting subscription credits: {e}")
            raise

    async def _get_plan_code_from_subscription(self, session: AsyncSession, plan_id: uuid.UUID) -> str:
        """Get plan code from plan ID."""
        result = await session.execute(
            select(Plan.code).where(Plan.id == plan_id)
        )
        return result.scalar_one()

    async def _get_billing_period_from_subscription(self, session: AsyncSession, plan_id: uuid.UUID) -> str:
        """Get billing period from plan ID."""
        result = await session.execute(
            select(Plan.billing_period).where(Plan.id == plan_id)
        )
        return result.scalar_one()