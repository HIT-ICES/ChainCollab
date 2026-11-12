from pathlib import Path

from tools.compare_ir import compare, load_rules
from tools.extract_dsl_ir import parse_dsl


def test_compare_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    dsl_ir = parse_dsl(root / "cases" / "positive" / "basic_linear_case.b2c")
    go_ir = {
        "globals": [{"name": "Approved", "type": "bool"}],
        "elements": {
            "messages": ["Request", "Confirm"],
            "events": ["StartEvent_1", "EndEvent_1"],
            "gateways": ["Decision"],
            "businessrules": [],
        },
        "handlers": [
            {
                "name": "StartEvent_1",
                "trigger": {"kind": "start_event", "name": "StartEvent_1"},
                "actions": [{"op": "enable", "target": "Request"}],
                "branches": [],
            },
            {
                "name": "Message_Request_Complete",
                "trigger": {"kind": "message_completed", "name": "Request"},
                "actions": [{"op": "enable", "target": "Decision"}],
                "branches": [],
            },
            {
                "name": "Decision",
                "trigger": {"kind": "gateway_completed", "name": "Decision"},
                "actions": [],
                "branches": [
                    {
                        "condition": "Approved == true",
                        "actions": [{"op": "enable", "target": "Confirm"}],
                        "else_actions": [{"op": "enable", "target": "EndEvent_1"}],
                    }
                ],
            },
            {
                "name": "Message_Confirm_Complete",
                "trigger": {"kind": "message_completed", "name": "Confirm"},
                "actions": [{"op": "enable", "target": "EndEvent_1"}],
                "branches": [],
            },
        ],
    }
    result = compare(dsl_ir, go_ir, load_rules(root / "config" / "mapping_rules.yaml"), "go")
    assert result["summary"]["verdict"] in {"PASS", "PARTIAL"}
