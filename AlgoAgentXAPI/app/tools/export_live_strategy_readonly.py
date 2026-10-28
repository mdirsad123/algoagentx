"""Export exact deployed strategy source from PostgreSQL, read-only.

python -m app.tools.export_live_strategy_readonly --deployment-id <UUID> \\
  --out /tmp/active_strategy.py
Review source for secrets/private data before sharing. No broker or order actions.
"""
from __future__ import annotations
import argparse
import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from app.db.session import async_session
from app.db.models import Strategy, StrategyDeployment


async def export(deployment_id: UUID, output: Path):
    async with async_session() as db:
        row = (await db.execute(
            select(Strategy.name, Strategy.parameters).join(
                StrategyDeployment, StrategyDeployment.strategy_id == Strategy.id
            ).where(StrategyDeployment.id == deployment_id)
        )).first()
        if row is None:
            raise ValueError('Deployment/Strategy not found')
        strategy_name, parameters = row
        parameters = parameters if isinstance(parameters, dict) else {}
        source = parameters.get('source_code')
        if not isinstance(source, str) or not source.strip():
            raise ValueError('No DB-stored source_code for this deployment (static strategy)')
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError('Refusing to overwrite existing export')
        output.write_text(source, encoding='utf-8')
        print('strategy:', strategy_name)
        print('sha256:', sha256(source.encode('utf-8')).hexdigest())
        print('output:', output)
        print('parameters_keys:', sorted(k for k in parameters if k != 'source_code'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deployment-id', type=UUID, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(export(args.deployment_id, args.out))


if __name__ == '__main__':
    main()
