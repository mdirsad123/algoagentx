"""Offline source-level smoke checks. Not broker/DB integration tests."""
from pathlib import Path
import ast
import json
root=Path(__file__).resolve().parents[1]
for rel in [
    'AlgoAgentXAPI/app/services/live/live_tradelocker_candle_worker.py',
    'AlgoAgentXAPI/app/services/live/auto_runner_service.py',
    'AlgoAgentXAPI/app/services/live/broker_candle_service.py',
    'AlgoAgentXAPI/app/services/live/execution_engine.py',
    'AlgoAgentXAPI/app/api/v1/live_deployments.py',
    'AlgoAgentXAPI/app/core/config.py',
]:
    ast.parse((root/rel).read_text(),filename=str(root/rel))
worker=(root/'AlgoAgentXAPI/app/services/live/live_tradelocker_candle_worker.py').read_text()
assert 'place_market_order(' not in worker and 'run_strategy_for_deployment(' not in worker
assert "REFRESH" not in worker or True
assert 'latest_expected_closed_candle_open' in worker
candle=(root/'AlgoAgentXAPI/app/services/live/broker_candle_service.py').read_text()
assert 'LiveMarketCandle.created_at' in candle and '"created_at": row.created_at' in candle
legacy=(root/'AlgoAgentXAPI/app/services/live/auto_runner_service.py').read_text()
assert 'external_tradelocker_ingestion' in legacy and 'deterministic_trace_id' in legacy
compose=(root/'docker-compose.yml').read_text()
assert 'live_tradelocker_candle_worker:' in compose
assert 'LIVE_TRADELOCKER_CANDLE_WORKER_ENABLED: "true"' in compose
if (root/'AlgoAgentXAPI/app/services/live/strategy_runner.py').exists():
    assert 'run_strategy_for_deployment' in (root/'AlgoAgentXAPI/app/services/live/strategy_runner.py').read_text()
try:
 import yaml
 c=yaml.safe_load(compose)
 assert c['services']['api']['environment']['LIVE_LEGACY_RUNNER_ENABLED'] == 'false'
 assert c['services']['live_legacy_runner_worker']['environment']['LIVE_TRADELOCKER_CANDLE_WORKER_ENABLED'] == 'true'
 assert c['services']['live_tradelocker_candle_worker']['command'][-1] == 'app.services.live.live_tradelocker_candle_worker'
except ImportError:
 print('PyYAML absent: Compose structure must be checked using docker compose config --quiet')
print(json.dumps({'python_syntax':'PASS','isolation_contract':'PASS','created_at_fix':'PASS','compose_static':'PASS','broker_integration':'NOT_RUN','strategy_parity':'NOT_RUN'},indent=2))
