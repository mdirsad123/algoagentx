"""Explicit registry services. Not wired into the live runner until queue cutover.

All writes belong to the caller's transaction. No source execution, broker calls,
internal commits, or implicit schema creation. One AsyncSession per task.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, BrokerProvider, Strategy, StrategyDeployment
from ...db.models.live_strategy_registry import LiveStrategyRevision, LiveStrategyRuntime
from ..dynamic_strategy_loader import extract_dynamic_strategy_params, load_dynamic_strategy_class, validate_dynamic_strategy_source
from .incremental_contract import ExecutionIdentity, IncrementalContractError, canonical_json, positive_int, source_digest, validate_native_class
from .universal_incremental import inspect_incremental_source


def conflict_insert(db: AsyncSession, model):
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(model)
    if dialect == "sqlite":
        # Used only by isolated transactional contract tests, not production.
        return sqlite_insert(model)
    raise IncrementalContractError(f"Unsupported registry database dialect: {dialect}")


def inspect_revision(source: str) -> tuple[dict, dict]:
    """Store dependencies and structural errors without importing strategy code."""
    report = inspect_incremental_source(source)
    report["sha256"] = source_digest(source)
    report["verification"] = "structural_only_not_signal_parity"
    dependencies = {}
    try:
        validate_dynamic_strategy_source(source)
        tree = ast.parse(source)
        # The dynamic loader exposes pd/np even when the source omits imports.
        roots = {"pandas", "numpy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
            # Conservative: inherited async protocol methods cannot be accepted.
            if isinstance(node, ast.AsyncFunctionDef) and node.name in (
                "generate", "initialize", "on_closed_bar", "snapshot", "restore"
            ):
                report["errors"].append(f"Unsupported async protocol method: {node.name}")
        for root in sorted(roots):
            if root in {"pandas", "numpy"}:
                try:
                    dependencies[root] = package_version(root)
                except PackageNotFoundError:
                    report["errors"].append(f"Dependency unavailable: {root}")
            else:
                dependencies[root] = "stdlib_or_validated_base"
    except (ValueError, SyntaxError) as exc:
        report["errors"].append(str(exc))
    report["compatible"] = not report["errors"]
    report["interface_version"] = 1 if report["compatible"] else None
    return report, dependencies


async def register_revision(db: AsyncSession, *, strategy_id: str, source: str,
                            version: str) -> LiveStrategyRevision:
    if not isinstance(version, str) or not version.strip() or len(version) > 128:
        raise IncrementalContractError("Strategy version must contain 1 to 128 characters")
    digest = source_digest(source)
    report, dependencies = inspect_revision(source)
    await db.execute(conflict_insert(db, LiveStrategyRevision).values(
        id=uuid4(), strategy_id=strategy_id, version=version, source_code=source,
        source_sha256=digest, entrypoint=report.get("entrypoint"),
        interface_version=report.get("interface_version"),
        contract_status="declared" if report["compatible"] else "unsupported",
        contract_report=report, dependencies=dependencies,
    ).on_conflict_do_nothing(index_elements=["strategy_id", "source_sha256", "version"]))
    revision = (await db.execute(select(LiveStrategyRevision).where(
        LiveStrategyRevision.strategy_id == strategy_id,
        LiveStrategyRevision.source_sha256 == digest,
        LiveStrategyRevision.version == version,
    ))).scalar_one()
    if revision.source_code != source:
        raise IncrementalContractError("Registered source integrity mismatch")
    return revision


async def load_registered_class(db: AsyncSession, identity: ExecutionIdentity) -> type:
    """Worker-only source loading; this does NOT authorize orders or prove parity.

    Call only in an isolated compute process, never inside an HTTP request or a
    dispatcher. The existing loader's restrictions are retained, not weakened.
    """
    revision = (await db.execute(select(LiveStrategyRevision).where(
        LiveStrategyRevision.id == UUID(identity.revision_id))
        .execution_options(populate_existing=True))).scalar_one_or_none()
    if revision is None or revision.contract_status != "declared":
        raise IncrementalContractError("Registered source lacks the native contract")
    if source_digest(revision.source_code) != identity.source_sha256 or revision.source_sha256 != identity.source_sha256:
        raise IncrementalContractError("Registered source SHA mismatch")
    report, dependencies = inspect_revision(revision.source_code)
    if not report["compatible"] or dependencies != revision.dependencies:
        raise IncrementalContractError("Source dependencies or contract changed; revalidation required")
    strategy_class = load_dynamic_strategy_class(revision.source_code)
    if validate_native_class(strategy_class) != identity.state_schema_version:
        raise IncrementalContractError("Declared state schema does not match runtime binding")
    return strategy_class


@dataclass(frozen=True)
class RegisteredDeployment:
    identity: ExecutionIdentity
    generation: int
    status: str
    reason: str


async def bind_deployment(db: AsyncSession, deployment_id: UUID, *, runtime_config: dict,
                          warmup_bars: int, state_schema_version: int = 1) -> RegisteredDeployment:
    """Snapshot DB identity plus the existing runtime resolver's effective inputs.

    The caller must supply that resolver's unmodified runtime_config. No equity,
    sizing, instrument or broker defaults are guessed by this service. Binding is
    not permission to submit orders; structural compatibility remains unverified.
    """
    positive_int(warmup_bars, "warmup bars")
    positive_int(state_schema_version, "state schema version")
    if type(runtime_config) is not dict:
        raise IncrementalContractError("Resolved runtime configuration must be a JSON object")
    canonical_json(runtime_config)
    d, s = StrategyDeployment.__table__, Strategy.__table__
    row = (await db.execute(select(
        d.c.id, d.c.strategy_id, d.c.instrument, d.c.instrument_key,
        d.c.broker_symbol, d.c.timeframe, d.c.broker_account_id, d.c.mode,
        s.c.parameters, s.c.config_version,
    ).join(s, s.c.id == d.c.strategy_id).where(d.c.id == deployment_id)
        .with_for_update(of=[d, s]))).mappings().one_or_none()
    if row is None:
        raise IncrementalContractError("Deployment or strategy does not exist")
    parameters = row["parameters"] or {}
    if not isinstance(parameters, dict):
        raise IncrementalContractError("Database strategy parameters must be an object")
    source = parameters.get("source_code")
    digest = source_digest(source)
    version = str(parameters.get("strategy_version") or parameters.get("version")
                  or f"config-{row['config_version']}-{digest[:16]}")
    revision = await register_revision(db, strategy_id=row["strategy_id"], source=source, version=version)
    current_report, current_dependencies = inspect_revision(source)
    broker_code = None
    if row["broker_account_id"] is not None:
        b, p = BrokerAccount.__table__, BrokerProvider.__table__
        broker_code = (await db.execute(select(func.coalesce(p.c.code, b.c.broker_code, b.c.broker_name))
            .select_from(b.outerjoin(p, p.c.id == b.c.broker_provider_id))
            .where(b.c.id == row["broker_account_id"]))).scalar_one_or_none()
    configuration = {
        "parameters": extract_dynamic_strategy_params(parameters),
        # Also retain all parameter metadata: conservative invalidation until
        # strategy-specific independence has been explicitly demonstrated.
        "parameter_metadata": {key: value for key, value in parameters.items() if key != "source_code"},
        "runtime": runtime_config, "warmup_bars": warmup_bars,
        "instrument": row["instrument"], "instrument_key": row["instrument_key"],
        "broker_symbol": row["broker_symbol"], "timeframe": row["timeframe"],
        "broker_account_id": str(row["broker_account_id"]) if row["broker_account_id"] else None,
        "broker": str(broker_code).upper().strip() if broker_code else None,
        "mode": row["mode"], "dependencies": current_dependencies,
    }
    identity = ExecutionIdentity(str(deployment_id), str(revision.id), digest,
                                 canonical_json(configuration), state_schema_version)
    unsupported = revision.contract_status != "declared" or not current_report["compatible"]
    dependencies_changed = current_dependencies != revision.dependencies
    missing_broker = row["mode"] in {"DEMO", "LIVE"} and not broker_code
    status = "blocked" if unsupported or missing_broker or dependencies_changed else "pending"
    reason = ("unsupported_source" if unsupported else "dependency_environment_changed" if dependencies_changed
              else "broker_not_resolved" if missing_broker else "compatibility_verification_required")
    await db.execute(conflict_insert(db, LiveStrategyRuntime).values(
        deployment_id=deployment_id, revision_id=revision.id, fingerprint=identity.fingerprint,
        configuration=json.loads(identity.configuration_json), state_schema_version=state_schema_version,
        generation=1, checkpoint_sequence=0, status=status, reason=reason,
    ).on_conflict_do_nothing(index_elements=["deployment_id"]))
    runtime = (await db.execute(select(LiveStrategyRuntime).where(
        LiveStrategyRuntime.deployment_id == deployment_id).with_for_update()
        .execution_options(populate_existing=True))).scalar_one()
    if runtime.fingerprint != identity.fingerprint:
        runtime.revision_id = revision.id
        runtime.fingerprint = identity.fingerprint
        runtime.configuration = json.loads(identity.configuration_json)
        runtime.state_schema_version = state_schema_version
        runtime.generation += 1
        runtime.checkpoint_sequence = 0
        runtime.candle_open = None
        runtime.status, runtime.reason = status, reason
        runtime.updated_at = func.now()
        await db.flush()
    return RegisteredDeployment(identity, runtime.generation, runtime.status, runtime.reason)