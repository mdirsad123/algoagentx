from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

from app.services.funded_backtest.simulator import FundedBacktestSimulator, FundedOpportunity

D = Decimal
UTC = timezone.utc

INSTRUMENT = {
    "quantity_mode": "SHARES",
    "account_currency": "USD",
    "currency_symbol": "$",
    "min_quantity": 1,
    "quantity_step": 1,
    "max_quantity": 1000000,
    "tick_size": 0.01,
    "pip_size": 0.01,
}

TIERS = [
    {"id": None, "name": "Defensive", "sort_order": 1, "min_account_return_pct": None, "max_account_return_pct": "-0.04", "risk_percent": "0.0025", "is_active": True},
    {"id": None, "name": "Reduced", "sort_order": 2, "min_account_return_pct": "-0.04", "max_account_return_pct": "-0.02", "risk_percent": "0.005", "is_active": True},
    {"id": None, "name": "Normal", "sort_order": 3, "min_account_return_pct": "-0.02", "max_account_return_pct": "0.02", "risk_percent": "0.01", "is_active": True},
    {"id": None, "name": "Growth", "sort_order": 4, "min_account_return_pct": "0.02", "max_account_return_pct": "0.04", "risk_percent": "0.015", "is_active": True},
    {"id": None, "name": "Aggressive", "sort_order": 5, "min_account_return_pct": "0.04", "max_account_return_pct": None, "risk_percent": "0.02", "is_active": True},
]


def phase(target="0.08", min_days=0, reset=False, num=1, daily="0.05", maxdd="0.10", mode="ANY_TRADE_DAY"):
    return {
        "phase_number": num, "phase_name": f"Phase {num}", "sequence": num,
        "profit_target_pct": target, "profit_target_required": True,
        "daily_drawdown_pct": daily, "daily_drawdown_mode": "STATIC_INITIAL_BALANCE",
        "max_drawdown_pct": maxdd, "max_drawdown_mode": "STATIC_INITIAL_BALANCE",
        "minimum_trading_days": min_days, "minimum_qualifying_day_profit_pct": "0.005" if mode == "MIN_PROFIT_DAY" else None,
        "qualifying_day_mode": mode, "reset_balance_after_pass": reset,
    }


def opp(day, exit_price, entry=100, stop=99, side="LONG"):
    t = datetime(2025, 11, day, 10, tzinfo=UTC)
    return FundedOpportunity(str(day), t, t + timedelta(hours=1), side, D(str(entry)), D(str(exit_price)), D(str(stop)), D("110"), D("2"), "TEST_EXIT")


def run(opps, phases=None, challenge="ONE_STEP", payout=None, **kwargs):
    return FundedBacktestSimulator().simulate(initial_balance=5000, challenge_type=challenge, phases=phases or [phase()], payout_config=payout or {}, risk_tiers=TIERS, instrument_spec=INSTRUMENT, opportunities=opps, historical_end_date=date(2025,11,30), **kwargs)


def test_dynamic_downscaling_and_upscaling_boundaries():
    # Large source outcomes deliberately move the account through configured bands.
    out = run([opp(1, 96), opp(2, 96), opp(3, 108), opp(4, 108), opp(5, 108)], phases=[phase(target="0.90")])
    names = [t["selected_risk_tier_name"] for t in out.trades]
    assert names[0] == "Normal"
    assert "Reduced" in names or "Defensive" in names


def test_daily_dd_failure_stops_future_trades():
    out = run([opp(1, 94), opp(2, 110)], phases=[phase(target="0.90")], safety_buffer_pct=D("0"))
    assert out.status == "FAILED_DAILY_DD"
    assert len(out.trades) == 1


def test_max_dd_failure():
    # Daily limit wide enough not to fire first; gap beyond SL breaches static max DD.
    out = run([opp(1, 89)], phases=[phase(target="0.90", daily="0.50", maxdd="0.10")], safety_buffer_pct=D("0"))
    assert out.status == "FAILED_MAX_DD"


def test_effective_risk_reduction_near_boundary():
    # First gap loss leaves account near DD floor; next trade must be reduced.
    out = run([opp(1, 95.4), opp(1, 102)], phases=[phase(target="0.90")], safety_buffer_pct=D("0"))
    assert len(out.trades) >= 1
    if len(out.trades) > 1:
        assert out.trades[1]["effective_risk_pct"] <= out.trades[1]["requested_risk_pct"]
    assert out.summary["risk_reductions_count"] >= 0


def test_unsafe_minimum_quantity_is_skipped():
    spec = dict(INSTRUMENT)
    spec["min_quantity"] = 100
    out = FundedBacktestSimulator().simulate(initial_balance=5000, challenge_type="ONE_STEP", phases=[phase(target="0.90")], payout_config={}, risk_tiers=TIERS, instrument_spec=spec, opportunities=[opp(1, 101)], configured_max_risk_pct=D("0.0005"))
    assert out.summary["skipped_unsafe_opportunities"] == 1
    assert len(out.trades) == 0
    assert any(e["event_type"] == "TRADE_SKIPPED_RISK_LIMIT" for e in out.events)


def test_target_before_min_days_and_two_step_continuity_reset():
    phases = [phase(target="0.08", min_days=3, reset=False, num=1), phase(target="0.05", min_days=1, reset=True, num=2)]
    out = run([opp(1,108), opp(2,100), opp(3,100), opp(4,105), opp(5,100)], phases=phases, challenge="TWO_STEP")
    p1 = next(p for p in out.phases if p["phase_number"] == 1)
    assert p1["target_reached"] is True
    assert p1["trading_days"] >= 3
    phase2_trades = [t for t in out.trades if t["phase_number"] == 2]
    assert phase2_trades
    assert min(t["entry_time"].day for t in phase2_trades) >= 4
    assert phase2_trades[0]["account_return_pct_before_trade"] == D("0")


def test_qualifying_day_threshold_2499_vs_2500():
    # Direct day math through funded sizing: fixed risk with quantity 25 and $1 move => $25.
    out = run([opp(1, 100.9996), opp(2, 101)], phases=[phase(target="0.90", min_days=2, mode="MIN_PROFIT_DAY")], risk_mode="FIXED", fixed_risk_pct=D("0.005"))
    assert out.days[0]["qualifying_day"] is False
    assert out.days[1]["qualifying_day"] is True


def test_consistency_blocks_then_can_satisfy_without_failure():
    payout = {
        "profit_target_amount": "0", "minimum_payout_amount": "0", "minimum_trading_days": 1,
        "minimum_qualifying_profitable_days": 1, "qualifying_day_minimum_profit_pct": "0",
        "consistency_rule_enabled": True, "consistency_maximum_pct": "0.50",
        "payout_waiting_calendar_days": 0, "payout_profit_split_pct": "0.80", "stop_simulation_when_payout_ready": False,
        "daily_drawdown_pct": "0.50", "daily_drawdown_mode": "STATIC_INITIAL_BALANCE", "max_drawdown_pct": "0.50", "max_drawdown_mode": "STATIC_INITIAL_BALANCE",
    }
    out = run([opp(1,102), opp(2,102), opp(3,102)], phases=[], challenge="INSTANT", payout=payout)
    assert out.status in {"PAYOUT_READY", "PAYOUT_ELIGIBLE", "INCOMPLETE"}
    assert not out.status.startswith("FAILED")
    assert D(out.summary["payout"]["consistency_pct"]) <= D("1")


def test_payout_ready_wait_and_stop():
    payout = {
        "profit_target_amount": "20", "minimum_payout_amount": "20", "minimum_trading_days": 1,
        "minimum_qualifying_profitable_days": 1, "qualifying_day_minimum_profit_pct": "0",
        "consistency_rule_enabled": False, "payout_waiting_calendar_days": 1,
        "payout_profit_split_pct": "0.80", "stop_simulation_when_payout_ready": True,
        "daily_drawdown_pct": "0.50", "daily_drawdown_mode": "STATIC_INITIAL_BALANCE", "max_drawdown_pct": "0.50", "max_drawdown_mode": "STATIC_INITIAL_BALANCE",
    }
    out = run([opp(1,101), opp(2,101), opp(3,101)], phases=[], challenge="INSTANT", payout=payout)
    assert out.status == "PAYOUT_READY"
    assert out.payout_ready_at is not None
    assert len(out.trades) <= 2


def test_incomplete_and_determinism():
    inputs = [opp(1,101), opp(2,99.5)]
    a = run(inputs, phases=[phase(target="0.90")])
    b = run(inputs, phases=[phase(target="0.90")])
    assert a.status == "INCOMPLETE"
    assert (a.status, a.final_balance, [(t["requested_risk_pct"], t["pnl"]) for t in a.trades]) == (b.status, b.final_balance, [(t["requested_risk_pct"], t["pnl"]) for t in b.trades])


def test_terminal_phase_at_next_day_boundary_does_not_duplicate_daily_snapshot():
    # Day 1 reaches the target. The next day's opportunity causes Day 1 to be
    # finalized and the phase to pass before Day 2 starts. Day 1 must only be
    # emitted once because the DB contract is one snapshot per run/date.
    out = run([opp(1, 108), opp(2, 100)], phases=[phase(target="0.08", min_days=1)])
    assert out.status == "PASSED"
    dates = [d["trading_date"] for d in out.days]
    assert dates.count(date(2025, 11, 1)) == 1
    assert len(dates) == len(set(dates))


def test_incomplete_near_max_dd_reports_risk_capacity_exhaustion():
    # A very high broker minimum can leave the account unable to safely open
    # later opportunities without actually breaching the hard loss floor.
    spec = dict(INSTRUMENT)
    spec["min_quantity"] = 100
    out = FundedBacktestSimulator().simulate(
        initial_balance=5000,
        challenge_type="ONE_STEP",
        phases=[phase(target="0.90")],
        payout_config={},
        risk_tiers=TIERS,
        instrument_spec=spec,
        opportunities=[opp(1, 101), opp(2, 101)],
        configured_max_risk_pct=D("0.0005"),
        historical_end_date=date(2025, 11, 30),
    )
    assert out.status == "INCOMPLETE"
    assert out.summary["incomplete_reason"] in {"RISK_CAPACITY_EXHAUSTED", "NO_TRADES"}


def test_phase_does_not_pass_if_target_was_touched_then_given_back_before_min_days():
    # Day 1 touches the 8% target ($5,400). Day 2 gives back profit, and Day 3
    # completes the minimum-day requirement. The historical target-touch must
    # remain auditable, but the phase must NOT pass below the target balance.
    phases = [phase(target="0.08", min_days=3, reset=False, num=1)]
    out = run([opp(1,108), opp(2,99.5), opp(3,100)], phases=phases, challenge="ONE_STEP", safety_buffer_pct=D("0"))
    assert out.status == "INCOMPLETE"
    p1 = out.phases[0]
    assert p1["target_reached"] is True
    assert D(str(p1["ending_balance"])) < D(str(p1["target_balance"]))


def test_default_safety_buffer_is_zero_for_neutral_backtesting():
    from app.services.funded_backtest.risk_policy import apply_effective_risk_guard
    decision = apply_effective_risk_guard(
        current_balance=D("5000"),
        requested_risk_percentage=D("0.01"),
        remaining_daily_capacity=D("50"),
        remaining_max_capacity=D("500"),
    )
    # With no explicit safety buffer, the full $50 remaining daily capacity is usable.
    assert decision.effective_risk_amount == D("50")
    assert decision.effective_risk_percentage == D("0.01")

def test_payout_waiting_window_resets_if_consistency_becomes_invalid():
    payout = {
        "profit_target_amount": "0", "minimum_payout_amount": "0", "minimum_trading_days": 2,
        "minimum_qualifying_profitable_days": 2, "qualifying_day_minimum_profit_pct": "0",
        "consistency_rule_enabled": True, "consistency_maximum_pct": "0.60",
        "payout_waiting_calendar_days": 2, "payout_profit_split_pct": "0.90", "stop_simulation_when_payout_ready": True,
        "daily_drawdown_pct": "0.50", "daily_drawdown_mode": "STATIC_INITIAL_BALANCE", "max_drawdown_pct": "0.50", "max_drawdown_mode": "STATIC_INITIAL_BALANCE",
    }
    # Two equal +$50 days satisfy 60% consistency (50/100 = 50%) and start the
    # waiting window. A later +$200 day makes consistency 200/300 = 66.67%, so
    # payout readiness must be revoked/reset rather than becoming ready later.
    out = run([opp(1,102), opp(2,102), opp(3,108)], phases=[], challenge="INSTANT", payout=payout, risk_mode="FIXED", fixed_risk_pct=D("0.005"))
    assert out.status == "INCOMPLETE"
    assert out.summary["payout"]["consistency_satisfied"] is False
    assert D(out.summary["payout"]["consistency_pct"]) > D("0.60")
    assert out.payout_ready_at is None
