from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import load_only
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Instrument, MarketData, Strategy, StrategyRuntimePreset, Timeframe
from ..services.strategy_registry import resolve_strategy
from ..services.dynamic_strategy_loader import build_dynamic_strategy_entry, DynamicStrategyLoadError, DynamicStrategySecurityError
from ..services.backtest_advanced_filters import apply_advanced_filters, build_filter_summary
from engine.backtest_engine import BacktestParams, BacktestResult, run_backtest_engine
from .trading.runtime_config_service import resolve_runtime_config, validate_runtime_config
from .trading.guardrails import validate_backtest_guardrails, RISK_ENGINE_VERSION, PNL_ENGINE_VERSION


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
    advanced_filter_impact: dict[str, Any] | None = None
    runtime_config: dict[str, Any] | None = None
    instrument_spec: dict[str, Any] | None = None
    warnings: list[str] | None = None
    rejected_trade_count: int = 0
    rejection_reasons: dict[str, int] | None = None

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
        advanced_filters: Any | None = None,
        runtime_config: dict[str, Any] | None = None,
        strategy_preset_id: str | None = None,
        timeframe_id: int | None = None,
    ) -> BacktestServiceResponse:
        if start_date >= end_date:
            raise InvalidDateRangeError(f"Start date {start_date} must be before end date {end_date}")

        resolved_timeframe = await BacktestService._resolve_timeframe(db, timeframe_id, timeframe)
        market_data_df = await BacktestService._fetch_market_data(db, instrument_id, resolved_timeframe, start_date, end_date)
        if market_data_df.empty:
            raise MarketDataNotFoundError(
                f"No market data found for instrument {instrument_id}, timeframe {resolved_timeframe}, period {start_date} to {end_date}"
            )

        instrument = await BacktestService._get_instrument(db, instrument_id)
        instrument_symbol = str(getattr(instrument, "symbol", f"Instrument_{instrument_id}")) if instrument else f"Instrument_{instrument_id}"
        instrument_market = getattr(instrument, "market", None) if instrument else None
        instrument_spec = BacktestService._instrument_to_spec(instrument)

        market_data_df, advanced_filter_impact = apply_advanced_filters(
            market_data_df,
            advanced_filters,
            timeframe=resolved_timeframe,
            instrument_symbol=instrument_symbol,
            instrument_market=instrument_market,
        )
        if advanced_filter_impact is not None:
            advanced_filter_impact["summary"] = build_filter_summary(advanced_filters)
        if market_data_df.empty:
            raise MarketDataNotFoundError(
                "Advanced filters removed all candles. Please widen the day/session/time filters."
            )

        strategy, strategy_class, strategy_params, strategy_name = await BacktestService._get_strategy_details(db, strategy_id)
        strategy_preset = await BacktestService._get_strategy_preset(db, strategy_preset_id, strategy_id)
        resolved_runtime_config = resolve_runtime_config(
            strategy=strategy,
            instrument=instrument,
            user_override=runtime_config,
            strategy_preset=strategy_preset,
        )
        # Capital in the payload remains source of truth for old API compatibility.
        resolved_runtime_config.setdefault("risk", {})["initial_capital"] = float(initial_capital)

        config_validation = validate_runtime_config(resolved_runtime_config)
        if not config_validation.get("valid"):
            raise BacktestError("Runtime config is invalid: " + "; ".join(config_validation.get("errors") or []))

        guardrail_result = validate_backtest_guardrails(
            resolved_runtime_config,
            instrument_spec,
            capital=float(initial_capital),
            candle_count=len(market_data_df),
        )
        if not guardrail_result.get("valid"):
            raise BacktestError(" ".join(guardrail_result.get("errors") or []))
        guardrail_warnings = list(guardrail_result.get("warnings") or [])
        merged_strategy_params = dict(strategy_params or {})
        if isinstance(resolved_runtime_config.get("strategy_params"), dict):
            merged_strategy_params.update(resolved_runtime_config.get("strategy_params") or {})

        backtest_params = BacktestParams(
            initial_capital=float(initial_capital),
            market=BacktestService._infer_market(instrument_market, instrument_symbol),
            trade_mode=BacktestService._infer_trade_mode(resolved_timeframe),
            rr_ratio=float((resolved_runtime_config.get("sl_tp") or {}).get("rr_ratio") or 2.0),
            capital_risk_pct=float((resolved_runtime_config.get("risk") or {}).get("risk_percent") or 0.01),
            price_risk_pct=float((resolved_runtime_config.get("sl_tp") or {}).get("fixed_price_risk_pct") or 0.002),
            use_strategy_sl_tp=bool((resolved_runtime_config.get("sl_tp") or {}).get("use_strategy_suggested_sl", False)),
            runtime_config=resolved_runtime_config,
            instrument_spec=instrument_spec,
        )

        result = run_backtest_engine(
            market_data=market_data_df,
            strategy_class=strategy_class,
            strategy_params=merged_strategy_params,
            backtest_params=backtest_params,
        )
        result.warnings = list(dict.fromkeys([*(getattr(result, "warnings", []) or []), *guardrail_warnings]))
        result.summary = getattr(result, "summary", {}) or {}
        result.summary.update({
            "risk_engine_version": RISK_ENGINE_VERSION,
            "pnl_engine_version": PNL_ENGINE_VERSION,
            "warnings": result.warnings,
            "rejected_trade_count": int(getattr(result, "rejected_trade_count", 0) or 0),
            "rejection_reasons": getattr(result, "rejection_reasons", {}) or {},
        })

        return BacktestServiceResponse(
            result=result,
            strategy_name=strategy_name,
            instrument_symbol=instrument_symbol,
            timeframe=resolved_timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal(str(initial_capital)),
            advanced_filter_impact=advanced_filter_impact,
            runtime_config=resolved_runtime_config,
            instrument_spec=instrument_spec,
            warnings=list(getattr(result, "warnings", []) or []),
            rejected_trade_count=int(getattr(result, "rejected_trade_count", 0) or 0),
            rejection_reasons=getattr(result, "rejection_reasons", {}) or {},
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
                .options(load_only(MarketData.timestamp, MarketData.open, MarketData.high, MarketData.low, MarketData.close, MarketData.volume))
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

        # Preserve DB candle timestamp exactly.
        # Do not strip tzinfo here: MT5 candles are UTC instants in DB, and
        # frontend/report should convert/display the same instant consistently.
        df = pd.DataFrame([
            {
                "Date": pd.to_datetime(row.timestamp),
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
    async def _get_strategy_details(db: AsyncSession, strategy_id: str) -> Tuple[Strategy, Any, Dict[str, Any], str]:
        strategy = await db.get(Strategy, strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy with id {strategy_id} not found")
        params = strategy.parameters if isinstance(strategy.parameters, dict) else None
        dynamic_requested = bool(
            isinstance(params, dict)
            and str(params.get("source_code") or "").strip()
            and str(params.get("engine_mode") or "").upper() == "DYNAMIC_DB"
        )

        if dynamic_requested:
            try:
                strategy_class, strategy_params, strategy_name = build_dynamic_strategy_entry(
                    strategy_id=str(strategy.id),
                    strategy_name=str(strategy.name),
                    db_parameters=params,
                )
                return strategy, strategy_class, strategy_params, strategy_name
            except (DynamicStrategyLoadError, DynamicStrategySecurityError, ValueError) as dynamic_exc:
                raise StrategyNotFoundError(f"Dynamic strategy load failed: {dynamic_exc}") from dynamic_exc

        try:
            strategy_class, strategy_params, strategy_name = resolve_strategy(
                strategy_id=str(strategy.id),
                strategy_name=str(strategy.name),
                db_parameters=params,
            )
        except ValueError as static_exc:
            if isinstance(params, dict) and str(params.get("source_code") or "").strip():
                try:
                    strategy_class, strategy_params, strategy_name = build_dynamic_strategy_entry(
                        strategy_id=str(strategy.id),
                        strategy_name=str(strategy.name),
                        db_parameters=params,
                    )
                except (DynamicStrategyLoadError, DynamicStrategySecurityError, ValueError) as dynamic_exc:
                    raise StrategyNotFoundError(
                        f"No static mapping found and dynamic strategy load failed: {dynamic_exc}"
                    ) from dynamic_exc
            else:
                raise StrategyNotFoundError(str(static_exc)) from static_exc
        return strategy, strategy_class, strategy_params, strategy_name

    @staticmethod
    async def _get_strategy_preset(db: AsyncSession, preset_id: str | None, strategy_id: str) -> StrategyRuntimePreset | None:
        if preset_id:
            preset = await db.get(StrategyRuntimePreset, str(preset_id))
            if preset and str(preset.strategy_id) == str(strategy_id) and bool(getattr(preset, "is_active", True)):
                return preset
            return None
        rows = (
            await db.execute(
                select(StrategyRuntimePreset).where(
                    StrategyRuntimePreset.strategy_id == str(strategy_id),
                    StrategyRuntimePreset.is_default == True,
                    StrategyRuntimePreset.is_active == True,
                )
            )
        ).scalars().all()
        return rows[0] if rows else None

    @staticmethod
    async def _get_instrument(db: AsyncSession, instrument_id: int) -> Instrument | None:
        return await db.get(Instrument, instrument_id)

    @staticmethod
    def _instrument_to_spec(instrument: Instrument | None) -> dict[str, Any]:
        if instrument is None:
            return {}
        fields = [
            "id", "symbol", "name", "market", "asset_class", "base_currency", "quote_currency",
            "account_currency", "currency_symbol", "price_unit_name", "quantity_mode", "contract_size",
            "tick_size", "tick_value_per_lot", "pip_size", "min_quantity", "max_quantity",
            "quantity_step", "min_lot", "max_lot", "lot_step", "price_precision",
            "quantity_precision", "broker_symbol", "is_tradeable_backtest", "is_tradeable_live",
        ]
        spec: dict[str, Any] = {}
        for field in fields:
            value = getattr(instrument, field, None)
            if isinstance(value, Decimal):
                value = float(value)
            spec[field] = value
        spec["quantity_mode"] = str(spec.get("quantity_mode") or "SHARES").upper()
        spec["account_currency"] = spec.get("account_currency")
        spec["currency_symbol"] = spec.get("currency_symbol") or ("₹" if spec.get("account_currency") == "INR" else "$" if spec.get("account_currency") == "USD" else None)
        spec["tick_size"] = float(spec.get("tick_size")) if spec.get("tick_size") is not None else None
        spec["pip_size"] = float(spec.get("pip_size") or spec.get("tick_size")) if (spec.get("pip_size") is not None or spec.get("tick_size") is not None) else None
        return spec

    @staticmethod
    async def _resolve_timeframe(db: AsyncSession, timeframe_id: int | None, fallback: str) -> str:
        if timeframe_id is None:
            return fallback
        timeframe = await db.get(Timeframe, timeframe_id)
        return str(getattr(timeframe, "code", None) or fallback)

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
