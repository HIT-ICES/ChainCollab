#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from tag_utils import (
    NS_BPMN,
    add_edge,
    add_node,
    make_tag,
    map_bpmn_type,
    parse_condition,
    parse_json_documentation,
    public_the_name,
    write_json,
)


BPMN_TAG = "http://www.omg.org/spec/BPMN/20100524/MODEL"


def bpmn(tag: str) -> str:
    return f"{{{BPMN_TAG}}}{tag}"


def first_text(element: ET.Element, child_tag: str) -> str:
    child = element.find(bpmn(child_tag))
    return (child.text or "").strip() if child is not None else ""


def children_text(element: ET.Element, child_tag: str) -> list[str]:
    return [(child.text or "").strip() for child in element.findall(bpmn(child_tag)) if (child.text or "").strip()]


def element_id(element: ET.Element) -> str:
    return element.attrib.get("id", "")


def element_name(element: ET.Element) -> str:
    return element.attrib.get("name", "")


def documentation_text(element: ET.Element) -> str:
    doc = element.find(bpmn("documentation"))
    return (doc.text or "").strip() if doc is not None else "{}"


def add_documentation_derivatives(tag: dict, owner_id: str, documentation: str, source_kind: str) -> None:
    doc = parse_json_documentation(documentation)
    for prop_name, definition in (doc.get("properties") or {}).items():
        derived_id = f"{owner_id}__property__{prop_name}"
        global_name = public_the_name(prop_name)
        add_node(
            tag,
            derived_id,
            "bpmn:messageProperty",
            prop_name,
            {
                "name": prop_name,
                "global_name": global_name,
                "type": definition.get("type", "string"),
                "dsl_type": map_bpmn_type(definition.get("type", "string")),
                "description": definition.get("description", ""),
                "owner": owner_id,
                "source_kind": source_kind,
            },
        )
        add_edge(
            tag,
            f"{owner_id}__documentationProperty__{prop_name}",
            "bpmn:documentationProperty",
            owner_id,
            derived_id,
            {},
        )
        tag["derived"].append(
            {
                "id": f"Derive_{global_name}",
                "type": "bpmn:message_property",
                "target": global_name,
                "sources": [owner_id],
                "rule": "MessageProperty2GlobalVar",
                "attrs": {
                    "name": prop_name,
                    "type": definition.get("type", "string"),
                    "dsl_type": map_bpmn_type(definition.get("type", "string")),
                },
            }
        )
    for direction, edge_type in (("inputs", "bpmn:documentationInput"), ("outputs", "bpmn:documentationOutput")):
        for entry in doc.get(direction, []) or []:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            param_id = f"{owner_id}__{direction[:-1]}__{entry['name']}"
            node_type = "bpmn:businessRuleParameter" if source_kind == "businessrule" else "bpmn:oracleOutputParameter"
            add_node(
                tag,
                param_id,
                node_type,
                entry["name"],
                {
                    "name": entry["name"],
                    "global_name": public_the_name(entry["name"]),
                    "direction": direction[:-1],
                    "type": entry.get("type", "string"),
                    "dsl_type": map_bpmn_type(entry.get("type", "string")),
                    "owner": owner_id,
                },
            )
            add_edge(tag, f"{owner_id}__{edge_type.split(':')[1]}__{entry['name']}", edge_type, owner_id, param_id, {})


def extract(bpmn_file: Path, case_name: str) -> dict:
    root = ET.parse(bpmn_file).getroot()
    tag = make_tag(
        case_name,
        "bpmn",
        bpmn_file,
        "extract_bpmn_structure",
        [
            "src/newTranslator/generator/parser/choreography_parser/parser.py",
            "src/newTranslator/generator/parser/choreography_parser/elements.py",
        ],
    )

    choreography = root.find(bpmn("choreography"))
    if choreography is None:
        raise ValueError("No bpmn:choreography element found")

    for participant in choreography.findall(bpmn("participant")):
        pid = element_id(participant)
        multiplicity = participant.find(bpmn("participantMultiplicity"))
        is_multi = multiplicity is not None
        add_node(
            tag,
            pid,
            "bpmn:participant",
            element_name(participant),
            {
                "is_multi": is_multi,
                "multi_minimum": int(multiplicity.attrib.get("minimum", 0)) if multiplicity is not None else 0,
                "multi_maximum": int(multiplicity.attrib.get("maximum", 0)) if multiplicity is not None else 0,
            },
        )

    message_ids_from_flows: set[str] = set()
    for flow in choreography.findall(bpmn("messageFlow")):
        fid = element_id(flow)
        message_ref = flow.attrib.get("messageRef", "")
        message_ids_from_flows.add(message_ref)
        add_edge(
            tag,
            fid,
            "bpmn:messageFlow",
            flow.attrib.get("sourceRef", ""),
            flow.attrib.get("targetRef", ""),
            {
                "message": message_ref,
                "name": element_name(flow),
            },
        )
        add_edge(tag, f"{fid}__messageRef", "bpmn:messageRef", fid, message_ref, {})

    for message in root.findall(bpmn("message")):
        mid = element_id(message)
        if mid not in message_ids_from_flows:
            continue
        documentation = documentation_text(message)
        add_node(
            tag,
            mid,
            "bpmn:message",
            element_name(message),
            {
                "documentation": documentation,
            },
        )
        add_documentation_derivatives(tag, mid, documentation, "message")

    node_specs = [
        ("startEvent", "bpmn:startEvent"),
        ("endEvent", "bpmn:endEvent"),
        ("exclusiveGateway", "bpmn:exclusiveGateway"),
        ("parallelGateway", "bpmn:parallelGateway"),
        ("eventBasedGateway", "bpmn:eventBasedGateway"),
        ("businessRuleTask", "bpmn:businessRuleTask"),
        ("receiveTask", "bpmn:receiveTask"),
        ("scriptTask", "bpmn:scriptTask"),
        ("DataTask", "bpmn:dataTask"),
    ]
    for xml_name, node_type in node_specs:
        for element in choreography.findall(bpmn(xml_name)):
            nid = element_id(element)
            attrs = {
                "incoming": children_text(element, "incoming"),
                "outgoing": children_text(element, "outgoing"),
            }
            if node_type in {"bpmn:businessRuleTask", "bpmn:receiveTask", "bpmn:scriptTask", "bpmn:dataTask"}:
                attrs["documentation"] = documentation_text(element)
            add_node(tag, nid, node_type, element_name(element), attrs)
            if node_type == "bpmn:businessRuleTask":
                add_documentation_derivatives(tag, nid, attrs["documentation"], "businessrule")
            if node_type in {"bpmn:receiveTask", "bpmn:scriptTask", "bpmn:dataTask"}:
                add_documentation_derivatives(tag, nid, attrs["documentation"], "oracle")

    for task in choreography.findall(bpmn("choreographyTask")):
        tid = element_id(task)
        participant_refs = children_text(task, "participantRef")
        message_flow_refs = children_text(task, "messageFlowRef")
        initiating = task.attrib.get("initiatingParticipantRef", "")
        add_node(
            tag,
            tid,
            "bpmn:choreographyTask",
            element_name(task),
            {
                "incoming": first_text(task, "incoming"),
                "outgoing": first_text(task, "outgoing"),
                "participants": participant_refs,
                "initiatingParticipantRef": initiating,
                "messageFlowRefs": message_flow_refs,
            },
        )
        for ref in participant_refs:
            add_edge(tag, f"{tid}__participantRef__{ref}", "bpmn:participantRef", tid, ref, {})
        if initiating:
            add_edge(tag, f"{tid}__initiatingParticipant__{initiating}", "bpmn:initiatingParticipant", tid, initiating, {})
        for ref in message_flow_refs:
            add_edge(tag, f"{tid}__messageFlowRef__{ref}", "bpmn:messageFlowRef", tid, ref, {})

    for seq in choreography.findall(bpmn("sequenceFlow")):
        sid = element_id(seq)
        condition = ""
        condition_el = seq.find(bpmn("conditionExpression"))
        if condition_el is not None and condition_el.text:
            condition = condition_el.text.strip()
        elif seq.attrib.get("name"):
            condition = seq.attrib["name"]
        add_edge(
            tag,
            sid,
            "bpmn:sequenceFlow",
            seq.attrib.get("sourceRef", ""),
            seq.attrib.get("targetRef", ""),
            {
                "name": element_name(seq),
                "condition_expression": condition,
            },
        )
        parsed_condition = parse_condition(condition)
        if parsed_condition:
            cond_id = f"{sid}__condition__{public_the_name(parsed_condition['name'])}"
            add_node(
                tag,
                cond_id,
                "bpmn:sequenceConditionVariable",
                parsed_condition["name"],
                {
                    **parsed_condition,
                    "global_name": public_the_name(parsed_condition["name"]),
                    "dsl_type": map_bpmn_type("string"),
                    "sequenceFlow": sid,
                },
            )
            add_edge(tag, f"{sid}__condition", "bpmn:condition", sid, cond_id, {})
            tag["derived"].append(
                {
                    "id": f"Derive_{public_the_name(parsed_condition['name'])}",
                    "type": "bpmn:condition_variable",
                    "target": public_the_name(parsed_condition["name"]),
                    "sources": [sid],
                    "rule": "SequenceConditionVariable2GlobalVar",
                    "attrs": parsed_condition,
                }
            )

    return tag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpmn-file", type=Path, required=True)
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    tag = extract(args.bpmn_file, args.case_name)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "bpmn_tag.json", tag)
    write_json(args.out_dir / "bpmn_elements.json", tag["nodes"])
    write_json(args.out_dir / "bpmn_relations.json", tag["edges"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
