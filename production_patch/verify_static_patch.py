"""Read-only structural checks for the AlgoAgentX HTTP isolation patch.

Does not test actual trades, PostgreSQL, Celery, Redis, or the broker.
"""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'AlgoAgentXAPI' / 'app'
W = ROOT / 'AlgoAgentXApp'

def must(test, message):
    if not test:
        raise AssertionError(message)
    print('PASS:', message)

for f in (A/'api/v1/live_deployments.py', A/'tasks.py', A/'services/live/dry_test_jobs.py',
          A/'services/live/live_legacy_runner_worker.py', A/'services/live/auto_runner_service.py'):
    ast.parse(f.read_text(), filename=str(f))
    print('PASS: Python AST',f.relative_to(ROOT))

compose = (ROOT/'docker-compose.yml').read_text()
try:
    import yaml
    services = yaml.safe_load(compose)['services']
    must(services['api']['environment']['LIVE_LEGACY_RUNNER_ENABLED'] == 'false', 'API legacy runner disabled')
    must(services['live_legacy_runner_worker']['environment']['LIVE_LEGACY_RUNNER_ENABLED'] == 'true', 'dedicated legacy runner enabled')
    must('live_dry_test' in services['live_dry_test_worker']['command'], 'dry-test queue isolated')
except ImportError:
    must('LIVE_LEGACY_RUNNER_ENABLED: "false"' in compose, 'API legacy runner explicitly disabled')
    must('live_dry_test_worker:' in compose, 'dedicated dry-test worker configured')

route = (A/'api/v1/live_deployments.py').read_text()
must('result = await run_full_dry_test_for_deployment(db, deployment_id)' not in route, 'dry test no longer computes inside HTTP request')
must('job = await enqueue_dry_test(str(deployment_id))' in route, 'dry test enqueues')
must('await get_deployment_or_404(db, deployment_id, current_user)\n    result = await dry_test_status' in route, 'dry-test result access checks deployment authorization')
page = (W/'app/(user)/live-trading/[deploymentId]/page.tsx').read_text()
must('getFullDryTestJob(deploymentId, queued.job_id)' in page, 'UI polls async dry-test results')
must('pipeline_mode === "CTRADER_STREAM"' in page, 'legacy broker health not judged by cTrader feeds')
runner = (A/'services/live/strategy_runner.py').read_text()
must('async def run_full_dry_test_for_deployment' in runner, 'original dry-test runner retained')
print('Structural checks passed. Runtime and live/broker integration remain UNVERIFIED.')
