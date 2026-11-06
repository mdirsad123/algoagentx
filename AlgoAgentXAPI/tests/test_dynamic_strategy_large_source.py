"""Large-source regressions. Generated inputs are test fixtures, not market data."""
import ast
import asyncio
import builtins
import hashlib
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from app.services import dynamic_strategy_loader as loader


SOURCE = '''from .base_strategy import BaseStrategy
class Strategy(BaseStrategy):
    def __init__(self, df, stop_points=10.0):
        super().__init__(df)
        self.stop_points = stop_points

    def generate(self):
        out = self.df.copy()
        out["Position"] = 0
        out["strategy_stop_loss"] = float("nan")
        out["strategy_target"] = float("nan")
        out.loc[out.index[1], ["Position", "strategy_stop_loss", "strategy_target"]] = [1, 90.0, 120.0]
        out.loc[out.index[4], ["Position", "strategy_stop_loss", "strategy_target"]] = [-1, 105.0, 90.0]
        return out
'''


def large_source(size=300_000, character="x"):
    # Non-whitespace padding survives the editor's existing strip normalization.
    return SOURCE + "\n# " + character * size


@pytest.fixture(autouse=True)
def clear_loader_cache():
    loader._load_dynamic_strategy_class_cached.cache_clear()
    yield
    loader._load_dynamic_strategy_class_cached.cache_clear()


@pytest.fixture
def candles():
    return pd.DataFrame({
        "Date": pd.date_range("2026-09-28", periods=7),
        "Open": [100.] * 7,
        "High": [103., 103., 103., 103., 121., 101., 101.],
        "Low": [97., 97., 97., 97., 96., 98., 88.],
        "Close": [100., 100., 100., 100., 100., 100., 90.],
        "Volume": [1.] * 7,
    })


@pytest.mark.parametrize("size,character", [(250_001, "x"), (1_000_001, "x"), (300_000, "\u03bb")])
def test_large_source_validates_loads_and_generates_without_truncation(size, character, candles):
    source = large_source(size, character)
    # Trailing executable code also proves the complete source was loaded.
    source += "\nMARKER = 42\n"
    assert len(source) > 250_000
    assert loader.validate_dynamic_strategy_source(source) == {"ok": True, "classes": ["Strategy"]}
    cls = loader.load_dynamic_strategy_class(source)
    assert cls.generate.__globals__["MARKER"] == 42
    pd.testing.assert_frame_equal(cls(candles).generate(), loader.load_dynamic_strategy_class(SOURCE)(candles).generate())


def test_large_executable_ast_not_just_comments(candles):
    source = SOURCE + "\n" + "\n".join(f"constant_{i} = {i}" for i in range(16_000))
    assert len(source) > 250_000
    cls = loader.load_dynamic_strategy_class(source)
    assert cls.generate.__globals__["constant_15999"] == 15999
    pd.testing.assert_frame_equal(cls(candles).generate(), loader.load_dynamic_strategy_class(SOURCE)(candles).generate())


@pytest.mark.parametrize("suffix", [
    "import os", "import requests", "import json", "from pathlib import Path",
    "open('not-permitted')", "eval('1')", "x = Strategy.__dict__",
])
def test_large_source_still_rejects_unsafe_code_at_end(suffix):
    source = large_source() + "\n" + suffix
    with pytest.raises(loader.DynamicStrategySecurityError):
        loader.validate_dynamic_strategy_source(source)
    with pytest.raises(loader.DynamicStrategySecurityError):
        loader.load_dynamic_strategy_class(source)


def test_large_source_syntax_errors_are_not_hidden():
    with pytest.raises(loader.DynamicStrategyLoadError, match="Syntax check failed"):
        loader.load_dynamic_strategy_class(large_source() + "\nclass Broken(:")


def test_compile_reuses_validated_ast(monkeypatch):
    compiled = []

    def record_compile(tree, *args, **kwargs):
        compiled.append(tree)
        return builtins.compile(tree, *args, **kwargs)

    monkeypatch.setattr(loader, "compile", record_compile, raising=False)
    loader.load_dynamic_strategy_class(large_source())
    assert len(compiled) == 1
    assert isinstance(compiled[0], ast.Module)


def test_concurrent_cache_misses_load_once_and_restore_module(monkeypatch):
    calls = []
    original = loader._validated_strategy_ast

    def record_parse(source):
        calls.append(source)
        return original(source)

    monkeypatch.setattr(loader, "_validated_strategy_ast", record_parse)
    previous = sys.modules.get("dynamic_strategy")
    source = large_source()
    with ThreadPoolExecutor(max_workers=4) as pool:
        classes = list(pool.map(loader.load_dynamic_strategy_class, [source] * 8))
    assert all(cls is classes[0] for cls in classes)
    assert len(calls) == 1
    assert sys.modules.get("dynamic_strategy") is previous
    assert loader.load_dynamic_strategy_class(source + "\n# edited") is not classes[0]


@pytest.mark.parametrize("error", [MemoryError, RecursionError])
@pytest.mark.parametrize("operation", [loader.validate_dynamic_strategy_source, loader.load_dynamic_strategy_class])
def test_resource_errors_are_actionable_and_not_cached(monkeypatch, error, operation):
    original = loader._validated_strategy_ast

    def exhausted(source):
        raise error("test-only resource failure")

    monkeypatch.setattr(loader, "_validated_strategy_ast", exhausted)
    with pytest.raises(loader.DynamicStrategyLoadError, match="exhausted available memory"):
        operation(large_source())
    assert loader._load_dynamic_strategy_class_cached.cache_info().currsize == 0
    monkeypatch.setattr(loader, "_validated_strategy_ast", original)
    assert operation(large_source())


def test_module_memory_error_restores_registration(monkeypatch):
    previous = sys.modules.get("dynamic_strategy")

    def exhausted(*args):
        raise MemoryError("test-only module allocation failure")

    monkeypatch.setattr(loader, "exec", exhausted, raising=False)
    with pytest.raises(loader.DynamicStrategyLoadError, match="exhausted available memory"):
        loader.load_dynamic_strategy_class(large_source())
    assert sys.modules.get("dynamic_strategy") is previous
    assert loader._load_dynamic_strategy_class_cached.cache_info().currsize == 0


@pytest.mark.parametrize("payload_kind", ["create", "update", "nested"])
def test_admin_save_payload_and_serialization_preserve_large_source(payload_kind):
    from app.api.v1.admin_strategy_requests import (
        StrategyCreateIn, StrategyUpdateIn, _apply_payload_to_parameters, _duplicate_parameters,
    )

    source = large_source(character="\u03bb")
    if payload_kind == "create":
        payload = StrategyCreateIn.model_validate_json(json.dumps({"name": "Large regression", "source_code": source}))
    else:
        body = {"parameters": {"source_code": source}} if payload_kind == "nested" else {"source_code": source}
        payload = StrategyUpdateIn.model_validate_json(json.dumps(body))
    params = _apply_payload_to_parameters({}, payload)
    # JSON is the existing JSONB transport; no production database is modified.
    restored = json.loads(json.dumps(params))
    assert restored["source_code"] == source
    assert restored["engine_mode"] == "DYNAMIC_DB"
    assert restored["source_code_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    duplicated = _duplicate_parameters(SimpleNamespace(id="large", name="Large regression", parameters=restored))
    assert duplicated["source_code"] == source


@pytest.mark.parametrize("engine_mode", ["DYNAMIC_DB", None])
def test_backtest_service_loads_large_stored_source(engine_mode, candles):
    from app.services.backtest_service import BacktestService

    params = {"source_code": large_source(), "engine_mode": engine_mode, "strategy_params": {"stop_points": 7.}}
    strategy = SimpleNamespace(id="large", name="Large regression", parameters=params)
    db = SimpleNamespace(get=AsyncMock(return_value=strategy))
    stored, cls, kwargs, name = asyncio.run(BacktestService._get_strategy_details(db, "large"))
    assert stored is strategy
    assert name == strategy.name
    assert kwargs == {"stop_points": 7.}
    assert len(cls(candles, **kwargs).generate()) == len(candles)


def test_large_source_backtest_preserves_trades_sltp_and_warmup(candles):
    from engine.backtest_engine import BacktestParams, run_backtest_engine

    params = BacktestParams(
        initial_capital=5000., capital_risk_pct=0.01, use_strategy_sl_tp=True,
        report_start_date=date(2026, 10, 1),
        runtime_config={"execution": {"exit_on_opposite_signal": False}},
    )
    small = run_backtest_engine(candles, loader.load_dynamic_strategy_class(SOURCE), backtest_params=params)
    large = run_backtest_engine(candles, loader.load_dynamic_strategy_class(large_source()), backtest_params=params)
    assert large.total_trades == small.total_trades == 1
    assert large.trades == small.trades
    assert large.equity_curve == small.equity_curve
    assert large.final_capital == small.final_capital == pytest.approx(5100.)
    assert large.summary["carry_in_position_excluded"] is True


def test_large_source_dry_run_signal_path_matches_small_source(candles):
    from app.services.strategy_registry import resolve_strategy
    from app.services.live.strategy_runner import _run_strategy_generate
    from app.services.live.signal_contract import extract_latest_signal_payload

    outputs = []
    for source in (SOURCE, large_source()):
        cls, params, _ = resolve_strategy("large", "Large regression", {"source_code": source})
        # Exercise the dry-test/runner generation helper, never broker submission.
        generated = _run_strategy_generate(cls(candles.iloc[:5], **params))
        outputs.append(extract_latest_signal_payload(generated))
    assert outputs[0] == outputs[1]
    assert outputs[1]["signal_type"] == "SELL"
    assert outputs[1]["strategy_stop_loss"] == 105.
    assert outputs[1]["strategy_target"] == 90.


def test_large_source_support_does_not_remove_worker_resource_protections():
    from app.backtest_celery import backtest_app

    assert backtest_app.conf.worker_concurrency == 1
    assert backtest_app.conf.worker_max_tasks_per_child == 1
    assert backtest_app.conf.task_time_limit > 0
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    worker = compose.split("  backtest_worker:", 1)[1].split("  backtest_dispatcher:", 1)[0]
    for safeguard in ("mem_limit:", "memswap_limit:", "--max-memory-per-child=", '"-Q", "backtest"'):
        assert safeguard in worker
    dry_jobs = (root / "AlgoAgentXAPI/app/services/live/dry_test_jobs.py").read_text(encoding="utf-8")
    assert 'queue="live_dry_test"' in dry_jobs
    assert "no synchronous fallback" in dry_jobs