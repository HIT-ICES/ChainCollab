from pathlib import Path

from tools.extract_dsl_ir import parse_dsl


def test_parse_seed_dsl() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = parse_dsl(root / "cases" / "positive" / "business_rule_case.b2c")
    assert payload["contract"] == "BusinessRuleCase"
    assert any(item["name"] == "RuleA" for item in payload["businessrules"])
    assert any(flow["trigger"]["kind"] == "rule_done" for flow in payload["flows"])
