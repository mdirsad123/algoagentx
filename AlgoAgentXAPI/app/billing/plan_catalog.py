"""
Plan catalog for subscription system
Defines plan features, limits, and included credits
"""
from typing import Dict, Any
from enum import Enum


class PlanCode(str, Enum):
    """Plan codes"""
    FREE = "FREE"
    PRO = "PRO"
    PREMIUM = "PREMIUM"
    ULTIMATE = "ULTIMATE"


class BillingPeriod(str, Enum):
    """Billing periods"""
    NONE = "NONE"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class PlanCatalog:
    """Centralized plan definitions and benefits"""
    
    @staticmethod
    def get_plan_features(plan_code: str, billing_period: str) -> Dict[str, Any]:
        """
        Get plan features and limits
        
        Args:
            plan_code: Plan code (FREE, PRO, PREMIUM, ULTIMATE)
            billing_period: Billing period (NONE, MONTHLY, YEARLY)
        
        Returns:
            Dictionary with plan features and limits
        """
        base_features = {
            PlanCode.FREE: {
                "backtests_per_day": 5,
                "ai_runs_per_day": 3,
                "max_parallel_jobs": 1,
                "max_date_range_days": 30,
                "export_enabled": False,
                "support_priority": "LOW"
            },
            PlanCode.PRO: {
                "backtests_per_day": 50,
                "ai_runs_per_day": 20,
                "max_parallel_jobs": 3,
                "max_date_range_days": 180,
                "export_enabled": True,
                "support_priority": "MEDIUM"
            },
            PlanCode.PREMIUM: {
                "backtests_per_day": 200,
                "ai_runs_per_day": 100,
                "max_parallel_jobs": 5,
                "max_date_range_days": 365,
                "export_enabled": True,
                "support_priority": "HIGH"
            },
            PlanCode.ULTIMATE: {
                "backtests_per_day": 500,
                "ai_runs_per_day": 300,
                "max_parallel_jobs": 10,
                "max_date_range_days": 730,
                "export_enabled": True,
                "support_priority": "PRIORITY"
            }
        }
        
        return base_features.get(plan_code, base_features[PlanCode.FREE])
    
    @staticmethod
    def get_included_credits(plan_code: str, billing_period: str) -> int:
        """
        Get included credits per billing period
        
        Args:
            plan_code: Plan code (FREE, PRO, PREMIUM, ULTIMATE)
            billing_period: Billing period (NONE, MONTHLY, YEARLY)
        
        Returns:
            Number of included credits
        """
        credit_map = {
            (PlanCode.FREE, BillingPeriod.NONE): 50,
            (PlanCode.PRO, BillingPeriod.MONTHLY): 500,
            (PlanCode.PRO, BillingPeriod.YEARLY): 6000,
            (PlanCode.PREMIUM, BillingPeriod.MONTHLY): 1500,
            (PlanCode.PREMIUM, BillingPeriod.YEARLY): 18000,
            (PlanCode.ULTIMATE, BillingPeriod.MONTHLY): 5000,
            (PlanCode.ULTIMATE, BillingPeriod.YEARLY): 60000,
        }
        
        return credit_map.get((plan_code, billing_period), 0)
    
    @staticmethod
    def get_plan_price(plan_code: str, billing_period: str) -> int:
        """
        Get plan price in INR
        
        Args:
            plan_code: Plan code (FREE, PRO, PREMIUM, ULTIMATE)
            billing_period: Billing period (NONE, MONTHLY, YEARLY)
        
        Returns:
            Price in INR
        """
        price_map = {
            (PlanCode.FREE, BillingPeriod.NONE): 0,
            (PlanCode.PRO, BillingPeriod.MONTHLY): 999,
            (PlanCode.PRO, BillingPeriod.YEARLY): 9999,
            (PlanCode.PREMIUM, BillingPeriod.MONTHLY): 1999,
            (PlanCode.PREMIUM, BillingPeriod.YEARLY): 19999,
            (PlanCode.ULTIMATE, BillingPeriod.MONTHLY): 3999,
            (PlanCode.ULTIMATE, BillingPeriod.YEARLY): 39999,
        }
        
        return price_map.get((plan_code, billing_period), 0)
    
    @staticmethod
    def get_all_plans() -> Dict[str, Dict[str, Any]]:
        """
        Get all available plans with their details
        
        Returns:
            Dictionary of all plans with features and pricing
        """
        plans = {}
        
        for plan_code in [PlanCode.FREE, PlanCode.PRO, PlanCode.PREMIUM, PlanCode.ULTIMATE]:
            for billing_period in [BillingPeriod.NONE, BillingPeriod.MONTHLY, BillingPeriod.YEARLY]:
                # Skip invalid combinations
                if plan_code == PlanCode.FREE and billing_period != BillingPeriod.NONE:
                    continue
                if plan_code != PlanCode.FREE and billing_period == BillingPeriod.NONE:
                    continue
                
                plan_key = f"{plan_code}_{billing_period}"
                plans[plan_key] = {
                    "code": plan_code,
                    "billing_period": billing_period,
                    "price_inr": PlanCatalog.get_plan_price(plan_code, billing_period),
                    "included_credits": PlanCatalog.get_included_credits(plan_code, billing_period),
                    "features": PlanCatalog.get_plan_features(plan_code, billing_period),
                    "is_active": True
                }
        
        return plans
    
    @staticmethod
    def is_valid_plan(plan_code: str, billing_period: str) -> bool:
        """
        Check if plan combination is valid
        
        Args:
            plan_code: Plan code
            billing_period: Billing period
        
        Returns:
            True if valid combination
        """
        valid_combinations = {
            (PlanCode.FREE, BillingPeriod.NONE),
            (PlanCode.PRO, BillingPeriod.MONTHLY),
            (PlanCode.PRO, BillingPeriod.YEARLY),
            (PlanCode.PREMIUM, BillingPeriod.MONTHLY),
            (PlanCode.PREMIUM, BillingPeriod.YEARLY),
            (PlanCode.ULTIMATE, BillingPeriod.MONTHLY),
            (PlanCode.ULTIMATE, BillingPeriod.YEARLY),
        }
        
        return (plan_code, billing_period) in valid_combinations