#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from common import EXP3_ROOT, dump_json, dump_text, load_json
from compare_normalized_traces import compare_traces, render_markdown


STATE_BY_CODE = {
    0: "INACTIVE",
    1: "READY",
    2: "PENDING_CONFIRMATION",
    3: "DONE",
}


def state_name(value: Any) -> str:
    if isinstance(value, str) and not value.isdigit():
        return value
    try:
        return STATE_BY_CODE.get(int(value), str(value))
    except Exception:
        return str(value)


def model_element_order(model: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "message": [item["name"] for item in model.get("messages", [])],
        "gateway": [item["name"] for item in model.get("gateways", [])],
        "event": [item["name"] for item in model.get("events", [])],
        "businessRule": [item["name"] for item in model.get("businessrules", [])],
        "oracletask": [item["name"] for item in model.get("oracletasks", [])],
    }


def initial_element_states(model: Dict[str, Any]) -> Dict[str, str]:
    states: Dict[str, str] = {}
    for model_key in ("messages", "gateways", "events"):
        for item in model.get(model_key, []):
            states[item["name"]] = state_name(item.get("initial_state") or "INACTIVE")
    for item in model.get("businessrules", []):
        states[item["name"]] = "INACTIVE"
    return states


def enabled_from_states(states: Dict[str, str]) -> List[str]:
    return sorted(name for name, value in states.items() if value == "READY")


def snapshot_to_states(snapshot: Dict[str, Any], order: Dict[str, List[str]]) -> Dict[str, str]:
    states: Dict[str, str] = {}
    mappings = (
        ("message", "messageIds", "messageStates"),
        ("gateway", "gatewayIds", "gatewayStates"),
        ("event", "eventIds", "eventStates"),
        ("businessRule", "businessRuleIds", "businessRuleStates"),
    )
    for kind, id_key, state_key in mappings:
        ids = snapshot.get(id_key) or []
        values = snapshot.get(state_key) or []
        by_id = {
            str(element_id): state_name(values[index] if index < len(values) else 0)
            for index, element_id in enumerate(ids)
        }
        for element_id in order.get(kind, []):
            states[element_id] = by_id.get(element_id, "INACTIVE")
    return states


def diff_states(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, List[str]]:
    return {
        key: [before.get(key, "INACTIVE"), value]
        for key, value in after.items()
        if before.get(key, "INACTIVE") != value
    }


def merge_state_diff(first: Dict[str, List[str]], second: Dict[str, List[str]]) -> Dict[str, List[str]]:
    merged = deepcopy(first)
    for element_id, transition in second.items():
        if element_id in merged:
            merged[element_id] = [merged[element_id][0], transition[1]]
        else:
            merged[element_id] = transition
    return merged


def collapse_fabric_business_rules(raw_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    collapsed: List[Dict[str, Any]] = []
    index = 0
    while index < len(raw_steps):
        current = deepcopy(raw_steps[index])
        trigger = current.get("trigger") or {}
        method = str(trigger.get("method") or "")
        element = trigger.get("element")
        is_rule_request = trigger.get("type") == "businessRule" and not method.endswith("_Continue")
        if is_rule_request and index + 1 < len(raw_steps):
            next_step = raw_steps[index + 1]
            next_trigger = next_step.get("trigger") or {}
            next_method = str(next_trigger.get("method") or "")
            same_rule = next_trigger.get("element") == element
            if same_rule and next_method.endswith("_Continue"):
                current["trigger"]["method"] = f"{method}+{next_method}"
                current["payload"] = {
                    "request": current.get("payload", {}),
                    "continue": next_step.get("payload", {}),
                }
                current["state_diff"] = merge_state_diff(
                    current.get("state_diff", {}),
                    next_step.get("state_diff", {}),
                )
                current["states_after"] = deepcopy(next_step.get("states_after", {}))
                current["tx_status"] = [current.get("tx_status"), next_step.get("tx_status")]
                current["raw"] = {"request": current.get("raw"), "continue": next_step.get("raw")}
                collapsed.append(current)
                index += 2
                continue
        collapsed.append(current)
        index += 1

    for step_index, step in enumerate(collapsed):
        step["index"] = step_index
    return collapsed


def normalize_fabric_replay(replay_path: Path, model: Dict[str, Any]) -> Dict[str, Any]:
    replay = load_json(replay_path)
    order = model_element_order(model)
    states = initial_element_states(model)
    raw_steps: List[Dict[str, Any]] = []

    for index, step in enumerate(replay.get("steps", [])):
        before = deepcopy(states)
        after = snapshot_to_states(step.get("snapshot_after") or {}, order)
        states = after
        element_type = step.get("element_type")
        normalized_type = "businessRule" if element_type == "businessRule" else element_type
        raw_steps.append(
            {
                "index": index,
                "phase": "execute",
                "trigger": {
                    "type": normalized_type,
                    "element": step.get("element_id"),
                    "method": step.get("method"),
                },
                "enabled_before": enabled_from_states(before),
                "accepted": True,
                "rejection_reason": "",
                "payload": step.get("payload", {}),
                "outputs": {},
                "state_diff": diff_states(before, after),
                "global_diff": {},
                "states_after": deepcopy(after),
                "tx_status": (step.get("response") or {}).get("status"),
                "raw": step,
            }
        )

    final_states = snapshot_to_states(replay.get("final_snapshot") or {}, order)
    final_status = "accepted" if replay.get("success") else "rejected"
    return {
        "schema_version": "exp3.unified_trace.v1",
        "platform": "fabric",
        "case_name": replay.get("bpmn_name") or "SupplyChainPaper",
        "path_name": replay_path.stem,
        "source_trace": str(replay_path),
        "element_order": order,
        "raw_steps": raw_steps,
        "steps": collapse_fabric_business_rules(raw_steps),
        "final_state": {
            "status": final_status,
            "reason": "" if replay.get("success") else "replay failed",
            "enabled_elements": enabled_from_states(final_states),
            "element_states": final_states,
            "globals": {},
            "fabric_instance_id": replay.get("instance_id"),
        },
    }


def infer_case_and_path(fabric_replay: Path, sequence_file: str = "") -> tuple[str, str]:
    for source in [Path(sequence_file).resolve() if sequence_file else None, fabric_replay.resolve()]:
        if not source:
            continue
        parts = source.parts
        if "paths" not in parts:
            continue
        path_index = parts.index("paths")
        if path_index == 0 or path_index + 1 >= len(parts):
            continue
        return parts[path_index - 1], parts[path_index + 1]
    raise ValueError("Unable to infer case/path; pass --case-name and --path-name")


def build_paths(
    *,
    fabric_replay: Path,
    sequence_file: str = "",
    case_name: str = "",
    path_name: str = "",
    model_file: str = "",
    output_root: str = "",
) -> Dict[str, Path]:
    if not case_name or not path_name:
        inferred_case, inferred_path = infer_case_and_path(fabric_replay, sequence_file)
        case_name = case_name or inferred_case
        path_name = path_name or inferred_path

    base = Path(output_root) if output_root else EXP3_ROOT / "outputs" / case_name / "paths" / path_name
    return {
        "model": Path(model_file) if model_file else EXP3_ROOT / "dsl" / case_name / "paths" / path_name / "dsl_model.json",
        "normalized_dir": base / "normalized",
        "dsl_normalized": base / "normalized" / "dsl.normalized.json",
        "solidity_normalized": base / "normalized" / "solidity.normalized.json",
        "fabric_normalized": base / "normalized" / "fabric.normalized.json",
        "dsl_fabric_json": base / "comparison.dsl_fabric.json",
        "dsl_fabric_md": base / "comparison.dsl_fabric.md",
        "solidity_fabric_json": base / "comparison.solidity_fabric.json",
        "solidity_fabric_md": base / "comparison.solidity_fabric.md",
    }


def write_comparison(left_path: Path, right_path: Path, output_json: Path, output_md: Path) -> Dict[str, Any]:
    report = compare_traces(load_json(left_path), load_json(right_path))
    dump_json(output_json, report)
    dump_text(output_md, render_markdown(report))
    return report


def run_fabric_comparison(
    *,
    fabric_replay: Path,
    sequence_file: str = "",
    case_name: str = "",
    path_name: str = "",
    model_file: str = "",
    output_root: str = "",
    strict: bool = False,
) -> Dict[str, Any]:
    paths = build_paths(
        fabric_replay=fabric_replay,
        sequence_file=sequence_file,
        case_name=case_name,
        path_name=path_name,
        model_file=model_file,
        output_root=output_root,
    )
    model_path = paths["model"]
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    normalized = normalize_fabric_replay(fabric_replay, load_json(model_path))
    dump_json(paths["fabric_normalized"], normalized)

    reports: Dict[str, Any] = {
        "fabric_normalized": str(paths["fabric_normalized"]),
        "comparisons": {},
        "warnings": [],
    }

    comparisons = (
        ("dsl_fabric", paths["dsl_normalized"], paths["dsl_fabric_json"], paths["dsl_fabric_md"]),
        ("solidity_fabric", paths["solidity_normalized"], paths["solidity_fabric_json"], paths["solidity_fabric_md"]),
    )
    for name, left_path, output_json, output_md in comparisons:
        if not left_path.exists():
            message = f"Skipped {name}; missing normalized trace: {left_path}"
            reports["warnings"].append(message)
            if strict:
                raise FileNotFoundError(message)
            continue
        report = write_comparison(left_path, paths["fabric_normalized"], output_json, output_md)
        reports["comparisons"][name] = {
            "json": str(output_json),
            "md": str(output_md),
            "consistent": report.get("consistent"),
            "finding_count": report.get("finding_count"),
            "left_steps": (report.get("left") or {}).get("step_count"),
            "right_steps": (report.get("right") or {}).get("step_count"),
        }
        if strict and not report.get("consistent"):
            raise RuntimeError(f"{name} comparison is not consistent; see {output_json}")

    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a Fabric replay and compare it with existing DSL/Solidity normalized traces.")
    parser.add_argument("--fabric-replay", required=True, help="Path to Fabric replay JSON")
    parser.add_argument("--sequence-file", default="", help="Optional logical path/sequence file used to infer case/path")
    parser.add_argument("--case-name", default="", help="Optional case name override")
    parser.add_argument("--path-name", default="", help="Optional path name override")
    parser.add_argument("--model", default="", help="Optional dsl_model.json path")
    parser.add_argument("--output-root", default="", help="Optional output root for normalized/comparison files")
    parser.add_argument("--strict", action="store_true", help="Fail if comparison inputs are missing or comparisons differ")
    args = parser.parse_args()

    result = run_fabric_comparison(
        fabric_replay=Path(args.fabric_replay).resolve(),
        sequence_file=args.sequence_file,
        case_name=args.case_name,
        path_name=args.path_name,
        model_file=args.model,
        output_root=args.output_root,
        strict=args.strict,
    )
    print(f"Wrote Fabric normalized trace: {result['fabric_normalized']}")
    for warning in result["warnings"]:
        print(f"Warning: {warning}")
    for name, report in result["comparisons"].items():
        print(
            f"{name}: consistent={report['consistent']} "
            f"findings={report['finding_count']} "
            f"steps={report['left_steps']}/{report['right_steps']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
