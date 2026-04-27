#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import dump_json, load_json, normalize_name
from dsl_simulator import DSLSimulator
from parse_b2c import parse_b2c_model


def load_model(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return parse_b2c_model(path)


def schema_payload(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        schema = json.loads(message.get("schema") or "{}")
    except Exception:
        schema = {}
    payload: Dict[str, Any] = {}
    for name, prop in (schema.get("properties") or {}).items():
        payload[name] = sample_value(name, str(prop.get("type") or "string"))
    for name, prop in (schema.get("files") or {}).items():
        payload[name] = sample_value(name, str(prop.get("type") or "file"))
    return payload


def sample_value(name: str, kind: str) -> Any:
    lowered = normalize_name(name)
    if kind in ("number", "integer", "int"):
        return 1
    if kind in ("boolean", "bool"):
        return True
    if kind == "file":
        return f"{name}-sample-file"
    if lowered.endswith("id") or "requestid" in lowered:
        return f"sample-{name}"
    return f"sample-{name}"


def collect_branch_values_by_global(model: Dict[str, Any]) -> Dict[str, List[Any]]:
    values: Dict[str, List[Any]] = {}
    for flow in model.get("flows", []):
        if flow.get("kind") != "gateway_flow":
            continue
        for branch in flow.get("conditions", []) or []:
            if branch.get("condition_kind") != "compare":
                continue
            if branch.get("relation") != "==":
                continue
            var = branch.get("var")
            if not var:
                continue
            values.setdefault(var, [])
            value = branch.get("value")
            if value not in values[var]:
                values[var].append(value)
    return values


def output_variants_for_rule(rule: Dict[str, Any], branch_values: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = [{}]
    for mapping in rule.get("output_mapping", []) or []:
        param = mapping.get("dmn_param")
        global_name = mapping.get("global")
        candidates = branch_values.get(global_name) or [sample_value(param or global_name or "output", "string")]
        next_variants = []
        for base in variants:
            for value in candidates:
                item = dict(base)
                item[param] = value
                next_variants.append(item)
        variants = next_variants
    return variants or [{}]


def build_step_variants(model: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    variants: Dict[str, List[Dict[str, Any]]] = {}
    for message in model.get("messages", []):
        variants[message["name"]] = [
            {
                "type": "message",
                "element": message["name"],
                "payload": schema_payload(message),
            }
        ]
    for gateway in model.get("gateways", []):
        variants[gateway["name"]] = [{"type": "gateway", "element": gateway["name"]}]
    for event in model.get("events", []):
        variants[event["name"]] = [{"type": "event", "element": event["name"]}]
    branch_values = collect_branch_values_by_global(model)
    for rule in model.get("businessrules", []):
        variants[rule["name"]] = [
            {
                "type": "businessrule",
                "element": rule["name"],
                "outputs": outputs,
            }
            for outputs in output_variants_for_rule(rule, branch_values)
        ]
    for task in model.get("oracletasks", []):
        variants[task["name"]] = [
            {
                "type": "oracletask",
                "element": task["name"],
                "outputs": {
                    mapping.get("dmn_param"): sample_value(mapping.get("dmn_param") or "output", "string")
                    for mapping in task.get("output_mapping", []) or []
                },
            }
        ]
    return variants


def state_signature(simulator: DSLSimulator) -> Tuple[Any, ...]:
    return (
        tuple(sorted(simulator.states.items())),
        tuple(sorted((key, repr(value)) for key, value in simulator.globals.items())),
    )


def is_terminal(simulator: DSLSimulator) -> bool:
    return not simulator.enabled_elements()


def enumerate_paths(
    model: Dict[str, Any],
    case_name: str,
    max_depth: int,
    max_paths: int,
) -> List[Dict[str, Any]]:
    root = DSLSimulator(model, case_name)
    variants = build_step_variants(model)
    auto_parallel_gateways = {
        (flow.get("trigger") or {}).get("name")
        for flow in model.get("flows", [])
        if flow.get("kind") == "parallel_join"
    }
    paths: List[Dict[str, Any]] = []

    def walk(simulator: DSLSimulator, steps: List[Dict[str, Any]], seen: set[Tuple[Any, ...]]) -> None:
        if len(paths) >= max_paths:
            return
        if simulator.rejected:
            return
        if is_terminal(simulator):
            paths.append(make_path(case_name, len(paths), steps, simulator))
            return
        if len(steps) >= max_depth:
            return

        enabled = [
            element
            for element in simulator.enabled_elements()
            if element not in auto_parallel_gateways
        ]
        if not enabled:
            paths.append(make_path(case_name, len(paths), steps, simulator))
            return
        for element in enabled:
            for step in variants.get(element, [{"type": simulator.elements[element].kind, "element": element}]):
                next_sim = deepcopy(simulator)
                next_step = deepcopy(step)
                next_sim._execute_step(len(next_sim.trace_steps), next_step)
                signature = state_signature(next_sim)
                if signature in seen:
                    continue
                walk(next_sim, steps + [next_step], seen | {signature})

    walk(root, [], {state_signature(root)})
    return paths


def make_path(case_name: str, index: int, steps: List[Dict[str, Any]], simulator: DSLSimulator) -> Dict[str, Any]:
    return {
        "path_name": f"{case_name}_auto_path_{index + 1:03d}",
        "expect": "accepted",
        "steps": steps,
        "final_enabled_elements": simulator.enabled_elements(),
        "final_element_states": deepcopy(simulator.states),
        "final_globals": deepcopy(simulator.globals),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate executable DSL paths for a BPMN/DMN-derived B2C case.")
    parser.add_argument("--model", required=True, help="Path to .b2c or parsed dsl_model.json")
    parser.add_argument("--case-name", default="", help="Case name for generated paths")
    parser.add_argument("--output", required=True, help="Path to write generated paths JSON")
    parser.add_argument("--max-depth", type=int, default=64)
    parser.add_argument("--max-paths", type=int, default=1000)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    model = load_model(model_path)
    case_name = args.case_name or str(model.get("contract_name") or model_path.stem)
    paths = enumerate_paths(model, case_name, args.max_depth, args.max_paths)
    payload = {
        "case_name": case_name,
        "source_model": str(model_path),
        "path_count": len(paths),
        "paths": paths,
    }
    dump_json(Path(args.output), payload)
    print(f"Generated {len(paths)} paths: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
