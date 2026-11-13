"""V9.32-only exact streaming cache for its V4.x trendline event detector.

Only the expensive trendline *event scan* is advanced one closed candle at a
 time. This is not a native V9.32 strategy or broker-order parity approval:
 other V8/V9 features still rebuild the retained candle vectors.

Never use cached results after a gap, rewind, parameter mutation or source
 mismatch. The caller remains responsible for the complete signal semantics.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
import json
from typing import Any

import numpy as np
import pandas as pd

from . import v932_pinned_strategy as frozen

_ORIGINAL_DETECTOR = frozen.detect_trendline_events
_ACTIVE: ContextVar["TrendlineCache | None"] = ContextVar('v932_trendline_cache', default=None)


def activate(cache: "TrendlineCache"):
    return _ACTIVE.set(cache)


def deactivate(token) -> None:
    _ACTIVE.reset(token)


@dataclass
class _EventState:
    params: dict
    dates: list = field(default_factory=list)
    opens: list = field(default_factory=list)
    highs: list = field(default_factory=list)
    lows: list = field(default_factory=list)
    closes: list = field(default_factory=list)
    true_ranges: list = field(default_factory=list)
    atrs: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    last: dict = field(default_factory=lambda: {'SHORT': None, 'LONG': None})
    events: list = field(default_factory=list)
    anchors: list = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.dates)

    def _accept(self, date: Any, o: float, h: float, l: float, c: float):
        i = self.size
        o, h, l, c = float(o), float(h), float(l), float(c)
        old_close = self.closes[-1] if i else float('nan')
        tr = max(h-l, abs(h-old_close), abs(l-old_close)) if i else h-l
        self.true_ranges.append(tr)
        period = int(self.params['atr_period'])
        av = float(np.mean(self.true_ranges[-period:])) if i+1 >= period else float('nan')
        self.atrs.append(av)
        self.dates.append(date)
        self.opens.append(o); self.highs.append(h); self.lows.append(l); self.closes.append(c)
        lines = self.lines
        if pd.notna(av) and av > 0 and i > 0:
            retained = []
            for line in lines:
                if line['invalidated']:
                    continue
                age = i-line['confirmed_index']
                if age > self.params['max_line_age']:
                    continue
                side = line['direction']
                price = line['anchor2_price']+line['slope']*(i-line['anchor2_index'])
                band = self.params['touch_band_atr']*av
                reset = self.params['reset_distance_atr']*av
                if side == 'SHORT':
                    away = h < price-band-reset
                    overlap = h >= price-band and l <= price+band
                    broken = c > price+self.params['invalidate_close_atr']*av
                    rejected = c < price-band
                else:
                    away = l > price+band+reset
                    overlap = l <= price+band and h >= price-band
                    broken = c < price-self.params['invalidate_close_atr']*av
                    rejected = c > price+band
                if broken:
                    line['invalidated'] = True
                    line['invalidated_index'] = i
                    continue
                if away:
                    line['armed'] = True
                if overlap and line['armed']:
                    line['touches'] += 1
                    line['armed'] = False
                    cf = frozen.candle_features(o,h,l,c,self.opens[i-1],self.closes[i-1],av,self.params['tick_size'])
                    self.events.append(dict(
                        event_id=f"{line['line_id']}:{i}",index=i,timestamp=str(date), direction=side,
                        line_id=line['line_id'],anchor1_index=line['anchor1_index'],
                        anchor2_index=line['anchor2_index'],anchor1_time=str(self.dates[line['anchor1_index']]),
                        anchor2_time=str(self.dates[line['anchor2_index']]),
                        anchor1_price=line['anchor1_price'],anchor2_price=line['anchor2_price'],
                        anchor2_confirm_time=str(self.dates[line['confirmed_index']]),confirmed_index=line['confirmed_index'],
                        slope_price_per_bar=line['slope'],slope_atr=line['slope_atr'],line_price=price,atr=av,
                        touch_number=line['touches'],line_age_bars=age,distance_close_atr=(c-price)/av,
                        state='REJECTION' if rejected else 'TOUCH',**cf))
                retained.append(line)
            lines[:] = retained
        j = i-int(self.params['right'])
        if j < int(self.params['left']) or j < 0:
            return
        for side,v,arr in [('SHORT',self.highs[j],self.highs),('LONG',self.lows[j],self.lows)]:
            left=arr[j-self.params['left']:j]
            right=arr[j+1:i+1]
            yes = v>max(left) and v>=max(right) if side=='SHORT' else v<min(left) and v<=min(right)
            if not yes:
                continue
            anchor={'direction':side,'index':j,'time':str(self.dates[j]),'price':float(v),
                    'confirmed_index':i,'confirmed_time':str(date)}
            self.anchors.append(anchor)
            a=self.last[side]; self.last[side]=anchor
            if a is None or not pd.notna(self.atrs[j]) or self.atrs[j]<=0:
                continue
            sep=j-a['index']
            if sep<self.params['min_anchor_separation'] or sep>self.params['max_anchor_separation']:
                continue
            slope=(float(v)-a['price'])/sep
            slope_atr=slope/self.atrs[j]
            if side=='SHORT' and slope_atr>=-self.params['min_abs_slope_atr']:
                continue
            if side=='LONG' and slope_atr<=self.params['min_abs_slope_atr']:
                continue
            line_id=f"TL-{side}-{a['index']:07d}-{j:07d}"
            lines.append(dict(line_id=line_id,direction=side,anchor1_index=a['index'],
                              anchor1_price=a['price'],anchor2_index=j,anchor2_price=float(v),
                              confirmed_index=i,slope=slope,slope_atr=slope_atr,touches=2,armed=False,invalidated=False))

    def init(self, df: pd.DataFrame):
        for dt, o,h,l,c in zip(df.Date.tolist(),df.Open.to_numpy(),df.High.to_numpy(),
                              df.Low.to_numpy(),df.Close.to_numpy()):
            self._accept(dt,o,h,l,c)

    def extend(self, df: pd.DataFrame):
        if len(df)!=self.size+1:
            raise ValueError('Unexpected row count for trendline cache')
        row=df.iloc[-1]
        if pd.Timestamp(df.iloc[-2]['Date']) != pd.Timestamp(self.dates[-1]):
            raise ValueError('Trendline cache prefix time changed')
        if not np.isclose(float(df.iloc[-2]['Close']), self.closes[-1],rtol=0,atol=1e-9):
            raise ValueError('Trendline cache prefix price changed')
        if pd.Timestamp(row.Date) <= pd.Timestamp(self.dates[-1]):
            raise ValueError('Trendline cache timestamp not advancing')
        self._accept(row.Date,row.Open,row.High,row.Low,row.Close)

    def result(self):
        return pd.DataFrame(self.events),pd.DataFrame(self.anchors)


class TrendlineCache:
    def __init__(self):
        self._states: dict[str,_EventState]={}
        self.reset_count=0

    def detect(self, df:pd.DataFrame, params:dict|None=None):
        p={**frozen.DEFAULTS,**(params or {})}
        key=json.dumps(p,sort_keys=True,default=str)
        state=self._states.get(key)
        if state is None:
            state=_EventState(p);state.init(df);self._states[key]=state
        elif len(df)==state.size+1:
            try:
                state.extend(df)
            except (ValueError,TypeError):
                state=_EventState(p);state.init(df);self._states[key]=state;self.reset_count+=1
        elif (len(df)!=state.size or df.empty
              or pd.Timestamp(df.iloc[-1].Date)!=pd.Timestamp(state.dates[-1])
              or any(not np.isclose(float(df.iloc[-1][col]), vals[-1], rtol=0, atol=1e-9)
                     for col,vals in [('Open',state.opens),('High',state.highs),
                                      ('Low',state.lows),('Close',state.closes)])):
            state=_EventState(p);state.init(df);self._states[key]=state;self.reset_count+=1
        return state.result()


def _dispatch_detector(df, params=None):
    cache=_ACTIVE.get()
    if cache is None:
        return _ORIGINAL_DETECTOR(df, params)
    return cache.detect(df,params)


# This is a backend-local wrapper, and only runs in the V9.32 hybrid context.
# All other callers see the original function. ContextVar isolates concurrent
# execution without a process-global mutable active strategy pointer.
if frozen.detect_trendline_events is not _dispatch_detector:
    frozen.detect_trendline_events=_dispatch_detector

# V9.33's Gold causal research fork uses the exact same trendline detector.
# Reuse the cache only if source-level implementation text is identical.
# A future revised detector must opt in only after independent parity tests.
try:
    from . import v933_causal_pinned_strategy as _v933
    import inspect as _inspect
    if _inspect.getsource(_v933.detect_trendline_events) == _inspect.getsource(_ORIGINAL_DETECTOR) and _v933.DEFAULTS == frozen.DEFAULTS:
        _v933.detect_trendline_events = _dispatch_detector
except (ImportError, AttributeError, OSError):
    pass
