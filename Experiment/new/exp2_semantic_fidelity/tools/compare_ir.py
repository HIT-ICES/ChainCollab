#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from tools.common import dump_json, dump_text, load_json


def load_rules(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize_action_key(action: dict[str, Any]) -> tuple[str, str]:
    if action.get("op") == "set":
        return ("set", action.get("var", ""))
    return (action.get("op", ""), action.get("target", ""))


def action_match_stats(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    if not expected:
        return 1.0, []
    actual_keys = Counter(normalize_action_key(item) for item in actual)
    matched = 0
    missing: list[dict[str, Any]] = []
    for item in expected:
        key = normalize_action_key(item)
        if actual_keys[key] > 0:
            actual_keys[key] -= 1
            matched += 1
        else:
            missing.append(item)
    return matched / len(expected), missing


def trigger_matches(dsl_trigger: dict[str, Any], code_trigger: dict[str, Any], aliases: dict[str, Any]) -> bool:
    dsl_kind = dsl_trigger.get("kind", "")
    code_kind = code_trigger.get("kind", "")
    if dsl_trigger.get("name") != code_trigger.get("name"):
        return False
    allowed = set(aliases.get("trigger_aliases", {}).get(dsl_kind, [dsl_kind]))
    return code_kind in allowed


def find_handler_for_flow(flow: dict[str, Any], handlers: list[dict[str, Any]], aliases: dict[str, Any]) -> dict[str, Any] | None:
    for handler in handlers:
        if trigger_matches(flow.get("trigger", {}), handler.get("trigger", {}), aliases):
            return handler
    return None


def branch_match(flow: dict[str, Any], handler: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if not flow.get("branches"):
        return notes
    handler_branches = handler.get("branches", [])
    for branch in flow["branches"]:
        condition = branch.get("condition", {})
        expected_actions = branch.get("actions", [])
        if condition.get("kind") == "else":
            candidate = next((item for item in handler_branches if item.get("else_actions")), None)
            if not candidate:
                notes.append("missing else branch")
                continue
            ratio, missing = action_match_stats(expected_actions, candidate.get("else_actions", []))
            if ratio < 1.0:
                notes.append(f"else branch missing actions: {missing}")
            continue
        target_condition = " ".join(str(value) for value in condition.values()).lower()
        candidate = next(
            (item for item in handler_branches if target_condition and target_condition in item.get("condition", "").lower()),
            None,
        )
        if not candidate:
            candidate = next(
                (item for item in handler_branches if condition.get("var", "").lower() in item.get("condition", "").lower()),
                None,
            )
        if not candidate:
            notes.append(f"missing branch for condition {condition}")
            continue
        ratio, missing = action_match_stats(expected_actions, candidate.get("actions", []))
        if ratio < 1.0:
            notes.append(f"branch {condition} missing actions: {missing}")
    return notes


def compare(dsl_ir: dict[str, Any], code_ir: dict[str, Any], rules: dict[str, Any], language: str) -> dict[str, Any]:
    dsl_elements = {
        "globals": sorted(item["name"] for item in dsl_ir.get("globals", [])),
        "messages": sorted(item["name"] for item in dsl_ir.get("messages", [])),
        "events": sorted(item["name"] for item in dsl_ir.get("events", [])),
        "gateways": sorted(item["name"] for item in dsl_ir.get("gateways", [])),
        "businessrules": sorted(item["name"] for item in dsl_ir.get("businessrules", [])),
    }
    code_elements = {
        "globals": sorted(item["name"] for item in code_ir.get("globals", [])),
        "messages": sorted(code_ir.get("elements", {}).get("messages", [])),
        "events": sorted(code_ir.get("elements", {}).get("events", [])),
        "gateways": sorted(code_ir.get("elements", {}).get("gateways", [])),
        "businessrules": sorted(code_ir.get("elements", {}).get("businessrules", [])),
    }

    structure: dict[str, Any] = {}
    for category, expected in dsl_elements.items():
        actual = set(code_elements.get(category, []))
        expected_set = set(expected)
        structure[category] = {
            "matched": sorted(expected_set & actual),
            "missing": sorted(expected_set - actual),
            "extra": sorted(actual - expected_set),
            "unsupported": [],
        }

    flow_results: list[dict[str, Any]] = []
    for flow in dsl_ir.get("flows", []):
        handler = find_handler_for_flow(flow, code_ir.get("handlers", []), rules.get(language, {}))
        if not handler:
            flow_results.append(
                {
                    "rule_id": flow["id"],
                    "matched": False,
                    "trigger_match": False,
                    "action_match_ratio": 0.0,
                    "missing_actions": flow.get("actions", []),
                    "notes": ["no matching handler"],
                }
            )
            continue
        ratio, missing = action_match_stats(flow.get("actions", []), handler.get("actions", []))
        notes = branch_match(flow, handler)
        matched = ratio == 1.0 and not notes
        flow_results.append(
            {
                "rule_id": flow["id"],
                "matched": matched,
                "trigger_match": True,
                "handler": handler.get("name", ""),
                "action_match_ratio": ratio,
                "missing_actions": missing,
                "notes": notes,
            }
        )

    matched_rules = sum(1 for item in flow_results if item["matched"])
    total_rules = len(flow_results)
    coverage = matched_rules / total_rules if total_rules else 1.0
    unsupported = sorted({note for item in flow_results for note in item.get("notes", []) if "missing" in note})
    verdict = "PASS" if coverage == 1.0 and not unsupported else "PARTIAL" if coverage > 0 else "FAIL"

    return {
        "language": language,
        "dsl_source": dsl_ir.get("source_file", ""),
        "code_source": code_ir.get("source_file", ""),
        "structure": structure,
        "flow_results": flow_results,
        "summary": {
            "flow_total": total_rules,
            "flow_matched": matched_rules,
            "flow_coverage": round(coverage, 4),
            "unsupported_constructs": unsupported,
            "verdict": verdict,
        },
    }


def report_markdown(case_name: str, dsl_ir: dict[str, Any], go_compare: dict[str, Any] | None, sol_compare: dict[str, Any] | None, code_paths: dict[str, str]) -> str:
    lines = [
        f"# Semantic Fidelity Report: {case_name}",
        "",
        f"- DSL: `{code_paths.get('dsl', '')}`",
        f"- Go: `{code_paths.get('go', '')}`",
        f"- Solidity: `{code_paths.get('sol', '')}`",
        "",
        "## DSL Statistics",
        "",
        f"- participants: {len(dsl_ir.get('participants', []))}",
        f"- globals: {len(dsl_ir.get('globals', []))}",
        f"- messages: {len(dsl_ir.get('messages', []))}",
        f"- events: {len(dsl_ir.get('events', []))}",
        f"- gateways: {len(dsl_ir.get('gateways', []))}",
        f"- businessrules: {len(dsl_ir.get('businessrules', []))}",
        f"- flows: {len(dsl_ir.get('flows', []))}",
        "",
    ]
    for title, payload in (("Go", go_compare), ("Solidity", sol_compare)):
        if not payload:
            continue
        lines.extend(
            [
                f"## {title}",
                "",
                f"- verdict: {payload['summary']['verdict']}",
                f"- flow matched: {payload['summary']['flow_matched']} / {payload['summary']['flow_total']}",
                f"- flow coverage: {payload['summary']['flow_coverage']}",
                f"- unsupported: {', '.join(payload['summary']['unsupported_constructs']) or 'none'}",
                "",
                "### Missing Structure",
                "",
            ]
        )
        for category, detail in payload["structure"].items():
            lines.append(f"- {category}: missing={detail['missing']} extra={detail['extra']}")
        lines.extend(["", "### Unmatched Rules", ""])
        unmatched = [item for item in payload["flow_results"] if not item["matched"]]
        if not unmatched:
            lines.append("- none")
        else:
            for item in unmatched:
                lines.append(
                    f"- {item['rule_id']}: trigger_match={item['trigger_match']} ratio={item['action_match_ratio']} missing={item['missing_actions']} notes={item['notes']}"
                )
        lines.append("")
    final_verdicts = [item["summary"]["verdict"] for item in (go_compare, sol_compare) if item]
    if final_verdicts and all(item == "PASS" for item in final_verdicts):
        final = "PASS"
    elif any(item == "PARTIAL" for item in final_verdicts) or any(item == "PASS" for item in final_verdicts):
        final = "PARTIAL"
    else:
        final = "FAIL"
    lines.extend(["## Conclusion", "", f"- final verdict: {final}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare DSL IR against Go/Solidity IR.")
    parser.add_argument("--dsl-ir", required=True)
    parser.add_argument("--code-ir", required=True)
    parser.add_argument("--language", required=True, choices=["go", "solidity"])
    parser.add_argument("--mapping-rules", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = compare(load_json(Path(args.dsl_ir)), load_json(Path(args.code_ir)), load_rules(Path(args.mapping_rules)), args.language)
    dump_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
