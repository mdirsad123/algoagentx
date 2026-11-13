"""DB-source native incremental contract; no per-strategy source hashes or adapters.

A class must expose generate(), initialize(history, context), on_closed_bar(bar),
snapshot(), restore(snapshot, context). generate() remains authoritative for
historical/backtest execution. initialize/on_closed_bar are author-written;
this module does NOT transcompile arbitrary Python batch algorithms.
"""
from __future__ import annotations

import ast
from hashlib import sha256
from typing import Any

import pandas as pd


PROTOCOL_METHODS = ("generate", "initialize", "on_closed_bar", "snapshot", "restore")


def inspect_incremental_source(source: str) -> dict[str, Any]:
    """Static inspection with actionable errors; does not execute untrusted source."""
    digest = sha256(source.strip().encode("utf-8")).hexdigest()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"compatible": False, "sha256": digest, "entrypoint": None,
                "errors": [f"Python syntax error at line {exc.lineno}: {exc.msg}"]}
    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}
    if not classes:
        return {"compatible": False, "sha256": digest, "entrypoint": None,
                "errors": ["Missing strategy class. Define class Strategy with the incremental methods."]}
    # Same explicit-entrypoint convention as dynamic_strategy_loader.
    preferred = classes.get("Strategy")
    if preferred is None:
        # AlgoAgentX research files commonly end with `Strategy = FinalVersion`.
        for node in reversed(tree.body):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "Strategy" for t in node.targets):
                if isinstance(node.value, ast.Name) and node.value.id in classes:
                    preferred = classes[node.value.id]
                break
    if preferred is None:
        candidates = [c for c in classes.values() if any(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == "generate" for x in c.body)]
        preferred = candidates[0] if len(candidates) == 1 else None
    if preferred is None:
        return {"compatible": False, "sha256": digest, "entrypoint": None,
                "errors": ["Ambiguous entrypoint. Name the executable class Strategy."]}
    # Inheritance from classes defined in the same pasted module is supported.
    def defined(cls: ast.ClassDef, seen: set[str]) -> dict:
        if cls.name in seen:
            return {}
        seen.add(cls.name)
        methods = {}
        for base in cls.bases:
            if isinstance(base, ast.Name) and base.id in classes:
                for name, method in defined(classes[base.id], seen).items():
                    methods.setdefault(name, method)
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods[node.name] = node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        methods.pop(target.id, None)
        return methods
    methods = defined(preferred, set())
    missing = [name for name in PROTOCOL_METHODS if name not in methods]
    async_methods = [name for name, node in methods.items() if name in PROTOCOL_METHODS and isinstance(node, ast.AsyncFunctionDef)]
    errors = (["Missing native incremental methods: " + ", ".join(missing) + ". "] if missing else [])
    if async_methods:
        errors.append("Native strategy methods must be synchronous: " + ", ".join(async_methods))
    arities = {"generate": 1, "initialize": 3, "on_closed_bar": 2, "snapshot": 1, "restore": 3}
    for name, arity in arities.items():
        node = methods.get(name)
        if node is None:
            continue
        if node.decorator_list:
            errors.append(f"{name} must be an undecorated instance method for static verification")
        args = node.args
        positional = args.posonlyargs + args.args
        required = len(positional) - len(args.defaults)
        if required > arity or (not args.vararg and len(positional) < arity) or any(default is None for default in args.kw_defaults):
            errors.append(f"{name} has an incompatible signature; expected {arity - 1} positional arguments after self")
        if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)):
            errors.append(f"{name} must return a value, not a generator")
    return {"compatible": not errors, "sha256": digest, "entrypoint": preferred.name,
            "interface_version": 1 if not errors else None, "errors": errors}


def make_incremental_strategy_class(base: type) -> type:
    """Bridge the public contract into the existing retained runner ABI.

    A fresh class is constructed only for source with the explicit protocol.
    All history computations remain in the strategy's own generate() method.
    """
    if not all(callable(getattr(base, method, None)) for method in PROTOCOL_METHODS):
        raise ValueError("Strategy lacks the native incremental interface")

    class NativeIncrementalBridge(base):
        LIVE_INCREMENTAL_VERSION = 1
        LIVE_INCREMENTAL_NATIVE = True
        LIVE_INCREMENTAL_STATE_SCHEMA_VERSION = getattr(base, "LIVE_INCREMENTAL_STATE_SCHEMA_VERSION", 1)

        def start_live_incremental(self, generated: pd.DataFrame) -> bool:
            if self.initialize(self.df.copy(), {"interface_version": 1, "generated": generated}) is False:
                raise ValueError('Native initialization rejected history')
            return True

        def on_closed_candle(self, candle: dict) -> pd.DataFrame:
            result = self.on_closed_bar(dict(candle))
            if result is None:
                result = {"Position": 0}
            if isinstance(result, pd.DataFrame):
                output = result.copy()
            elif isinstance(result, dict):
                output = pd.DataFrame([result])
            else:
                raise ValueError("on_closed_bar() must return a dict, DataFrame or None (HOLD)")
            if output.empty or len(output) != 1:
                raise ValueError("on_closed_bar() must return exactly one evaluated bar")
            if "Date" not in output:
                output["Date"] = candle["Date"]
            if "Position" not in output:
                raise ValueError("on_closed_bar() output requires Position: -1, 0, or 1")
            if output.iloc[0]["Position"] not in (-1, 0, 1):
                raise ValueError("Position must be -1, 0 or 1")
            for key in ("Open", "High", "Low", "Close", "Volume"):
                if key not in output and key in candle:
                    output[key] = candle[key]
            return output

    NativeIncrementalBridge.__name__ = base.__name__ + "_NativeIncremental"
    NativeIncrementalBridge.__module__ = base.__module__
    return NativeIncrementalBridge


def check_native_right_edge_parity(strategy_class: type, params: dict, candles: pd.DataFrame,
                                   *, steps: int = 3) -> dict[str, Any]:
    """Compare native streaming and freshly evaluated as-of-prefix outputs.

    This checks real right-edge behavior, never a historical result computed with
    future candles. It is a smoke test, not a multi-year statistical guarantee.
    """
    import json
    import math
    if len(candles) < steps + 2:
        raise ValueError("Insufficient candles for incremental right-edge comparison")
    base = candles.iloc[:-steps].copy().reset_index(drop=True)
    strategy = strategy_class(base, **params)
    generated = strategy.generate()
    if not isinstance(generated, pd.DataFrame) or generated.empty:
        raise ValueError("generate() must return a nonempty DataFrame")
    if strategy.start_live_incremental(generated) is not True:
        raise ValueError("initialize() failed to accept historical warmup")
    results = []
    pending_restored = None
    for i in range(steps):
        bar = candles.iloc[len(base) + i].to_dict()
        incremental = strategy.on_closed_candle(bar)
        fresh = strategy_class(candles.iloc[:len(base) + i + 1].copy(), **params).generate()
        if fresh.empty:
            raise ValueError("generate() produced no closed-candle output")
        actual = incremental.iloc[-1]
        expected = fresh.iloc[-1]
        if pending_restored is not None:
            for col in ("Position", "strategy_stop_loss", "strategy_target"):
                a, b = actual.get(col), pending_restored.iloc[-1].get(col)
                if pd.isna(a) and pd.isna(b):
                    continue
                if pd.isna(a) != pd.isna(b) or not math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-8):
                    raise ValueError(f"Restore parity mismatch at {bar['Date']}: {col}")
            if ("signal_reason" in actual) != ("signal_reason" in pending_restored):
                raise ValueError(f"Restore parity mismatch at {bar['Date']}: signal_reason field missing")
            if "signal_reason" in actual:
                restored_reason = pending_restored.iloc[-1]["signal_reason"]
                actual_reason = actual["signal_reason"]
                if ("" if pd.isna(actual_reason) else str(actual_reason)) != ("" if pd.isna(restored_reason) else str(restored_reason)):
                    raise ValueError(f"Restore parity mismatch at {bar['Date']}: signal_reason")
        for col in ("Position", "strategy_stop_loss", "strategy_target"):
            a, b = actual.get(col), expected.get(col)
            if col == "Position":
                if int(a or 0) != int(b or 0):
                    raise ValueError(f"Live right-edge mismatch at {bar['Date']}: {col} incremental={a}, history={b}")
            else:
                if pd.isna(a) and pd.isna(b):
                    continue
                if pd.isna(a) != pd.isna(b) or not math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-8):
                    raise ValueError(f"Live right-edge mismatch at {bar['Date']}: {col} incremental={a}, history={b}")
        # An omitted reason is not equivalent to a supplied FILTERED or HOLD
        # explanation. Compare field presence as well as the value.
        if ("signal_reason" in actual) != ("signal_reason" in expected):
            raise ValueError(f"Live right-edge mismatch at {bar['Date']}: signal_reason field missing")
        if "signal_reason" in actual:
            left = "" if pd.isna(actual["signal_reason"]) else str(actual["signal_reason"])
            right = "" if pd.isna(expected["signal_reason"]) else str(expected["signal_reason"])
            if left != right:
                raise ValueError(f"Live right-edge mismatch at {bar['Date']}: signal_reason incremental={left}, history={right}")
        state = strategy.snapshot()
        json.dumps(state, sort_keys=True, allow_nan=False)
        pending_restored = None
        if i < steps - 1:
            copy = strategy_class(candles.iloc[len(base) + i:len(base) + i + 1].copy(), **params)
            copy.restore(state, {"interface_version": 1, "restored": True})
            next_bar = candles.iloc[len(base) + i + 1].to_dict()
            pending_restored = copy.on_closed_candle(next_bar)
        results.append(str(bar["Date"]))
    return {"ok": True, "bars": results, "steps": len(results), "restore_checked": True}


async def verify_native_parity_from_market_data(db, *, strategy_class: type, params: dict,
                                                instrument_id: int, timeframe: str,
                                                warmup_bars: int) -> dict[str, Any]:
    """Independent real-candle parity smoke check; never part of Quick Verify.

    Uses the complete configured warmup, never generates fabricated candle data.
    This is a bounded local smoke check and should not be described as an
    exhaustive multi-year forward test.
    """
    from sqlalchemy import select
    from ...db.models.market_data import MarketData
    steps = 3
    needed = max(2, int(warmup_bars)) + steps
    tf = str(timeframe).upper().strip()
    variants = [tf]
    if tf in {"M5", "5M", "5MIN", "5MINUTE"}:
        variants = [tf] + [v for v in ("M5", "5M", "5MIN", "5MINUTE") if v != tf]
    elif tf in {"H1", "1H", "60M"}:
        variants = [tf] + [v for v in ("H1", "1H", "60M") if v != tf]
    rows = []
    # Never merge two timeframe aliases into one candle stream: some databases
    # contain both M5 and 5m snapshots for the same timestamps.
    for candidate in variants:
        current = (await db.execute(
            select(MarketData.timestamp, MarketData.open, MarketData.high,
                   MarketData.low, MarketData.close, MarketData.volume)
            .where(MarketData.instrument_id == instrument_id,
                   MarketData.timeframe == candidate)
            .order_by(MarketData.timestamp.desc()).limit(needed)
        )).all()
        if len(current) > len(rows):
            rows = current
        if len(rows) >= needed:
            break
    if len(rows) < needed:
        raise ValueError(f"Incremental parity requires {needed} stored {timeframe} candles; found {len(rows)}")
    frame = pd.DataFrame([{
        "Date": row.timestamp,
        "Open": float(row.open), "High": float(row.high),
        "Low": float(row.low), "Close": float(row.close),
        "Volume": float(row.volume or 0),
    } for row in reversed(rows)])
    return check_native_right_edge_parity(strategy_class, params, frame, steps=steps)
