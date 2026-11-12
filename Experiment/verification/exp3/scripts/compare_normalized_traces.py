#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import dump_json, dump_text, load_json


def trigger_key(step: Dict[str, Any]) -> Tuple[str, str]:
    trigger = step.get("trigger") or {}
    trigger_type = str(trigger.get("type") or "").strip()
    if trigger_type == "businessRule":
        trigger_type = "businessrule"
    return trigger_type.lower(), str(trigger.get("element") or "")


def normalized_state_diff(step: Dict[str, Any]) -> Dict[str, Tuple[Any, Any]]:
    return {
        key: tuple(value)
        for key, value in sorted((step.get("state_diff") or {}).items())
    }


def sorted_list(value: Any) -> List[Any]:
    return sorted(value or [])


def compare_traces(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    left_steps = list(left.get("steps") or [])
    right_steps = list(right.get("steps") or [])

    def add_finding(scope: str, field: str, left_value: Any, right_value: Any) -> None:
        findings.append(
            {
                "scope": scope,
                "field": field,
                "left": left_value,
                "right": right_value,
            }
        )

    if left.get("schema_version") != right.get("schema_version"):
        add_finding("trace", "schema_version", left.get("schema_version"), right.get("schema_version"))

    if len(left_steps) != len(right_steps):
        add_finding("trace", "step_count", len(left_steps), len(right_steps))

    if (left.get("final_state") or {}).get("status") != (right.get("final_state") or {}).get("status"):
        add_finding(
            "final_state",
            "status",
            (left.get("final_state") or {}).get("status"),
            (right.get("final_state") or {}).get("status"),
        )

    for index in range(min(len(left_steps), len(right_steps))):
        left_step = left_steps[index]
        right_step = right_steps[index]
        scope = f"steps[{index}]"

        if trigger_key(left_step) != trigger_key(right_step):
            add_finding(scope, "trigger", trigger_key(left_step), trigger_key(right_step))

        if sorted_list(left_step.get("enabled_before")) != sorted_list(right_step.get("enabled_before")):
            add_finding(
                scope,
                "enabled_before",
                sorted_list(left_step.get("enabled_before")),
                sorted_list(right_step.get("enabled_before")),
            )

        if bool(left_step.get("accepted")) != bool(right_step.get("accepted")):
            add_finding(scope, "accepted", left_step.get("accepted"), right_step.get("accepted"))

        if str(left_step.get("rejection_reason") or "") != str(right_step.get("rejection_reason") or ""):
            add_finding(
                scope,
                "rejection_reason",
                left_step.get("rejection_reason") or "",
                right_step.get("rejection_reason") or "",
            )

        if normalized_state_diff(left_step) != normalized_state_diff(right_step):
            add_finding(scope, "state_diff", left_step.get("state_diff") or {}, right_step.get("state_diff") or {})

    left_final = left.get("final_state") or {}
    right_final = right.get("final_state") or {}
    left_states = left_final.get("element_states") or {}
    right_states = right_final.get("element_states") or {}
    state_diffs = []
    for element_id in sorted(set(left_states) | set(right_states)):
        if left_states.get(element_id) != right_states.get(element_id):
            state_diffs.append(
                {
                    "element": element_id,
                    "left": left_states.get(element_id),
                    "right": right_states.get(element_id),
                }
            )
    if state_diffs:
        add_finding("final_state", "element_states", state_diffs, f"{len(state_diffs)} differences")

    if sorted_list(left_final.get("enabled_elements")) != sorted_list(right_final.get("enabled_elements")):
        add_finding(
            "final_state",
            "enabled_elements",
            sorted_list(left_final.get("enabled_elements")),
            sorted_list(right_final.get("enabled_elements")),
        )

    return {
        "schema_version": "exp3.trace_comparison.v1",
        "left": {
            "platform": left.get("platform"),
            "source_trace": left.get("source_trace"),
            "step_count": len(left_steps),
            "final_status": left_final.get("status"),
        },
        "right": {
            "platform": right.get("platform"),
            "source_trace": right.get("source_trace"),
            "step_count": len(right_steps),
            "final_status": right_final.get("status"),
        },
        "consistent": len(findings) == 0,
        "finding_count": len(findings),
        "findings": findings,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Exp3 Normalized Trace Comparison",
        "",
        f"- Left platform: `{report['left'].get('platform')}`",
        f"- Right platform: `{report['right'].get('platform')}`",
        f"- Left steps: `{report['left'].get('step_count')}`",
        f"- Right steps: `{report['right'].get('step_count')}`",
        f"- Left final status: `{report['left'].get('final_status')}`",
        f"- Right final status: `{report['right'].get('final_status')}`",
        f"- Consistent: `{report.get('consistent')}`",
        f"- Finding count: `{report.get('finding_count')}`",
        "",
        "## Sources",
        "",
        f"- Left: `{report['left'].get('source_trace')}`",
        f"- Right: `{report['right'].get('source_trace')}`",
        "",
        "## Findings",
        "",
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("No differences found.")
        return "\n".join(lines) + "\n"

    for index, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"{index}. `{finding.get('scope')}` / `{finding.get('field')}`",
                "",
                "```json",
                jsonish({"left": finding.get("left"), "right": finding.get("right")}),
                "```",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def jsonish(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two exp3 normalized traces.")
    parser.add_argument("--left", required=True, help="Left normalized trace JSON")
    parser.add_argument("--right", required=True, help="Right normalized trace JSON")
    parser.add_argument("--output-json", default="", help="Optional comparison JSON output path")
    parser.add_argument("--output-md", default="", help="Optional comparison Markdown output path")
    args = parser.parse_args()

    left_path = Path(args.left).resolve()
    right_path = Path(args.right).resolve()
    report = compare_traces(load_json(left_path), load_json(right_path))

    if args.output_json:
        dump_json(Path(args.output_json), report)
    if args.output_md:
        dump_text(Path(args.output_md), render_markdown(report))

    print(f"Consistent: {report['consistent']}")
    print(f"Finding count: {report['finding_count']}")
    print(f"Left steps: {report['left']['step_count']}")
    print(f"Right steps: {report['right']['step_count']}")
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
