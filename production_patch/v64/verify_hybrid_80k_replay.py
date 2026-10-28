"""Offline, read-only frozen V6.4 vs hybrid full and rolling bar-parity check.

NEVER sends orders, reads broker APIs or edits the Strategy database.
Use EXACT active DB source and non-secret strategy parameters and broker M5 UTC data.
A passed spot-check is NOT permission for unattended live order execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time
import numpy as np
import pandas as pd

COLUMNS = ('Date', 'Position', 'strategy_stop_loss', 'strategy_target', 'signal_reason')
_NUMS = {'Position','strategy_stop_loss','strategy_target'}


def safe_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output_diffs(a, b, all_rows=False):
    if not all_rows:
        a, b = a.tail(1).reset_index(drop=True), b.tail(1).reset_index(drop=True)
    result = {}
    for c in COLUMNS:
        if c not in a or c not in b:
            result[c] = {'missing_column': True}
            continue
        if len(a) != len(b):
            result[c] = {'row_count_left': len(a), 'row_count_right': len(b)}
            continue
        if c in _NUMS:
            av = pd.to_numeric(a[c],errors='coerce').to_numpy(dtype=float)
            bv = pd.to_numeric(b[c],errors='coerce').to_numpy(dtype=float)
            mask = ~np.isclose(av,bv,rtol=1e-12,atol=1e-9,equal_nan=True)
        elif c == 'Date':
            av = pd.to_datetime(a[c],utc=True)
            bv = pd.to_datetime(b[c],utc=True)
            mask = av.ne(bv).to_numpy()
        else:
            mask = a[c].fillna('').astype(str).reset_index(drop=True).ne(b[c].fillna('').astype(str).reset_index(drop=True)).to_numpy()
        if mask.any():
            result[c] = {'count':int(mask.sum()),'first_indices':np.where(mask)[0][:10].astype(int).tolist()}
    return result


def params_from_file(path):
    if not path: return {}
    raw = json.loads(Path(path).read_text(encoding='utf8'))
    if not isinstance(raw,dict): raise ValueError('Strategy params JSON must be an object')
    if isinstance(raw.get('strategy_params'),dict): return raw['strategy_params']
    metadata={'source_code','source_code_sha256','engine_mode','strategy_type','market','timeframe','live_history_bars',
              'required_history_bars','live_incremental_enabled','live_incremental_parity_verified', 'runtime_config'}
    return {k:v for k,v in raw.items() if k not in metadata and not k.startswith('_') and isinstance(v,(str,int,float,bool,type(None)))}


def check_candles(frame):
    # Accept canonical TradeLocker columns or historical research CSV names.
    canonical={'timestamp':'Date','date':'Date','time':'Date','open':'Open',
               'high':'High','low':'Low','close':'Close','volume':'Volume'}
    frame=frame.rename(columns={k:canonical.get(str(k).strip().lower(),k) for k in frame.columns})
    keys=('Date','Open','High','Low','Close')
    for k in keys:
        if k not in frame: raise ValueError(f'Missing {k}')
    frame['Date']=pd.to_datetime(frame['Date'],utc=True,errors='raise')
    if frame.Date.isna().any() or frame.Date.duplicated().any():raise ValueError('Invalid/duplicate UTC Date')
    if not frame.Date.is_monotonic_increasing:raise ValueError('Input must be sorted ascending by UTC Date')
    for k in ('Open','High','Low','Close'):
        frame[k]=pd.to_numeric(frame[k],errors='raise')
        if not np.isfinite(frame[k].to_numpy(dtype=float)).all():raise ValueError(f'Nonfinite {k}')
    if 'Volume' not in frame: frame['Volume']=0.0
    frame['Volume']=pd.to_numeric(frame['Volume'],errors='raise')
    return frame


def execute(csv,base,candidate,params_path,bars,checks,report,start_index=None):
    params=params_from_file(params_path)
    candles=check_candles(pd.read_csv(csv))
    if start_index is None: start_index=len(candles)-bars-checks
    if start_index < 0 or start_index+bars+checks>len(candles):raise ValueError('Not enough candles for bars + checks')
    # Match live loader: output timestamps normalized to UTC.
    history=candles.iloc[start_index:start_index+bars].copy().reset_index(drop=True)
    baseline=runpy.run_path(str(base))['Strategy']
    hybrid=runpy.run_path(str(candidate))['Strategy']
    result={'source_baseline_sha256':safe_sha(base),'candidate_sha256':safe_sha(candidate),
            'csv':str(Path(csv).name),'bars':bars,'start_utc':str(history.Date.iloc[0]),
            'params_supplied':bool(params_path),'checks_requested':checks,'steps':[],
            'limitations':'External candle CSV, may not match active TradeLocker DB. Position/SL/TP/reason compare only. Not execution parity or approval.'}
    print('START frozen full history',bars,flush=True)
    t=time.perf_counter(); reference=baseline(history.copy(),**params).generate();bt=time.perf_counter()-t
    print('START hybrid full history',bars,flush=True)
    t=time.perf_counter(); inst=hybrid(history.copy(),**params); generated=inst.generate();ht=time.perf_counter()-t
    diffs=output_diffs(reference,generated,all_rows=True)
    result['initial']={'baseline_s':round(bt,3),'hybrid_s':round(ht,3),'all_signal_rows_match':not diffs,'differences':diffs,
                       'baseline_buy_sell_count':int((pd.to_numeric(reference.Position,errors='coerce').fillna(0)!=0).sum())}
    print('INITIAL',json.dumps(result['initial']),flush=True)
    if diffs:
        result['parity_pass']=False
        Path(report).write_text(json.dumps(result,indent=2,default=str))
        return 2
    if not inst.start_live_incremental(generated):
        raise RuntimeError('Hybrid did not accept its own warmup output')
    for k in range(checks):
        i=start_index+bars+k
        raw=candles.iloc[i].to_dict()
        t=time.perf_counter(); actual=inst.on_closed_candle(raw); it=time.perf_counter()-t
        rolling=candles.iloc[i-bars+1:i+1].reset_index(drop=True)
        t=time.perf_counter(); expected=baseline(rolling,**params).generate();ft=time.perf_counter()-t
        diff=output_diffs(expected,actual)
        step={'candle_utc':str(raw['Date']),'frozen_full_s':round(ft,3),'hybrid_incremental_s':round(it,3),
              'position':str(actual.iloc[-1].get('Position')),'match':not diff,'differences':diff}
        result['steps'].append(step)
        print('STEP',k+1,json.dumps(step),flush=True)
        if diff:break
    result['parity_pass']=all(row['match'] for row in result['steps']) and len(result['steps'])==checks
    Path(report).write_text(json.dumps(result,indent=2,default=str))
    return 0 if result['parity_pass'] else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    here=Path(__file__).resolve().parent
    p.add_argument('--csv',required=True)
    p.add_argument('--baseline',default=str(here/'V64_BASELINE_RESEARCH_ONLY.py'))
    p.add_argument('--candidate',default=str(here/'V64_HYBRID_INCREMENTAL_EXPERIMENT.py'))
    p.add_argument('--params-file',default=None,help='Non-secret exact active DB strategy parameters JSON')
    p.add_argument('--bars',type=int,default=80000)
    p.add_argument('--checks',type=int,default=3)
    p.add_argument('--start-index',type=int,default=None)
    p.add_argument('--report',default='v64_hybrid_80k_report.json')
    a=p.parse_args()
    code=execute(a.csv,a.baseline,a.candidate,a.params_file,a.bars,a.checks,a.report,a.start_index)
    sys.exit(code)
