#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from textx import metamodel_from_file

from common import GRAMMAR_PATH, python_path_setup


python_path_setup()


def _literal_value(node: Any, source_text: str) -> Any:
    if node is None:
        return None
    start = getattr(node, "_tx_position", None)
    end = getattr(node, "_tx_position_end", None)
    if start is None or end is None:
        return None
    raw = source_text[start:end].strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw == "true":
        return True
    if raw == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def _action_to_json(action: Any, source_text: str) -> Dict[str, Any]:
    kind = action.__class__.__name__
    if kind == "EnableAction":
        return {"kind": "enable", "target": getattr(getattr(action, "target", None), "name", None)}
    if kind == "DisableAction":
        return {"kind": "disable", "target": getattr(getattr(action, "target", None), "name", None)}
    if kind == "SetGlobalAction":
        return {
            "kind": "set",
            "target": getattr(getattr(action, "var", None), "name", None),
            "value": _literal_value(getattr(action, "expr", None), source_text),
        }
    return {"kind": kind, "target": None}


def _branch_to_json(branch: Any, source_text: str) -> Dict[str, Any]:
    branch_type = branch.__class__.__name__
    payload: Dict[str, Any] = {
        "kind": branch_type,
        "actions": [_action_to_json(action, source_text) for action in getattr(branch, "actions", [])],
    }
    if branch_type == "GatewayCompareBranch":
        payload.update(
            {
                "condition_kind": "compare",
                "var": getattr(getattr(branch, "var", None), "name", None),
                "relation": getattr(branch, "relation", None),
                "value": _literal_value(getattr(branch, "value", None), source_text),
            }
        )
    elif branch_type == "GatewayExpressionBranch":
        payload.update({"condition_kind": "expression", "expr": getattr(branch, "expr", None)})
    else:
        payload.update({"condition_kind": "else"})
    return payload


def _flow_to_json(item: Any, source_text: str) -> Dict[str, Any]:
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
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    if kind == "GatewayFlow":
        return {
            "kind": "gateway_flow",
            "trigger": {"type": "gateway", "name": getattr(getattr(item, "gtw", None), "name", None), "state": "completed"},
            "conditions": [_branch_to_json(branch, source_text) for branch in getattr(item, "branches", [])],
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    if kind == "RuleFlow":
        return {
            "kind": "rule_flow",
            "trigger": {"type": "businessrule", "name": getattr(getattr(item, "rule", None), "name", None), "state": getattr(item, "ruleCond", None)},
            "conditions": [],
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    if kind == "OracleTaskFlow":
        return {
            "kind": "oracle_flow",
            "trigger": {"type": "oracletask", "name": getattr(getattr(item, "task", None), "name", None), "state": "done"},
            "conditions": [],
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    if kind == "EventFlow":
        return {
            "kind": "event_flow",
            "trigger": {"type": "event", "name": getattr(getattr(item, "ev", None), "name", None), "state": "completed"},
            "conditions": [],
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    if kind == "ParallelJoin":
        return {
            "kind": "parallel_join",
            "trigger": {"type": "parallel", "name": getattr(getattr(item, "gtw", None), "name", None), "state": "await"},
            "conditions": [{"condition_kind": "await_all", "sources": [getattr(source, "name", None) for source in getattr(item, "sources", [])]}],
            "actions": [_action_to_json(action, source_text) for action in getattr(item, "actions", [])],
        }
    return {"kind": kind, "trigger": {"type": "unknown", "name": None, "state": None}, "conditions": [], "actions": []}


def parse_b2c_model(b2c_path: Path) -> Dict[str, Any]:
    source_text = b2c_path.read_text(encoding="utf-8")
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
                participants.append(
                    {
                        "name": participant.name,
                        "msp": getattr(participant, "msp", None),
                        "x509": getattr(participant, "x509", None),
                        "is_multi": getattr(participant, "isMulti", None),
                        "multi_min": getattr(participant, "multiMin", None),
                        "multi_max": getattr(participant, "multiMax", None),
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
                flows.append(_flow_to_json(item, source_text))

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
