"""NAS100/USTECH M5 V1.8 historical RESEARCH ONLY — single-file AlgoAgentX strategy.

Generated from archived V1.1 -> V1.2 -> V1.4 -> V1.5 -> V1.6 -> V1.7 -> V1.8
without changing strategy calculation rules, constants, thresholds, or parameters.
The source is self-contained except numpy and pandas. Do NOT use for live orders
without native AlgoAgentX validation and broker-cost verification.
"""

from __future__ import annotations

import numpy as np

import pandas as pd


# ===== START FROZEN MODULE: NAS100_M5_V1_1.py =====

_v11core_VERSION = 'NAS100_M5_V1_1_RESEARCH_ONLY'

class _v11core_NAS100M5V11:
    LIVE_HISTORY_BARS = 80000

    def __init__(self, df, *, family='sweep', level='rolling48', atr_buffer=0.12, sweep_depth=0.08, close_quality=0.65, body_atr=0.22, rr=2.0, stop_atr_max=4.0, trend='none', session='all', volume_min=0.0, cooldown=6, **kwargs):
        self.df = df
        self.params = dict(family=family, level=level, atr_buffer=atr_buffer, sweep_depth=sweep_depth, close_quality=close_quality, body_atr=body_atr, rr=rr, stop_atr_max=stop_atr_max, trend=trend, session=session, volume_min=volume_min, cooldown=cooldown)

    def generate(self):
        d = self.df.copy().reset_index(drop=True)
        rename = {k: k.title() for k in ['open', 'high', 'low', 'close', 'volume'] if k in d.columns}
        if 'timestamp' in d.columns:
            rename['timestamp'] = 'Date'
        d = d.rename(columns=rename)
        for col in ('Date', 'Open', 'High', 'Low', 'Close'):
            if col not in d:
                raise ValueError('Missing ' + col)
        d['Date'] = pd.to_datetime(d['Date'], utc=True).dt.tz_localize(None)
        if not d.Date.is_monotonic_increasing or d.Date.duplicated().any():
            raise ValueError('Dates not sorted/unique')
        o, h, l, c = [d[k].to_numpy(float) for k in ('Open', 'High', 'Low', 'Close')]
        if (h < np.maximum(o, c)).any() or (l > np.minimum(o, c)).any():
            raise ValueError('Bad OHLC')
        n = len(d)
        p = self.params
        pc = np.r_[c[0], c[:-1]]
        tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
        ema20 = pd.Series(c).ewm(span=20, adjust=False).mean().to_numpy(float)
        ema50 = pd.Series(c).ewm(span=50, adjust=False).mean().to_numpy(float)
        if p['level'].startswith('rolling'):
            length = int(p['level'][7:])
            high = pd.Series(h).shift(1).rolling(length, min_periods=length).max().to_numpy(float)
            low = pd.Series(l).shift(1).rolling(length, min_periods=length).min().to_numpy(float)
        elif p['level'] == 'prevday':
            key = d.Date.dt.floor('D')
            grouped = pd.DataFrame({'key': key, 'hi': h, 'lo': l}).groupby('key').agg(hi=('hi', 'max'), lo=('lo', 'min')).shift(1)
            high = grouped.hi.reindex(key).to_numpy(float)
            low = grouped.lo.reindex(key).to_numpy(float)
        else:
            raise ValueError('Unknown level')
        span = np.maximum(h - l, 1e-10)
        bullclose = (c - l) / span
        bearclose = (h - c) / span
        up = (c > o) & (c - o >= p['body_atr'] * atr) & (bullclose >= p['close_quality'])
        dn = (c < o) & (o - c >= p['body_atr'] * atr) & (bearclose >= p['close_quality'])
        if p['family'] == 'sweep':
            up &= (l < low - p['sweep_depth'] * atr) & (c > low + p['atr_buffer'] * atr)
            dn &= (h > high + p['sweep_depth'] * atr) & (c < high - p['atr_buffer'] * atr)
            sl = np.minimum(l, low) - 0.15 * atr
            ss = np.maximum(h, high) + 0.15 * atr
        elif p['family'] == 'breakout':
            up &= (pc <= high + 0.1 * atr) & (c > high + p['atr_buffer'] * atr)
            dn &= (pc >= low - 0.1 * atr) & (c < low - p['atr_buffer'] * atr)
            sl = np.minimum(l, high - 0.75 * atr) - 0.15 * atr
            ss = np.maximum(h, low + 0.75 * atr) + 0.15 * atr
        elif p['family'] == 'retest':
            highprev = np.r_[np.nan, high[:-1]]
            lowprev = np.r_[np.nan, low[:-1]]
            up &= (pc > highprev + 0.06 * atr) & (l <= high + 0.15 * atr) & (c > high + 0.08 * atr)
            dn &= (pc < lowprev - 0.06 * atr) & (h >= low - 0.15 * atr) & (c < low - 0.08 * atr)
            sl = np.minimum(l, high - 0.75 * atr) - 0.15 * atr
            ss = np.maximum(h, low + 0.75 * atr) + 0.15 * atr
        else:
            raise ValueError('Unknown family')
        if p['trend'] == 'ema':
            up &= ema20 > ema50
            dn &= ema20 < ema50
        elif p['trend'] == 'counter':
            up &= ema20 < ema50
            dn &= ema20 > ema50
        elif p['trend'] != 'none':
            raise ValueError('Unknown trend')
        if p['session'] != 'all':
            ny = d.Date.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
            hh = ny.dt.hour.to_numpy()
            mm = ny.dt.minute.to_numpy()
            nymins = hh * 60 + mm
            if p['session'] == 'ny':
                allowed = (nymins >= 570) & (nymins < 960)
            elif p['session'] == 'open':
                allowed = (nymins >= 570) & (nymins < 690)
            else:
                raise ValueError('Unknown session')
            up &= allowed
            dn &= allowed
        if p['volume_min'] > 0:
            if 'Volume' not in d:
                raise ValueError('volume missing')
            vol = d.Volume.to_numpy(float)
            vmean = pd.Series(vol).shift(1).rolling(24, min_periods=24).mean().to_numpy(float)
            good = vol / np.maximum(vmean, 1) >= p['volume_min']
            up &= good
            dn &= good
        rl = c - sl
        rs = ss - c
        up &= np.isfinite(rl) & (rl >= 0.2 * atr) & (rl <= p['stop_atr_max'] * atr)
        dn &= np.isfinite(rs) & (rs >= 0.2 * atr) & (rs <= p['stop_atr_max'] * atr)
        overlap = up & dn
        pos = np.where(up & ~overlap, 1, np.where(dn & ~overlap, -1, 0)).astype(np.int8)
        if p['cooldown'] > 0:
            last = -100000
            for k in np.flatnonzero(pos):
                if k - last < p['cooldown']:
                    pos[k] = 0
                else:
                    last = k
        stops = np.where(pos > 0, sl, np.where(pos < 0, ss, np.nan))
        target = np.where(pos != 0, c + pos * p['rr'] * abs(c - stops), np.nan)
        d['Position'] = pos
        d['strategy_stop_loss'] = stops
        d['strategy_target'] = target
        d['signal_reason'] = np.where(pos != 0, _v11core_VERSION + '|' + p['family'] + '|' + p['level'], '')
        d.attrs['strategy_diagnostics'] = {'version': _v11core_VERSION, 'live_approved': False, 'research_only': True, 'parameters': p}
        return d
_v11core_Strategy = _v11core_NAS100M5V11

# ===== END FROZEN MODULE: NAS100_M5_V1_1.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_1_SELECTED_RESEARCH_ONLY.py =====

class _v11selected_NAS100M5V11Selected(_v11core_NAS100M5V11):
    LIVE_HISTORY_BARS = 80000

    def __init__(self, df, **kwargs):
        fixed = dict(family='retest', level='rolling48', trend='none', session='ny', rr=3.0, close_quality=0.7)
        for name, value in fixed.items():
            if name in kwargs and kwargs[name] != value:
                raise ValueError(f'Frozen NAS100 V1.1 research parameter {name}: {value}')
        super().__init__(df, **{**kwargs, **fixed})
_v11selected_Strategy = _v11selected_NAS100M5V11Selected

# ===== END FROZEN MODULE: NAS100_M5_V1_1_SELECTED_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_2_FILTER_CANDIDATE_RESEARCH_ONLY.py =====

_v12_VERSION = 'NAS100_M5_V1_2_NY_TIME_WEEKDAY_FILTER_RESEARCH_ONLY'

class _v12_NAS100M5V12Diagnostic(_v11selected_NAS100M5V11Selected):
    LIVE_HISTORY_BARS = 80000

    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)

    def generate(self):
        result = super().generate()
        dates = pd.to_datetime(result['Date'], utc=True).dt.tz_convert('America/New_York')
        minutes = dates.dt.hour.to_numpy() * 60 + dates.dt.minute.to_numpy()
        allowed = (minutes >= 570) & (minutes < 870) & (dates.dt.dayofweek.to_numpy() != 0)
        original = result['Position'].to_numpy(dtype=np.int8).copy()
        removed = (original != 0) & ~allowed
        for col in ('strategy_stop_loss', 'strategy_target'):
            result.loc[removed, col] = np.nan
        result.loc[removed, 'Position'] = 0
        result.loc[removed, 'signal_reason'] = _v12_VERSION + '|FILTERED'
        assert np.all((result['Position'].to_numpy() == 0) | (result['Position'].to_numpy() == original))
        result.attrs['strategy_diagnostics'] = {'version': _v12_VERSION, 'frozen_parent': 'NAS100_M5_V1_1', 'filter_only': True, 'added_signal_intents': 0, 'vetoed_signal_intents': int(removed.sum()), 'research_only': True, 'native_engine_verified': False, 'live_approved': False, 'time_filter': 'America/New_York 09:30 inclusive to 14:30 exclusive', 'weekday_filter': 'Exclude Mondays', 'warning': 'Historical selection over 489 configurations; holdout weak, drawdown high.'}
        return result
_v12_Strategy = _v12_NAS100M5V12Diagnostic

# ===== END FROZEN MODULE: NAS100_M5_V1_2_FILTER_CANDIDATE_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: nas100_v14_entries.py =====

_v14bank_FAMILY_NAMES = tuple((f'{style}_{level}' for level in ('rolling12', 'rolling24', 'rolling48', 'rolling96', 'prevday', 'ny_orb') for style in ('sweep', 'reclaim', 'retest')))
_v14bank_SESSIONS = ((570, 690), (570, 750), (570, 870), (630, 870), (690, 960), (570, 960))
_v14bank_BODY = (0.0, 0.15, 0.3, 0.5, 0.7)
_v14bank_CLOSE = (0.52, 0.6, 0.68, 0.76, 0.84)
_v14bank_VOL = (0.0, 0.55, 0.9, 1.25)
_v14bank_ATR_REL = (0.0, 0.65, 0.9, 1.15, 1.5)
_v14bank_STOP_ATR = (1.0, 1.5, 2.0, 3.0, 4.5)
_v14bank_TRENDS = ('none', 'ema', 'h1')
_v14bank_SIDES = ('both', 'long', 'short')

def _v14bank_make_bank(frame):
    d = frame
    o, h, l, c = (d[k].to_numpy(dtype=float) for k in ('Open', 'High', 'Low', 'Close'))
    times = pd.to_datetime(d['Date'], utc=True)
    ny = times.dt.tz_convert('America/New_York')
    minute = (ny.dt.hour.to_numpy() * 60 + ny.dt.minute.to_numpy()).astype(np.int32)
    dow = ny.dt.dayofweek.to_numpy(np.int8)
    day = ny.dt.strftime('%Y-%m-%d').to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    relatr = atr / np.maximum(pd.Series(atr).shift(1).rolling(288, min_periods=144).median().to_numpy(float), 1e-08)
    ema20 = pd.Series(c).ewm(span=20, adjust=False).mean().to_numpy(float)
    ema50 = pd.Series(c).ewm(span=50, adjust=False).mean().to_numpy(float)
    vol = d['Volume'].to_numpy(float)
    volume = vol / np.maximum(pd.Series(vol).shift(1).rolling(24, min_periods=12).mean().to_numpy(float), 1.0)
    body = np.abs(c - o) / np.maximum(atr, 1e-08)
    upquality = (c - l) / np.maximum(h - l, 1e-08)
    downquality = (h - c) / np.maximum(h - l, 1e-08)
    ht = d.set_index(times)[['Open', 'High', 'Low', 'Close']].resample('1h', label='left', closed='left').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    counts = d.set_index(times)['Close'].resample('1h', label='left', closed='left').count()
    ht = ht[counts == 12].copy()
    Hc = ht['Close'].to_numpy(float)
    Hema20 = pd.Series(Hc).ewm(span=20, adjust=False).mean().to_numpy(float)
    Hema50 = pd.Series(Hc).ewm(span=50, adjust=False).mean().to_numpy(float)
    available = (ht.index + pd.Timedelta(hours=1)).tz_localize(None).to_numpy(dtype='datetime64[ns]')
    close_t = (times.dt.tz_convert('UTC').dt.tz_localize(None) + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    ix = np.searchsorted(available, close_t, side='right') - 1
    h1up = np.zeros(len(c), dtype=bool)
    h1down = h1up.copy()
    ok = ix >= 0
    h1up[ok] = Hema20[ix[ok]] > Hema50[ix[ok]]
    h1down[ok] = Hema20[ix[ok]] < Hema50[ix[ok]]
    levels = {}
    for w in (12, 24, 48, 96):
        hi = pd.Series(h).shift(1).rolling(w, min_periods=w).max().to_numpy(float)
        lo = pd.Series(l).shift(1).rolling(w, min_periods=w).min().to_numpy(float)
        levels[f'rolling{w}'] = (hi, lo)
    utcday = times.dt.floor('D')
    grouped = pd.DataFrame({'day': utcday, 'high': h, 'low': l}).groupby('day', sort=True).agg(hi=('high', 'max'), lo=('low', 'min')).shift(1)
    levels['prevday'] = (grouped['hi'].reindex(utcday).to_numpy(float), grouped['lo'].reindex(utcday).to_numpy(float))
    mask = (minute >= 570) & (minute < 600)
    grp = pd.DataFrame({'day': day[mask], 'h': h[mask], 'l': l[mask]}).groupby('day', sort=False).agg(hi=('h', 'max'), lo=('l', 'min'), count=('h', 'size'))
    j = pd.Index(day)
    orbhi = grp.hi.reindex(j).to_numpy(float)
    orblo = grp.lo.reindex(j).to_numpy(float)
    cnt = grp['count'].reindex(j).fillna(0).to_numpy(int)
    orbhi[(minute < 600) | (cnt < 6)] = np.nan
    orblo[(minute < 600) | (cnt < 6)] = np.nan
    levels['ny_orb'] = (orbhi, orblo)
    return {'o': o, 'h': h, 'l': l, 'c': c, 'pc': np.r_[np.nan, c[:-1]], 'atr': atr, 'atrrel': relatr, 'volume': volume, 'body': body, 'uq': upquality, 'dq': downquality, 'ema_up': ema20 > ema50, 'ema_down': ema20 < ema50, 'h1_up': h1up, 'h1_down': h1down, 'minute': minute, 'dow': dow, 'levels': levels}

def _v14bank_family_raw(bank, name):
    kind, level = name.split('_', 1)
    f = bank
    o, h, l, c, pc, atr = (f[k] for k in ('o', 'h', 'l', 'c', 'pc', 'atr'))
    hi, lo = f['levels'][level]
    if kind == 'sweep':
        up = (l < lo - 0.04 * atr) & (c > lo + 0.04 * atr)
        down = (h > hi + 0.04 * atr) & (c < hi - 0.04 * atr)
        sl = np.minimum(l, lo) - 0.14 * atr
        ss = np.maximum(h, hi) + 0.14 * atr
    elif kind == 'reclaim':
        up = (pc < lo + 0.18 * atr) & (l <= lo + 0.12 * atr) & (c > lo + 0.24 * atr)
        down = (pc > hi - 0.18 * atr) & (h >= hi - 0.12 * atr) & (c < hi - 0.24 * atr)
        sl = np.minimum(l, lo) - 0.14 * atr
        ss = np.maximum(h, hi) + 0.14 * atr
    elif kind == 'retest':
        oldhi = np.r_[np.nan, hi[:-1]]
        oldlo = np.r_[np.nan, lo[:-1]]
        up = (pc > oldhi + 0.04 * atr) & (l <= hi + 0.16 * atr) & (c > hi + 0.08 * atr)
        down = (pc < oldlo - 0.04 * atr) & (h >= lo - 0.16 * atr) & (c < lo - 0.08 * atr)
        sl = np.minimum(l, hi - 0.75 * atr) - 0.14 * atr
        ss = np.maximum(h, lo + 0.75 * atr) + 0.14 * atr
    else:
        raise ValueError(name)
    up &= c > o
    down &= c < o
    up &= np.isfinite(sl) & np.isfinite(atr) & (c - sl >= 0.2 * atr) & (c - sl <= 5.0 * atr)
    down &= np.isfinite(ss) & np.isfinite(atr) & (ss - c >= 0.2 * atr) & (ss - c <= 5.0 * atr)
    clash = up & down
    pos = np.where(up & ~clash, 1, np.where(down & ~clash, -1, 0)).astype(np.int8)
    stop = np.where(pos > 0, sl, np.where(pos < 0, ss, np.nan))
    return (pos, stop)

def _v14bank_intent_for_config(bank, name, side, session, body, close, vol, atr_rel, stop_atr, trend, warmup=80000):
    raw, stop = _v14bank_family_raw(bank, name)
    f = bank
    c, atr = (f[k] for k in ('c', 'atr'))
    minute = f['minute']
    lo, hi = session
    keep = (np.arange(len(raw)) >= warmup) & (minute >= lo) & (minute < hi) & (f['dow'] < 5)
    if side == 'long':
        keep &= raw > 0
    elif side == 'short':
        keep &= raw < 0
    keep &= f['body'] >= body
    keep &= np.where(raw > 0, f['uq'], f['dq']) >= close
    keep &= f['volume'] >= vol
    keep &= f['atrrel'] >= atr_rel
    keep &= np.abs(c - stop) / np.maximum(atr, 1e-09) <= stop_atr
    if trend == 'ema':
        keep &= np.where(raw > 0, f['ema_up'], f['ema_down'])
    elif trend == 'h1':
        keep &= np.where(raw > 0, f['h1_up'], f['h1_down'])
    pos = np.where(keep, raw, 0).astype(np.int8)
    st = np.where(pos != 0, stop, np.nan)
    return (pos, st)

# ===== END FROZEN MODULE: nas100_v14_entries.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_4_NEW_ENTRY_RESEARCH_ONLY.py =====

_v14_VERSION = 'NAS100_M5_V1_4_NY_ORB_RECLAIM_RESEARCH_ONLY'
_v14_CONFIG = {'family': 'reclaim_ny_orb', 'side': 'long', 'session': (570, 690), 'body': 0.3, 'close': 0.6, 'volume': 1.25, 'atr_rel': 0.9, 'stop_atr': 2.0, 'trend': 'none'}

class _v14_NAS100M5V14NewEntriesResearch(_v12_NAS100M5V12Diagnostic):
    LIVE_HISTORY_BARS = 80000

    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)

    def generate(self):
        out = super().generate()
        ctx = _v14bank_make_bank(out)
        p, stop = _v14bank_intent_for_config(ctx, _v14_CONFIG['family'], _v14_CONFIG['side'], _v14_CONFIG['session'], _v14_CONFIG['body'], _v14_CONFIG['close'], _v14_CONFIG['volume'], _v14_CONFIG['atr_rel'], _v14_CONFIG['stop_atr'], _v14_CONFIG['trend'], self.LIVE_HISTORY_BARS)
        old = out['Position'].to_numpy(np.int8).copy()
        new = (old == 0) & (p != 0)
        out.loc[new, 'Position'] = p[new]
        out.loc[new, 'strategy_stop_loss'] = stop[new]
        close = ctx['c']
        target = close + p * 3.0 * np.abs(close - stop)
        out.loc[new, 'strategy_target'] = target[new]
        out.loc[new, 'signal_reason'] = _v14_VERSION + '|NEW_ENTRY|' + _v14_CONFIG['family']
        out.attrs['strategy_diagnostics'] = {'version': _v14_VERSION, 'frozen_baseline': 'NAS100_M5_V1_2', 'new_signal_intents': int(new.sum()), 'parameters': dict(_v14_CONFIG), 'baseline_signal_intents_preserved': True, 'live_approved': False, 'research_only': True, 'native_engine_verified': False, 'warning': '2026 history previously examined; independent forward validation required.'}
        return out
_v14_Strategy = _v14_NAS100M5V14NewEntriesResearch

# ===== END FROZEN MODULE: NAS100_M5_V1_4_NEW_ENTRY_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: nas100_v15_entries.py =====

_v15bank_FAMILY_NAMES = ('h1_ema_reclaim', 'h4_ema_reclaim', 'm15_bos_retest', 'm15_fvg_mitigation', 'prevweek_q25_reclaim', 'prevweek_q75_reclaim', 'prevweek_edges_sweep', 'prevday_mid_reclaim', 'vwap_reclaim', 'bollinger_reversal', 'rsi_trend_pullback', 'm5_engulf_supply_demand', 'h1_extreme_sweep', 'm15_compression_release', 'stoch_trend_reversal', 'ema50_momentum_pullback', 'm30_ema_retest', 'prevweek_mid_retest')
_v15bank_SESSIONS = ((570, 690), (570, 750), (570, 870), (630, 870), (690, 960), (570, 960))
_v15bank_BODY = (0.0, 0.15, 0.3, 0.5, 0.7)
_v15bank_CLOSE = (0.52, 0.6, 0.68, 0.76, 0.84)
_v15bank_VOL = (0.0, 0.55, 0.9, 1.25)
_v15bank_ATR_REL = (0.0, 0.65, 0.9, 1.15, 1.5)
_v15bank_STOP_ATR = (1.0, 1.5, 2.0, 3.0, 4.5)
_v15bank_TRENDS = ('none', 'ema', 'h1')
_v15bank_SIDES = ('both', 'long', 'short')

def _v15bank_lag_roll(v, n, mode):
    s = pd.Series(v).shift(1).rolling(n, min_periods=n)
    return (s.max() if mode == 'hi' else s.min()).to_numpy(float)

def _v15bank_htf_projection(d, rule, expected, min_delta, m5_close):
    dat = d.set_index('Date')
    a = dat[['Open', 'High', 'Low', 'Close']].resample(rule, label='left', closed='left').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    cnt = dat.Close.resample(rule, label='left', closed='left').count().to_numpy()
    a = a[cnt == expected].copy()
    if a.empty:
        raise ValueError('No complete ' + rule + ' bars')
    cc = a.Close.to_numpy(float)
    hh = a.High.to_numpy(float)
    ll = a.Low.to_numpy(float)
    a['e20'] = pd.Series(cc).ewm(span=20, adjust=False).mean().to_numpy(float)
    a['e50'] = pd.Series(cc).ewm(span=50, adjust=False).mean().to_numpy(float)
    a['hi12'] = _v15bank_lag_roll(hh, 12, 'hi')
    a['lo12'] = _v15bank_lag_roll(ll, 12, 'lo')
    a['atr'] = pd.Series(np.maximum(hh - ll, np.maximum(abs(hh - np.r_[cc[0], cc[:-1]]), abs(ll - np.r_[cc[0], cc[:-1]])))).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    available = (a.index + pd.Timedelta(minutes=min_delta)).to_numpy(dtype='datetime64[ns]')
    ids = np.searchsorted(available, m5_close, side='right') - 1
    out = {}
    for col in ('e20', 'e50', 'hi12', 'lo12', 'atr', 'Close', 'High', 'Low'):
        x = a[col].to_numpy(float)
        out[col] = np.full(len(ids), np.nan)
        good = ids >= 0
        out[col][good] = x[ids[good]]
    out['up'] = (out['e20'] > out['e50']) & (out['Close'] > out['e20'])
    out['dn'] = (out['e20'] < out['e50']) & (out['Close'] < out['e20'])
    return (a, out, ids, available)

def _v15bank_last_event(a, ids, available, flag, edge, m5close, ttl_bars):
    flags = np.asarray(flag, dtype=bool)
    indices = np.where(flags, np.arange(len(flags)), -1)
    indices = np.maximum.accumulate(indices)
    origin = np.full(len(ids), -1, np.int64)
    eligible = ids >= 0
    origin[eligible] = indices[ids[eligible]]
    val = np.full(len(ids), np.nan)
    good = origin >= 0
    if good.any():
        index = np.flatnonzero(good)
        fresh = ids[index] - origin[index] <= ttl_bars
        index = index[fresh]
        val[index] = np.asarray(edge, dtype=float)[origin[index]]
    return val

def _v15bank_make_bank(d):
    f = _v14bank_make_bank(d)
    n = len(d)
    c = f['c']
    o = f['o']
    h = f['h']
    l = f['l']
    atr = np.maximum(f['atr'], 1e-10)
    dt = pd.to_datetime(d['Date'], utc=True).dt.tz_localize(None)
    close_t = (dt + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    m15, m15p, i15, t15 = _v15bank_htf_projection(d, '15min', 3, 15, close_t)
    h1, h1p, ih1, th1 = _v15bank_htf_projection(d, '1h', 12, 60, close_t)
    h4, h4p, ih4, th4 = _v15bank_htf_projection(d, '4h', 48, 240, close_t)
    m30, m30p, i30, t30 = _v15bank_htf_projection(d, '30min', 6, 30, close_t)
    f['m15'] = m15p
    f['h1'] = h1p
    f['h4'] = h4p
    f['m30'] = m30p
    mo = m15.Open.to_numpy(float)
    mh = m15.High.to_numpy(float)
    ml = m15.Low.to_numpy(float)
    mc = m15.Close.to_numpy(float)
    ma = m15.atr.to_numpy(float)
    bosu = (mc > m15.hi12.to_numpy(float) + 0.1 * ma) & (mc > mo)
    bosd = (mc < m15.lo12.to_numpy(float) - 0.1 * ma) & (mc < mo)
    f['m15_bos_up'] = _v15bank_last_event(m15, i15, t15, bosu, m15.hi12.to_numpy(float), close_t, 8)
    f['m15_bos_dn'] = _v15bank_last_event(m15, i15, t15, bosd, m15.lo12.to_numpy(float), close_t, 8)
    gapu = np.r_[False, False, ml[2:] > mh[:-2] + 0.04 * ma[2:]]
    gapd = np.r_[False, False, mh[2:] < ml[:-2] - 0.04 * ma[2:]]
    gu = np.r_[np.nan, np.nan, mh[:-2]]
    gd = np.r_[np.nan, np.nan, ml[:-2]]
    f['m15_fvg_up'] = _v15bank_last_event(m15, i15, t15, gapu, gu, close_t, 12)
    f['m15_fvg_dn'] = _v15bank_last_event(m15, i15, t15, gapd, gd, close_t, 12)
    pastwidth = pd.Series(mh).shift(1).rolling(8, min_periods=8).max() - pd.Series(ml).shift(1).rolling(8, min_periods=8).min()
    compact = pastwidth.to_numpy(float) / np.maximum(ma, 1e-09) < 3.8
    f['m15_comp_up'] = _v15bank_last_event(m15, i15, t15, compact & (mc > m15.hi12.to_numpy(float)), m15.hi12.to_numpy(float), close_t, 3)
    f['m15_comp_dn'] = _v15bank_last_event(m15, i15, t15, compact & (mc < m15.lo12.to_numpy(float)), m15.lo12.to_numpy(float), close_t, 3)
    week = dt.dt.to_period('W-SUN')
    g = pd.DataFrame({'week': week, 'h': h, 'l': l}).groupby('week', sort=True).agg(hi=('h', 'max'), lo=('l', 'min'), n=('h', 'size')).shift(1)
    prev_hi = g.hi.reindex(week).to_numpy(float)
    prev_lo = g.lo.reindex(week).to_numpy(float)
    full = g.n.reindex(week).fillna(0).to_numpy(int) >= 500
    f['week_hi'] = np.where(full, prev_hi, np.nan)
    f['week_lo'] = np.where(full, prev_lo, np.nan)
    f['week_q25'] = prev_lo + 0.25 * (prev_hi - prev_lo)
    f['week_q75'] = prev_lo + 0.75 * (prev_hi - prev_lo)
    f['week_mid'] = (prev_hi + prev_lo) / 2
    dkey = dt.dt.floor('D')
    gp = pd.DataFrame({'day': dkey, 'h': h, 'l': l}).groupby('day', sort=True).agg(hi=('h', 'max'), lo=('l', 'min')).shift(1)
    f['prevday_mid'] = ((gp.hi + gp.lo) * 0.5).reindex(dkey).to_numpy(float)
    nyday = dt.dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
    v = pd.to_numeric(d.Volume, errors='coerce').to_numpy(float)
    cumvol = pd.Series(v).groupby(nyday, sort=False).cumsum().to_numpy(float)
    cumpv = pd.Series(v * (h + l + c) / 3).groupby(nyday, sort=False).cumsum().to_numpy(float)
    f['vwap'] = cumpv / np.maximum(cumvol, 1.0)
    f['prev_vwap'] = np.r_[np.nan, f['vwap'][:-1]]
    f['ema20'] = pd.Series(c).ewm(span=20, adjust=False).mean().to_numpy(float)
    f['ema50'] = pd.Series(c).ewm(span=50, adjust=False).mean().to_numpy(float)
    f['high12'] = _v15bank_lag_roll(h, 12, 'hi')
    f['low12'] = _v15bank_lag_roll(l, 12, 'lo')
    f['high24'] = _v15bank_lag_roll(h, 24, 'hi')
    f['low24'] = _v15bank_lag_roll(l, 24, 'lo')
    s = pd.Series(c).shift(1).rolling(20, min_periods=20)
    f['bb_mid'] = s.mean().to_numpy(float)
    std = s.std(ddof=0).to_numpy(float)
    f['bb_low'] = f['bb_mid'] - 2 * std
    f['bb_hi'] = f['bb_mid'] + 2 * std
    change = np.r_[0, np.diff(c)]
    up = pd.Series(np.maximum(change, 0)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    dn = pd.Series(np.maximum(-change, 0)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    f['rsi'] = 100 * up / np.maximum(up + dn, 1e-10)
    high14 = pd.Series(h).rolling(14, min_periods=14).max().to_numpy(float)
    low14 = pd.Series(l).rolling(14, min_periods=14).min().to_numpy(float)
    stoch = (c - low14) / np.maximum(high14 - low14, 1e-10) * 100
    f['stoch'] = stoch
    f['pc2'] = np.r_[np.nan, np.nan, c[:-2]]
    f['po1'] = np.r_[np.nan, o[:-1]]
    f['highprev'] = np.r_[np.nan, h[:-1]]
    f['lowprev'] = np.r_[np.nan, l[:-1]]
    return f

def _v15bank_family_raw(f, name):
    o, h, l, c, pc, atr = (f[k] for k in ('o', 'h', 'l', 'c', 'pc', 'atr'))
    ema = f['ema20']
    e50 = f['ema50']
    n = len(c)
    span = np.maximum(h - l, 1e-09)
    bup = (c - l) / span
    bdn = (h - c) / span
    longstop = np.minimum(l, f['lowprev']) - 0.16 * atr
    shortstop = np.maximum(h, f['highprev']) + 0.16 * atr
    if name == 'h1_ema_reclaim':
        level = f['h1']['e20']
        up = (pc < level + 0.05 * atr) & (l <= level + 0.08 * atr) & (c > level + 0.16 * atr) & f['h1']['up']
        dn = (pc > level - 0.05 * atr) & (h >= level - 0.08 * atr) & (c < level - 0.16 * atr) & f['h1']['dn']
    elif name == 'h4_ema_reclaim':
        level = f['h4']['e20']
        up = (pc < level + 0.12 * atr) & (l < level + 0.08 * atr) & (c > level + 0.18 * atr) & f['h4']['up']
        dn = (pc > level - 0.12 * atr) & (h > level - 0.08 * atr) & (c < level - 0.18 * atr) & f['h4']['dn']
    elif name == 'm15_bos_retest':
        u = f['m15_bos_up']
        v = f['m15_bos_dn']
        up = (l <= u + 0.16 * atr) & (c > u + 0.12 * atr) & (pc > u - 0.22 * atr)
        dn = (h >= v - 0.16 * atr) & (c < v - 0.12 * atr) & (pc < v + 0.22 * atr)
        longstop = np.minimum(l, u - 0.85 * atr) - 0.16 * atr
        shortstop = np.maximum(h, v + 0.85 * atr) + 0.16 * atr
    elif name == 'm15_fvg_mitigation':
        u = f['m15_fvg_up']
        v = f['m15_fvg_dn']
        up = (l <= u + 0.25 * atr) & (c > u + 0.18 * atr) & (pc > u - 0.5 * atr)
        dn = (h >= v - 0.25 * atr) & (c < v - 0.18 * atr) & (pc < v + 0.5 * atr)
        longstop = np.minimum(l, u - 0.7 * atr) - 0.16 * atr
        shortstop = np.maximum(h, v + 0.7 * atr) + 0.16 * atr
    elif name in ('prevweek_q25_reclaim', 'prevweek_q75_reclaim'):
        level = f['week_q25'] if 'q25' in name else f['week_q75']
        up = (pc < level + 0.16 * atr) & (l < level + 0.09 * atr) & (c > level + 0.22 * atr)
        dn = (pc > level - 0.16 * atr) & (h > level - 0.09 * atr) & (c < level - 0.22 * atr)
        longstop = np.minimum(l, level - 0.55 * atr) - 0.16 * atr
        shortstop = np.maximum(h, level + 0.55 * atr) + 0.16 * atr
    elif name == 'prevweek_edges_sweep':
        lo = f['week_lo']
        hi = f['week_hi']
        up = (l < lo - 0.07 * atr) & (c > lo + 0.08 * atr) & (bup > 0.6)
        dn = (h > hi + 0.07 * atr) & (c < hi - 0.08 * atr) & (bdn > 0.6)
        longstop = np.minimum(l, lo) - 0.16 * atr
        shortstop = np.maximum(h, hi) + 0.16 * atr
    elif name == 'prevday_mid_reclaim':
        level = f['prevday_mid']
        up = (pc < level + 0.12 * atr) & (l <= level + 0.09 * atr) & (c > level + 0.18 * atr)
        dn = (pc > level - 0.12 * atr) & (h >= level - 0.09 * atr) & (c < level - 0.18 * atr)
        longstop = np.minimum(l, level - 0.6 * atr) - 0.16 * atr
        shortstop = np.maximum(h, level + 0.6 * atr) + 0.16 * atr
    elif name == 'vwap_reclaim':
        level = f['vwap']
        pl = f['prev_vwap']
        up = (pc < pl + 0.08 * atr) & (l < level + 0.12 * atr) & (c > level + 0.2 * atr)
        dn = (pc > pl - 0.08 * atr) & (h > level - 0.12 * atr) & (c < level - 0.2 * atr)
    elif name == 'bollinger_reversal':
        low = f['bb_low']
        hi = f['bb_hi']
        up = (l < low - 0.04 * atr) & (c > low + 0.12 * atr) & (bup > 0.65)
        dn = (h > hi + 0.04 * atr) & (c < hi - 0.12 * atr) & (bdn > 0.65)
        longstop = np.minimum(l, low) - 0.16 * atr
        shortstop = np.maximum(h, hi) + 0.16 * atr
    elif name == 'rsi_trend_pullback':
        up = (f['rsi'] >= 41) & (f['rsi'] < 58) & f['h1']['up'] & (l < ema + 0.1 * atr) & (c > ema + 0.12 * atr)
        dn = (f['rsi'] <= 59) & (f['rsi'] > 42) & f['h1']['dn'] & (h > ema - 0.1 * atr) & (c < ema - 0.12 * atr)
    elif name == 'm5_engulf_supply_demand':
        up = (pc < f['po1']) & (o < pc + 0.08 * atr) & (c > f['po1'] + 0.06 * atr) & (l < f['low24'] + 0.35 * atr)
        dn = (pc > f['po1']) & (o > pc - 0.08 * atr) & (c < f['po1'] - 0.06 * atr) & (h > f['high24'] - 0.35 * atr)
    elif name == 'h1_extreme_sweep':
        lo = f['h1']['lo12']
        hi = f['h1']['hi12']
        up = (l < lo - 0.06 * atr) & (c > lo + 0.1 * atr)
        dn = (h > hi + 0.06 * atr) & (c < hi - 0.1 * atr)
        longstop = np.minimum(l, lo) - 0.16 * atr
        shortstop = np.maximum(h, hi) + 0.16 * atr
    elif name == 'm15_compression_release':
        u = f['m15_comp_up']
        v = f['m15_comp_dn']
        up = (c > u + 0.15 * atr) & (pc < u + 0.5 * atr) & (l > u - 0.5 * atr)
        dn = (c < v - 0.15 * atr) & (pc > v - 0.5 * atr) & (h < v + 0.5 * atr)
        longstop = np.minimum(l, u - 0.9 * atr) - 0.16 * atr
        shortstop = np.maximum(h, v + 0.9 * atr) + 0.16 * atr
    elif name == 'stoch_trend_reversal':
        up = (f['stoch'] >= 25) & (f['stoch'] < 55) & f['h1']['up'] & (l < ema + 0.1 * atr) & (c > ema + 0.12 * atr)
        dn = (f['stoch'] <= 75) & (f['stoch'] > 45) & f['h1']['dn'] & (h > ema - 0.1 * atr) & (c < ema - 0.12 * atr)
    elif name == 'ema50_momentum_pullback':
        up = (ema > e50) & (pc <= e50 + 0.3 * atr) & (l <= e50 + 0.15 * atr) & (c > e50 + 0.25 * atr) & (c - o > 0.25 * atr)
        dn = (ema < e50) & (pc >= e50 - 0.3 * atr) & (h >= e50 - 0.15 * atr) & (c < e50 - 0.25 * atr) & (o - c > 0.25 * atr)
    elif name == 'm30_ema_retest':
        level = f['m30']['e20']
        up = (pc <= level + 0.15 * atr) & (l <= level + 0.12 * atr) & (c > level + 0.18 * atr) & f['m30']['up']
        dn = (pc >= level - 0.15 * atr) & (h >= level - 0.12 * atr) & (c < level - 0.18 * atr) & f['m30']['dn']
    elif name == 'prevweek_mid_retest':
        level = f['week_mid']
        up = (pc <= level + 0.22 * atr) & (l <= level + 0.12 * atr) & (c > level + 0.18 * atr)
        dn = (pc >= level - 0.22 * atr) & (h >= level - 0.12 * atr) & (c < level - 0.18 * atr)
        longstop = np.minimum(l, level - 0.5 * atr) - 0.16 * atr
        shortstop = np.maximum(h, level + 0.5 * atr) + 0.16 * atr
    else:
        raise ValueError('Invalid family ' + str(name))
    up &= c > o
    dn &= c < o
    lr = c - longstop
    sr = shortstop - c
    up &= np.isfinite(lr) & (lr > 0.2 * atr) & (lr <= 6 * atr)
    dn &= np.isfinite(sr) & (sr > 0.2 * atr) & (sr <= 6 * atr)
    both = up & dn
    p = np.where(up & ~both, 1, np.where(dn & ~both, -1, 0)).astype(np.int8)
    stops = np.where(p > 0, longstop, np.where(p < 0, shortstop, np.nan))
    return (p, stops)

def _v15bank_intent_for_config(f, name, side, session, body, close, vol, atr_rel, stop_atr, trend, warmup=80000):
    p, stop = _v15bank_family_raw(f, name)
    i = np.arange(len(p))
    mini = f['minute']
    a = np.maximum(f['atr'], 1e-10)
    lo, hi = session
    keep = (i >= warmup) & (mini >= lo) & (mini < hi) & (f['dow'] < 5) & (i < len(p) - 1)
    if side == 'long':
        keep &= p > 0
    elif side == 'short':
        keep &= p < 0
    keep &= (f['body'] >= body) & (np.where(p > 0, f['uq'], f['dq']) >= close)
    keep &= (f['volume'] >= vol) & (f['atrrel'] >= atr_rel)
    keep &= np.abs(f['c'] - stop) / a <= stop_atr
    if trend == 'ema':
        keep &= np.where(p > 0, f['ema_up'], f['ema_down'])
    elif trend == 'h1':
        keep &= np.where(p > 0, f['h1_up'], f['h1_down'])
    p = np.where(keep, p, 0).astype(np.int8)
    return (p, np.where(p != 0, stop, np.nan))

# ===== END FROZEN MODULE: nas100_v15_entries.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_5_ADD_ONLY_RESEARCH_ONLY.py =====

_v15_VERSION = 'NAS100_M5_V1_5_NEW_ENTRIES_ONLY_RESEARCH_NOT_ACCEPTED'
_v15_NEW_ENTRY_CONFIGS = ({'family': 'm30_ema_retest', 'side': 'long', 'session': (690, 960), 'body': 0.7, 'close': 0.84, 'volume': 0.9, 'atr_rel': 1.15, 'stop_atr': 3.0, 'trend': 'none'}, {'family': 'm15_fvg_mitigation', 'side': 'long', 'session': (690, 960), 'body': 0.5, 'close': 0.84, 'volume': 0.9, 'atr_rel': 0.65, 'stop_atr': 1.5, 'trend': 'none'})

class _v15_NAS100M5V15NewEntriesOnly(_v14_Strategy):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        base_p = out['Position'].to_numpy(np.int8).copy()
        base_sl = out['strategy_stop_loss'].to_numpy(float).copy()
        base_tp = out['strategy_target'].to_numpy(float).copy()
        f = _v15bank_make_bank(out)
        updated = base_p.copy()
        st = base_sl.copy()
        tp = base_tp.copy()
        reasons = out['signal_reason'].astype(str).to_numpy().copy()
        total = 0
        by_group = {}
        for conf in _v15_NEW_ENTRY_CONFIGS:
            p, s = _v15bank_intent_for_config(f, conf['family'], conf['side'], conf['session'], conf['body'], conf['close'], conf['volume'], conf['atr_rel'], conf['stop_atr'], conf['trend'], self.LIVE_HISTORY_BARS)
            insert = (updated == 0) & (p != 0)
            updated[insert] = p[insert]
            st[insert] = s[insert]
            tp[insert] = f['c'][insert] + p[insert] * 3.0 * np.abs(f['c'][insert] - s[insert])
            reasons[insert] = _v15_VERSION + '|ADD_ONLY|' + conf['family']
            count = int(insert.sum())
            total += count
            by_group[conf['family']] = count
        keep = base_p != 0
        assert np.array_equal(updated[keep], base_p[keep])
        assert np.array_equal(st[keep], base_sl[keep])
        assert np.array_equal(tp[keep], base_tp[keep])
        assert not np.any(keep & (updated == 0))
        out['Position'] = updated
        out['strategy_stop_loss'] = st
        out['strategy_target'] = tp
        out['signal_reason'] = reasons
        out.attrs['strategy_diagnostics'] = {'version': _v15_VERSION, 'frozen_baseline': 'V1.4', 'research_only': True, 'native_engine_verified': False, 'live_approved': False, 'new_signal_intents': total, 'by_group': by_group, 'selection': '2022-2024 development and 2025 validation', 'warning': '2026 was inspected in earlier cycles, not untouched OOS. Stop-first local replay; broker costs unverified.'}
        return out
_v15_Strategy = _v15_NAS100M5V15NewEntriesOnly

# ===== END FROZEN MODULE: NAS100_M5_V1_5_ADD_ONLY_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: filter_features.py =====

_v16features_FEATURE_NAMES = ('body_atr', 'relative_volume', 'atr_relative', 'close_quality', 'opp_wick', 'same_wick', 'stop_atr', 'ema_distance', 'ema_spread', 'rsi', 'stochastic', 'bb_zscore', 'vwap_distance', 'momentum_6', 'momentum_24', 'h1_ema_dist', 'h4_ema_dist', 'h1_slope', 'h4_slope', 'range48_atr', 'dist_level48', 'macd_atr', 'adx', 'close_gap_atr', 'prevday_mid_dist', 'day_range_atr')

def _v16features_feature_data(out):
    f = _v15bank_make_bank(out)
    n = len(out)
    o, h, l, c = (f[x] for x in ('o', 'h', 'l', 'c'))
    side = out['Position'].to_numpy(np.int8)
    st = out['strategy_stop_loss'].to_numpy(float)
    atr = np.maximum(f['atr'], 1e-09)
    span = np.maximum(h - l, 1e-09)
    pclose = np.r_[np.nan, c[:-1]]
    e20 = pd.Series(c).ewm(span=20, adjust=False).mean().to_numpy(float)
    e50 = pd.Series(c).ewm(span=50, adjust=False).mean().to_numpy(float)
    e12 = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy(float)
    e26 = pd.Series(c).ewm(span=26, adjust=False).mean().to_numpy(float)
    macd = e12 - e26
    macds = pd.Series(macd).ewm(span=9, adjust=False).mean().to_numpy(float)
    rsi_change = np.r_[0, np.diff(c)]
    gain = pd.Series(np.maximum(rsi_change, 0)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    loss = pd.Series(np.maximum(-rsi_change, 0)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    rsi = 100 * gain / np.maximum(gain + loss, 1e-09)
    lo14 = pd.Series(l).rolling(14, min_periods=14).min().to_numpy(float)
    hi14 = pd.Series(h).rolling(14, min_periods=14).max().to_numpy(float)
    stoch = 100 * (c - lo14) / np.maximum(hi14 - lo14, 1e-09)
    mid = pd.Series(c).shift(1).rolling(20, min_periods=20).mean().to_numpy(float)
    std = pd.Series(c).shift(1).rolling(20, min_periods=20).std(ddof=0).to_numpy(float)
    bbw = (c - mid) / np.maximum(std, 1e-09)
    utc = pd.to_datetime(out['Date'], utc=True)
    ny = utc.dt.tz_convert('America/New_York')
    day = ny.dt.strftime('%Y-%m-%d')
    vol = out['Volume'].to_numpy(float)
    cvol = pd.Series(vol).groupby(day, sort=False).cumsum().to_numpy(float)
    cpv = pd.Series(vol * (h + l + c) / 3).groupby(day, sort=False).cumsum().to_numpy(float)
    vwap = cpv / np.maximum(cvol, 1.0)
    mom6 = side * (c - np.r_[np.full(6, np.nan), c[:-6]]) / atr
    mom24 = side * (c - np.r_[np.full(24, np.nan), c[:-24]]) / atr
    hi48 = pd.Series(h).shift(1).rolling(48, min_periods=48).max().to_numpy(float)
    lo48 = pd.Series(l).shift(1).rolling(48, min_periods=48).min().to_numpy(float)
    spread = side * (e20 - e50) / atr
    h1 = f['h1']
    h4 = f['h4']
    pwh = np.r_[np.nan, h[:-1]]
    pwl = np.r_[np.nan, l[:-1]]
    up = h - np.maximum(o, c)
    down = np.minimum(o, c) - l
    u = side > 0
    same = np.where(u, down, up) / span
    opp = np.where(u, up, down) / span
    dr = np.where(u, hi48 - c, c - lo48) / atr
    hd = np.r_[0.0, np.diff(h)]
    ld = np.r_[0.0, -np.diff(l)]
    plus = np.where((hd > ld) & (hd > 0), hd, 0.0)
    minus = np.where((ld > hd) & (ld > 0), ld, 0.0)
    prev = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - prev), abs(l - prev)))
    atradx = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    plusdi = 100 * pd.Series(plus).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float) / np.maximum(atradx, 1e-09)
    minusdi = 100 * pd.Series(minus).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float) / np.maximum(atradx, 1e-09)
    dx = 100 * abs(plusdi - minusdi) / np.maximum(plusdi + minusdi, 1e-09)
    adx = pd.Series(dx).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
    utcday = utc.dt.floor('D')
    prevdaily = pd.DataFrame({'day': utcday, 'hi': h, 'lo': l}).groupby('day', sort=True).agg(h=('hi', 'max'), l=('lo', 'min')).shift(1)
    prevmid = ((prevdaily['h'] + prevdaily['l']) / 2).reindex(utcday).to_numpy(float)
    curhi = pd.Series(h).groupby(day, sort=False).cummax().to_numpy(float)
    curlo = pd.Series(l).groupby(day, sort=False).cummin().to_numpy(float)
    vals = {'body_atr': np.abs(c - o) / atr, 'relative_volume': f['volume'], 'atr_relative': f['atrrel'], 'close_quality': np.where(u, (c - l) / span, (h - c) / span), 'opp_wick': opp, 'same_wick': same, 'stop_atr': np.abs(c - st) / atr, 'ema_distance': side * (c - e20) / atr, 'ema_spread': spread, 'rsi': rsi, 'stochastic': stoch, 'bb_zscore': bbw, 'vwap_distance': side * (c - vwap) / atr, 'momentum_6': mom6, 'momentum_24': mom24, 'h1_ema_dist': side * (c - h1['e20']) / atr, 'h4_ema_dist': side * (c - h4['e20']) / atr, 'h1_slope': side * (h1['e20'] - h1['e50']) / np.maximum(h1['atr'], 1e-09), 'h4_slope': side * (h4['e20'] - h4['e50']) / np.maximum(h4['atr'], 1e-09), 'range48_atr': (hi48 - lo48) / atr, 'dist_level48': dr, 'macd_atr': side * (macd - macds) / atr, 'adx': adx, 'close_gap_atr': np.abs(o - pclose) / atr, 'prevday_mid_dist': side * (c - prevmid) / atr, 'day_range_atr': (curhi - curlo) / atr}
    return (vals, dict(ny_min=(ny.dt.hour * 60 + ny.dt.minute).to_numpy(np.int32), weekday=ny.dt.dayofweek.to_numpy(np.int8), side=side, year=utc.dt.year.to_numpy(np.int16), reasons=out['signal_reason'].astype(str).to_numpy(), h1_up=h1['up'], h1_dn=h1['dn'], h4_up=h4['up'], h4_dn=h4['dn'], ema_up=e20 > e50, ema_dn=e20 < e50))

def _v16features_build_predicates(out, sigidx=None, min_dev=30, return_metrics=False):
    vals, meta = _v16features_feature_data(out)
    side = meta['side']
    sigidx = np.flatnonzero(side != 0) if sigidx is None else sigidx
    dev = (meta['year'][sigidx] >= 2022) & (meta['year'][sigidx] <= 2024)
    p = []
    seen = set()

    def add(label, mask):
        m = np.asarray(mask, dtype=bool)
        m &= side[sigidx] != 0
        m &= np.arange(len(sigidx)) >= 0
        cnt = m.sum()
        if cnt < min_dev or cnt > len(m) * 0.92:
            return
        fingerprint = np.packbits(m).tobytes()
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        p.append((label, m))
    for key in _v16features_FEATURE_NAMES:
        v = vals[key][sigidx]
        finite = v[dev & np.isfinite(v)]
        if len(finite) < 50:
            continue
        for quant in (0.08, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.92):
            q = float(np.quantile(finite, quant))
            add(f'{key} <= {q:.6g}', np.isfinite(v) & (v <= q))
            add(f'{key} >= {q:.6g}', np.isfinite(v) & (v >= q))
    for wd in range(5):
        add(f'weekday == {wd}', meta['weekday'][sigidx] == wd)
    for a, b in ((570, 630), (630, 690), (690, 750), (750, 810), (810, 870), (870, 930), (930, 960), (570, 690), (690, 810), (810, 960), (570, 750), (750, 960)):
        add(f'NY minute {a}..{b}', (meta['ny_min'][sigidx] >= a) & (meta['ny_min'][sigidx] < b))
    add('LONG only', side[sigidx] > 0)
    add('SHORT only', side[sigidx] < 0)
    for k in ('h1', 'h4', 'ema'):
        tr_up = meta[k + '_up'][sigidx]
        tr_dn = meta[k + '_dn'][sigidx]
        align = np.where(side[sigidx] > 0, tr_up, tr_dn)
        add(k + ' aligned', align)
        add(k + ' opposed', np.where(side[sigidx] > 0, tr_dn, tr_up))
    reason = meta['reasons'][sigidx]
    for name in ('m30_ema_retest', 'm15_fvg_mitigation', 'reclaim_ny_orb'):
        add('entry_family == ' + name, np.char.find(reason.astype(str), name) >= 0)
    if return_metrics:
        return (p, vals, meta)
    return p

# ===== END FROZEN MODULE: filter_features.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_6_FILTER_ONLY_RESEARCH_ONLY.py =====

_v16_VERSION = 'NAS100_M5_V1_6_FILTER_ONLY_RESEARCH_NOT_ACCEPTED'
_v16_FILTER_THRESHOLDS = {'stop_atr_max': 1.66201, 'bb_zscore_max': -2.35055, 'h1_directional_ema_distance_min': 3.33802}

def _v16_rejected_intents_from_frozen_output(out):
    """Boolean mask, true exclusively at baseline signals meeting rejection rules."""
    vals, meta = _v16features_feature_data(out)
    side = meta['side']
    return (side != 0) & np.isfinite(vals['stop_atr']) & (vals['stop_atr'] <= _v16_FILTER_THRESHOLDS['stop_atr_max']) & np.isfinite(vals['bb_zscore']) & (vals['bb_zscore'] <= _v16_FILTER_THRESHOLDS['bb_zscore_max']) & np.isfinite(vals['h1_ema_dist']) & (vals['h1_ema_dist'] >= _v16_FILTER_THRESHOLDS['h1_directional_ema_distance_min'])

class _v16_NAS100M5V16FilterOnlyResearch(_v15_Strategy):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out['Position'].to_numpy(np.int8).copy()
        original_sl = out['strategy_stop_loss'].to_numpy(float).copy()
        original_tp = out['strategy_target'].to_numpy(float).copy()
        veto = _v16_rejected_intents_from_frozen_output(out)
        assert not np.any(veto & (original_p == 0))
        out.loc[veto, 'Position'] = 0
        out.loc[veto, 'strategy_stop_loss'] = np.nan
        out.loc[veto, 'strategy_target'] = np.nan
        out.loc[veto, 'signal_reason'] = 'V1.6|FILTER_ONLY|STOP_ATR_BB_EXTREME_H1_EMA_DIST'
        p = out['Position'].to_numpy(np.int8)
        keep = p != 0
        assert np.all((p == 0) | (p == original_p)), 'signal changed or created'
        assert np.array_equal(out['strategy_stop_loss'].to_numpy(float)[keep], original_sl[keep]), 'retained SL changed'
        assert np.array_equal(out['strategy_target'].to_numpy(float)[keep], original_tp[keep]), 'retained TP changed'
        old = out.attrs.get('strategy_diagnostics', {}).copy()
        old.update({'version': _v16_VERSION, 'frozen_baseline': 'NAS100_M5_V1_5', 'mode': 'FILTER_EXISTING_LOSING_TRADES_ONLY', 'raw_signal_intents_rejected': int(veto.sum()), 'filter_thresholds': dict(_v16_FILTER_THRESHOLDS), 'research_only': True, 'live_approved': False, 'native_algoagentx_verified': False, 'user_acceptance_pending': True, 'warning': '2026 was inspected in previous searches; no untouched OOS confirmation.'})
        out.attrs['strategy_diagnostics'] = old
        return out
_v16_Strategy = _v16_NAS100M5V16FilterOnlyResearch

# ===== END FROZEN MODULE: NAS100_M5_V1_6_FILTER_ONLY_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: nas100_v17_entries.py =====

_v17bank_FAMILY_NAMES = ('m10_bos_retest', 'm45_ema_reclaim', 'h1_donchian_sweep', 'm5_fvg_mitigation', 'h1_macd_vwap_pullback', 'prevday_edge_break_retest', 'ny_open_range_reclaim', 'm30_sweep_reject', 'm10_ema_cross_retest', 'm45_range_break', 'm15_ema_trendline', 'prevday_extreme_falsebreak')
_v17bank_SESSIONS = ((570, 690), (570, 750), (570, 870), (630, 870), (690, 960), (570, 960))
_v17bank_BODY = (0.0, 0.15, 0.3, 0.5, 0.7)
_v17bank_CLOSE = (0.52, 0.6, 0.68, 0.76, 0.84)
_v17bank_VOL = (0.0, 0.55, 0.9, 1.25)
_v17bank_ATR_REL = (0.0, 0.65, 0.9, 1.15, 1.5)
_v17bank_STOP_ATR = (1.0, 1.5, 2.0, 3.0, 4.5)
_v17bank_TRENDS = ('none', 'ema', 'h1')
_v17bank_SIDES = ('both', 'long', 'short')

def _v17bank_make_bank(d):
    f = _v15bank_make_bank(d)
    dt = pd.to_datetime(d['Date'], utc=True).dt.tz_localize(None)
    close_t = (dt + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    a10, p10, _, _ = _v15bank_htf_projection(d, '10min', 2, 10, close_t)
    a45, p45, _, _ = _v15bank_htf_projection(d, '45min', 9, 45, close_t)
    f['m10'] = p10
    f['m45'] = p45
    o, h, l, c = (f[k] for k in ('o', 'h', 'l', 'c'))
    f['m10_bos_up'] = (p10['Close'] > p10['hi12'] + 0.08 * p10['atr']) & p10['up']
    f['m10_bos_dn'] = (p10['Close'] < p10['lo12'] - 0.08 * p10['atr']) & p10['dn']
    f['m45_break_up'] = (p45['Close'] > p45['hi12'] + 0.06 * p45['atr']) & p45['up']
    f['m45_break_dn'] = (p45['Close'] < p45['lo12'] - 0.06 * p45['atr']) & p45['dn']
    f['high72'] = _v15bank_lag_roll(h, 72, 'hi')
    f['low72'] = _v15bank_lag_roll(l, 72, 'lo')
    f['pc3'] = np.r_[np.full(3, np.nan), c[:-3]]
    f['ph3'] = np.r_[np.full(3, np.nan), h[:-3]]
    f['pl3'] = np.r_[np.full(3, np.nan), l[:-3]]
    f['ph2'] = np.r_[np.full(2, np.nan), h[:-2]]
    f['pl2'] = np.r_[np.full(2, np.nan), l[:-2]]
    f['pl1'] = np.r_[np.nan, l[:-1]]
    f['ph1'] = np.r_[np.nan, h[:-1]]
    f['m5_gap_up'] = f['pl1'] > f['ph3'] + 0.04 * f['atr']
    f['m5_gap_dn'] = f['ph1'] < f['pl3'] - 0.04 * f['atr']
    e12 = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy(float)
    e26 = pd.Series(c).ewm(span=26, adjust=False).mean().to_numpy(float)
    macd = e12 - e26
    sig = pd.Series(macd).ewm(span=9, adjust=False).mean().to_numpy(float)
    f['macdh'] = macd - sig
    ema = f['ema20']
    f['ema20_slope12'] = (ema - np.r_[np.full(12, np.nan), ema[:-12]]) / np.maximum(f['atr'], 1e-09)
    day = dt.dt.floor('D')
    g = pd.DataFrame({'day': day, 'h': h, 'l': l}).groupby('day', sort=True).agg(hi=('h', 'max'), lo=('l', 'min')).shift(1)
    f['pdh'] = g.hi.reindex(day).to_numpy(float)
    f['pdl'] = g.lo.reindex(day).to_numpy(float)
    ny = dt.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    key = ny.dt.strftime('%Y-%m-%d')
    minute = ny.dt.hour * 60 + ny.dt.minute
    mask = (minute >= 570) & (minute < 600)
    ordata = pd.DataFrame({'day': key[mask], 'h': h[mask.to_numpy()], 'l': l[mask.to_numpy()]})
    ranges = ordata.groupby('day', sort=True).agg(hi=('h', 'max'), lo=('l', 'min'), n=('h', 'size'))
    fk = pd.Index(key)
    full = (ranges.n.reindex(fk).fillna(0).to_numpy(int) >= 6) & (minute.to_numpy() >= 600)
    f['orb_hi'] = np.where(full, ranges.hi.reindex(fk).to_numpy(float), np.nan)
    f['orb_lo'] = np.where(full, ranges.lo.reindex(fk).to_numpy(float), np.nan)
    return f

def _v17bank_family_raw(f, name):
    o, h, l, c, pc, atr = (f[k] for k in ('o', 'h', 'l', 'c', 'pc', 'atr'))
    a = np.maximum(atr, 1e-09)
    n = len(c)
    m10 = f['m10']
    m45 = f['m45']
    h1 = f['h1']
    m30 = f['m30']
    up = np.zeros(n, bool)
    dn = np.zeros(n, bool)
    ls = np.minimum(l, f['pl1']) - 0.16 * a
    ss = np.maximum(h, f['ph1']) + 0.16 * a
    if name == 'm10_bos_retest':
        levelu = m10['hi12']
        leveld = m10['lo12']
        up = f['m10_bos_up'] & (l <= levelu + 0.25 * a) & (c > levelu + 0.12 * a) & (pc > levelu - 0.3 * a)
        dn = f['m10_bos_dn'] & (h >= leveld - 0.25 * a) & (c < leveld - 0.12 * a) & (pc < leveld + 0.3 * a)
        ls = np.minimum(l, levelu - 0.75 * a) - 0.16 * a
        ss = np.maximum(h, leveld + 0.75 * a) + 0.16 * a
    elif name == 'm45_ema_reclaim':
        u = m45['e20']
        up = m45['up'] & (pc <= u + 0.2 * a) & (l <= u + 0.17 * a) & (c > u + 0.22 * a)
        dn = m45['dn'] & (pc >= u - 0.2 * a) & (h >= u - 0.17 * a) & (c < u - 0.22 * a)
    elif name == 'h1_donchian_sweep':
        low = h1['lo12']
        hi = h1['hi12']
        up = (l < low - 0.07 * a) & (c > low + 0.12 * a) & (pc < low + 0.35 * a)
        dn = (h > hi + 0.07 * a) & (c < hi - 0.12 * a) & (pc > hi - 0.35 * a)
        ls = np.minimum(l, low) - 0.16 * a
        ss = np.maximum(h, hi) + 0.16 * a
    elif name == 'm5_fvg_mitigation':
        edgeu = f['ph3']
        edged = f['pl3']
        up = f['m5_gap_up'] & (l <= edgeu + 0.3 * a) & (c > edgeu + 0.16 * a) & (pc > edgeu - 0.4 * a)
        dn = f['m5_gap_dn'] & (h >= edged - 0.3 * a) & (c < edged - 0.16 * a) & (pc < edged + 0.4 * a)
        ls = np.minimum(l, edgeu - 0.6 * a) - 0.16 * a
        ss = np.maximum(h, edged + 0.6 * a) + 0.16 * a
    elif name == 'h1_macd_vwap_pullback':
        u = f['vwap']
        up = (f['macdh'] > 0.03 * a) & h1['up'] & (pc < u + 0.1 * a) & (l <= u + 0.1 * a) & (c > u + 0.2 * a)
        dn = (f['macdh'] < -0.03 * a) & h1['dn'] & (pc > u - 0.1 * a) & (h >= u - 0.1 * a) & (c < u - 0.2 * a)
    elif name == 'prevday_edge_break_retest':
        hi = f['pdh']
        lo = f['pdl']
        up = (pc < hi + 0.25 * a) & (l < hi + 0.2 * a) & (c > hi + 0.22 * a) & h1['up']
        dn = (pc > lo - 0.25 * a) & (h > lo - 0.2 * a) & (c < lo - 0.22 * a) & h1['dn']
        ls = np.minimum(l, hi - 0.8 * a) - 0.16 * a
        ss = np.maximum(h, lo + 0.8 * a) + 0.16 * a
    elif name == 'ny_open_range_reclaim':
        hi = f['orb_hi']
        lo = f['orb_lo']
        up = (pc < hi + 0.2 * a) & (l <= hi + 0.12 * a) & (c > hi + 0.19 * a) & h1['up']
        dn = (pc > lo - 0.2 * a) & (h >= lo - 0.12 * a) & (c < lo - 0.19 * a) & h1['dn']
        ls = np.minimum(l, hi - 0.8 * a) - 0.16 * a
        ss = np.maximum(h, lo + 0.8 * a) + 0.16 * a
    elif name == 'm30_sweep_reject':
        low = m30['lo12']
        hi = m30['hi12']
        up = (l < low - 0.1 * a) & (c > low + 0.1 * a) & (pc < low + 0.3 * a)
        dn = (h > hi + 0.1 * a) & (c < hi - 0.1 * a) & (pc > hi - 0.3 * a)
        ls = np.minimum(l, low) - 0.16 * a
        ss = np.maximum(h, hi) + 0.16 * a
    elif name == 'm10_ema_cross_retest':
        lev = m10['e20']
        up = m10['up'] & (pc < lev + 0.05 * a) & (l <= lev + 0.1 * a) & (c > lev + 0.23 * a) & (f['macdh'] > 0)
        dn = m10['dn'] & (pc > lev - 0.05 * a) & (h >= lev - 0.1 * a) & (c < lev - 0.23 * a) & (f['macdh'] < 0)
    elif name == 'm45_range_break':
        up = f['m45_break_up'] & (c > m45['hi12'] + 0.13 * a) & (pc < m45['hi12'] + 0.6 * a)
        dn = f['m45_break_dn'] & (c < m45['lo12'] - 0.13 * a) & (pc > m45['lo12'] - 0.6 * a)
        ls = np.minimum(l, m45['hi12'] - 0.9 * a) - 0.16 * a
        ss = np.maximum(h, m45['lo12'] + 0.9 * a) + 0.16 * a
    elif name == 'm15_ema_trendline':
        lev = f['m15']['e20']
        up = f['m15']['up'] & (f['ema20_slope12'] > 0.12) & (pc < lev + 0.35 * a) & (l <= lev + 0.18 * a) & (c > lev + 0.18 * a)
        dn = f['m15']['dn'] & (f['ema20_slope12'] < -0.12) & (pc > lev - 0.35 * a) & (h >= lev - 0.18 * a) & (c < lev - 0.18 * a)
    elif name == 'prevday_extreme_falsebreak':
        hi = f['pdh']
        lo = f['pdl']
        up = (l < lo - 0.12 * a) & (c > lo + 0.16 * a) & (pc < lo + 0.35 * a)
        dn = (h > hi + 0.12 * a) & (c < hi - 0.16 * a) & (pc > hi - 0.35 * a)
        ls = np.minimum(l, lo) - 0.16 * a
        ss = np.maximum(h, hi) + 0.16 * a
    else:
        raise ValueError('unknown V1.7 family ' + name)
    up &= c > o
    dn &= c < o
    lr = c - ls
    sr = ss - c
    up &= np.isfinite(lr) & (lr > 0.2 * a) & (lr <= 6 * a)
    dn &= np.isfinite(sr) & (sr > 0.2 * a) & (sr <= 6 * a)
    both = up & dn
    p = np.where(up & ~both, 1, np.where(dn & ~both, -1, 0)).astype(np.int8)
    st = np.where(p > 0, ls, np.where(p < 0, ss, np.nan))
    return (p, st)

def _v17bank_intent_for_config(f, name, side, session, body, close, vol, atr_rel, stop_atr, trend, warmup=80000):
    p, st = _v17bank_family_raw(f, name)
    i = np.arange(len(p))
    a = np.maximum(f['atr'], 1e-09)
    lo, hi = session
    keep = (i >= warmup) & (i < len(p) - 1) & (f['dow'] < 5) & (f['minute'] >= lo) & (f['minute'] < hi)
    if side == 'long':
        keep &= p > 0
    elif side == 'short':
        keep &= p < 0
    keep &= (f['body'] >= body) & (np.where(p > 0, f['uq'], f['dq']) >= close)
    keep &= (f['volume'] >= vol) & (f['atrrel'] >= atr_rel)
    keep &= abs(f['c'] - st) / a <= stop_atr
    if trend == 'ema':
        keep &= np.where(p > 0, f['ema_up'], f['ema_down'])
    elif trend == 'h1':
        keep &= np.where(p > 0, f['h1_up'], f['h1_down'])
    p = np.where(keep, p, 0).astype(np.int8)
    return (p, np.where(p != 0, st, np.nan))

# ===== END FROZEN MODULE: nas100_v17_entries.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_7_ADD_ONLY_RESEARCH_ONLY.py =====

_v17_VERSION = 'NAS100_M5_V1_7_ADD_ONLY_RESEARCH_NOT_ACCEPTED'
_v17_NEW_ENTRY_CONFIGS = ({'family': 'm5_fvg_mitigation', 'side': 'long', 'session': (690, 960), 'body': 0.3, 'close': 0.52, 'volume': 0.55, 'atr_rel': 1.5, 'stop_atr': 4.5, 'trend': 'h1'}, {'family': 'm10_ema_cross_retest', 'side': 'both', 'session': (570, 870), 'body': 0.7, 'close': 0.84, 'volume': 0.0, 'atr_rel': 0.9, 'stop_atr': 3.0, 'trend': 'h1'})

class _v17_NAS100M5V17AddOnlyResearch(_v16_Strategy):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        baseline_p = out['Position'].to_numpy(np.int8).copy()
        baseline_sl = out['strategy_stop_loss'].to_numpy(float).copy()
        baseline_tp = out['strategy_target'].to_numpy(float).copy()
        p = baseline_p.copy()
        st = baseline_sl.copy()
        tp = baseline_tp.copy()
        reasons = out['signal_reason'].astype(str).to_numpy().copy()
        f = _v17bank_make_bank(out)
        counts = {}
        for conf in _v17_NEW_ENTRY_CONFIGS:
            ep, es = _v17bank_intent_for_config(f, conf['family'], conf['side'], conf['session'], conf['body'], conf['close'], conf['volume'], conf['atr_rel'], conf['stop_atr'], conf['trend'], self.LIVE_HISTORY_BARS)
            add = (p == 0) & (ep != 0)
            p[add] = ep[add]
            st[add] = es[add]
            tp[add] = f['c'][add] + ep[add] * 3.0 * np.abs(f['c'][add] - es[add])
            reasons[add] = _v17_VERSION + '|NEW_ENTRY|' + conf['family']
            counts[conf['family']] = int(add.sum())
        old = baseline_p != 0
        assert np.array_equal(p[old], baseline_p[old]), 'Baseline signal overwritten'
        assert np.array_equal(st[old], baseline_sl[old]), 'Baseline SL overwritten'
        assert np.array_equal(tp[old], baseline_tp[old]), 'Baseline TP overwritten'
        assert not np.any((baseline_p != 0) & (p == 0)), 'Baseline signal removed'
        out['Position'] = p
        out['strategy_stop_loss'] = st
        out['strategy_target'] = tp
        out['signal_reason'] = reasons
        d = out.attrs.get('strategy_diagnostics', {}).copy()
        d.update({'version': _v17_VERSION, 'frozen_baseline': 'V1.6', 'mode': 'ADD_NEW_WINNING_TRADES_ONLY', 'new_signal_intents': int(sum(counts.values())), 'added_by_family': counts, 'research_only': True, 'live_approved': False, 'native_algoagentx_verified': False, 'unseen_oos_verified': False, 'warning': '2026 already inspected in previous studies; external forward validation required.'})
        out.attrs['strategy_diagnostics'] = d
        return out
_v17_Strategy = _v17_NAS100M5V17AddOnlyResearch

# ===== END FROZEN MODULE: NAS100_M5_V1_7_ADD_ONLY_RESEARCH_ONLY.py =====


# ===== START FROZEN MODULE: NAS100_M5_V1_8_ADD_ONLY_RECENT_RESEARCH_ONLY.py =====

_v18_VERSION = 'NAS100_M5_V1_8_ADD_ONLY_RECENT_RESEARCH_NOT_LIVE_APPROVED'
_v18_NEW_ENTRY_CONFIGS = ({'source': 'v15', 'family': 'h1_extreme_sweep', 'side': 'long', 'session': (570, 750), 'body': 0.0, 'close': 0.52, 'volume': 0.9, 'atr_rel': 0.65, 'stop_atr': 1.0, 'trend': 'none'}, {'source': 'v15', 'family': 'prevweek_mid_retest', 'side': 'short', 'session': (570, 690), 'body': 0.3, 'close': 0.52, 'volume': 1.25, 'atr_rel': 1.15, 'stop_atr': 3.0, 'trend': 'h1'})

def _v18__new_intent(f, config, warmup):
    side, stop = _v15bank_family_raw(f, config['family'])
    i = np.arange(len(side))
    atr = np.maximum(f['atr'], 1e-09)
    lo, hi = config['session']
    keep = (i >= warmup) & (i < len(i) - 1) & (f['dow'] < 5) & (f['minute'] >= lo) & (f['minute'] < hi)
    if config['side'] == 'long':
        keep &= side > 0
    if config['side'] == 'short':
        keep &= side < 0
    quality = np.where(side > 0, f['uq'], f['dq'])
    keep &= (f['body'] >= config['body']) & (quality >= config['close'])
    keep &= (f['volume'] >= config['volume']) & (f['atrrel'] >= config['atr_rel'])
    keep &= np.abs(f['c'] - stop) / atr <= config['stop_atr']
    if config['trend'] == 'ema':
        keep &= np.where(side > 0, f['ema_up'], f['ema_down'])
    if config['trend'] == 'h1':
        keep &= np.where(side > 0, f['h1_up'], f['h1_down'])
    pos = np.where(keep, side, 0).astype(np.int8)
    return (pos, np.where(pos != 0, stop, np.nan))

class _v18_NAS100M5V18AddOnlyRecentResearch(_v17_Strategy):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        initial_p = out['Position'].to_numpy(np.int8).copy()
        initial_s = out['strategy_stop_loss'].to_numpy(float).copy()
        initial_t = out['strategy_target'].to_numpy(float).copy()
        p = initial_p.copy()
        s = initial_s.copy()
        t = initial_t.copy()
        why = out['signal_reason'].astype(str).to_numpy().copy()
        f = _v17bank_make_bank(out)
        by_family = {}
        for config in _v18_NEW_ENTRY_CONFIGS:
            sp, ss = _v18__new_intent(f, config, self.LIVE_HISTORY_BARS)
            add = (p == 0) & (sp != 0)
            p[add] = sp[add]
            s[add] = ss[add]
            t[add] = f['c'][add] + sp[add] * 3.0 * np.abs(f['c'][add] - ss[add])
            why[add] = _v18_VERSION + '|NEW_ENTRY|' + config['family']
            by_family[config['family']] = int(add.sum())
        old = initial_p != 0
        assert np.array_equal(p[old], initial_p[old])
        assert np.array_equal(s[old], initial_s[old])
        assert np.array_equal(t[old], initial_t[old])
        assert np.count_nonzero(~old & (p != 0) & (np.arange(len(p)) < self.LIVE_HISTORY_BARS)) == 0
        out['Position'] = p
        out['strategy_stop_loss'] = s
        out['strategy_target'] = t
        out['signal_reason'] = why
        out.attrs['strategy_diagnostics'] = {'version': _v18_VERSION, 'frozen_baseline': 'V1.7', 'mode': 'ADD_NEW_WINNING_TRADES_ONLY', 'new_signal_intents': int(sum(by_family.values())), 'added_by_family': by_family, 'research_only': True, 'live_approved': False, 'native_algoagentx_verified': False, 'untouched_out_of_sample_verified': False, 'warning': '2025/26 reused in selection and prior studies; no unseen forward validation.'}
        return out
_v18_Strategy = _v18_NAS100M5V18AddOnlyRecentResearch

# ===== END FROZEN MODULE: NAS100_M5_V1_8_ADD_ONLY_RECENT_RESEARCH_ONLY.py =====



Strategy = _v18_Strategy

LIVE_HISTORY_BARS = 80000


# ===== V1.9 EXPERIMENTAL FILTER-ONLY OVERLAY =====
# V1.8 source above is frozen and byte-for-byte unchanged.
V19_VERSION = "NAS100_M5_V1_9_FILTER_ONLY_RESEARCH_NOT_LIVE_APPROVED"
V19_FILTER_RULES = (
    (
        ("momentum_24", ">=", 4.783347),
        ("h4_slope", "<=", -1.536017),
        ("close_gap_atr", "<=", 0.038654),
    ),
    (
        ("opp_wick", ">=", 0.258841),
        ("stochastic", ">=", 88.092895),
        ("momentum_6", ">=", 1.479106),
    ),
)

class NAS100M5V19FilterOnly(Strategy):
    """Only reject existing V1.8 intents; never add/reverse/retarget trades."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original = out["Position"].to_numpy(dtype=np.int8).copy()
        original_sl = out["strategy_stop_loss"].to_numpy(dtype=float).copy()
        original_tp = out["strategy_target"].to_numpy(dtype=float).copy()
        # Uses only confirmed M5 and completed H4 data as of signal close.
        values, _meta = _v16features_feature_data(out)
        veto = np.zeros(len(out), dtype=bool)
        for group in V19_FILTER_RULES:
            hit = np.ones(len(out), dtype=bool)
            for key, op, threshold in group:
                x = values[key]
                hit &= np.isfinite(x)
                if op == ">=":
                    hit &= x >= threshold
                elif op == "<=":
                    hit &= x <= threshold
                else:
                    raise ValueError("Unsupported V1.9 condition")
            veto |= hit
        veto &= original != 0
        out.loc[veto, "Position"] = 0
        out.loc[veto, "strategy_stop_loss"] = np.nan
        out.loc[veto, "strategy_target"] = np.nan
        out.loc[veto, "signal_reason"] = V19_VERSION + "|VETO"
        updated = out["Position"].to_numpy(dtype=np.int8)
        retained = updated != 0
        assert np.all((updated == 0) | (updated == original)), "Unexpected added/reversed signal"
        assert np.array_equal(out["strategy_stop_loss"].to_numpy(float)[retained], original_sl[retained])
        assert np.array_equal(out["strategy_target"].to_numpy(float)[retained], original_tp[retained])
        out.attrs["strategy_diagnostics"] = {
            "version": V19_VERSION,
            "frozen_baseline": "NAS100_M5_V1_8_ALGOAGENTX_STANDALONE",
            "research_mode": "FILTER_EXISTING_LOSING_TRADES_ONLY",
            "rejected_existing_signal_bars": int(veto.sum()),
            "filter_rules": V19_FILTER_RULES,
            "new_signals": 0,
            "stop_target_modifications": 0,
            "research_only": True,
            "live_approved": False,
            "native_algoagentx_candidate_verified": False,
            "untouched_forward_validation": False,
            "selection_bias_warning": "2025 and 2026 previously inspected; parameters selected from historical backtests",
        }
        return out

Strategy = NAS100M5V19FilterOnly


# ===== V2.0 RESEARCH-ONLY ADD-NEW-ENTRIES OVERLAY =====
# Frozen V1.9 code above remains unchanged. No custom-module imports.
# Changes to existing V1.9 signals, SL, TP, or signal_reason are prohibited.
V20_VERSION = "NAS100_M5_V2_0_M30_EMA50_REJECTION_ADD_ONLY_RESEARCH"
V20_SETTINGS = {
    "side": "long",
    "ny_minute_start": 570,
    "ny_minute_end": 870,
    "body_atr_min": 0.30,
    "close_quality_min": 0.84,
    "stop_atr_max": 3.0,
    "close_gap_atr_min": 0.011761813452185632,
    "ny_day_range_atr_min": 6.033045325031411,
    "trend": "completed_H1_aligned",
    "take_profit_R": 3.0,
}

class NAS100V20AddOnly(Strategy):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        oldp = out["Position"].to_numpy(dtype=np.int8).copy()
        olds = out["strategy_stop_loss"].to_numpy(dtype=float).copy()
        oldt = out["strategy_target"].to_numpy(dtype=float).copy()
        oldreason = out["signal_reason"].astype(str).to_numpy().copy()
        f = _v17bank_make_bank(out)
        o, h, l, c = (f[k] for k in ("o", "h", "l", "c"))
        a = np.maximum(f["atr"], 1e-9)
        e50 = f["m30"]["e50"]
        n = len(out)
        strength = (c - o) / a
        close_quality = (c - l) / np.maximum(h - l, 1e-9)
        sl = np.minimum(l, f["pl1"]) - 0.16 * a
        previous_close = np.r_[np.nan, c[:-1]]
        close_gap_atr = np.abs(o - previous_close) / a
        ny = pd.to_datetime(out["Date"], utc=True).dt.tz_convert("America/New_York")
        day = ny.dt.strftime("%Y-%m-%d")
        intraday_high = pd.Series(h).groupby(day, sort=False).cummax().to_numpy(float)
        intraday_low = pd.Series(l).groupby(day, sort=False).cummin().to_numpy(float)
        day_range_atr = (intraday_high - intraday_low) / a
        keep = (
            (np.arange(n) >= self.LIVE_HISTORY_BARS) & (np.arange(n) < n - 1) &
            (oldp == 0) & (f["dow"] < 5) &
            (f["minute"] >= 570) & (f["minute"] < 870) &
            (f["m30"]["up"]) & (f["h1"]["up"]) &
            (l < e50 + 0.15*a) & (c > e50 + 0.25*a) &
            (close_quality > 0.70) & (c > o) &
            (strength >= 0.30 - 1e-5) & (close_quality >= 0.84 - 1e-5) &
            (c - sl > 0.2*a) & (c - sl <= 6.0*a) &
            ((c - sl)/a <= 3.0 + 1e-5) &
            (close_gap_atr >= V20_SETTINGS["close_gap_atr_min"]) &
            (day_range_atr >= V20_SETTINGS["ny_day_range_atr_min"])
        )
        # All features are known by the close of the signal-generating M5 candle.
        keep &= np.isfinite(sl) & np.isfinite(close_gap_atr) & np.isfinite(day_range_atr)
        out.loc[keep,"Position"] = 1
        out.loc[keep,"strategy_stop_loss"] = sl[keep]
        out.loc[keep,"strategy_target"] = (c + 3.0 * np.abs(c-sl))[keep]
        out.loc[keep,"signal_reason"] = V20_VERSION + "|NEW_ENTRY|M30_EMA50_WICK_REJECT_LONG"
        newp = out["Position"].to_numpy(dtype=np.int8)
        retained = oldp != 0
        assert np.array_equal(newp[retained],oldp[retained]),"Modified original V1.9 direction"
        assert np.array_equal(out["strategy_stop_loss"].to_numpy(float)[retained],olds[retained]),"Changed V1.9 SL"
        assert np.array_equal(out["strategy_target"].to_numpy(float)[retained],oldt[retained]),"Changed V1.9 TP"
        assert np.array_equal(out["signal_reason"].astype(str).to_numpy()[retained],oldreason[retained]),"Changed V1.9 reason"
        assert np.count_nonzero((newp != 0) & (oldp == 0)) == int(keep.sum())
        out.attrs["strategy_diagnostics"] = {
            "version":V20_VERSION, "frozen_baseline":"V1.9", "mode":"ADD_NEW_WINNING_TRADES_ONLY",
            "new_signal_intents":int(keep.sum()), "old_signal_intents_unchanged":True,
            "research_only":True, "live_approved":False,
            "native_algoagentx_verified":False, "forward_untouched_verified":False,
            "parameters":dict(V20_SETTINGS),
            "warning":"2025/2026 reused in research. Local native-like replay only."
        }
        return out

Strategy = NAS100V20AddOnly


# ===== V2.1 FILTER-ONLY RESEARCH OVERLAY =====
# All V2.0 and ancestral strategy logic above is unmodified.
# Existing V2.0 source SHA256: d11620f69ca759006ec8e41c859f2653b3484d6d4b4494f1aec8c65e71d17ee6
V21_VERSION = "NAS100_M5_V2_1_FILTER_EXISTING_LOSING_TRADES_ONLY_RESEARCH"
V21_FILTER_RULES = (
    (
        ("h1_slope", ">=", 0.195587),
        ("macd_atr", ">=", 0.347768),
        ("day_range_atr", "<=", 7.668549),
    ),
    (
        ("atr_relative", ">=", 1.806409),
        ("h1_ema_dist", ">=", 1.213132),
        ("h4_ema_dist", "<=", -1.766317),
    ),
)

class NAS100V21FilterOnly(Strategy):
    """Reject some existing V2.0 signals, never change SL/TP or create signals."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original = out["Position"].to_numpy(dtype=np.int8).copy()
        old_sl = out["strategy_stop_loss"].to_numpy(dtype=float).copy()
        old_tp = out["strategy_target"].to_numpy(dtype=float).copy()
        old_reason = out["signal_reason"].astype(str).to_numpy().copy()
        values, _meta = _v16features_feature_data(out)
        reject = np.zeros(len(out), dtype=bool)
        for group in V21_FILTER_RULES:
            hit = np.ones(len(out), dtype=bool)
            for feature, operation, threshold in group:
                value = values[feature]
                hit &= np.isfinite(value)
                if operation == ">=":
                    hit &= value >= threshold
                elif operation == "<=":
                    hit &= value <= threshold
                else:
                    raise ValueError("Invalid V2.1 filter operation")
            reject |= hit
        reject &= (original != 0)
        out.loc[reject, "Position"] = 0
        out.loc[reject, "strategy_stop_loss"] = np.nan
        out.loc[reject, "strategy_target"] = np.nan
        out.loc[reject, "signal_reason"] = V21_VERSION + "|FILTERED"
        new = out["Position"].to_numpy(dtype=np.int8)
        retained = new != 0
        assert np.all((new == 0) | (new == original)), "V2.1 must never add/alter directions"
        assert np.array_equal(out["strategy_stop_loss"].to_numpy(float)[retained], old_sl[retained]), "V2.1 modified SL"
        assert np.array_equal(out["strategy_target"].to_numpy(float)[retained], old_tp[retained]), "V2.1 modified TP"
        assert np.array_equal(out["signal_reason"].astype(str).to_numpy()[retained], old_reason[retained]), "V2.1 modified baseline signal reasons"
        out.attrs["strategy_diagnostics"] = {
            "version": V21_VERSION,
            "frozen_baseline": "V2.0",
            "mode": "FILTER_EXISTING_LOSING_TRADES_ONLY",
            "filtered_raw_existing_signal_intents": int(reject.sum()),
            "filter_rules": V21_FILTER_RULES,
            "added_signal_intents": 0,
            "stop_target_changes": 0,
            "research_only": True,
            "live_approved": False,
            "native_algoagentx_verified": False,
            "untouched_oos_verified": False,
            "warning": "Historical 2025/2026 have already been inspected; forward demo and broker costs must be independently validated."
        }
        return out

Strategy = NAS100V21FilterOnly


# ===== V2.3 FILTER-ONLY RESEARCH OVERLAY =====
# Frozen V2.1 source above is byte-for-byte identical to the accepted source.
# This filter only removes V2.1 entry intents; stops and targets on all retained intents are unchanged.
V23_VERSION = "NAS100_M5_V2_3_FILTER_ONLY_RESEARCH_CANDIDATE"
V23_FILTER_RULES = ((('stochastic', '<=', 21.850573), ('h1_slope', '>=', 1.203608), ('h4_slope', '>=', 0.284075)), (('ema_spread', '<=', 0.059911), ('h1_ema_dist', '>=', 1.860323), ('h1_slope', '>=', 0.204153)))

class NAS100V23FilterOnly(NAS100V21FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out["Position"].to_numpy(dtype=np.int8).copy()
        original_sl = out["strategy_stop_loss"].to_numpy(dtype=float).copy()
        original_tp = out["strategy_target"].to_numpy(dtype=float).copy()
        original_reason = out["signal_reason"].astype(str).to_numpy().copy()
        feature_values, meta = _v16features_feature_data(out)
        reject = np.zeros(len(out), dtype=bool)
        side = original_p
        for group in V23_FILTER_RULES:
            matched = np.ones(len(out), dtype=bool)
            for feature, operation, threshold in group:
                if feature.endswith("_trend"):
                    context = feature.split("_")[0]
                    rising = meta[context + "_up"]
                    falling = meta[context + "_dn"]
                    condition = np.where(side > 0,
                        rising if threshold == "aligned" else falling,
                        falling if threshold == "aligned" else rising)
                elif feature == "ny_time":
                    condition = (meta["ny_min"] >= threshold[0]) & (meta["ny_min"] < threshold[1])
                elif feature == "weekday":
                    condition = meta["weekday"] == threshold
                elif feature == "side":
                    condition = side == threshold
                else:
                    values = feature_values[feature]
                    condition = np.isfinite(values)
                    if operation == ">=":
                        condition &= values >= threshold
                    elif operation == "<=":
                        condition &= values <= threshold
                    else:
                        raise ValueError("Invalid V2.3 filter operation")
                matched &= condition
            reject |= matched
        reject &= original_p != 0
        out.loc[reject, "Position"] = 0
        out.loc[reject, "strategy_stop_loss"] = np.nan
        out.loc[reject, "strategy_target"] = np.nan
        out.loc[reject, "signal_reason"] = V23_VERSION + "|FILTERED"
        new_p = out["Position"].to_numpy(dtype=np.int8)
        kept = new_p != 0
        assert np.all((new_p == 0) | (new_p == original_p)), "V2.3 changed/added baseline direction"
        assert np.array_equal(out["strategy_stop_loss"].to_numpy(dtype=float)[kept], original_sl[kept]), "V2.3 altered retained stops"
        assert np.array_equal(out["strategy_target"].to_numpy(dtype=float)[kept], original_tp[kept]), "V2.3 altered retained targets"
        assert np.array_equal(out["signal_reason"].astype(str).to_numpy()[kept], original_reason[kept]), "V2.3 altered retained reasons"
        out.attrs["strategy_diagnostics"] = {
            "version": V23_VERSION,
            "frozen_baseline": "V2.1",
            "mode": "FILTER_EXISTING_LOSING_TRADES_ONLY",
            "filtered_existing_raw_intents": int(reject.sum()),
            "added_raw_intents": 0,
            "retained_sl_tp_identical": True,
            "rules": V23_FILTER_RULES,
            "research_only": True,
            "live_approved": False,
            "native_algoagentx_verified": False,
            "untouched_out_of_sample_verified": False,
            "warning": "Historical results reused 2025/26; fresh native/forward validation required.",
        }
        return out

Strategy = NAS100V23FilterOnly


"""Twenty-four incremental NAS100 signal families; based exclusively on completed M5/HTF features."""
import numpy as np
V22_FAMILIES = (
    'Q25_M15_RECLAIM', 'Q75_M15_REJECT', 'PREVDAY_MID_EMA_RECLAIM',
    'M45_EMA20_TREND_REENGAGE', 'M30_EMA20_VOLUME_RETEST', 'H1_EMA50_DEEP_RECLAIM',
    'H4_EMA20_LIQUIDITY_REVERSAL', 'M10_EMA50_M15_CONFLUENCE', 'M15_EMA20_BOS_RETEST',
    'NY_ORB_MIDPOINT_RECLAIM', 'NY_ORB_VWAP_CONFLUENCE', 'ROLLING72_RANGE_SWEEP',
    'ROLLING72_BREAK_PULLBACK', 'VWAP_EMA20_DUAL_RECLAIM', 'MACD_RSI_CAPITULATION',
    'M15_FVG_DOUBLE_CONFIRM', 'M10_BOS_VWAP_FOLLOW', 'M45_BREAK_VOLATILITY_EXPAND',
    'PREVWEEK_HIGH_REJECTION', 'PREVWEEK_LOW_RECLAIM', 'H1_DONCHIAN_TWO_BAR_FOLLOW',
    'M30_EMA50_COUNTER_SWEEP', 'M15_COMPRESS_EMA_ADVANCE', 'STOCH_BB_REJECTION',
)
def v22_raw(f, family):
    if family not in V22_FAMILIES: raise ValueError('Unknown V2.2 family')
    o,h,l,c=(f[x] for x in ('o','h','l','c'))
    pc=f['pc'];ph=f['ph1'];pl=f['pl1'];a=np.maximum(f['atr'],1.e-9)
    up=f['uq'];dn=f['dq'];v=f['volume'];n=len(c)
    E=f['ema20']; E50=f['ema50']; H=f['h1']; M=f['m15']; M10=f['m10']; M30=f['m30']; M45=f['m45']; Q=f['h4']
    # SL is based on the current/previous available structure and is never moved on old signals.
    long_sl=np.minimum(l,pl)-.16*a
    short_sl=np.maximum(h,ph)+.16*a
    if family=='Q25_M15_RECLAIM':
        x=f['week_q25'];bu=(pc<x-.06*a)&(l<x+.15*a)&(c>x+.20*a)&M['up'];bd=(pc>x+.06*a)&(h>x-.15*a)&(c<x-.20*a)&M['dn']
        long_sl=np.minimum(l,x-.55*a)-.16*a;short_sl=np.maximum(h,x+.55*a)+.16*a
    elif family=='Q75_M15_REJECT':
        x=f['week_q75'];bu=(pl<x-.08*a)&(pc<x+.05*a)&(c>x+.18*a)&H['up'];bd=(ph>x+.08*a)&(pc>x-.05*a)&(c<x-.18*a)&H['dn']
        long_sl=np.minimum(l,x-.65*a)-.16*a;short_sl=np.maximum(h,x+.65*a)+.16*a
    elif family=='PREVDAY_MID_EMA_RECLAIM':
        x=f['prevday_mid'];bu=(pc<x-.10*a)&(l<x+.15*a)&(c>x+.20*a)&(c>E)&M['up'];bd=(pc>x+.10*a)&(h>x-.15*a)&(c<x-.20*a)&(c<E)&M['dn']
        long_sl=np.minimum(l,x-.6*a)-.16*a;short_sl=np.maximum(h,x+.6*a)+.16*a
    elif family=='M45_EMA20_TREND_REENGAGE':
        x=M45['e20'];bu=M45['up']&(pc<x)&(l<x+.1*a)&(c>x+.22*a)&H['up'];bd=M45['dn']&(pc>x)&(h>x-.1*a)&(c<x-.22*a)&H['dn']
    elif family=='M30_EMA20_VOLUME_RETEST':
        x=M30['e20'];bu=M30['up']&(pc<=x+.25*a)&(l<x+.1*a)&(c>x+.25*a)&(v>1.2);bd=M30['dn']&(pc>=x-.25*a)&(h>x-.1*a)&(c<x-.25*a)&(v>1.2)
    elif family=='H1_EMA50_DEEP_RECLAIM':
        x=H['e50'];bu=(pc<x-.15*a)&(l<x+.1*a)&(c>x+.22*a)&H['up'];bd=(pc>x+.15*a)&(h>x-.1*a)&(c<x-.22*a)&H['dn']
    elif family=='H4_EMA20_LIQUIDITY_REVERSAL':
        x=Q['e20'];bu=(pl<x-.24*a)&(l<x-.35*a)&(c>x+.15*a)&(f['rsi']<58);bd=(ph>x+.24*a)&(h>x+.35*a)&(c<x-.15*a)&(f['rsi']>42)
        long_sl=np.minimum(l,x-.50*a)-.16*a;short_sl=np.maximum(h,x+.50*a)+.16*a
    elif family=='M10_EMA50_M15_CONFLUENCE':
        x=M10['e50'];bu=M10['up']&M['up']&(pc<x+.1*a)&(l<x+.15*a)&(c>x+.25*a);bd=M10['dn']&M['dn']&(pc>x-.1*a)&(h>x-.15*a)&(c<x-.25*a)
    elif family=='M15_EMA20_BOS_RETEST':
        x=M['e20'];bu=np.isfinite(f['m15_bos_up'])&M['up']&(l<x+.15*a)&(c>x+.18*a)&(pc<x+.35*a);bd=np.isfinite(f['m15_bos_dn'])&M['dn']&(h>x-.15*a)&(c<x-.18*a)&(pc>x-.35*a)
    elif family=='NY_ORB_MIDPOINT_RECLAIM':
        x=(f['orb_hi']+f['orb_lo'])*.5;bu=(pc<x-.1*a)&(l<x+.1*a)&(c>x+.24*a)&(c>f['vwap']);bd=(pc>x+.1*a)&(h>x-.1*a)&(c<x-.24*a)&(c<f['vwap'])
        long_sl=np.minimum(l,x-.65*a)-.16*a;short_sl=np.maximum(h,x+.65*a)+.16*a
    elif family=='NY_ORB_VWAP_CONFLUENCE':
        x=f['orb_hi'];y=f['orb_lo'];z=f['vwap'];bu=(pc<x+.15*a)&(l<x+.15*a)&(c>x+.26*a)&(c>z+.1*a);bd=(pc>y-.15*a)&(h>y-.15*a)&(c<y-.26*a)&(c<z-.1*a)
        long_sl=np.minimum(l,x-.7*a)-.16*a;short_sl=np.maximum(h,y+.7*a)+.16*a
    elif family=='ROLLING72_RANGE_SWEEP':
        x=f['low72'];y=f['high72'];bu=(l<x-.12*a)&(c>x+.18*a)&(f['rsi']<55);bd=(h>y+.12*a)&(c<y-.18*a)&(f['rsi']>45)
        long_sl=np.minimum(l,x)-.16*a;short_sl=np.maximum(h,y)+.16*a
    elif family=='ROLLING72_BREAK_PULLBACK':
        x=f['high72'];y=f['low72'];bu=(pc<x+.22*a)&(l<x+.1*a)&(c>x+.25*a)&H['up'];bd=(pc>y-.22*a)&(h>y-.1*a)&(c<y-.25*a)&H['dn']
        long_sl=np.minimum(l,x-.75*a)-.16*a;short_sl=np.maximum(h,y+.75*a)+.16*a
    elif family=='VWAP_EMA20_DUAL_RECLAIM':
        x=f['vwap'];bu=(pc<x-.08*a)&(l<E+.15*a)&(c>x+.22*a)&(c>E+.12*a)&(f['macdh']>0);bd=(pc>x+.08*a)&(h>E-.15*a)&(c<x-.22*a)&(c<E-.12*a)&(f['macdh']<0)
    elif family=='MACD_RSI_CAPITULATION':
        x=f['bb_low'];y=f['bb_hi'];bu=(l<x-.15*a)&(pc<E)&(c>E-.1*a)&(f['rsi']<45)&(f['macdh']>0);bd=(h>y+.15*a)&(pc>E)&(c<E+.1*a)&(f['rsi']>55)&(f['macdh']<0)
        long_sl=np.minimum(l,x)-.16*a;short_sl=np.maximum(h,y)+.16*a
    elif family=='M15_FVG_DOUBLE_CONFIRM':
        bu=np.isfinite(f['m15_fvg_up'])&(pl<f['m15_fvg_up']+.2*a)&(c>f['m15_fvg_up']+.15*a)&(c>E)&H['up'];bd=np.isfinite(f['m15_fvg_dn'])&(ph>f['m15_fvg_dn']-.2*a)&(c<f['m15_fvg_dn']-.15*a)&(c<E)&H['dn']
    elif family=='M10_BOS_VWAP_FOLLOW':
        bu=np.isfinite(f['m10_bos_up'])&(pc<f['m10_bos_up']+.2*a)&(c>f['m10_bos_up']+.18*a)&(c>f['vwap'])&M10['up'];bd=np.isfinite(f['m10_bos_dn'])&(pc>f['m10_bos_dn']-.2*a)&(c<f['m10_bos_dn']-.18*a)&(c<f['vwap'])&M10['dn']
    elif family=='M45_BREAK_VOLATILITY_EXPAND':
        x=M45['hi12'];y=M45['lo12'];bu=(pc<x+.12*a)&(c>x+.20*a)&M45['up']&(f['atrrel']>1.2);bd=(pc>y-.12*a)&(c<y-.20*a)&M45['dn']&(f['atrrel']>1.2)
    elif family=='PREVWEEK_HIGH_REJECTION':
        x=f['week_hi'];bu=(pl<x-.08*a)&(c>x+.25*a)&H['up'];bd=(h>x+.1*a)&(pc>x-.15*a)&(c<x-.22*a)&(f['rsi']>48)
        long_sl=np.minimum(l,x-.6*a)-.16*a;short_sl=np.maximum(h,x+.6*a)+.16*a
    elif family=='PREVWEEK_LOW_RECLAIM':
        x=f['week_lo'];bu=(l<x-.1*a)&(pc<x+.15*a)&(c>x+.22*a)&(f['rsi']<52);bd=(ph>x+.08*a)&(c<x-.25*a)&H['dn']
        long_sl=np.minimum(l,x-.6*a)-.16*a;short_sl=np.maximum(h,x+.6*a)+.16*a
    elif family=='H1_DONCHIAN_TWO_BAR_FOLLOW':
        x=H['hi12'];y=H['lo12'];bu=(pl<x+.05*a)&(pc>x)&(c>ph+.08*a)&H['up'];bd=(ph>y-.05*a)&(pc<y)&(c<pl-.08*a)&H['dn']
        long_sl=np.minimum(l,x-.8*a)-.16*a;short_sl=np.maximum(h,y+.8*a)+.16*a
    elif family=='M30_EMA50_COUNTER_SWEEP':
        x=M30['e50'];bu=M30['dn']&(l<x-.3*a)&(pc<x)&(c>x+.12*a)&(up>.68);bd=M30['up']&(h>x+.3*a)&(pc>x)&(c<x-.12*a)&(dn>.68)
    elif family=='M15_COMPRESS_EMA_ADVANCE':
        x=M['e20'];bu=np.isfinite(f['m15_comp_up'])&(pc<x+.25*a)&(c>x+.18*a)&(v>.8);bd=np.isfinite(f['m15_comp_dn'])&(pc>x-.25*a)&(c<x-.18*a)&(v>.8)
    elif family=='STOCH_BB_REJECTION':
        x=f['bb_low'];y=f['bb_hi'];bu=(l<x)&(c>x+.1*a)&(f['stoch']<30)&(up>.7);bd=(h>y)&(c<y-.1*a)&(f['stoch']>70)&(dn>.7)
    # All signal predicates require bar close confirmation and structure SL validity.
    bu &= (c>o)&(up>.53);bd &= (c<o)&(dn>.53)
    bu &= np.isfinite(long_sl)&(c-long_sl>=.2*a)&(c-long_sl<=6*a)
    bd &= np.isfinite(short_sl)&(short_sl-c>=.2*a)&(short_sl-c<=6*a)
    collision=bu&bd
    p=np.where(bu&~collision,1,np.where(bd&~collision,-1,0)).astype(np.int8)
    stops=np.where(p>0,long_sl,np.where(p<0,short_sl,np.nan))
    return p,stops


"""New V2.4 entry families, strictly calculated from closed M5 and projected CLOSED HTF features."""
import numpy as np
V24_FAMILIES=(
'H4_EMA50_SNAPBACK','M45_DONCHIAN_RETEST','M30_SWING_TRAP','WEEK_Q35_RECLAIM',
'WEEK_Q65_RECLAIM','PREVDAY_HIGH_FALSEBREAK','PREVDAY_LOW_FALSEBREAK',
'H1_EMA20_OVEREXTENSION_FADE','M10_VWAP_PULLBACK','BB_SQUEEZE_BREAKOUT',
'RSI_MOMENTUM_REVERSAL','M15_FVG_SECOND_TOUCH','M5_INSIDE_BAR_BREAKOUT',
'M30_EMA50_CONTINUATION','M45_VWAP_DUAL_TREND','H1_DONCHIAN_MID_RECLAIM',
'WEEK_MID_MOMENTUM_RETEST','VOLUME_BOS_EXTENSION','M5_ENGULF_SR_REJECTION',
'H1_VWAP_LIQUIDITY_FLIP')

def v24_raw(f, family):
    if family not in V24_FAMILIES: raise ValueError(family)
    o,h,l,c=(f[k] for k in ('o','h','l','c'))
    a=np.maximum(f['atr'],1e-9); pc=f['pc']; ph=f['ph1']; pl=f['pl1'];
    m10=f['m10'];m15=f['m15'];m30=f['m30'];m45=f['m45'];h1=f['h1'];h4=f['h4']
    ls=np.minimum(l,pl)-.16*a;ss=np.maximum(h,ph)+.16*a
    up=np.zeros(len(c),bool);dn=np.zeros(len(c),bool)
    if family=='H4_EMA50_SNAPBACK':
        x=h4['e50'];up=(pc<x-.10*a)&(l<x-.25*a)&(c>x+.18*a)&m15['up'];dn=(pc>x+.10*a)&(h>x+.25*a)&(c<x-.18*a)&m15['dn']
    elif family=='M45_DONCHIAN_RETEST':
        x=m45['hi12'];y=m45['lo12'];up=m45['up']&h1['up']&(pc<x+.12*a)&(l<x+.14*a)&(c>x+.20*a);dn=m45['dn']&h1['dn']&(pc>y-.12*a)&(h>y-.14*a)&(c<y-.20*a)
        ls=np.minimum(l,x-.70*a)-.16*a;ss=np.maximum(h,y+.70*a)+.16*a
    elif family=='M30_SWING_TRAP':
        x=m30['lo12'];y=m30['hi12'];up=(l<x-.10*a)&(c>x+.15*a)&(f['rsi']<60);dn=(h>y+.10*a)&(c<y-.15*a)&(f['rsi']>40)
        ls=np.minimum(l,x)-.16*a;ss=np.maximum(h,y)+.16*a
    elif family in ('WEEK_Q35_RECLAIM','WEEK_Q65_RECLAIM'):
        x=f['week_lo']+(.35 if family=='WEEK_Q35_RECLAIM' else .65)*(f['week_hi']-f['week_lo'])
        up=(pc<x+.15*a)&(l<x+.10*a)&(c>x+.20*a)&m15['up'];dn=(pc>x-.15*a)&(h>x-.10*a)&(c<x-.20*a)&m15['dn']
        ls=np.minimum(l,x-.60*a)-.16*a;ss=np.maximum(h,x+.60*a)+.16*a
    elif family=='PREVDAY_HIGH_FALSEBREAK':
        x=f['pdh'];up=(pc<x-.20*a)&(l<x-.15*a)&(c>x+.20*a)&h1['up'];dn=(h>x+.10*a)&(pc>x-.20*a)&(c<x-.20*a)
        ls=np.minimum(l,x-.75*a)-.16*a;ss=np.maximum(h,x+.75*a)+.16*a
    elif family=='PREVDAY_LOW_FALSEBREAK':
        x=f['pdl'];up=(l<x-.10*a)&(pc<x+.20*a)&(c>x+.18*a);dn=(pc>x+.20*a)&(h>x+.15*a)&(c<x-.22*a)&h1['dn']
        ls=np.minimum(l,x-.75*a)-.16*a;ss=np.maximum(h,x+.75*a)+.16*a
    elif family=='H1_EMA20_OVEREXTENSION_FADE':
        x=h1['e20'];up=(pc<x-1.0*a)&(l<x-1.4*a)&(c>pc+.30*a)&(f['rsi']<48);dn=(pc>x+1.0*a)&(h>x+1.4*a)&(c<pc-.30*a)&(f['rsi']>52)
    elif family=='M10_VWAP_PULLBACK':
        x=f['vwap'];up=m10['up']&h1['up']&(pc<x+.18*a)&(l<x+.1*a)&(c>x+.22*a);dn=m10['dn']&h1['dn']&(pc>x-.18*a)&(h>x-.1*a)&(c<x-.22*a)
    elif family=='BB_SQUEEZE_BREAKOUT':
        x=f['bb_hi'];y=f['bb_low'];wd=(x-y)/a
        up=(wd<5.2)&(pc<x+.1*a)&(c>x+.16*a)&h1['up'];dn=(wd<5.2)&(pc>y-.1*a)&(c<y-.16*a)&h1['dn']
    elif family=='RSI_MOMENTUM_REVERSAL':
        up=(f['rsi']<47)&(f['macdh']>0)&(l<f['low24']+.18*a)&(c>pc+.15*a);dn=(f['rsi']>53)&(f['macdh']<0)&(h>f['high24']-.18*a)&(c<pc-.15*a)
    elif family=='M15_FVG_SECOND_TOUCH':
        x=f['m15_fvg_up'];y=f['m15_fvg_dn'];up=np.isfinite(x)&m15['up']&(pl<x+.20*a)&(l<x+.14*a)&(c>x+.18*a)&(f['macdh']>0);dn=np.isfinite(y)&m15['dn']&(ph>y-.20*a)&(h>y-.14*a)&(c<y-.18*a)&(f['macdh']<0)
        ls=np.minimum(l,x-.55*a)-.16*a;ss=np.maximum(h,y+.55*a)+.16*a
    elif family=='M5_INSIDE_BAR_BREAKOUT':
        inside=(ph<=f['ph2'])&(pl>=f['pl2']);up=inside&(pc<ph+.08*a)&(c>ph+.12*a)&h1['up'];dn=inside&(pc>pl-.08*a)&(c<pl-.12*a)&h1['dn']
    elif family=='M30_EMA50_CONTINUATION':
        x=m30['e50'];up=m30['up']&h1['up']&(l<x+.15*a)&(c>x+.27*a)&(pc<x+.45*a);dn=m30['dn']&h1['dn']&(h>x-.15*a)&(c<x-.27*a)&(pc>x-.45*a)
    elif family=='M45_VWAP_DUAL_TREND':
        x=f['vwap'];up=m45['up']&h1['up']&(pc<x+.1*a)&(l<x+.1*a)&(c>x+.2*a);dn=m45['dn']&h1['dn']&(pc>x-.1*a)&(h>x-.1*a)&(c<x-.2*a)
    elif family=='H1_DONCHIAN_MID_RECLAIM':
        x=(h1['lo12']+h1['hi12'])/2;up=h1['up']&(pc<x)&(l<x+.1*a)&(c>x+.2*a);dn=h1['dn']&(pc>x)&(h>x-.1*a)&(c<x-.2*a)
        ls=np.minimum(l,x-.7*a)-.16*a;ss=np.maximum(h,x+.7*a)+.16*a
    elif family=='WEEK_MID_MOMENTUM_RETEST':
        x=f['week_mid'];up=(pc<x+.12*a)&(l<x+.1*a)&(c>x+.22*a)&(f['macdh']>0);dn=(pc>x-.12*a)&(h>x-.1*a)&(c<x-.22*a)&(f['macdh']<0)
        ls=np.minimum(l,x-.65*a)-.16*a;ss=np.maximum(h,x+.65*a)+.16*a
    elif family=='VOLUME_BOS_EXTENSION':
        x=f['high24'];y=f['low24'];up=(f['volume']>1.35)&(pc<x+.06*a)&(c>x+.22*a)&(f['macdh']>.06*a);dn=(f['volume']>1.35)&(pc>y-.06*a)&(c<y-.22*a)&(f['macdh']<-.06*a)
        ls=np.minimum(l,x-.75*a)-.16*a;ss=np.maximum(h,y+.75*a)+.16*a
    elif family=='M5_ENGULF_SR_REJECTION':
        up=(pc<f['po1'])&(o<pc+.08*a)&(c>f['po1']+.12*a)&(l<f['low24']+.25*a)&m15['up'];dn=(pc>f['po1'])&(o>pc-.08*a)&(c<f['po1']-.12*a)&(h>f['high24']-.25*a)&m15['dn']
    elif family=='H1_VWAP_LIQUIDITY_FLIP':
        x=f['vwap'];up=(pl<x-.12*a)&(l<x-.20*a)&(c>x+.22*a)&h1['up'];dn=(ph>x+.12*a)&(h>x+.20*a)&(c<x-.22*a)&h1['dn']
    up &= (c>o)&(f['uq']>.53)&np.isfinite(ls)&((c-ls)>.2*a)&((c-ls)<6*a)
    dn &= (c<o)&(f['dq']>.53)&np.isfinite(ss)&((ss-c)>.2*a)&((ss-c)<6*a)
    both=up&dn;p=np.where(up&~both,1,np.where(dn&~both,-1,0)).astype(np.int8)
    stop=np.where(p>0,ls,np.where(p<0,ss,np.nan))
    return p,stop


"""Minimal closed-bar market bank for the three selected V2.4 family predicates.
Identical indicator formulae to frozen _v14bank/_v15bank/_v17bank feature builders,
without unnecessary weekly, M10, M45 and H4 resampling of the output frame.
"""
def _v24_minimal_bank(d):
    f = _v14bank_make_bank(d)
    # Source names used by v22_raw/v24_raw; selected families do not use M10/M45/H4.
    f['m10'] = {}
    f['m45'] = {}
    f['h4'] = {}
    o,h,l,c = (f[x] for x in ('o','h','l','c'))
    a = np.maximum(f['atr'],1e-9)
    f['ph1'] = np.r_[np.nan,h[:-1]]
    f['pl1'] = np.r_[np.nan,l[:-1]]
    f['ema20'] = pd.Series(c).ewm(span=20,adjust=False).mean().to_numpy(float)
    f['ema50'] = pd.Series(c).ewm(span=50,adjust=False).mean().to_numpy(float)
    dt = pd.to_datetime(d['Date'],utc=True).dt.tz_localize(None)
    close_t = (dt + pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    m15, f['m15'], i15, t15 = _v15bank_htf_projection(d,'15min',3,15,close_t)
    _, f['m30'], _, _ = _v15bank_htf_projection(d,'30min',6,30,close_t)
    _, f['h1'], _, _ = _v15bank_htf_projection(d,'1h',12,60,close_t)
    mh = m15.High.to_numpy(float)
    ml = m15.Low.to_numpy(float)
    mc = m15.Close.to_numpy(float)
    ma = m15.atr.to_numpy(float)
    pastwidth = pd.Series(mh).shift(1).rolling(8,min_periods=8).max() - pd.Series(ml).shift(1).rolling(8,min_periods=8).min()
    compact = pastwidth.to_numpy(float)/np.maximum(ma,1e-9) < 3.8
    m15hi = m15.hi12.to_numpy(float)
    m15lo = m15.lo12.to_numpy(float)
    f['m15_comp_up'] = _v15bank_last_event(m15,i15,t15,compact & (mc>m15hi),m15hi,close_t,3)
    f['m15_comp_dn'] = _v15bank_last_event(m15,i15,t15,compact & (mc<m15lo),m15lo,close_t,3)
    dkey=dt.dt.floor('D')
    gp = pd.DataFrame({'day':dkey,'h':h,'l':l}).groupby('day',sort=True).agg(hi=('h','max'),lo=('l','min')).shift(1)
    f['pdh'] = gp.hi.reindex(dkey).to_numpy(float)
    f['pdl'] = gp.lo.reindex(dkey).to_numpy(float)
    change = np.r_[0,np.diff(c)]
    gain=pd.Series(np.maximum(change,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    loss=pd.Series(np.maximum(-change,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    f['rsi']=100*gain/np.maximum(gain+loss,1e-10)
    high14=pd.Series(h).rolling(14,min_periods=14).max().to_numpy(float)
    low14=pd.Series(l).rolling(14,min_periods=14).min().to_numpy(float)
    f['stoch'] = 100*(c-low14)/np.maximum(high14-low14,1e-10)
    # ADX source formula matches _v16features_feature_data exactly.
    hd=np.r_[0.0,np.diff(h)];ld=np.r_[0.0,-np.diff(l)]
    plus=np.where((hd>ld)&(hd>0),hd,0.0)
    minus=np.where((ld>hd)&(ld>0),ld,0.0)
    prev=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-prev),abs(l-prev)))
    atradx=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    plusdi=100*pd.Series(plus).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(atradx,1e-9)
    minusdi=100*pd.Series(minus).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(atradx,1e-9)
    dx=100*abs(plusdi-minusdi)/np.maximum(plusdi+minusdi,1e-9)
    f['adx'] = pd.Series(dx).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    return f


# ===== V2.4 ADD-NEW-WINNING-TRADES-ONLY EXPERIMENT =====
# Accepted V2.3 is preserved byte-identically before this section.
# This is a research-only candidate. Do not auto-deploy or promote.
V24_VERSION = "NAS100_M5_V2_4_ADD_ONLY_RESEARCH_CANDIDATE"
V24_NEW_ENTRY_GROUPS = ({'family_index': 29, 'family': 'PREVDAY_HIGH_FALSEBREAK', 'side': 'both', 'session': [570, 870], 'body': 0.3199999928474426, 'quality': 0.6200000047683716, 'vol': 1.2999999523162842, 'atrrel': 1.2000000476837158, 'max_stop_atr': 5.0, 'trend': 'none', 'screen_score': 95.64962005615234, 'dev_n': 224, 'dev_R': 23.489295959472656, '2025_n': 68, '2025_R': 37.20322036743164, '2026_independent_n': 52, '2026_independent_R': 8.008219718933105, 'gates': [['stoch_dir', '>=', 65.0], ['stop_atr', '<=', 1.65]]}, {'family_index': 26, 'family': 'M30_SWING_TRAP', 'side': 'long', 'session': [570, 960], 'body': 0.18000000715255737, 'quality': 0.7200000286102295, 'vol': 0.6499999761581421, 'atrrel': 0.949999988079071, 'max_stop_atr': 2.0, 'trend': 'none', 'screen_score': 120.91786193847656, 'dev_n': 607, 'dev_R': 58.82960510253906, '2025_n': 186, '2025_R': 46.405479431152344, '2026_independent_n': 142, '2026_independent_R': 18.06951904296875, 'gates': [['adx', '<=', 19.0]]}, {'family_index': 22, 'family': 'M15_COMPRESS_EMA_ADVANCE', 'side': 'both', 'session': [570, 960], 'body': 0.0, 'quality': 0.5299999713897705, 'vol': 1.2999999523162842, 'atrrel': 0.0, 'max_stop_atr': 3.200000047683716, 'trend': 'm30', 'screen_score': 74.3530044555664, 'dev_n': 62, 'dev_R': 17.08639907836914, '2025_n': 39, '2025_R': 29.528697967529297, '2026_independent_n': 28, '2026_independent_R': -0.06734108924865723, 'gates': [['stoch_dir', '<=', 40.0]]})

class NAS100V24AddOnly(NAS100V23FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out['Position'].to_numpy(dtype=np.int8).copy()
        original_stop = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        original_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        original_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        market = pd.DataFrame({k:out[k].to_numpy(copy=False) for k in
            ('Date','Open','High','Low','Close','Volume')})
        f = _v24_minimal_bank(market)
        feature_values = {'stochastic':f['stoch'], 'adx':f['adx']}
        n = len(out)
        ix = np.arange(n)
        atr = np.maximum(f['atr'], 1e-9)
        newly_added = np.zeros(n, bool)
        group_counts = {}
        for conf in V24_NEW_ENTRY_GROUPS:
            family = conf['family']
            if family in V22_FAMILIES:
                prop, stop = v22_raw(f, family)
            elif family in V24_FAMILIES:
                prop, stop = v24_raw(f, family)
            else:
                raise ValueError('Unknown V2.4 new entry family: '+family)
            quality = np.where(prop > 0, f['uq'], f['dq'])
            begin, end = conf['session']
            mask = (
                (prop != 0) &
                (original_p == 0) &
                (~newly_added) &
                (ix >= self.LIVE_HISTORY_BARS) & (ix < n-1) &
                (f['dow'] < 5) &
                (f['minute'] >= begin) & (f['minute'] < end) &
                (f['body'] >= conf['body'] - 1e-6) &
                (quality >= conf['quality'] - 1e-6) &
                (f['volume'] >= conf['vol'] - 1e-6) &
                (f['atrrel'] >= conf['atrrel'] - 1e-6) &
                (np.abs(f['c']-stop)/atr <= conf['max_stop_atr'] + 1e-6) &
                np.isfinite(stop)
            )
            if conf['side'] == 'long':
                mask &= prop == 1
            elif conf['side'] == 'short':
                mask &= prop == -1
            if conf['trend'] != 'none':
                t = f[conf['trend']]
                mask &= np.where(prop > 0, t['up'], t['dn'])
            for name, op, value in conf['gates']:
                if name == 'stoch_dir':
                    measured = np.where(prop > 0, feature_values['stochastic'], 100.0-feature_values['stochastic'])
                elif name == 'adx':
                    measured = feature_values['adx']
                elif name == 'stop_atr':
                    measured = np.abs(f['c']-stop)/atr
                else:
                    raise ValueError('Unsupported V2.4 condition '+name)
                mask &= np.isfinite(measured) & (
                    (measured <= value) if op == '<=' else (measured >= value)
                )
            out.loc[mask,'Position'] = prop[mask]
            out.loc[mask,'strategy_stop_loss'] = stop[mask]
            out.loc[mask,'strategy_target'] = (f['c'] + prop*3.0*np.abs(f['c']-stop))[mask]
            out.loc[mask,'signal_reason'] = V24_VERSION + '|NEW_ENTRY|' + family
            newly_added |= mask
            group_counts[family] = int(mask.sum())
        latest_p = out['Position'].to_numpy(dtype=np.int8)
        old = original_p != 0
        assert np.array_equal(latest_p[old],original_p[old]), 'Baseline signals modified'
        assert np.array_equal(out['strategy_stop_loss'].to_numpy(dtype=float)[old],original_stop[old]), 'Old stop changed'
        assert np.array_equal(out['strategy_target'].to_numpy(dtype=float)[old],original_tp[old]), 'Old target changed'
        assert np.array_equal(out['signal_reason'].fillna('').astype(str).to_numpy()[old],original_reason[old]), 'Old signal reason changed'
        assert np.count_nonzero(latest_p[~old]) == np.count_nonzero(newly_added), 'Unexpected new raw signals'
        out.attrs['strategy_diagnostics'] = dict(
            version=V24_VERSION,frozen_baseline='V2.3',
            mode='ADD_NEW_WINNING_TRADES_ONLY',
            baseline_signals_unchanged=True,
            new_raw_intents=int(newly_added.sum()),
            new_group_intents=group_counts,
            retained_sl_tp_identical=True,
            research_only=True,native_algoagentx_verified=False,
            untouched_out_of_sample_verified=False,
            warning='Research-only historical local replay; 2025–2026 repeatedly researched; native AlgoAgentX validation required.'
        )
        return out

Strategy = NAS100V24AddOnly


# ===== V2.5 FILTER-ONLY RESEARCH OVERLAY =====
# The entire accepted V2.4 source above is preserved byte-for-byte.
# No entry discovery, no SL/TP changes, no additional raw entries.
V25_VERSION = "NAS100_M5_V2_5_FILTER_ONLY_RESEARCH_CANDIDATE"
V25_FILTER_RULES = ((('ema_spread', '>=', 1.471932), ('stochastic', '>=', 97.486882), ('h1_ema_dist', '>=', 8.957477)), (('stochastic', '>=', 97.486882), ('h1_slope', '<=', -1.187094)))

class NAS100V25FilterOnly(NAS100V24AddOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        old_p = out["Position"].to_numpy(dtype=np.int8).copy()
        old_sl = out["strategy_stop_loss"].to_numpy(dtype=float).copy()
        old_tp = out["strategy_target"].to_numpy(dtype=float).copy()
        old_reason = out["signal_reason"].fillna("").astype(str).to_numpy().copy()
        values, _meta = _v16features_feature_data(out)
        rejected = np.zeros(len(out), dtype=bool)
        for group in V25_FILTER_RULES:
            group_hit = np.ones(len(out), dtype=bool)
            for feature, op, threshold in group:
                observed = values[feature]
                group_hit &= np.isfinite(observed)
                if op == ">=":
                    group_hit &= observed >= threshold
                elif op == "<=":
                    group_hit &= observed <= threshold
                else:
                    raise ValueError("Unsupported V2.5 filter operator: " + str(op))
            rejected |= group_hit
        rejected &= old_p != 0
        out.loc[rejected, "Position"] = 0
        out.loc[rejected, "strategy_stop_loss"] = np.nan
        out.loc[rejected, "strategy_target"] = np.nan
        out.loc[rejected, "signal_reason"] = V25_VERSION + "|FILTERED"
        new_p = out["Position"].to_numpy(dtype=np.int8)
        kept = new_p != 0
        assert np.all((new_p == 0) | (new_p == old_p)), "V2.5 created/changed a signal"
        assert np.array_equal(out["strategy_stop_loss"].to_numpy(dtype=float)[kept],old_sl[kept]), "V2.5 changed SL"
        assert np.array_equal(out["strategy_target"].to_numpy(dtype=float)[kept],old_tp[kept]), "V2.5 changed TP"
        assert np.array_equal(out["signal_reason"].fillna("").astype(str).to_numpy()[kept],old_reason[kept]), "V2.5 changed signal reason"
        out.attrs["strategy_diagnostics"] = dict(
            version=V25_VERSION, frozen_baseline="V2.4",
            mode="FILTER_EXISTING_LOSING_TRADES_ONLY",
            rejected_baseline_raw_intents=int(rejected.sum()), new_raw_signal_intents=0,
            retained_sl_tp_identical=True, filters=V25_FILTER_RULES,
            research_only=True, native_algoagentx_verified=False,
            untouched_out_of_sample_verified=False,
            warning="2022-2026 researched repeatedly. Local model only; native and forward validation required.")
        return out

Strategy = NAS100V25FilterOnly


# ===== V2.6 NEW-ENTRY ONLY RESEARCH OVERLAY =====
# Full frozen V2.5 strategy above is preserved byte for byte.
# Experimental add-only signals; no baseline source or existing trade parameters changed.
"""Experimental V2.6 entry families computed solely from closed M5 bars and completed HTF flags.
Zero future-candle reads: shifted rolling levels, already closed H1/M15 state, current closed M5 bar.
"""
V26_FAMILIES=(
 'RANGE48_LIQUIDITY_RECLAIM', 'RANGE96_LIQUIDITY_RECLAIM',
 'RANGE48_BREAKOUT_HOLD', 'RANGE96_BREAKOUT_HOLD',
 'VWAP_VOLUME_TREND_RECLAIM','VWAP_COUNTER_SWEEP',
 'EMA50_PULLBACK_M15','EMA20_PULLBACK_H1',
 'PREVDAY_MID_BREAK_RETEST','PREVDAY_LOW_HIGH_SWEEP',
 'BOLLINGER_MID_MOMENTUM_FLIP','BOLLINGER_OUTER_REVERSAL',
 'ENGULFING_EMA50_PULLBACK', 'THREE_BAR_MOMENTUM_CONTINUATION',
 'M15_TREND_ATR_EXPANSION','H1_TREND_TWO_BAR_REVERSAL',
 'ROLLING24_REJECTION_VOLUME','ROLLING72_BREAK_AND_RECLAIM',
 'STOCH_RSI_LIQUIDITY_FLIP','M5_BB_SQUEEZE_DISPLACEMENT')

def v26_bank(d,f):
 o,h,l,c=(np.asarray(d[k],dtype=float) for k in ('Open','High','Low','Close'))
 vol=np.asarray(d['Volume'],dtype=float)
 a=np.maximum(f['atr'],1e-9)
 ser=pd.Series(c)
 e20=ser.ewm(span=20,adjust=False).mean().to_numpy(float)
 e50=ser.ewm(span=50,adjust=False).mean().to_numpy(float)
 r20=ser.rolling(20,min_periods=20)
 bbmid=r20.mean().to_numpy(float)
 bbstd=r20.std(ddof=0).to_numpy(float)
 rhi={k:pd.Series(h).shift(1).rolling(k,min_periods=k).max().to_numpy(float) for k in (24,48,72,96)}
 rlo={k:pd.Series(l).shift(1).rolling(k,min_periods=k).min().to_numpy(float) for k in (24,48,72,96)}
 # Daily VWAP uses only observed data through the current closed bar, never full-day future totals.
 date=pd.to_datetime(d['Date'],utc=True).dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
 typ=(h+l+c)/3.
 v0=np.maximum(vol,0)
 df=pd.DataFrame({'key':date,'cv':typ*v0,'v':v0})
 cumcv=df.groupby('key',sort=False)['cv'].cumsum().to_numpy(float)
 cumv=df.groupby('key',sort=False)['v'].cumsum().to_numpy(float)
 vw=np.where(cumv>0,cumcv/np.maximum(cumv,1e-9),c)
 # previous full UTC day high/low: shift entire group's aggregate to previous day.
 utcday=pd.to_datetime(d['Date'],utc=True).dt.floor('D')
 g=pd.DataFrame({'day':utcday,'hi':h,'lo':l}).groupby('day',sort=True).agg(hi=('hi','max'),lo=('lo','min')).shift(1)
 pdh=g.hi.reindex(utcday).to_numpy(float);pdl=g.lo.reindex(utcday).to_numpy(float)
 high14=pd.Series(h).rolling(14,min_periods=14).max().to_numpy(float)
 low14=pd.Series(l).rolling(14,min_periods=14).min().to_numpy(float)
 stoch=100*(c-low14)/np.maximum(high14-low14,1e-10)
 pc=np.r_[np.nan,c[:-1]]
 dlt=np.r_[0.,np.diff(c)]
 up=pd.Series(np.maximum(dlt,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
 dn=pd.Series(np.maximum(-dlt,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
 rsi=100*up/np.maximum(up+dn,1e-9)
 return dict(o=o,h=h,l=l,c=c,pc=pc,vol=vol,atr=a,e20=e20,e50=e50,
             bbmid=bbmid,bbstd=bbstd,vwap=vw,pdh=pdh,pdl=pdl,rsi=rsi,stoch=stoch,
             rhi=rhi,rlo=rlo,ph=np.r_[np.nan,h[:-1]],pl=np.r_[np.nan,l[:-1]],
             po=np.r_[np.nan,o[:-1]],pc2=np.r_[np.nan,np.nan,c[:-2]],
             h1_up=np.asarray(f['h1']['up'],bool),h1_dn=np.asarray(f['h1']['dn'],bool),
             m15_up=np.asarray(f['m15']['up'],bool),m15_dn=np.asarray(f['m15']['dn'],bool),
             m30_up=np.asarray(f['m30']['up'],bool),m30_dn=np.asarray(f['m30']['dn'],bool))

def v26_raw(f,name):
 if name not in V26_FAMILIES:raise ValueError('unknown family: '+str(name))
 o,h,l,c,pc=(f[k] for k in ('o','h','l','c','pc'))
 a=f['atr'];ph=f['ph'];pl=f['pl'];e20=f['e20'];e50=f['e50'];v=f['vwap']
 hr48=f['rhi'][48];lr48=f['rlo'][48];hr96=f['rhi'][96];lr96=f['rlo'][96]
 h1u=f['h1_up'];h1d=f['h1_dn'];m15u=f['m15_up'];m15d=f['m15_dn'];m30u=f['m30_up'];m30d=f['m30_dn']
 up=np.zeros(len(c),dtype=bool);dn=up.copy()
 ls=np.minimum(l,pl)-.16*a;ss=np.maximum(h,ph)+.16*a
 if name=='RANGE48_LIQUIDITY_RECLAIM':
  x=lr48;y=hr48;up=(l<x-.09*a)&(c>x+.16*a)&(pc<x+.25*a);dn=(h>y+.09*a)&(c<y-.16*a)&(pc>y-.25*a)
 elif name=='RANGE96_LIQUIDITY_RECLAIM':
  x=lr96;y=hr96;up=(l<x-.10*a)&(c>x+.22*a)&(pc<x+.30*a);dn=(h>y+.10*a)&(c<y-.22*a)&(pc>y-.30*a)
 elif name=='RANGE48_BREAKOUT_HOLD':
  x=hr48;y=lr48;up=(pc<x+.12*a)&(l<x+.18*a)&(c>x+.27*a)&m15u;dn=(pc>y-.12*a)&(h>y-.18*a)&(c<y-.27*a)&m15d
  ls=np.minimum(l,x-.80*a)-.16*a;ss=np.maximum(h,y+.80*a)+.16*a
 elif name=='RANGE96_BREAKOUT_HOLD':
  x=hr96;y=lr96;up=(pc<x+.12*a)&(l<x+.15*a)&(c>x+.24*a)&h1u;dn=(pc>y-.12*a)&(h>y-.15*a)&(c<y-.24*a)&h1d
  ls=np.minimum(l,x-.90*a)-.16*a;ss=np.maximum(h,y+.90*a)+.16*a
 elif name=='VWAP_VOLUME_TREND_RECLAIM':
  up=(pc<v-.10*a)&(l<v+.08*a)&(c>v+.18*a)&h1u;dn=(pc>v+.10*a)&(h>v-.08*a)&(c<v-.18*a)&h1d
 elif name=='VWAP_COUNTER_SWEEP':
  up=(l<v-.35*a)&(c>v+.10*a)&m15d;dn=(h>v+.35*a)&(c<v-.10*a)&m15u
 elif name=='EMA50_PULLBACK_M15':
  up=(pc<e50+.15*a)&(l<e50+.12*a)&(c>e50+.24*a)&m15u;dn=(pc>e50-.15*a)&(h>e50-.12*a)&(c<e50-.24*a)&m15d
 elif name=='EMA20_PULLBACK_H1':
  up=(pc<e20+.10*a)&(l<e20+.09*a)&(c>e20+.24*a)&h1u;dn=(pc>e20-.10*a)&(h>e20-.09*a)&(c<e20-.24*a)&h1d
 elif name=='PREVDAY_MID_BREAK_RETEST':
  x=(f['pdh']+f['pdl'])/2
  up=(pc<x+.12*a)&(l<x+.12*a)&(c>x+.25*a)&h1u;dn=(pc>x-.12*a)&(h>x-.12*a)&(c<x-.25*a)&h1d
  ls=np.minimum(l,x-.75*a)-.16*a;ss=np.maximum(h,x+.75*a)+.16*a
 elif name=='PREVDAY_LOW_HIGH_SWEEP':
  x=f['pdl'];y=f['pdh'];up=(l<x-.12*a)&(c>x+.14*a)&(pc<x+.35*a);dn=(h>y+.12*a)&(c<y-.14*a)&(pc>y-.35*a)
 elif name=='BOLLINGER_MID_MOMENTUM_FLIP':
  x=f['bbmid'];up=(pc<x-.18*a)&(c>x+.16*a)&m15u;dn=(pc>x+.18*a)&(c<x-.16*a)&m15d
 elif name=='BOLLINGER_OUTER_REVERSAL':
  x=f['bbmid']-2*f['bbstd'];y=f['bbmid']+2*f['bbstd'];up=(l<x-.10*a)&(c>x+.20*a)&(f['rsi']<53);dn=(h>y+.10*a)&(c<y-.20*a)&(f['rsi']>47)
 elif name=='ENGULFING_EMA50_PULLBACK':
  up=(o<pc+.07*a)&(c>f['po']+.08*a)&(pc<f['po'])&(l<e50+.20*a)&m15u
  dn=(o>pc-.07*a)&(c<f['po']-.08*a)&(pc>f['po'])&(h>e50-.20*a)&m15d
 elif name=='THREE_BAR_MOMENTUM_CONTINUATION':
  up=(c>ph+.14*a)&(pc>f['pc2'])&(pc>e20)&h1u
  dn=(c<pl-.14*a)&(pc<f['pc2'])&(pc<e20)&h1d
 elif name=='M15_TREND_ATR_EXPANSION':
  up=m15u&(c>e20+.24*a)&(pc<e20+.15*a)&(f['vol']>0)
  dn=m15d&(c<e20-.24*a)&(pc>e20-.15*a)&(f['vol']>0)
 elif name=='H1_TREND_TWO_BAR_REVERSAL':
  up=h1u&(pc<e20)&(c>e20+.20*a)&(c>ph+.12*a)
  dn=h1d&(pc>e20)&(c<e20-.20*a)&(c<pl-.12*a)
 elif name=='ROLLING24_REJECTION_VOLUME':
  x=f['rlo'][24];y=f['rhi'][24];up=(l<x-.05*a)&(c>x+.12*a)&(pc<x+.26*a)
  dn=(h>y+.05*a)&(c<y-.12*a)&(pc>y-.26*a)
 elif name=='ROLLING72_BREAK_AND_RECLAIM':
  x=f['rhi'][72];y=f['rlo'][72];up=(pc<x+.08*a)&(l<x+.10*a)&(c>x+.20*a)&m30u
  dn=(pc>y-.08*a)&(h>y-.10*a)&(c<y-.20*a)&m30d
 elif name=='STOCH_RSI_LIQUIDITY_FLIP':
  x=f['rlo'][24];y=f['rhi'][24];up=(l<x-.12*a)&(c>x+.15*a)&(f['stoch']<42)&(f['rsi']<52)
  dn=(h>y+.12*a)&(c<y-.15*a)&(f['stoch']>58)&(f['rsi']>48)
 elif name=='M5_BB_SQUEEZE_DISPLACEMENT':
  wd=(4*f['bbstd'])/a;up=(wd<4.4)&(c>f['bbmid']+.7*f['bbstd'])&(c>ph+.15*a)&m15u
  dn=(wd<4.4)&(c<f['bbmid']-.7*f['bbstd'])&(c<pl-.15*a)&m15d
 up&=(c>o)&np.isfinite(ls)&((c-ls)>.2*a)&((c-ls)<6*a)
 dn&=(c<o)&np.isfinite(ss)&((ss-c)>.2*a)&((ss-c)<6*a)
 both=up&dn
 p=np.where(up&~both,1,np.where(dn&~both,-1,0)).astype(np.int8)
 stop=np.where(p>0,ls,np.where(p<0,ss,np.nan))
 return p,stop


V26_VERSION = 'NAS100_M5_V2_6_ADD_ONLY_RESEARCH_CANDIDATE'
V26_NEW_ENTRY_GROUPS = ({'baseline_family_index': 6, 'base': {'family_index': 6, 'family': 'H4_EMA20_LIQUIDITY_REVERSAL', 'side': 'both', 'session': [690, 960], 'body': 0.0, 'quality': 0.5299999713897705, 'vol': 0.0, 'atrrel': 0.0, 'max_stop_atr': 1.2000000476837158, 'trend': 'none', 'rsi': 'none', 'adx': 'none', 'macd': 'none', 'stoch': 'none', 'dev_n': 95, 'dev_R': 12.895140647888184, '2025_n': 34, '2025_R': 17.816925048828125, '2026_independent_n': 19, '2026_independent_R': 1.054260015487671, 'screen_score': 47.133758544921875}, 'extra': {'adx_min': 25.0, 'quality': 0.62}}, {'baseline_family_index': 9, 'base': {'family_index': 9, 'family': 'NY_ORB_MIDPOINT_RECLAIM', 'side': 'both', 'session': [600, 960], 'body': 0.18000000715255737, 'quality': 0.5299999713897705, 'vol': 0.0, 'atrrel': 0.699999988079071, 'max_stop_atr': 5.0, 'trend': 'none', 'rsi': 'ge60', 'adx': 'le20', 'macd': 'ge10', 'stoch': 'ge60', 'dev_n': 70, 'dev_R': 17.118083953857422, '2025_n': 28, '2025_R': 23.921493530273438, '2026_independent_n': 16, '2026_independent_R': 8.047906875610352, 'screen_score': 61.64777755737305}, 'extra': {'vol': 0.65, 'atrrel': 1.5, 'rsi_min': 50.0}}, {'baseline_family_index': 63, 'base': {'family_index': 63, 'family': 'M5_BB_SQUEEZE_DISPLACEMENT', 'side': 'short', 'session': [570, 960], 'body': 0.3199999928474426, 'quality': 0.5299999713897705, 'vol': 1.2999999523162842, 'atrrel': 0.0, 'max_stop_atr': 5.0, 'trend': 'm15', 'rsi': 'ge60', 'adx': 'le20', 'macd': 'none', 'stoch': 'ge60', 'dev_n': 72, 'dev_R': 24.120676040649414, '2025_n': 49, '2025_R': 42.51457595825195, '2026_independent_n': 21, '2026_independent_R': 3.0347442626953125, 'screen_score': 107.98248291015625}, 'extra': {'quality': 0.72, 'vol': 2.0}})

class NAS100V26AddOnly(NAS100V25FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out['Position'].to_numpy(dtype=np.int8).copy()
        original_sl = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        original_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        original_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        f = _v17bank_make_bank(out)
        new_bank = v26_bank(out, f)
        more, _ = _v16features_feature_data(out)
        n = len(out)
        row = np.arange(n)
        p = original_p.copy()
        st = original_sl.copy()
        tp = original_tp.copy()
        reason = original_reason.copy()
        new_counts = {}
        for record in V26_NEW_ENTRY_GROUPS:
            base = record['base']
            extra = record['extra']
            fi = record['baseline_family_index']
            family = base['family']
            if fi < 24:
                rawp, rawstop = v22_raw(f, family)
            elif fi < 44:
                rawp, rawstop = v24_raw(f, family)
            else:
                rawp, rawstop = v26_raw(new_bank, family)
            side = rawp
            atr = np.maximum(f['atr'].astype(np.float32), 1.e-9)
            quality = np.where(side>0, f['uq'], f['dq']).astype(np.float32)
            rsi = np.where(side>0,f['rsi'],100.-f['rsi']).astype(np.float32)
            macd = np.where(side>0,f['macdh'],-f['macdh'])/np.maximum(f['atr'],1.e-9)
            macd = macd.astype(np.float32)
            stoch = np.where(side>0,more['stochastic'],100.-more['stochastic'])
            adx = more['adx']
            min_session,max_session = base['session']
            stop_atr = np.abs(f['c']-rawstop)/atr
            mask = (
                (side!=0) & (original_p==0) & (p==0) &
                (row>=self.LIVE_HISTORY_BARS) & (row<n-1) & (f['dow']<5) &
                (f['minute']>=min_session) & (f['minute']<max_session) &
                (f['body'].astype(np.float32)>=base['body']-1.e-6) &
                (quality>=base['quality']-1.e-6) &
                (f['volume'].astype(np.float32)>=base['vol']-1.e-6) &
                (f['atrrel'].astype(np.float32)>=base['atrrel']-1.e-6) &
                (stop_atr<=base['max_stop_atr']+1.e-6) & np.isfinite(rawstop)
            )
            if base['side']=='long': mask &= side==1
            elif base['side']=='short': mask &= side==-1
            if base['trend']!='none':
                t=f[base['trend']]
                mask &= np.where(side>0,t['up'],t['dn'])
            if base['rsi']=='ge50':mask &= rsi>=50
            elif base['rsi']=='le40':mask &= rsi<=40
            elif base['rsi']=='ge60':mask &= rsi>=60
            if base['adx']=='le20':mask &= adx<=20
            elif base['adx']=='ge22':mask &= adx>=22
            elif base['adx']=='ge30':mask &= adx>=30
            if base['macd']=='ge0':mask &= macd>=0
            elif base['macd']=='ge10':mask &= macd>=.10
            if base['stoch']=='ge60':mask &= stoch>=60
            elif base['stoch']=='le40':mask &= stoch<=40
            elif base['stoch']=='ge80':mask &= stoch>=80
            for key,value in extra.items():
                if key=='session': mask &= (f['minute']>=value[0])&(f['minute']<value[1])
                elif key=='body': mask &= f['body'].astype(np.float32)>=value-1.e-6
                elif key=='quality':mask &= quality>=value-1.e-6
                elif key=='vol':mask &= f['volume'].astype(np.float32)>=value-1.e-6
                elif key=='atrrel':mask &= f['atrrel'].astype(np.float32)>=value-1.e-6
                elif key=='stopatr_max':mask &= stop_atr<=value+1.e-6
                elif key=='rsi_min':mask &= rsi>=value
                elif key=='stoch_min':mask &= stoch>=value
                elif key=='macd_min':mask &= macd>=value
                elif key=='adx_min':mask &= adx>=value
                elif key=='h1_required':mask &= np.where(side>0,f['h1']['up'],f['h1']['dn'])
                elif key=='h4_required':mask &= np.where(side>0,f['h4']['up'],f['h4']['dn'])
                else:raise ValueError('Unknown V2.6 extra condition: '+str(key))
            p[mask]=side[mask]
            st[mask]=rawstop[mask]
            tp[mask]=f['c'][mask]+side[mask]*3.*np.abs(f['c'][mask]-rawstop[mask])
            reason[mask]=V26_VERSION+'|NEW_ENTRY|'+family
            new_counts[family]=int(mask.sum())
        old=original_p!=0
        assert np.array_equal(p[old],original_p[old]),'V2.5 direction changed'
        assert np.array_equal(st[old],original_sl[old]),'V2.5 SL changed'
        assert np.array_equal(tp[old],original_tp[old]),'V2.5 TP changed'
        assert np.array_equal(reason[old],original_reason[old]),'V2.5 signal reason changed'
        assert not np.any((p!=0)&(original_p==0)&(row<self.LIVE_HISTORY_BARS))
        out['Position']=p
        out['strategy_stop_loss']=st
        out['strategy_target']=tp
        out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
          'version':V26_VERSION,'frozen_baseline':'V2.5',
          'mode':'ADD_NEW_WINNING_TRADES_ONLY',
          'baseline_existing_intents_unchanged':True,
          'additional_raw_intents':int(np.count_nonzero((p!=0)&(original_p==0))),
          'new_entry_group_counts':new_counts,
          'retained_sl_tp_unchanged':True,
          'native_algoagentx_verified':False,
          'untouched_out_of_sample_verified':False,
          'research_only':True,
          'warning':'Research only; costs and source execution require native validation; 2025-2026 repeatedly researched.'}
        return out

Strategy=NAS100V26AddOnly


# ===== V2.7 ADD-ONLY RESEARCH EXTENSION =====

# V2.7 add-only research feature bank. Requires numpy as np, pandas as pd and frozen
# _v15bank_htf_projection from the byte-identical V2.6 module.
V27_FAMILIES = (
 'VWAP_REJECT_EMA_TREND','VWAP_DEVIATION_REVERT','EMA100_PULLBACK_SWEEP',
 'PREVDAY_MID_RECLAIM','PREVWEEK_Q35_RECLAIM','PREVWEEK_Q65_RECLAIM',
 'PREVDAY_HIGH_BREAK_RETEST','PREVDAY_LOW_BREAK_RETEST','PREVWEEK_EDGE_FAKEOUT',
 'RSI50_TREND_REENTRY','MACD_ZERO_TREND_CROSS','BOLLINGER_MID_RETEST',
 'BOLLINGER_OUTER_RECLAIM','ADX_TREND_RANGE_BREAK','LOWVOL_RANGE_EXPANSION',
 'STOCH_RESET_EMA_REENTRY','THREE_BAR_COIL_BREAK','H1_EMA50_RECLAIM',
 'H4_EMA50_RECLAIM','M15_EMA20_REJECT','M30_EMA20_REJECT',
 'H1_H4_ALIGNMENT_PULLBACK','ROLLING48_LIQUIDITY_FAKEOUT',
 'ROLLING24_BREAK_VOL','DAILY_OPEN_RECLAIM','NY_ORB_EDGE_BREAKOUT',
 'DOUBLE_BOTTOM_SWEEP','DOUBLE_TOP_SWEEP','FAIR_VALUE_GAP_M5_RETEST',
 'H1_STRUCTURE_BREAK','WEEKLY_MID_TREND_RETEST','M15_RANGE_BREAK_M5_RETEST',
)

def _v27_bank(d):
    t=pd.DatetimeIndex(pd.to_datetime(d['Date'],utc=True)).tz_convert('UTC').tz_localize(None)
    o,h,l,c,v=(d[k].to_numpy(float) for k in ['Open','High','Low','Close','Volume'])
    n=len(c);pc=np.r_[c[0],c[:-1]];p2=np.r_[c[0],c[0],c[:-2]]
    span=np.maximum(h-l,1e-8);tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))
    a=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy(float);a=np.maximum(a,1e-8)
    e20=pd.Series(c).ewm(span=20,adjust=False).mean().to_numpy(float)
    e50=pd.Series(c).ewm(span=50,adjust=False).mean().to_numpy(float)
    e100=pd.Series(c).ewm(span=100,adjust=False).mean().to_numpy(float)
    ss=pd.Series(c);bb=ss.rolling(20,min_periods=20).mean().to_numpy(float)
    bs=ss.rolling(20,min_periods=20).std(ddof=0).to_numpy(float)
    diff=c-pc;up=pd.Series(np.maximum(diff,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    dn=pd.Series(np.maximum(-diff,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    rsi=100*up/np.maximum(up+dn,1e-8)
    macd=pd.Series(c).ewm(span=12,adjust=False).mean().to_numpy(float)-pd.Series(c).ewm(span=26,adjust=False).mean().to_numpy(float)
    macdh=macd-pd.Series(macd).ewm(span=9,adjust=False).mean().to_numpy(float)
    LL=pd.Series(l).rolling(14,min_periods=14).min().to_numpy(float)
    HH=pd.Series(h).rolling(14,min_periods=14).max().to_numpy(float)
    k=100*(c-LL)/np.maximum(HH-LL,1e-9);ks=pd.Series(k).rolling(3,min_periods=3).mean().to_numpy(float)
    dmp=np.maximum(np.r_[0,np.diff(h)],0);dmm=np.maximum(np.r_[0,-np.diff(l)],0)
    dmp=np.where(dmp>dmm,dmp,0);dmm=np.where(dmm>dmp,dmm,0)
    smtr=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    sp=pd.Series(dmp).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(smtr,1e-9)
    sn=pd.Series(dmm).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(smtr,1e-9)
    adx=pd.Series(100*abs(sp-sn)/np.maximum(sp+sn,1e-9)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    volm=pd.Series(v).shift(1).rolling(24,min_periods=24).mean().to_numpy(float)
    rv=v/np.maximum(volm,1)
    am=pd.Series(a).shift(1).rolling(200,min_periods=100).median().to_numpy(float)
    ar=a/np.maximum(am,1e-9)
    hl={};
    for length in (8,12,24,48,96):
        hl['hi'+str(length)]=pd.Series(h).shift(1).rolling(length,min_periods=length).max().to_numpy(float)
        hl['lo'+str(length)]=pd.Series(l).shift(1).rolling(length,min_periods=length).min().to_numpy(float)
    dates=t.tz_localize('UTC').tz_convert('America/New_York')
    minute=dates.hour.to_numpy()*60+dates.minute.to_numpy();dow=dates.dayofweek.to_numpy()
    nydate=dates.normalize();group=pd.DataFrame({'key':nydate,'hi':h,'lo':l,'op':o}).groupby('key',sort=True)
    ds=group.agg(dhi=('hi','max'),dlo=('lo','min'),dopen=('op','first')).shift(1)
    dh=ds.dhi.reindex(nydate).to_numpy(float);dl=ds.dlo.reindex(nydate).to_numpy(float)
    dopen=group.first()['op'].reindex(nydate).to_numpy(float)
    wk=nydate.to_period('W-SUN'); ww=pd.DataFrame({'week':wk,'hi':h,'lo':l}).groupby('week').agg(hi=('hi','max'),lo=('lo','min')).shift(1)
    wh=ww.hi.reindex(wk).to_numpy(float);wl=ww.lo.reindex(wk).to_numpy(float)
    # Opening range values become available at 10:00 NY; no earlier usage.
    orb_idx=(minute>=570)&(minute<600)
    orh=pd.DataFrame({'day':nydate,'value':np.where(orb_idx,h,np.nan)}).groupby('day').value.max().reindex(nydate).to_numpy(float)
    orl=pd.DataFrame({'day':nydate,'value':np.where(orb_idx,l,np.nan)}).groupby('day').value.min().reindex(nydate).to_numpy(float)
    orh=np.where(minute>=600,orh,np.nan);orl=np.where(minute>=600,orl,np.nan)
    # Cumulative NY VWAP uses only current/earlier candles, never a day's future close.
    vv=np.where(minute>=570,v,0.)
    pvv=(h+l+c)/3*vv
    g=pd.DataFrame({'date':nydate,'v':vv,'pv':pvv}).groupby('date',sort=False)
    vw=g['pv'].cumsum().to_numpy(float)/np.maximum(g['v'].cumsum().to_numpy(float),1e-9)
    vw=np.where(minute>=570,vw,np.nan)
    q=(c-l)/span;bearq=(h-c)/span;body=abs(c-o)/a
    close_time=t.to_numpy(dtype='datetime64[ns]')+np.timedelta64(5,'m')
    proj={}
    for rule,expected,delta,key in [('15min',3,15,'m15'),('30min',6,30,'m30'),('1h',12,60,'h1'),('4h',48,240,'h4')]:
        _,p,_,_=_v15bank_htf_projection(d,rule,expected,delta,close_time)
        proj[key]=p
    f=dict(o=o,h=h,l=l,c=c,pc=pc,p2=p2,a=a,e20=e20,e50=e50,e100=e100,bb=bb,bs=bs,rsi=rsi,macdh=macdh,k=k,ks=ks,adx=adx,rv=rv,ar=ar,q=q,bearq=bearq,body=body,minute=minute,dow=dow,dh=dh,dl=dl,dopen=dopen,wh=wh,wl=wl,orh=orh,orl=orl,vw=vw,t=t)
    f.update(hl);f.update(proj)
    return f

def _v27_raw(f,name):
    o,h,l,c,pc,a=(f[k] for k in ('o','h','l','c','pc','a'))
    e20,e50,e100=(f[k] for k in ('e20','e50','e100'))
    h1,h4,m15,m30=(f[k] for k in ('h1','h4','m15','m30'))
    up=dn=np.zeros(len(c),bool)
    if name=='VWAP_REJECT_EMA_TREND':
        v=f['vw'];up=(l<v-.06*a)&(c>v+.08*a)&(e20>e50);dn=(h>v+.06*a)&(c<v-.08*a)&(e20<e50)
    elif name=='VWAP_DEVIATION_REVERT':
        v=f['vw'];up=(l<v-1.25*a)&(c>pc+.15*a)&(c<v-.40*a);dn=(h>v+1.25*a)&(c<pc-.15*a)&(c>v+.40*a)
    elif name=='EMA100_PULLBACK_SWEEP':
        up=(l<e100-.12*a)&(c>e100+.10*a)&(e20>e50);dn=(h>e100+.12*a)&(c<e100-.10*a)&(e20<e50)
    elif name=='PREVDAY_MID_RECLAIM':
        x=(f['dh']+f['dl'])/2;up=(pc<x-.08*a)&(c>x+.12*a);dn=(pc>x+.08*a)&(c<x-.12*a)
    elif name=='PREVWEEK_Q35_RECLAIM':
        x=f['wl']+.35*(f['wh']-f['wl']);up=(pc<x-.08*a)&(c>x+.10*a);dn=(pc>x+.08*a)&(c<x-.10*a)
    elif name=='PREVWEEK_Q65_RECLAIM':
        x=f['wl']+.65*(f['wh']-f['wl']);up=(pc<x-.08*a)&(c>x+.10*a);dn=(pc>x+.08*a)&(c<x-.10*a)
    elif name=='PREVDAY_HIGH_BREAK_RETEST':
        x=f['dh'];up=(pc>x+.08*a)&(l<x+.09*a)&(c>x+.16*a);dn=(pc<x-.08*a)&(h>x-.09*a)&(c<x-.16*a)
    elif name=='PREVDAY_LOW_BREAK_RETEST':
        x=f['dl'];up=(pc>x+.08*a)&(l<x+.09*a)&(c>x+.16*a);dn=(pc<x-.08*a)&(h>x-.09*a)&(c<x-.16*a)
    elif name=='PREVWEEK_EDGE_FAKEOUT':
        up=(l<f['wl']-.11*a)&(c>f['wl']+.09*a);dn=(h>f['wh']+.11*a)&(c<f['wh']-.09*a)
    elif name=='RSI50_TREND_REENTRY':
        rr=f['rsi'];pr=np.r_[rr[0],rr[:-1]];up=(pr<48)&(rr>52)&(e20>e50);dn=(pr>52)&(rr<48)&(e20<e50)
    elif name=='MACD_ZERO_TREND_CROSS':
        x=f['macdh'];px=np.r_[x[0],x[:-1]];up=(px<0)&(x>0)&(e20>e50);dn=(px>0)&(x<0)&(e20<e50)
    elif name=='BOLLINGER_MID_RETEST':
        x=f['bb'];up=(pc>x+.12*a)&(l<x-.07*a)&(c>x+.12*a);dn=(pc<x-.12*a)&(h>x+.07*a)&(c<x-.12*a)
    elif name=='BOLLINGER_OUTER_RECLAIM':
        x=f['bb']-2*f['bs'];y=f['bb']+2*f['bs'];up=(l<x-.08*a)&(c>x+.1*a)&(f['rsi']<52);dn=(h>y+.08*a)&(c<y-.1*a)&(f['rsi']>48)
    elif name=='ADX_TREND_RANGE_BREAK':
        up=(c>f['hi24']+.12*a)&(f['adx']>23)&(e20>e50);dn=(c<f['lo24']-.12*a)&(f['adx']>23)&(e20<e50)
    elif name=='LOWVOL_RANGE_EXPANSION':
        squeeze=(4*f['bs']/a<3.8);up=squeeze&(c>f['hi12']+.15*a);dn=squeeze&(c<f['lo12']-.15*a)
    elif name=='STOCH_RESET_EMA_REENTRY':
        pk=np.r_[f['k'][0],f['k'][:-1]];up=(pk<36)&(f['k']>45)&(e20>e50);dn=(pk>64)&(f['k']<55)&(e20<e50)
    elif name=='THREE_BAR_COIL_BREAK':
        x=np.r_[h[0],h[:-1]];y=np.r_[l[0],l[:-1]];up=(x<f['hi12'])&(c>f['hi12']+.1*a)&(f['rv']>1);dn=(y>f['lo12'])&(c<f['lo12']-.1*a)&(f['rv']>1)
    elif name=='H1_EMA50_RECLAIM':
        x=h1['e50'];up=(l<x-.1*a)&(c>x+.12*a)&h1['up'];dn=(h>x+.1*a)&(c<x-.12*a)&h1['dn']
    elif name=='H4_EMA50_RECLAIM':
        x=h4['e50'];up=(l<x-.12*a)&(c>x+.13*a)&h4['up'];dn=(h>x+.12*a)&(c<x-.13*a)&h4['dn']
    elif name=='M15_EMA20_REJECT':
        x=m15['e20'];up=(l<x-.12*a)&(c>x+.13*a)&m15['up'];dn=(h>x+.12*a)&(c<x-.13*a)&m15['dn']
    elif name=='M30_EMA20_REJECT':
        x=m30['e20'];up=(l<x-.12*a)&(c>x+.13*a)&m30['up'];dn=(h>x+.12*a)&(c<x-.13*a)&m30['dn']
    elif name=='H1_H4_ALIGNMENT_PULLBACK':
        up=h1['up']&h4['up']&(l<e20-.12*a)&(c>e20+.13*a);dn=h1['dn']&h4['dn']&(h>e20+.12*a)&(c<e20-.13*a)
    elif name=='ROLLING48_LIQUIDITY_FAKEOUT':
        up=(l<f['lo48']-.12*a)&(c>f['lo48']+.12*a);dn=(h>f['hi48']+.12*a)&(c<f['hi48']-.12*a)
    elif name=='ROLLING24_BREAK_VOL':
        up=(c>f['hi24']+.16*a)&(f['rv']>1.3);dn=(c<f['lo24']-.16*a)&(f['rv']>1.3)
    elif name=='DAILY_OPEN_RECLAIM':
        x=f['dopen'];up=(pc<x-.10*a)&(c>x+.13*a);dn=(pc>x+.10*a)&(c<x-.13*a)
    elif name=='NY_ORB_EDGE_BREAKOUT':
        up=(pc<f['orh']+.08*a)&(c>f['orh']+.15*a);dn=(pc>f['orl']-.08*a)&(c<f['orl']-.15*a)
    elif name=='DOUBLE_BOTTOM_SWEEP':
        x=f['lo24'];up=(l<x-.07*a)&(c>x+.13*a)&(f['rsi']<53);dn=np.zeros(len(c),bool)
    elif name=='DOUBLE_TOP_SWEEP':
        y=f['hi24'];up=np.zeros(len(c),bool);dn=(h>y+.07*a)&(c<y-.13*a)&(f['rsi']>47)
    elif name=='FAIR_VALUE_GAP_M5_RETEST':
        ph2=np.r_[h[0],h[0],h[:-2]];pl2=np.r_[l[0],l[0],l[:-2]]
        gup=(l>ph2+.05*a);gdn=(h<pl2-.05*a)
        x=np.r_[np.nan,ph2[:-1]];y=np.r_[np.nan,pl2[:-1]]
        up=np.r_[False,gup[:-1]]&(l<x+.1*a)&(c>x+.16*a)
        dn=np.r_[False,gdn[:-1]]&(h>y-.1*a)&(c<y-.16*a)
    elif name=='H1_STRUCTURE_BREAK':
        up=(c>h1['hi12']+.11*a)&(pc<h1['hi12']+.05*a)&h1['up'];dn=(c<h1['lo12']-.11*a)&(pc>h1['lo12']-.05*a)&h1['dn']
    elif name=='WEEKLY_MID_TREND_RETEST':
        x=(f['wl']+f['wh'])/2;up=(l<x-.07*a)&(c>x+.10*a)&h1['up'];dn=(h>x+.07*a)&(c<x-.10*a)&h1['dn']
    elif name=='M15_RANGE_BREAK_M5_RETEST':
        x=m15['hi12'];y=m15['lo12'];up=(pc<x+.04*a)&(l<x+.08*a)&(c>x+.17*a)&m15['up'];dn=(pc>y-.04*a)&(h>y-.08*a)&(c<y-.17*a)&m15['dn']
    else:raise ValueError('Unknown family '+name)
    # All observations are closed on decision bar. Stop/target use M5 structure, 3R.
    L=np.minimum(l,f['lo8'])-.15*a;S=np.maximum(h,f['hi8'])+.15*a
    up=up&(c>o)&(c-L>.2*a)&(c-L<6*a)&np.isfinite(L)
    dn=dn&(c<o)&(S-c>.2*a)&(S-c<6*a)&np.isfinite(S)
    clash=up&dn
    side=np.where(up&~clash,1,np.where(dn&~clash,-1,0)).astype(np.int8)
    stop=np.where(side>0,L,np.where(side<0,S,np.nan))
    return side,stop


V27_VERSION = 'NAS100_M5_V2_7_ADD_ONLY_RESEARCH_CANDIDATE'
V27_SELECTED_GROUPS = ({'family': 'EMA100_PULLBACK_SWEEP', 'family_index': 2, 'session': [570, 960], 'side': 'both', 'min_body': 0.42, 'min_quality': 0.73, 'min_relative_volume': 2.1, 'min_relative_atr': 1.85, 'max_stop_atr': 2.0, 'trend': 'none', 'min_adx': 0.0, 'min_directional_rsi': 45.0}, {'family': 'M30_EMA20_REJECT', 'family_index': 20, 'session': [570, 960], 'side': 'long', 'min_body': 0.12, 'min_quality': 0.7, 'min_relative_volume': 2.1, 'min_relative_atr': 1.5, 'max_stop_atr': 5.0, 'trend': 'h4', 'min_adx': 0.0, 'min_directional_rsi': 55.0})

class NAS100V27AddOnly(NAS100V26AddOnly):
    """V2.6-frozen, add-only V2.7 strategy. All calculations are closed-bar causal."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out['Position'].to_numpy(np.int8).copy()
        original_st = out['strategy_stop_loss'].to_numpy(float).copy()
        original_tp = out['strategy_target'].to_numpy(float).copy()
        original_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        f = _v27_bank(out)
        n = len(out)
        idx = np.arange(n)
        p = original_p.copy()
        st = original_st.copy()
        tp = original_tp.copy()
        reason = original_reason.copy()
        counts = {}
        # Signal-intent precedence: all frozen V2.6 entries always win, then V2.7 in order.
        for cfg in V27_SELECTED_GROUPS:
            side, stop = _v27_raw(f, cfg['family'])
            mins, maxs = cfg['session']
            q = np.where(side>0, f['q'], f['bearq']).astype(np.float32)
            body = f['body'].astype(np.float32)
            rv = f['rv'].astype(np.float32)
            ar = f['ar'].astype(np.float32)
            atr = np.maximum(f['a'].astype(np.float32),1.e-8)
            stop_atr = np.abs(f['c']-stop)/atr
            adx = f['adx'].astype(np.float32)
            rsi = f['rsi'].astype(np.float32)
            drsi = np.where(side>0,rsi,100-rsi)
            mask = (
                (side!=0) & (original_p==0) & (p==0) &
                (idx>=self.LIVE_HISTORY_BARS) & (idx<n-1) & (f['dow']<5) &
                (f['minute']>=mins) & (f['minute']<maxs) &
                (body>=cfg['min_body']-1.e-6) &
                (q>=cfg['min_quality']-1.e-6) &
                (rv>=cfg['min_relative_volume']-1.e-6) &
                (ar>=cfg['min_relative_atr']-1.e-6) &
                (stop_atr<=cfg['max_stop_atr']+1.e-6) &
                (adx>=cfg['min_adx']) &
                (drsi>=cfg['min_directional_rsi']) & np.isfinite(stop)
            )
            if cfg['side']=='long':mask &= side==1
            elif cfg['side']=='short':mask &= side==-1
            align_h1=np.where(side>0,f['h1']['up'],f['h1']['dn'])
            align_h4=np.where(side>0,f['h4']['up'],f['h4']['dn'])
            if cfg['trend']=='h1':mask &= align_h1
            elif cfg['trend']=='h4':mask &= align_h4
            elif cfg['trend'] in ('h1_h4','ema'):mask &= align_h1&align_h4
            elif cfg['trend']!='none':raise ValueError('Unknown V2.7 trend filter')
            p[mask]=side[mask]
            st[mask]=stop[mask]
            tp[mask]=f['c'][mask]+3.0*side[mask]*abs(f['c'][mask]-stop[mask])
            reason[mask]=V27_VERSION+'|NEW_ENTRY|'+cfg['family']
            counts[cfg['family']]=int(mask.sum())
        # Safety and lineage: V2.7 MUST NOT change existing V2.6 intents.
        old=original_p!=0
        assert np.array_equal(p[old],original_p[old]),'Frozen V2.6 direction changed'
        assert np.array_equal(st[old],original_st[old]),'Frozen V2.6 SL changed'
        assert np.array_equal(tp[old],original_tp[old]),'Frozen V2.6 TP changed'
        assert np.array_equal(reason[old],original_reason[old]),'Frozen V2.6 signal reason changed'
        assert not np.any((p!=0)&(original_p==0)&(idx<self.LIVE_HISTORY_BARS))
        out['Position']=p
        out['strategy_stop_loss']=st
        out['strategy_target']=tp
        out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
            'version':V27_VERSION,'frozen_baseline':'V2.6',
            'mode':'ADD_NEW_WINNING_TRADES_ONLY',
            'original_signals_sl_tp_unchanged':True,
            'new_signal_intents':int(np.count_nonzero((p!=0)&(original_p==0))),
            'new_entry_groups':counts,
            'native_algoagentx_verified':False,
            'untouched_forward_validation':False,
            'research_only':True,
        }
        return out

Strategy = NAS100V27AddOnly



# ===== NAS100 V2.8 FILTER-ONLY RESEARCH EXTENSION =====
# V2.7 source above is frozen byte-for-byte. Reject existing signals only.
V28_VERSION = 'NAS100_M5_V2_8_FILTER_ONLY_RESEARCH_CANDIDATE'
V28_REJECTION_RULES = ((('wick_against', '<=', 0.05505344867706299), ('range24_atr', '<=', 3.8863365650177), ('volume_slope', '<=', 0.8103665113449097)), (('rv', '<=', 0.9100769996643067), ('range24_atr', '<=', 3.8863365650177)))

# Appended inside standalone version; only pandas/numpy used; all signals evaluated after closed M5 candle.
def _v28_context(d, signal_side, baseline_stop):
    o=d['Open'].to_numpy(float); h=d['High'].to_numpy(float)
    l=d['Low'].to_numpy(float); c=d['Close'].to_numpy(float)
    v=d['Volume'].to_numpy(float)
    p=np.asarray(signal_side, dtype=np.int8)
    t=pd.DatetimeIndex(pd.to_datetime(d['Date'],utc=True))
    s=pd.Series(c); vs=pd.Series(v)
    pc=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))
    atr=np.maximum(pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy(float),1e-9)
    e20=s.ewm(span=20,adjust=False).mean().to_numpy(float)
    e50=s.ewm(span=50,adjust=False).mean().to_numpy(float)
    e100=s.ewm(span=100,adjust=False).mean().to_numpy(float)
    delta=c-pc
    up=pd.Series(np.maximum(delta,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    down=pd.Series(np.maximum(-delta,0)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    rsi=100*up/np.maximum(up+down,1e-9)
    lo14=pd.Series(l).rolling(14,min_periods=14).min().to_numpy(float)
    hi14=pd.Series(h).rolling(14,min_periods=14).max().to_numpy(float)
    stoch=100*(c-lo14)/np.maximum(hi14-lo14,1e-9)
    bb_mid=s.rolling(20,min_periods=20).mean().to_numpy(float)
    bb_sd=s.rolling(20,min_periods=20).std(ddof=0).to_numpy(float)
    macd=s.ewm(span=12,adjust=False).mean().to_numpy(float)-s.ewm(span=26,adjust=False).mean().to_numpy(float)
    macd_hist=macd-pd.Series(macd).ewm(span=9,adjust=False).mean().to_numpy(float)
    rv=v/np.maximum(vs.shift(1).rolling(24,min_periods=24).mean().to_numpy(float),1.)
    av=atr/np.maximum(pd.Series(atr).shift(1).rolling(200,min_periods=100).median().to_numpy(float),1e-9)
    plus=np.maximum(np.r_[0,np.diff(h)],0)
    minus=np.maximum(np.r_[0,-np.diff(l)],0)
    plus1=np.where(plus>minus,plus,0); minus1=np.where(minus>plus,minus,0)
    di_plus=pd.Series(plus1).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(atr,1e-9)
    di_minus=pd.Series(minus1).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)/np.maximum(atr,1e-9)
    adx=pd.Series(100*abs(di_plus-di_minus)/np.maximum(di_plus+di_minus,1e-9)).ewm(alpha=1/14,adjust=False).mean().to_numpy(float)
    hh24=pd.Series(h).shift(1).rolling(24,min_periods=24).max().to_numpy(float)
    ll24=pd.Series(l).shift(1).rolling(24,min_periods=24).min().to_numpy(float)
    hh96=pd.Series(h).shift(1).rolling(96,min_periods=96).max().to_numpy(float)
    ll96=pd.Series(l).shift(1).rolling(96,min_periods=96).min().to_numpy(float)
    shift=lambda x,k: np.r_[np.full(k,np.nan), x[:-k]]
    span=np.maximum(h-l,1e-9)
    buy=p>0
    q=np.where(buy,(c-l)/span,(h-c)/span)
    wick_against=np.where(buy,np.minimum(o,c)-l,h-np.maximum(o,c))/span
    wick_with=np.where(buy,h-np.maximum(o,c),np.minimum(o,c)-l)/span
    ny=t.tz_convert('America/New_York')
    minute=(ny.hour.to_numpy()*60+ny.minute.to_numpy()).astype(float)
    dow=ny.dayofweek.to_numpy().astype(float)
    key=ny.normalize()
    pv=((h+l+c)/3)*np.maximum(v,0)
    cumulative=pd.DataFrame({'key':key,'vol':np.maximum(v,0),'pv':pv}).groupby('key',sort=False)
    vwap=cumulative.pv.cumsum().to_numpy(float)/np.maximum(cumulative.vol.cumsum().to_numpy(float),1e-9)
    # Completed H1/H4 trend flags come from the previously precomputed causal bank (not recomputed here).
    return {
      'body_atr':np.abs(c-o)/atr,'close_quality':q,'wick_against':wick_against,'wick_with':wick_with,
      'rv':rv,'atr_rel':av,'atr_slope_12':atr/np.maximum(shift(atr,12),1e-9),
      'atr_slope_48':atr/np.maximum(shift(atr,48),1e-9),
      'rsi_raw':rsi,'rsi_direction':np.where(buy,rsi,100-rsi),
      'stoch_raw':stoch,'stoch_direction':np.where(buy,stoch,100-stoch),
      'adx':adx,'macd_dir':p*macd_hist/atr,
      'boll_dir':p*(c-bb_mid)/np.maximum(bb_sd,1e-9),
      'ema20_gap_dir':p*(c-e20)/atr,'ema50_gap_dir':p*(c-e50)/atr,'ema100_gap_dir':p*(c-e100)/atr,
      'ema_spread_dir':p*(e20-e50)/atr,'ema50_100_dir':p*(e50-e100)/atr,
      'ema20_slope_12':p*(e20-shift(e20,12))/atr,
      'ema50_slope_48':p*(e50-shift(e50,48))/atr,
      'momentum_3':p*(c-shift(c,3))/atr,'momentum_12':p*(c-shift(c,12))/atr,
      'momentum_48':p*(c-shift(c,48))/atr,'momentum_96':p*(c-shift(c,96))/atr,
      'stop_atr':abs(c-baseline_stop)/atr,'vwap_gap_dir':p*(c-vwap)/atr,
      'channel24_pos':(c-ll24)/np.maximum(hh24-ll24,1e-9),
      'channel96_pos':(c-ll96)/np.maximum(hh96-ll96,1e-9),
      'range24_atr':(hh24-ll24)/atr,'range96_atr':(hh96-ll96)/atr,
      'minute_ny':minute,'day_of_week':dow,
      'prior_close_gap':p*(o-pc)/atr,'upper_wick':(h-np.maximum(o,c))/span,
      'lower_wick':(np.minimum(o,c)-l)/span,
      'volume_z':(v-vs.shift(1).rolling(48,min_periods=24).mean().to_numpy(float))/np.maximum(vs.shift(1).rolling(48,min_periods=24).std(ddof=0).to_numpy(float),1),
      'volume_slope':vs.shift(1).rolling(12,min_periods=12).mean().to_numpy(float)/np.maximum(vs.shift(13).rolling(48,min_periods=48).mean().to_numpy(float),1),
    }


class NAS100V28FilterOnly(NAS100V27AddOnly):
    """Drop existing, statistically weak V2.7 signal intents, never add trades."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out=super().generate()
        old_p=out['Position'].to_numpy(np.int8).copy()
        old_st=out['strategy_stop_loss'].to_numpy(float).copy()
        old_tp=out['strategy_target'].to_numpy(float).copy()
        old_reason=out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        f=_v28_context(out,old_p,old_st)
        # Cast the research features to float32 exactly as in the 2022-24 training bank.
        reject=np.zeros(len(out),dtype=bool)
        for group in V28_REJECTION_RULES:
            candidate=np.ones(len(out),dtype=bool)
            for field,comparison,threshold in group:
                v=np.asarray(f[field],dtype=np.float32)
                th=np.float32(threshold)
                if comparison=='<=':
                    candidate &= v<=th
                elif comparison=='>=':
                    candidate &= v>=th
                else:
                    raise ValueError('Unexpected V2.8 filter comparison')
            reject |= candidate
        idx=np.arange(len(out))
        reject &= (old_p!=0)&(idx>=self.LIVE_HISTORY_BARS)
        pos=old_p.copy();sl=old_st.copy();tp=old_tp.copy();reason=old_reason.copy()
        pos[reject]=0;sl[reject]=np.nan;tp[reject]=np.nan;reason[reject]=''
        # Source lineage invariant: keep every permitted original entry untouched.
        keep=~reject
        assert np.array_equal(pos[keep],old_p[keep])
        assert np.array_equal(sl[keep],old_st[keep],equal_nan=True)
        assert np.array_equal(tp[keep],old_tp[keep],equal_nan=True)
        assert np.array_equal(reason[keep],old_reason[keep])
        assert not np.any((old_p==0)&(pos!=0))
        out['Position']=pos
        out['strategy_stop_loss']=sl
        out['strategy_target']=tp
        out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
            'version':V28_VERSION,'frozen_baseline':'V2.7',
            'mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_intents':int(reject.sum()),
            'new_intents':0,'original_accepted_signals_sl_tp_unchanged':True,
            'native_algoagentx_verified':False,'untouched_forward_validation':False,
            'research_only':True
        }
        return out

Strategy=NAS100V28FilterOnly



# ==== V2.9 ADD-ONLY RESEARCH EXTENSION ==== 
# Source above is identical to the frozen accepted V2.8 module.
V29_VERSION = 'NAS100_M5_V2_9_ADD_ONLY_RESEARCH_CANDIDATE'
V29_SELECTED_GROUPS = ((1, (0.10000000149011612, 0.7699999809265137, 0.6499999761581421, 1.100000023841858, 12.0, 48.0, 3.0, 1.0, 1.0)), (22, (0.18000000715255737, 0.7699999809265137, 1.2000000476837158, 1.100000023841858, 0.0, 48.0, 0.0, 0.0, 3.0)))

# V2.9 genuinely new candidate families. Inputs are current completed M5 and already-completed HTF bars.
V29_FAMILIES = (
 'EMA200_SWEEP','EMA200_TREND_RECLAIM','EMA50_WICK_REJECTION','EMA20_MOMENTUM_RETEST',
 'WEEK_Q20_RECLAIM','WEEK_Q80_RECLAIM','WEEK_HIGH_SWEEP_REV','WEEK_LOW_SWEEP_REV',
 'PREVDAY_Q25_RECLAIM','PREVDAY_Q75_RECLAIM','PREVDAY_HIGH_REJECT','PREVDAY_LOW_REJECT',
 'VWAP_BAND_BREAK_RETEST','VWAP_BAND_LIQUIDITY_REV','VWAP_EMA_PULLBACK','VWAP_MEAN_REENTRY',
 'ROLLING96_SWEEP','ROLLING12_SWEEP','ROLLING96_BREAK_RETEST','ROLLING12_BREAK_RETEST',
 'M30_EMA50_TREND_RETEST','M15_EMA50_TREND_RETEST','H1_EMA20_TREND_RETEST','H4_EMA20_TREND_RETEST',
 'BOLL_SQUEEZE_EXPANSION','BOLL_TREND_PULLBACK','MACD_HIST_RECLAIM','RSI_40_60_RECLAIM',
 'STOCH_EXTREME_REENTRY','CANDLE_ENGULF_SWEEP','FVG_ONE_BAR_RETURN','H1_EDGE_REJECTION',
 'H4_EDGE_REJECTION','NY_ORB_MID_RECLAIM','OPEN_RANGE_FADE','DOUBLE_SWEEP_24',
)

def _v29_raw(f,name):
    o,h,l,c,pc,a=(f[k] for k in ('o','h','l','c','pc','a'))
    e20,e50,e100=(f[k] for k in ('e20','e50','e100'))
    m15,m30,h1,h4=(f[k] for k in ('m15','m30','h1','h4'))
    shift=lambda v,n: np.r_[np.full(n,np.nan),v[:-n]]
    zero=np.zeros(len(c),dtype=bool)
    up=dn=zero
    e200=pd.Series(c).ewm(span=200,adjust=False).mean().to_numpy(float)
    hi24,lo24=f['hi24'],f['lo24'];hi48,lo48=f['hi48'],f['lo48'];hi96,lo96=f['hi96'],f['lo96']
    wklo,wkhi=f['wl'],f['wh']; dh,dl=f['dh'],f['dl'];vw=f['vw']
    if name=='EMA200_SWEEP':
        up=(l<e200-.20*a)&(c>e200+.09*a)&(e50>e200);dn=(h>e200+.20*a)&(c<e200-.09*a)&(e50<e200)
    elif name=='EMA200_TREND_RECLAIM':
        up=(pc<e200-.06*a)&(c>e200+.17*a)&h1['up'];dn=(pc>e200+.06*a)&(c<e200-.17*a)&h1['dn']
    elif name=='EMA50_WICK_REJECTION':
        up=(l<e50-.22*a)&(c>e50+.18*a)&(e50>e100);dn=(h>e50+.22*a)&(c<e50-.18*a)&(e50<e100)
    elif name=='EMA20_MOMENTUM_RETEST':
        up=(pc>e20+.08*a)&(l<e20-.10*a)&(c>e20+.21*a)&(e20>e50);dn=(pc<e20-.08*a)&(h>e20+.10*a)&(c<e20-.21*a)&(e20<e50)
    elif name in ('WEEK_Q20_RECLAIM','WEEK_Q80_RECLAIM'):
        x=wklo+(.2 if name=='WEEK_Q20_RECLAIM' else .8)*(wkhi-wklo)
        up=(pc<x-.13*a)&(l<x-.15*a)&(c>x+.16*a);dn=(pc>x+.13*a)&(h>x+.15*a)&(c<x-.16*a)
    elif name=='WEEK_HIGH_SWEEP_REV':
        dn=(h>wkhi+.18*a)&(c<wkhi-.17*a);up=zero
    elif name=='WEEK_LOW_SWEEP_REV':
        up=(l<wklo-.18*a)&(c>wklo+.17*a);dn=zero
    elif name in ('PREVDAY_Q25_RECLAIM','PREVDAY_Q75_RECLAIM'):
        x=dl+(.25 if name=='PREVDAY_Q25_RECLAIM' else .75)*(dh-dl)
        up=(pc<x-.08*a)&(c>x+.21*a)&(l<x-.06*a);dn=(pc>x+.08*a)&(c<x-.21*a)&(h>x+.06*a)
    elif name=='PREVDAY_HIGH_REJECT':
        dn=(h>dh+.19*a)&(c<dh-.17*a);up=zero
    elif name=='PREVDAY_LOW_REJECT':
        up=(l<dl-.19*a)&(c>dl+.17*a);dn=zero
    elif name=='VWAP_BAND_BREAK_RETEST':
        up=(pc>vw+.35*a)&(l<vw+.05*a)&(c>vw+.38*a);dn=(pc<vw-.35*a)&(h>vw-.05*a)&(c<vw-.38*a)
    elif name=='VWAP_BAND_LIQUIDITY_REV':
        up=(l<vw-.75*a)&(c>vw-.45*a)&(f['rsi']<55);dn=(h>vw+.75*a)&(c<vw+.45*a)&(f['rsi']>45)
    elif name=='VWAP_EMA_PULLBACK':
        up=(l<vw-.08*a)&(c>vw+.20*a)&(e20>e50);dn=(h>vw+.08*a)&(c<vw-.20*a)&(e20<e50)
    elif name=='VWAP_MEAN_REENTRY':
        up=(pc<vw-.50*a)&(c>vw-.14*a)&(c<vw+.45*a);dn=(pc>vw+.50*a)&(c<vw+.14*a)&(c>vw-.45*a)
    elif name in ('ROLLING96_SWEEP','ROLLING12_SWEEP'):
        lo=lo96 if name=='ROLLING96_SWEEP' else f['lo12']; hi=hi96 if name=='ROLLING96_SWEEP' else f['hi12']
        up=(l<lo-.19*a)&(c>lo+.20*a);dn=(h>hi+.19*a)&(c<hi-.20*a)
    elif name in ('ROLLING96_BREAK_RETEST','ROLLING12_BREAK_RETEST'):
        lo=lo96 if name=='ROLLING96_BREAK_RETEST' else f['lo12'];hi=hi96 if name=='ROLLING96_BREAK_RETEST' else f['hi12']
        up=(pc>hi-.05*a)&(l<hi+.13*a)&(c>hi+.25*a);dn=(pc<lo+.05*a)&(h>lo-.13*a)&(c<lo-.25*a)
    elif name in ('M30_EMA50_TREND_RETEST','M15_EMA50_TREND_RETEST'):
        ht=m30 if name.startswith('M30') else m15;x=ht['e50']
        up=(l<x-.13*a)&(c>x+.17*a)&ht['up'];dn=(h>x+.13*a)&(c<x-.17*a)&ht['dn']
    elif name in ('H1_EMA20_TREND_RETEST','H4_EMA20_TREND_RETEST'):
        ht=h1 if name.startswith('H1') else h4;x=ht['e20']
        up=(l<x-.16*a)&(c>x+.2*a)&ht['up'];dn=(h>x+.16*a)&(c<x-.2*a)&ht['dn']
    elif name=='BOLL_SQUEEZE_EXPANSION':
        comp=(4*f['bs']/a<4.2);up=comp&(c>f['bb']+1.8*f['bs'])&(e20>e50);dn=comp&(c<f['bb']-1.8*f['bs'])&(e20<e50)
    elif name=='BOLL_TREND_PULLBACK':
        up=(l<f['bb']-.17*a)&(c>f['bb']+.22*a)&(e50>e100);dn=(h>f['bb']+.17*a)&(c<f['bb']-.22*a)&(e50<e100)
    elif name=='MACD_HIST_RECLAIM':
        mh=f['macdh'];up=(shift(mh,2)<-.04*a)&(mh>.07*a)&(e20>e50);dn=(shift(mh,2)>.04*a)&(mh<-.07*a)&(e20<e50)
    elif name=='RSI_40_60_RECLAIM':
        rr=f['rsi'];up=(shift(rr,3)<42)&(rr>49)&(e20>e50);dn=(shift(rr,3)>58)&(rr<51)&(e20<e50)
    elif name=='STOCH_EXTREME_REENTRY':
        kk=f['k'];up=(shift(kk,3)<17)&(kk>34)&(c>e50);dn=(shift(kk,3)>83)&(kk<66)&(c<e50)
    elif name=='CANDLE_ENGULF_SWEEP':
        up=(c>shift(o,1))&(o<shift(c,1))&(l<lo24+.1*a)&(c>pc+.16*a)
        dn=(c<shift(o,1))&(o>shift(c,1))&(h>hi24-.1*a)&(c<pc-.16*a)
    elif name=='FVG_ONE_BAR_RETURN':
        up=(shift(l,1)>shift(h,3)+.12*a)&(l<shift(h,3)+.13*a)&(c>shift(h,3)+.23*a)
        dn=(shift(h,1)<shift(l,3)-.12*a)&(h>shift(l,3)-.13*a)&(c<shift(l,3)-.23*a)
    elif name=='H1_EDGE_REJECTION':
        up=(l<h1['lo12']-.14*a)&(c>h1['lo12']+.19*a);dn=(h>h1['hi12']+.14*a)&(c<h1['hi12']-.19*a)
    elif name=='H4_EDGE_REJECTION':
        up=(l<h4['lo12']-.14*a)&(c>h4['lo12']+.19*a);dn=(h>h4['hi12']+.14*a)&(c<h4['hi12']-.19*a)
    elif name=='NY_ORB_MID_RECLAIM':
        x=(f['orh']+f['orl'])/2;up=(pc<x-.16*a)&(c>x+.20*a);dn=(pc>x+.16*a)&(c<x-.20*a)
    elif name=='OPEN_RANGE_FADE':
        up=(l<f['orl']-.14*a)&(c>f['orl']+.20*a);dn=(h>f['orh']+.14*a)&(c<f['orh']-.20*a)
    elif name=='DOUBLE_SWEEP_24':
        up=(l<lo24-.16*a)&(shift(l,3)<shift(lo24,3)-.12*a)&(c>lo24+.19*a)
        dn=(h>hi24+.16*a)&(shift(h,3)>shift(hi24,3)+.12*a)&(c<hi24-.19*a)
    else:raise ValueError('Unknown family '+name)
    # V2.9 uses identical 3R target convention and next-open policy as V2.8.
    L=np.minimum(l,f['lo8'])-.15*a; S=np.maximum(h,f['hi8'])+.15*a
    up=up&(c>o)&(c-L>.20*a)&(c-L<6*a)&np.isfinite(L)
    dn=dn&(c<o)&(S-c>.20*a)&(S-c<6*a)&np.isfinite(S)
    clash=up&dn
    side=np.where(up&~clash,1,np.where(dn&~clash,-1,0)).astype(np.int8)
    stop=np.where(side>0,L,np.where(side<0,S,np.nan))
    return side,stop


class NAS100V29AddOnly(NAS100V28FilterOnly):
    """Preserves V2.8 entries, stops, targets and priorities; adds new groups."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        bp=out['Position'].to_numpy(np.int8).copy()
        bs=out['strategy_stop_loss'].to_numpy(float).copy()
        bt=out['strategy_target'].to_numpy(float).copy()
        br=out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        f=_v27_bank(out)  # closed-bar features and completed HTF projections
        n=len(out); idx=np.arange(n)
        pp=bp.copy();ss=bs.copy();tt=bt.copy();rs=br.copy();counts={}
        for family_index,cfg in V29_SELECTED_GROUPS:
            side,stop=_v29_raw(f,V29_FAMILIES[family_index]); side=side.astype(np.int8)
            body,quality,rvmin,armin,adxmin,drsimin,trend,choice,session=cfg
            quality_dir=np.where(side>0,f['q'],f['bearq']).astype(np.float32)
            directional_rsi=np.where(side>0,f['rsi'],100-f['rsi']).astype(np.float32)
            good=(side!=0)&(bp==0)&(pp==0)&(idx>=self.LIVE_HISTORY_BARS)&(idx<n-1)&(f['dow']<5)&np.isfinite(stop)
            good &= (f['body'].astype(np.float32)>=body)&(quality_dir>=quality)
            good &= (f['rv'].astype(np.float32)>=rvmin)&(f['ar'].astype(np.float32)>=armin)
            good &= (f['adx'].astype(np.float32)>=adxmin)&(directional_rsi>=drsimin)
            h1=np.where(side>0,f['h1']['up'],f['h1']['dn'])
            h4=np.where(side>0,f['h4']['up'],f['h4']['dn'])
            if trend==1:good &= h1
            elif trend==2:good &= h4
            elif trend==3:good &= (h1 & h4)
            if choice!=0:good &= (side==choice)
            minute=f['minute']
            if session==1:good &= (minute>=570)&(minute<690)
            elif session==2:good &= (minute>=570)&(minute<870)
            elif session==3:good &= (minute>=600)&(minute<960)
            elif session==4:good &= (minute>=480)&(minute<960)
            # IMPORTANT: no future open or future candle is inspected when creating a signal.
            pp[good]=side[good]
            ss[good]=stop.astype(np.float32)[good]
            tt[good]=(f['c']+3.0*side*np.abs(f['c']-stop)).astype(np.float32)[good]
            rs[good]=V29_VERSION+'|NEW_ENTRY|'+V29_FAMILIES[family_index]
            counts[V29_FAMILIES[family_index]]=int(np.count_nonzero(good))
        base=bp!=0
        assert np.array_equal(pp[base],bp[base]),'V2.8 direction changed'
        assert np.array_equal(ss[base],bs[base],equal_nan=True),'V2.8 stop changed'
        assert np.array_equal(tt[base],bt[base],equal_nan=True),'V2.8 target changed'
        assert np.array_equal(rs[base],br[base]),'V2.8 signal reason changed'
        assert not np.any((pp!=0)&(bp==0)&(idx<self.LIVE_HISTORY_BARS))
        out['Position']=pp;out['strategy_stop_loss']=ss;out['strategy_target']=tt;out['signal_reason']=rs
        out.attrs['strategy_diagnostics']={
            'version':V29_VERSION,'frozen_baseline':'V2.8','mode':'ADD_NEW_WINNING_TRADES_ONLY',
            'new_signal_intents':int(np.count_nonzero((pp!=0)&(bp==0))),
            'entry_groups':counts,'original_signals_unchanged':True,
            'native_algoagentx_verified':False,'untouched_forward_validation':False,'research_only':True}
        return out

Strategy=NAS100V29AddOnly



# ===== V3.0 FILTER-ONLY CANDIDATE EXTENSION =====
# Original V2.9 code above is unchanged. Existing entries may only be rejected.
V30_VERSION = 'NAS100_M5_V3_0_FILTER_ONLY_RESEARCH_CANDIDATE'
V30_REJECTION_GROUPS = ((('stoch_direction', '<=', 30.060667037963867), ('range96_atr', '<=', 5.216437339782715)), (('stoch_direction', '<=', 34.14674377441406), ('adx', '>=', 40.710899353027344), ('ema20_slope_12', '<=', -1.3930253982543945)))

class NAS100V30FilterOnly(NAS100V29AddOnly):
    """Reject only V2.9 original entry opportunities in identified weak contexts."""
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        output = super().generate()
        old_pos = output['Position'].to_numpy(dtype=np.int8).copy()
        old_stop = output['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_target = output['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = output['signal_reason'].fillna('').astype(str).to_numpy().copy()
        context = _v28_context(output, old_pos, old_stop)
        n = len(output)
        rejection = np.zeros(n, dtype=bool)
        for conditions in V30_REJECTION_GROUPS:
            group_match = np.ones(n, dtype=bool)
            for feature, op, threshold in conditions:
                values = np.asarray(context[feature], dtype=np.float32)
                th = np.float32(threshold)
                if op == '<=':
                    group_match &= np.isfinite(values) & (values <= th)
                elif op == '>=':
                    group_match &= np.isfinite(values) & (values >= th)
                else:
                    raise ValueError('Unrecognized V3.0 filter condition')
            rejection |= group_match
        rejection &= (old_pos != 0) & (np.arange(n) >= self.LIVE_HISTORY_BARS)
        new_pos = old_pos.copy()
        new_stop = old_stop.copy()
        new_target = old_target.copy()
        new_reason = old_reason.copy()
        new_pos[rejection] = 0
        new_stop[rejection] = np.nan
        new_target[rejection] = np.nan
        new_reason[rejection] = ''
        keep = ~rejection
        assert np.array_equal(new_pos[keep], old_pos[keep])
        assert np.array_equal(new_stop[keep], old_stop[keep], equal_nan=True)
        assert np.array_equal(new_target[keep], old_target[keep], equal_nan=True)
        assert np.array_equal(new_reason[keep], old_reason[keep])
        assert not np.any((old_pos == 0) & (new_pos != 0)), 'Filter may not add new signals'
        output['Position'] = new_pos
        output['strategy_stop_loss'] = new_stop
        output['strategy_target'] = new_target
        output['signal_reason'] = new_reason
        output.attrs['strategy_diagnostics'] = {
            'version': V30_VERSION,
            'frozen_baseline': 'V2.9',
            'mode': 'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_intents': int(np.sum(rejection)),
            'created_intents': 0,
            'baseline_levels_unchanged': True,
            'native_engine_verified': False,
            'untouched_forward_validation': False,
            'research_only': True,
        }
        return output

Strategy = NAS100V30FilterOnly



# ===== BEGIN V3.1 ADD-ONLY RESEARCH EXTENSION =====
# The accepted V3.0 source above is byte-for-byte unchanged.
# The only added behavior is to emit new signals where the V3.0 baseline is FLAT.
"""V3.1 novel entry-bank (M5 causal closed-bar features, HTF completed projection).
Return (side,stop) for optional ADD-ONLY overlay; no actual entries before warmup.
The V3.0 strategy and its levels remain frozen; this defines only missed opportunity groups.
"""
V31_FAMILIES=(
 'WEEK_Q10_BOUNCE','WEEK_Q90_FADE','WEEK_MID_MOMENTUM','WEEK_HIGH_BREAK_RETEST','WEEK_LOW_BREAK_RETEST',
 'PREVDAY_Q10_BOUNCE','PREVDAY_Q90_FADE','PREVDAY_OPEN_REJECTION','PREVDAY_MID_TREND',
 'H1_EMA100_REJECTION','H4_EMA100_REJECTION','M15_EMA50_WICK','M30_EMA50_WICK',
 'H1_H4_SWING_CONTINUATION','H1_H4_SWING_REVERSAL','M15_LIQUIDITY_SPRING',
 'M30_RANGE_SWEEP','H1_RANGE_BREAK_RETEST','M15_RANGE_BREAK_RETEST',
 'VWAP_DEEP_PULLBACK','VWAP_TREND_ACCELERATION','VWAP_EXTREME_REVERSION',
 'BOLLINGER_TWO_SIGMA_RECLAIM','BOLLINGER_WALK_RETEST','MACD_HIST_TWO_BAR_FLIP',
 'RSI_35_65_REVERSAL','STOCH_DIVERGENCE_PROXY','M5_INSIDE_BAR_BREAK',
 'M5_THREE_BAR_REVERSAL','ROLLING72_FAKE_BREAK','ROLLING48_DISPLACEMENT',
 'NY_ORB_QUARTILE_RECLAIM','NY_ORB_DOUBLE_BREAK','PREVDAY_RANGE_COMPRESSION_BREAK',
 'EMA200_COUNTER_TREND_SPRING','M30_H4_EMA_CONFLUENCE'
)
def _v31_raw(f,name):
 import numpy as np,pandas as pd
 o,h,l,c,pc,a=(f[k] for k in ('o','h','l','c','pc','a'))
 e20,e50,e100=(f[k] for k in ('e20','e50','e100'))
 m15,m30,h1,h4=(f[k] for k in ('m15','m30','h1','h4'))
 z=np.zeros(len(c),dtype=bool)
 sh=lambda v,n:np.r_[np.full(n,np.nan),v[:-n]]
 ph,pl=f['dh'],f['dl'];wh,wl=f['wh'],f['wl'];hi24,lo24=f['hi24'],f['lo24'];hi48,lo48=f['hi48'],f['lo48']
 ma200=f.get('e200')
 if ma200 is None:ma200=pd.Series(c).ewm(span=200,adjust=False).mean().to_numpy(float)
 up=z;dn=z
 if name=='WEEK_Q10_BOUNCE':
  x=wl+.10*(wh-wl);up=(l<x-.12*a)&(c>x+.17*a);dn=z
 elif name=='WEEK_Q90_FADE':
  x=wl+.90*(wh-wl);up=z;dn=(h>x+.12*a)&(c<x-.17*a)
 elif name=='WEEK_MID_MOMENTUM':
  x=(wl+wh)/2;up=(pc<x-.13*a)&(c>x+.22*a)&(e50>e100);dn=(pc>x+.13*a)&(c<x-.22*a)&(e50<e100)
 elif name=='WEEK_HIGH_BREAK_RETEST':
  up=(pc>wh+.06*a)&(l<wh+.14*a)&(c>wh+.25*a);dn=z
 elif name=='WEEK_LOW_BREAK_RETEST':
  up=z;dn=(pc<wl-.06*a)&(h>wl-.14*a)&(c<wl-.25*a)
 elif name=='PREVDAY_Q10_BOUNCE':
  x=pl+.10*(ph-pl);up=(l<x-.12*a)&(c>x+.19*a);dn=z
 elif name=='PREVDAY_Q90_FADE':
  x=pl+.90*(ph-pl);up=z;dn=(h>x+.12*a)&(c<x-.19*a)
 elif name=='PREVDAY_OPEN_REJECTION':
  x=f['dopen'];up=(l<x-.23*a)&(c>x+.26*a)&(e20>e50);dn=(h>x+.23*a)&(c<x-.26*a)&(e20<e50)
 elif name=='PREVDAY_MID_TREND':
  x=(ph+pl)/2;up=(l<x-.18*a)&(c>x+.22*a)&h1['up'];dn=(h>x+.18*a)&(c<x-.22*a)&h1['dn']
 elif name=='H1_EMA100_REJECTION':
  x=h1['e50'];up=(l<x-.22*a)&(c>x+.23*a)&h1['up'];dn=(h>x+.22*a)&(c<x-.23*a)&h1['dn']
 elif name=='H4_EMA100_REJECTION':
  x=h4['e50'];up=(l<x-.24*a)&(c>x+.25*a)&h4['up'];dn=(h>x+.24*a)&(c<x-.25*a)&h4['dn']
 elif name=='M15_EMA50_WICK':
  x=m15['e50'];up=(l<x-.27*a)&(c>x+.18*a)&h1['up'];dn=(h>x+.27*a)&(c<x-.18*a)&h1['dn']
 elif name=='M30_EMA50_WICK':
  x=m30['e50'];up=(l<x-.27*a)&(c>x+.18*a)&h4['up'];dn=(h>x+.27*a)&(c<x-.18*a)&h4['dn']
 elif name=='H1_H4_SWING_CONTINUATION':
  up=h1['up']&h4['up']&(l<e50-.27*a)&(c>e50+.26*a);dn=h1['dn']&h4['dn']&(h>e50+.27*a)&(c<e50-.26*a)
 elif name=='H1_H4_SWING_REVERSAL':
  up=h1['dn']&h4['up']&(l<f['lo24']-.17*a)&(c>f['lo24']+.20*a);dn=h1['up']&h4['dn']&(h>f['hi24']+.17*a)&(c<f['hi24']-.20*a)
 elif name=='M15_LIQUIDITY_SPRING':
  up=(l<m15['lo12']-.15*a)&(c>m15['lo12']+.21*a);dn=(h>m15['hi12']+.15*a)&(c<m15['hi12']-.21*a)
 elif name=='M30_RANGE_SWEEP':
  up=(l<m30['lo12']-.15*a)&(c>m30['lo12']+.21*a);dn=(h>m30['hi12']+.15*a)&(c<m30['hi12']-.21*a)
 elif name=='H1_RANGE_BREAK_RETEST':
  up=(pc>h1['hi12']-.07*a)&(l<h1['hi12']+.15*a)&(c>h1['hi12']+.29*a);dn=(pc<h1['lo12']+.07*a)&(h>h1['lo12']-.15*a)&(c<h1['lo12']-.29*a)
 elif name=='M15_RANGE_BREAK_RETEST':
  up=(pc>m15['hi12']-.07*a)&(l<m15['hi12']+.15*a)&(c>m15['hi12']+.29*a);dn=(pc<m15['lo12']+.07*a)&(h>m15['lo12']-.15*a)&(c<m15['lo12']-.29*a)
 elif name=='VWAP_DEEP_PULLBACK':
  vw=f['vw'];up=(l<vw-1.25*a)&(c>vw-.60*a)&(e50>e100);dn=(h>vw+1.25*a)&(c<vw+.60*a)&(e50<e100)
 elif name=='VWAP_TREND_ACCELERATION':
  vw=f['vw'];up=(pc<vw+.33*a)&(c>vw+.8*a)&(e20>e50);dn=(pc>vw-.33*a)&(c<vw-.8*a)&(e20<e50)
 elif name=='VWAP_EXTREME_REVERSION':
  vw=f['vw'];up=(l<vw-2.0*a)&(c>vw-1.1*a);dn=(h>vw+2.0*a)&(c<vw+1.1*a)
 elif name=='BOLLINGER_TWO_SIGMA_RECLAIM':
  x=f['bb']-2.3*f['bs'];y=f['bb']+2.3*f['bs'];up=(l<x-.13*a)&(c>x+.25*a);dn=(h>y+.13*a)&(c<y-.25*a)
 elif name=='BOLLINGER_WALK_RETEST':
  x=f['bb']+f['bs'];y=f['bb']-f['bs'];up=(pc>x+.17*a)&(l<x-.22*a)&(c>x+.21*a);dn=(pc<y-.17*a)&(h>y+.22*a)&(c<y-.21*a)
 elif name=='MACD_HIST_TWO_BAR_FLIP':
  mh=f['macdh'];up=(sh(mh,3)<-.035*a)&(sh(mh,1)<0)&(mh>.055*a);dn=(sh(mh,3)>.035*a)&(sh(mh,1)>0)&(mh<-.055*a)
 elif name=='RSI_35_65_REVERSAL':
  rr=f['rsi'];up=(sh(rr,3)<34)&(rr>45)&(l<lo24+.23*a);dn=(sh(rr,3)>66)&(rr<55)&(h>hi24-.23*a)
 elif name=='STOCH_DIVERGENCE_PROXY':
  kk=f['k'];up=(l<sh(l,4)-.16*a)&(kk>sh(kk,4)+12)&(kk<48);dn=(h>sh(h,4)+.16*a)&(kk<sh(kk,4)-12)&(kk>52)
 elif name=='M5_INSIDE_BAR_BREAK':
  inside=(sh(h,1)<sh(h,2))&(sh(l,1)>sh(l,2));up=inside&(c>sh(h,2)+.12*a)&(e20>e50);dn=inside&(c<sh(l,2)-.12*a)&(e20<e50)
 elif name=='M5_THREE_BAR_REVERSAL':
  up=(l<sh(l,1))&(sh(l,1)<sh(l,2))&(c>sh(h,1)+.16*a);dn=(h>sh(h,1))&(sh(h,1)>sh(h,2))&(c<sh(l,1)-.16*a)
 elif name=='ROLLING72_FAKE_BREAK':
  hi=pd.Series(h).shift(1).rolling(72,min_periods=72).max().to_numpy();lo=pd.Series(l).shift(1).rolling(72,min_periods=72).min().to_numpy()
  up=(l<lo-.18*a)&(c>lo+.21*a);dn=(h>hi+.18*a)&(c<hi-.21*a)
 elif name=='ROLLING48_DISPLACEMENT':
  up=(pc<hi48+.05*a)&(c>hi48+.32*a)&(e50>e100);dn=(pc>lo48-.05*a)&(c<lo48-.32*a)&(e50<e100)
 elif name=='NY_ORB_QUARTILE_RECLAIM':
  x=f['orl']+.25*(f['orh']-f['orl']);y=f['orl']+.75*(f['orh']-f['orl'])
  up=(pc<x-.09*a)&(c>x+.20*a);dn=(pc>y+.09*a)&(c<y-.20*a)
 elif name=='NY_ORB_DOUBLE_BREAK':
  up=(sh(c,2)<f['orh']-.1*a)&(pc<f['orh']+.08*a)&(c>f['orh']+.28*a);dn=(sh(c,2)>f['orl']+.1*a)&(pc>f['orl']-.08*a)&(c<f['orl']-.28*a)
 elif name=='PREVDAY_RANGE_COMPRESSION_BREAK':
  day_range=ph-pl;up=(day_range<10*a)&(pc<ph-.05*a)&(c>ph+.25*a);dn=(day_range<10*a)&(pc>pl+.05*a)&(c<pl-.25*a)
 elif name=='EMA200_COUNTER_TREND_SPRING':
  up=(e50<ma200)&(l<ma200-.40*a)&(c>ma200-.12*a)&(f['rsi']<52);dn=(e50>ma200)&(h>ma200+.40*a)&(c<ma200+.12*a)&(f['rsi']>48)
 elif name=='M30_H4_EMA_CONFLUENCE':
  up=h4['up']&(l<m30['e20']-.23*a)&(c>m30['e20']+.20*a);dn=h4['dn']&(h>m30['e20']+.23*a)&(c<m30['e20']-.20*a)
 else:raise ValueError(name)
 # Original strategies use 3R, next-open, and M5 ATR/pivotal stop. New groups only.
 longstop=np.minimum(l,f['lo8'])-.15*a;shortstop=np.maximum(h,f['hi8'])+.15*a
 goodup=up&(c>o)&(c-longstop>.20*a)&(c-longstop<6*a)&np.isfinite(longstop)
 gooddn=dn&(c<o)&(shortstop-c>.20*a)&(shortstop-c<6*a)&np.isfinite(shortstop)
 side=np.where(goodup&~gooddn,1,np.where(gooddn&~goodup,-1,0)).astype(np.int8)
 stop=np.where(side>0,longstop,np.where(side<0,shortstop,np.nan))
 return side,stop

V31_SELECTED_GROUPS = ((26, (0.10000000149011612, 0.8799999952316284, 0.949999988079071, 0.800000011920929, 14.0, 0.0, 3.0, -1.0, 4.0)), (2, (0.6800000071525574, 0.7400000095367432, 0.949999988079071, 0.6499999761581421, 29.0, 44.0, 1.0, 0.0, 0.0)), (14, (0.18000000715255737, 0.550000011920929, 0.699999988079071, 0.800000011920929, 0.0, 38.0, 0.0, 1.0, 0.0)))
V31_VERSION = 'NAS100_M5_V3_1_ADD_ONLY_RESEARCH_CANDIDATE'

class NAS100V31AddOnly(NAS100V30FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        base_p=out['Position'].to_numpy(np.int8).copy()
        base_stop=out['strategy_stop_loss'].to_numpy(float).copy()
        base_tp=out['strategy_target'].to_numpy(float).copy()
        base_reason=out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        pp=base_p.copy();ss=base_stop.copy();tt=base_tp.copy();reason=base_reason.copy()
        # All features are computed causally using M5 closed candles and completed HTF projection.
        f=_v27_bank(out)
        n=len(out);ids=np.arange(n)
        feat={k:np.asarray(f[k],dtype=np.float32) for k in ('body','q','bearq','rv','ar','adx','rsi')}
        f['e200']=pd.Series(f['c']).ewm(span=200,adjust=False).mean().to_numpy(float)
        group_counts={}
        for family_idx,cfg in V31_SELECTED_GROUPS:
            name=V31_FAMILIES[family_idx]
            direction,stops=_v31_raw(f,name)
            direction=np.asarray(direction,dtype=np.int8)
            stops=np.asarray(stops,dtype=np.float32)
            body,quality,rv,ar,adx,rsi,trend,choice,session=cfg
            directional_quality=np.where(direction>0,feat['q'],feat['bearq'])
            directional_rsi=np.where(direction>0,feat['rsi'],100-feat['rsi'])
            good=(direction!=0)&(base_p==0)&(pp==0)&(ids>=self.LIVE_HISTORY_BARS)&(ids<n-1)&(f['dow']<5)&np.isfinite(stops)
            good&=(feat['body']>=np.float32(body))&(directional_quality>=np.float32(quality))
            good&=(feat['rv']>=np.float32(rv))&(feat['ar']>=np.float32(ar))&(feat['adx']>=np.float32(adx))&(directional_rsi>=np.float32(rsi))
            if int(trend):
                h1=np.where(direction>0,f['h1']['up'],f['h1']['dn'])
                h4=np.where(direction>0,f['h4']['up'],f['h4']['dn'])
                if int(trend)==1:good &= h1
                elif int(trend)==2:good &= h4
                elif int(trend)==3:good &= h1&h4
            if int(choice):good&=(direction==int(choice))
            minute=f['minute']
            if int(session)==1:good&=(minute>=570)&(minute<690)
            elif int(session)==2:good&=(minute>=570)&(minute<870)
            elif int(session)==3:good&=(minute>=600)&(minute<960)
            elif int(session)==4:good&=(minute>=480)&(minute<960)
            elif int(session)==5:good&=(minute>=660)&(minute<900)
            valid=np.flatnonzero(good)
            pp[valid]=direction[valid]
            ss[valid]=stops[valid]
            tt[valid]=(f['c'][valid]+direction[valid]*3*np.abs(f['c'][valid]-stops[valid])).astype(np.float32)
            reason[valid]=['V3_1_'+name]*len(valid)
            group_counts[name]=int(len(valid))
        had=base_p!=0
        assert np.array_equal(pp[had],base_p[had])
        assert np.array_equal(ss[had],base_stop[had],equal_nan=True)
        assert np.array_equal(tt[had],base_tp[had],equal_nan=True)
        assert np.array_equal(reason[had],base_reason[had])
        assert not np.any((base_p==0)&(pp==0)&(reason!=base_reason)), 'New-entry reason must match new signal'
        out['Position']=pp
        out['strategy_stop_loss']=ss
        out['strategy_target']=tt
        out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
          'version':V31_VERSION,
          'frozen_baseline':'V3.0',
          'research_mode':'ADD_NEW_WINNING_TRADES_ONLY',
          'groups':group_counts,
          'original_signals_preserved':True,
          'native_algoagentx_verified':False,
          'forward_validation_untouched':False,
          'research_only':True}
        return out

Strategy=NAS100V31AddOnly


# ===== V3.2 FILTER-ONLY RESEARCH OVERLAY =====
# The entire frozen V3.1 source above is preserved byte-for-byte.
# No new entries, no SL/TP or risk changes, no custom imports.
V32_VERSION = 'NAS100_M5_V3_2_FILTER_ONLY_RESEARCH_CANDIDATE'
V32_REJECTION_GROUPS = ((('channel24_pos', '>=', 1.0356107950210571), ('bar_range_atr', '<=', 0.7276761531829834)), (('bbwidth', '<=', 2.5981898307800293), ('bar_range_atr', '>=', 2.6520047187805176)))

class NAS100V32FilterOnly(NAS100V31AddOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        baseline_pos = out['Position'].to_numpy(dtype=np.int8).copy()
        baseline_sl = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        baseline_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        baseline_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        ctx = _v28_context(out, baseline_pos, baseline_sl)
        h = out['High'].to_numpy(float)
        l = out['Low'].to_numpy(float)
        c = out['Close'].to_numpy(float)
        previous = np.r_[c[0],c[:-1]]
        tr = np.maximum(h-l,np.maximum(np.abs(h-previous),np.abs(l-previous)))
        atr = np.maximum(pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy(float),1e-9)
        ctx['bar_range_atr'] = (h-l)/atr
        ctx['bbwidth'] = 4*pd.Series(c).rolling(20,min_periods=20).std(ddof=0).to_numpy(float)/atr
        rejected = np.zeros(len(out),dtype=bool)
        for conjunction in V32_REJECTION_GROUPS:
            group = np.ones(len(out),dtype=bool)
            for feature,comparison,threshold in conjunction:
                v = np.asarray(ctx[feature],dtype=np.float32)
                t = np.float32(threshold)
                group &= np.isfinite(v) & ((v<=t) if comparison == '<=' else (v>=t))
            rejected |= group
        rejected &= (baseline_pos!=0)&(np.arange(len(out))>=self.LIVE_HISTORY_BARS)
        pos = baseline_pos.copy();sl=baseline_sl.copy();tp=baseline_tp.copy();reason=baseline_reason.copy()
        pos[rejected]=0;sl[rejected]=np.nan;tp[rejected]=np.nan;reason[rejected]=''
        kept=~rejected
        assert not np.any((baseline_pos==0)&(pos!=0)), 'V3.2 must not add signals'
        assert np.array_equal(pos[kept],baseline_pos[kept])
        assert np.array_equal(sl[kept],baseline_sl[kept],equal_nan=True)
        assert np.array_equal(tp[kept],baseline_tp[kept],equal_nan=True)
        assert np.array_equal(reason[kept],baseline_reason[kept])
        out['Position']=pos
        out['strategy_stop_loss']=sl
        out['strategy_target']=tp
        out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
            'version':V32_VERSION,'frozen_baseline':'V3.1',
            'research_mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_intents':int(rejected.sum()),'new_entry_intents':0,
            'prior_signals_stops_targets_preserved':True,
            'native_algoagentx_verified':False,
            'untouched_forward_validation':False,
            'research_only':True}
        return out

Strategy=NAS100V32FilterOnly


# ==== V3.3 FILTER EXISTING LOSING TRADES ONLY ====
# Above source contains the complete frozen V3.2 strategy unchanged byte-for-byte.
V33_VERSION = 'NAS100_M5_V3_3_FILTER_ONLY_RESEARCH_CANDIDATE'
V33_REJECTION_GROUPS = ((('rsi_raw', '>=', 72.27560424804688), ('momentum_96', '<=', 6.172241687774658), ('volume_z', '<=', 2.2937428951263428)), (('momentum_12', '<=', -2.008460283279419), ('range24_atr', '>=', 7.475912094116211)))

class NAS100V33FilterOnly(NAS100V32FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        old_pos = result['Position'].to_numpy(dtype=np.int8).copy()
        old_stop = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        # All indicators use the completed current M5 bar and earlier bars.
        features = _v28_context(result, old_pos, old_stop)
        reject = np.zeros(len(result), dtype=bool)
        for conjunction in V33_REJECTION_GROUPS:
            meets = np.ones(len(result), dtype=bool)
            for name, comparison, threshold in conjunction:
                arr = np.asarray(features[name], dtype=np.float32)
                bound = np.float32(threshold)
                meets &= np.isfinite(arr) & ((arr <= bound) if comparison == '<=' else (arr >= bound))
            reject |= meets
        reject &= (old_pos != 0) & (np.arange(len(result)) >= self.LIVE_HISTORY_BARS)
        pos = old_pos.copy(); stop = old_stop.copy(); target = old_tp.copy(); reason = old_reason.copy()
        pos[reject] = 0; stop[reject] = np.nan; target[reject] = np.nan; reason[reject] = ''
        kept = ~reject
        assert np.array_equal(pos[kept], old_pos[kept])
        assert np.array_equal(stop[kept], old_stop[kept], equal_nan=True)
        assert np.array_equal(target[kept], old_tp[kept], equal_nan=True)
        assert np.array_equal(reason[kept], old_reason[kept])
        assert not np.any((old_pos == 0) & (pos != 0)), 'V3.3 cannot add signals'
        result['Position'] = pos
        result['strategy_stop_loss'] = stop
        result['strategy_target'] = target
        result['signal_reason'] = reason
        result.attrs['strategy_diagnostics'] = {
            'version':V33_VERSION,'frozen_baseline':'V3.2',
            'research_mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_intents':int(reject.sum()),'new_intents':0,
            'preserved_original_sl_tp':True,'native_algoagentx_verified':False,
            'untouched_forward_validation':False,'research_only':True}
        return result

Strategy = NAS100V33FilterOnly


# ==== V3.4 FILTER_EXISTING_LOSING_TRADES_ONLY — RESEARCH ONLY ====
# Source above is the byte-identical frozen V3.3 baseline. No new entries, SL/TP changes or extra imports.
V34_VERSION = 'NAS100_M5_V3_4_FILTER_ONLY_RESEARCH_CANDIDATE'
V34_REJECTION_GROUPS = ((('atr_slope_12', '>=', 2.130690097808838), ('stop_atr', '>=', 3.370675802230835)), (('atr_rel', '>=', 3.4761691093444824), ('stoch_raw', '<=', 1.4455089569091797)))

class NAS100V34FilterOnly(NAS100V33FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        old_pos = result['Position'].to_numpy(dtype=np.int8).copy()
        old_stop = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(result, old_pos, old_stop)
        reject = np.zeros(len(result), dtype=bool)
        for group in V34_REJECTION_GROUPS:
            meets = np.ones(len(result), dtype=bool)
            for field, op, threshold in group:
                values = np.asarray(features[field], dtype=np.float32)
                th = np.float32(threshold)
                meets &= np.isfinite(values) & ((values <= th) if op == '<=' else (values >= th))
            reject |= meets
        reject &= (old_pos != 0) & (np.arange(len(result)) >= self.LIVE_HISTORY_BARS)
        pos = old_pos.copy(); stop = old_stop.copy(); target = old_tp.copy(); reason = old_reason.copy()
        pos[reject] = 0; stop[reject] = np.nan; target[reject] = np.nan; reason[reject] = ''
        retained = ~reject
        assert not np.any((old_pos == 0) & (pos != 0))
        assert np.array_equal(pos[retained], old_pos[retained])
        assert np.array_equal(stop[retained], old_stop[retained], equal_nan=True)
        assert np.array_equal(target[retained], old_tp[retained], equal_nan=True)
        assert np.array_equal(reason[retained], old_reason[retained])
        result['Position'] = pos
        result['strategy_stop_loss'] = stop
        result['strategy_target'] = target
        result['signal_reason'] = reason
        result.attrs['strategy_diagnostics'] = {
           'version': V34_VERSION, 'frozen_baseline': 'V3.3',
           'research_mode': 'FILTER_EXISTING_LOSING_TRADES_ONLY',
           'rejected_raw_signals': int(reject.sum()), 'added_raw_signals': 0,
           'baseline_stop_target_preserved': True, 'native_algoagentx_verified': False,
           'untouched_forward_validation': False, 'research_only': True}
        return result

Strategy = NAS100V34FilterOnly


# ==== NAS100 V3.5 ADD_NEW_WINNING_TRADES_ONLY — RESEARCH CANDIDATE ====
# All V3.4 source above is byte-identical to the accepted frozen baseline.
"""V3.5 novel closed-bar M5 signal families; no changes to V3.4.
Input bank is frozen _v27_bank(DataFrame) from V3.4, with confirmed HTF candles.
All proposed raw families are independent and add-only overlays are gated downstream.
"""
import numpy as np
import pandas as pd
V35_FAMILIES=(
 'WEEK_Q05_SPRING','WEEK_Q95_UPTHRUST','WEEK_Q15_PULLBACK','WEEK_Q85_PULLBACK',
 'WEEK_Q40_MOMENTUM','WEEK_Q60_MOMENTUM','WEEK_FIRST_BREAK_FAIL',
 'DAY_Q33_REVERSAL','DAY_Q67_REVERSAL','DAY_HI_AFTER_BREAK_FAIL','DAY_LO_AFTER_BREAK_FAIL',
 'DAY_OPEN_FIRST_RETEST','DAY_MID_SWEEP','WEEK_MID_RSI_REGIME',
 'H1_EMA20_ADX_RESET','H1_EMA50_LIQUIDITY_FADE','H4_EMA20_ATR_EXPANSION','H4_EMA50_MACD_RESET',
 'M15_EMA100_REJECTION','M30_EMA100_REJECTION','M15_SLOW_RANGE_EXPANSION',
 'M30_RANGE_REVERSAL','H1_RANGE_REENTRY','H4_RANGE_MOMENTUM',
 'VWAP_TREND_TWO_PULLBACK','VWAP_BAND_3SIG_REVERSAL','VWAP_H1_MOMENTUM','BBWIDTH_TREND_BREAK',
 'BBWIDTH_REVERSAL','MACD_H1_DISPLACEMENT','RSI_EXTREME_WICK','STOCH_KD_FLIP',
 'DOUBLE_INSIDE_RANGE_BREAK','SEQUENTIAL_SWEEP_48','SEQUENTIAL_BOS_24','H1_H4_CONFLICT_RECLAIM',
)
def _v35_raw(f,name):
    o,h,l,c,pc,a=[f[k] for k in ('o','h','l','c','pc','a')]
    m15,m30,h1,h4=[f[k] for k in ('m15','m30','h1','h4')]
    e20,e50,e100=[f[k] for k in ('e20','e50','e100')]
    rsi,adx,rv=f['rsi'],f['adx'],f['rv']
    sh=lambda x,k: np.r_[np.full(k,np.nan),x[:-k]]
    up=np.zeros(len(c),bool);dn=up
    wl,wh,dl,dh=f['wl'],f['wh'],f['dl'],f['dh']
    if name=='WEEK_Q05_SPRING':
        x=wl+.05*(wh-wl);up=(l<x-.08*a)&(c>x+.18*a)&(rsi<53)
    elif name=='WEEK_Q95_UPTHRUST':
        x=wl+.95*(wh-wl);dn=(h>x+.08*a)&(c<x-.18*a)&(rsi>47)
    elif name=='WEEK_Q15_PULLBACK':
        x=wl+.15*(wh-wl);up=(l<x-.08*a)&(c>x+.13*a)&h4['up'];dn=(h>x+.08*a)&(c<x-.13*a)&h4['dn']
    elif name=='WEEK_Q85_PULLBACK':
        x=wl+.85*(wh-wl);up=(l<x-.08*a)&(c>x+.13*a)&h4['up'];dn=(h>x+.08*a)&(c<x-.13*a)&h4['dn']
    elif name=='WEEK_Q40_MOMENTUM':
        x=wl+.40*(wh-wl);up=(pc<x-.04*a)&(c>x+.23*a)&h1['up'];dn=(pc>x+.04*a)&(c<x-.23*a)&h1['dn']
    elif name=='WEEK_Q60_MOMENTUM':
        x=wl+.60*(wh-wl);up=(pc<x-.04*a)&(c>x+.23*a)&h1['up'];dn=(pc>x+.04*a)&(c<x-.23*a)&h1['dn']
    elif name=='WEEK_FIRST_BREAK_FAIL':
        up=(sh(c,1)<wl-.15*a)&(l<wl-.20*a)&(c>wl+.20*a);dn=(sh(c,1)>wh+.15*a)&(h>wh+.20*a)&(c<wh-.20*a)
    elif name=='DAY_Q33_REVERSAL':
        x=dl+(dh-dl)/3;up=(l<x-.24*a)&(c>x+.25*a)&(rsi<57);dn=(h>x+.24*a)&(c<x-.25*a)&(rsi>43)
    elif name=='DAY_Q67_REVERSAL':
        x=dl+(dh-dl)*2/3;up=(l<x-.24*a)&(c>x+.25*a)&(rsi<57);dn=(h>x+.24*a)&(c<x-.25*a)&(rsi>43)
    elif name=='DAY_HI_AFTER_BREAK_FAIL':
        dn=(sh(c,2)>dh+.14*a)&(h>dh+.22*a)&(c<dh-.26*a)
    elif name=='DAY_LO_AFTER_BREAK_FAIL':
        up=(sh(c,2)<dl-.14*a)&(l<dl-.22*a)&(c>dl+.26*a)
    elif name=='DAY_OPEN_FIRST_RETEST':
        x=f['dopen'];up=(pc>x+.15*a)&(l<x-.11*a)&(c>x+.28*a)&(e20>e100);dn=(pc<x-.15*a)&(h>x+.11*a)&(c<x-.28*a)&(e20<e100)
    elif name=='DAY_MID_SWEEP':
        x=(dh+dl)/2;up=(l<x-.34*a)&(c>x+.21*a)&(f['k']<65);dn=(h>x+.34*a)&(c<x-.21*a)&(f['k']>35)
    elif name=='WEEK_MID_RSI_REGIME':
        x=(wh+wl)/2;up=(pc<x-.16*a)&(c>x+.19*a)&(rsi>52);dn=(pc>x+.16*a)&(c<x-.19*a)&(rsi<48)
    elif name=='H1_EMA20_ADX_RESET':
        x=h1['e20'];up=(l<x-.32*a)&(c>x+.20*a)&(adx>20)&(h1['up']);dn=(h>x+.32*a)&(c<x-.20*a)&(adx>20)&(h1['dn'])
    elif name=='H1_EMA50_LIQUIDITY_FADE':
        x=h1['e50'];up=(l<x-.46*a)&(c>x+.17*a)&(h1['dn']);dn=(h>x+.46*a)&(c<x-.17*a)&(h1['up'])
    elif name=='H4_EMA20_ATR_EXPANSION':
        x=h4['e20'];up=(l<x-.17*a)&(c>x+.31*a)&h4['up']&(f['ar']>1.08);dn=(h>x+.17*a)&(c<x-.31*a)&h4['dn']&(f['ar']>1.08)
    elif name=='H4_EMA50_MACD_RESET':
        x=h4['e50'];up=(l<x-.35*a)&(c>x+.23*a)&(f['macdh']>0);dn=(h>x+.35*a)&(c<x-.23*a)&(f['macdh']<0)
    elif name=='M15_EMA100_REJECTION':
        x=m15['e50'];up=(l<x-.43*a)&(c>x+.22*a)&m15['up']&(e50>e100);dn=(h>x+.43*a)&(c<x-.22*a)&m15['dn']&(e50<e100)
    elif name=='M30_EMA100_REJECTION':
        x=m30['e50'];up=(l<x-.43*a)&(c>x+.22*a)&m30['up']&(e50>e100);dn=(h>x+.43*a)&(c<x-.22*a)&m30['dn']&(e50<e100)
    elif name=='M15_SLOW_RANGE_EXPANSION':
        up=(c>m15['hi12']+.30*a)&(h1['up'])&(f['bs']/a<2.8);dn=(c<m15['lo12']-.30*a)&(h1['dn'])&(f['bs']/a<2.8)
    elif name=='M30_RANGE_REVERSAL':
        up=(l<m30['lo12']-.28*a)&(c>m30['lo12']+.28*a)&(rsi>38);dn=(h>m30['hi12']+.28*a)&(c<m30['hi12']-.28*a)&(rsi<62)
    elif name=='H1_RANGE_REENTRY':
        up=(l<h1['lo12']-.20*a)&(c>h1['lo12']+.33*a)&(rsi>41);dn=(h>h1['hi12']+.20*a)&(c<h1['hi12']-.33*a)&(rsi<59)
    elif name=='H4_RANGE_MOMENTUM':
        up=(pc<h4['hi12']-.15*a)&(c>h4['hi12']+.39*a)&h1['up'];dn=(pc>h4['lo12']+.15*a)&(c<h4['lo12']-.39*a)&h1['dn']
    elif name=='VWAP_TREND_TWO_PULLBACK':
        vw=f['vw'];up=(sh(l,1)<vw-.25*a)&(l<vw-.15*a)&(c>vw+.30*a)&h1['up'];dn=(sh(h,1)>vw+.25*a)&(h>vw+.15*a)&(c<vw-.30*a)&h1['dn']
    elif name=='VWAP_BAND_3SIG_REVERSAL':
        vw=f['vw'];up=(l<vw-3*a)&(c>vw-1.75*a);dn=(h>vw+3*a)&(c<vw+1.75*a)
    elif name=='VWAP_H1_MOMENTUM':
        vw=f['vw'];up=(pc<vw-.17*a)&(c>vw+.40*a)&h1['up'];dn=(pc>vw+.17*a)&(c<vw-.40*a)&h1['dn']
    elif name=='BBWIDTH_TREND_BREAK':
        up=(4*f['bs']/a<3.0)&(c>f['hi24']+.25*a)&h1['up'];dn=(4*f['bs']/a<3.0)&(c<f['lo24']-.25*a)&h1['dn']
    elif name=='BBWIDTH_REVERSAL':
        up=(4*f['bs']/a>9.0)&(l<f['lo24']-.20*a)&(c>f['lo24']+.21*a);dn=(4*f['bs']/a>9.0)&(h>f['hi24']+.20*a)&(c<f['hi24']-.21*a)
    elif name=='MACD_H1_DISPLACEMENT':
        up=(sh(f['macdh'],3)<0)&(f['macdh']>.13*a)&(h1['up']);dn=(sh(f['macdh'],3)>0)&(f['macdh']<-.13*a)&h1['dn']
    elif name=='RSI_EXTREME_WICK':
        up=(sh(rsi,3)<24)&(rsi>34)&(l<f['lo24']+.20*a);dn=(sh(rsi,3)>76)&(rsi<66)&(h>f['hi24']-.20*a)
    elif name=='STOCH_KD_FLIP':
        up=(sh(f['k'],2)<18)&(f['k']>44)&(f['k']>f['ks']+8)&(e20>e50);dn=(sh(f['k'],2)>82)&(f['k']<56)&(f['k']<f['ks']-8)&(e20<e50)
    elif name=='DOUBLE_INSIDE_RANGE_BREAK':
        inside=(sh(h,1)<sh(h,2))&(sh(l,1)>sh(l,2))&(sh(h,2)<sh(h,3))&(sh(l,2)>sh(l,3))
        up=inside&(c>sh(h,3)+.15*a)&(h1['up']);dn=inside&(c<sh(l,3)-.15*a)&h1['dn']
    elif name=='SEQUENTIAL_SWEEP_48':
        up=(sh(l,1)<f['lo48']-.16*a)&(c>f['lo48']+.26*a)&(rsi>44);dn=(sh(h,1)>f['hi48']+.16*a)&(c<f['hi48']-.26*a)&(rsi<56)
    elif name=='SEQUENTIAL_BOS_24':
        up=(sh(c,2)>f['hi24']+.10*a)&(l<f['hi24']+.12*a)&(c>f['hi24']+.31*a);dn=(sh(c,2)<f['lo24']-.10*a)&(h>f['lo24']-.12*a)&(c<f['lo24']-.31*a)
    elif name=='H1_H4_CONFLICT_RECLAIM':
        up=h1['dn']&h4['up']&(l<e100-.30*a)&(c>e100+.30*a);dn=h1['up']&h4['dn']&(h>e100+.30*a)&(c<e100-.30*a)
    else:raise ValueError(name)
    L=np.minimum(l,f['lo8'])-.15*a;S=np.maximum(h,f['hi8'])+.15*a
    long=up&(c>o)&np.isfinite(L)&(c-L>.2*a)&(c-L<6*a)
    short=dn&(c<o)&np.isfinite(S)&(S-c>.2*a)&(S-c<6*a)
    side=np.where(long&~short,1,np.where(short&~long,-1,0)).astype(np.int8)
    stop=np.where(side>0,L,np.where(side<0,S,np.nan))
    return side,stop

V35_VERSION = 'NAS100_M5_V3_5_ADD_ONLY_RESEARCH_CANDIDATE'
V35_SELECTED_GROUPS = ((28, (0.20000000298023224, 0.550000011920929, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0, 0.0)), (9, (0.10000000149011612, 0.550000011920929, 0.6499999761581421, 0.6499999761581421, 12.0, 36.0, 2.0, -1.0, 0.0)), (27, (0.30000001192092896, 0.8700000047683716, 0.6499999761581421, 0.800000011920929, 20.0, 48.0, 1.0, -1.0, 0.0)))
class NAS100V35AddOnly(NAS100V34FilterOnly):
    LIVE_HISTORY_BARS=80000
    def generate(self):
        result=super().generate()
        old_side=result['Position'].to_numpy(np.int8).copy()
        old_stop=result['strategy_stop_loss'].to_numpy(float).copy()
        old_target=result['strategy_target'].to_numpy(float).copy()
        old_reason=result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        side=old_side.copy(); stop=old_stop.copy(); target=old_target.copy(); reason=old_reason.copy()
        bank=_v27_bank(result)
        n=len(result);ii=np.arange(n);added=0;counts={}
        for fi,config in V35_SELECTED_GROUPS:
            # A new family is allowed to populate an EMPTY V3.4 signal timestamp only.
            family=V35_FAMILIES[fi]
            raw_side,raw_stop=_v35_raw(bank,family)
            new_tp=(bank['c']+raw_side*3*np.abs(bank['c']-raw_stop)).astype(np.float32)
            raw_stop=np.asarray(raw_stop,dtype=np.float32)
            body,quality,volume,relative_atr,adx_min,rsi_min,trend,choice,session=config
            body_m=np.asarray(bank['body'],dtype=np.float32)
            quality_m=np.asarray(np.where(raw_side>0,bank['q'],bank['bearq']),dtype=np.float32)
            volume_m=np.asarray(bank['rv'],dtype=np.float32)
            atr_m=np.asarray(bank['ar'],dtype=np.float32)
            adx_m=np.asarray(bank['adx'],dtype=np.float32)
            rsi_m=np.asarray(np.where(raw_side>0,bank['rsi'],100-bank['rsi']),dtype=np.float32)
            choose=(raw_side!=0)&(old_side==0)&(side==0)&(ii>=self.LIVE_HISTORY_BARS)&(bank['dow']<5)&np.isfinite(raw_stop)
            choose&=(body_m>=np.float32(body))&(quality_m>=np.float32(quality))&(volume_m>=np.float32(volume))
            choose&=(atr_m>=np.float32(relative_atr))&(adx_m>=np.float32(adx_min))&(rsi_m>=np.float32(rsi_min))
            if int(choice):choose&=(raw_side==int(choice))
            if int(trend):
                h1_agree=np.where(raw_side>0,bank['h1']['up'],bank['h1']['dn'])
                h4_agree=np.where(raw_side>0,bank['h4']['up'],bank['h4']['dn'])
                if int(trend)==1:choose &= h1_agree
                elif int(trend)==2:choose &= h4_agree
                elif int(trend)==3:choose &= h1_agree & h4_agree
            minute=bank['minute']
            if int(session)==1:choose&=(minute>=570)&(minute<690)
            elif int(session)==2:choose&=(minute>=570)&(minute<870)
            elif int(session)==3:choose&=(minute>=600)&(minute<960)
            elif int(session)==4:choose&=(minute>=480)&(minute<960)
            elif int(session)==5:choose&=(minute>=660)&(minute<900)
            # TP follows the unchanged original 3R convention, with float32
            # rounding matching the research source-generated signal arrays.
            side[choose]=raw_side[choose];stop[choose]=raw_stop[choose]
            target[choose]=new_tp[choose]
            reason[choose]='V3.5_'+family
            counts[family]=int(choose.sum());added+=counts[family]
        kept=old_side!=0
        assert np.array_equal(side[kept],old_side[kept])
        assert np.array_equal(stop[kept],old_stop[kept],equal_nan=True)
        assert np.array_equal(target[kept],old_target[kept],equal_nan=True)
        assert np.array_equal(reason[kept],old_reason[kept])
        result['Position']=side;result['strategy_stop_loss']=stop
        result['strategy_target']=target;result['signal_reason']=reason
        result.attrs['strategy_diagnostics']={'version':V35_VERSION,
            'frozen_baseline':'V3.4','mode':'ADD_NEW_WINNING_TRADES_ONLY',
            'added_raw_intents':added,'new_groups':counts,
            'baseline_entry_stop_target_preserved':True,
            'native_algoagentx_verified':False,'research_only':True}
        return result
Strategy=NAS100V35AddOnly


# ==== V3.6 FILTER_EXISTING_LOSING_TRADES_ONLY: RESEARCH CANDIDATE ====
# All source code above is byte-for-byte the accepted V3.5 source.
V36_VERSION = 'NAS100_M5_V3_6_FILTER_ONLY_RESEARCH_CANDIDATE'
V36_REJECTION_GROUPS = ((('ema20_gap_dir', '<=', -1.661760926246643), ('ema50_100_dir', '<=', -1.1058861017227173), ('upper_wick', '>=', 0.4602389633655548)), (('ema50_slope_48', '<=', -2.967622995376587), ('stop_atr', '<=', 0.9311659932136536), ('vwap_gap_dir', '<=', -5.691187858581543)))

class NAS100V36FilterOnly(NAS100V35AddOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        old_p = out['Position'].to_numpy(dtype=np.int8).copy()
        old_st = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(out, old_p, old_st)
        reject = np.zeros(len(out), dtype=bool)
        for conjunction in V36_REJECTION_GROUPS:
            meets = np.ones(len(out), dtype=bool)
            for field, comparison, threshold in conjunction:
                values = np.asarray(features[field], dtype=np.float32)
                bound = np.float32(threshold)
                meets &= np.isfinite(values) & ((values <= bound) if comparison == '<=' else (values >= bound))
            reject |= meets
        reject &= (old_p != 0) & (np.arange(len(out)) >= self.LIVE_HISTORY_BARS)
        pos=old_p.copy(); stop=old_st.copy(); target=old_tp.copy(); reason=old_reason.copy()
        pos[reject]=0; stop[reject]=np.nan; target[reject]=np.nan; reason[reject]=''
        keep=~reject
        assert not np.any((old_p==0) & (pos!=0))
        assert np.array_equal(pos[keep], old_p[keep])
        assert np.array_equal(stop[keep], old_st[keep], equal_nan=True)
        assert np.array_equal(target[keep], old_tp[keep], equal_nan=True)
        assert np.array_equal(reason[keep], old_reason[keep])
        out['Position']=pos; out['strategy_stop_loss']=stop
        out['strategy_target']=target; out['signal_reason']=reason
        out.attrs['strategy_diagnostics']={
            'version':V36_VERSION, 'baseline_version':'V3.5',
            'mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_existing_signal_intents':int(reject.sum()), 'new_signal_intents':0,
            'original_retained_signal_SL_TP_unchanged':True,
            'native_algoagentx_verified':False,'untouched_out_of_sample_verified':False,
            'research_only':True}
        return out

Strategy = NAS100V36FilterOnly


# ===== V3.7 NEW ENTRIES ONLY: frozen V3.6 source above is UNCHANGED =====
# Screened and tested through Oct 30 2026. Research-only; native verification pending.
LEVELS=('WEEK_Q10','WEEK_Q25','WEEK_Q50','WEEK_Q75','WEEK_Q90','DAY_Q25','DAY_Q50','DAY_Q75',
        'H1_EMA20','H1_EMA50','H4_EMA20','H4_EMA50','M15_EMA20','M30_EMA20','M30_EMA50','NY_VWAP')
PATTERNS=('SWEEP','CROSS','RETEST','ENGULF','SEQUENTIAL')
FAMILIES=tuple(f'{p}_{l}' for p in PATTERNS for l in LEVELS)

def _v37_raw(f,name):
    pattern,lev=name.split('_',1)
    o,h,l,c,pc,a=(f[k] for k in ('o','h','l','c','pc','a'))
    sh=lambda x,k:np.r_[np.full(k,np.nan),x[:-k]]
    if lev.startswith('WEEK_Q'):
        q=float(lev[6:])/100.;x=f['wl']+q*(f['wh']-f['wl'])
    elif lev.startswith('DAY_Q'):
        q=float(lev[5:])/100.;x=f['dl']+q*(f['dh']-f['dl'])
    elif lev=='NY_VWAP':x=f['vw']
    else:
        key,field=lev.split('_EMA');x=f[key.lower()]['e'+field]
    bull=c>o;bear=c<o
    if pattern=='SWEEP':
        up=(l<x-.14*a)&(c>x+.16*a)&(pc<x+.65*a)
        dn=(h>x+.14*a)&(c<x-.16*a)&(pc>x-.65*a)
    elif pattern=='CROSS':
        up=(pc<x-.10*a)&(c>x+.25*a)&(f['rsi']>47)
        dn=(pc>x+.10*a)&(c<x-.25*a)&(f['rsi']<53)
    elif pattern=='RETEST':
        up=(pc>x+.11*a)&(l<x-.11*a)&(c>x+.24*a)
        dn=(pc<x-.11*a)&(h>x+.11*a)&(c<x-.24*a)
    elif pattern=='ENGULF':
        up=(sh(c,1)<sh(o,1))&(o<sh(c,1)+.12*a)&(c>sh(o,1)+.12*a)&(l<x+.5*a)&(h>x-.5*a)
        dn=(sh(c,1)>sh(o,1))&(o>sh(c,1)-.12*a)&(c<sh(o,1)-.12*a)&(h>x-.5*a)&(l<x+.5*a)
    elif pattern=='SEQUENTIAL':
        up=(sh(l,1)<sh(x,1)-.15*a)&(sh(c,1)<sh(x,1)+.12*a)&(c>x+.22*a)&(f['k']>36)
        dn=(sh(h,1)>sh(x,1)+.15*a)&(sh(c,1)>sh(x,1)-.12*a)&(c<x-.22*a)&(f['k']<64)
    else:raise ValueError(name)
    # Exact same stop/target convention as existing V3.5 add-only overlay.
    L=np.minimum(l,f['lo8'])-.15*a;S=np.maximum(h,f['hi8'])+.15*a
    long=up&bull&(c-L>.2*a)&(c-L<6*a)&np.isfinite(L)
    short=dn&bear&(S-c>.2*a)&(S-c<6*a)&np.isfinite(S)
    side=np.where(long & ~short,1,np.where(short & ~long,-1,0)).astype(np.int8)
    stop=np.where(side>0,L,np.where(side<0,S,np.nan)).astype('f4')
    return side,stop


V37_VERSION = 'NAS100_M5_V3_7_ADD_ONLY_RESEARCH_CANDIDATE'
V37_SELECTED_GROUPS = ((39, (0.20000000298023224, 0.6499999761581421, 0.0, 0.800000011920929, 29.0, 0.0, 3.0, 1.0, 0.0)), (32, (0.20000000298023224, 0.550000011920929, 1.149999976158142, 1.2000000476837158, 0.0, 54.0, 0.0, 0.0, 4.0)), (31, (0.10000000149011612, 0.6499999761581421, 0.0, 1.0, 37.0, 36.0, 2.0, -1.0, 1.0)))

class NAS100V37AddOnly(NAS100V36FilterOnly):
    LIVE_HISTORY_BARS=80000

    @classmethod
    def apply_v37_additions(cls, result):
        old_side=result['Position'].to_numpy(dtype=np.int8).copy()
        old_stop=result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_target=result['strategy_target'].to_numpy(dtype=float).copy()
        old_reason=result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        side=old_side.copy();stop=old_stop.copy();target=old_target.copy();reason=old_reason.copy()
        bank=_v27_bank(result)
        n=len(result);ii=np.arange(n);added=0;counts={}
        for fi,cfg in V37_SELECTED_GROUPS:
            family=FAMILIES[fi]
            raw_side,raw_stop=_v37_raw(bank,family)
            new_tp=(bank['c']+raw_side*3*np.abs(bank['c']-raw_stop)).astype(np.float32)
            B,Q,RV,AR,ADX,RSI,trend,choice,session=cfg
            eligible=(raw_side!=0)&(old_side==0)&(side==0)&(ii>=cls.LIVE_HISTORY_BARS)&(ii<n-1)
            eligible&=(bank['dow']<5)&np.isfinite(raw_stop)
            body=np.asarray(bank['body'],dtype=np.float32)
            qual=np.asarray(np.where(raw_side>0,bank['q'],bank['bearq']),dtype=np.float32)
            vol=np.asarray(bank['rv'],dtype=np.float32)
            ar=np.asarray(bank['ar'],dtype=np.float32)
            adx=np.asarray(bank['adx'],dtype=np.float32)
            rsi=np.asarray(np.where(raw_side>0,bank['rsi'],100-bank['rsi']),dtype=np.float32)
            eligible &= (body>=np.float32(B))&(qual>=np.float32(Q))
            eligible &= (vol>=np.float32(RV))&(ar>=np.float32(AR))&(adx>=np.float32(ADX))&(rsi>=np.float32(RSI))
            if int(choice):eligible&=(raw_side==int(choice))
            if int(trend):
                h1=np.where(raw_side>0,bank['h1']['up'],bank['h1']['dn'])
                h4=np.where(raw_side>0,bank['h4']['up'],bank['h4']['dn'])
                if int(trend)==1:eligible&=h1
                elif int(trend)==2:eligible&=h4
                elif int(trend)==3:eligible&=h1&h4
            minute=bank['minute']
            if int(session)==1:eligible&=(minute>=570)&(minute<690)
            elif int(session)==2:eligible&=(minute>=570)&(minute<870)
            elif int(session)==3:eligible&=(minute>=600)&(minute<960)
            elif int(session)==4:eligible&=(minute>=480)&(minute<960)
            elif int(session)==5:eligible&=(minute>=660)&(minute<900)
            side[eligible]=raw_side[eligible]
            stop[eligible]=raw_stop[eligible]
            target[eligible]=new_tp[eligible]
            reason[eligible]='V3.7_'+family
            counts[family]=int(eligible.sum());added+=counts[family]
        retained=old_side!=0
        assert np.array_equal(side[retained],old_side[retained])
        assert np.array_equal(stop[retained],old_stop[retained],equal_nan=True)
        assert np.array_equal(target[retained],old_target[retained],equal_nan=True)
        assert np.array_equal(reason[retained],old_reason[retained])
        result['Position']=side;result['strategy_stop_loss']=stop
        result['strategy_target']=target;result['signal_reason']=reason
        result.attrs['strategy_diagnostics']={'version':V37_VERSION,'baseline':'V3.6',
          'mode':'ADD_NEW_WINNING_TRADES_ONLY','new_raw_entry_intents':added,
          'new_group_intents':counts,'old_signals_and_SLTP_preserved':True,
          'native_algoagentx_validated':False,'research_only':True}
        return result

    def generate(self):
        return self.apply_v37_additions(super().generate())

Strategy=NAS100V37AddOnly


# ==== V3.8 RESEARCH CANDIDATE — FILTER EXISTING V3.7 SIGNALS ONLY ====
# All source code above this line is byte-identical to accepted V3.7.
V38_VERSION = 'NAS100_M5_V3_8_FILTER_ONLY_RESEARCH_CANDIDATE'
V38_REJECTION_GROUPS = ((('adx', '<=', 12.933850288391113), ('volume_z', '<=', -0.8773056268692017)), (('stoch_raw', '<=', 2.876351833343506), ('range96_atr', '>=', 15.014636993408203), ('ema_spread_abs', '>=', 2.2666115760803223)))

class NAS100V38FilterOnly(NAS100V37AddOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        old_p = out['Position'].to_numpy(dtype=np.int8).copy()
        old_st = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(out, old_p, old_st)
        # On existing signals abs(EMA-spread/ATR) equals this directional magnitude.
        features['ema_spread_abs'] = np.abs(np.asarray(features['ema_spread_dir'], dtype=np.float32))
        reject = np.zeros(len(out), dtype=bool)
        for conjunction in V38_REJECTION_GROUPS:
            meets = np.ones(len(out), dtype=bool)
            for field, comparison, threshold in conjunction:
                values = np.asarray(features[field], dtype=np.float32)
                bound = np.float32(threshold)
                meets &= np.isfinite(values) & ((values <= bound) if comparison == '<=' else (values >= bound))
            reject |= meets
        reject &= (old_p != 0) & (np.arange(len(out)) >= self.LIVE_HISTORY_BARS)
        pos = old_p.copy(); stop = old_st.copy(); target = old_tp.copy(); reason = old_reason.copy()
        pos[reject] = 0; stop[reject] = np.nan; target[reject] = np.nan; reason[reject] = ''
        keep = ~reject
        assert not np.any((old_p == 0) & (pos != 0))
        assert np.array_equal(pos[keep], old_p[keep])
        assert np.array_equal(stop[keep], old_st[keep], equal_nan=True)
        assert np.array_equal(target[keep], old_tp[keep], equal_nan=True)
        assert np.array_equal(reason[keep], old_reason[keep])
        out['Position'] = pos; out['strategy_stop_loss'] = stop
        out['strategy_target'] = target; out['signal_reason'] = reason
        out.attrs['strategy_diagnostics'] = {
            'version':V38_VERSION,'baseline_version':'V3.7',
            'mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_existing_signal_intents':int(reject.sum()),
            'new_entry_intents':0, 'retained_entry_SL_TP_unchanged':True,
            'native_algoagentx_validated':False, 'untouched_out_of_sample':False,
            'research_only':True}
        return out

Strategy = NAS100V38FilterOnly


# === V3.9 RESEARCH ONLY: FILTER CURRENT V3.8 SIGNALS, NO NEW ENTRIES ===
# This suffix does not modify a single byte of the frozen V3.8 strategy above.
V39_VERSION = 'NAS100_M5_V3_9_FILTER_ONLY_RESEARCH_CANDIDATE'
V39_FILTER_GROUPS = ((('ema50_slope_48', '>=', 4.702386856079102), ('macd_dir', '<=', -0.3299252688884735)), (('body_atr', '>=', 2.315232753753662), ('stop_atr', '>=', 2.908172369003296), ('range96_atr', '<=', 5.106493949890137)))

class NAS100V39FilterOnly(NAS100V38FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        out = super().generate()
        original_p = out['Position'].to_numpy(dtype=np.int8).copy()
        original_sl = out['strategy_stop_loss'].to_numpy(dtype=float).copy()
        original_tp = out['strategy_target'].to_numpy(dtype=float).copy()
        original_reason = out['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(out, original_p, original_sl)
        rejected = np.zeros(len(original_p),dtype=bool)
        for group in V39_FILTER_GROUPS:
            condition = np.ones(len(original_p),dtype=bool)
            for name,operator,threshold in group:
                values = np.asarray(features[name],dtype=np.float32)
                cut = np.float32(threshold)
                condition &= np.isfinite(values) & ((values <= cut) if operator == '<=' else (values >= cut))
            rejected |= condition
        rejected &= (original_p!=0) & (np.arange(len(original_p)) >= self.LIVE_HISTORY_BARS)
        positions = original_p.copy();sl = original_sl.copy();tp = original_tp.copy();reasons = original_reason.copy()
        positions[rejected]=0;sl[rejected]=np.nan;tp[rejected]=np.nan;reasons[rejected]=''
        keep=~rejected
        assert not np.any((original_p==0)&(positions!=0))
        assert np.array_equal(positions[keep],original_p[keep])
        assert np.array_equal(sl[keep],original_sl[keep],equal_nan=True)
        assert np.array_equal(tp[keep],original_tp[keep],equal_nan=True)
        assert np.array_equal(reasons[keep],original_reason[keep])
        out['Position']=positions;out['strategy_stop_loss']=sl;out['strategy_target']=tp;out['signal_reason']=reasons
        out.attrs['strategy_diagnostics'] = {'version':V39_VERSION,'baseline_version':'V3.8',
             'mode':'FILTER_EXISTING_LOSING_TRADES_ONLY',
             'rejected_original_signals':int(rejected.sum()),'added_signals':0,
             'preserves_retained_SL_TP':True,'native_validated':False,
             'research_only':True,'untouched_oos':False}
        return out

Strategy = NAS100V39FilterOnly


# ===== V4_RESEARCH_VERSION ADD-ONLY OVERLAY =====
# The accepted V3.9 source above is byte-identical, unchanged.
# Uses the pre-existing causal _v27_bank and _v37_raw family functions.
# No candidate is native validated or live approved.
V4_VERSION_LABEL = 'V4.2'
V4_ALL_SELECTED_GROUPS = ((51, (0.11999999731779099, 0.7599999904632568, 0.800000011920929, 0.7200000286102295, 0.0, 60.0, 3.0, 1.0, 0.0)), (58, (0.11999999731779099, 0.5, 0.6000000238418579, 0.550000011920929, 18.0, 54.0, 1.0, 1.0, 0.0)), (52, (0.6000000238418579, 0.5, 0.800000011920929, 0.8999999761581421, 30.0, 54.0, 0.0, 1.0, 3.0)), (19, (0.2199999988079071, 0.8399999737739563, 1.0, 0.550000011920929, 18.0, 35.0, 1.0, 1.0, 0.0)), (30, (0.6000000238418579, 0.5, 1.0, 1.100000023841858, 18.0, 48.0, 3.0, 0.0, 4.0)), (57, (0.0, 0.5, 1.7999999523162842, 1.600000023841858, 18.0, 60.0, 0.0, 1.0, 1.0)), (45, (0.11999999731779099, 0.6800000071525574, 0.800000011920929, 1.100000023841858, 12.0, 0.0, 3.0, 0.0, 5.0)))

def _v4_apply_new_entries(result, groups, label):
    original_side=result['Position'].to_numpy(dtype=np.int8).copy()
    original_stop=result['strategy_stop_loss'].to_numpy(dtype=float).copy()
    original_target=result['strategy_target'].to_numpy(dtype=float).copy()
    original_reason=result['signal_reason'].fillna('').astype(str).to_numpy().copy()
    side=original_side.copy();stop=original_stop.copy();target=original_target.copy();reason=original_reason.copy()
    bank=_v27_bank(result)
    index=np.arange(len(side));added_counts={}
    for fi, cfg in groups:
        family=FAMILIES[fi]
        raw_side, raw_stop=_v37_raw(bank,family)
        new_tp=(bank['c']+raw_side*3*np.abs(bank['c']-raw_stop)).astype(np.float32)
        B,Q,RV,AR,ADX,RSI,trend,direction,session=cfg
        eligible=(raw_side!=0)&(original_side==0)&(side==0)
        eligible&=(index>=80000)&(index<len(side)-1)&(bank['dow']<5)&np.isfinite(raw_stop)
        quality=np.asarray(np.where(raw_side>0,bank['q'],bank['bearq']),dtype=np.float32)
        momentum=np.asarray(np.where(raw_side>0,bank['rsi'],100-bank['rsi']),dtype=np.float32)
        eligible&=(np.asarray(bank['body'],dtype=np.float32)>=np.float32(B))&(quality>=np.float32(Q))
        eligible&=(np.asarray(bank['rv'],dtype=np.float32)>=np.float32(RV))
        eligible&=(np.asarray(bank['ar'],dtype=np.float32)>=np.float32(AR))
        eligible&=(np.asarray(bank['adx'],dtype=np.float32)>=np.float32(ADX))&(momentum>=np.float32(RSI))
        if int(direction):eligible&=(raw_side==int(direction))
        if int(trend):
            h1=np.where(raw_side>0,bank['h1']['up'],bank['h1']['dn']).astype(bool)
            h4=np.where(raw_side>0,bank['h4']['up'],bank['h4']['dn']).astype(bool)
            if int(trend)==1:eligible&=h1
            elif int(trend)==2:eligible&=h4
            else:eligible&=h1&h4
        if int(session):
            mins=bank['minute']
            if int(session)==1:eligible&=(mins>=570)&(mins<690)
            elif int(session)==2:eligible&=(mins>=570)&(mins<870)
            elif int(session)==3:eligible&=(mins>=600)&(mins<960)
            elif int(session)==4:eligible&=(mins>=480)&(mins<960)
            elif int(session)==5:eligible&=(mins>=660)&(mins<900)
        side[eligible]=raw_side[eligible]
        stop[eligible]=raw_stop[eligible]
        target[eligible]=new_tp[eligible]
        reason[eligible]=label+'_'+family
        added_counts[family]=added_counts.get(family,0)+int(eligible.sum())
    retain=(original_side!=0)
    assert np.array_equal(side[retain],original_side[retain])
    assert np.array_equal(stop[retain],original_stop[retain],equal_nan=True)
    assert np.array_equal(target[retain],original_target[retain],equal_nan=True)
    assert np.array_equal(reason[retain],original_reason[retain])
    result['Position']=side;result['strategy_stop_loss']=stop
    result['strategy_target']=target;result['signal_reason']=reason
    result.attrs['strategy_diagnostics']={
       'version':label,'frozen_baseline':'V3.9',
       'mode':'ADD_NEW_WINNING_TRADES_ONLY',
       'added_raw_signals':int(sum(added_counts.values())),'family_intents':added_counts,
       'old_signals_stops_targets_unchanged':True,
       'native_algoagentx_validated':False,'research_only':True}
    return result

class NAS100VV42AddOnly(NAS100V39FilterOnly):
    LIVE_HISTORY_BARS=80000
    def generate(self):
        result=super().generate()
        return _v4_apply_new_entries(result,V4_ALL_SELECTED_GROUPS,V4_VERSION_LABEL)

Strategy=NAS100VV42AddOnly


# === V4.3 FILTER-ONLY RESEARCH CANDIDATE (frozen V4.2 above is unchanged) ===
V43_VERSION='NAS100_M5_V4_3_FILTER_ONLY_RESEARCH'
V43_GROUPS = ((('volume_z', '>=', 5.195839881896973), ('session', 'beforeNY', 0.0)), (('ema_spread_dir', '>=', 1.8579703569412231), ('ema50_100_dir', '>=', 1.7997304201126099), ('channel24_pos', '<=', -0.1266978681087494)))

class NAS100V43FilterOnly(NAS100VV42AddOnly):
    LIVE_HISTORY_BARS = 80000
    def generate(self):
        result = super().generate()
        baseline_p = result['Position'].to_numpy(dtype=np.int8).copy()
        baseline_sl = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        baseline_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        baseline_reasons = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        context = _v28_context(result, baseline_p, baseline_sl)
        reject = np.zeros(len(baseline_p),dtype=bool)
        for group in V43_GROUPS:
            group_reject = np.ones(len(baseline_p),dtype=bool)
            for name,operator,threshold in group:
                if name == 'session':
                    limits = {'beforeNY': (0,570), 'openNY': (570,690),
                              'midNY': (690,840), 'lateNY': (840,960), 'londonNY': (480,780)}
                    low,high=limits[operator]
                    values=np.asarray(context['minute_ny'],dtype=np.float32)
                    group_reject &= (values>=low)&(values<high)
                elif name == 'weekday':
                    values=np.asarray(context['day_of_week'],dtype=np.float32)
                    group_reject &= (values==np.float32(threshold))
                else:
                    values = np.asarray(context[name],dtype=np.float32)
                    level = np.float32(threshold)
                    group_reject &= np.isfinite(values)&((values<=level) if operator=='<=' else (values>=level))
            reject |= group_reject
        reject &= (baseline_p!=0) & (np.arange(len(baseline_p))>=self.LIVE_HISTORY_BARS)
        reject &= (np.arange(len(baseline_p)) < len(baseline_p)-1)
        out_p=baseline_p.copy();out_sl=baseline_sl.copy();out_tp=baseline_tp.copy();out_reasons=baseline_reasons.copy()
        out_p[reject]=0;out_sl[reject]=np.nan;out_tp[reject]=np.nan;out_reasons[reject]=''
        keep=~reject
        assert not np.any((baseline_p==0)&(out_p!=0))
        assert np.array_equal(out_p[keep],baseline_p[keep])
        assert np.array_equal(out_sl[keep],baseline_sl[keep],equal_nan=True)
        assert np.array_equal(out_tp[keep],baseline_tp[keep],equal_nan=True)
        assert np.array_equal(out_reasons[keep],baseline_reasons[keep])
        result['Position']=out_p;result['strategy_stop_loss']=out_sl
        result['strategy_target']=out_tp;result['signal_reason']=out_reasons
        result.attrs['strategy_diagnostics']={'version':V43_VERSION,'frozen_baseline':'V4.2',
            'mode':'FILTER_EXISTING_LOSING_TRADES_ONLY','rejected_original_signals':int(reject.sum()),
            'new_signals':0,'retained_SL_TP_unchanged':True,'research_only':True,
            'native_algoagentx_validated':False,'untouched_forward_test':False}
        return result

Strategy = NAS100V43FilterOnly


# === NAS100 V4.4 FILTER_EXISTING_LOSING_TRADES_ONLY (frozen V4.3 code above unchanged) ===
V44_VERSION = "NAS100_M5_V4_4_FILTER_ONLY_RESEARCH"
V44_GROUPS = ((('momentum_3', '>=', 3.6005771160125732), ('range96_atr', '<=', 4.92988395690918)), (('atr_rel', '>=', 4.198264122009277), ('momentum_3', '<=', -0.6920666098594666)))

class NAS100V44FilterOnly(NAS100V43FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        baseline_p = result['Position'].to_numpy(dtype=np.int8).copy()
        baseline_sl = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        baseline_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        baseline_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        context = _v28_context(result, baseline_p, baseline_sl)
        reject = np.zeros(len(baseline_p), dtype=bool)
        for group in V44_GROUPS:
            active = np.ones(len(baseline_p), dtype=bool)
            for feature, operator, cut in group:
                value = np.asarray(context[feature], dtype=np.float32)
                threshold = np.float32(cut)
                if operator == '<=':
                    active &= np.isfinite(value) & (value <= threshold)
                else:
                    active &= np.isfinite(value) & (value >= threshold)
            reject |= active
        reject &= (baseline_p != 0)
        reject &= (np.arange(len(baseline_p)) >= self.LIVE_HISTORY_BARS)
        reject &= (np.arange(len(baseline_p)) < len(baseline_p) - 1)
        output_p = baseline_p.copy()
        output_sl = baseline_sl.copy()
        output_tp = baseline_tp.copy()
        output_reason = baseline_reason.copy()
        output_p[reject] = 0
        output_sl[reject] = np.nan
        output_tp[reject] = np.nan
        output_reason[reject] = ''
        keep = ~reject
        assert not np.any((baseline_p == 0) & (output_p != 0))
        assert np.array_equal(output_p[keep], baseline_p[keep])
        assert np.array_equal(output_sl[keep], baseline_sl[keep], equal_nan=True)
        assert np.array_equal(output_tp[keep], baseline_tp[keep], equal_nan=True)
        assert np.array_equal(output_reason[keep], baseline_reason[keep])
        result['Position'] = output_p
        result['strategy_stop_loss'] = output_sl
        result['strategy_target'] = output_tp
        result['signal_reason'] = output_reason
        result.attrs['strategy_diagnostics'] = {
            'version': V44_VERSION,
            'frozen_baseline': 'V4.3',
            'research_mode': 'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_original_intents': int(reject.sum()),
            'new_raw_signals': 0,
            'retained_signals_SL_TP_unchanged': True,
            'native_algoagentx_replays': 0,
            'untouched_out_of_sample_validated': False,
            'research_only': True,
        }
        return result

Strategy = NAS100V44FilterOnly


# === V4.5 FILTER_ONLY RESEARCH: frozen V4.4 source above is byte-identical ===
V45_VERSION = "NAS100_M5_V4_5_FILTER_ONLY_RESEARCH"
V45_GROUPS = ((('channel24_pos', '>=', 1.2337236404418945), ('stoch_direction', '>=', 99.47098541259766)), (('wick_with', '<=', 0.0012569708051159978), ('range96_atr', '<=', 4.959787368774414), ('lower_wick', '<=', 0.016091447323560715)))

class NAS100V45FilterOnly(NAS100V44FilterOnly):
    LIVE_HISTORY_BARS = 80000
    def generate(self):
        result = super().generate()
        initial_p = result['Position'].to_numpy(dtype=np.int8).copy()
        initial_stop = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        initial_target = result['strategy_target'].to_numpy(dtype=float).copy()
        initial_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(result, initial_p, initial_stop)
        rejection = np.zeros(len(initial_p), dtype=bool)
        for group in V45_GROUPS:
            active = np.ones(len(initial_p), dtype=bool)
            for feature, operator, threshold in group:
                value = np.asarray(features[feature], dtype=np.float32)
                cut = np.float32(threshold)
                if operator == '<=':
                    active &= np.isfinite(value) & (value <= cut)
                else:
                    active &= np.isfinite(value) & (value >= cut)
            rejection |= active
        index = np.arange(len(initial_p))
        rejection &= (initial_p != 0) & (index >= self.LIVE_HISTORY_BARS) & (index < len(initial_p)-1)
        output_p = initial_p.copy()
        output_stop = initial_stop.copy()
        output_target = initial_target.copy()
        output_reason = initial_reason.copy()
        output_p[rejection] = 0
        output_stop[rejection] = np.nan
        output_target[rejection] = np.nan
        output_reason[rejection] = ''
        keep = ~rejection
        assert not np.any((initial_p==0)&(output_p!=0))
        assert np.array_equal(output_p[keep],initial_p[keep])
        assert np.array_equal(output_stop[keep],initial_stop[keep],equal_nan=True)
        assert np.array_equal(output_target[keep],initial_target[keep],equal_nan=True)
        assert np.array_equal(output_reason[keep],initial_reason[keep])
        result['Position'] = output_p
        result['strategy_stop_loss'] = output_stop
        result['strategy_target'] = output_target
        result['signal_reason'] = output_reason
        result.attrs['strategy_diagnostics'] = {
            'version': V45_VERSION,
            'frozen_baseline': 'V4.4',
            'research_mode': 'FILTER_EXISTING_LOSING_TRADES_ONLY',
            'rejected_baseline_intents': int(rejection.sum()),
            'new_signal_intents': 0,
            'native_algoagentx_replays': 0,
            'full_native_validation_pending': True,
            'untouched_out_of_sample_validated': False,
            'research_only': True,
        }
        return result

Strategy = NAS100V45FilterOnly


# ===== V4.6 FILTER-ONLY RESEARCH — FROZEN V4.5 SOURCE ABOVE UNCHANGED =====
V46_VERSION = 'NAS100_M5_V4_6_FILTER_ONLY_RESEARCH'
V46_GROUPS = ((('stop_atr', '>=', 3.367453098297119), ('channel24_pos', '>=', 1.0674799680709839), ('weekday', '==', 0.0)), (('momentum_48', '>=', 5.5829267501831055), ('vwap_gap_dir', '>=', 4.73580265045166), ('session', 'pre_open', 0.0)))

class NAS100V46FilterOnly(NAS100V45FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        old_p = result['Position'].to_numpy(dtype=np.int8).copy()
        old_sl = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        context = _v28_context(result, old_p, old_sl)
        reject = np.zeros(len(old_p), dtype=bool)
        session_ranges = {'pre_open': (0,570), 'ny_open': (570,690),
                          'ny_mid': (690,840), 'ny_late': (840,960),
                          'london': (480,780), 'ny_lunch': (720,840),
                          'afterhours': (960,1440)}
        for group in V46_GROUPS:
            active = np.ones(len(old_p), dtype=bool)
            for feature, operator, threshold in group:
                if feature == 'session':
                    low, high = session_ranges[operator]
                    value = np.asarray(context['minute_ny'], dtype=np.float32)
                    active &= (value >= low) & (value < high)
                elif feature == 'weekday':
                    value = np.asarray(context['day_of_week'], dtype=np.float32)
                    active &= value == np.float32(threshold)
                else:
                    value = np.asarray(context[feature], dtype=np.float32)
                    cut = np.float32(threshold)
                    active &= np.isfinite(value) & ((value <= cut) if operator == '<=' else (value >= cut))
            reject |= active
        idx = np.arange(len(old_p))
        reject &= (old_p != 0) & (idx >= self.LIVE_HISTORY_BARS) & (idx < len(old_p)-1)
        new_p = old_p.copy(); new_sl = old_sl.copy(); new_tp = old_tp.copy()
        new_reason = old_reason.copy()
        new_p[reject] = 0; new_sl[reject] = np.nan; new_tp[reject] = np.nan
        new_reason[reject] = ''
        keep = ~reject
        assert not np.any((old_p == 0) & (new_p != 0))
        assert np.array_equal(new_p[keep], old_p[keep])
        assert np.array_equal(new_sl[keep], old_sl[keep], equal_nan=True)
        assert np.array_equal(new_tp[keep], old_tp[keep], equal_nan=True)
        assert np.array_equal(new_reason[keep], old_reason[keep])
        result['Position'] = new_p
        result['strategy_stop_loss'] = new_sl
        result['strategy_target'] = new_tp
        result['signal_reason'] = new_reason
        result.attrs['strategy_diagnostics'] = dict(
            version=V46_VERSION, frozen_baseline='V4.5',
            mode='FILTER_EXISTING_LOSING_TRADES_ONLY',
            rejected_existing_signal_intents=int(reject.sum()),
            new_signals=0, retained_SL_TP_unchanged=True,
            native_algoagentx_replays=0, research_only=True,
            untouched_out_of_sample_validated=False)
        return result

Strategy = NAS100V46FilterOnly


# ===== V4.7 EXPERIMENTAL FILTER-ONLY OVERLAY. FROZEN V4.6 CODE ABOVE UNCHANGED =====
V47_VERSION = 'NAS100_M5_V4_7_FILTER_ONLY_RESEARCH'
V47_GROUPS = ((('stoch_raw', '>=', 94.34354400634766), ('momentum_12', '>=', 3.953228712081909), ('channel24_pos', '>=', 1.2728482484817505)), (('momentum_3', '>=', 2.1793887615203857), ('channel96_pos', '>=', 1.1552002429962158), ('weekday', '==', 1.0)))

class NAS100V47FilterOnly(NAS100V46FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        old_p = result['Position'].to_numpy(dtype=np.int8).copy()
        old_sl = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        old_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        old_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(result, old_p, old_sl)
        rejection = np.zeros(len(old_p), dtype=bool)
        for group in V47_GROUPS:
            active = np.ones(len(old_p), dtype=bool)
            for feature, operator, threshold in group:
                if feature == 'weekday':
                    values = np.asarray(features['day_of_week'], dtype=np.float32)
                    active &= np.isfinite(values) & (values == np.float32(threshold))
                else:
                    values = np.asarray(features[feature], dtype=np.float32)
                    cut = np.float32(threshold)
                    if operator == '<=':
                        active &= np.isfinite(values) & (values <= cut)
                    else:
                        active &= np.isfinite(values) & (values >= cut)
            rejection |= active
        idx = np.arange(len(old_p))
        rejection &= (old_p != 0) & (idx >= self.LIVE_HISTORY_BARS) & (idx < len(old_p)-1)
        new_p = old_p.copy(); new_sl = old_sl.copy(); new_tp = old_tp.copy()
        new_reason = old_reason.copy()
        new_p[rejection] = 0; new_sl[rejection] = np.nan; new_tp[rejection] = np.nan
        new_reason[rejection] = ''
        keep = ~rejection
        assert not np.any((old_p == 0) & (new_p != 0))
        assert np.array_equal(new_p[keep], old_p[keep])
        assert np.array_equal(new_sl[keep], old_sl[keep], equal_nan=True)
        assert np.array_equal(new_tp[keep], old_tp[keep], equal_nan=True)
        assert np.array_equal(new_reason[keep], old_reason[keep])
        result['Position'] = new_p
        result['strategy_stop_loss'] = new_sl
        result['strategy_target'] = new_tp
        result['signal_reason'] = new_reason
        result.attrs['strategy_diagnostics'] = dict(
            version=V47_VERSION, comparison_baseline='V4.6',
            mode='FILTER_EXISTING_LOSING_TRADES_ONLY',
            rejected_existing_signal_intents=int(rejection.sum()), new_signals=0,
            native_algoagentx_replays=0, research_only=True,
            untouched_out_of_sample_validated=False)
        return result

Strategy = NAS100V47FilterOnly


# ===== V4.8 FILTER-ONLY EXPERIMENT, V4.7 BASELINE SOURCE ABOVE IS FROZEN =====
V48_VERSION = 'NAS100_M5_V4_8_FILTER_ONLY_RESEARCH'
V48_RULES = ((('lower_wick', '>=', 0.528242290019989), ('atr_slope_12', '<=', 0.8329852223396301)), (('adx', '<=', 14.343328475952148), ('lower_wick', '<=', 0.01900448650121689)))

class NAS100V48FilterOnly(NAS100V47FilterOnly):
    LIVE_HISTORY_BARS = 80000

    def generate(self):
        result = super().generate()
        original_signal = result['Position'].to_numpy(dtype=np.int8).copy()
        original_sl = result['strategy_stop_loss'].to_numpy(dtype=float).copy()
        original_tp = result['strategy_target'].to_numpy(dtype=float).copy()
        original_reason = result['signal_reason'].fillna('').astype(str).to_numpy().copy()
        features = _v28_context(result, original_signal, original_sl)
        veto = np.zeros(len(original_signal), dtype=bool)
        for group in V48_RULES:
            group_veto = np.ones(len(original_signal), dtype=bool)
            for feature, op, limit in group:
                values = np.asarray(features[feature], dtype=np.float32)
                bound = np.float32(limit)
                if op == '<=':
                    group_veto &= np.isfinite(values) & (values <= bound)
                elif op == '>=':
                    group_veto &= np.isfinite(values) & (values >= bound)
                else:
                    raise ValueError('Unsupported V4.8 operator')
            veto |= group_veto
        index = np.arange(len(original_signal))
        veto &= (original_signal != 0) & (index >= self.LIVE_HISTORY_BARS) & (index < len(original_signal)-1)
        p = original_signal.copy()
        sl = original_sl.copy()
        tp = original_tp.copy()
        why = original_reason.copy()
        p[veto] = 0
        sl[veto] = np.nan
        tp[veto] = np.nan
        why[veto] = ''
        keep = ~veto
        assert not np.any((original_signal == 0) & (p != 0))
        assert np.array_equal(p[keep], original_signal[keep])
        assert np.array_equal(sl[keep], original_sl[keep], equal_nan=True)
        assert np.array_equal(tp[keep], original_tp[keep], equal_nan=True)
        assert np.array_equal(why[keep], original_reason[keep])
        result['Position'] = p
        result['strategy_stop_loss'] = sl
        result['strategy_target'] = tp
        result['signal_reason'] = why
        result.attrs['strategy_diagnostics'] = dict(
            version=V48_VERSION, reference_strategy='V4.7',
            mode='FILTER_EXISTING_LOSING_TRADES_ONLY',
            rejected_existing_intents=int(veto.sum()),
            new_entry_intents=0, native_algoagentx_replays=0,
            research_only=True, untouched_out_of_sample_validated=False)
        return result

Strategy = NAS100V48FilterOnly
