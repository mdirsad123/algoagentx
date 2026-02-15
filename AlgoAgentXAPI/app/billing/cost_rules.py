"""
Cost calculation rules for backtests and AI screener
Centralized cost logic for credit-based pricing
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum


class CostType(str, Enum):
    """Cost calculation types"""
    BACKTEST = "backtest"
    AI_SCREENER = "ai_screener"


class CostRules:
    """Centralized cost calculation rules"""
    
    # Backtest cost rules based on date range
    BACKTEST_COST_RULES = [
        {"max_days": 180, "base_cost": 5},
        {"max_days": 365, "base_cost": 10},
        {"max_days": 730, "base_cost": 15},
        {"max_days": float('inf'), "base_cost": 25}  # For ranges > 730 days
    ]
    
    # Timeframe multipliers
    TIMEFRAME_MULTIPLIERS = {
        "1m": 1.5,
        "5m": 1.5,
        "15m": 1.2,
        "30m": 1.1,
        "1h": 1.0,
        "4h": 0.8,
        "1d": 0.5,
        "1w": 0.3,
        "1M": 0.2
    }
    
    # AI Screener cost rules
    AI_SCREENER_COST_RULES = {
        "basic": 10,
        "advanced": 25,
        "deep": 50
    }
    
    @staticmethod
    def calculate_backtest_cost(start_date: datetime, end_date: datetime, timeframe: str) -> int:
        """
        Calculate backtest cost based on date range and timeframe
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Chart timeframe (1m, 5m, 1h, etc.)
        
        Returns:
            Cost in credits
        """
        # Calculate date range in days
        date_range_days = (end_date - start_date).days
        
        # Find base cost based on date range
        base_cost = 0
        for rule in CostRules.BACKTEST_COST_RULES:
            if date_range_days <= rule["max_days"]:
                base_cost = rule["base_cost"]
                break
        
        # Apply timeframe multiplier
        multiplier = CostRules.TIMEFRAME_MULTIPLIERS.get(timeframe.lower(), 1.0)
        final_cost = int(base_cost * multiplier)
        
        return max(final_cost, 1)  # Minimum cost of 1 credit
    
    @staticmethod
    def calculate_ai_screener_cost(mode: str, depth: Optional[str] = None) -> int:
        """
        Calculate AI screener cost based on mode and depth
        
        Args:
            mode: Screener mode (basic, advanced, deep)
            depth: Analysis depth (optional)
        
        Returns:
            Cost in credits
        """
        base_cost = CostRules.AI_SCREENER_COST_RULES.get(mode.lower(), 10)
        
        # Apply depth multiplier if specified
        if depth:
            depth_multipliers = {
                "light": 1.0,
                "medium": 1.5,
                "deep": 2.0
            }
            multiplier = depth_multipliers.get(depth.lower(), 1.0)
            base_cost = int(base_cost * multiplier)
        
        return base_cost
    
    @staticmethod
    def get_cost_breakdown(cost_type: str, **kwargs) -> Dict[str, Any]:
        """
        Get detailed cost breakdown for transparency
        
        Args:
            cost_type: Type of cost calculation
            **kwargs: Additional parameters based on cost type
        
        Returns:
            Detailed cost breakdown
        """
        breakdown = {
            "type": cost_type,
            "base_cost": 0,
            "multipliers": {},
            "total_cost": 0,
            "details": {}
        }
        
        if cost_type == CostType.BACKTEST:
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date")
            timeframe = kwargs.get("timeframe", "1h")
            
            if start_date and end_date:
                date_range_days = (end_date - start_date).days
                breakdown["details"]["date_range_days"] = date_range_days
                breakdown["details"]["timeframe"] = timeframe
                
                # Find base cost
                for rule in CostRules.BACKTEST_COST_RULES:
                    if date_range_days <= rule["max_days"]:
                        breakdown["base_cost"] = rule["base_cost"]
                        breakdown["details"]["date_range_tier"] = f"≤ {rule['max_days']} days"
                        break
                
                # Apply timeframe multiplier
                multiplier = CostRules.TIMEFRAME_MULTIPLIERS.get(timeframe.lower(), 1.0)
                breakdown["multipliers"]["timeframe"] = {
                    "timeframe": timeframe,
                    "multiplier": multiplier
                }
                
                breakdown["total_cost"] = int(breakdown["base_cost"] * multiplier)
        
        elif cost_type == CostType.AI_SCREENER:
            mode = kwargs.get("mode", "basic")
            depth = kwargs.get("depth")
            
            breakdown["details"]["mode"] = mode
            if depth:
                breakdown["details"]["depth"] = depth
            
            base_cost = CostRules.AI_SCREENER_COST_RULES.get(mode.lower(), 10)
            breakdown["base_cost"] = base_cost
            
            if depth:
                depth_multipliers = {
                    "light": 1.0,
                    "medium": 1.5,
                    "deep": 2.0
                }
                multiplier = depth_multipliers.get(depth.lower(), 1.0)
                breakdown["multipliers"]["depth"] = {
                    "depth": depth,
                    "multiplier": multiplier
                }
                breakdown["total_cost"] = int(base_cost * multiplier)
            else:
                breakdown["total_cost"] = base_cost
        
        return breakdown
    
    @staticmethod
    def validate_cost_parameters(cost_type: str, **kwargs) -> bool:
        """
        Validate cost calculation parameters
        
        Args:
            cost_type: Type of cost calculation
            **kwargs: Parameters to validate
        
        Returns:
            True if parameters are valid
        """
        if cost_type == CostType.BACKTEST:
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date")
            timeframe = kwargs.get("timeframe")
            
            if not start_date or not end_date:
                return False
            
            if start_date >= end_date:
                return False
            
            if (end_date - start_date).days > 3650:  # Max 10 years
                return False
            
            if timeframe and timeframe.lower() not in CostRules.TIMEFRAME_MULTIPLIERS:
                return False
            
            return True
        
        elif cost_type == CostType.AI_SCREENER:
            mode = kwargs.get("mode", "").lower()
            depth = kwargs.get("depth", "").lower()
            
            if mode not in CostRules.AI_SCREENER_COST_RULES:
                return False
            
            if depth and depth not in ["light", "medium", "deep"]:
                return False
            
            return True
        
        return False