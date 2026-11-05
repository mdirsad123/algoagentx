"""Launch checks outside the tool's short command timeout; persist exit codes."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = ROOT / 'AlgoAgentXAPI'
APP = ROOT / 'AlgoAgentXApp'
jobs = {
    'focused': [str(API / '.venv/Scripts/python.exe'), str(API / 'scripts/run_copy_reliability_tests.py'),
                'tests/test_copy_execution_reliability.py', 'tests/test_ctrader_connection_routing.py',
                'tests/test_20261102_hotfix_isolated.py', 'tests/test_20261103_copy_followup_isolated.py',
                '-o', 'addopts=', '-q', '-ra'],
    'acceptance': [str(API / '.venv/Scripts/python.exe'), str(API / 'scripts/run_copy_reliability_tests.py'), 'tests/test_copy_shared_login_20261105.py', '-o', 'addopts=', '-q', '-ra'],
    'regression': [str(API / '.venv/Scripts/python.exe'), str(API / 'scripts/run_copy_reliability_tests.py')],
    'typescript': ['node', str(APP / 'node_modules/typescript/bin/tsc'), '--noEmit', '--incremental', 'false'],
}
regressions = sorted(p for p in (API / 'tests').glob('test_*.py') if any(
    word in p.name for word in ('copy_', 'ctrader_', 'tradelocker_', 'incremental_', 'v64_',
                               'retained_', 'runner_hotpath', 'generic_order', 'live_order',
                               'live_partial', 'pretrade_', '20261102', '20261103')))
jobs['targeted'] = [str(API / '.venv/Scripts/python.exe'), str(API / 'scripts/run_copy_reliability_tests.py'),
                    *map(str, regressions), '-o', 'addopts=', '-q', '-ra']
jobs['remaining'] = [str(API / '.venv/Scripts/python.exe'), str(API / 'scripts/run_copy_reliability_tests.py'),
                     'tests', '--ignore=tests/local_debug', '--ignore=tests/test_demo_observed_long_gap_20261028.py', '-o', 'addopts=', '-q', '-ra']
if len(sys.argv) > 1 and sys.argv[1] != 'launch':
    name = sys.argv[1]
    with (ROOT / f'artifacts/copy_{name}_final.txt').open('w') as out:
        result = subprocess.run(jobs[name], cwd=APP if name == 'typescript' else API, stdout=out, stderr=subprocess.STDOUT)
        out.write(f'\nEXIT_CODE={result.returncode}\n')
else:
    for name in (sys.argv[2:] if len(sys.argv) > 1 else ('targeted', 'remaining')):
        process = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), name],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        print(name, process.pid)