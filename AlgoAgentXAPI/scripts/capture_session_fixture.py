"""Extract the already captured broker calendar, not synthetic market data."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
data = json.loads((root / 'gold_session_diagnostic.txt').read_text(encoding='utf-8'))
target = root / 'AlgoAgentXAPI/tests/fixtures/gold_tradelocker_session.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(data['calendar'], indent=2) + '\n', encoding='utf-8')
print(target)