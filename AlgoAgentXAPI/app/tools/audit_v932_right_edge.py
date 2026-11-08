"""Offline-only audit for signals that require a future candle in V9.32.

This checks one known historical candidate by comparing the *same bar*
with and without candles that occur after it. It does not change code.

python -m app.tools.audit_v932_right_edge --csv ../artifacts/backtest_private/xauusd.csv --lookback 10000 --target 2026-11-04T17:30:00Z --output ../V932_RIGHT_EDGE_AUDIT.json
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import pandas as pd
from strategies.v932_original_db_source import Strategy

def read_signal(frame, i):
    r=frame.iloc[i]
    return {'Date':str(r['Date']),'Position':int(r['Position']),
            'signal_reason':str(r['signal_reason']),
            'SL':None if pd.isna(r['strategy_stop_loss']) else float(r['strategy_stop_loss']),
            'TP':None if pd.isna(r['strategy_target']) else float(r['strategy_target'])}

def main():
    p=argparse.ArgumentParser();p.add_argument('--csv',type=Path,required=True);p.add_argument('--target',default='2026-11-04T17:30:00Z');p.add_argument('--lookback',type=int,default=10000);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    d=pd.read_csv(a.csv).tail(a.lookback).reset_index(drop=True)
    d.Date=pd.to_datetime(d.Date,utc=True)
    target=pd.Timestamp(a.target)
    if target.tzinfo is None:target=target.tz_localize('UTC')
    ix=d.index[d.Date.eq(target)]
    if len(ix)!=1:raise ValueError('Target not found in lookback')
    ix=int(ix[0])
    t=time.perf_counter();full=Strategy(d).generate();full_s=time.perf_counter()-t
    t=time.perf_counter();rolling=Strategy(d.iloc[:ix+1].copy()).generate();rolling_s=time.perf_counter()-t
    with_future=read_signal(full,ix);at_right_edge=read_signal(rolling,-1)
    r={'target':a.target,'lookback':a.lookback,'historical_full_window':with_future,
       'as_latest_closed_candle':at_right_edge,
       'latest_differs':with_future!=at_right_edge,
       'future_candles_present':len(d)-ix-1,
       'wall_seconds':{'full':round(full_s,3),'prefix':round(rolling_s,3)},
       'interpretation':'A right-edge mismatch means backtest entry parity cannot be assumed for this latest candle.'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
