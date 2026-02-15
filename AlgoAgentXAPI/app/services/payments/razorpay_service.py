from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import razorpay
import hmac
import hashlib
import logging
from datetime import datetime

from app.db.models.payments import Payment
from app.db.models.user_credits import UserCredit
from app.db.models.credit_transactions import CreditTransaction
from app.core.config import settings
from app.schemas.credits import CreditTransactionType

logger = logging.getLogger(__name__)


class RazorpayService:
    def __init__(self):
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise ValueError("Razorpay credentials not configured")
        
        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    def calculate_amount_inr(self, credits_to_buy: int) -> int:
        """
        Calculate amount in INR for given credits.
        Pricing: 1 credit = ₹1
        """
        # Simple pricing: 1 credit = ₹1
        # Could be extended for bulk discounts or different pricing tiers
        return credits_to_buy * 100  # Razorpay expects amount in paise

    async def create_order(self, session: AsyncSession, user_id: str, credits_to_buy: int) -> Dict[str, Any]:
        """
        Create a Razorpay order and save payment record.
        """
        try:
            amount_inr = self.calculate_amount_inr(credits_to_buy)
            
            # Create Razorpay order
            order_data = {
                'amount': amount_inr,
                'currency': 'INR',
                'receipt': f'credit_order_{user_id}_{int(datetime.now().timestamp())}',
                'payment_capture': 1  # Auto capture
            }
            
            razorpay_order = self.client.order.create(data=order_data)
            order_id = razorpay_order['id']
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                provider='RAZORPAY',
                purpose='CREDITS_TOPUP',
                amount_inr=amount_inr // 100,  # Store in rupees
                currency='INR',
                status='CREATED',
                razorpay_order_id=order_id
            )
            
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            
            return {
                'order_id': order_id,
                'amount': amount_inr,
                'currency': 'INR',
                'razorpay_key_id': settings.razorpay_key_id
            }
            
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {e}")
            raise

    async def verify_payment(self, session: AsyncSession, order_id: str, 
                           razorpay_payment_id: str, razorpay_signature: str) -> Dict[str, Any]:
        """
        Verify payment signature and mark payment as PAID.
        Grant credits to user.
        """
        try:
            # Verify signature
            if not self._verify_signature(order_id, razorpay_payment_id, razorpay_signature):
                raise ValueError("Invalid payment signature")
            
            # Update payment status
            result = await session.execute(
                update(Payment)
                .where(Payment.razorpay_order_id == order_id)
                .values(
                    status='PAID',
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_signature=razorpay_signature
                )
                .returning(Payment)
            )
            
            payment = result.scalar_one_or_none()
            if not payment:
                raise ValueError("Payment record not found")
            
            await session.commit()
            
            # Grant credits to user
            credits_granted = await self._grant_credits(session, payment.user_id, payment.amount_inr)
            
            return {
                'success': True,
                'payment_id': payment.id,
                'credits_granted': credits_granted,
                'message': 'Payment verified and credits granted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            raise

    async def handle_webhook(self, session: AsyncSession, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Handle Razorpay webhook for payment captured events.
        """
        try:
            # Verify webhook signature
            if not self._verify_webhook_signature(payload, signature):
                raise ValueError("Invalid webhook signature")
            
            event_type = payload.get('event')
            if event_type != 'payment.captured':
                return {'status': 'ignored', 'event': event_type}
            
            payment_data = payload.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_data.get('order_id')
            payment_id = payment_data.get('id')
            
            if not order_id or not payment_id:
                raise ValueError("Invalid webhook payload")
            
            # Check if payment already processed
            result = await session.execute(
                select(Payment).where(Payment.razorpay_order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                raise ValueError("Payment record not found")
            
            if payment.status == 'PAID':
                return {'status': 'already_processed', 'payment_id': payment.id}
            
            # Update payment status
            await session.execute(
                update(Payment)
                .where(Payment.razorpay_order_id == order_id)
                .values(
                    status='PAID',
                    razorpay_payment_id=payment_id,
                    razorpay_signature=signature
                )
            )
            
            await session.commit()
            
            # Grant credits to user (idempotent)
            credits_granted = await self._grant_credits(session, payment.user_id, payment.amount_inr)
            
            return {
                'status': 'processed',
                'payment_id': payment.id,
                'credits_granted': credits_granted,
                'message': 'Webhook processed and credits granted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise

    def _verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify Razorpay payment signature.
        """
        try:
            # Create signature string
            signature_string = f"{order_id}|{payment_id}"
            
            # Generate expected signature
            expected_signature = hmac.new(
                settings.razorpay_key_secret.encode(),
                signature_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature == expected_signature
            
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    def _verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify Razorpay webhook signature.
        """
        try:
            if not settings.razorpay_webhook_secret:
                raise ValueError("Razorpay webhook secret not configured")
            
            # Convert payload to string (Razorpay sends raw JSON)
            import json
            payload_string = json.dumps(payload, separators=(',', ':'))
            
            # Generate expected signature
            expected_signature = hmac.new(
                settings.razorpay_webhook_secret.encode(),
                payload_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature == expected_signature
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def _grant_credits(self, session: AsyncSession, user_id: str, amount_inr: int) -> int:
        """
        Grant credits to user based on amount paid.
        Returns the number of credits granted.
        """
        try:
            # Calculate credits (1 INR = 1 credit)
            credits_to_add = amount_inr
            
            # Get or create user credit record
            result = await session.execute(
                select(UserCredit).where(UserCredit.user_id == user_id)
            )
            user_credit = result.scalar_one_or_none()
            
            if not user_credit:
                user_credit = UserCredit(
                    user_id=user_id,
                    credits=credits_to_add,
                    last_updated=datetime.utcnow()
                )
                session.add(user_credit)
            else:
                user_credit.credits += credits_to_add
                user_credit.last_updated = datetime.utcnow()
            
            # Create credit transaction
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type=CreditTransactionType.CREDIT,
                amount=credits_to_add,
                description=f"Credit topup via Razorpay payment",
                created_at=datetime.utcnow()
            )
            
            session.add(transaction)
            await session.commit()
            
            return credits_to_add
            
        except Exception as e:
            logger.error(f"Error granting credits: {e}")
            raise