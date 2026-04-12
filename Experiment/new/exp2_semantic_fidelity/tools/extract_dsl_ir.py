#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from textx import metamodel_from_file

from tools.common import GRAMMAR_PATH, dump_json
from tools.normalize_ir import canonical_trigger, infer_event_type, normalize_action


def literal_value(node: Any) -> Any:
    if node is None:
        return None
    for attr in ("stringValue", "intValue", "boolValue"):
        value = getattr(node, attr, None)
        if value is not None:
            return value
    return None


def action_to_ir(action: Any) -> dict[str, Any]:
    kind = action.__class__.__name__
    if kind == "EnableAction":
        return normalize_action("enable", getattr(getattr(action, "target", None), "name", None))
    if kind == "DisableAction":
        return normalize_action("disable", getattr(getattr(action, "target", None), "name", None))
    if kind == "SetGlobalAction":
        value = literal_value(getattr(action, "expr", None))
        return normalize_action("set", var=getattr(getattr(action, "var", None), "name", None), value=repr(value))
    return {"op": kind}


def branch_to_ir(branch: Any) -> dict[str, Any]:
    name = branch.__class__.__name__
    payload = {"kind": name, "actions": [action_to_ir(action) for action in getattr(branch, "actions", [])]}
    if name == "GatewayCompareBranch":
        payload["condition"] = {
            "kind": "compare",
            "var": getattr(getattr(branch, "var", None), "name", None),
            "relation": getattr(branch, "relation", None),
            "value": literal_value(getattr(branch, "value", None)),
        }
    elif name == "GatewayExpressionBranch":
        payload["condition"] = {"kind": "expression", "expr": getattr(branch, "expr", None)}
    else:
        payload["condition"] = {"kind": "else"}
    return payload


def flow_to_ir(flow: Any, index: int) -> dict[str, Any]:
    kind = flow.__class__.__name__
    if kind == "StartFlow":
        target = getattr(getattr(flow, "target", None), "target", None)
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("event", getattr(getattr(flow, "start", None), "name", ""), "start"),
            "actions": [normalize_action("enable", getattr(target, "name", None))],
            "branches": [],
        }
    if kind == "MessageFlow":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("message", getattr(getattr(flow, "msg", None), "name", ""), getattr(flow, "msgCond", None)),
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [],
        }
    if kind == "GatewayFlow":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("gateway", getattr(getattr(flow, "gtw", None), "name", "")),
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [branch_to_ir(branch) for branch in getattr(flow, "branches", [])],
        }
    if kind == "RuleFlow":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("businessrule", getattr(getattr(flow, "rule", None), "name", ""), getattr(flow, "ruleCond", None)),
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [],
        }
    if kind == "OracleTaskFlow":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("oracletask", getattr(getattr(flow, "task", None), "name", ""), "done"),
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [],
        }
    if kind == "EventFlow":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": canonical_trigger("event", getattr(getattr(flow, "ev", None), "name", ""), "completed"),
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [],
        }
    if kind == "ParallelJoin":
        return {
            "id": f"flow_{index:03d}",
            "source_kind": kind,
            "trigger": {
                "kind": "parallel_join",
                "name": getattr(getattr(flow, "gtw", None), "name", ""),
                "sources": [getattr(source, "name", None) for source in getattr(flow, "sources", [])],
            },
            "actions": [action_to_ir(action) for action in getattr(flow, "actions", [])],
            "branches": [],
        }
    return {"id": f"flow_{index:03d}", "source_kind": kind, "trigger": {"kind": "unknown"}, "actions": [], "branches": []}


def parse_dsl(path: Path) -> dict[str, Any]:
    mm = metamodel_from_file(str(GRAMMAR_PATH))
    model = mm.model_from_file(str(path))
    contract = model.contracts[0]

    participants: list[dict[str, Any]] = []
    globals_ir: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    gateways: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    businessrules: list[dict[str, Any]] = []
    oracletasks: list[dict[str, Any]] = []
    flows: list[dict[str, Any]] = []

    for section in getattr(contract, "sections", []):
        section_name = section.__class__.__name__
        if section_name == "ParticipantSection":
            for item in getattr(section, "participants", []):
                participants.append(
                    {
                        "name": item.name,
                        "msp": getattr(item, "msp", None),
                        "x509": getattr(item, "x509", None),
                        "is_multi": getattr(item, "isMulti", None),
                        "multi_min": getattr(item, "multiMin", None),
                        "multi_max": getattr(item, "multiMax", None),
                        "attributes": {
                            attr.key: (attr.value or "").strip('"')
                            for attr in getattr(item, "attributes", []) or []
                        },
                    }
                )
        elif section_name == "GlobalSection":
            for item in getattr(section, "globals", []):
                globals_ir.append({"name": item.name, "type": item.type, "initial_value": None})
        elif section_name == "MessageSection":
            for item in getattr(section, "messages", []):
                messages.append(
                    {
                        "name": item.name,
                        "from": getattr(getattr(item, "sender", None), "name", None),
                        "to": getattr(getattr(item, "receiver", None), "name", None),
                        "payload": getattr(item, "schema", None),
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "GatewaySection":
            for item in getattr(section, "gateways", []):
                gateways.append({"name": item.name, "type": getattr(item, "gatewayType", None), "initial_state": getattr(item, "initialState", None)})
        elif section_name == "EventSection":
            for item in getattr(section, "events", []):
                events.append({"name": item.name, "type": infer_event_type(item.name), "initial_state": getattr(item, "initialState", None)})
        elif section_name == "BusinessRuleSection":
            for item in getattr(section, "rules", []):
                businessrules.append(
                    {
                        "name": item.name,
                        "referenced_dmn": getattr(item, "dmnResource", None),
                        "decision": getattr(item, "decisionID", None),
                        "input_mapping": [
                            {"param": mapping.dmnParam, "global": getattr(getattr(mapping, "globalRef", None), "name", None)}
                            for mapping in getattr(item, "inputMappings", [])
                        ],
                        "output_mapping": [
                            {"param": mapping.dmnParam, "global": getattr(getattr(mapping, "globalRef", None), "name", None)}
                            for mapping in getattr(item, "outputMappings", [])
                        ],
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "OracleTaskSection":
            for item in getattr(section, "tasks", []):
                oracletasks.append(
                    {
                        "name": item.name,
                        "type": getattr(item, "oracleType", None),
                        "data_source": getattr(item, "dataSource", None),
                        "compute_script": getattr(item, "computeScript", None),
                        "output_mapping": [
                            {"param": mapping.dmnParam, "global": getattr(getattr(mapping, "globalRef", None), "name", None)}
                            for mapping in getattr(item, "outputMappings", [])
                        ],
                    }
                )
        elif section_name == "FlowSection":
            for idx, item in enumerate(getattr(section, "flowItems", []), start=len(flows) + 1):
                flows.append(flow_to_ir(item, idx))

    return {
        "contract": contract.name,
        "source_file": str(path),
        "participants": participants,
        "globals": globals_ir,
        "messages": messages,
        "events": events,
        "gateways": gateways,
        "businessrules": businessrules,
        "oracletasks": oracletasks,
        "flows": flows,
        "unsupported": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract normalized DSL IR from B2CDSL.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dump_json(Path(args.output), parse_dsl(Path(args.input).resolve()))


if __name__ == "__main__":
    main()

