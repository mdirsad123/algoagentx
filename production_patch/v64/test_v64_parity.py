"""Parity tests for exact full-replay performance optimizations, no broker or live orders."""
import argparse,runpy,time,sys
from pathlib import Path
import numpy as np
import pandas as pd

def candles(n, seed, style):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0, 1.8, n)
    if style == 'uptrend': eps += 0.18
    if style == 'downtrend': eps -= 0.18
    if style == 'flat': eps *= 0.15
    if style == 'spike': eps[::31] += rng.choice([-1, 1], len(eps[::31]))*9
    mid = 4000 + np.cumsum(eps)
    op = mid+rng.normal(0,0.25,n)
    high = np.maximum(op,mid) + rng.uniform(.15,2.,n)
    low = np.minimum(op,mid) - rng.uniform(.15,2.,n)
    return pd.DataFrame({'Date':pd.date_range('2024-01-01',periods=n,freq='5min',tz='UTC'), 'Open':op,'High':high,'Low':low,'Close':mid,'Volume':rng.integers(100,5000,n)})

def equal_output(a,b):
    if list(a.columns)!=list(b.columns):return f'columns mismatch: {set(a.columns).symmetric_difference(b.columns)}'
    for k in a.columns:
        x,y=a[k],b[k]
        try:
            pd.testing.assert_series_equal(x,y,check_dtype=False,check_exact=False,atol=1e-12,rtol=1e-12)
        except AssertionError as exc:
            return f'{k}: {str(exc)[:200]}'
    return ''

def run(base,opt,cases):
    Baseline = runpy.run_path(str(base))['Strategy']
    Optimized = runpy.run_path(str(opt))['Strategy']
    result=[]
    for n,seed,kind in cases:
        df=candles(n,seed,kind)
        t0=time.perf_counter(); left=Baseline(df).generate();base_s=time.perf_counter()-t0
        t0=time.perf_counter(); right=Optimized(df).generate();fast_s=time.perf_counter()-t0
        fail=equal_output(left,right)
        # exact trade intent, SL/TP/signal reasons, and shadow portfolio positions
        if fail:raise AssertionError(f'{n}/{seed}/{kind}: {fail}')
        result.append({'bars':n,'seed':seed,'style':kind,'baseline_s':round(base_s,3),'optimized_s':round(fast_s,3),'positions':int((left.Position!=0).sum()),'parity':'PASS'})
        print(result[-1],flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',default=str(Path(__file__).parent/'V64_BASELINE_RESEARCH_ONLY.py'))
    parser.add_argument('--optimized',default=str(Path(__file__).parent/'V64_OPTIMIZED_RESEARCH_ONLY.py'))
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--long',action='store_true')
    a=parser.parse_args()
    cases=[(600,2,'normal'),(1000,5,'spike'),(1400,8,'uptrend'),(1400,9,'downtrend'),(1800,11,'flat')]
    if not a.quick:cases.extend([(2600,19,'normal'),(3500,20,'spike')])
    if getattr(a, "long", False):cases.extend([(10000,24,'spike')])
    run(a.baseline,a.optimized,cases)
