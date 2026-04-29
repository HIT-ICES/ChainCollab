#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

from common import CHAINCOLLAB_ROOT, dump_json, load_json, normalize_name
from dmn_input_solver import normalize_literal, parse_dmn, sample_for_expression
from dsl_simulator import DSLSimulator
from parse_b2c import parse_b2c_model


DEFAULT_DMN_DIR = CHAINCOLLAB_ROOT / "Experiment" / "BPMNwithDMNcase"


def load_model(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return parse_b2c_model(path)


def unique_values(values: List[Any]) -> List[Any]:
    unique: List[Any] = []
    seen = set()
    for value in values:
        key = (type(value).__name__, repr(value))
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def schema_payload_variants(message: Dict[str, Any], branch_values: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    try:
        schema = json.loads(message.get("schema") or "{}")
    except Exception:
        schema = {}
    fields = []
    field_specs = list((schema.get("properties") or {}).items()) + list((schema.get("files") or {}).items())
    for name, prop in field_specs:
        kind = str(prop.get("type") or "string")
        candidates = list(branch_values.get(normalize_name(name)) or [])
        if not candidates:
            candidates.append(sample_value(name, kind))
        fields.append((name, unique_values(candidates)))
    if not fields:
        return [{}]
    variants = []
    for values in product(*[candidates for _, candidates in fields]):
        variants.append({name: value for (name, _), value in zip(fields, values)})
    return variants


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


def sample_for_compare(relation: str, value: Any) -> Optional[Any]:
    if relation == "==":
        return value
    if relation == "!=":
        if isinstance(value, bool):
            return not value
        if isinstance(value, (int, float)):
            return value + 1
        if isinstance(value, str):
            return f"not-{value}"
        return None
    if not isinstance(value, (int, float)):
        return None
    if relation in (">", ">="):
        return value + 1
    if relation in ("<", "<="):
        return value - 1
    return None


def collect_branch_values_by_global(model: Dict[str, Any]) -> Dict[str, List[Any]]:
    values: Dict[str, List[Any]] = {}
    for flow in model.get("flows", []):
        if flow.get("kind") != "gateway_flow":
            continue
        for branch in flow.get("conditions", []) or []:
            if branch.get("condition_kind") != "compare":
                continue
            var = branch.get("var")
            if not var:
                continue
            value = sample_for_compare(str(branch.get("relation") or ""), branch.get("value"))
            if value is None:
                continue
            key = normalize_name(var)
            values.setdefault(key, [])
            if value not in values[key]:
                values[key].append(value)
    return values


def find_dmn_file(case_name: str, rule: Dict[str, Any], dmn_dir: Path) -> Optional[Path]:
    if not dmn_dir.exists():
        return None
    resource = str(rule.get("dmn") or "").strip()
    candidates: List[Path] = []
    if resource:
        resource_path = Path(resource)
        candidates.extend([resource_path, dmn_dir / resource, dmn_dir / resource_path.name])
    normalized_case = normalize_name(case_name)
    for path in dmn_dir.glob("*.dmn"):
        if normalize_name(path.stem) == normalized_case:
            candidates.append(path)
    for path in dmn_dir.glob("*.dmn"):
        if normalized_case and normalized_case in normalize_name(path.stem):
            candidates.append(path)
    for path in candidates:
        if path.exists():
            return path.resolve()
    return None


def matching_branch_value(value: Any, candidates: List[Any]) -> Any:
    normalized_value = normalize_literal(value)
    for candidate in candidates:
        if normalize_literal(candidate) == normalized_value:
            return candidate
    return value


def dmn_output_variants_for_rule(
    case_name: str,
    rule: Dict[str, Any],
    dmn_dir: Path,
    branch_values: Dict[str, List[Any]],
) -> List[Dict[str, Any]]:
    dmn_file = find_dmn_file(case_name, rule, dmn_dir)
    if not dmn_file:
        return []
    decisions = parse_dmn(dmn_file)
    decision_id = str(rule.get("decision") or "")
    decision = decisions.get(decision_id)
    mapped_output_norms = {
        normalize_name(item.get("dmn_param"))
        for item in rule.get("output_mapping", []) or []
        if item.get("dmn_param")
    }
    if decision is None and decisions:
        decision = next(
            (
                item
                for item in decisions.values()
                if mapped_output_norms.issubset({normalize_name(output) for output in item.outputs})
            ),
            None,
        )
    if decision is None and decisions:
        decision = next(iter(decisions.values()))
    if decision is None:
        return []
    mapped_outputs = {normalize_name(item.get("dmn_param")): item.get("dmn_param") for item in rule.get("output_mapping", []) or []}
    variants: List[Dict[str, Any]] = []
    for dmn_rule in decision.rules:
        outputs: Dict[str, Any] = {}
        for output_name, value in dmn_rule.outputs.items():
            mapped_name = mapped_outputs.get(normalize_name(output_name), output_name)
            outputs[mapped_name] = matching_branch_value(value, branch_values.get(normalize_name(mapped_name), []))
        if outputs:
            variants.append(outputs)
    return unique_values(variants)


def output_variants_for_rule(
    rule: Dict[str, Any],
    branch_values: Dict[str, List[Any]],
    *,
    case_name: str,
    dmn_dir: Path,
) -> List[Dict[str, Any]]:
    dmn_variants = dmn_output_variants_for_rule(case_name, rule, dmn_dir, branch_values)
    if dmn_variants:
        return dmn_variants

    variants: List[Dict[str, Any]] = [{}]
    for mapping in rule.get("output_mapping", []) or []:
        param = mapping.get("dmn_param")
        global_name = mapping.get("global")
        candidates = (
            branch_values.get(normalize_name(global_name))
            or branch_values.get(normalize_name(param))
            or [sample_value(param or global_name or "output", "string")]
        )
        next_variants = []
        for base in variants:
            for value in candidates:
                item = dict(base)
                item[param] = value
                next_variants.append(item)
        variants = next_variants
    return variants or [{}]


def build_step_variants(model: Dict[str, Any], case_name: str, dmn_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    variants: Dict[str, List[Dict[str, Any]]] = {}
    branch_values = collect_branch_values_by_global(model)
    for message in model.get("messages", []):
        variants[message["name"]] = []
        for payload in schema_payload_variants(message, branch_values):
            variants[message["name"]].append({
                "type": "message",
                "element": message["name"],
                "payload": payload,
            })
    for gateway in model.get("gateways", []):
        variants[gateway["name"]] = [{"type": "gateway", "element": gateway["name"]}]
    for event in model.get("events", []):
        variants[event["name"]] = [{"type": "event", "element": event["name"]}]
    for rule in model.get("businessrules", []):
        variants[rule["name"]] = [
            {
                "type": "businessrule",
                "element": rule["name"],
                "outputs": outputs,
            }
            for outputs in output_variants_for_rule(rule, branch_values, case_name=case_name, dmn_dir=dmn_dir)
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
    dmn_dir: Path,
) -> List[Dict[str, Any]]:
    root = DSLSimulator(model, case_name)
    variants = build_step_variants(model, case_name, dmn_dir)
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
    parser.add_argument("--dmn-dir", default=str(DEFAULT_DMN_DIR), help="Directory containing source DMN files")
    parser.add_argument("--max-depth", type=int, default=64)
    parser.add_argument("--max-paths", type=int, default=1000)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    model = load_model(model_path)
    case_name = args.case_name or str(model.get("contract_name") or model_path.stem)
    paths = enumerate_paths(model, case_name, args.max_depth, args.max_paths, Path(args.dmn_dir).resolve())
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
