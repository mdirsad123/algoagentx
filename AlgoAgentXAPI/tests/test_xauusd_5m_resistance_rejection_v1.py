import pandas as pd

from strategies.xauusd_5m_resistance_rejection_v1 import XAUUSD5MResistanceRejectionV1


def make_df(rows):
    return pd.DataFrame([
        {"Date": pd.Timestamp("2026-07-01 00:00") + pd.Timedelta(minutes=5*i), "Open": o, "High": h, "Low": l, "Close": c}
        for i, (o,h,l,c) in enumerate(rows)
    ])


def base_kwargs(**extra):
    params = dict(
        swing_left=2,
        swing_right=2,
        zone_width=1.0,
        minimum_reaction=1.0,
        minimum_strength=0.5,
        approach_distance=3.0,
        merge_distance=0.3,
        max_zone_age=50,
        minimum_body_ratio=0.10,
        minimum_upper_wick_ratio=0.10,
        minimum_zone_penetration=0.0,
        maximum_close_position=0.8,
        entry_confirmation="BREAK_REJECTION_LOW",
        confirmation_bars=3,
        sl_buffer=0.2,
        minimum_rr=1.5,
        target_rr=2.0,
        breakout_buffer=0.2,
        debug_mode=True,
    )
    params.update(extra)
    return params


def valid_rejection_rows():
    return [
        (98.0, 99.0, 97.5, 98.5),
        (98.5, 100.0, 98.0, 99.3),
        (99.3, 103.0, 99.0, 102.0),  # pivot high -> zone around 103
        (102.0, 102.2, 100.0, 100.5),
        (100.5, 101.0, 98.5, 99.0),   # swing is now confirmed
        (99.0, 100.5, 98.8, 100.0),
        (100.0, 102.0, 99.8, 101.5),
        (101.5, 103.4, 101.2, 102.2), # enters/sweeps zone, closes below zone_low 102.5
        (102.1, 102.2, 100.8, 101.0), # breaks rejection low -> short
        (101.0, 101.2, 99.8, 100.0),
    ]


def test_valid_sequence_generates_one_short_and_diagnostics():
    out = XAUUSD5MResistanceRejectionV1(make_df(valid_rejection_rows()), **base_kwargs()).generate()
    assert int((out["Position"] == -1).sum()) == 1
    diag = out.attrs["strategy_diagnostics"]
    assert diag["total_zones"] >= 1
    assert diag["zone_interactions"] >= 1
    assert diag["rejection_setups"] >= 1
    assert diag["confirmed_setups"] == 1
    assert diag["executed_trades"] == 1
    signal = out.loc[out["Position"] == -1].iloc[0]
    assert float(signal["strategy_stop_loss"]) > float(signal["Close"])
    assert float(signal["strategy_target"]) < float(signal["Close"])


def test_clean_breakout_generates_zero_shorts():
    rows = valid_rejection_rows()[:7] + [
        (101.5, 104.0, 101.4, 103.8),
        (103.8, 104.5, 103.5, 104.2),
        (104.2, 105.0, 104.0, 104.8),
    ]
    out = XAUUSD5MResistanceRejectionV1(make_df(rows), **base_kwargs()).generate()
    assert int((out["Position"] == -1).sum()) == 0


def test_touch_only_generates_zero_shorts():
    rows = valid_rejection_rows()[:7] + [
        (101.5, 102.7, 101.6, 102.6), # touch zone, close inside it
        (102.6, 102.8, 102.2, 102.5),
        (102.5, 102.7, 102.1, 102.4),
        (102.4, 102.6, 102.0, 102.3),
    ]
    out = XAUUSD5MResistanceRejectionV1(make_df(rows), **base_kwargs(setup_expiry_bars=2)).generate()
    assert int((out["Position"] == -1).sum()) == 0


def test_duplicate_bearish_candles_do_not_duplicate_trade():
    rows = valid_rejection_rows() + [
        (100.0, 100.2, 98.5, 99.0),
        (99.0, 99.2, 97.5, 98.0),
        (98.0, 98.2, 96.5, 97.0),
    ]
    out = XAUUSD5MResistanceRejectionV1(make_df(rows), **base_kwargs()).generate()
    assert int((out["Position"] == -1).sum()) == 1


def test_rejection_close_mode_supported():
    out = XAUUSD5MResistanceRejectionV1(
        make_df(valid_rejection_rows()),
        **base_kwargs(entry_confirmation="REJECTION_CLOSE"),
    ).generate()
    assert int((out["Position"] == -1).sum()) == 1
