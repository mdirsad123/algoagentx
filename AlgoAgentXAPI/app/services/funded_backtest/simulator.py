from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.trading.pnl_engine import calculate_trade_pnl
from app.services.trading.risk_engine import calculate_position_size

from . import FUNDED_RULE_ENGINE_VERSION
from .consistency import consistency_percentage
from .risk_policy import apply_effective_risk_guard, resolve_dynamic_risk
from .rule_engine import calculate_daily_floor, calculate_max_loss_floor, qualifies_trading_day, qualifying_profit_threshold

D = Decimal
ZERO = D("0")
ONE = D("1")


def _d(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return D(default)
    return D(str(value))


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def _json_num(value: Decimal | None):
    return None if value is None else str(value)


def _safe_div(num: Decimal, den: Decimal) -> Decimal:
    return ZERO if den == 0 else num / den


@dataclass(frozen=True)
class FundedOpportunity:
    source_trade_id: str
    entry_time: datetime
    exit_time: datetime
    side: str
    entry_price: Decimal
    exit_price: Decimal
    stop_loss: Decimal
    target: Decimal | None = None
    rr_ratio: Decimal | None = None
    exit_type: str | None = None

    @classmethod
    def from_source_trade(cls, trade: Any, index: int) -> "FundedOpportunity":
        return cls(
            source_trade_id=str(getattr(trade, "id", None) or getattr(trade, "source_trade_id", None) or index),
            entry_time=_dt(getattr(trade, "entry_datetime", None) or getattr(trade, "entry_time", None)),
            exit_time=_dt(getattr(trade, "exit_datetime", None) or getattr(trade, "exit_time", None)),
            side=str(getattr(trade, "direction", None) or getattr(trade, "side", None) or "").upper(),
            entry_price=_d(getattr(trade, "entry_price", None)),
            exit_price=_d(getattr(trade, "exit_price", None)),
            stop_loss=_d(getattr(trade, "stop_loss", None)),
            target=None if getattr(trade, "target", None) is None else _d(getattr(trade, "target")),
            rr_ratio=None if getattr(trade, "rr_ratio", None) is None else _d(getattr(trade, "rr_ratio")),
            exit_type=str(getattr(trade, "exit_reason", None) or getattr(trade, "exit_type", None) or "SOURCE_EXIT"),
        )


@dataclass
class SimulationOutput:
    status: str
    final_balance: Decimal
    final_equity: Decimal
    current_phase: int | None
    passed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    payout_eligible_at: datetime | None = None
    payout_ready_at: datetime | None = None
    trades: list[dict[str, Any]] = field(default_factory=list)
    days: list[dict[str, Any]] = field(default_factory=list)
    phases: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class FundedBacktestSimulator:
    """Deterministic trade-level funded challenge simulator.

    Source trades provide market outcome only. Position size and PnL are recalculated
    from funded state before every trade. Intrabar equity is not reconstructed because
    the current reusable BacktestResult exposes completed trade outcomes rather than
    the candle path for each trade. The summary therefore records TRADE_LEVEL fidelity.
    """

    version = FUNDED_RULE_ENGINE_VERSION

    def simulate(
        self,
        *,
        initial_balance: Any,
        challenge_type: str,
        phases: Iterable[dict[str, Any]],
        payout_config: dict[str, Any] | None,
        risk_tiers: Iterable[dict[str, Any]],
        instrument_spec: dict[str, Any],
        opportunities: Iterable[FundedOpportunity | Any],
        risk_mode: str = "DYNAMIC",
        fixed_risk_pct: Any | None = None,
        safety_buffer_pct: Any = D("0"),
        configured_max_risk_pct: Any | None = None,
        rule_timezone: str = "UTC",
        historical_end_date: date | None = None,
    ) -> SimulationOutput:
        try:
            rule_tz = ZoneInfo(str(rule_timezone or "UTC"))
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Invalid funded rule timezone: {rule_timezone}") from exc
        initial = _d(initial_balance)
        if initial <= 0:
            raise ValueError("initial_balance must be greater than 0")

        phase_cfgs = sorted([dict(p) for p in phases], key=lambda p: int(p.get("sequence") or p.get("phase_number") or 0))
        tiers = [dict(t) for t in risk_tiers if bool(t.get("is_active", True))]
        payout = dict(payout_config or {})
        challenge = str(challenge_type or "CUSTOM").upper()
        normalized_risk_mode = str(risk_mode or "DYNAMIC").upper()
        if normalized_risk_mode not in {"DYNAMIC", "FIXED"}:
            raise ValueError("risk_mode must be DYNAMIC or FIXED")
        if normalized_risk_mode == "FIXED" and _d(fixed_risk_pct) <= 0:
            raise ValueError("fixed_risk_pct must be greater than 0 in FIXED mode")

        normalized: list[FundedOpportunity] = []
        for i, item in enumerate(opportunities, start=1):
            normalized.append(item if isinstance(item, FundedOpportunity) else FundedOpportunity.from_source_trade(item, i))
        normalized.sort(key=lambda x: (x.entry_time, x.exit_time, x.source_trade_id))

        if challenge != "INSTANT" and not phase_cfgs:
            raise ValueError("Challenge profile has no phases")

        balance = initial
        equity = initial
        high_water_balance = initial
        high_water_equity = initial
        peak_balance = initial
        lowest_balance = initial
        peak_equity = initial
        lowest_equity = initial
        status = "RUNNING"
        failure_reason = None
        failed_at = None
        passed_at = None
        payout_eligible_at = None
        payout_ready_at = None
        payout_eligibility_window_at = None
        current_phase_index = 0
        current_phase_cfg = None if challenge == "INSTANT" else phase_cfgs[0]
        phase_reference = initial
        phase_start_time = normalized[0].entry_time if normalized else None
        phase_state = self._new_phase_state(current_phase_cfg, initial, phase_start_time) if current_phase_cfg else None
        phase_results: list[dict[str, Any]] = []
        trades: list[dict[str, Any]] = []
        days: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        daily_positive_profits: list[Decimal] = []
        current_day = None
        day_state = None
        previous_risk_tier = None
        warning_levels_seen: set[tuple[Any, ...]] = set()
        skipped_unsafe = 0
        risk_reductions = 0
        requested_risks: list[Decimal] = []
        effective_risks: list[Decimal] = []
        actual_risks: list[Decimal] = []
        lots: list[Decimal] = []
        trade_r_values: list[Decimal] = []
        gross_profit = ZERO
        gross_loss = ZERO
        wins = 0
        losses = 0
        max_dd_amount_seen = ZERO
        max_dd_pct_seen = ZERO
        worst_daily_dd_amount = ZERO
        worst_daily_dd_pct = ZERO
        target_reached_at = None
        simulation_start = normalized[0].entry_time if normalized else None
        simulation_end = normalized[-1].exit_time if normalized else None

        self._event(events, simulation_start or datetime.now(timezone.utc), "CHALLENGE_STARTED" if challenge != "INSTANT" else "FUNDED_RUN_STARTED", "Funded simulation started")
        if current_phase_cfg:
            self._event(events, phase_start_time or datetime.now(timezone.utc), "PHASE_STARTED", f"{current_phase_cfg.get('phase_name', 'Phase')} started", phase_number=current_phase_cfg.get("phase_number"))

        for opportunity in normalized:
            if self._terminal(status, challenge, payout):
                break

            trade_date = opportunity.entry_time.astimezone(rule_tz).date()
            if current_day is None or trade_date != current_day:
                if day_state is not None:
                    day_row = self._finalize_day(day_state, current_phase_cfg or payout, phase_reference, status)
                    days.append(day_row)
                    # The previous trading day is now closed. Clear the mutable state
                    # immediately so a terminal phase/pass decision below cannot cause
                    # the same day to be finalized a second time after the loop breaks.
                    day_state = None
                    daily_positive_profits.append(_d(day_row["day_pnl"]) if _d(day_row["day_pnl"]) > 0 else ZERO)
                    if phase_state is not None:
                        self._apply_day_to_phase(phase_state, day_row)
                    if bool(day_row["qualifying_day"]):
                        self._event(events, opportunity.entry_time, "QUALIFYING_DAY_RECORDED", "Qualifying trading day recorded", trading_date=str(day_row["trading_date"]))
                    if challenge == "INSTANT":
                        instant_eval = self._evaluate_payout(initial, balance, payout, days, day_row.get("last_timestamp") or opportunity.entry_time, daily_positive_profits)
                        if instant_eval.get("eligible"):
                            eligible_now = _dt(instant_eval.get("payout_eligible_at")) if instant_eval.get("payout_eligible_at") else (day_row.get("last_timestamp") or opportunity.entry_time)
                            if payout_eligible_at is None:
                                payout_eligible_at = eligible_now
                            if payout_eligibility_window_at is None:
                                payout_eligibility_window_at = eligible_now
                                wait_days = int(payout.get("payout_waiting_calendar_days") or 0)
                                payout_ready_at = payout_eligibility_window_at + timedelta(days=wait_days)
                                self._event(events, eligible_now, "PAYOUT_REQUIREMENTS_MET", "Payout requirements satisfied")
                        else:
                            # Payout requirements (especially consistency) must remain valid
                            # throughout the waiting window. Preserve the first historical
                            # eligibility timestamp for audit, but reset the active window.
                            if payout_eligibility_window_at is not None:
                                self._event(events, day_row.get("last_timestamp") or opportunity.entry_time, "CONSISTENCY_REQUIREMENT_BLOCKED", "Payout waiting window reset because payout requirements are no longer satisfied")
                            payout_eligibility_window_at = None
                            payout_ready_at = None
                        if instant_eval.get("eligible") and payout_ready_at is not None and opportunity.entry_time >= payout_ready_at:
                            status = "PAYOUT_READY"
                            self._event(events, payout_ready_at, "PAYOUT_READY", "Payout requirements remained satisfied through the waiting period")
                            if bool(payout.get("stop_simulation_when_payout_ready")):
                                self._event(events, payout_ready_at, "SIMULATION_STOPPED", "Simulation stopped at payout-ready boundary")
                                break
                    status, passed_now, phase_transition = self._evaluate_after_day(
                        status=status,
                        challenge=challenge,
                        balance=balance,
                        phase_cfg=current_phase_cfg,
                        phase_state=phase_state,
                        phase_reference=phase_reference,
                        phase_cfgs=phase_cfgs,
                        current_phase_index=current_phase_index,
                        payout=payout,
                        days=days,
                        now=opportunity.entry_time,
                        events=events,
                    )
                    if passed_now:
                        target_reached_at = target_reached_at or phase_state.get("target_reached_at") if phase_state else target_reached_at
                    if phase_transition:
                        phase_results.append(self._finalize_phase(phase_state, balance, opportunity.entry_time, "PASSED"))
                        current_phase_index += 1
                        current_phase_cfg = phase_cfgs[current_phase_index]
                        if bool(current_phase_cfg.get("reset_balance_after_pass", False)):
                            balance = initial
                            equity = initial
                        phase_reference = balance if not bool(current_phase_cfg.get("reset_balance_after_pass", False)) else initial
                        high_water_balance = balance
                        high_water_equity = equity
                        phase_state = self._new_phase_state(current_phase_cfg, balance, opportunity.entry_time)
                        previous_risk_tier = None
                        self._event(events, opportunity.entry_time, "PHASE_STARTED", f"{current_phase_cfg.get('phase_name', 'Phase')} started", phase_number=current_phase_cfg.get("phase_number"))
                    if self._terminal(status, challenge, payout):
                        break

                current_day = trade_date
                day_state = self._new_day_state(trade_date, balance, equity)

            active_phase = current_phase_cfg
            phase_initial = phase_reference if active_phase else initial
            daily_floor = self._daily_floor(active_phase, payout, initial, day_state)
            max_floor = self._max_floor(active_phase, payout, initial, high_water_balance, high_water_equity)
            remaining_daily = None if daily_floor is None else max(ZERO, equity - daily_floor)
            remaining_max = None if max_floor is None else max(ZERO, equity - max_floor)

            if normalized_risk_mode == "FIXED":
                requested_pct = _d(fixed_risk_pct)
                account_return = _safe_div(balance - phase_initial, phase_initial)
                tier_id = None
                tier_name = "FIXED"
                risk_reason = "Fixed funded risk mode"
            else:
                risk_decision = resolve_dynamic_risk(phase_initial, balance, tiers)
                requested_pct = risk_decision.requested_risk_percentage
                account_return = risk_decision.account_return_percentage
                tier_id = risk_decision.selected_tier_id
                tier_name = risk_decision.selected_tier_name
                risk_reason = risk_decision.reason

            if tier_name != previous_risk_tier:
                self._event(events, opportunity.entry_time, "RISK_TIER_CHANGED", "Funded risk tier changed", previous_tier=previous_risk_tier, new_tier=tier_name, account_return_pct=_json_num(account_return), balance=_json_num(balance), requested_risk_pct=_json_num(requested_pct))
                previous_risk_tier = tier_name

            guard = apply_effective_risk_guard(
                current_balance=balance,
                requested_risk_percentage=requested_pct,
                remaining_daily_capacity=remaining_daily,
                remaining_max_capacity=remaining_max,
                configured_max_risk=configured_max_risk_pct or requested_pct,
                safety_buffer_percentage=safety_buffer_pct,
            )
            if guard.effective_risk_percentage < requested_pct:
                risk_reductions += 1
                self._event(events, opportunity.entry_time, "EFFECTIVE_RISK_REDUCED", "Effective funded risk reduced by loss-boundary guard", requested_risk_pct=_json_num(requested_pct), effective_risk_pct=_json_num(guard.effective_risk_percentage), limiting_rule=guard.limiting_rule)

            requested_risks.append(requested_pct)
            effective_risks.append(guard.effective_risk_percentage)
            if guard.effective_risk_amount <= 0:
                skipped_unsafe += 1
                self._event(events, opportunity.entry_time, "TRADE_SKIPPED_RISK_LIMIT", "Trade skipped because no funded loss capacity remains", source_trade_id=opportunity.source_trade_id, requested_risk_amount=_json_num(guard.requested_risk_amount), allowed_risk_amount=_json_num(guard.effective_risk_amount))
                continue

            sizing = calculate_position_size(
                entry_price=float(opportunity.entry_price),
                stop_loss=float(opportunity.stop_loss),
                capital=float(balance),
                risk_percent=float(guard.effective_risk_percentage),
                instrument_spec=instrument_spec,
                position_size_mode="RISK_BASED",
                side=opportunity.side,
            )
            if sizing.get("status") == "REJECTED":
                skipped_unsafe += 1
                self._event(events, opportunity.entry_time, "TRADE_SKIPPED_RISK_LIMIT", "Trade skipped because funded position could not be safely sized", source_trade_id=opportunity.source_trade_id, reason=sizing.get("rejected_reason"), requested_risk_amount=_json_num(guard.requested_risk_amount), allowed_risk_amount=_json_num(guard.effective_risk_amount))
                continue

            actual_risk = _d(sizing.get("actual_risk_amount"))
            # Existing risk engine may round a sub-minimum calculation up to broker minimum.
            # Never execute that minimum if it knowingly exceeds the funded safe risk budget.
            if actual_risk <= 0 or actual_risk > guard.effective_risk_amount:
                skipped_unsafe += 1
                self._event(events, opportunity.entry_time, "TRADE_SKIPPED_RISK_LIMIT", "Trade skipped because broker minimum/rounding exceeds funded safe risk", source_trade_id=opportunity.source_trade_id, actual_risk_amount=_json_num(actual_risk), allowed_risk_amount=_json_num(guard.effective_risk_amount), min_lot=instrument_spec.get("min_lot"), min_quantity=instrument_spec.get("min_quantity"))
                continue

            quantity_mode = str(sizing.get("quantity_mode") or instrument_spec.get("quantity_mode") or "SHARES").upper()
            lot_size = None if sizing.get("final_lot_size") is None else _d(sizing.get("final_lot_size"))
            quantity = None if sizing.get("final_quantity") is None else _d(sizing.get("final_quantity"))
            pnl_result = calculate_trade_pnl(
                entry_price=float(opportunity.entry_price),
                exit_price=float(opportunity.exit_price),
                side=opportunity.side,
                quantity_mode=quantity_mode,
                quantity=None if quantity is None else float(quantity),
                lot_size=None if lot_size is None else float(lot_size),
                instrument_spec=instrument_spec,
            )
            if pnl_result.get("status") != "OK":
                self._event(events, opportunity.entry_time, "TRADE_SKIPPED_EXECUTION_INVALID", "Trade skipped because funded PnL could not be calculated", reason=pnl_result.get("rejected_reason"), source_trade_id=opportunity.source_trade_id)
                continue

            pnl = _d(pnl_result.get("pnl"))
            before_balance = balance
            before_equity = equity
            balance += pnl
            equity = balance
            high_water_balance = max(high_water_balance, balance)
            high_water_equity = max(high_water_equity, equity)
            peak_balance = max(peak_balance, balance)
            lowest_balance = min(lowest_balance, balance)
            peak_equity = max(peak_equity, equity)
            lowest_equity = min(lowest_equity, equity)
            actual_risks.append(actual_risk)
            if lot_size is not None:
                lots.append(lot_size)
            r_multiple = _safe_div(pnl, actual_risk)
            trade_r_values.append(r_multiple)
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            elif pnl < 0:
                losses += 1
                gross_loss += abs(pnl)

            day_state["end_balance"] = balance
            day_state["end_equity"] = equity
            day_state["peak_equity"] = max(day_state["peak_equity"], equity)
            day_state["low_equity"] = min(day_state["low_equity"], equity)
            day_state["trades_count"] += 1
            day_state["winning_trades"] += int(pnl > 0)
            day_state["losing_trades"] += int(pnl < 0)
            day_state["day_pnl"] += pnl
            day_state["last_timestamp"] = opportunity.exit_time

            current_daily_floor = self._daily_floor(active_phase, payout, initial, day_state)
            current_max_floor = self._max_floor(active_phase, payout, initial, high_water_balance, high_water_equity)
            daily_dd_amount = max(ZERO, day_state["start_equity"] - equity)
            daily_ref = day_state["start_equity"] if day_state["start_equity"] > 0 else initial
            daily_dd_pct = _safe_div(daily_dd_amount, daily_ref)
            max_dd_amount = max(ZERO, high_water_equity - equity)
            max_dd_pct = _safe_div(max_dd_amount, high_water_equity)
            max_dd_amount_seen = max(max_dd_amount_seen, max_dd_amount)
            max_dd_pct_seen = max(max_dd_pct_seen, max_dd_pct)
            worst_daily_dd_amount = max(worst_daily_dd_amount, daily_dd_amount)
            worst_daily_dd_pct = max(worst_daily_dd_pct, daily_dd_pct)

            hard_status = None
            hard_reason = None
            if current_daily_floor is not None and equity < current_daily_floor:
                hard_status = "FAILED_DAILY_DD"
                hard_reason = f"Daily drawdown breached: equity {equity} fell below daily floor {current_daily_floor}"
            elif current_max_floor is not None and equity < current_max_floor:
                hard_status = "FAILED_MAX_DD"
                hard_reason = f"Maximum drawdown breached: equity {equity} fell below maximum-loss floor {current_max_floor}"

            trade_number = len(trades) + 1
            trade_row = {
                "source_trade_id": opportunity.source_trade_id,
                "trade_number": trade_number,
                "phase_number": active_phase.get("phase_number") if active_phase else None,
                "entry_time": opportunity.entry_time,
                "exit_time": opportunity.exit_time,
                "side": opportunity.side,
                "entry_price": opportunity.entry_price,
                "exit_price": opportunity.exit_price,
                "stop_loss": opportunity.stop_loss,
                "target": opportunity.target,
                "rr_ratio": opportunity.rr_ratio,
                "exit_type": opportunity.exit_type,
                "balance_before_trade": before_balance,
                "equity_before_trade": before_equity,
                "account_return_pct_before_trade": account_return,
                "selected_risk_tier_id": tier_id,
                "selected_risk_tier_name": tier_name,
                "requested_risk_pct": requested_pct,
                "effective_risk_pct": guard.effective_risk_percentage,
                "requested_risk_amount": guard.requested_risk_amount,
                "effective_risk_amount": guard.effective_risk_amount,
                "actual_risk_amount": actual_risk,
                "quantity_mode": quantity_mode,
                "calculated_lot_size": lot_size,
                "calculated_quantity": quantity,
                "pnl": pnl,
                "r_multiple": r_multiple,
                "balance_after_trade": balance,
                "equity_after_trade": equity,
                "daily_pnl_after_trade": day_state["day_pnl"],
                "daily_dd_pct_used": daily_dd_pct,
                "max_dd_pct_used": max_dd_pct,
                "qualifying_day_state": "PENDING_DAY_CLOSE",
                "consistency_contribution": None,
                "rule_event": hard_status,
                "account_state_after_trade": hard_status or status,
                "risk_reason": risk_reason,
            }
            trades.append(trade_row)

            self._emit_warning_events(events, warning_levels_seen, opportunity.exit_time, current_day, active_phase, equity, current_daily_floor, current_max_floor, initial)

            if hard_status:
                status = hard_status
                failure_reason = hard_reason
                failed_at = opportunity.exit_time
                day_state["state"] = status
                day_state["failure_reason"] = hard_reason
                if phase_state is not None:
                    phase_state["status"] = status
                    phase_state["failure_reason"] = hard_reason
                    phase_state["failed_at"] = failed_at
                self._event(events, failed_at, "PHASE_FAILED", "Funded challenge phase failed", reason=hard_reason, trade_number=trade_number, phase_number=active_phase.get("phase_number") if active_phase else None)
                self._event(events, failed_at, "SIMULATION_STOPPED", "Simulation stopped after funded-rule breach", status=status)
                break

            if phase_state is not None:
                target_balance = phase_state.get("target_balance")
                if target_balance is not None and not phase_state["target_reached"] and balance >= target_balance:
                    phase_state["target_reached"] = True
                    phase_state["target_reached_at"] = opportunity.exit_time
                    target_reached_at = target_reached_at or opportunity.exit_time
                    self._event(events, opportunity.exit_time, "PHASE_TARGET_REACHED", "Phase profit target reached", balance=_json_num(balance), target_balance=_json_num(target_balance), phase_number=active_phase.get("phase_number"))

        if day_state is not None:
            day_row = self._finalize_day(day_state, current_phase_cfg or payout, phase_reference, status)
            days.append(day_row)
            daily_positive_profits.append(_d(day_row["day_pnl"]) if _d(day_row["day_pnl"]) > 0 else ZERO)
            if phase_state is not None:
                self._apply_day_to_phase(phase_state, day_row)

        final_time = (trades[-1]["exit_time"] if trades else simulation_end) or datetime.now(timezone.utc)
        range_end_time = datetime.combine(historical_end_date, datetime.max.time(), tzinfo=timezone.utc) if historical_end_date else final_time

        if status == "RUNNING":
            if challenge == "INSTANT":
                payout_eval = self._evaluate_payout(initial, balance, payout, days, final_time, daily_positive_profits)
                if payout_eval.get("eligible"):
                    eligible_now = _dt(payout_eval["payout_eligible_at"]) if payout_eval.get("payout_eligible_at") else final_time
                    if payout_eligible_at is None:
                        payout_eligible_at = eligible_now
                    if payout_eligibility_window_at is None:
                        payout_eligibility_window_at = eligible_now
                    payout_ready_at = payout_eligibility_window_at + timedelta(days=int(payout.get("payout_waiting_calendar_days") or 0))
                    if range_end_time >= payout_ready_at:
                        status = "PAYOUT_READY"
                        self._event(events, payout_ready_at, "PAYOUT_READY", "Payout requirements remained satisfied through the waiting period")
                    else:
                        status = "PAYOUT_ELIGIBLE"
                else:
                    payout_eligibility_window_at = None
                    payout_ready_at = None
                    status = "INCOMPLETE"
            else:
                if phase_state is not None:
                    phase_status = self._phase_pass_ready(phase_state, current_phase_cfg, balance)
                    if phase_status and current_phase_index == len(phase_cfgs) - 1:
                        status = "PASSED"
                        passed_at = final_time
                        phase_results.append(self._finalize_phase(phase_state, balance, final_time, "PASSED"))
                        self._event(events, final_time, "PHASE_PASSED", "Final funded challenge phase passed", phase_number=current_phase_cfg.get("phase_number"))
                    else:
                        status = "INCOMPLETE"
                        phase_results.append(self._finalize_phase(phase_state, balance, final_time, "INCOMPLETE"))
                else:
                    status = "INCOMPLETE"
        elif phase_state is not None:
            phase_results.append(self._finalize_phase(phase_state, balance, final_time, status))

        if challenge != "INSTANT" and status == "RUNNING":
            status = "INCOMPLETE"

        if challenge != "INSTANT" and status == "PASSED" and passed_at is None:
            passed_at = final_time

        payout_eval = self._evaluate_payout(initial, balance, payout, days, final_time, daily_positive_profits) if payout else self._empty_payout()
        payout_eligible_at = payout_eligible_at or (_dt(payout_eval.get("payout_eligible_at")) if payout_eval.get("payout_eligible_at") else None)
        payout_ready_at = payout_ready_at or (_dt(payout_eval.get("payout_ready_at")) if payout_eval.get("payout_ready_at") else None)

        total_trades = len(trades)
        net_pnl = balance - initial
        total_days = len({d["trading_date"] for d in days if int(d.get("trades_count") or 0) > 0})
        qualifying_days = sum(1 for d in days if bool(d.get("qualifying_day")))
        calendar_days = 0
        if simulation_start and final_time:
            calendar_days = (final_time.date() - simulation_start.date()).days + 1
        avg_req = sum(requested_risks, ZERO) / len(requested_risks) if requested_risks else ZERO
        avg_eff = sum(effective_risks, ZERO) / len(effective_risks) if effective_risks else ZERO
        avg_r = sum(trade_r_values, ZERO) / len(trade_r_values) if trade_r_values else ZERO
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
        risk_distribution: dict[str, int] = {}
        for t in trades:
            key = str(t.get("selected_risk_tier_name") or "UNSPECIFIED")
            risk_distribution[key] = risk_distribution.get(key, 0) + 1
        unmet = self._unmet_requirements(challenge, current_phase_cfg, phase_state, payout_eval, initial, balance, days)
        incomplete_reason = None
        if status == "INCOMPLETE":
            active_max_floor = self._max_floor(current_phase_cfg, payout, initial, high_water_balance, high_water_equity)
            remaining_max_capacity = None if active_max_floor is None else max(ZERO, equity - active_max_floor)
            if skipped_unsafe > 0 and remaining_max_capacity is not None:
                incomplete_reason = "RISK_CAPACITY_EXHAUSTED"
                unmet["remaining_max_loss_capacity"] = _json_num(remaining_max_capacity)
                unmet["unsafe_opportunities_skipped"] = skipped_unsafe
            elif total_trades == 0:
                incomplete_reason = "NO_TRADES"
            else:
                incomplete_reason = "REQUIREMENTS_NOT_MET_BEFORE_RANGE_END"

        summary = {
            "status": status,
            "initial_balance": _json_num(initial),
            "final_balance": _json_num(balance),
            "net_pnl": _json_num(net_pnl),
            "return_pct": _json_num(_safe_div(net_pnl, initial)),
            "peak_balance": _json_num(peak_balance),
            "lowest_balance": _json_num(lowest_balance),
            "peak_equity": _json_num(peak_equity),
            "lowest_equity": _json_num(lowest_equity),
            "max_drawdown_amount": _json_num(max_dd_amount_seen),
            "max_drawdown_pct": _json_num(max_dd_pct_seen),
            "worst_daily_drawdown_amount": _json_num(worst_daily_dd_amount),
            "worst_daily_drawdown_pct": _json_num(worst_daily_dd_pct),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": _json_num(D(wins) / D(total_trades) if total_trades else ZERO),
            "average_r": _json_num(avg_r),
            "profit_factor": _json_num(profit_factor),
            "trading_days": total_days,
            "qualifying_days": qualifying_days,
            "calendar_days": calendar_days,
            "risk_mode": normalized_risk_mode,
            "fixed_risk_pct": _json_num(_d(fixed_risk_pct)) if normalized_risk_mode == "FIXED" else None,
            "average_requested_risk_pct": _json_num(avg_req),
            "average_effective_risk_pct": _json_num(avg_eff),
            "minimum_requested_risk_pct": _json_num(min(requested_risks)) if requested_risks else None,
            "maximum_requested_risk_pct": _json_num(max(requested_risks)) if requested_risks else None,
            "minimum_actual_risk_amount": _json_num(min(actual_risks)) if actual_risks else None,
            "maximum_actual_risk_amount": _json_num(max(actual_risks)) if actual_risks else None,
            "average_lot": _json_num(sum(lots, ZERO) / len(lots)) if lots else None,
            "risk_reductions_count": risk_reductions,
            "skipped_unsafe_opportunities": skipped_unsafe,
            "risk_tier_distribution": risk_distribution,
            "drawdown_evaluation_mode": "TRADE_LEVEL",
            "drawdown_fidelity_note": "Funded DD is evaluated at funded trade closes using source strategy trade outcomes; intrabar candle path is not exposed by the reusable BacktestResult.",
            "engine_version": self.version,
            "rule_timezone": str(rule_timezone or "UTC"),
            "breach_operator": "<",
            "overlapping_position_policy": "SOURCE_ENGINE_SINGLE_POSITION",
            "target_reached_at": target_reached_at.isoformat() if target_reached_at else None,
            "payout": payout_eval,
            "first_payout_eligible_at": payout_eligible_at.isoformat() if payout_eligible_at else None,
            "active_payout_waiting_since": payout_eligibility_window_at.isoformat() if payout_eligibility_window_at else None,
            "unmet_requirements": unmet,
            "progress": self._progress(challenge, current_phase_cfg, phase_state, payout, initial, balance, days, payout_eval),
            "zero_trade_reason": "NO_TRADES" if total_trades == 0 else None,
            "incomplete_reason": incomplete_reason,
        }
        self._event(events, final_time, "SIMULATION_COMPLETED", "Funded simulation completed", status=status)
        return SimulationOutput(
            status=status,
            final_balance=balance,
            final_equity=equity,
            current_phase=current_phase_cfg.get("phase_number") if current_phase_cfg else None,
            passed_at=passed_at,
            failed_at=failed_at,
            failure_reason=failure_reason,
            payout_eligible_at=payout_eligible_at,
            payout_ready_at=payout_ready_at,
            trades=trades,
            days=days,
            phases=phase_results,
            events=events,
            summary=summary,
        )

    @staticmethod
    def _new_phase_state(cfg, balance, start_time):
        if cfg is None:
            return None
        target_pct = None if cfg.get("profit_target_pct") is None else _d(cfg.get("profit_target_pct"))
        target_amount = None if target_pct is None else balance * target_pct
        return {
            "phase_number": int(cfg.get("phase_number") or 1),
            "phase_name": cfg.get("phase_name") or f"Phase {cfg.get('phase_number') or 1}",
            "starting_at": start_time,
            "starting_balance": balance,
            "target_pct": target_pct,
            "target_amount": target_amount,
            "target_balance": None if target_amount is None else balance + target_amount,
            "target_reached": not bool(cfg.get("profit_target_required", True)),
            "target_reached_at": None,
            "trading_days": 0,
            "qualifying_days": 0,
            "maximum_drawdown": ZERO,
            "worst_daily_drawdown": ZERO,
            "status": "RUNNING",
            "failed_at": None,
            "failure_reason": None,
        }

    @staticmethod
    def _new_day_state(trading_date, balance, equity):
        return {"trading_date": trading_date, "start_balance": balance, "start_equity": equity, "end_balance": balance, "end_equity": equity, "day_pnl": ZERO, "peak_equity": equity, "low_equity": equity, "trades_count": 0, "winning_trades": 0, "losing_trades": 0, "state": "RUNNING", "failure_reason": None}

    def _finalize_day(self, state, phase_cfg, reference_balance, run_status):
        day_pnl = state["end_balance"] - state["start_balance"]
        day_return = _safe_div(day_pnl, state["start_balance"])
        dd_amount = max(ZERO, state["peak_equity"] - state["low_equity"])
        dd_pct = _safe_div(dd_amount, state["peak_equity"])
        if phase_cfg:
            if phase_cfg.get("qualifying_day_minimum_profit_pct") is not None:
                mode = "MIN_PROFIT_DAY"
                min_pct = phase_cfg.get("qualifying_day_minimum_profit_pct")
            else:
                mode = phase_cfg.get("qualifying_day_mode") or "ANY_TRADE_DAY"
                min_pct = phase_cfg.get("minimum_qualifying_day_profit_pct")
            qualifies = qualifies_trading_day(day_closed_profit=day_pnl, trades_count=state["trades_count"], account_size=reference_balance, mode=mode, minimum_profit_pct=min_pct)
            threshold = qualifying_profit_threshold(reference_balance, min_pct) if str(mode).upper() == "MIN_PROFIT_DAY" and min_pct is not None else ZERO
        else:
            qualifies = False
            threshold = ZERO
        return {**state, "phase_number": phase_cfg.get("phase_number") if phase_cfg else None, "day_pnl": day_pnl, "day_return_pct": day_return, "daily_drawdown_amount": dd_amount, "daily_drawdown_pct": dd_pct, "qualifying_day": qualifies, "qualifying_profit_threshold": threshold, "consistency_pct": None, "state": state.get("state") if state.get("state") != "RUNNING" else run_status}

    @staticmethod
    def _apply_day_to_phase(phase_state, day_row):
        if int(day_row.get("trades_count") or 0) > 0:
            phase_state["trading_days"] += 1
        if bool(day_row.get("qualifying_day")):
            phase_state["qualifying_days"] += 1
        phase_state["worst_daily_drawdown"] = max(phase_state["worst_daily_drawdown"], _d(day_row.get("daily_drawdown_amount")))

    @staticmethod
    def _phase_pass_ready(state, cfg, current_balance) -> bool:
        if state is None or cfg is None:
            return False
        # `target_reached` is an audit flag meaning the target was touched at least once.
        # Passing is stricter: when a profit target is required, the account must still
        # be at/above the configured target balance when all other phase requirements
        # become satisfied. This prevents a phase from passing after touching the target
        # early and then giving the profit back while waiting for minimum days.
        if bool(cfg.get("profit_target_required", True)):
            target_balance = state.get("target_balance")
            target_ok = target_balance is not None and _d(current_balance) >= _d(target_balance)
        else:
            target_ok = True
        min_days = int(cfg.get("minimum_trading_days") or 0)
        # Foundation has one minimum day field; qualifying days are authoritative when MIN_PROFIT_DAY is selected.
        mode = str(cfg.get("qualifying_day_mode") or "ANY_TRADE_DAY").upper()
        day_count = state["qualifying_days"] if mode == "MIN_PROFIT_DAY" else state["trading_days"]
        return bool(target_ok and day_count >= min_days)

    def _evaluate_after_day(self, *, status, challenge, balance, phase_cfg, phase_state, phase_reference, phase_cfgs, current_phase_index, payout, days, now, events):
        if status != "RUNNING" or challenge == "INSTANT" or phase_state is None:
            return status, False, False
        if not phase_state["target_reached"] and phase_state.get("target_balance") is not None and balance >= phase_state["target_balance"]:
            phase_state["target_reached"] = True
            phase_state["target_reached_at"] = now
            self._event(events, now, "PHASE_TARGET_REACHED", "Phase profit target reached", balance=_json_num(balance), target_balance=_json_num(phase_state["target_balance"]), phase_number=phase_cfg.get("phase_number"))
        if not self._phase_pass_ready(phase_state, phase_cfg, balance):
            return status, False, False
        phase_state["status"] = "PASSED"
        self._event(events, now, "PHASE_PASSED", "Funded challenge phase passed", phase_number=phase_cfg.get("phase_number"), trading_days=phase_state["trading_days"], qualifying_days=phase_state["qualifying_days"])
        if current_phase_index < len(phase_cfgs) - 1:
            return "RUNNING", True, True
        return "PASSED", True, False

    @staticmethod
    def _finalize_phase(state, ending_balance, ending_at, phase_status):
        if state is None:
            return {}
        return {**state, "ending_at": ending_at, "ending_balance": ending_balance, "phase_status": phase_status, "passed_at": ending_at if phase_status == "PASSED" else None, "failed_at": state.get("failed_at"), "failure_reason": state.get("failure_reason")}

    @staticmethod
    def _daily_floor(phase, payout, initial, day_state):
        cfg = phase or payout
        pct = cfg.get("daily_drawdown_pct") if cfg else None
        mode = cfg.get("daily_drawdown_mode") if cfg else None
        if pct is None or mode is None:
            return None
        return calculate_daily_floor(mode, initial_balance=initial, start_balance=day_state["start_balance"], start_equity=day_state["start_equity"], drawdown_pct=pct)

    @staticmethod
    def _max_floor(phase, payout, initial, high_water_balance, high_water_equity):
        cfg = phase or payout
        pct = cfg.get("max_drawdown_pct") if cfg else None
        mode = cfg.get("max_drawdown_mode") if cfg else None
        if pct is None or mode is None:
            return None
        return calculate_max_loss_floor(mode, initial_balance=initial, high_water_balance=high_water_balance, high_water_equity=high_water_equity, drawdown_pct=pct)

    def _evaluate_payout(self, initial, balance, payout, days, now, positive_profits):
        if not payout:
            return self._empty_payout()
        profit = max(ZERO, balance - initial)
        pct_target = payout.get("profit_target_pct")
        amount_target = payout.get("profit_target_amount")
        target_amount = _d(amount_target) if amount_target is not None else (initial * _d(pct_target) if pct_target is not None else ZERO)
        min_payout = _d(payout.get("minimum_payout_amount"))
        required_trading = int(payout.get("minimum_trading_days") or 0)
        required_qualifying = int(payout.get("minimum_qualifying_profitable_days") or 0)
        qualifying_min_pct = payout.get("qualifying_day_minimum_profit_pct")
        threshold = initial * _d(qualifying_min_pct) if qualifying_min_pct is not None else ZERO
        trading_days = sum(1 for d in days if int(d.get("trades_count") or 0) > 0)
        qualifying_days = sum(1 for d in days if int(d.get("trades_count") or 0) > 0 and _d(d.get("day_pnl")) >= threshold)
        profitable = [_d(d.get("day_pnl")) for d in days if _d(d.get("day_pnl")) > 0]
        total_positive = sum(profitable, ZERO)
        best = max(profitable) if profitable else ZERO
        consistency = consistency_percentage(best, total_positive)
        consistency_enabled = bool(payout.get("consistency_rule_enabled", False))
        consistency_max = payout.get("consistency_maximum_pct")
        consistency_ok = not consistency_enabled or (consistency_max is not None and consistency <= _d(consistency_max))
        target_ok = profit >= target_amount
        minimum_payout_ok = profit >= min_payout
        eligible = target_ok and minimum_payout_ok and trading_days >= required_trading and qualifying_days >= required_qualifying and consistency_ok
        eligible_at = now if eligible else None
        waiting_days = int(payout.get("payout_waiting_calendar_days") or 0)
        ready_at = eligible_at + timedelta(days=waiting_days) if eligible_at else None
        payout_ready = bool(eligible and waiting_days == 0)
        split = _d(payout.get("payout_profit_split_pct"), "1") if payout.get("payout_profit_split_pct") is not None else ONE
        return {"eligible": eligible, "payout_ready": payout_ready, "profit_target_amount": _json_num(target_amount), "profit_target_achieved": target_ok, "gross_eligible_profit": _json_num(profit), "minimum_payout_amount": _json_num(min_payout), "trading_days_completed": trading_days, "trading_days_required": required_trading, "qualifying_days_completed": qualifying_days, "qualifying_days_required": required_qualifying, "qualifying_profit_threshold": _json_num(threshold), "best_profitable_day": _json_num(best), "total_positive_profit": _json_num(total_positive), "consistency_pct": _json_num(consistency), "consistency_maximum_pct": None if consistency_max is None else str(consistency_max), "consistency_satisfied": consistency_ok, "payout_waiting_calendar_days": waiting_days, "payout_eligible_at": eligible_at.isoformat() if eligible_at else None, "payout_ready_at": ready_at.isoformat() if ready_at else None, "profit_split_pct": _json_num(split), "estimated_payout_amount": _json_num(profit * split)}

    @staticmethod
    def _empty_payout():
        return {"eligible": False, "payout_ready": False, "payout_eligible_at": None, "payout_ready_at": None}

    @staticmethod
    def _terminal(status, challenge, payout):
        if status in {"FAILED_DAILY_DD", "FAILED_MAX_DD", "FAILED_OTHER_RULE", "PASSED", "SIMULATION_ERROR"}:
            return True
        return status == "PAYOUT_READY" and bool((payout or {}).get("stop_simulation_when_payout_ready"))

    @staticmethod
    def _event(events, timestamp, event_type, title, **metadata):
        events.append({"event_timestamp": _dt(timestamp), "event_type": event_type, "event_title": title, "message": title, "metadata_json": metadata or None})

    def _emit_warning_events(self, events, seen, timestamp, trading_date, phase, equity, daily_floor, max_floor, initial):
        for rule_name, floor in (("DAILY_DD", daily_floor), ("MAX_DD", max_floor)):
            if floor is None:
                continue
            reference = initial if rule_name == "MAX_DD" else max(initial, equity)
            total_capacity = max(ZERO, reference - floor)
            used = max(ZERO, reference - equity)
            ratio = _safe_div(used, total_capacity) if total_capacity > 0 else ZERO
            for level in (D("0.50"), D("0.75"), D("0.90")):
                key = (trading_date if rule_name == "DAILY_DD" else "RUN", rule_name, level)
                if ratio >= level and key not in seen:
                    seen.add(key)
                    self._event(events, timestamp, f"{rule_name}_WARNING", f"{rule_name} warning threshold crossed", threshold_pct=str(level), consumed_pct=_json_num(ratio), floor=_json_num(floor), equity=_json_num(equity))

    @staticmethod
    def _unmet_requirements(challenge, phase_cfg, phase_state, payout_eval, initial, balance, days):
        if challenge == "INSTANT":
            return {"payout_eligible": bool(payout_eval.get("eligible")), "trading_days_completed": payout_eval.get("trading_days_completed", 0), "trading_days_required": payout_eval.get("trading_days_required", 0), "qualifying_days_completed": payout_eval.get("qualifying_days_completed", 0), "qualifying_days_required": payout_eval.get("qualifying_days_required", 0), "consistency_current": payout_eval.get("consistency_pct"), "consistency_required_max": payout_eval.get("consistency_maximum_pct")}
        if not phase_cfg or not phase_state:
            return {}
        target_balance = phase_state.get("target_balance")
        target_remaining = max(ZERO, target_balance - balance) if target_balance is not None else ZERO
        min_days = int(phase_cfg.get("minimum_trading_days") or 0)
        mode = str(phase_cfg.get("qualifying_day_mode") or "ANY_TRADE_DAY").upper()
        completed = phase_state["qualifying_days"] if mode == "MIN_PROFIT_DAY" else phase_state["trading_days"]
        return {"target_remaining": _json_num(target_remaining), "target_reached": bool(target_balance is None or balance >= target_balance), "target_ever_reached": phase_state.get("target_reached", False), "trading_days_completed": phase_state["trading_days"], "trading_days_required": min_days if mode == "ANY_TRADE_DAY" else 0, "qualifying_days_completed": phase_state["qualifying_days"], "qualifying_days_required": min_days if mode == "MIN_PROFIT_DAY" else 0}

    @staticmethod
    def _progress(challenge, phase_cfg, phase_state, payout, initial, balance, days, payout_eval):
        if challenge == "INSTANT":
            req_q = max(1, int(payout_eval.get("qualifying_days_required") or 0))
            return {"payout_profit_target": 1.0 if payout_eval.get("profit_target_achieved") else float(min(ONE, _safe_div(max(ZERO, balance - initial), _d(payout_eval.get("profit_target_amount"), "1")))) if _d(payout_eval.get("profit_target_amount"), "0") > 0 else 1.0, "qualifying_days": min(1.0, float(D(int(payout_eval.get("qualifying_days_completed") or 0)) / D(req_q))) if int(payout_eval.get("qualifying_days_required") or 0) > 0 else 1.0, "consistency_satisfied": bool(payout_eval.get("consistency_satisfied", True))}
        if not phase_cfg or not phase_state:
            return {}
        target = phase_state.get("target_amount") or ZERO
        profit = max(ZERO, balance - phase_state["starting_balance"])
        min_days = int(phase_cfg.get("minimum_trading_days") or 0)
        completed = phase_state["qualifying_days"] if str(phase_cfg.get("qualifying_day_mode") or "ANY_TRADE_DAY").upper() == "MIN_PROFIT_DAY" else phase_state["trading_days"]
        return {"target": 1.0 if target == 0 else min(1.0, float(profit / target)), "minimum_days": 1.0 if min_days == 0 else min(1.0, completed / min_days)}


def size_funded_position(*, entry_price, stop_loss, current_balance, effective_risk_percentage, instrument_spec, position_size_mode="RISK_BASED", **kwargs):
    """Compatibility adapter that delegates to AlgoAgentX's existing risk engine."""
    return calculate_position_size(entry_price=entry_price, stop_loss=stop_loss, capital=current_balance, risk_percent=effective_risk_percentage, instrument_spec=instrument_spec, position_size_mode=position_size_mode, **kwargs)
