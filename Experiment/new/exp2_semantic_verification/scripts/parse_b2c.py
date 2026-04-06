#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from textx import metamodel_from_file

from common import GRAMMAR_PATH, dump_json


def _literal_value(node: Any) -> Any:
    if node is None:
        return None
    for attr in ("stringValue", "intValue", "boolValue"):
        value = getattr(node, attr, None)
        if value is not None:
            return value
    return None


def _participant_attributes(participant: Any) -> Dict[str, str]:
    return {
        getattr(attr, "key", ""): (getattr(attr, "value", "") or "").strip('"')
        for attr in (getattr(participant, "attributes", None) or [])
    }


def _action_to_json(action: Any) -> Dict[str, Any]:
    kind = action.__class__.__name__
    if kind == "EnableAction":
        return {"kind": "enable", "target": getattr(getattr(action, "target", None), "name", None)}
    if kind == "DisableAction":
        return {"kind": "disable", "target": getattr(getattr(action, "target", None), "name", None)}
    if kind == "SetGlobalAction":
        return {
            "kind": "set",
            "target": getattr(getattr(action, "var", None), "name", None),
            "value": _literal_value(getattr(action, "expr", None)),
        }
    return {"kind": kind, "target": None}


def _branch_to_json(branch: Any) -> Dict[str, Any]:
    branch_type = branch.__class__.__name__
    payload: Dict[str, Any] = {
        "kind": branch_type,
        "actions": [_action_to_json(action) for action in getattr(branch, "actions", [])],
    }
    if branch_type == "GatewayCompareBranch":
        payload.update(
            {
                "condition_kind": "compare",
                "var": getattr(getattr(branch, "var", None), "name", None),
                "relation": getattr(branch, "relation", None),
                "value": _literal_value(getattr(branch, "value", None)),
            }
        )
    elif branch_type == "GatewayExpressionBranch":
        payload.update({"condition_kind": "expression", "expr": getattr(branch, "expr", None)})
    else:
        payload.update({"condition_kind": "else"})
    return payload


def _flow_to_json(item: Any) -> Dict[str, Any]:
    kind = item.__class__.__name__
    if kind == "StartFlow":
        return {
            "kind": "start_flow",
            "trigger": {"type": "start", "name": getattr(getattr(item, "start", None), "name", None), "state": "ready"},
            "conditions": [],
            "actions": [{"kind": "enable", "target": getattr(getattr(getattr(item, "target", None), "target", None), "name", None)}],
        }
    if kind == "MessageFlow":
        return {
            "kind": "message_flow",
            "trigger": {"type": "message", "name": getattr(getattr(item, "msg", None), "name", None), "state": getattr(item, "msgCond", None)},
            "conditions": [],
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    if kind == "GatewayFlow":
        branches = [_branch_to_json(branch) for branch in getattr(item, "branches", [])]
        return {
            "kind": "gateway_flow",
            "trigger": {"type": "gateway", "name": getattr(getattr(item, "gtw", None), "name", None), "state": "completed"},
            "conditions": branches,
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    if kind == "RuleFlow":
        return {
            "kind": "rule_flow",
            "trigger": {"type": "businessrule", "name": getattr(getattr(item, "rule", None), "name", None), "state": getattr(item, "ruleCond", None)},
            "conditions": [],
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    if kind == "EventFlow":
        return {
            "kind": "event_flow",
            "trigger": {"type": "event", "name": getattr(getattr(item, "ev", None), "name", None), "state": "completed"},
            "conditions": [],
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    if kind == "OracleTaskFlow":
        return {
            "kind": "oracle_flow",
            "trigger": {"type": "oracletask", "name": getattr(getattr(item, "task", None), "name", None), "state": "done"},
            "conditions": [],
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    if kind == "ParallelJoin":
        return {
            "kind": "parallel_join",
            "trigger": {"type": "parallel", "name": getattr(getattr(item, "gtw", None), "name", None), "state": "await"},
            "conditions": [{"condition_kind": "await_all", "sources": [getattr(source, "name", None) for source in getattr(item, "sources", [])]}],
            "actions": [_action_to_json(action) for action in getattr(item, "actions", [])],
        }
    return {"kind": kind, "trigger": {"type": "unknown", "name": None, "state": None}, "conditions": [], "actions": []}


def parse_b2c_model(b2c_path: Path) -> Dict[str, Any]:
    metamodel = metamodel_from_file(str(GRAMMAR_PATH))
    model = metamodel.model_from_file(str(b2c_path))
    contracts = getattr(model, "contracts", None) or []
    if not contracts:
        raise ValueError(f"No contract found in {b2c_path}")
    contract = contracts[0]

    participants: List[Dict[str, Any]] = []
    globals_section: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    gateways: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    businessrules: List[Dict[str, Any]] = []
    oracletasks: List[Dict[str, Any]] = []
    flows: List[Dict[str, Any]] = []

    for section in getattr(contract, "sections", []):
        section_type = section.__class__.__name__
        if section_type == "ParticipantSection":
            for participant in getattr(section, "participants", []):
                attrs = _participant_attributes(participant)
                participants.append(
                    {
                        "name": participant.name,
                        "msp": getattr(participant, "msp", None),
                        "x509": getattr(participant, "x509", None),
                        "is_multi": getattr(participant, "isMulti", None),
                        "multi_min": getattr(participant, "multiMin", None),
                        "multi_max": getattr(participant, "multiMax", None),
                        "role": attrs.get("role"),
                        "attributes": attrs,
                    }
                )
        elif section_type == "GlobalSection":
            for item in getattr(section, "globals", []):
                globals_section.append({"name": item.name, "type": item.type})
        elif section_type == "MessageSection":
            for item in getattr(section, "messages", []):
                messages.append(
                    {
                        "name": item.name,
                        "from": getattr(getattr(item, "sender", None), "name", None),
                        "to": getattr(getattr(item, "receiver", None), "name", None),
                        "initial_state": getattr(item, "initialState", None),
                        "schema": getattr(item, "schema", None),
                    }
                )
        elif section_type == "GatewaySection":
            for item in getattr(section, "gateways", []):
                gateways.append(
                    {
                        "name": item.name,
                        "type": getattr(item, "gatewayType", None),
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_type == "EventSection":
            for item in getattr(section, "events", []):
                events.append({"name": item.name, "initial_state": getattr(item, "initialState", None)})
        elif section_type == "BusinessRuleSection":
            for item in getattr(section, "rules", []):
                businessrules.append(
                    {
                        "name": item.name,
                        "dmn": getattr(item, "dmnResource", None),
                        "decision": getattr(item, "decisionID", None),
                        "input_mapping": [
                            {
                                "dmn_param": getattr(mapping, "dmnParam", None),
                                "global": getattr(getattr(mapping, "globalRef", None), "name", None),
                            }
                            for mapping in getattr(item, "inputMappings", [])
                        ],
                        "output_mapping": [
                            {
                                "dmn_param": getattr(mapping, "dmnParam", None),
                                "global": getattr(getattr(mapping, "globalRef", None), "name", None),
                            }
                            for mapping in getattr(item, "outputMappings", [])
                        ],
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_type == "OracleTaskSection":
            for item in getattr(section, "tasks", []):
                oracletasks.append(
                    {
                        "name": item.name,
                        "type": getattr(item, "oracleType", None),
                        "data_source": getattr(item, "dataSource", None),
                        "compute_script": getattr(item, "computeScript", None),
                        "output_mapping": [
                            {
                                "dmn_param": getattr(mapping, "dmnParam", None),
                                "global": getattr(getattr(mapping, "globalRef", None), "name", None),
                            }
                            for mapping in getattr(item, "outputMappings", [])
                        ],
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_type == "FlowSection":
            for item in getattr(section, "flowItems", []):
                flows.append(_flow_to_json(item))

    return {
        "contract_name": contract.name,
        "source_file": str(b2c_path),
        "participants": participants,
        "globals": globals_section,
        "messages": messages,
        "gateways": gateways,
        "events": events,
        "businessrules": businessrules,
        "oracletasks": oracletasks,
        "flows": flows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse B2CDSL into normalized JSON.")
    parser.add_argument("--input", required=True, help="Path to .b2c file.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    args = parser.parse_args()

    payload = parse_b2c_model(Path(args.input).resolve())
    dump_json(Path(args.output).resolve(), payload)


if __name__ == "__main__":
    main()
