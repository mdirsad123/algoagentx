from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Instrument, MarketData, Strategy
from ..services.strategy_registry import resolve_strategy
from engine.backtest_engine import BacktestParams, BacktestResult, run_backtest_engine


class BacktestError(Exception):
    pass


class MarketDataNotFoundError(BacktestError):
    pass


class InvalidDateRangeError(BacktestError):
    pass


class StrategyNotFoundError(BacktestError):
    pass


@dataclass
class BacktestServiceResponse:
    result: BacktestResult
    strategy_name: str
    instrument_symbol: str
    timeframe: str
    start_date: date
    end_date: date
    initial_capital: Decimal

    @property
    def final_capital(self) -> Decimal:
        return Decimal(str(self.result.final_capital))

    @property
    def net_profit(self) -> Decimal:
        return self.final_capital - self.initial_capital

    @property
    def max_drawdown(self) -> Decimal:
        return Decimal(str(self.result.max_drawdown))

    @property
    def sharpe_ratio(self) -> Decimal:
        return Decimal(str(self.result.sharpe_ratio))

    @property
    def win_rate(self) -> Decimal:
        return Decimal(str(self.result.win_rate))

    @property
    def total_trades(self) -> int:
        return int(self.result.total_trades)


class BacktestService:
    @staticmethod
    async def run_backtest(
        db: AsyncSession,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal = Decimal("100000"),
    ) -> BacktestServiceResponse:
        if start_date >= end_date:
            raise InvalidDateRangeError(f"Start date {start_date} must be before end date {end_date}")

        market_data_df = await BacktestService._fetch_market_data(db, instrument_id, timeframe, start_date, end_date)
        if market_data_df.empty:
            raise MarketDataNotFoundError(
                f"No market data found for instrument {instrument_id}, timeframe {timeframe}, period {start_date} to {end_date}"
            )

        strategy_class, strategy_params, strategy_name = await BacktestService._get_strategy_details(db, strategy_id)
        instrument_symbol, instrument_market = await BacktestService._get_instrument_details(db, instrument_id)

        backtest_params = BacktestParams(
            initial_capital=float(initial_capital),
            market=BacktestService._infer_market(instrument_market, instrument_symbol),
            trade_mode=BacktestService._infer_trade_mode(timeframe),
        )

        result = run_backtest_engine(
            market_data=market_data_df,
            strategy_class=strategy_class,
            strategy_params=strategy_params,
            backtest_params=backtest_params,
        )

        return BacktestServiceResponse(
            result=result,
            strategy_name=strategy_name,
            instrument_symbol=instrument_symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal(str(initial_capital)),
        )

    @staticmethod
    async def _fetch_market_data(
        db: AsyncSession,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        rows = (
            await db.execute(
                select(MarketData)
                .where(
                    MarketData.instrument_id == instrument_id,
                    MarketData.timeframe == timeframe,
                    MarketData.timestamp >= start_dt,
                    MarketData.timestamp <= end_dt,
                )
                .order_by(MarketData.timestamp.asc())
            )
        ).scalars().all()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                "Date": pd.to_datetime((row.timestamp.replace(tzinfo=None) if getattr(row.timestamp, 'tzinfo', None) else row.timestamp)),
                "Open": float(row.open),
                "High": float(row.high),
                "Low": float(row.low),
                "Close": float(row.close),
                "Volume": float(row.volume or 0),
            }
            for row in rows
        ])
        return df.sort_values("Date").reset_index(drop=True)

    @staticmethod
    async def _get_strategy_details(db: AsyncSession, strategy_id: str) -> Tuple[Any, Dict[str, Any], str]:
        strategy = await db.get(Strategy, strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy with id {strategy_id} not found")
        try:
            strategy_class, strategy_params, strategy_name = resolve_strategy(
                strategy_id=str(strategy.id),
                strategy_name=str(strategy.name),
                db_parameters=strategy.parameters if isinstance(strategy.parameters, dict) else None,
            )
        except ValueError as exc:
            raise StrategyNotFoundError(str(exc)) from exc
        return strategy_class, strategy_params, strategy_name

    @staticmethod
    async def _get_instrument_details(db: AsyncSession, instrument_id: int) -> Tuple[str, Optional[str]]:
        instrument = await db.get(Instrument, instrument_id)
        if not instrument:
            return f"Instrument_{instrument_id}", None
        return str(getattr(instrument, 'symbol', f'Instrument_{instrument_id}')), getattr(instrument, 'market', None)

    @staticmethod
    def _infer_trade_mode(timeframe: str) -> str:
        tf = str(timeframe or '').lower()
        if tf in {'1m', '3m', '5m'}:
            return 'scalp'
        if tf in {'10m', '15m', '30m'}:
            return 'intraday'
        return 'swing'

    @staticmethod
    def _infer_market(instrument_market: Optional[str], symbol: str) -> str:
        market = str(instrument_market or '').upper()
        symbol_upper = str(symbol or '').upper()
        if market in {'CRYPTO', 'FOREX', 'INDIA'}:
            return market
        if any(token in symbol_upper for token in ['BTC', 'ETH', 'USDT']):
            return 'CRYPTO'
        if any(token in symbol_upper for token in ['XAU', 'EUR', 'GBP', 'JPY', 'USD']):
            return 'FOREX'
        return 'INDIA'
