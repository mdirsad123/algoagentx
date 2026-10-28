"""Offline strict all-column checks for the V6.4 hybrid warm state adapter.

This exercises an *experimental* adapter on synthetic candles only. It is not
an acceptance certificate for a real 80K TradeLocker live deployment.
"""
import argparse
from pathlib import Path
import runpy
import time
import sys
import json
from test_v64_parity import candles, equal_output

ROOT=Path(__file__).resolve().parent

def run(cases):
    cls=runpy.run_path(str(ROOT/'V64_HYBRID_INCREMENTAL_EXPERIMENT.py'))['Strategy']
    report=[]
    for bars,seed,style,steps in cases:
        data=candles(bars+steps,seed,style)
        inst=cls(data.iloc[:bars])
        started=time.monotonic()
        warm=inst.generate()
        warm_sec=time.monotonic()-started
        assert inst.start_live_incremental(warm) is True
        for i in range(bars,bars+steps):
            now=time.monotonic()
            inc=inst.on_closed_candle(data.iloc[i].to_dict()).reset_index(drop=True)
            inc_sec=time.monotonic()-now
            now=time.monotonic()
            expected=cls(data.iloc[i-bars+1:i+1]).generate().tail(1).reset_index(drop=True)
            base_sec=time.monotonic()-now
            difference=equal_output(expected,inc)
            if difference: raise AssertionError(f'{bars}/{seed}/{style} at {i}: {difference}')
            report.append({'warmup_bars':bars,'seed':seed,'style':style,
                           'bar':i,'warmup_seconds':round(warm_sec,3),
                           'hybrid_seconds':round(inc_sec,3),'full_seconds':round(base_sec,3),
                           'all_columns_match':True})
            print(report[-1],flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--short',action='store_true')
    p.add_argument('--report',default=str(ROOT/'HYBRID_PARITY_RESULTS.json'))
    a=p.parse_args()
    tests=[(650,3,'normal',4),(800,7,'flat',4)] if a.short else [
        (650,3,'normal',4),(800,7,'flat',4),(800,7,'uptrend',4),(800,7,'downtrend',4),(800,7,'spike',4),
        (1400,8,'normal',2)]
    rows=run(tests)
    Path(a.report).write_text(json.dumps({'type':'synthetic_rolling_all_column','passed':True,'comparisons':rows},indent=2))
    print('PASS',len(rows),'strict rolling-bar checks')
