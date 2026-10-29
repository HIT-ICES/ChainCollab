#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from common import dump_json, load_json
from mapping_rules import (
    MatchResult,
    verify_businessrule_go,
    verify_event_go,
    verify_flow_go,
    verify_gateway_go,
    verify_global_go,
    verify_message_go,
    verify_oracletask_go,
    verify_participant_go,
)


def append_result(results: List[Dict[str, Any]], element_name: str, element_type: str, match: MatchResult) -> None:
    results.append(
        {
            "element_name": element_name,
            "element_type": element_type,
            "matched": match.matched,
            "evidence": match.evidence,
            "missing_reason": match.missing_reason,
            "severity": match.severity,
        }
    )


def coverage(results: List[Dict[str, Any]], element_type: str | None = None) -> float:
    scoped = [item for item in results if element_type is None or item["element_type"] == element_type]
    if not scoped:
        return 1.0
    matched = sum(1 for item in scoped if item["matched"])
    return matched / len(scoped)


def build_report(case_name: str, dsl_ast: Dict[str, Any], go_ast: Dict[str, Any]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for item in dsl_ast.get("globals", []):
        append_result(results, item["name"], "global", verify_global_go(item, go_ast))
    for item in dsl_ast.get("participants", []):
        append_result(results, item["name"], "participant", verify_participant_go(item, go_ast))
    for item in dsl_ast.get("messages", []):
        append_result(results, item["name"], "message", verify_message_go(item, go_ast))
    for item in dsl_ast.get("gateways", []):
        append_result(results, item["name"], "gateway", verify_gateway_go(item, go_ast))
    for item in dsl_ast.get("events", []):
        append_result(results, item["name"], "event", verify_event_go(item, go_ast))
    for item in dsl_ast.get("businessrules", []):
        append_result(results, item["name"], "businessrule", verify_businessrule_go(item, go_ast))
    for item in dsl_ast.get("oracletasks", []):
        append_result(results, item["name"], "oracletask", verify_oracletask_go(item, go_ast))
    for index, flow in enumerate(dsl_ast.get("flows", []), start=1):
        trigger = flow.get("trigger", {})
        label = f"flow_{index}:{trigger.get('type')}:{trigger.get('name')}"
        append_result(results, label, "flow", verify_flow_go(flow, go_ast))

    return {
        "case_name": case_name,
        "target": "go",
        "contract_name": dsl_ast.get("contract_name"),
        "elements": results,
        "summary": {
            "dsl_element_coverage": coverage(results),
            "state_transition_preservation_rate": coverage(results, "flow"),
            "branch_logic_preservation_rate": coverage(results, "gateway"),
            "businessrule_mapping_accuracy": coverage(results, "businessrule"),
            "total_elements": len(results),
            "matched_elements": sum(1 for item in results if item["matched"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify DSL -> Go semantic preservation.")
    parser.add_argument("--dsl-ast", required=True, help="Path to dsl_ast.json")
    parser.add_argument("--go-ast", required=True, help="Path to go_ast.json")
    parser.add_argument("--output", required=True, help="Path to report JSON")
    parser.add_argument("--case-name", help="Override case name")
    args = parser.parse_args()

    dsl_ast = load_json(Path(args.dsl_ast).resolve())
    go_ast = load_json(Path(args.go_ast).resolve())
    report = build_report(args.case_name or Path(args.output).resolve().parent.name, dsl_ast, go_ast)
    dump_json(Path(args.output).resolve(), report)


if __name__ == "__main__":
    main()
