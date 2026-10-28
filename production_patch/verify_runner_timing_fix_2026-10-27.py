"""Offline checks for runner-timing release candidate.

These are syntax/structural/pure helper tests. They are not a substitute for
DB + Redis + TradeLocker end-to-end or V6.4 full-replay parity tests.
"""
from __future__ import annotations
import ast
import importlib.util
import io
import logging
from pathlib import Path
import zipfile
import yaml

root=Path(__file__).resolve().parents[1]
paths=[
'AlgoAgentXAPI/app/core/config.py',
'AlgoAgentXAPI/app/services/live/auto_runner_service.py',
'AlgoAgentXAPI/app/services/live/strategy_runner.py',
'AlgoAgentXAPI/app/services/live/runner_diagnostics.py',
]
for p in paths:
    source=(root/p).read_text()
    ast.parse(source,filename=p)
    print('PASS AST',p)

runner=(root/paths[2]).read_text()
sched=(root/paths[1]).read_text()
config=(root/paths[0]).read_text()
assert 'stage_clock.stop("strategy_generate", timer' in runner
assert 'stage_clock.stop("load_closed_candles", timer' in runner
assert 'stage_clock.stop("build_dataframe", timer' in runner
assert 'RUNNER_STALE_SIGNAL_BLOCKED' in runner
assert 'live_runner_stale_order_guard_enabled: bool = Field(default=False' in config
assert 'live_strategy_cprofile_enabled: bool = Field(default=False' in config
assert 'if not runner_result.get("success", False):' in sched
assert 'if str(runner_result.get("final_action") or "").upper() == "LOCK_SKIPPED":' in sched
assert 'RUNNER_CANDLE_GAP' in sched
# Guard against accidental logic mutation from a replace script.
assert '_run_strategy_generate(strategy_instance)' in runner
assert 'run_strategy_for_deployment(' in runner
assert 'try_deployment_xact_lock(db, deployment.id)' in runner

spec=importlib.util.spec_from_file_location('runner_diagnostics',(root/paths[3]))
module=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=module
spec.loader.exec_module(module)
stream=io.StringIO()
logger=logging.getLogger('runner_diagnostic_test')
logger.handlers.clear()
h=logging.StreamHandler(stream);logger.addHandler(h);logger.setLevel(logging.DEBUG)
clock=module.StageClock('test-deployment',logger)
timer=clock.start('strategy_generate')
clock.stop('strategy_generate',timer,bars=80000)
clock.summary()
assert 'RUNNER_STAGE_DONE' in stream.getvalue()
assert 'RUNNER_STAGE_SUMMARY' in stream.getvalue()
assert clock.stages['strategy_generate']>=0

def sample_run(instance):
    return instance+1
assert module.profile_generate(sample_run,4,logger,'test') == 5
assert 'RUNNER_CPROFILE' in stream.getvalue()

compose=yaml.safe_load((root/'docker-compose.yml').read_text())
assert compose['services']['api']['environment']['LIVE_LEGACY_RUNNER_ENABLED']=='false'
assert compose['services']['live_legacy_runner_worker']['environment']['LIVE_LEGACY_RUNNER_ENABLED']=='true'
assert 'live_tradelocker_candle_worker' in compose['services']
print('PASS static scheduler and safety contract')
print('PASS optional switches remain OFF by default')
print('PASS DB and broker tasks intentionally NOT RUN')
print('PASS V6.4 parity intentionally NOT CLAIMED')
