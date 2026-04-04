from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
EXP1_ROOT = SCRIPT_DIR.parent
CHAINCOLLAB_ROOT = EXP1_ROOT.parent.parent.parent
NEW_TRANSLATOR_ROOT = CHAINCOLLAB_ROOT / "src" / "newTranslator"
NEW_TRANSLATOR_PYTHON = NEW_TRANSLATOR_ROOT / ".venv" / "bin" / "python"

if str(NEW_TRANSLATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(NEW_TRANSLATOR_ROOT))

from generator.parser.choreography_parser.elements import EdgeType, NodeType  # noqa: E402
from generator.parser.choreography_parser.parser import Choreography  # noqa: E402
from generator.parser.dmn_parser.parser import DMNParser  # noqa: E402
from textx import metamodel_from_file  # noqa: E402


BPMN_NS = {"bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
GRAMMAR_PATH = NEW_TRANSLATOR_ROOT / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"

_B2C_METAMODEL = None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def dump_text(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def generate_b2c_with_newtranslator(
    bpmn_path: Path,
    output_path: Path,
    contract_name: Optional[str] = None,
) -> Path:
    ensure_parent(output_path)
    command = [
        str(NEW_TRANSLATOR_PYTHON),
        "-m",
        "generator.bpmn_to_dsl",
        str(bpmn_path),
        "-o",
        str(output_path),
    ]
    if contract_name:
        command.extend(["-n", contract_name])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(NEW_TRANSLATOR_ROOT)
    result = subprocess.run(
        command,
        cwd=str(NEW_TRANSLATOR_ROOT),
        text=True,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"newTranslator generation failed for {bpmn_path}:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return output_path


def normalize_text(value: Optional[str], fallback: Optional[str] = None) -> str:
    text = (value or "").strip()
    if not text and fallback:
        text = str(fallback).strip()
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = re.sub(r"[\s\-_/]+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_identifier(value: Optional[str]) -> str:
    text = unicodedata.normalize("NFKC", (value or "").strip())
    text = re.sub(r"[^\w]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def safe_json_loads(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def infer_case_name(path: Path) -> str:
    return path.stem


def _load_b2c_metamodel():
    global _B2C_METAMODEL
    if _B2C_METAMODEL is None:
        _B2C_METAMODEL = metamodel_from_file(str(GRAMMAR_PATH))
    return _B2C_METAMODEL


def _first(iterable: Iterable[Any]) -> Any:
    for item in iterable:
        return item
    return None


def parse_dmn_metadata(dmn_path: Optional[Path]) -> Dict[str, Any]:
    if not dmn_path or not dmn_path.exists():
        return {"path": None, "decisions": [], "main_decision": None}
    parser = DMNParser.load_from_xml_string(dmn_path.read_text(encoding="utf-8"))
    decisions = []
    for decision in parser.get_all_decisions():
        decisions.append(
            {
                "id": decision._id,
                "name": decision._name,
                "inputs": [item._asdict() for item in decision.inputs],
                "outputs": [item._asdict() for item in decision.outputs],
                "is_main": getattr(decision, "is_main", False),
            }
        )
    main_decision = _first([item for item in decisions if item.get("is_main")]) or _first(decisions)
    return {
        "path": str(dmn_path),
        "file_name": dmn_path.name,
        "decisions": decisions,
        "main_decision": main_decision,
    }


def parse_bpmn_file(
    bpmn_path: Path,
    dmn_path: Optional[Path] = None,
    case_name: Optional[str] = None,
) -> Dict[str, Any]:
    choreography = Choreography()
    choreography.load_diagram_from_xml_file(str(bpmn_path))

    root = ET.parse(bpmn_path).getroot()
    participants = []
    participant_names: Dict[str, str] = {}
    for node in choreography.query_element_with_type(NodeType.PARTICIPANT):
        participant = {
            "id": node.id,
            "name": node.name or node.id,
        }
        participants.append(participant)
        participant_names[node.id] = participant["name"]

    messages_by_id = {
        node.id: node for node in choreography.query_element_with_type(NodeType.MESSAGE)
    }
    messages = []
    for edge in choreography.query_element_with_type(EdgeType.MESSAGE_FLOW):
        message = messages_by_id.get(edge.message.id if edge.message else None)
        documentation = safe_json_loads(getattr(message, "documentation", ""))
        messages.append(
            {
                "id": edge.id,
                "messageRef": message.id if message else None,
                "name": (message.name if message and message.name else (message.id if message else edge.id)),
                "sourceRef": edge.source.id,
                "targetRef": edge.target.id,
                "sender": participant_names.get(edge.source.id, edge.source.id),
                "receiver": participant_names.get(edge.target.id, edge.target.id),
                "schema": documentation if documentation else {},
            }
        )

    gateway_type_map = {
        NodeType.EXCLUSIVE_GATEWAY: "exclusive",
        NodeType.EVENT_BASED_GATEWAY: "event",
        NodeType.PARALLEL_GATEWAY: "parallel",
    }
    gateways = []
    for gateway_type, normalized_type in gateway_type_map.items():
        for node in choreography.query_element_with_type(gateway_type):
            gateways.append(
                {
                    "id": node.id,
                    "name": node.name or node.id,
                    "type": normalized_type,
                }
            )

    events = []
    for node in choreography.query_element_with_type(NodeType.START_EVENT):
        events.append(
            {
                "id": node.id,
                "name": node.name or node.id,
                "kind": "start",
            }
        )
    for node in choreography.query_element_with_type(NodeType.END_EVENT):
        events.append(
            {
                "id": node.id,
                "name": node.name or node.id,
                "kind": "end",
            }
        )

    dmn_metadata = parse_dmn_metadata(dmn_path)
    businessrules = []
    for task in root.findall(".//bpmn2:businessRuleTask", BPMN_NS):
        task_id = task.attrib["id"]
        task_name = task.attrib.get("name") or task_id
        documentation = safe_json_loads(_first_text(task, "./bpmn2:documentation"))
        input_mapping = documentation.get("input_mapping") or documentation.get("inputMapping") or documentation.get("inputs") or []
        output_mapping = documentation.get("output_mapping") or documentation.get("outputMapping") or documentation.get("outputs") or []

        explicit_dmn = documentation.get("dmn")
        explicit_decision = documentation.get("decision")
        inferred_main_decision = dmn_metadata.get("main_decision") or {}

        businessrules.append(
            {
                "id": task_id,
                "name": task_name,
                "dmn": explicit_dmn,
                "decision": explicit_decision,
                "input_mapping": input_mapping,
                "output_mapping": output_mapping,
                "dmn_inference": {
                    "path": dmn_metadata.get("file_name"),
                    "decision_id": inferred_main_decision.get("id"),
                    "decision_name": inferred_main_decision.get("name"),
                    "used_inference": not bool(explicit_dmn or explicit_decision),
                },
            }
        )

    flows = []
    for edge in choreography.query_element_with_type(EdgeType.SEQUENCE_FLOW):
        flows.append(
            {
                "id": edge.id,
                "sourceRef": edge.source.id,
                "targetRef": edge.target.id,
                "type": "sequenceFlow",
                "trigger_hint": edge.name or getattr(edge, "condition_expression", "") or "",
            }
        )

    return {
        "case_name": case_name or infer_case_name(bpmn_path),
        "source_files": {
            "bpmn": str(bpmn_path),
            "dmn": str(dmn_path) if dmn_path else None,
        },
        "participants": participants,
        "messages": messages,
        "gateways": gateways,
        "events": events,
        "businessrules": businessrules,
        "flows": flows,
        "dmn_metadata": dmn_metadata,
    }


def _first_text(element: ET.Element, xpath: str) -> str:
    found = element.findall(xpath, BPMN_NS)
    if not found:
        return ""
    return found[0].text or ""


def _quote_literal(literal: Any) -> str:
    if hasattr(literal, "stringValue") and getattr(literal, "stringValue") is not None:
        return getattr(literal, "stringValue")
    if hasattr(literal, "intValue") and getattr(literal, "intValue") is not None:
        return str(getattr(literal, "intValue"))
    if hasattr(literal, "boolValue") and getattr(literal, "boolValue") is not None:
        return "true" if getattr(literal, "boolValue") else "false"
    return ""


def _action_to_json(action: Any) -> Dict[str, Any]:
    cls_name = action.__class__.__name__
    if cls_name == "EnableAction":
        target_name = getattr(getattr(action, "target", None), "name", None)
        return {"kind": "enable", "target": target_name}
    if cls_name == "DisableAction":
        target_name = getattr(getattr(action, "target", None), "name", None)
        return {"kind": "disable", "target": target_name}
    if cls_name == "SetGlobalAction":
        expr = _quote_literal(getattr(action, "expr", None))
        var_name = getattr(getattr(action, "var", None), "name", None)
        return {"kind": "set", "target": var_name, "value": expr}
    return {"kind": cls_name, "target": None}


def _render_action(action: Dict[str, Any]) -> str:
    if action["kind"] == "enable":
        return f"enable {action['target']}"
    if action["kind"] == "disable":
        return f"disable {action['target']}"
    if action["kind"] == "set":
        return f"set {action['target']} = {action.get('value', '')}"
    return action["kind"]


def _flow_item_to_json(item: Any) -> Dict[str, Any]:
    cls_name = item.__class__.__name__
    actions = [_action_to_json(action) for action in getattr(item, "actions", [])]
    if cls_name == "StartFlow":
        trigger_name = getattr(getattr(item, "start", None), "name", None)
        target_name = getattr(getattr(getattr(item, "target", None), "target", None), "name", None)
        raw = f"start event {trigger_name} enables {target_name};"
        return {
            "kind": "start_flow",
            "trigger_type": "start",
            "trigger_name": trigger_name,
            "trigger_state": "ready",
            "actions": [{"kind": "enable", "target": target_name}],
            "raw_text": raw,
        }
    if cls_name == "MessageFlow":
        trigger_name = getattr(getattr(item, "msg", None), "name", None)
        trigger_state = getattr(item, "msgCond", None)
        raw = f"when message {trigger_name} {trigger_state} then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "message_flow",
            "trigger_type": "message",
            "trigger_name": trigger_name,
            "trigger_state": trigger_state,
            "actions": actions,
            "raw_text": raw,
        }
    if cls_name == "GatewayFlow":
        trigger_name = getattr(getattr(item, "gtw", None), "name", None)
        branches = []
        for branch in getattr(item, "branches", []):
            branch_actions = [_action_to_json(action) for action in getattr(branch, "actions", [])]
            entry: Dict[str, Any] = {"actions": branch_actions}
            branch_cls = branch.__class__.__name__
            if branch_cls == "GatewayCompareBranch":
                entry.update(
                    {
                        "condition_kind": "compare",
                        "var": getattr(getattr(branch, "var", None), "name", None),
                        "relation": getattr(branch, "relation", None),
                        "value": _quote_literal(getattr(branch, "value", None)),
                    }
                )
            elif branch_cls == "GatewayExpressionBranch":
                entry.update({"condition_kind": "expression", "expr": getattr(branch, "expr", None)})
            else:
                entry.update({"condition_kind": "else"})
            branches.append(entry)
        if branches:
            raw = f"when gateway {trigger_name} completed choose ..."
        else:
            raw = f"when gateway {trigger_name} completed then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "gateway_flow",
            "trigger_type": "gateway",
            "trigger_name": trigger_name,
            "trigger_state": "completed",
            "actions": actions,
            "branches": branches,
            "raw_text": raw,
        }
    if cls_name == "RuleFlow":
        trigger_name = getattr(getattr(item, "rule", None), "name", None)
        trigger_state = getattr(item, "ruleCond", None)
        raw = f"when businessrule {trigger_name} {trigger_state} then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "rule_flow",
            "trigger_type": "businessrule",
            "trigger_name": trigger_name,
            "trigger_state": trigger_state,
            "actions": actions,
            "raw_text": raw,
        }
    if cls_name == "EventFlow":
        trigger_name = getattr(getattr(item, "ev", None), "name", None)
        raw = f"when event {trigger_name} completed then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "event_flow",
            "trigger_type": "event",
            "trigger_name": trigger_name,
            "trigger_state": "completed",
            "actions": actions,
            "raw_text": raw,
        }
    if cls_name == "OracleTaskFlow":
        trigger_name = getattr(getattr(item, "task", None), "name", None)
        raw = f"when oracletask {trigger_name} done then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "oracle_flow",
            "trigger_type": "oracletask",
            "trigger_name": trigger_name,
            "trigger_state": "done",
            "actions": actions,
            "raw_text": raw,
        }
    if cls_name == "ParallelJoin":
        trigger_name = getattr(getattr(item, "gtw", None), "name", None)
        sources = [getattr(source, "name", None) for source in getattr(item, "sources", [])]
        raw = f"parallel gateway {trigger_name} await {', '.join(sources)} then {', '.join(_render_action(action) for action in actions)};"
        return {
            "kind": "parallel_join",
            "trigger_type": "parallel",
            "trigger_name": trigger_name,
            "trigger_state": "await",
            "sources": sources,
            "actions": actions,
            "raw_text": raw,
        }
    return {
        "kind": cls_name,
        "trigger_type": "unknown",
        "trigger_name": None,
        "trigger_state": None,
        "actions": actions,
        "raw_text": cls_name,
    }


def _participant_role(participant: Any) -> Optional[str]:
    for attr in getattr(participant, "attributes", []) or []:
        if getattr(attr, "key", None) == "role":
            return getattr(attr, "value", None)
    return None


def parse_b2c_file(b2c_path: Path, case_name: Optional[str] = None) -> Dict[str, Any]:
    metamodel = _load_b2c_metamodel()
    model = metamodel.model_from_file(str(b2c_path))
    contracts = getattr(model, "contracts", []) or []
    if not contracts:
        raise ValueError(f"No contract found in {b2c_path}")
    contract = contracts[0]

    participants = []
    participant_aliases: Dict[str, List[str]] = {}
    for section in getattr(contract, "sections", []):
        if section.__class__.__name__ != "ParticipantSection":
            continue
        for participant in getattr(section, "participants", []):
            role = _participant_role(participant)
            item = {
                "name": participant.name,
                "msp": getattr(participant, "msp", None),
                "x509": getattr(participant, "x509", None),
                "isMulti": getattr(participant, "isMulti", None),
                "multiMin": getattr(participant, "multiMin", None),
                "multiMax": getattr(participant, "multiMax", None),
                "attributes": [
                    {"key": attr.key, "value": attr.value}
                    for attr in (getattr(participant, "attributes", []) or [])
                ],
                "role": role,
            }
            participants.append(item)
            aliases = [participant.name]
            if role:
                aliases.append(role.strip("\""))
            participant_aliases[participant.name] = aliases

    globals_section = []
    messages = []
    gateways = []
    events = []
    businessrules = []
    flows = []

    for section in getattr(contract, "sections", []):
        section_name = section.__class__.__name__
        if section_name == "GlobalSection":
            globals_section.extend(
                {"name": item.name, "type": item.type}
                for item in getattr(section, "globals", [])
            )
        elif section_name == "MessageSection":
            for item in getattr(section, "messages", []):
                messages.append(
                    {
                        "name": item.name,
                        "sender": getattr(getattr(item, "sender", None), "name", None),
                        "receiver": getattr(getattr(item, "receiver", None), "name", None),
                        "schema": getattr(item, "schema", None),
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "GatewaySection":
            for item in getattr(section, "gateways", []):
                gateways.append(
                    {
                        "name": item.name,
                        "type": getattr(item, "gatewayType", None),
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "EventSection":
            for item in getattr(section, "events", []):
                events.append(
                    {
                        "name": item.name,
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "BusinessRuleSection":
            for item in getattr(section, "rules", []):
                businessrules.append(
                    {
                        "name": item.name,
                        "dmn": getattr(item, "dmnResource", None),
                        "decision": getattr(item, "decisionID", None),
                        "input_mapping": [
                            {
                                "dmnParam": mapping.dmnParam,
                                "globalRef": getattr(getattr(mapping, "globalRef", None), "name", None),
                            }
                            for mapping in getattr(item, "inputMappings", [])
                        ],
                        "output_mapping": [
                            {
                                "dmnParam": mapping.dmnParam,
                                "globalRef": getattr(getattr(mapping, "globalRef", None), "name", None),
                            }
                            for mapping in getattr(item, "outputMappings", [])
                        ],
                        "initial_state": getattr(item, "initialState", None),
                    }
                )
        elif section_name == "FlowSection":
            flows.extend(_flow_item_to_json(item) for item in getattr(section, "flowItems", []))

    return {
        "case_name": case_name or infer_case_name(b2c_path),
        "source_files": {"b2c": str(b2c_path)},
        "contracts": [getattr(contract, "name", None)],
        "participants": participants,
        "globals": globals_section,
        "messages": messages,
        "gateways": gateways,
        "events": events,
        "businessrules": businessrules,
        "flows": flows,
        "participant_aliases": participant_aliases,
    }


def _candidate_names_from_bpmn(item: Dict[str, Any]) -> List[str]:
    values = []
    for key in ("name", "id", "messageRef"):
        if item.get(key):
            values.append(item[key])
    return values


def _find_participant_match(bpmn_item: Dict[str, Any], dsl_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    bpmn_aliases = {normalize_text(bpmn_item.get("name"), bpmn_item.get("id")), normalize_text(bpmn_item.get("id"))}
    for dsl_item in dsl_items:
        aliases = {normalize_text(dsl_item.get("name"))}
        if dsl_item.get("role"):
            aliases.add(normalize_text(dsl_item.get("role")))
        if bpmn_aliases & aliases:
            return dsl_item
    return None


def _find_match(
    bpmn_item: Dict[str, Any],
    dsl_items: List[Dict[str, Any]],
    *,
    dsl_name_key: str = "name",
    extra_alias_keys: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    bpmn_aliases = {normalize_text(value) for value in _candidate_names_from_bpmn(bpmn_item) if value}
    for dsl_item in dsl_items:
        aliases = {normalize_text(dsl_item.get(dsl_name_key))}
        for key in extra_alias_keys or []:
            if dsl_item.get(key):
                aliases.add(normalize_text(dsl_item.get(key)))
        if bpmn_aliases & aliases:
            return dsl_item
    return None


@dataclass
class ValidationRecord:
    contract_type: str
    bpmn_element_type: str
    bpmn_element_id: str
    bpmn_element_name: str
    dsl_node_id: Optional[str]
    passed: bool
    reason: str
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "bpmn_element_type": self.bpmn_element_type,
            "bpmn_element_id": self.bpmn_element_id,
            "bpmn_element_name": self.bpmn_element_name,
            "dsl_node_id": self.dsl_node_id,
            "passed": self.passed,
            "reason": self.reason,
            "severity": self.severity,
        }


def _has_flow_action(flows: List[Dict[str, Any]], target_name: str) -> bool:
    target_normalized = normalize_text(target_name)
    for flow in flows:
        for action in flow.get("actions", []):
            if action.get("kind") == "enable" and normalize_text(action.get("target")) == target_normalized:
                return True
        for branch in flow.get("branches", []):
            for action in branch.get("actions", []):
                if action.get("kind") == "enable" and normalize_text(action.get("target")) == target_normalized:
                    return True
    return False


def _has_trigger_flow(flows: List[Dict[str, Any]], trigger_type: str, trigger_name: str, trigger_states: List[str]) -> bool:
    trigger_name_normalized = normalize_text(trigger_name)
    trigger_states_normalized = {normalize_text(state) for state in trigger_states}
    for flow in flows:
        if normalize_text(flow.get("trigger_type")) != normalize_text(trigger_type):
            continue
        if normalize_text(flow.get("trigger_name")) != trigger_name_normalized:
            continue
        if normalize_text(flow.get("trigger_state")) in trigger_states_normalized:
            return True
    return False


def verify_mapping(bpmn_data: Dict[str, Any], dsl_data: Dict[str, Any]) -> Dict[str, Any]:
    records: List[ValidationRecord] = []
    missing_items: List[Dict[str, Any]] = []
    type_mismatches: List[Dict[str, Any]] = []
    preserved_elements = 0
    exact_matches = 0

    dsl_participants = dsl_data.get("participants", [])
    dsl_messages = dsl_data.get("messages", [])
    dsl_gateways = dsl_data.get("gateways", [])
    dsl_events = dsl_data.get("events", [])
    dsl_businessrules = dsl_data.get("businessrules", [])
    dsl_flows = dsl_data.get("flows", [])

    for participant in bpmn_data.get("participants", []):
        matched = _find_participant_match(participant, dsl_participants)
        if not matched:
            reason = "BPMN participant missing in DSL participants."
            records.append(ValidationRecord("participant_mapping", "participant", participant["id"], participant["name"], None, False, reason))
            missing_items.append(records[-1].to_dict())
            continue
        preserved_elements += 1
        exact_matches += 1
        records.append(
            ValidationRecord(
                "participant_mapping",
                "participant",
                participant["id"],
                participant["name"],
                matched.get("name"),
                True,
                "Participant matched by id/name/role alias.",
                severity="info",
            )
        )

    count_match = len(bpmn_data.get("participants", [])) == len(dsl_participants)
    records.append(
        ValidationRecord(
            "participant_count",
            "participant_group",
            "participants",
            "participants",
            "participants",
            count_match,
            f"BPMN participants={len(bpmn_data.get('participants', []))}, DSL participants={len(dsl_participants)}.",
        )
    )
    if not count_match:
        type_mismatches.append(records[-1].to_dict())

    for message in bpmn_data.get("messages", []):
        matched = _find_match(message, dsl_messages)
        if not matched:
            reason = "BPMN message flow missing corresponding DSL message definition."
            records.append(ValidationRecord("message_mapping", "messageFlow", message["id"], message["name"], None, False, reason))
            missing_items.append(records[-1].to_dict())
            continue
        preserved_elements += 1
        problems = []
        sender_match = normalize_text(matched.get("sender")) == normalize_text(message.get("sourceRef"))
        receiver_match = normalize_text(matched.get("receiver")) == normalize_text(message.get("targetRef"))
        if not sender_match:
            problems.append(f"sender mismatch: BPMN {message.get('sourceRef')} vs DSL {matched.get('sender')}")
        if not receiver_match:
            problems.append(f"receiver mismatch: BPMN {message.get('targetRef')} vs DSL {matched.get('receiver')}")
        if not matched.get("schema"):
            problems.append("DSL message schema missing")
        if not _has_trigger_flow(dsl_flows, "message", matched.get("name"), ["sent", "completed"]):
            problems.append("DSL flows missing message sent/completed trigger")
        if problems:
            records.append(ValidationRecord("message_mapping", "messageFlow", message["id"], message["name"], matched.get("name"), False, "; ".join(problems)))
            type_mismatches.append(records[-1].to_dict())
        else:
            exact_matches += 1
            records.append(ValidationRecord("message_mapping", "messageFlow", message["id"], message["name"], matched.get("name"), True, "Message definition and flow trigger preserved.", severity="info"))

    for gateway in bpmn_data.get("gateways", []):
        matched = _find_match(gateway, dsl_gateways)
        if not matched:
            reason = f'BPMN gateway "{gateway["name"]}" missing in DSL gateways.'
            records.append(ValidationRecord("gateway_mapping", "gateway", gateway["id"], gateway["name"], None, False, reason))
            missing_items.append(records[-1].to_dict())
            continue
        preserved_elements += 1
        if normalize_text(matched.get("type")) != normalize_text(gateway.get("type")):
            reason = f'Gateway type mismatch: BPMN {gateway.get("type")} vs DSL {matched.get("type")}.'
            records.append(ValidationRecord("gateway_mapping", "gateway", gateway["id"], gateway["name"], matched.get("name"), False, reason))
            type_mismatches.append(records[-1].to_dict())
        else:
            exact_matches += 1
            records.append(ValidationRecord("gateway_mapping", "gateway", gateway["id"], gateway["name"], matched.get("name"), True, "Gateway type preserved.", severity="info"))

    for event in bpmn_data.get("events", []):
        matched = _find_match(event, dsl_events)
        if not matched:
            reason = f'BPMN {event["kind"]} event missing in DSL events.'
            records.append(ValidationRecord("event_mapping", "event", event["id"], event["name"], None, False, reason))
            missing_items.append(records[-1].to_dict())
            continue
        preserved_elements += 1
        problems = []
        if event["kind"] == "start" and normalize_text(matched.get("initial_state")) != normalize_text("READY"):
            problems.append("start event initial_state is not READY")
        if event["kind"] == "start" and not _has_trigger_flow(dsl_flows, "start", matched.get("name"), ["ready"]):
            problems.append("missing start event enables flow")
        if event["kind"] == "end" and not (
            _has_flow_action(dsl_flows, matched.get("name")) or _has_trigger_flow(dsl_flows, "event", matched.get("name"), ["completed"])
        ):
            problems.append("missing event completion or enablement flow")
        if problems:
            records.append(ValidationRecord("event_mapping", "event", event["id"], event["name"], matched.get("name"), False, "; ".join(problems)))
            type_mismatches.append(records[-1].to_dict())
        else:
            exact_matches += 1
            records.append(ValidationRecord("event_mapping", "event", event["id"], event["name"], matched.get("name"), True, "Event preserved with expected progression rule.", severity="info"))

    for rule in bpmn_data.get("businessrules", []):
        matched = _find_match(rule, dsl_businessrules)
        if not matched:
            reason = f'BPMN businessRuleTask "{rule["name"]}" missing in DSL businessrules.'
            records.append(ValidationRecord("businessrule_mapping", "businessRuleTask", rule["id"], rule["name"], None, False, reason))
            missing_items.append(records[-1].to_dict())
            continue
        preserved_elements += 1
        problems = []
        if rule.get("dmn") and normalize_text(matched.get("dmn")) != normalize_text(rule.get("dmn")):
            problems.append(f'dmn mismatch: BPMN {rule.get("dmn")} vs DSL {matched.get("dmn")}')
        if rule.get("decision") and normalize_text(matched.get("decision")) != normalize_text(rule.get("decision")):
            problems.append(f'decision mismatch: BPMN {rule.get("decision")} vs DSL {matched.get("decision")}')
        if not matched.get("dmn"):
            problems.append("DSL businessrule missing dmn")
        if not matched.get("decision"):
            problems.append("DSL businessrule missing decision")
        if not matched.get("input_mapping"):
            problems.append("DSL businessrule missing input mapping")
        if not matched.get("output_mapping"):
            problems.append("DSL businessrule missing output mapping")

        bpmn_input_names = {normalize_text(item.get("name")) for item in rule.get("input_mapping", []) if isinstance(item, dict) and item.get("name")}
        dsl_input_names = {normalize_text(item.get("dmnParam")) for item in matched.get("input_mapping", []) if item.get("dmnParam")}
        if bpmn_input_names and not bpmn_input_names.issubset(dsl_input_names):
            problems.append(f"input mapping mismatch: BPMN {sorted(bpmn_input_names)} vs DSL {sorted(dsl_input_names)}")

        bpmn_output_names = {normalize_text(item.get("name")) for item in rule.get("output_mapping", []) if isinstance(item, dict) and item.get("name")}
        dsl_output_names = {normalize_text(item.get("dmnParam")) for item in matched.get("output_mapping", []) if item.get("dmnParam")}
        if bpmn_output_names and not bpmn_output_names.issubset(dsl_output_names):
            problems.append(f"output mapping mismatch: BPMN {sorted(bpmn_output_names)} vs DSL {sorted(dsl_output_names)}")

        if not _has_trigger_flow(dsl_flows, "businessrule", matched.get("name"), ["ready", "waiting", "done"]):
            problems.append("DSL flows missing businessrule ready|waiting|done trigger")

        if problems:
            records.append(ValidationRecord("businessrule_mapping", "businessRuleTask", rule["id"], rule["name"], matched.get("name"), False, "; ".join(problems)))
            type_mismatches.append(records[-1].to_dict())
        else:
            exact_matches += 1
            records.append(ValidationRecord("businessrule_mapping", "businessRuleTask", rule["id"], rule["name"], matched.get("name"), True, "Business rule mapping preserved.", severity="info"))

    total_elements = sum(
        len(bpmn_data.get(key, []))
        for key in ("participants", "messages", "gateways", "events", "businessrules")
    )
    failed_records = [record for record in records if not record.passed]
    passed_records = [record for record in records if record.passed]
    contract_total = len(records)
    contract_passed = len(passed_records)
    element_preservation_rate = round((preserved_elements / total_elements) if total_elements else 1.0, 4)
    mapping_accuracy = round((exact_matches / preserved_elements) if preserved_elements else 1.0, 4)
    contract_satisfaction_rate = round((contract_passed / contract_total) if contract_total else 1.0, 4)

    return {
        "case_name": bpmn_data.get("case_name") or dsl_data.get("case_name"),
        "source_files": {
            "bpmn": bpmn_data.get("source_files", {}).get("bpmn"),
            "dmn": bpmn_data.get("source_files", {}).get("dmn"),
            "b2c": dsl_data.get("source_files", {}).get("b2c"),
        },
        "total_elements": total_elements,
        "success_mappings": exact_matches,
        "preserved_elements": preserved_elements,
        "missing_items": missing_items,
        "type_mismatches": type_mismatches,
        "contract_total": contract_total,
        "contract_passed": contract_passed,
        "contract_failed": contract_total - contract_passed,
        "element_preservation_rate": element_preservation_rate,
        "mapping_accuracy": mapping_accuracy,
        "contract_satisfaction_rate": contract_satisfaction_rate,
        "pass": contract_satisfaction_rate == 1.0,
        "details": [record.to_dict() for record in records],
        "failed_details": [record.to_dict() for record in failed_records],
    }


def render_mapping_report_md(report: Dict[str, Any]) -> str:
    lines = [
        f"# Mapping Report: {report['case_name']}",
        "",
        "## Metrics",
        "",
        f"- Total elements: {report['total_elements']}",
        f"- Preserved elements: {report['preserved_elements']}",
        f"- Successful mappings: {report['success_mappings']}",
        f"- Contract total: {report['contract_total']}",
        f"- Contract passed: {report['contract_passed']}",
        f"- Element Preservation Rate: {report['element_preservation_rate']:.2%}",
        f"- Mapping Accuracy: {report['mapping_accuracy']:.2%}",
        f"- Contract Satisfaction Rate: {report['contract_satisfaction_rate']:.2%}",
        f"- Pass/Fail: {'PASS' if report['pass'] else 'FAIL'}",
        "",
        "## Source Files",
        "",
        f"- BPMN: `{report['source_files'].get('bpmn')}`",
        f"- DMN: `{report['source_files'].get('dmn')}`",
        f"- B2C: `{report['source_files'].get('b2c')}`",
        "",
        "## Failed Checks",
        "",
    ]
    if not report["failed_details"]:
        lines.append("- None")
    else:
        for item in report["failed_details"]:
            lines.append(
                f'- [{item["contract_type"]}] BPMN {item["bpmn_element_type"]} '
                f'"{item["bpmn_element_name"]}" ({item["bpmn_element_id"]}) -> '
                f'DSL `{item["dsl_node_id"]}`: {item["reason"]}'
            )
    lines.extend(["", "## All Contract Checks", ""])
    for item in report["details"]:
        lines.append(
            f'- {"PASS" if item["passed"] else "FAIL"} | {item["contract_type"]} | '
            f'BPMN `{item["bpmn_element_id"]}` -> DSL `{item["dsl_node_id"]}` | {item["reason"]}'
        )
    lines.append("")
    return "\n".join(lines)


def render_summary_md(rows: List[Dict[str, Any]]) -> str:
    headers = [
        "Case",
        "Participants",
        "Messages",
        "Gateways",
        "Events",
        "BusinessRules",
        "Contract Satisfaction",
        "Element Preservation Rate",
        "Mapping Accuracy",
        "Pass/Fail",
    ]
    lines = ["# Exp1 Summary", "", "|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append(
            "|"
            + "|".join(
                [
                    str(row["Case"]),
                    str(row["Participants"]),
                    str(row["Messages"]),
                    str(row["Gateways"]),
                    str(row["Events"]),
                    str(row["BusinessRules"]),
                    str(row["Contract Satisfaction"]),
                    str(row["Element Preservation Rate"]),
                    str(row["Mapping Accuracy"]),
                    str(row["Pass/Fail"]),
                ]
            )
            + "|"
        )
    lines.append("")
    return "\n".join(lines)


def write_summary_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    ensure_parent(path)
    fieldnames = [
        "Case",
        "Participants",
        "Messages",
        "Gateways",
        "Events",
        "BusinessRules",
        "Contract Satisfaction",
        "Element Preservation Rate",
        "Mapping Accuracy",
        "Pass/Fail",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def discover_case_dirs(cases_root: Path) -> List[Path]:
    return sorted([path for path in cases_root.iterdir() if path.is_dir()])


def resolve_case_files(case_dir: Path) -> Dict[str, Optional[Path]]:
    manifest_path = case_dir / "case.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        return {
            "case_name": manifest.get("case_name") or case_dir.name,
            "bpmn": Path(manifest["bpmn"]).resolve() if manifest.get("bpmn") else None,
            "dmn": Path(manifest["dmn"]).resolve() if manifest.get("dmn") else None,
            "b2c": Path(manifest["b2c"]).resolve() if manifest.get("b2c") else None,
        }

    def _pick(pattern: str) -> Optional[Path]:
        matches = sorted(case_dir.glob(pattern))
        return matches[0] if matches else None

    return {
        "case_name": case_dir.name,
        "bpmn": _pick("*.bpmn"),
        "dmn": _pick("*.dmn"),
        "b2c": _pick("*.b2c"),
    }
