"""Read-only Gold V9.32/V9.33 source/adapter diagnostic. Never submits orders.

Docker examples (run from project root):
  docker compose --env-file .env.prod exec api python -m app.tools.diagnose_xauusd_incremental --deployment-id UUID
  docker compose --env-file .env.prod exec api python -m app.tools.diagnose_xauusd_incremental --deployment-id UUID --export-source /tmp/gold_deployed_source.py
  docker compose --env-file .env.prod cp api:/tmp/gold_deployed_source.py ./gold_deployed_source.py

Offline: python -m app.tools.diagnose_xauusd_incremental --source-file strategies/v932_original_db_source.py
The export is exclusive-create, mode 0600, and must be explicitly requested.
"""
from __future__ import annotations

import argparse
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.services.live.incremental_adapter_registry import select_registered_adapter, v932_demo_forward_test_orders_permitted
from app.services.live.v932_hybrid_gate import V932_NORMALIZED_SHA256
from app.services.live.v933_causal_gate import matches_v933_causal_source

from strategies import v932_original_db_source

ORIGINAL = Path(v932_original_db_source.__file__)


def digest(s: str) -> str:
    return sha256(s.encode('utf-8')).hexdigest() if s else ''


def resolve_gold_history(source: str, parameters: dict) -> int | None:
    """Resolve the runner profile only for pinned code, never execute DB text."""
    from app.services.live.strategy_history_profile import resolve_live_strategy_profile
    if matches_v933_causal_source(source):
        from strategies.v933_causal_gold_source import Strategy as strategy_class
    elif source and digest(source.strip()) == V932_NORMALIZED_SHA256:
        from strategies.v932_original_db_source import Strategy as strategy_class
    else:
        return None
    return resolve_live_strategy_profile(strategy_class, parameters).required_history_bars


def inspect_source(source: str, *, mode: str, instrument: str,
                   timeframe_seconds: int, history_bars: int,
                   strategy_name: str | None = None) -> dict:
    bundled = ORIGINAL.read_text(encoding='utf-8')
    exact = bool(source) and source == bundled
    normalized = bool(source) and digest(source.strip()) == V932_NORMALIZED_SHA256
    causal_research = matches_v933_causal_source(source)
    selection = select_registered_adapter(
        settings=settings, source_code=source, mode=mode, instrument=instrument,
        timeframe_seconds=timeframe_seconds, required_history_bars=history_bars,
    )
    v932_demo_orders = v932_demo_forward_test_orders_permitted(
        source_code=source, mode=mode, selection=selection,
    )
    return {
        'strategy_name': strategy_name,
        'instrument': instrument,
        'mode': mode,
        'timeframe_seconds': timeframe_seconds,
        'history_bars': history_bars,
        'source_version': 'V9.33' if causal_research else 'V9.32' if normalized else 'UNRECOGNIZED',
        'manual_env_sha_required': False,
        'source_sha256': digest(source),
        'bundled_original_sha256': digest(bundled),
        'normalized_source_sha256': digest(source.strip()) if source else '',
        'source_byte_identical': exact,
        'source_normalized_identical': normalized,
        'v933_causal_research_source_recognized': causal_research,
        'registered_adapter': selection.adapter_id,
        'selection_reason': selection.reason,
        'incremental_selected': selection.strategy_class is not None,
        'adapter_order_monitor_only': selection.monitor_only,
        'gold_specific_monitor_flag_required': False,
        'global_adapter_monitor_only': bool(settings.live_incremental_monitor_only),
        'native_incremental_compatible': False,
        'native_persistent_state_available': False,
        'native_acceptance_status': 'BLOCKED_SOURCE_CAUSALITY' if causal_research else 'NOT_APPROVED',
        'gold_auto_orders_permitted': v932_demo_orders,
        'explanation': (
            'V9.33 research remains DEMO monitor-only. Future-candle '
            'dependencies in V99/V912/V915/V916 are unresolved; broker orders '
            'are not authorized by this adapter.'
        ) if causal_research else (
            'V9.32 exact-source-pinned DEMO hybrid: broker orders are enabled '
            'for forward testing when the single global monitor-only toggle is '
            'false and all runtime checks pass. This is NOT native incremental '
            'or historical signal parity approval; known historical-vs-right-edge '
            'BUY mismatch remains.'
            if v932_demo_orders
            else 'V9.32 DEMO hybrid is monitoring signals only; broker orders '
            'are suppressed. Known historical-vs-right-edge mismatch remains.'
        ) if normalized else 'Unrecognized source: no Gold compatibility or execution approval.',
        'action_if_source_mismatch': (
            'Export the exact deployed DB source with --export-source and '
            'compare privately; never replace the DB source from a similar filename.'
        ) if not (normalized or causal_research) else None,
    }


def secure_export(source: str, path: Path) -> None:
    """Exclusive-create private local file; never stdout, no DB mutation."""
    if not source:
        raise ValueError('Cannot export empty source')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(source.encode('utf-8'))
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


async def read_deployed(deployment_id: UUID) -> tuple[dict, str]:
    # Deferred imports so offline source checks work without a database driver.
    from sqlalchemy import select, text
    from app.db.models import Strategy, StrategyDeployment
    from app.db.session import async_session
    async with async_session() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        row = (await db.execute(
            select(StrategyDeployment, Strategy.name, Strategy.parameters)
            .join(Strategy, Strategy.id == StrategyDeployment.strategy_id)
            .where(StrategyDeployment.id == deployment_id)
        )).first()
        if row is None:
            raise ValueError('Deployment not found')
        deployment, name, parameters = row
        p = parameters if isinstance(parameters, dict) else {}
        source = str(p.get('source_code') or '')
        tf = str(deployment.timeframe or '').upper().strip()
        detail = {
            'deployment_id': str(deployment.id),
            'strategy_name': name,
            'instrument': str(deployment.instrument),
            'broker_symbol': str(getattr(deployment, 'broker_symbol', '') or ''),
            'timeframe': tf,
            'timeframe_seconds': 300 if tf in {'M5', '5M'} else -1,
            'mode': str(deployment.mode or '').upper(),
            'auto_trade_enabled': bool(deployment.auto_trade_enabled),
            'last_processed_candle_time': str(deployment.last_processed_candle_time),
            'resolved_history_bars': resolve_gold_history(source, p),
            'history_resolution': 'pinned_source_and_saved_parameters',
        }
        return detail, source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--deployment-id', type=UUID)
    group.add_argument('--source-file', type=Path)
    parser.add_argument('--export-source', type=Path)
    parser.add_argument('--output', type=Path, help='Write diagnostic JSON, never source or credentials')
    parser.add_argument('--history-bars', type=int, help='Hypothetical selection override, not deployed runtime proof')
    parser.add_argument('--instrument', default='XAUUSD.X', help='Offline source-file mode')
    parser.add_argument('--mode', default='DEMO', help='Offline source-file mode')
    parser.add_argument('--timeframe-seconds', type=int, default=300, help='Offline source-file mode')
    args = parser.parse_args()
    if args.history_bars is not None and args.history_bars < 1:
        parser.error('history-bars must be positive')
    if args.source_file:
        if args.export_source:
            parser.error('--export-source requires --deployment-id')
        source = args.source_file.read_text(encoding='utf-8')
        detail = {'source_file': str(args.source_file), 'instrument': args.instrument,
                  'mode': args.mode.upper(), 'timeframe_seconds': args.timeframe_seconds,
                  'resolved_history_bars': resolve_gold_history(source, {}),
                  'history_resolution': 'local_pinned_source_without_db_parameters'}
    else:
        detail, source = asyncio.run(read_deployed(args.deployment_id))
        if args.export_source:
            secure_export(source, args.export_source)
            detail['exported_to'] = str(args.export_source)
            detail['export_private_mode'] = '0600 (exclusive-create)'
    history_bars = args.history_bars if args.history_bars is not None else detail['resolved_history_bars']
    detail['selection_is_hypothetical'] = args.history_bars is not None
    # Unknown sources cannot gain eligibility by borrowing the default 80K.
    report = inspect_source(
        source, mode=detail['mode'], instrument=detail['instrument'],
        timeframe_seconds=detail['timeframe_seconds'], history_bars=history_bars or -1,
        strategy_name=detail.get('strategy_name'),
    )
    encoded = json.dumps({**detail, **report}, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')
    print(encoded)


if __name__ == '__main__':
    main()
