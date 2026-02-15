"""
Billing API endpoints
Handles plan information and cost preview functionality
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.schemas.billing import PlanResponse, CostPreviewRequest, CostPreviewResponse
from app.billing.plan_catalog import PlanCatalog
from app.billing.cost_rules import CostRules, CostType
from app.core.dependencies import get_current_user, get_user_entitlements, get_db

router = APIRouter()


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans():
    """
    Get all available plans with their features and pricing
    
    Returns:
        List of all available plans
    """
    try:
        plans_data = PlanCatalog.get_all_plans()
        plans = []
        
        for plan_key, plan_info in plans_data.items():
            plans.append(PlanResponse(
                code=plan_info["code"],
                billing_period=plan_info["billing_period"],
                price_inr=plan_info["price_inr"],
                included_credits=plan_info["included_credits"],
                features=plan_info["features"],
                is_active=plan_info["is_active"]
            ))
        
        return plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")


@router.post("/preview-cost", response_model=CostPreviewResponse)
async def preview_cost(request: CostPreviewRequest):
    """
    Preview cost for backtest or AI screener operations
    
    Args:
        request: Cost preview request with operation details
    
    Returns:
        Cost preview with detailed breakdown
    """
    try:
        # Validate request parameters
        if request.type == "backtest":
            if not request.start_date or not request.end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="start_date and end_date are required for backtest cost calculation"
                )
            
            if not request.timeframe:
                request.timeframe = "1h"  # Default timeframe
            
            # Validate parameters
            if not CostRules.validate_cost_parameters(
                CostType.BACKTEST,
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backtest parameters"
                )
            
            # Calculate cost
            cost = CostRules.calculate_backtest_cost(
                request.start_date,
                request.end_date,
                request.timeframe
            )
            
            # Get detailed breakdown
            breakdown = CostRules.get_cost_breakdown(
                CostType.BACKTEST,
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe
            )
        
        elif request.type == "ai_screener":
            if not request.mode:
                request.mode = "basic"  # Default mode
            
            # Validate parameters
            if not CostRules.validate_cost_parameters(
                CostType.AI_SCREENER,
                mode=request.mode,
                depth=request.depth
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid AI screener parameters"
                )
            
            # Calculate cost
            cost = CostRules.calculate_ai_screener_cost(
                request.mode,
                request.depth
            )
            
            # Get detailed breakdown
            breakdown = CostRules.get_cost_breakdown(
                CostType.AI_SCREENER,
                mode=request.mode,
                depth=request.depth
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid cost type. Must be 'backtest' or 'ai_screener'"
            )
        
        return CostPreviewResponse(
            type=request.type,
            total_cost=cost,
            breakdown=breakdown
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating cost: {str(e)}"
        )


@router.get("/cost-rules")
async def get_cost_rules():
    """
    Get cost calculation rules and multipliers
    
    Returns:
        Cost calculation rules and multipliers
    """
    try:
        rules = {
            "backtest_cost_rules": CostRules.BACKTEST_COST_RULES,
            "timeframe_multipliers": CostRules.TIMEFRAME_MULTIPLIERS,
            "ai_screener_cost_rules": CostRules.AI_SCREENER_COST_RULES,
            "valid_timeframes": list(CostRules.TIMEFRAME_MULTIPLIERS.keys()),
            "valid_modes": list(CostRules.AI_SCREENER_COST_RULES.keys()),
            "valid_depths": ["light", "medium", "deep"]
        }
        
        return rules
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cost rules: {str(e)}"
        )


@router.get("/me")
async def get_user_billing_info(
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's billing information
    
    Returns:
        Current plan, trial status, credits balance, and limits summary
    """
    try:
        # Get user's credit balance
        credits_query = text("""
            SELECT balance FROM user_credits WHERE user_id = :user_id
        """)
        
        credits_result = await db.execute(credits_query, {"user_id": current_user["user_id"]})
        credits_row = credits_result.fetchone()
        credits_balance = credits_row.balance if credits_row else 0
        
        # Get daily usage counts
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Backtest count
        backtest_count_query = text("""
            SELECT COUNT(*) as count FROM backtests 
            WHERE user_id = :user_id AND created_at >= :start_date AND created_at < :end_date
        """)
        
        backtest_result = await db.execute(backtest_count_query, {
            "user_id": current_user["user_id"],
            "start_date": today_start,
            "end_date": today_end
        })
        daily_backtest_count = backtest_result.scalar() or 0
        
        # AI runs count (placeholder - would need actual tracking)
        ai_runs_count_query = text("""
            SELECT COUNT(*) as count FROM credit_transactions 
            WHERE user_id = :user_id AND type = 'DEBIT' AND reason LIKE '%AI%' 
            AND created_at >= :start_date AND created_at < :end_date
        """)
        
        ai_result = await db.execute(ai_runs_count_query, {
            "user_id": current_user["user_id"],
            "start_date": today_start,
            "end_date": today_end
        })
        daily_ai_runs_count = ai_result.scalar() or 0
        
        return {
            "user_id": current_user["user_id"],
            "plan": {
                "code": entitlements["plan_code"],
                "billing_period": entitlements["billing_period"],
                "price_inr": entitlements["price_inr"],
                "subscription_status": entitlements["subscription_status"],
                "is_trial": entitlements["is_trial"],
                "is_premium": entitlements["is_premium"]
            },
            "trial": {
                "remaining_days": entitlements["trial_remaining_days"],
                "end_date": (datetime.utcnow() + timedelta(days=entitlements["trial_remaining_days"])).isoformat() if entitlements["trial_remaining_days"] > 0 else None
            },
            "credits": {
                "balance": credits_balance,
                "included_in_plan": entitlements["included_credits"],
                "total_available": credits_balance + entitlements["included_credits"]
            },
            "limits": {
                "max_backtests_per_day": entitlements["features"]["backtests_per_day"],
                "daily_backtests_used": daily_backtest_count,
                "backtests_remaining_today": max(0, entitlements["features"]["backtests_per_day"] - daily_backtest_count),
                
                "max_ai_runs_per_day": entitlements["features"]["ai_runs_per_day"],
                "daily_ai_runs_used": daily_ai_runs_count,
                "ai_runs_remaining_today": max(0, entitlements["features"]["ai_runs_per_day"] - daily_ai_runs_count),
                
                "max_parallel_jobs": entitlements["features"]["max_parallel_jobs"],
                "max_date_range_days": entitlements["features"]["max_date_range_days"],
                "export_enabled": entitlements["features"]["export_enabled"],
                "support_priority": entitlements["features"]["support_priority"]
            },
            "usage": {
                "daily_backtest_count": daily_backtest_count,
                "daily_ai_runs_count": daily_ai_runs_count
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving billing information: {str(e)}"
        )
