from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime

from ...core.dependencies import get_current_user, get_db, get_user_entitlements
from ...services.credits.calculation import CreditCalculationService
from ...services.credits.management import CreditManagementService
from ...schemas.credits import CreditCostPreview, CreditBalance, CreditSummary, CreditTransaction, InsufficientCreditsError

router = APIRouter()

@router.post("/preview-cost", response_model=CreditCostPreview)
async def preview_backtest_cost(
    start_date: date,
    end_date: date,
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview credit cost for a backtest run.
    
    Args:
        start_date: Backtest start date
        end_date: Backtest end date
        timeframe: Optional timeframe (e.g., '1m', '5m', '1h', '1d')
        db: Database session
        current_user: Current user
        
    Returns:
        Cost breakdown with detailed information
    """
    try:
        cost_breakdown = CreditCalculationService.format_cost_breakdown(
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )
        
        return CreditCostPreview(**cost_breakdown)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current credit balance for the user.
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        Current credit balance
    """
    try:
        balance = await CreditManagementService.get_user_balance(db, current_user["user_id"])
        
        return CreditBalance(
            user_id=current_user["user_id"],
            current_balance=float(balance),
            last_updated=date.today().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credit balance: {str(e)}"
        )

@router.get("/summary", response_model=CreditSummary)
async def get_credit_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements)
):
    """
    Get credit summary for the user including balance, included credits, plan info, and next reset date.
    
    Args:
        db: Database session
        current_user: Current user
        entitlements: User entitlements and plan info
        
    Returns:
        Credit summary with balance, included credits, plan name, and next reset date
    """
    try:
        # Get current credit balance
        current_balance = await CreditManagementService.get_user_balance(db, current_user["user_id"])
        
        # Get plan information from entitlements
        plan_code = entitlements.get("plan_code", "FREE")
        included_credits = entitlements.get("included_credits", 0)
        billing_period = entitlements.get("billing_period", "NONE")
        
        # Calculate next reset date based on billing period
        next_reset_date = None
        if billing_period in ["MONTHLY", "ANNUAL"]:
            from datetime import datetime, timedelta
            import calendar
            
            now = datetime.utcnow()
            if billing_period == "MONTHLY":
                # Next month's 1st day
                if now.month == 12:
                    next_reset_date = datetime(now.year + 1, 1, 1)
                else:
                    next_reset_date = datetime(now.year, now.month + 1, 1)
            elif billing_period == "ANNUAL":
                # Next year's same month and day
                next_reset_date = datetime(now.year + 1, now.month, now.day)
            
            if next_reset_date:
                next_reset_date = next_reset_date.isoformat()
        
        # Get transaction summary
        transaction_summary = await CreditManagementService.get_user_credit_summary(db, current_user["user_id"])
        
        # Build enhanced summary
        summary = {
            "user_id": current_user["user_id"],
            "credit_balance": float(current_balance),
            "included_remaining": included_credits,
            "plan_name": plan_code,
            "next_reset_date": next_reset_date,
            "total_transactions": transaction_summary.get("total_transactions", 0),
            "transaction_counts": transaction_summary.get("transaction_counts", {}),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return CreditSummary(**summary)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credit summary: {str(e)}"
        )

@router.get("/transactions", response_model=List[CreditTransaction])
async def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get credit transaction history for the user.
    
    Args:
        limit: Number of transactions to return (max 100)
        offset: Offset for pagination
        db: Database session
        current_user: Current user
        
    Returns:
        List of credit transactions
    """
    try:
        # Limit maximum limit to prevent large responses
        limit = min(limit, 100)
        
        transactions = await CreditManagementService.get_transaction_history(
            db=db,
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset
        )
        
        return transactions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credit transactions: {str(e)}"
        )

@router.post("/check-credits")
async def check_credits_for_backtest(
    start_date: date,
    end_date: date,
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if user has sufficient credits for a backtest and return cost.
    This endpoint is used by the backtest service to validate credits before running.
    
    Args:
        start_date: Backtest start date
        end_date: Backtest end date
        timeframe: Optional timeframe
        db: Database session
        current_user: Current user
        
    Returns:
        Cost information or error if insufficient credits
    """
    try:
        # Calculate cost
        cost = CreditCalculationService.calculate_backtest_cost(start_date, end_date, timeframe)
        
        # Get current balance
        balance = await CreditManagementService.get_user_balance(db, current_user["user_id"])
        
        if balance < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=InsufficientCreditsError(
                    needed=cost,
                    balance=float(balance)
                ).dict()
            )
        
        return {
            "cost": cost,
            "balance": float(balance),
            "sufficient": True,
            "message": f"User has sufficient credits. Cost: {cost}, Balance: {float(balance)}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/grant")
async def grant_credits(
    user_id: str,
    amount: float,
    description: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Grant credits to a user (admin function).
    
    Args:
        user_id: Target user ID
        amount: Amount to grant
        description: Reason for granting credits
        db: Database session
        current_user: Current user (must be admin)
        
    Returns:
        Transaction details
    """
    try:
        # TODO: Add admin role check
        # For now, allow any authenticated user to grant credits
        
        transaction = await CreditManagementService.credit_credits(
            db=db,
            user_id=user_id,
            amount=Decimal(str(amount)),
            description=description,
            metadata={"granted_by": current_user["user_id"]}
        )
        
        return {
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "amount": float(transaction.amount),
            "balance_after": float(transaction.balance_after),
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant credits: {str(e)}"
        )


@router.post("/refund/{transaction_id}")
async def refund_transaction(
    transaction_id: str,
    description: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Refund a specific transaction.
    
    Args:
        transaction_id: ID of the transaction to refund
        description: Reason for refund
        db: Database session
        current_user: Current user (must be admin)
        
    Returns:
        Refund transaction details
    """
    try:
        # TODO: Add admin role check
        # For now, allow any authenticated user to refund
        
        refund_transaction = await CreditManagementService.refund_transaction(
            db=db,
            transaction_id=transaction_id
        )
        
        return {
            "refund_transaction_id": refund_transaction.id,
            "original_transaction_id": transaction_id,
            "user_id": refund_transaction.user_id,
            "amount": float(refund_transaction.amount),
            "balance_after": float(refund_transaction.balance_after),
            "description": refund_transaction.description,
            "created_at": refund_transaction.created_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund transaction: {str(e)}"
        )
