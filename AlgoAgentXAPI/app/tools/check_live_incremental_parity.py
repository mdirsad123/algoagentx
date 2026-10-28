"""Read-only full-history vs retained-state parity validation.

Example (offline; no API, DB, broker or orders):
python -m app.tools.check_live_incremental_parity --source active_v64.py \\
    --csv market_data.csv --history-bars 80000 --checks 10 \\
    --parameters-json '{"rr_ratio":2.0}' --report incremental_parity.json

The strategy's source must be compatible with AlgoAgentX dynamic loader.
PASS verifies the selected sample bars only, not all market regimes or execution.
"""
from __future__ import annotations

import argparse
from datetime import timezone
import inspect
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

from app.services.dynamic_strategy_loader import load_dynamic_strategy_class
from app.services.live.signal_contract import extract_latest_signal_payload


def _run_strategy_generate(instance):
    for name in ('generate', 'generate_signals', 'run'):
        method = getattr(instance, name, None)
        if callable(method):
            output = method()
            if isinstance(output, pd.DataFrame):
                return output
    frame = getattr(instance, 'df', None)
    if isinstance(frame, pd.DataFrame):
        return frame
    raise ValueError('Strategy generate() did not return DataFrame')

FIELDS = ('signal_type', 'strategy_stop_loss', 'strategy_target', 'strategy_risk_points',
          'strategy_reward_points', 'signal_reason')


def normalize(value):
    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return None
    if hasattr(value, 'item'):
        return normalize(value.item())
    return value


def compare(expected, observed):
    problems = {}
    for key in FIELDS:
        left, right = normalize(expected.get(key)), normalize(observed.get(key))
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            identical = np.isclose(left, right, rtol=1e-12, atol=1e-10, equal_nan=True)
        else:
            identical = (str(left) == str(right))
        if not identical:
            problems[key] = {'full': str(left), 'incremental': str(right)}
    return problems


def construct(cls, frame, kwargs):
    sig = inspect.signature(cls.__init__)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        args = kwargs
    else:
        args = {k:v for k,v in kwargs.items() if k in sig.parameters and k not in {'self','df'}}
    return cls(frame.copy(), **args)


def read_data(path):
    frame = pd.read_csv(path)
    rename = {c:c.title() for c in frame.columns if c.lower() in {'open','high','low','close','volume','date'}}
    frame = frame.rename(columns=rename)
    if 'Date' not in frame and 'time' in frame.columns:
        frame = frame.rename(columns={'time':'Date'})
    required = {'Date','Open','High','Low','Close','Volume'}
    if not required.issubset(frame.columns):
        raise ValueError(f'CSV must include {required}; found {set(frame.columns)}')
    frame['Date'] = pd.to_datetime(frame['Date'], utc=True, errors='raise')
    frame = frame.sort_values('Date').drop_duplicates('Date').reset_index(drop=True)
    for col in ('Open','High','Low','Close','Volume'):
        frame[col] = pd.to_numeric(frame[col], errors='raise')
    return frame


def verify(cls, data, history_bars, checks, params):
    if getattr(cls, 'LIVE_INCREMENTAL_VERSION', None) != 1:
        raise ValueError('Strategy must declare LIVE_INCREMENTAL_VERSION = 1')
    if not callable(getattr(cls, 'start_live_incremental', None)) or not callable(getattr(cls, 'on_closed_candle', None)):
        raise ValueError('Missing start_live_incremental or on_closed_candle method')
    if len(data) < history_bars + checks:
        raise ValueError('Need at least history_bars + checks candles')
    warm = data.iloc[:history_bars]
    strategy = construct(cls, warm, params)
    started = time.perf_counter()
    initial = _run_strategy_generate(strategy)
    warm_elapsed = time.perf_counter() - started
    if strategy.start_live_incremental(initial) is not True:
        raise ValueError('start_live_incremental must return True')
    results = []
    for i in range(history_bars, history_bars + checks):
        closed = data.iloc[i].to_dict()
        started = time.perf_counter()
        inc = strategy.on_closed_candle(closed)
        inc_elapsed = time.perf_counter() - started
        if not isinstance(inc, pd.DataFrame) or inc.empty or 'Date' not in inc.columns:
            raise ValueError(f'Bad incremental output for bar {i}')
        observed_date = pd.Timestamp(inc.iloc[-1]['Date']).to_pydatetime().astimezone(timezone.utc)
        expected_date = pd.Timestamp(closed['Date']).to_pydatetime().astimezone(timezone.utc)
        if observed_date != expected_date:
            raise ValueError(f'Date mismatch at {i}')
        started = time.perf_counter()
        reference = _run_strategy_generate(construct(cls, data.iloc[i-history_bars+1:i+1], params))
        full_elapsed = time.perf_counter() - started
        problems = compare(extract_latest_signal_payload(reference), extract_latest_signal_payload(inc))
        results.append({'bar': i, 'date': str(closed['Date']), 'matched': not problems,
                        'problems': problems, 'full_seconds': round(full_elapsed,3),
                        'incremental_seconds': round(inc_elapsed,5)})
    return {'pass': all(x['matched'] for x in results), 'warmup_seconds': round(warm_elapsed,3),
            'checks': results, 'history_bars': history_bars,
            'limitations': 'Selected-bar signal contract parity only; not runtime/order/backtest parity.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--history-bars', type=int, required=True)
    parser.add_argument('--checks', type=int, default=10)
    parser.add_argument('--parameters-json', default='{}')
    parser.add_argument('--report', default='incremental_parity.json')
    args = parser.parse_args()
    params = json.loads(args.parameters_json)
    if not isinstance(params, dict):
        raise ValueError('Parameters must be JSON object')
    cls = load_dynamic_strategy_class(Path(args.source).read_text(encoding='utf-8'))
    data = read_data(args.csv)
    report = verify(cls, data, args.history_bars, args.checks, params)
    Path(args.report).write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('PARITY PASS' if report['pass'] else 'PARITY FAIL', 'report=', args.report)
    sys.exit(0 if report['pass'] else 2)


if __name__ == '__main__':
    main()
