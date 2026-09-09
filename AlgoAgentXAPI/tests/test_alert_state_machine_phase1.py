"""Focused transition tests for Phase 1 alert duplicate prevention/rearm semantics."""
from decimal import Decimal
from types import SimpleNamespace

from app.services.alerts.evaluator import _can_rearm, _transition_matches


def _alert(**kwargs):
    base = dict(
        trigger_mode="RECURRING",
        rearm_eligible_at=None,
        rearm_distance=Decimal("2"),
        alert_type="CROSSING_UP",
        target_price=Decimal("3525"),
        zone_low=None,
        zone_high=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_crossing_up_is_transition_only():
    alert = _alert(alert_type="CROSSING_UP")
    assert _transition_matches(alert, Decimal("3524.80"), Decimal("3525.10")) is True
    assert _transition_matches(alert, Decimal("3525.10"), Decimal("3525.20")) is False


def test_crossing_down_is_transition_only():
    alert = _alert(alert_type="CROSSING_DOWN", target_price=Decimal("3500"))
    assert _transition_matches(alert, Decimal("3500.30"), Decimal("3499.90")) is True
    assert _transition_matches(alert, Decimal("3499.90"), Decimal("3499.80")) is False


def test_entering_and_leaving_zone_do_not_spam_inside_zone():
    entering = _alert(alert_type="ENTERING_ZONE", zone_low=Decimal("3524"), zone_high=Decimal("3526"))
    leaving = _alert(alert_type="LEAVING_ZONE", zone_low=Decimal("3524"), zone_high=Decimal("3526"))
    assert _transition_matches(entering, Decimal("3523.90"), Decimal("3524.20")) is True
    assert _transition_matches(entering, Decimal("3524.20"), Decimal("3524.30")) is False
    assert _transition_matches(leaving, Decimal("3525.90"), Decimal("3526.10")) is True


def test_crossing_rearm_requires_reset_distance_after_cooldown():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    alert = _alert(rearm_eligible_at=now - timedelta(seconds=1))
    assert _can_rearm(alert, Decimal("3524"), now) is False
    assert _can_rearm(alert, Decimal("3523"), now) is True

    alert.rearm_eligible_at = now + timedelta(seconds=30)
    assert _can_rearm(alert, Decimal("3522"), now) is False
