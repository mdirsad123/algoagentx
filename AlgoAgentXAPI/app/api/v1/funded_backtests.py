from __future__ import annotations

from datetime import datetime, timezone
import csv
import io
from decimal import Decimal
from uuid import UUID
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ...core.dependencies import get_current_user, get_db
from ...db.models import (
    FundedAccountPhase,
    FundedAccountProfile,
    FundedBacktestDailySnapshot,
    FundedBacktestEvent,
    FundedBacktestPhase,
    FundedBacktestRun,
    FundedBacktestTrade,
    FundedRiskTier,
    Instrument,
    Strategy,
)
from ...schemas.funded_backtests import FundedProfileCreate, FundedProfileUpdate, FundedRunRequest
from ...services.backtest_service import BacktestError, BacktestService, MarketDataNotFoundError, StrategyNotFoundError
from ...services.funded_backtest import FUNDED_RULE_ENGINE_VERSION
from ...services.funded_backtest.simulator import FundedBacktestSimulator, FundedOpportunity
from ...services.funded_backtest.snapshots import build_run_snapshots
from ...services.funded_backtest.report_exports import build_funded_excel, build_funded_pdf
from ...services.funded_backtest.billing_service import build_funded_credit_quote
from ...services.credits.management import CreditManagementService
from ...services.trade_chart_context import load_trade_chart_candles
from ...utils.api_response import success_response
from ...utils.timezone import format_kolkata_datetime, iso_utc

router = APIRouter()


def _is_admin(current_user: dict) -> bool:
    return str(current_user.get("role") or "").upper() == "ADMIN"


def _json_safe(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


async def _load_profile(db: AsyncSession, profile_id: UUID, current_user: dict, *, write: bool = False):
    stmt = select(FundedAccountProfile).options(
        selectinload(FundedAccountProfile.phases), selectinload(FundedAccountProfile.risk_tiers)
    ).where(FundedAccountProfile.id == profile_id)
    if write and not _is_admin(current_user):
        stmt = stmt.where(FundedAccountProfile.user_id == current_user["user_id"], FundedAccountProfile.is_template.is_(False))
    elif not _is_admin(current_user):
        stmt = stmt.where(or_(FundedAccountProfile.user_id == current_user["user_id"], FundedAccountProfile.is_template.is_(True)))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Funded account profile not found or not accessible")
    return profile


async def _load_owned_run(db: AsyncSession, run_id: UUID, current_user: dict):
    stmt = select(FundedBacktestRun).where(FundedBacktestRun.id == run_id)
    if not _is_admin(current_user):
        stmt = stmt.where(FundedBacktestRun.user_id == current_user["user_id"])
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Funded backtest run not found or not accessible")
    return row


def _phase_payload(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in {"id", "profile_id", "created_at", "updated_at"}}


def _risk_payload(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in {"id", "profile_id", "created_at", "updated_at"}}


def _profile_payload(profile):
    return {
        "id": str(profile.id), "user_id": str(profile.user_id) if profile.user_id else None,
        "name": profile.name, "provider_name": profile.provider_name, "challenge_type": profile.challenge_type,
        "account_size": profile.account_size, "account_currency": profile.account_currency,
        "is_template": profile.is_template, "is_active": profile.is_active, "description": profile.description,
        "payout_config": profile.payout_config, "rules_json": profile.rules_json,
        "phases": [_phase_payload(p) for p in sorted(profile.phases, key=lambda x: x.sequence)],
        "risk_tiers": [_risk_payload(t) for t in sorted(profile.risk_tiers, key=lambda x: x.sort_order)],
        "created_at": profile.created_at, "updated_at": profile.updated_at,
    }


async def _replace_children(profile, payload, db: AsyncSession | None = None):
    """Replace profile child collections without violating unique constraints.

    SQLAlchemy may schedule INSERTs before DELETEs when a delete-orphan collection is
    cleared and repopulated in the same flush. Because funded phases/risk tiers have
    per-profile unique keys, updates must flush the orphan DELETEs first, then append
    the replacement rows. New profiles do not need the intermediate flush.
    """
    profile.phases.clear()
    profile.risk_tiers.clear()

    if db is not None:
        # Force DELETEs for the existing children to reach PostgreSQL before the
        # replacement INSERTs. This avoids uq_funded_phase_profile_number and
        # uq_funded_risk_tier_order collisions during profile edits.
        await db.flush()

    for phase in payload.phases:
        profile.phases.append(FundedAccountPhase(**phase.model_dump()))
    for tier in payload.risk_tiers:
        profile.risk_tiers.append(FundedRiskTier(**tier.model_dump()))


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_profile(payload: FundedProfileCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.is_template and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins may create shared funded-account templates")
    data = payload.model_dump(exclude={"phases", "risk_tiers"})
    if data.get("payout_config") is not None:
        data["payout_config"] = payload.payout_config.model_dump(mode="json")
    profile = FundedAccountProfile(user_id=None if payload.is_template else current_user["user_id"], **data)
    await _replace_children(profile, payload)
    db.add(profile)
    await db.commit()
    profile = await _load_profile(db, profile.id, current_user)
    return success_response(_profile_payload(profile), "Funded account profile created")


@router.get("/profiles")
async def list_profiles(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(FundedAccountProfile).options(selectinload(FundedAccountProfile.phases), selectinload(FundedAccountProfile.risk_tiers)).where(FundedAccountProfile.is_active.is_(True))
    if not _is_admin(current_user):
        stmt = stmt.where(or_(FundedAccountProfile.user_id == current_user["user_id"], FundedAccountProfile.is_template.is_(True)))
    rows = (await db.execute(stmt.order_by(FundedAccountProfile.is_template.desc(), FundedAccountProfile.created_at.desc()))).scalars().unique().all()
    return success_response([_profile_payload(x) for x in rows])


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return success_response(_profile_payload(await _load_profile(db, profile_id, current_user)))


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: UUID, payload: FundedProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_profile(db, profile_id, current_user, write=True)
    if payload.is_template and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins may create shared funded-account templates")
    for key, value in payload.model_dump(exclude={"phases", "risk_tiers", "payout_config"}).items():
        setattr(profile, key, value)
    profile.payout_config = payload.payout_config.model_dump(mode="json") if payload.payout_config else None
    try:
        await _replace_children(profile, payload, db=db)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Funded profile update conflicts with an existing phase or risk-tier sequence. Refresh the profile and try again.",
        ) from exc
    return success_response(_profile_payload(await _load_profile(db, profile_id, current_user)), "Funded account profile updated")


@router.delete("/profiles/{profile_id}")
async def deactivate_profile(profile_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_profile(db, profile_id, current_user, write=True)
    profile.is_active = False
    await db.commit()
    return success_response({"id": str(profile.id), "is_active": False}, "Funded account profile deactivated")


async def _validate_run_references(db: AsyncSession, payload: FundedRunRequest, current_user: dict):
    profile = await _load_profile(db, payload.profile_id, current_user)
    if not profile.is_active:
        raise HTTPException(status_code=400, detail="Funded account profile is inactive")
    strategy = (await db.execute(select(Strategy).where(Strategy.id == payload.strategy_id))).scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not _is_admin(current_user):
        visibility = str(getattr(strategy, "visibility", "") or "PRIVATE").upper()
        owner = str(getattr(strategy, "created_by", "") or "")
        if visibility != "PUBLIC" and owner != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Strategy is not accessible for funded backtest")
    instrument = (await db.execute(select(Instrument).where(Instrument.id == payload.instrument_id))).scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return profile, strategy, instrument


@router.post("/preview")
async def preview_funded_backtest(payload: FundedRunRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile, strategy, instrument = await _validate_run_references(db, payload, current_user)
    instrument_spec = BacktestService._instrument_to_spec(instrument)
    # Preview validates market-data coverage and quotes the same candle-based
    # credit expense used by Standard Backtest. Preview does not debit credits.
    billing, market_df = await build_funded_credit_quote(db, payload=payload, instrument=instrument, user_id=str(current_user["user_id"]))
    snapshots = build_run_snapshots(profile=profile, phases=profile.phases, risk_tiers=profile.risk_tiers, runtime_config=payload.runtime_config or {}, instrument_spec=instrument_spec)
    warnings = ["Drawdown evaluation uses trade-level fidelity because the reusable strategy result does not include the full intrabar price path for each trade."]
    warnings.extend([str(item) for item in (billing.get("advanced_filters") or {}).get("warnings") or [] if str(item).strip()])
    if not billing.get("has_enough_credits"):
        warnings.append("Insufficient credits for this funded backtest. Reduce the candle scope, upgrade your plan, or top up wallet credits.")
    return success_response({
        "valid": bool(billing.get("billable_candles", 0) > 0),
        "rule_engine_version": FUNDED_RULE_ENGINE_VERSION,
        "profile_id": str(profile.id),
        "strategy_id": strategy.id,
        "instrument_id": instrument.id,
        "account_name": profile.name,
        "challenge_type": profile.challenge_type,
        "initial_capital": profile.account_size,
        "risk_mode": payload.risk_mode,
        "fixed_risk_pct": payload.fixed_risk_pct,
        "safety_buffer_pct": payload.safety_buffer_pct,
        "market_data": {
            "candles": len(market_df),
            "selected_candles": billing.get("billable_candles"),
            "candles_removed": billing.get("candles_removed"),
            "from": str(market_df.iloc[0]["Date"]),
            "to": str(market_df.iloc[-1]["Date"]),
        },
        "snapshot_preview": snapshots,
        "warnings": warnings,
        "credit_policy": billing.get("credit_policy"),
        "billing": billing,
    })


def _run_payload(row):
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    data["id"] = str(row.id)
    return data


def _coalesce_daily_snapshots(days):
    """Return at most one finalized snapshot per funded run trading date.

    The database contract is one row per (funded_backtest_id, trading_date).
    If an older simulator path emits the same finalized day twice (for example
    when a phase becomes terminal at the next day boundary), the latest/final
    representation wins deterministically.
    """
    by_date = {}
    order = []
    for item in days or []:
        key = item.get("trading_date")
        if key not in by_date:
            order.append(key)
        by_date[key] = item
    return [by_date[key] for key in order]


async def _persist_output(db: AsyncSession, run: FundedBacktestRun, output):
    phase_id_by_number: dict[int, UUID] = {}
    for item in output.phases:
        if not item:
            continue
        row = FundedBacktestPhase(
            funded_backtest_id=run.id,
            phase_number=int(item.get("phase_number") or 1),
            phase_name=item.get("phase_name") or f"Phase {item.get('phase_number') or 1}",
            starting_at=item.get("starting_at"), ending_at=item.get("ending_at"),
            starting_balance=item.get("starting_balance") or run.initial_capital,
            ending_balance=item.get("ending_balance"), target_pct=item.get("target_pct"),
            target_amount=item.get("target_amount"), target_reached=bool(item.get("target_reached")),
            maximum_drawdown=item.get("maximum_drawdown"), worst_daily_drawdown=item.get("worst_daily_drawdown"),
            trading_days=int(item.get("trading_days") or 0), qualifying_days=int(item.get("qualifying_days") or 0),
            phase_status=item.get("phase_status") or item.get("status") or "INCOMPLETE",
            passed_at=item.get("passed_at"), failed_at=item.get("failed_at"), failure_reason=item.get("failure_reason"),
        )
        db.add(row)
        await db.flush()
        phase_id_by_number[row.phase_number] = row.id

    for item in output.trades:
        tier_id = item.get("selected_risk_tier_id")
        try:
            tier_id = UUID(str(tier_id)) if tier_id else None
        except Exception:
            tier_id = None
        db.add(FundedBacktestTrade(
            funded_backtest_id=run.id,
            funded_phase_id=phase_id_by_number.get(item.get("phase_number")),
            source_trade_id=item.get("source_trade_id"), trade_number=item["trade_number"],
            entry_time=item["entry_time"], exit_time=item.get("exit_time"), side=item["side"],
            entry_price=item["entry_price"], exit_price=item.get("exit_price"), stop_loss=item.get("stop_loss"), target=item.get("target"), rr_ratio=item.get("rr_ratio"), exit_type=item.get("exit_type"),
            balance_before_trade=item["balance_before_trade"], equity_before_trade=item["equity_before_trade"], account_return_pct_before_trade=item["account_return_pct_before_trade"],
            selected_risk_tier_id=tier_id, selected_risk_tier_name=item.get("selected_risk_tier_name"), requested_risk_pct=item["requested_risk_pct"], effective_risk_pct=item["effective_risk_pct"], requested_risk_amount=item["requested_risk_amount"], actual_risk_amount=item.get("actual_risk_amount"),
            quantity_mode=item.get("quantity_mode"), calculated_lot_size=item.get("calculated_lot_size"), calculated_quantity=item.get("calculated_quantity"), pnl=item.get("pnl"), r_multiple=item.get("r_multiple"),
            balance_after_trade=item.get("balance_after_trade"), equity_after_trade=item.get("equity_after_trade"), daily_pnl_after_trade=item.get("daily_pnl_after_trade"), daily_dd_pct_used=item.get("daily_dd_pct_used"), max_dd_pct_used=item.get("max_dd_pct_used"),
            qualifying_day_state=item.get("qualifying_day_state"), consistency_contribution=item.get("consistency_contribution"), rule_event=item.get("rule_event"), account_state_after_trade=item.get("account_state_after_trade"),
        ))

    positive_total = Decimal("0")
    best_day = Decimal("0")
    for item in _coalesce_daily_snapshots(output.days):
        pnl = Decimal(str(item.get("day_pnl") or 0))
        if pnl > 0:
            positive_total += pnl
            best_day = max(best_day, pnl)
        consistency = Decimal("0") if positive_total <= 0 else best_day / positive_total
        db.add(FundedBacktestDailySnapshot(
            funded_backtest_id=run.id, funded_phase_id=phase_id_by_number.get(item.get("phase_number")), trading_date=item["trading_date"],
            start_balance=item["start_balance"], start_equity=item["start_equity"], end_balance=item["end_balance"], end_equity=item["end_equity"], day_pnl=item["day_pnl"], day_return_pct=item["day_return_pct"], peak_equity=item.get("peak_equity"), low_equity=item.get("low_equity"), daily_drawdown_amount=item.get("daily_drawdown_amount"), daily_drawdown_pct=item.get("daily_drawdown_pct"), trades_count=item.get("trades_count", 0), winning_trades=item.get("winning_trades", 0), losing_trades=item.get("losing_trades", 0), qualifying_day=bool(item.get("qualifying_day")), qualifying_profit_threshold=item.get("qualifying_profit_threshold"), consistency_pct=consistency, state=item.get("state"), failure_reason=item.get("failure_reason"),
        ))

    for item in output.events:
        phase_number = (item.get("metadata_json") or {}).get("phase_number")
        db.add(FundedBacktestEvent(
            funded_backtest_id=run.id, funded_phase_id=phase_id_by_number.get(int(phase_number)) if phase_number else None,
            event_timestamp=item["event_timestamp"], event_type=item["event_type"], event_title=item["event_title"], message=item.get("message"), metadata_json=_json_safe(item.get("metadata_json")),
        ))


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_funded_backtest(
    payload: FundedRunRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, strategy, instrument = await _validate_run_references(db, payload, current_user)
    # Keep the Run request lightweight for multi-year scopes. The Funded Studio
    # already performs an authoritative billing/data Preview before Run. Exact
    # selected-candle billing is repeated inside the background worker before
    # credits are consumed, so direct API callers are still protected without
    # making this HTTP request load 1M+ candles.
    instrument_spec = BacktestService._instrument_to_spec(instrument)
    initial_snapshots = build_run_snapshots(profile=profile, phases=profile.phases, risk_tiers=profile.risk_tiers, runtime_config=payload.runtime_config or {}, instrument_spec=instrument_spec)
    risk_plan = {"mode": payload.risk_mode, "fixed_risk_pct": _json_safe(payload.fixed_risk_pct), "safety_buffer_pct": _json_safe(payload.safety_buffer_pct), "configured_max_risk_pct": _json_safe(payload.configured_max_risk_pct), "tiers": initial_snapshots["risk_plan_snapshot"]}
    run = FundedBacktestRun(
        user_id=current_user["user_id"], profile_id=profile.id, strategy_id=payload.strategy_id, instrument_id=payload.instrument_id,
        timeframe=payload.timeframe, start_date=payload.start_date, end_date=payload.end_date, initial_capital=profile.account_size,
        status="PENDING", current_phase=(profile.phases[0].phase_number if profile.phases else None),
        runtime_config_snapshot=initial_snapshots["runtime_config_snapshot"], instrument_spec_snapshot=initial_snapshots["instrument_spec_snapshot"],
        funded_profile_snapshot=initial_snapshots["funded_profile_snapshot"], risk_plan_snapshot=risk_plan, rule_engine_version=FUNDED_RULE_ENGINE_VERSION,
    )
    db.add(run)
    await db.flush()
    run.status = "RUNNING"
    await db.commit()

    dispatch_mode = "background"
    try:
        from ...celery_app import celery_app, is_celery_available, is_celery_worker_available
        if is_celery_available() and is_celery_worker_available():
            celery_app.send_task(
                "app.tasks.run_funded_backtest_v2_task",
                args=[str(run.id), str(current_user["user_id"]), payload.model_dump(mode="json"), str(current_user.get("role") or "")],
            )
            dispatch_mode = "celery"
        else:
            from ...tasks import run_funded_backtest_v2_fallback
            background_tasks.add_task(
                run_funded_backtest_v2_fallback,
                str(run.id),
                str(current_user["user_id"]),
                payload.model_dump(mode="json"),
                str(current_user.get("role") or ""),
            )
    except Exception:
        from ...tasks import run_funded_backtest_v2_fallback
        background_tasks.add_task(
            run_funded_backtest_v2_fallback,
            str(run.id),
            str(current_user["user_id"]),
            payload.model_dump(mode="json"),
            str(current_user.get("role") or ""),
        )
        dispatch_mode = "background"

    return success_response({
        "funded_backtest_id": str(run.id),
        "status": "RUNNING",
        "current_phase": run.current_phase,
        "final_balance": run.final_balance,
        "final_equity": run.final_equity,
        "trades_processed": 0,
        "execution_mode": dispatch_mode,
        "message": "Funded backtest started in the background. You can leave this page while it continues.",
    }, "Funded backtest queued")


async def _execute_funded_backtest_run(
    db: AsyncSession,
    run_id: UUID,
    payload: FundedRunRequest,
    user_id: str,
    user_role: str = "",
):
    """Execute a previously-created funded run outside the HTTP request."""
    current_user = {"user_id": user_id, "role": user_role}
    profile, strategy, instrument = await _validate_run_references(db, payload, current_user)
    billing, _ = await build_funded_credit_quote(
        db,
        payload=payload,
        instrument=instrument,
        user_id=str(user_id),
    )
    run = await db.get(FundedBacktestRun, run_id)
    if run is None:
        raise RuntimeError(f"Funded backtest run {run_id} no longer exists")
    instrument_spec = BacktestService._instrument_to_spec(instrument)

    consumption: dict[str, Any] | None = None
    try:
        try:
            consumption = await CreditManagementService.consume_credits_for_backtest(
                db=db,
                user_id=str(current_user["user_id"]),
                total_cost=Decimal(str(billing.get("credit_cost") or 0)),
                description=(
                    f"Funded backtest run {run.id}: {getattr(instrument, 'symbol', payload.instrument_id)} {payload.timeframe} "
                    f"{payload.start_date.isoformat()} to {payload.end_date.isoformat()} | "
                    f"billable candles: {billing.get('billable_candles') or 0} | "
                    f"rule: {billing.get('pricing_rule') or 'Credit expense rule'}"
                ),
                job_id=None,
                auto_commit=False,
            )
        except ValueError as exc:
            await db.rollback()
            persisted_run = await db.get(FundedBacktestRun, run.id)
            if persisted_run is not None:
                persisted_run.status = "SIMULATION_ERROR"
                persisted_run.failure_reason = str(exc)
                persisted_run.summary_json = {
                    "status": "SIMULATION_ERROR",
                    "technical_error": str(exc),
                    "billing": _json_safe(billing),
                    "engine_version": FUNDED_RULE_ENGINE_VERSION,
                }
                await db.commit()
            balances = billing.get("balances") or {}
            raise HTTPException(status_code=402, detail={
                "code": "INSUFFICIENT_CREDITS",
                "message": str(exc) or "Insufficient credits for funded backtest.",
                "needed": int(billing.get("credit_cost") or 0),
                "balance": int(balances.get("total_available") or 0),
                "funded_backtest_id": str(run.id),
                "action": {"upgrade_url": "/pricing", "topup_url": "/credits"},
            }) from exc

        source_runtime_capital = Decimal(str((((payload.runtime_config or {}).get("risk") or {}).get("initial_capital") or 100000)))
        source = await BacktestService.run_backtest(
            db=db, strategy_id=payload.strategy_id, instrument_id=payload.instrument_id, timeframe=payload.timeframe,
            start_date=payload.start_date, end_date=payload.end_date, initial_capital=source_runtime_capital,
            advanced_filters=payload.advanced_filters, runtime_config=payload.runtime_config, strategy_preset_id=payload.strategy_preset_id,
            opportunity_mode=True,
        )
        run.runtime_config_snapshot = _json_safe(source.runtime_config or {})
        run.instrument_spec_snapshot = _json_safe(source.instrument_spec or instrument_spec)
        opportunities = [FundedOpportunity.from_source_trade(t, i) for i, t in enumerate(source.result.trades, start=1)]
        snapshot = run.funded_profile_snapshot or {}
        profile_snapshot = snapshot.get("profile") or {}
        payout_rules = dict(profile_snapshot.get("payout_config") or {})
        profile_rules = dict(profile_snapshot.get("rules_json") or {})
        for key in ("daily_drawdown_pct", "daily_drawdown_mode", "max_drawdown_pct", "max_drawdown_mode"):
            if key in profile_rules and key not in payout_rules:
                payout_rules[key] = profile_rules[key]
        output = FundedBacktestSimulator().simulate(
            initial_balance=run.initial_capital,
            challenge_type=profile_snapshot.get("challenge_type") or profile.challenge_type,
            phases=snapshot.get("phases") or [], payout_config=payout_rules,
            risk_tiers=snapshot.get("risk_tiers") or [], instrument_spec=run.instrument_spec_snapshot,
            opportunities=opportunities, risk_mode=payload.risk_mode, fixed_risk_pct=payload.fixed_risk_pct,
            safety_buffer_pct=payload.safety_buffer_pct, configured_max_risk_pct=payload.configured_max_risk_pct,
            rule_timezone=((profile_snapshot.get("rules_json") or {}).get("rule_timezone") or "UTC"),
            historical_end_date=payload.end_date,
        )
        await _persist_output(db, run, output)
        run.status = output.status
        run.final_balance = output.final_balance
        run.final_equity = output.final_equity
        run.current_phase = output.current_phase
        run.passed_at = output.passed_at
        run.failed_at = output.failed_at
        run.failure_reason = output.failure_reason
        run.payout_eligible_at = output.payout_eligible_at
        run.calendar_days = int(output.summary.get("calendar_days") or 0)
        run.trading_days = int(output.summary.get("trading_days") or 0)
        run.qualifying_days = int(output.summary.get("qualifying_days") or 0)
        output.summary["source_strategy_name"] = source.strategy_name
        output.summary["source_instrument_symbol"] = source.instrument_symbol
        output.summary["source_trade_count"] = len(source.result.trades)
        output.summary["source_opportunity_count"] = len(source.result.trades)
        output.summary["source_generation_mode"] = "STRATEGY_OPPORTUNITY_MODE"
        output.summary["source_reference_capital"] = str(source_runtime_capital)
        output.summary["source_rejected_trade_count"] = int(getattr(source.result, "rejected_trade_count", 0) or 0)
        output.summary["executed_funded_trade_count"] = len(output.trades)
        output.summary["skipped_funded_opportunities"] = int(output.summary.get("skipped_unsafe_opportunities") or 0)
        if output.status == "INCOMPLETE":
            output.summary["completion_explanation"] = "Historical range ended before all configured phase requirements were satisfied."
        output.summary["payout_ready_at"] = output.payout_ready_at.isoformat() if output.payout_ready_at else None
        output.summary["strategy_snapshot"] = {"id": str(strategy.id), "name": getattr(strategy, "name", None), "lifecycle_status": getattr(strategy, "lifecycle_status", None), "updated_at": _json_safe(getattr(strategy, "updated_at", None))}
        output.summary["billing"] = {
            **_json_safe(billing),
            "included_credits_used": int((consumption or {}).get("included_debited") or 0),
            "wallet_credits_used": int((consumption or {}).get("wallet_debited") or 0),
        }
        run.summary_json = _json_safe(output.summary)
        await db.commit()
        return success_response({
            "funded_backtest_id": str(run.id),
            "status": run.status,
            "current_phase": run.current_phase,
            "final_balance": run.final_balance,
            "final_equity": run.final_equity,
            "trades_processed": len(output.trades),
            "summary": run.summary_json,
            "credits": {
                "debited": int(billing.get("credit_cost") or 0),
                "included_debited": int((consumption or {}).get("included_debited") or 0),
                "wallet_debited": int((consumption or {}).get("wallet_debited") or 0),
                "balance_after": int((consumption or {}).get("wallet_balance_after") or 0),
                "included_balance_after": int((consumption or {}).get("included_balance_after") or 0),
                "total_balance_after": int((consumption or {}).get("wallet_balance_after") or 0) + int((consumption or {}).get("included_balance_after") or 0),
                "subscription_state": (consumption or {}).get("subscription_state"),
                "deduction_order": ["subscription", "wallet"],
            },
        }, "Funded backtest completed")
    except HTTPException:
        raise
    except (MarketDataNotFoundError, StrategyNotFoundError, BacktestError, ValueError) as exc:
        run_id = run.id
        await db.rollback()
        persisted_run = await db.get(FundedBacktestRun, run_id)
        if persisted_run is not None:
            persisted_run.status = "SIMULATION_ERROR"
            persisted_run.failure_reason = str(exc)
            persisted_run.summary_json = {"status": "SIMULATION_ERROR", "technical_error": str(exc), "engine_version": FUNDED_RULE_ENGINE_VERSION}
            await db.commit()
        raise HTTPException(status_code=400, detail={"code": "FUNDED_SIMULATION_ERROR", "message": str(exc), "funded_backtest_id": str(run_id)}) from exc
    except Exception as exc:
        run_id = run.id
        await db.rollback()
        persisted_run = await db.get(FundedBacktestRun, run_id)
        if persisted_run is not None:
            persisted_run.status = "SIMULATION_ERROR"
            persisted_run.failure_reason = "Unexpected funded simulation error"
            persisted_run.summary_json = {"status": "SIMULATION_ERROR", "technical_error": str(exc), "engine_version": FUNDED_RULE_ENGINE_VERSION}
            await db.commit()
        raise HTTPException(status_code=500, detail={"code": "FUNDED_SIMULATION_ERROR", "message": "Funded simulation failed unexpectedly", "funded_backtest_id": str(run_id)}) from exc


@router.get("/runs")
@router.get("")
async def list_runs(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), status_filter: str | None = Query(None, alias="status"), profile_id: UUID | None = None, strategy_id: str | None = None, instrument_id: int | None = None):
    stmt = select(FundedBacktestRun)
    count_stmt = select(func.count()).select_from(FundedBacktestRun)
    filters = [] if _is_admin(current_user) else [FundedBacktestRun.user_id == current_user["user_id"]]
    if status_filter: filters.append(FundedBacktestRun.status == status_filter.upper())
    if profile_id: filters.append(FundedBacktestRun.profile_id == profile_id)
    if strategy_id: filters.append(FundedBacktestRun.strategy_id == strategy_id)
    if instrument_id: filters.append(FundedBacktestRun.instrument_id == instrument_id)
    for f in filters:
        stmt = stmt.where(f); count_stmt = count_stmt.where(f)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    stats_stmt = select(FundedBacktestRun.status, func.count()).group_by(FundedBacktestRun.status)
    for f in ([] if _is_admin(current_user) else [FundedBacktestRun.user_id == current_user["user_id"]]):
        stats_stmt = stats_stmt.where(f)
    status_counts = {str(name): int(count) for name, count in (await db.execute(stats_stmt)).all()}
    rows = (await db.execute(stmt.order_by(FundedBacktestRun.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()
    items = []
    for x in rows:
        payload = _run_payload(x)
        summary = x.summary_json or {}
        profile_snapshot = ((x.funded_profile_snapshot or {}).get("profile") or {})
        payload.update({
            "account_name": profile_snapshot.get("name"),
            "provider_name": profile_snapshot.get("provider_name"),
            "challenge_type": profile_snapshot.get("challenge_type"),
            "account_currency": profile_snapshot.get("account_currency") or "USD",
            "strategy_name": summary.get("source_strategy_name"),
            "instrument_symbol": summary.get("source_instrument_symbol"),
            "return_pct": summary.get("return_pct"),
            "max_drawdown_pct": summary.get("max_drawdown_pct"),
            "risk_mode": summary.get("risk_mode") or (x.risk_plan_snapshot or {}).get("mode"),
            "estimated_payout_amount": (summary.get("payout") or {}).get("estimated_payout_amount"),
            "engine_version": summary.get("engine_version") or x.rule_engine_version,
        })
        items.append(payload)
    return success_response({"items": items, "page": page, "page_size": page_size, "total": total, "status_counts": status_counts})


async def _run_report(run, db):
    phases = (await db.execute(select(FundedBacktestPhase).where(FundedBacktestPhase.funded_backtest_id == run.id).order_by(FundedBacktestPhase.phase_number))).scalars().all()
    return {**_run_payload(run), "summary": run.summary_json or {}, "phase_summaries": [{c.name: getattr(p, c.name) for c in p.__table__.columns} for p in phases], "account_snapshot": run.funded_profile_snapshot, "runtime_snapshot": run.runtime_config_snapshot, "instrument_snapshot": run.instrument_spec_snapshot, "risk_plan_snapshot": run.risk_plan_snapshot}


@router.get("/runs/{run_id}")
@router.get("/{run_id}")
async def get_run(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _load_owned_run(db, run_id, current_user)
    return success_response(await _run_report(run, db))


@router.get("/runs/{run_id}/status")
@router.get("/{run_id}/status")
async def get_run_status(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _load_owned_run(db, run_id, current_user)
    summary = run.summary_json or {}
    return success_response({"id": str(run.id), "status": run.status, "current_phase": run.current_phase, "trades_processed": summary.get("total_trades", 0), "current_balance": run.final_balance, "current_equity": run.final_equity, "target_progress": (summary.get("progress") or {}).get("target"), "trading_days": run.trading_days, "qualifying_days": run.qualifying_days, "failure_reason": run.failure_reason, "payout": summary.get("payout"), "technical_error": summary.get("technical_error")})


@router.get("/{run_id}/trades")
@router.get("/runs/{run_id}/trades")
async def get_run_trades(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500), phase: int | None = None, side: str | None = None):
    await _load_owned_run(db, run_id, current_user)
    stmt = select(FundedBacktestTrade).where(FundedBacktestTrade.funded_backtest_id == run_id)
    if side: stmt = stmt.where(FundedBacktestTrade.side == side.upper())
    if phase is not None:
        phase_id = (await db.execute(select(FundedBacktestPhase.id).where(FundedBacktestPhase.funded_backtest_id == run_id, FundedBacktestPhase.phase_number == phase))).scalar_one_or_none()
        if phase_id: stmt = stmt.where(FundedBacktestTrade.funded_phase_id == phase_id)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    rows = (await db.execute(stmt.order_by(FundedBacktestTrade.trade_number).offset((page-1)*page_size).limit(page_size))).scalars().all()
    return success_response({"items": [{c.name: getattr(x, c.name) for c in x.__table__.columns} for x in rows], "page": page, "page_size": page_size, "total": total})


@router.get("/{run_id}/trades/{trade_id}/chart-context")
@router.get("/runs/{run_id}/trades/{trade_id}/chart-context")
async def get_funded_trade_chart_context(
    run_id: UUID,
    trade_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return market candles + funded overlays for visual trade verification.

    The funded simulator recalculates position size/PnL but keeps the source
    opportunity entry/exit timestamps and prices. That is enough to render the
    same market candle context without persisting image blobs per trade.
    """
    run = await _load_owned_run(db, run_id, current_user)
    trade = (
        await db.execute(
            select(FundedBacktestTrade).where(
                FundedBacktestTrade.id == trade_id,
                FundedBacktestTrade.funded_backtest_id == run_id,
            )
        )
    ).scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Funded trade not found or not accessible")

    instrument_symbol = (
        await db.execute(select(Instrument.symbol).where(Instrument.id == run.instrument_id))
    ).scalar_one_or_none()

    candles = []
    lookup_meta: dict[str, Any] = {}
    warning = None
    try:
        candles, lookup_meta = await load_trade_chart_candles(
            db,
            instrument_id=run.instrument_id,
            timeframe=run.timeframe,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            candles_before=50,
            candles_after=30,
            allow_legacy_ist_shift_fallback=True,
        )
        warning = lookup_meta.get("warning")
    except Exception:
        warning = "No candle data found for this funded trade context."

    chart_entry_time = iso_utc(trade.entry_time)
    chart_exit_time = iso_utc(trade.exit_time)
    if candles and int(lookup_meta.get("lookup_shift_minutes") or 0) != 0:
        chart_entry_time = lookup_meta.get("lookup_entry_time") or chart_entry_time
        chart_exit_time = lookup_meta.get("lookup_exit_time") or chart_exit_time

    trade_payload = {c.name: getattr(trade, c.name) for c in trade.__table__.columns}
    trade_payload = _json_safe(trade_payload)
    trade_payload["entry_time"] = iso_utc(trade.entry_time)
    trade_payload["exit_time"] = iso_utc(trade.exit_time)

    return success_response(
        {
            "trade": trade_payload,
            "candles": candles,
            "overlays": {
                "side": trade.side,
                "entry_price": _json_safe(trade.entry_price),
                "exit_price": _json_safe(trade.exit_price),
                "stop_loss": _json_safe(trade.stop_loss),
                "target": _json_safe(trade.target),
                "entry_time": chart_entry_time,
                "exit_time": chart_exit_time,
                "exit_reason": trade.exit_type,
                "signal_reason": None,
                "pnl": _json_safe(trade.pnl),
                "r_multiple": _json_safe(trade.r_multiple),
            },
            "meta": {
                "instrument_symbol": instrument_symbol,
                "timeframe": run.timeframe,
                "funded_backtest_id": str(run.id),
                "funded_trade_id": str(trade.id),
                "source_trade_id": trade.source_trade_id,
                "candles_before": 50,
                "candles_after": 30,
                "warning": warning,
                "market_timestamp_storage": lookup_meta.get("market_timestamp_storage"),
                "lookup_shift_minutes": lookup_meta.get("lookup_shift_minutes", 0),
                "lookup_entry_time": lookup_meta.get("lookup_entry_time"),
                "lookup_exit_time": lookup_meta.get("lookup_exit_time"),
                "source": "funded_trade",
            },
        }
    )


@router.get("/{run_id}/days")
@router.get("/runs/{run_id}/days")
async def get_run_days(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _load_owned_run(db, run_id, current_user)
    rows = (await db.execute(select(FundedBacktestDailySnapshot).where(FundedBacktestDailySnapshot.funded_backtest_id == run_id).order_by(FundedBacktestDailySnapshot.trading_date))).scalars().all()
    return success_response([{c.name: getattr(x, c.name) for c in x.__table__.columns} for x in rows])


@router.get("/{run_id}/events")
@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=500)):
    await _load_owned_run(db, run_id, current_user)
    total = int((await db.execute(select(func.count()).select_from(FundedBacktestEvent).where(FundedBacktestEvent.funded_backtest_id == run_id))).scalar_one() or 0)
    rows = (await db.execute(select(FundedBacktestEvent).where(FundedBacktestEvent.funded_backtest_id == run_id).order_by(FundedBacktestEvent.event_timestamp, FundedBacktestEvent.created_at).offset((page-1)*page_size).limit(page_size))).scalars().all()
    return success_response({"items": [{c.name: getattr(x, c.name) for c in x.__table__.columns} for x in rows], "page": page, "page_size": page_size, "total": total})


@router.get("/{run_id}/equity")
@router.get("/runs/{run_id}/equity")
async def get_run_equity(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _load_owned_run(db, run_id, current_user)
    phase_rows = (await db.execute(select(FundedBacktestPhase).where(FundedBacktestPhase.funded_backtest_id == run_id))).scalars().all()
    phase_numbers = {p.id: p.phase_number for p in phase_rows}
    trades = (await db.execute(select(FundedBacktestTrade).where(FundedBacktestTrade.funded_backtest_id == run_id).order_by(FundedBacktestTrade.trade_number))).scalars().all()
    points = []
    if trades:
        first = trades[0]
        points.append({"sequence": 0, "timestamp": first.entry_time, "balance": first.balance_before_trade, "equity": first.equity_before_trade, "daily_dd_pct": None, "max_dd_pct": None, "phase": phase_numbers.get(first.funded_phase_id), "event": "START"})
    for t in trades:
        points.append({"sequence": t.trade_number, "timestamp": t.exit_time or t.entry_time, "balance": t.balance_after_trade, "equity": t.equity_after_trade, "daily_dd_pct": t.daily_dd_pct_used, "max_dd_pct": t.max_dd_pct_used, "phase": phase_numbers.get(t.funded_phase_id), "event": t.rule_event})
    return success_response({"items": points, "mode": "CLOSED_TRADE", "drawdown_evaluation_mode": (run.summary_json or {}).get("drawdown_evaluation_mode", "TRADE_LEVEL")})


async def _all_report_rows(run_id: UUID, db: AsyncSession):
    phases = (await db.execute(select(FundedBacktestPhase).where(FundedBacktestPhase.funded_backtest_id == run_id).order_by(FundedBacktestPhase.phase_number))).scalars().all()
    trades = (await db.execute(select(FundedBacktestTrade).where(FundedBacktestTrade.funded_backtest_id == run_id).order_by(FundedBacktestTrade.trade_number))).scalars().all()
    days = (await db.execute(select(FundedBacktestDailySnapshot).where(FundedBacktestDailySnapshot.funded_backtest_id == run_id).order_by(FundedBacktestDailySnapshot.trading_date))).scalars().all()
    events = (await db.execute(select(FundedBacktestEvent).where(FundedBacktestEvent.funded_backtest_id == run_id).order_by(FundedBacktestEvent.event_timestamp, FundedBacktestEvent.created_at))).scalars().all()
    def rows(items):
        return [{c.name: getattr(x, c.name) for c in x.__table__.columns} for x in items]
    return rows(phases), rows(trades), rows(days), rows(events)


@router.get("/{run_id}/export/trades.csv")
async def export_funded_trades_csv(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _load_owned_run(db, run_id, current_user)
    _, trades, _, _ = await _all_report_rows(run_id, db)
    fields = ["trade_number","funded_phase_id","entry_time","exit_time","side","entry_price","stop_loss","target","exit_price","selected_risk_tier_name","requested_risk_pct","effective_risk_pct","actual_risk_amount","calculated_lot_size","calculated_quantity","pnl","r_multiple","balance_before_trade","balance_after_trade","daily_dd_pct_used","max_dd_pct_used","account_state_after_trade"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    csv_rows = []
    for row in trades:
        safe_row = {k: _json_safe(v) for k, v in row.items()}
        if row.get("entry_time"):
            safe_row["entry_time"] = format_kolkata_datetime(row.get("entry_time"), fallback="", include_timezone=True)
        if row.get("exit_time"):
            safe_row["exit_time"] = format_kolkata_datetime(row.get("exit_time"), fallback="", include_timezone=True)
        csv_rows.append(safe_row)
    writer.writerows(csv_rows)
    content = out.getvalue().encode("utf-8")
    return StreamingResponse(io.BytesIO(content), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="funded-backtest-{run_id}-trades.csv"'})


@router.get("/{run_id}/export/excel")
async def export_funded_excel(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _load_owned_run(db, run_id, current_user)
    report = await _run_report(run, db)
    phases, trades, days, events = await _all_report_rows(run_id, db)
    content = build_funded_excel(_json_safe(report), _json_safe(phases), _json_safe(trades), _json_safe(days), _json_safe(events))
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="funded-backtest-{run_id}.xlsx"'})


@router.get("/{run_id}/export/pdf")
async def export_funded_pdf(run_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _load_owned_run(db, run_id, current_user)
    report = await _run_report(run, db)
    phases, _, days, events = await _all_report_rows(run_id, db)
    content = build_funded_pdf(_json_safe(report), _json_safe(phases), _json_safe(days), _json_safe(events))
    return StreamingResponse(io.BytesIO(content), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="funded-backtest-{run_id}.pdf"'})
