#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Set

from common import dump_json, load_json
from parse_b2c import parse_b2c_model


def load_model(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return parse_b2c_model(path)


def initial_ready_events(model: Dict[str, Any]) -> Set[str]:
    return {
        item["name"]
        for item in model.get("events", [])
        if str(item.get("initial_state") or "").upper() == "READY"
    }


def auto_parallel_gateways(model: Dict[str, Any]) -> Set[str]:
    return {
        str((flow.get("trigger") or {}).get("name"))
        for flow in model.get("flows", [])
        if flow.get("kind") == "parallel_join" and (flow.get("trigger") or {}).get("name")
    }


def clean_step(step: Dict[str, Any], *, platform: str) -> Dict[str, Any]:
    item = {
        "type": step.get("type"),
        "element": step.get("element"),
    }
    if step.get("payload") is not None:
        item["payload"] = step.get("payload")
    if platform == "dsl" and step.get("outputs") is not None:
        item["outputs"] = step.get("outputs")
    if platform == "solidity" and step.get("continue_payload") is not None:
        item["continue_payload"] = step.get("continue_payload")
    return item


def materialize_dsl_case(logical: Dict[str, Any], model: Dict[str, Any], source_b2c: Path) -> Dict[str, Any]:
    skip_events = initial_ready_events(model)
    skip_gateways = auto_parallel_gateways(model)
    steps: List[Dict[str, Any]] = []
    for step in logical.get("steps", []):
        element = str(step.get("element") or "")
        step_type = str(step.get("type") or "")
        if step_type == "event" and element in skip_events:
            continue
        if step_type == "gateway" and element in skip_gateways:
            continue
        steps.append(clean_step(step, platform="dsl"))

    return {
        "case_name": logical.get("case_name"),
        "description": logical.get("description", ""),
        "source_b2c": str(source_b2c),
        "paths": [
            {
                "path_name": logical.get("path_name", "logical_path"),
                "expect": logical.get("expect", "accepted"),
                "steps": steps,
            }
        ],
    }


def materialize_solidity_sequence(logical: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "steps": [
            clean_step(step, platform="solidity")
            for step in logical.get("steps", [])
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize one logical exp3 path into platform-specific inputs.")
    parser.add_argument("--logical-path", required=True, help="Platform-independent logical path JSON")
    parser.add_argument("--model", required=True, help="Path to .b2c or parsed dsl_model.json")
    parser.add_argument("--dsl-case-output", required=True, help="Output path for DSL case.json")
    parser.add_argument("--solidity-sequence-output", required=True, help="Output path for Solidity execution sequence JSON")
    args = parser.parse_args()

    logical = load_json(Path(args.logical_path).resolve())
    model_path = Path(args.model).resolve()
    model = load_model(model_path)
    dump_json(Path(args.dsl_case_output), materialize_dsl_case(logical, model, model_path))
    dump_json(Path(args.solidity_sequence_output), materialize_solidity_sequence(logical))
    print(f"Wrote DSL case: {args.dsl_case_output}")
    print(f"Wrote Solidity sequence: {args.solidity_sequence_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
