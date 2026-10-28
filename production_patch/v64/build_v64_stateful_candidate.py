"""Build an opt-in experimental V6.4 retained-state candidate from the tested optimized source.

No trading settings or server code are changed by this builder. The generated
strategy must pass full-vs-incremental parity before enabling in a deployment.
"""
from pathlib import Path
import sys, textwrap
src=Path(sys.argv[1]).read_text(encoding='utf8')
a=src.index('    def generate(self):\n        df = self.df.copy()', src.index('class XAUUSD5MSupplyDemandRejectionV35CandidateA'))
loop=src.index('        for i in range(len(df)):',a)
post=src.index('        diagnostics = {',loop)
body=src[loop+len('        for i in range(len(df)):\n'):post]
if '            if confirmed:' not in body: raise AssertionError('V35 loop mismatch')
# capture end-of-history state, exactly as computed by the frozen full generator
capture='''        self._live_v35_state = dict(df=df, zones=zones, active_short=active_short,
                                    active_long=active_long, resistance_sequence=resistance_sequence,
                                    support_sequence=support_sequence, setup_sequence=setup_sequence)
'''
src=src[:post]+capture+src[post:]
# one-candle method reuses original loop body verbatim (only indentation adjusted)
# ensure last i has own finalized ATR/HTF context, generated deterministically
single=textwrap.dedent(body) # remove 12 spaces from loop body; reindent 8 spaces
single=textwrap.indent(single,'        ')
method='''    def advance_live_v35(self, candle):
        """Append a closed candle to the exact V3.5 state after a full warmup.

        No source rules are changed: one-bar body is copied from the original
        historical loop. Expensive historical setup processing is not repeated.
        """
        st = self._live_v35_state
        if st is None:
            raise RuntimeError('V3.5 requires full historical warmup first')
        df = st['df']
        expected = ('Date','Open','High','Low','Close')
        row = {key: candle[key] for key in expected}
        if 'Volume' in df.columns:
            row['Volume'] = candle.get('Volume', 0)
        date = pd.Timestamp(row['Date'])
        if date <= pd.Timestamp(df.iloc[-1]['Date']):
            raise ValueError('Non-monotonic M5 candle')
        defaults = {'Position':0, 'strategy_stop_loss':pd.NA, 'strategy_target':pd.NA,
                    'signal_reason':pd.NA, 'rejection_reason':pd.NA, 'rr_setup_id':pd.NA,
                    'rr_zone_id':pd.NA, 'rr_state':'WAITING','rr_interaction':pd.NA,
                    'rr_direction':pd.NA,'rr_zone_low':pd.NA,'rr_zone_high':pd.NA,
                    'expansion_source':pd.NA,'same_day_loss_streak':0,
                    'cooldown_remaining':0,'monthly_entry_count':0,'daily_entry_count':0}
        row.update(defaults)
        row['Date'] = date
        new = pd.DataFrame([row])
        df = pd.concat([df, new], ignore_index=True)
        df['_rr_atr'] = self._atr(df)
        df = self._attach_15m_context(df, self._detected_source_timeframe_minutes)
        zones=st['zones']
        active_short=st['active_short']
        active_long=st['active_long']
        resistance_sequence=st['resistance_sequence']
        support_sequence=st['support_sequence']
        setup_sequence=st['setup_sequence']
        i=len(df)-1
'''+single+'''        st.update(df=df, zones=zones, active_short=active_short,
                  active_long=active_long, resistance_sequence=resistance_sequence,
                  support_sequence=support_sequence, setup_sequence=setup_sequence)
        self._live_v35_state = st
        return df.tail(1).copy()

'''
# fix wrong indentation: single body = 8 spaces okay after method's initial 8 spaces
start=src.index('    def generate(self):\n        df = self.df.copy()', src.index('class XAUUSD5MSupplyDemandRejectionV35CandidateA'))
src=src[:start]+method+src[start:]
# factor portfolio combining without changing existing calculations
parent=src.index('class AlgoAgentX_V62_NewEntries_RESEARCH_ONLY:')
start=src.index('    def generate(self):\n        raw = self.df.copy()',parent)
validate_begin=src.index("        hor = XAUUSD5MSupplyDemandRejectionV35CandidateA(raw).generate()",start)
validate_end=src.index('        def align(f):',validate_begin)
old_assign=src[validate_begin:validate_end]
if 'V431_RESEARCH_ONLY(raw).generate()' not in old_assign:raise RuntimeError('parent mismatch')
# parent _combine receives two generator outputs; old generate still constructs them in same order
src=src[:validate_begin]+'''        self._live_hor_engine = XAUUSD5MSupplyDemandRejectionV35CandidateA(raw)
        hor = self._live_hor_engine.generate()
        tr = V431_RESEARCH_ONLY(raw).generate()
        self._live_hor_history = hor
        self._live_trend_history = tr
        self._live_raw_history = raw
        return self._combine_live_sources(raw, hor, tr)

    def _combine_live_sources(self, raw, hor, tr):
'''+src[validate_end:]
# NOTE side effects to original generate: same source evaluations and outputs.
# experimental driver uses append and full vectorized trendline/gate while V3.5 incremental
last=src.rindex('Strategy = AlgoAgentX_V62_NewEntries_RESEARCH_ONLY')
parent_method='''    LIVE_INCREMENTAL_VERSION = 1

    def start_live_incremental(self, generated):
        """Retain the V3.5 zone/setup controller and current source histories."""
        if not isinstance(generated, pd.DataFrame) or generated.empty:
            return False
        if self._live_hor_engine is None:
            return False
        return bool(self._live_hor_engine._live_v35_state)

    def on_closed_candle(self, candle):
        """Update V3.5 state once; replay trendline and portfolio gate for parity.

        This is a hybrid incremental adapter, not a fully O(1) gate. It must be
        benchmarked and verified against the original 80K rolling baseline.
        """
        if not self._live_hor_engine:
            raise RuntimeError('Missing warmed strategy state')
        c = dict(candle)
        for k in ('Open','High','Low','Close'):
            c[k] = float(c[k])
        c['Date'] = pd.Timestamp(c['Date'])
        if 'Volume' not in c:
            c['Volume'] = 0
        new_h = self._live_hor_engine.advance_live_v35(c)
        raw = pd.concat([self._live_raw_history, pd.DataFrame([c])], ignore_index=True)
        tr = V431_RESEARCH_ONLY(raw).generate()
        hor = pd.concat([self._live_hor_history, new_h], ignore_index=True)
        result = self._combine_live_sources(raw, hor, tr)
        self._live_raw_history = raw
        self._live_hor_history = hor
        self._live_trend_history = tr
        return result.tail(1).copy()

'''
src=src[:last]+parent_method+src[last:]
Path(sys.argv[2]).write_text(src,encoding='utf8')
print('Wrote hybrid candidate',sys.argv[2],len(src),'bytes')
