from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from typing import Optional, List, Dict, Any

from ...db.models import CreditTransaction, CreditTransactionType, User, JobStatus
from ...schemas.users import User as UserSchema
from ...billing.cost_rules import CostRules, CostType


class CreditManagementService:
    """Service for managing user credits and transactions."""
    
    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: str) -> Decimal:
        """
        Get current credit balance for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Current credit balance
        """
        # Get the latest transaction for this user
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(1)
        )
        latest_txn = result.scalar_one_or_none()
        
        if latest_txn:
            return latest_txn.balance_after
        else:
            return Decimal('0.00')
    
    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        user_id: str,
        transaction_type: CreditTransactionType,
        amount: Decimal,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Create a new credit transaction.
        
        Args:
            db: Database session
            user_id: User ID
            transaction_type: Type of transaction
            amount: Transaction amount (positive for credit, negative for debit)
            description: Transaction description
            backtest_id: Optional backtest ID
            job_id: Optional job ID
            metadata: Optional transaction metadata
            
        Returns:
            Created transaction
        """
        # Get current balance
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        # Calculate new balance
        if transaction_type == CreditTransactionType.DEBIT:
            new_balance = current_balance - amount
        else:  # CREDIT or REFUND
            new_balance = current_balance + amount
            
        # Create transaction
        transaction = CreditTransaction(
            id=str(uuid4()),
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            metadata=metadata
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        return transaction
    
    @staticmethod
    async def debit_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
        description: str,
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Debit credits from user account atomically.
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to debit
            description: Transaction description
            job_id: Optional job ID
            metadata: Optional transaction metadata
            
        Returns:
            Created debit transaction
            
        Raises:
            ValueError: If insufficient credits
        """
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        if current_balance < amount:
            raise ValueError(f"Insufficient credits. Current balance: {current_balance}, Required: {amount}")
            
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.DEBIT,
            amount=amount,
            description=description,
            job_id=job_id,
            metadata=metadata
        )
    
    @staticmethod
    async def refund_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Refund credits to user account.
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to refund
            description: Transaction description
            backtest_id: Optional backtest ID
            job_id: Optional job ID
            metadata: Optional transaction metadata
            
        Returns:
            Created refund transaction
        """
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.REFUND,
            amount=amount,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            metadata=metadata
        )
    
    @staticmethod
    async def credit_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Credit additional credits to user account (admin function).
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to credit
            description: Transaction description
            metadata: Optional transaction metadata
            
        Returns:
            Created credit transaction
        """
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.CREDIT,
            amount=amount,
            description=description,
            metadata=metadata
        )
    
    @staticmethod
    async def refund_transaction(db: AsyncSession, transaction_id: str) -> CreditTransaction:
        """
        Refund a specific transaction by creating a REFUND transaction.
        
        Args:
            db: Database session
            transaction_id: ID of the transaction to refund
            
        Returns:
            Created refund transaction
            
        Raises:
            ValueError: If transaction not found or already refunded
        """
        # Get the original transaction
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.id == transaction_id)
        )
        original_txn = result.scalar_one_or_none()
        
        if not original_txn:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if original_txn.transaction_type == CreditTransactionType.REFUND:
            raise ValueError(f"Transaction {transaction_id} is already a refund")
        
        # Create refund transaction
        refund_amount = original_txn.amount
        refund_description = f"Refund for transaction {transaction_id}: {original_txn.description}"
        
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=original_txn.user_id,
            transaction_type=CreditTransactionType.REFUND,
            amount=refund_amount,
            description=refund_description,
            backtest_id=original_txn.backtest_id,
            job_id=original_txn.job_id,
            metadata={"refunded_transaction_id": transaction_id}
        )
    
    @staticmethod
    async def get_transaction_history(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditTransaction]:
        """
        Get credit transaction history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of transactions to return
            offset: Offset for pagination
            
        Returns:
            List of transactions
        """
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_user_credit_summary(db: AsyncSession, user_id: str) -> dict:
        """
        Get credit summary for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Credit summary with balance and transaction counts
        """
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        # Count transactions by type
        result = await db.execute(
            select(
                CreditTransaction.transaction_type,
                func.count(CreditTransaction.id).label('count')
            )
            .where(CreditTransaction.user_id == user_id)
            .group_by(CreditTransaction.transaction_type)
        )
        transaction_counts = dict(result.fetchall())
        
        return {
            "user_id": user_id,
            "current_balance": float(current_balance),
            "total_transactions": sum(transaction_counts.values()),
            "transaction_counts": transaction_counts,
            "last_updated": datetime.now().isoformat()
        }
    
    @staticmethod
    async def get_trial_backtest_count(db: AsyncSession, user_id: str) -> int:
        """
        Get the number of backtest runs during free trial period.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of trial backtest runs
        """
        # Count backtest transactions that occurred during trial period
        # This is a simplified implementation - in reality, you might want to track
        # trial usage separately or check user creation date
        result = await db.execute(
            select(func.count(CreditTransaction.id))
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type.in_([CreditTransactionType.CREDIT, CreditTransactionType.DEBIT]),
                CreditTransaction.description.like('%Backtest%'),
                CreditTransaction.created_at >= text("NOW() - INTERVAL '7 days'")
            )
        )
        return result.scalar() or 0
    
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
                CreditTransaction.created_at >= text("NOW() - INTERVAL '7 days'")
            )
        )
        return result.scalar() or 0
    
    @staticmethod
    async def update_included_credits(db: AsyncSession, user_id: str, amount_change: Decimal) -> None:
        """
        Update included credits for a user (for subscription plans).
        
        Args:
            db: Database session
            user_id: User ID
            amount_change: Amount to change included credits (negative to deduct)
        """
        # This would need to be implemented based on how included credits are tracked
        # For now, we'll use a placeholder implementation
        # In a real implementation, this would update a user_subscriptions table
        # or a separate included_credits table
        
        # Placeholder: Log the included credits update
        from sqlalchemy import text as sql_text
        await db.execute(
            sql_text("""
                -- Placeholder for included credits tracking
                -- In a real implementation, this would update user subscription records
                SELECT 1
            """)
        )
        await db.commit()
    
    @staticmethod
    async def compute_backtest_cost(
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> Decimal:
        """
        Compute backtest cost using cost rules.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Backtest timeframe
            
        Returns:
            Cost in credits
        """
        return CostRules.calculate_backtest_cost(start_date, end_date, timeframe)
    
    @staticmethod
    async def compute_ai_screener_cost(mode: str, depth: str) -> Decimal:
        """
        Compute AI screener cost using cost rules.
        
        Args:
            mode: AI screener mode
            depth: AI screener depth
            
        Returns:
            Cost in credits
        """
        return CostRules.calculate_ai_screener_cost(mode, depth)
    
    @staticmethod
    async def check_and_debit_backtest_credits(
        db: AsyncSession,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
        job_id: Optional[str] = None
    ) -> CreditTransaction:
        """
        Check balance and debit credits for backtest run.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Backtest timeframe
            job_id: Optional job ID
            
        Returns:
            Created debit transaction
            
        Raises:
            ValueError: If insufficient credits
        """
        # Compute cost
        cost = await CreditManagementService.compute_backtest_cost(
            start_date, end_date, timeframe
        )
        
        # Check balance
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        if current_balance < cost:
            raise ValueError(f"Insufficient credits. Current balance: {current_balance}, Required: {cost}")
        
        # Create debit transaction with metadata
        metadata = {
            "operation": "backtest",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timeframe": timeframe,
            "cost": float(cost)
        }
        
        return await CreditManagementService.debit_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"Backtest run: {start_date.date()} to {end_date.date()} ({timeframe})",
            job_id=job_id,
            metadata=metadata
        )
    
    @staticmethod
    async def check_and_debit_ai_screener_credits(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str,
        job_id: Optional[str] = None
    ) -> CreditTransaction:
        """
        Check balance and debit credits for AI screener run.
        
        Args:
            db: Database session
            user_id: User ID
            mode: AI screener mode
            depth: AI screener depth
            job_id: Optional job ID
            
        Returns:
            Created debit transaction
            
        Raises:
            ValueError: If insufficient credits
        """
        # Compute cost
        cost = await CreditManagementService.compute_ai_screener_cost(mode, depth)
        
        # Check balance
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        if current_balance < cost:
            raise ValueError(f"Insufficient credits. Current balance: {current_balance}, Required: {cost}")
        
        # Create debit transaction with metadata
        metadata = {
            "operation": "ai_screener",
            "mode": mode,
            "depth": depth,
            "cost": float(cost)
        }
        
        return await CreditManagementService.debit_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"AI screener run: {mode} mode, {depth} depth",
            job_id=job_id,
            metadata=metadata
        )
