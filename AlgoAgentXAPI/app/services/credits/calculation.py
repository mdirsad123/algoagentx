from datetime import date, timedelta
from decimal import Decimal
from typing import Optional


class CreditCalculationService:
    """Service for calculating backtest credit costs based on parameters."""
    
    @staticmethod
    def calculate_backtest_cost(
        start_date: date,
        end_date: date,
        timeframe: Optional[str] = None
    ) -> int:
        """
        Calculate credit cost for a backtest run.
        
        Cost rules:
        - <= 6 months: cost 5
        - > 6 and <= 12 months: cost 10  
        - > 12 months: cost 15
        - If timeframe is '1m' or '5m': add +5 cost
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Timeframe string (optional)
            
        Returns:
            Credit cost as integer
        """
        if start_date >= end_date:
            raise ValueError("Start date must be before end date")
            
        # Calculate months between dates
        months = CreditCalculationService._calculate_months(start_date, end_date)
        
        # Determine base cost based on months
        if months <= 6:
            base_cost = 5
        elif months <= 12:
            base_cost = 10
        else:
            base_cost = 15
            
        # Add timeframe bonus if applicable
        timeframe_bonus = 0
        if timeframe in ['1m', '5m']:
            timeframe_bonus = 5
            
        total_cost = base_cost + timeframe_bonus
        
        return total_cost
    
    @staticmethod
    def _calculate_months(start_date: date, end_date: date) -> int:
        """
        Calculate the number of months between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Number of months (rounded up)
        """
        # Calculate total days
        total_days = (end_date - start_date).days
        
        # Convert to months (approximate: 30.44 days per month)
        months = total_days / 30.44
        
        # Round up to nearest integer
        import math
        return math.ceil(months)
    
    @staticmethod
    def format_cost_breakdown(
        start_date: date,
        end_date: date,
        timeframe: Optional[str] = None
    ) -> dict:
        """
        Format detailed cost breakdown for API response.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Timeframe string (optional)
            
        Returns:
            Dictionary with cost breakdown details
        """
        months = CreditCalculationService._calculate_months(start_date, end_date)
        
        # Determine base cost
        if months <= 6:
            base_cost = 5
            cost_reason = "≤ 6 months"
        elif months <= 12:
            base_cost = 10
            cost_reason = "6-12 months"
        else:
            base_cost = 15
            cost_reason = "> 12 months"
            
        # Calculate timeframe bonus
        timeframe_bonus = 0
        timeframe_reason = ""
        if timeframe in ['1m', '5m']:
            timeframe_bonus = 5
            timeframe_reason = f"+5 for {timeframe} timeframe"
            
        total_cost = base_cost + timeframe_bonus
        
        return {
            "months": months,
            "base_cost": base_cost,
            "base_cost_reason": cost_reason,
            "timeframe_bonus": timeframe_bonus,
            "timeframe_reason": timeframe_reason,
            "total_cost": total_cost
        }