"""Compare optimized HTF snapshots to the unchanged scalar pivot helpers.

Small deterministic fixtures cover boundaries; 80K real-data replay is separate.
"""
import numpy as np
import pandas as pd
import pytest

from strategies.v64_hybrid_incremental import XAUUSD5MSupplyDemandRejectionV35CandidateA


def scalar_snapshots(engine, frame):
    highs, lows, result = [], [], []
    for j in range(len(frame)):
        pivot = j - engine.htf_swing_right
        if engine._is_htf_swing_high(frame, pivot):
            highs.append(float(frame.iloc[pivot]['High']))
        if engine._is_htf_swing_low(frame, pivot):
            lows.append(float(frame.iloc[pivot]['Low']))
        ph, lh = (highs[-2] if len(highs) >= 2 else None), (highs[-1] if highs else None)
        pl, ll = (lows[-2] if len(lows) >= 2 else None), (lows[-1] if lows else None)
        bias, reason = 'NEUTRAL', 'INSUFFICIENT_CONFIRMED_SWINGS'
        if None not in (ph, lh, pl, ll):
            if lh > ph and ll > pl:
                bias, reason = 'BULLISH', 'HH_AND_HL'
            elif lh < ph and ll < pl:
                bias, reason = 'BEARISH', 'LH_AND_LL'
            else:
                reason = 'MIXED_STRUCTURE'
        result.append(dict(available_time=pd.Timestamp(frame.iloc[j]['_htf_close_time']),
                           bias=bias, reason=reason, last_swing_high=lh,
                           previous_swing_high=ph, last_swing_low=ll, previous_swing_low=pl))
    return result


@pytest.mark.parametrize('left,right', [(1, 1), (2, 2), (3, 1), (1, 4), (0, 2), (2, 0)])
@pytest.mark.parametrize('length', [0, 1, 5, 150])
def test_snapshot_equality_including_ties_missing_values_and_edges(left, right, length):
    engine = XAUUSD5MSupplyDemandRejectionV35CandidateA.__new__(XAUUSD5MSupplyDemandRejectionV35CandidateA)
    engine.htf_swing_left, engine.htf_swing_right = left, right
    values = np.resize(np.array([3., 8., 8., 1., 4., np.nan, 9., 3., 2., 4., 5.]), length)
    frame = pd.DataFrame({'High': values + 10, 'Low': values,
                          '_htf_close_time': pd.date_range('2026-10-01', periods=length, freq='15min', tz='UTC')})
    assert engine._build_15m_structure_snapshots(frame) == scalar_snapshots(engine, frame)


def test_future_htf_bars_do_not_change_previous_snapshots():
    engine = XAUUSD5MSupplyDemandRejectionV35CandidateA.__new__(XAUUSD5MSupplyDemandRejectionV35CandidateA)
    engine.htf_swing_left = engine.htf_swing_right = 2
    values = np.resize(np.array([3., 9., 5., 1., 2., 7., 8., 3.]), 50)
    frame = pd.DataFrame({'High': values + 10, 'Low': values,
                          '_htf_close_time': pd.date_range('2026-10-01', periods=50, freq='15min', tz='UTC')})
    expected = engine._build_15m_structure_snapshots(frame)
    for size in (3, 10, 25, 49):
        assert engine._build_15m_structure_snapshots(frame.iloc[:size]) == expected[:size]


@pytest.mark.parametrize('left,right', [(1, 1), (2, 5), (8, 3), (20, 20)])
@pytest.mark.parametrize('kind', ['random', 'all_nan', 'ascending', 'descending', 'constant'])
def test_snapshot_randomized_and_degenerate_windows(left, right, kind):
    engine = XAUUSD5MSupplyDemandRejectionV35CandidateA.__new__(XAUUSD5MSupplyDemandRejectionV35CandidateA)
    engine.htf_swing_left, engine.htf_swing_right = left, right
    rng = np.random.default_rng(20261029)
    values = rng.integers(0, 20, 120).astype(float)
    values[rng.random(120) < .3] = np.nan
    if kind == 'all_nan':
        values[:] = np.nan
    elif kind == 'ascending':
        values = np.arange(120, dtype=float)
    elif kind == 'descending':
        values = np.arange(120, dtype=float)[::-1]
    elif kind == 'constant':
        values[:] = 5.
    frame = pd.DataFrame({'High': values + 10, 'Low': values,
                          '_htf_close_time': pd.date_range('2026-10-01', periods=120, freq='15min', tz='Asia/Kolkata')},
                         index=np.arange(120) * 3 + 7)
    assert engine._build_15m_structure_snapshots(frame) == scalar_snapshots(engine, frame)