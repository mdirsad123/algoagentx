"""Local-only source audit: compile changed Python and identify baseline blockers."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True, encoding='utf-8')


changed = set(git('diff', '--name-only').splitlines())
changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
compiled = []
for name in sorted(changed):
    path = ROOT / name
    if path.suffix == '.py' and path.is_file():
        compile(path.read_bytes(), str(path), 'exec')
        compiled.append(name)
print('Changed/untracked Python compiled:', len(compiled))
for name in compiled:
    print('COMPILE_OK', str(ROOT / name))

baseline = git('show', 'HEAD:AlgoAgentXAPI/app/services/live/candle_catchup.py')
test = git('show', 'HEAD:AlgoAgentXAPI/tests/test_demo_observed_long_gap_20261028.py')
print('BASELINE missing observed_broker_gap_eligible:', 'def observed_broker_gap_eligible' not in baseline)
print('BASELINE test imports missing function:', 'import observed_broker_gap_eligible' in test)
page = git('show', 'HEAD:AlgoAgentXApp/app/(user)/live-trading/[deploymentId]/page.tsx')
print('BASELINE deployment callback uses bind:', 'getDeploymentPipelineHealthDirect.bind(null, deploymentId)' in page)
for name in sorted(changed):
    if any(marker in name.lower() for marker in ('incremental', 'v64', 'risk', 'sizing', 'warmup', 'candle_catchup')):
        print('REVIEW_STRATEGY_PATH', name)

for relative in ('AlgoAgentXAPI/app/services/live/execution_engine.py',
                 'AlgoAgentXAPI/app/services/live/broker_sync_service.py',
                 'AlgoAgentXAPI/app/services/brokers/tradelocker.py'):
    lines = (ROOT / relative).read_text(encoding='utf-8').splitlines()
    for index, line in enumerate(lines):
        if any(marker in line for marker in ('order_outcome_unknown', "'UNCERTAIN'", 'BROKER_POSITION_SYNC', 'modify_position_protection')):
            print('\nCONTEXT', str(ROOT / relative), index + 1)
            for text in lines[max(0, index - 3):index + 9]:
                print(text)