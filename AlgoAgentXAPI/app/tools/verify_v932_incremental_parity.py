"""Offline V9.32 parity and wall-time probe; no DB/broker access.

Run from AlgoAgentXAPI (install dependencies first):
 python -m app.tools.verify_v932_incremental_parity --csv ../artifacts/backtest_private/xauusd.csv --history 80000 --steps 4 --output ../V932_PARITY_LOCAL.json

Requires >= history+steps genuine M5 rows and a consecutive final run. All results
are limited to the supplied windows: not a proof of all future live signals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from strategies.v932_original_db_source import Strategy as Frozen
from strategies.v932_pinned_strategy import Strategy as Pinned
from strategies.v932_incremental import Strategy as Hybrid

FIELDS = ('Date','Position','strategy_stop_loss','strategy_target','signal_reason')

def _serial(x):
    if pd.isna(x):return None
    if isinstance(x,pd.Timestamp):return x.isoformat()
    if isinstance(x,(np.integer,np.floating)):return x.item()
    return x

def _row(frame):
    r=frame.iloc[-1]
    return {k:_serial(r[k]) for k in FIELDS}

def _same(expected, actual):
    for k in FIELDS:
        a,b=expected[k],actual[k]
        if k in ('strategy_stop_loss','strategy_target'):
            if a is None and b is None:continue
            if a is None or b is None or abs(float(a)-float(b))>1e-7:return False,k
        elif a != b:return False,k
    return True,''

def verify(csv:Path, history:int, steps:int, end_at: str | None = None):
    d=pd.read_csv(csv,usecols=['Date','Open','High','Low','Close','Volume'])
    d.Date=pd.to_datetime(d.Date,utc=True)
    d=d.drop_duplicates('Date').sort_values('Date').reset_index(drop=True)
    if history<100 or steps<1 or len(d)<history+steps:
        raise ValueError('Need >= history+steps candles and history>=100')
    # Ensure final steps are all consecutive; skip invalid tail to find one.
    start=None
    if end_at:
        target=pd.Timestamp(end_at)
        if target.tzinfo is None:target=target.tz_localize('UTC')
        matches=d.index[d['Date'].eq(target)]
        if len(matches)!=1:raise ValueError('The requested end-at candle was not found')
        start=int(matches[0])-steps+1
        if start<history:raise ValueError('Not enough preceding history at requested time')
        tt=d.Date.iloc[start-1:start+steps]
        if len(tt)!=steps+1 or not tt.diff().iloc[1:].eq(pd.Timedelta(minutes=5)).all():
            raise ValueError('End-at candles are not consecutive')
    else:
        for j in range(len(d)-steps,history-1,-1):
            tt=d.Date.iloc[j-1:j+steps]
            if len(tt)==steps+1 and tt.diff().iloc[1:].eq(pd.Timedelta(minutes=5)).all():
                start=j
                break
        if start is None:raise ValueError('Could not find a final consecutive run')
    block=d.iloc[start-history:start+steps].reset_index(drop=True)
    history_df=block.iloc[:history].copy()
    result={'history':history,'steps':steps,'csv':str(csv),'first':str(block.Date.iloc[0]),'last':str(block.Date.iloc[-1]),'times':{},'checks':[],'passed':False}
    t=time.perf_counter()
    original = Frozen(history_df).generate()
    result['times']['cold_frozen_s']=time.perf_counter()-t
    t=time.perf_counter()
    pinned= Pinned(history_df).generate()
    result['times']['cold_pinned_s']=time.perf_counter()-t
    # Compare ENTIRE generated ledger for identical cold computation.
    if len(original)!=len(pinned): raise AssertionError('Cold pinned length mismatch')
    for k in FIELDS[1:]:
        a=original[k];b=pinned[k]
        if k in ('strategy_stop_loss','strategy_target'):
            if not np.allclose(pd.to_numeric(a,errors='coerce').to_numpy(float),pd.to_numeric(b,errors='coerce').to_numpy(float),rtol=0,atol=1e-7,equal_nan=True):
                raise AssertionError('Cold pinned signal ledger mismatch: '+k)
        elif not a.equals(b):raise AssertionError('Cold pinned signal ledger mismatch: '+k)
    t=time.perf_counter()
    adapter=Hybrid(history_df)
    cold=adapter.generate()
    result['times']['cold_adapter_s']=time.perf_counter()-t
    ok,field=_same(_row(original),_row(cold))
    if not ok: raise AssertionError('Cold adapter mismatch: '+field)
    if not adapter.start_live_incremental(cold):
        raise AssertionError('Failed to prime hybrid')
    # Compare next-candle row with ORIGINAL unmodified full source.
    for i in range(history, history+steps):
        new=block.iloc[i].to_dict()
        t=time.perf_counter();got=adapter.on_closed_candle(new)
        incr_time=time.perf_counter()-t
        t=time.perf_counter();baseline=Frozen(block.iloc[:i+1].copy()).generate()
        full_time=time.perf_counter()-t
        expectation=_row(baseline);actual=_row(got)
        same,diff=_same(expectation,actual)
        result['checks'].append({'candle':str(new['Date']),'same':same,'different_field':diff,'frozen':expectation,'hybrid':actual,'incremental_wall_s':round(incr_time,3),'baseline_wall_s':round(full_time,3)})
        if not same:break
    result['passed']=len(result['checks'])==steps and all(x['same'] for x in result['checks'])
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--csv',type=Path,required=True);p.add_argument('--history',type=int,default=80000);p.add_argument('--steps',type=int,default=4);p.add_argument('--output',type=Path,required=True);p.add_argument('--end-at',type=str,default=None,help='Exact UTC timestamp of final test candle')
    a=p.parse_args()
    try:r=verify(a.csv,a.history,a.steps,a.end_at)
    except Exception as exc:
        print(f'FAIL: {type(exc).__name__}: {exc}',file=sys.stderr)
        raise
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,default=str))
    print('PASS' if r['passed'] else 'FAIL', 'history',a.history,'steps',a.steps,'trace',a.output)
    for c in r['checks']: print('candle',c['candle'],'match',c['same'],'incremental_s',c['incremental_wall_s'],'frozen_s',c['baseline_wall_s'],'signal',c['frozen']['Position'])
    sys.exit(0 if r['passed'] else 2)
if __name__=='__main__':main()
