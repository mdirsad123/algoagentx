from app.api.v1.admin_strategy_requests import (
    StrategyUpdateIn,
    _apply_payload_to_parameters,
    _duplicate_parameters,
)


class _StrategyStub:
    id = "source-id"
    name = "XAUUSD 5M Resistance Rejection V3.5"

    def __init__(self, parameters):
        self.parameters = parameters


def test_admin_save_auto_marks_source_as_dynamic_db():
    payload = StrategyUpdateIn(source_code="class Strategy:\n    def generate(self):\n        pass\n")
    params = _apply_payload_to_parameters({}, payload)
    assert params["engine_mode"] == "DYNAMIC_DB"
    assert params["source_code_sha256"]


def test_admin_nested_parameters_source_also_becomes_dynamic_db():
    payload = StrategyUpdateIn(parameters={"source_code": "class Strategy:\n    def generate(self):\n        pass\n"})
    params = _apply_payload_to_parameters({}, payload)
    assert params["engine_mode"] == "DYNAMIC_DB"
    assert params["source_code_sha256"]


def test_duplicate_preserves_dynamic_runtime_contract():
    source = _StrategyStub({"source_code": "class Strategy:\n    def generate(self):\n        pass\n"})
    params = _duplicate_parameters(source)
    assert params["engine_mode"] == "DYNAMIC_DB"
    assert params["source_code_sha256"]
    assert params["_workflow"] == {}
