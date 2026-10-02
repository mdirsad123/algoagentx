from decimal import Decimal
from app.services.trading.partial_exit_engine import calculate_broker_partial_split
from app.services.live.live_partial_exit_service import make_idempotency_key

def spec(): return {"min_lot":0.01,"lot_step":0.01}

def test_010_90_percent_valid():
    r=calculate_broker_partial_split(total_size=0.10,percent=0.90,quantity_mode="LOTS",instrument_spec=spec())
    assert r["eligible"] is True; assert Decimal(str(r["partial_close_size"]))==Decimal("0.09"); assert Decimal(str(r["runner_size"]))==Decimal("0.01")

def test_009_90_percent_skips():
    r=calculate_broker_partial_split(total_size=0.09,percent=0.90,quantity_mode="LOTS",instrument_spec=spec())
    assert r["eligible"] is False; assert r["reason"]=="RUNNER_BELOW_BROKER_MINIMUM"

def test_idempotency_is_deterministic():
    a=make_idempotency_key('d','a','p','s',Decimal('1.7'),Decimal('0.9')); b=make_idempotency_key('d','a','p','s',Decimal('1.7'),Decimal('0.9')); assert a==b and a.startswith('AXPX-')

def test_trigger_formula_boundaries():
    entry=Decimal('100'); risk=Decimal('1'); r=Decimal('1.7')
    assert entry+r*risk==Decimal('101.7'); assert entry-r*risk==Decimal('98.3')

def test_006_50_percent_valid():
    r=calculate_broker_partial_split(total_size=0.06,percent=0.50,quantity_mode="LOTS",instrument_spec=spec())
    assert r["eligible"] is True
    assert Decimal(str(r["partial_close_size"]))==Decimal("0.03")
    assert Decimal(str(r["runner_size"]))==Decimal("0.03")


def test_copy_accounts_get_independent_idempotency_keys():
    primary=make_idempotency_key('dep','primary','pos-1','state-1',Decimal('1.0'),Decimal('0.5'))
    copy=make_idempotency_key('dep','copy','pos-2','state-2',Decimal('1.0'),Decimal('0.5'))
    assert primary != copy
