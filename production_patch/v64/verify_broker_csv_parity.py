"""Offline full-replay V6.4 parity check using exported broker candles.

Read-only. Does not contact API, DB, Redis or broker. This intentionally does not
claim or enable true per-candle incremental calculation.
"""
from pathlib import Path
import argparse,hashlib,json,runpy,time
import pandas as pd

OUTPUTS=('Date','Position','strategy_stop_loss','strategy_target','signal_reason')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    base=Path(__file__).resolve().parent
    p.add_argument('--csv',required=True,help='Chronological broker CSV with Date Open High Low Close; Volume optional')
    p.add_argument('--bars',type=int,default=80000)
    p.add_argument('--baseline',default=str(base/'V64_BASELINE_RESEARCH_ONLY.py'))
    p.add_argument('--optimized',default=str(base/'V64_OPTIMIZED_RESEARCH_ONLY.py'))
    p.add_argument('--report',default='v64_broker_parity_report.json')
    args=p.parse_args()
    df=pd.read_csv(args.csv)
    for col in ('Date','Open','High','Low','Close'):
        if col not in df.columns:raise ValueError(f'Missing {col}')
    df['Date']=pd.to_datetime(df['Date'],utc=True)
    if df.Date.duplicated().any():raise ValueError('Duplicate Date')
    df=df.sort_values('Date').tail(args.bars).reset_index(drop=True)
    if len(df)!=args.bars:raise ValueError(f'Need exactly {args.bars} bars; found {len(df)}')
    out=[]
    for path in (args.baseline,args.optimized):
        cls=runpy.run_path(path)['Strategy']
        start=time.perf_counter(); result=cls(df.copy()).generate(); elapsed=time.perf_counter()-start
        out.append((result,elapsed))
    left,right=out[0][0],out[1][0]
    mismatches={}
    for name in OUTPUTS:
        if name not in left or name not in right:
            raise ValueError(f'Missing required output: {name}')
        if name=='Date':
            bad=pd.to_datetime(left[name],utc=True).reset_index(drop=True).ne(pd.to_datetime(right[name],utc=True).reset_index(drop=True))
        elif name in ('Position','strategy_stop_loss','strategy_target'):
            a,b=pd.to_numeric(left[name],errors='coerce'),pd.to_numeric(right[name],errors='coerce')
            import numpy as np
            bad=~np.isclose(a.to_numpy(dtype=float),b.to_numpy(dtype=float),rtol=1e-12,atol=1e-10,equal_nan=True)
        else:
            bad=left[name].fillna('<NA>').astype(str).reset_index(drop=True).ne(right[name].fillna('<NA>').astype(str).reset_index(drop=True))
        indices=[int(k) for k in list(pd.Series(bad)[pd.Series(bad)].index[:10])]
        if indices:mismatches[name]=dict(count=int(sum(bad)),first_indices=indices)
    report=dict(parity_pass=not mismatches,baseline_sha256=sha(args.baseline),optimized_sha256=sha(args.optimized),bars=len(df),baseline_s=out[0][1],optimized_s=out[1][1],mismatches=mismatches,
        limitations='Matching source outputs is not end-to-end order fill, broker, or next-open parity. Uses this CSV and default strategy parameters only.')
    Path(args.report).write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['parity_pass'] else 2)
if __name__=='__main__':main()
