from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, func
from uuid import uuid4
from ..db.models import CreditTransaction, CreditTransactionType, JobStatus, Instrument
from ..services.credits.management import CreditManagementService
from ..core.dependencies import get_user_entitlements
from ..billing.plan_catalog import PlanCode
from ..schemas.credits import InsufficientCreditsError


class AIScreenerError(Exception):
    """Base exception for AI screener errors"""
    pass


class AIScreenerServiceResponse:
    """Structured response object for AI screener service"""
    def __init__(
        self,
        job_id: str,
        mode: str,
        depth: str,
        status: str,
        message: str
    ):
        self.job_id = job_id
        self.mode = mode
        self.depth = depth
        self.status = status
        self.message = message


class AIScreenerService:
    @staticmethod
    async def check_subscription_and_credits(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check subscription status and enforce credit policy for AI screener.
        
        Policy:
        - Subscription users: Use included credits first, then require additional credits if exceeded
        - Credit-only users: Always require credits
        - Free trial users: Limited runs, no credit deduction during trial period
        
        Args:
            db: Database session
            user_id: User ID
            mode: AI screener mode
            depth: AI screener depth
            job_id: Optional job ID for tracking
            
        Returns:
            Dict with policy result and cost information
            
        Raises:
            ValueError: If policy violations or insufficient credits
        """
        # Get user entitlements
        entitlements = await get_user_entitlements({"user_id": user_id}, db)
        
        # Calculate cost
        cost = await CreditManagementService.compute_ai_screener_cost(mode, depth)
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        plan_code = entitlements["plan_code"]
        subscription_status = entitlements["subscription_status"]
        included_credits = entitlements["included_credits"]
        is_trial = entitlements["is_trial"]
        
        # Policy implementation
        if is_trial:
            # Free trial: limited runs, no credit deduction
            trial_runs_used = await CreditManagementService.get_trial_ai_screener_count(db, user_id)
            max_trial_runs = 3  # Allow 3 free trial runs
            
            if trial_runs_used >= max_trial_runs:
                raise ValueError(f"Free trial limit exceeded. Maximum {max_trial_runs} AI screener runs allowed.")
            
            return {
                "policy": "trial",
                "cost": 0,
                "deducted": 0,
                "remaining_included": included_credits,
                "remaining_balance": current_balance,
                "message": f"Free trial run (remaining: {max_trial_runs - trial_runs_used - 1})"
            }
        
        elif plan_code != PlanCode.FREE and subscription_status == "ACTIVE":
            # Subscription user: use included credits first
            if included_credits > 0:
                # Use included credits
                if included_credits >= cost:
                    # Included credits cover the cost
                    await CreditManagementService.update_included_credits(
                        db, user_id, -cost
                    )
                    return {
                        "policy": "subscription_included",
                        "cost": cost,
                        "deducted": 0,
                        "remaining_included": included_credits - cost,
                        "remaining_balance": current_balance,
                        "message": f"Used included credits (remaining: {included_credits - cost})"
                    }
                else:
                    # Partially use included credits, rest from balance
                    remaining_cost = cost - included_credits
                    if current_balance < remaining_cost:
                        raise ValueError(f"Insufficient credits. Included credits: {included_credits}, Balance: {current_balance}, Required: {remaining_cost}")
                    
                    # Deduct from included credits and balance
                    await CreditManagementService.update_included_credits(db, user_id, -included_credits)
                    await CreditManagementService.debit_credits(
                        db=db,
                        user_id=user_id,
                        amount=remaining_cost,
                        description=f"AI screener cost (partial from balance) for {mode} mode, {depth} depth",
                        job_id=job_id
                    )
                    
                    return {
                        "policy": "subscription_mixed",
                        "cost": cost,
                        "deducted": remaining_cost,
                        "remaining_included": 0,
                        "remaining_balance": current_balance - remaining_cost,
                        "message": f"Used {included_credits} included credits + {remaining_cost} from balance"
                    }
            else:
                # No included credits, use balance
                if current_balance < cost:
                    raise ValueError(f"Insufficient credits. Balance: {current_balance}, Required: {cost}")
                
                await CreditManagementService.debit_credits(
                    db=db,
                    user_id=user_id,
                    amount=cost,
                    description=f"AI screener cost for {mode} mode, {depth} depth",
                    job_id=job_id
                )
                
                return {
                    "policy": "subscription_balance",
                    "cost": cost,
                    "deducted": cost,
                    "remaining_included": 0,
                    "remaining_balance": current_balance - cost,
                    "message": f"Used {cost} credits from balance"
                }
        
        else:
            # Credit-only user: always require credits
            if current_balance < cost:
                raise ValueError(f"Insufficient credits. Balance: {current_balance}, Required: {cost}")
            
            await CreditManagementService.debit_credits(
                db=db,
                user_id=user_id,
                amount=cost,
                description=f"AI screener cost for {mode} mode, {depth} depth",
                job_id=job_id
            )
            
            return {
                "policy": "credit_only",
                "cost": cost,
                "deducted": cost,
                "remaining_included": 0,
                "remaining_balance": current_balance - cost,
                "message": f"Used {cost} credits from balance"
            }

    @staticmethod
    async def create_job_status(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str,
        policy_result: Dict[str, Any]
    ) -> str:
        """
        Create a job status record for AI screener.
        
        Args:
            db: Database session
            user_id: User ID
            mode: AI screener mode
            depth: AI screener depth
            policy_result: Result from credit policy check
            
        Returns:
            Job ID
        """
        job_id = str(uuid4())
        
        await db.execute(
            insert(JobStatus).values(
                id=job_id,
                user_id=user_id,
                job_type="AI_SCREENER",
                status="PENDING",
                parameters={
                    "mode": mode,
                    "depth": depth,
                    "policy": policy_result["policy"],
                    "cost": policy_result["cost"],
                    "deducted": policy_result["deducted"]
                },
                metadata={
                    "policy_message": policy_result["message"],
                    "remaining_balance": policy_result["remaining_balance"],
                    "remaining_included": policy_result["remaining_included"]
                }
            )
        )
        await db.commit()
        
        return job_id

    @staticmethod
    async def get_job_status(db: AsyncSession, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get AI screener job status.
        
        Args:
            db: Database session
            job_id: Job ID
            user_id: User ID (for authorization)
            
        Returns:
            Job status information or None if not found
        """
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.id == job_id,
                JobStatus.user_id == user_id,
                JobStatus.job_type == "AI_SCREENER"
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
            
        return {
            "job_id": job.id,
            "status": job.status,
            "mode": job.parameters.get("mode"),
            "depth": job.parameters.get("depth"),
            "policy": job.parameters.get("policy"),
            "cost": job.parameters.get("cost"),
            "deducted": job.parameters.get("deducted"),
            "policy_message": job.extra_data.get("policy_message") if hasattr(job, 'extra_data') and job.extra_data else None,
            "remaining_balance": job.extra_data.get("remaining_balance") if hasattr(job, 'extra_data') and job.extra_data else None,
            "remaining_included": job.extra_data.get("remaining_included") if hasattr(job, 'extra_data') and job.extra_data else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "result": job.result
        }

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update AI screener job status.
        
        Args:
            db: Database session
            job_id: Job ID
            status: New status
            result: Optional result data
        """
        await db.execute(
            update(JobStatus).where(JobStatus.id == job_id).values(
                status=status,
                result=result,
                updated_at=func.now()
            )
        )
        await db.commit()

    @staticmethod
    async def refund_credits_on_failure(
        db: AsyncSession,
        user_id: str,
        cost: int,
        job_id: Optional[str] = None
    ) -> None:
        """
        Refund credits when AI screener fails.
        
        Args:
            db: Database session
            user_id: User ID
            cost: Amount to refund
            job_id: Optional job ID for tracking
        """
        await CreditManagementService.refund_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"Refund for failed AI screener job {job_id}",
            job_id=job_id
        )


class CreditManagementServiceExtensions:
    """Extensions to CreditManagementService for AI screener specific functionality"""
    
    @staticmethod
    async def get_trial_ai_screener_count(db: AsyncSession, user_id: str) -> int:
        """
        Get the number of AI screener runs during free trial period.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of trial AI screener runs
        """
        # Count AI screener transactions that occurred during trial period
        result = await db.execute(
            select(func.count(CreditTransaction.id))
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type.in_([CreditTransactionType.CREDIT, CreditTransactionType.DEBIT]),
                CreditTransaction.description.like('%AI screener%'),
                CreditTransaction.created_at >= func.now() - func.interval('7 days')
            )
        )
        return result.scalar() or 0