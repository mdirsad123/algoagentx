from __future__ import annotations

import ast
import builtins
import inspect
import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


class DynamicStrategySecurityError(ValueError):
    pass


class DynamicStrategyLoadError(ValueError):
    pass


BANNED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "requests", "urllib", "http", "ftplib",
    "shutil", "pathlib", "glob", "pickle", "marshal", "ctypes", "importlib", "builtins",
}

ALLOWED_IMPORT_ROOTS = {"pandas", "numpy", "math", "datetime", "statistics"}

BANNED_CALL_NAMES = {
    "open", "eval", "exec", "compile", "input", "help", "dir", "globals", "locals", "vars",
    "__import__", "getattr", "setattr", "delattr", "breakpoint", "memoryview",
}

BANNED_ATTR_NAMES = {
    "__dict__", "__class__", "__bases__", "__mro__", "__subclasses__", "__globals__",
    "__code__", "__closure__", "__getattribute__", "__setattr__", "__delattr__",
}

ALLOWED_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "object": object,
    "__build_class__": builtins.__build_class__,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
}


def _safe_import(name: str, globals: Any = None, locals: Any = None, fromlist: tuple[str, ...] = (), level: int = 0) -> Any:
    root = str(name).split(".", 1)[0]
    if root not in ALLOWED_IMPORT_ROOTS:
        raise ImportError(f"Import '{name}' is not allowed in strategy code")
    return builtins.__import__(name, globals, locals, fromlist, level)


class _StrategySafetyVisitor(ast.NodeVisitor):
    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root in BANNED_IMPORTS or root not in ALLOWED_IMPORT_ROOTS:
                raise DynamicStrategySecurityError(f"Import '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = node.module or ""
        root = module.split(".", 1)[0]
        if root in BANNED_IMPORTS or root not in ALLOWED_IMPORT_ROOTS:
            raise DynamicStrategySecurityError(f"Import from '{module}' is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        func = node.func
        if isinstance(func, ast.Name) and func.id in BANNED_CALL_NAMES:
            raise DynamicStrategySecurityError(f"Call to '{func.id}' is not allowed")
        if isinstance(func, ast.Attribute) and func.attr in BANNED_CALL_NAMES:
            raise DynamicStrategySecurityError(f"Call to '.{func.attr}' is not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if node.attr in BANNED_ATTR_NAMES or (node.attr.startswith("__") and node.attr.endswith("__")):
            raise DynamicStrategySecurityError(f"Access to attribute '{node.attr}' is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in BANNED_CALL_NAMES:
            raise DynamicStrategySecurityError(f"Use of '{node.id}' is not allowed")
        self.generic_visit(node)


def validate_dynamic_strategy_source(source_code: str) -> dict[str, Any]:
    source = (source_code or "").strip()
    if not source:
        raise DynamicStrategyLoadError("No strategy source code attached")
    if len(source) > 250_000:
        raise DynamicStrategySecurityError("Strategy source code is too large")

    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise DynamicStrategyLoadError(f"Syntax check failed: {exc}") from exc

    _StrategySafetyVisitor().visit(tree)
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    if not classes:
        raise DynamicStrategyLoadError("Strategy code must define a class with a generate(self) method")
    return {"ok": True, "classes": classes}


def _find_strategy_class(namespace: dict[str, Any]) -> type:
    preferred = namespace.get("Strategy")
    if inspect.isclass(preferred) and callable(getattr(preferred, "generate", None)):
        return preferred

    for value in namespace.values():
        if inspect.isclass(value) and callable(getattr(value, "generate", None)):
            return value
    raise DynamicStrategyLoadError("No executable strategy class found. Define class Strategy or any class with generate(self).")


def _filter_init_params(strategy_class: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        signature = inspect.signature(strategy_class.__init__)
    except (TypeError, ValueError):
        return dict(params)

    parameters = signature.parameters
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
        return dict(params)

    allowed = {
        name
        for name, param in parameters.items()
        if name not in {"self", "df"}
        and param.kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
    }
    return {key: value for key, value in params.items() if key in allowed}


_META_PARAM_KEYS = {
    "source_code", "strategy_type", "market", "timeframe", "entry_rules", "exit_rules",
    "confirmation_rules", "risk_rules", "invalidation_rules", "trade_management_rules", "notes",
    "performance_metrics", "runtime_config", "default_runtime_config", "runtime_config_schema", "engine_mode",
}


def extract_dynamic_strategy_params(parameters: dict[str, Any] | None) -> dict[str, Any]:
    params = parameters if isinstance(parameters, dict) else {}
    explicit = params.get("strategy_params")
    if isinstance(explicit, dict):
        return dict(explicit)

    result: dict[str, Any] = {}
    for key, value in params.items():
        if str(key).startswith("_") or key in _META_PARAM_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[str(key)] = value
    return result


def load_dynamic_strategy_class(source_code: str) -> type:
    validate_dynamic_strategy_source(source_code)
    safe_builtins = dict(ALLOWED_BUILTINS)
    safe_builtins["__import__"] = _safe_import
    namespace: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "__name__": "dynamic_strategy",
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "math": math,
    }
    code = compile(source_code, "<dynamic_strategy>", "exec")
    exec(code, namespace, namespace)
    return _find_strategy_class(namespace)


def build_dynamic_strategy_entry(
    strategy_id: str | None,
    strategy_name: str | None,
    db_parameters: dict[str, Any] | None,
) -> Tuple[Any, Dict[str, Any], str]:
    params = db_parameters if isinstance(db_parameters, dict) else {}
    source_code = str(params.get("source_code") or "")
    strategy_class = load_dynamic_strategy_class(source_code)
    strategy_params = _filter_init_params(strategy_class, extract_dynamic_strategy_params(params))
    canonical_name = strategy_name or strategy_id or getattr(strategy_class, "__name__", "Dynamic Strategy")
    return strategy_class, strategy_params, str(canonical_name)
