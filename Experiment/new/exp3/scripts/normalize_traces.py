#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import dump_json, load_json
from parse_b2c import parse_b2c_model


STATE_BY_CODE = {
    0: "INACTIVE",
    1: "READY",
    2: "PENDING_CONFIRMATION",
    3: "DONE",
}

KIND_TO_MODEL_KEY = {
    "message": "messages",
    "gateway": "gateways",
    "event": "events",
    "businessrule": "businessrules",
    "businessRule": "businessrules",
    "oracletask": "oracletasks",
}

SNAPSHOT_KEY_BY_KIND = {
    "message": "messageStates",
    "gateway": "gatewayStates",
    "event": "eventStates",
    "businessRule": "businessRuleStates",
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
    for kind, model_key in KIND_TO_MODEL_KEY.items():
        if kind == "businessRule":
            continue
        for item in model.get(model_key, []):
            states[item["name"]] = state_name(item.get("initial_state") or "INACTIVE")
    return states


def enabled_from_states(states: Dict[str, str]) -> List[str]:
    return sorted(name for name, value in states.items() if value == "READY")


def apply_state_diff(states: Dict[str, str], diff: Dict[str, List[Any]]) -> Dict[str, str]:
    updated = deepcopy(states)
    for element_id, transition in (diff or {}).items():
        if isinstance(transition, list) and len(transition) >= 2:
            updated[element_id] = state_name(transition[1])
    return updated


def diff_states(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, List[str]]:
    return {
        key: [before.get(key, "INACTIVE"), value]
        for key, value in after.items()
        if before.get(key, "INACTIVE") != value
    }


def snapshot_to_states(snapshot: Dict[str, Any], order: Dict[str, List[str]]) -> Dict[str, str]:
    states: Dict[str, str] = {}
    for kind, snapshot_key in SNAPSHOT_KEY_BY_KIND.items():
        values = snapshot.get(snapshot_key) or []
        for idx, element_id in enumerate(order.get(kind, [])):
            states[element_id] = state_name(values[idx] if idx < len(values) else 0)
    return states


def normalize_dsl_trace(trace_path: Path, model: Dict[str, Any]) -> Dict[str, Any]:
    trace = load_json(trace_path)
    states = initial_element_states(model)
    raw_steps: List[Dict[str, Any]] = []
    logical_steps: List[Dict[str, Any]] = []

    def append_step(raw: Dict[str, Any], phase: str, index: int) -> None:
        nonlocal states
        trigger = raw.get("trigger") or {}
        trigger_type = "event" if trigger.get("type") == "start" else trigger.get("type")
        before = deepcopy(states)
        combined_after = apply_state_diff(states, raw.get("state_diff") or {})
        states = combined_after
        normalized = {
            "index": index,
            "phase": phase,
            "trigger": {
                "type": trigger_type,
                "element": trigger.get("name"),
                "method": trigger.get("name"),
            },
            "enabled_before": enabled_from_states(before),
            "accepted": bool(raw.get("accepted", True)),
            "rejection_reason": raw.get("rejection_reason", ""),
            "payload": raw.get("payload", {}),
            "outputs": raw.get("outputs", {}),
            "state_diff": raw.get("state_diff", {}),
            "global_diff": raw.get("global_diff", {}),
            "states_after": deepcopy(combined_after),
            "logs": raw.get("logs", []),
            "raw": raw,
        }
        raw_steps.append(normalized)
        logical_steps.extend(split_dsl_parallel_join_step(normalized, before, combined_after))

    for bootstrap in trace.get("bootstrap", []):
        append_step(bootstrap, "bootstrap", len(logical_steps))
    for step in trace.get("steps", []):
        append_step(step, "execute", len(logical_steps))

    final = trace.get("final_state") or {}
    return {
        "schema_version": "exp3.unified_trace.v1",
        "platform": "dsl",
        "case_name": trace.get("case_name"),
        "path_name": trace.get("path_name"),
        "source_trace": str(trace_path),
        "element_order": model_element_order(model),
        "raw_steps": raw_steps,
        "steps": logical_steps,
        "final_state": {
            "status": final.get("status"),
            "reason": final.get("reason", ""),
            "enabled_elements": final.get("enabled_elements", enabled_from_states(states)),
            "element_states": final.get("element_states", states),
            "globals": final.get("globals", {}),
        },
    }


def split_dsl_parallel_join_step(
    step: Dict[str, Any],
    before: Dict[str, str],
    combined_after: Dict[str, str],
) -> List[Dict[str, Any]]:
    joins = [
        item for item in ((step.get("raw") or {}).get("flow_results") or [])
        if item.get("kind") == "parallel_join" and item.get("gateway")
    ]
    if not joins:
        return [deepcopy(step)]

    result: List[Dict[str, Any]] = []
    remaining_diff = deepcopy(step.get("state_diff") or {})
    synthetic_diffs: List[Tuple[str, Dict[str, List[str]], Dict[str, Any]]] = []

    for join in joins:
        gateway = join["gateway"]
        synthetic_diff: Dict[str, List[str]] = {}
        if gateway in remaining_diff:
            synthetic_diff[gateway] = remaining_diff.pop(gateway)
        for action in join.get("applied_actions") or []:
            target = action.get("target")
            if target in remaining_diff:
                synthetic_diff[target] = remaining_diff.pop(target)
        synthetic_diffs.append((gateway, synthetic_diff, join))

    primary_after = apply_state_diff(before, remaining_diff)
    primary = deepcopy(step)
    primary["state_diff"] = remaining_diff
    primary["states_after"] = deepcopy(primary_after)
    result.append(primary)

    current_before = primary_after
    for gateway, synthetic_diff, join in synthetic_diffs:
        synthetic_after = apply_state_diff(current_before, synthetic_diff)
        result.append(
            {
                "index": step["index"],
                "phase": "synthetic_parallel_join",
                "trigger": {
                    "type": "gateway",
                    "element": gateway,
                    "method": gateway,
                },
                "enabled_before": enabled_from_states(current_before),
                "accepted": bool(join.get("accepted", True)),
                "rejection_reason": join.get("reason", ""),
                "payload": {},
                "outputs": {},
                "state_diff": synthetic_diff,
                "global_diff": {},
                "states_after": deepcopy(synthetic_after),
                "logs": [f"synthetic parallel join {gateway}"],
                "raw": join,
            }
        )
        current_before = synthetic_after

    for index, item in enumerate(result):
        item["index"] = step["index"] + index
    return result


def normalize_solidity_replay(replay_path: Path, model: Dict[str, Any]) -> Dict[str, Any]:
    replay = load_json(replay_path)
    order = model_element_order(model)
    states = initial_element_states(model)
    raw_steps: List[Dict[str, Any]] = []

    for idx, step in enumerate(replay.get("steps", [])):
        before = deepcopy(states)
        after = snapshot_to_states(step.get("snapshot_after") or {}, order)
        states = after
        element_type = step.get("element_type")
        normalized_type = "businessRule" if element_type == "businessRule" else element_type
        normalized = {
            "index": idx,
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
        raw_steps.append(normalized)

    logical_steps = collapse_solidity_business_rules(raw_steps)
    final_states = snapshot_to_states(replay.get("final_snapshot") or {}, order)
    final_status = "accepted" if replay.get("success") else "rejected"
    return {
        "schema_version": "exp3.unified_trace.v1",
        "platform": "solidity",
        "case_name": replay.get("bpmn_name"),
        "path_name": replay_path.stem,
        "source_trace": str(replay_path),
        "element_order": order,
        "raw_steps": raw_steps,
        "steps": logical_steps,
        "final_state": {
            "status": final_status,
            "reason": "" if replay.get("success") else "replay failed",
            "enabled_elements": enabled_from_states(final_states),
            "element_states": final_states,
            "globals": {},
            "local_instance_id": replay.get("local_instance_id"),
            "on_chain_instance_id": replay.get("on_chain_instance_id"),
        },
    }


def collapse_solidity_business_rules(raw_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    collapsed: List[Dict[str, Any]] = []
    idx = 0
    while idx < len(raw_steps):
        current = deepcopy(raw_steps[idx])
        method = str(current.get("trigger", {}).get("method") or "")
        element = current.get("trigger", {}).get("element")
        is_rule_request = current.get("trigger", {}).get("type") == "businessRule" and not method.endswith("_Continue")
        if is_rule_request and idx + 1 < len(raw_steps):
            nxt = raw_steps[idx + 1]
            next_method = str(nxt.get("trigger", {}).get("method") or "")
            same_rule = nxt.get("trigger", {}).get("element") == element
            if same_rule and next_method.endswith("_Continue"):
                before_states = current.get("raw", {}).get("_states_before")
                merged = deepcopy(current)
                merged["trigger"]["method"] = f"{method}+{next_method}"
                merged["payload"] = {
                    "request": current.get("payload", {}),
                    "continue": nxt.get("payload", {}),
                }
                merged["state_diff"] = merge_state_diff(current.get("state_diff", {}), nxt.get("state_diff", {}))
                merged["states_after"] = deepcopy(nxt.get("states_after", {}))
                merged["tx_status"] = [current.get("tx_status"), nxt.get("tx_status")]
                merged["raw"] = {"request": current.get("raw"), "continue": nxt.get("raw")}
                collapsed.append(merged)
                idx += 2
                continue
        collapsed.append(current)
        idx += 1

    for index, step in enumerate(collapsed):
        step["index"] = index
    return collapsed


def merge_state_diff(first: Dict[str, List[str]], second: Dict[str, List[str]]) -> Dict[str, List[str]]:
    merged = deepcopy(first)
    for element_id, transition in second.items():
        if element_id in merged:
            merged[element_id] = [merged[element_id][0], transition[1]]
        else:
            merged[element_id] = transition
    return merged


def load_model(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return parse_b2c_model(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize exp3 DSL/Solidity traces into one comparison-friendly schema.")
    parser.add_argument("--platform", choices=["dsl", "solidity"], required=True)
    parser.add_argument("--trace", required=True, help="Path to a raw DSL trace or Solidity replay JSON")
    parser.add_argument("--model", required=True, help="Path to the B2C source or parsed dsl_model.json for the same model")
    parser.add_argument("--output", required=True, help="Path to write the normalized trace JSON")
    args = parser.parse_args()

    trace_path = Path(args.trace).resolve()
    model = load_model(Path(args.model).resolve())
    if args.platform == "dsl":
        normalized = normalize_dsl_trace(trace_path, model)
    else:
        normalized = normalize_solidity_replay(trace_path, model)
    dump_json(Path(args.output), normalized)
    print(f"Wrote normalized {args.platform} trace: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
