"""
Metrics calculation service for backtest performance analysis.

This module provides pure functions to calculate trading performance metrics
from equity curve and trades data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from decimal import Decimal


class MetricsCalculator:
    """
    Pure functions for calculating trading performance metrics.

    Designed for unit testing and reusability across different contexts.
    """

    @staticmethod
    def calculate_net_profit(equity_curve: pd.DataFrame, initial_capital: float = 100000.0) -> float:
        """
        Calculate net profit as final equity minus initial capital.

        Args:
            equity_curve: DataFrame with 'equity' column
            initial_capital: Starting capital amount

        Returns:
            Net profit amount
        """
        if equity_curve.empty:
            return 0.0

        final_equity = float(equity_curve['equity'].iloc[-1])
        return final_equity - initial_capital

    @staticmethod
    def calculate_win_rate(trades: pd.DataFrame) -> float:
        """
        Calculate win rate as percentage of profitable trades.

        Args:
            trades: DataFrame with 'pnl' column

        Returns:
            Win rate as decimal (0.0 to 1.0)
        """
        if trades.empty:
            return 0.0

        winning_trades = trades[trades['pnl'] > 0]
        return len(winning_trades) / len(trades)

    @staticmethod
    def calculate_max_drawdown(equity_curve: pd.DataFrame) -> float:
        """
        Calculate maximum drawdown as the largest peak-to-trough decline.

        Args:
            equity_curve: DataFrame with 'equity' column

        Returns:
            Maximum drawdown as decimal (negative value)
        """
        if equity_curve.empty:
            return 0.0

        equity_series = pd.Series(equity_curve['equity'].values)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        return float(drawdown.min())

    @staticmethod
    def calculate_sharpe_ratio(
        equity_curve: pd.DataFrame,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ) -> float:
        """
        Calculate Sharpe ratio (annualized).

        Sharpe = (mean return - risk_free_rate) / std_dev_returns * sqrt(trading_days)

        Args:
            equity_curve: DataFrame with 'equity' column
            risk_free_rate: Annual risk-free rate (default 2%)
            trading_days: Number of trading days per year (default 252)

        Returns:
            Sharpe ratio
        """
        if len(equity_curve) < 2:
            return 0.0

        # Calculate daily returns
        equity_series = pd.Series(equity_curve['equity'].values)
        returns = equity_series.pct_change().dropna()

        if returns.std() == 0:
            return 0.0

        # Annualize
        mean_return = returns.mean() * trading_days
        std_return = returns.std() * np.sqrt(trading_days)

        sharpe = (mean_return - risk_free_rate) / std_return
        return float(sharpe)

    @staticmethod
    def calculate_profit_factor(trades: pd.DataFrame) -> float:
        """
        Calculate profit factor as total profits divided by total losses.

        Args:
            trades: DataFrame with 'pnl' column

        Returns:
            Profit factor (returns 0.0 if no losses)
        """
        if trades.empty:
            return 0.0

        profits = trades[trades['pnl'] > 0]['pnl'].sum()
        losses = abs(trades[trades['pnl'] < 0]['pnl'].sum())

        if losses == 0:
            return float('inf') if profits > 0 else 0.0

        return float(profits / losses)

    @staticmethod
    def calculate_all_metrics(
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame,
        initial_capital: float = 100000.0,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ) -> Dict[str, Any]:
        """
        Calculate all performance metrics and return as dictionary.

        Args:
            equity_curve: DataFrame with 'equity' column
            trades: DataFrame with 'pnl' column
            initial_capital: Starting capital amount
            risk_free_rate: Annual risk-free rate
            trading_days: Number of trading days per year

        Returns:
            Dictionary with metric names as keys and values as values
        """
        return {
            'net_profit': MetricsCalculator.calculate_net_profit(equity_curve, initial_capital),
            'win_rate': MetricsCalculator.calculate_win_rate(trades),
            'max_drawdown': MetricsCalculator.calculate_max_drawdown(equity_curve),
            'sharpe_ratio': MetricsCalculator.calculate_sharpe_ratio(
                equity_curve, risk_free_rate, trading_days
            ),
            'profit_factor': MetricsCalculator.calculate_profit_factor(trades),
        }

    @staticmethod
    def format_metrics_for_db(metrics_dict: Dict[str, Any], backtest_id: str) -> list:
        """
        Format metrics dictionary for database insertion.

        Args:
            metrics_dict: Dictionary of metric names and values
            backtest_id: UUID of the backtest

        Returns:
            List of dictionaries ready for DB insertion
        """
        formatted_metrics = []
        for name, value in metrics_dict.items():
            # Convert to Decimal for database precision
            if isinstance(value, float):
                if np.isinf(value):
                    decimal_value = None  # Handle infinity
                else:
                    decimal_value = Decimal(str(round(value, 6)))
            else:
                decimal_value = Decimal(str(value))

            formatted_metrics.append({
                'backtest_id': backtest_id,
                'name': name,
                'value': decimal_value
            })

        return formatted_metrics

    @staticmethod
    def format_metrics_for_response(metrics_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format metrics dictionary for API response.

        Args:
            metrics_dict: Dictionary of metric names and values

        Returns:
            Dictionary with rounded values for frontend consumption
        """
        return {
            name: round(value, 4) if isinstance(value, (int, float)) and not np.isinf(value) else value
            for name, value in metrics_dict.items()
        }
