#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from tag_utils import edges_by_type, find_edge, find_node, node_index, nodes_by_type, read_json, summarize_message_schema, write_json


DIRECT_RULES = {
    "bpmn:participant": ("dsl:participant", "Participant2Participant"),
    "bpmn:message": ("dsl:message", "MessageRef2Message"),
    "bpmn:startEvent": ("dsl:event", "StartEvent2Event"),
    "bpmn:endEvent": ("dsl:event", "EndEvent2Event"),
    "bpmn:exclusiveGateway": ("dsl:gateway", "ExclusiveGateway2Gateway"),
    "bpmn:parallelGateway": ("dsl:gateway", "ParallelGateway2Gateway"),
    "bpmn:eventBasedGateway": ("dsl:gateway", "EventBasedGateway2Gateway"),
    "bpmn:businessRuleTask": ("dsl:businessrule", "BusinessRuleTask2BusinessRule"),
    "bpmn:receiveTask": ("dsl:oracletask", "ReceiveTask2OracleTask"),
    "bpmn:scriptTask": ("dsl:oracletask", "ScriptTask2OracleTask"),
    "bpmn:dataTask": ("dsl:oracletask", "ReceiveTask2OracleTask"),
}


def build_trace(bpmn_tag: Dict[str, Any], dsl_tag: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    dsl_nodes = node_index(dsl_tag)
    trace = {
        "case_name": bpmn_tag["case_name"],
        "contract": contract.get("name", ""),
        "links": [],
        "relation_links": [],
        "unmatched_sources": [],
        "unmatched_targets": [],
        "represented_sources": [],
    }

    matched_targets: set[str] = set()
    for node in bpmn_tag["nodes"]:
        source_type = node["type"]
        if source_type not in DIRECT_RULES:
            continue
        target_type, rule_name = DIRECT_RULES[source_type]
        target = dsl_nodes.get(node["id"])
        if target and target["type"] == target_type:
            matched_targets.add(target["id"])
            trace["links"].append(
                {
                    "source_id": node["id"],
                    "source_type": source_type,
                    "target_id": target["id"],
                    "target_type": target["type"],
                    "rule_name": rule_name,
                    "status": "matched",
                    "match_method": "same_id",
                }
            )
        else:
            trace["unmatched_sources"].append(
                {
                    "source_id": node["id"],
                    "source_type": source_type,
                    "expected_target_type": target_type,
                    "rule_name": rule_name,
                }
            )

    for edge in edges_by_type(bpmn_tag, "bpmn:messageFlow"):
        message_id = edge["attrs"].get("message")
        target = dsl_nodes.get(message_id)
        if target and target["type"] == "dsl:message":
            matched_targets.add(message_id)
            trace["relation_links"].append(
                {
                    "source_id": edge["id"],
                    "source_type": "bpmn:messageFlow",
                    "target_id": message_id,
                    "target_type": "dsl:message",
                    "rule_name": "MessageFlowEndpoints2MessageParticipants",
                    "status": "matched",
                    "match_method": "messageRef",
                }
            )
            trace["represented_sources"].append(
                {
                    "source_id": edge["id"],
                    "source_type": "bpmn:messageFlow",
                    "represented_by": [message_id],
                    "rule_name": "MessageFlowNoDirectNode",
                }
            )
        else:
            trace["unmatched_sources"].append(
                {
                    "source_id": edge["id"],
                    "source_type": "bpmn:messageFlow",
                    "expected_target_id": message_id,
                    "expected_target_type": "dsl:message",
                    "rule_name": "MessageFlowEndpoints2MessageParticipants",
                }
            )

    for node in nodes_by_type(bpmn_tag, "bpmn:choreographyTask"):
        represented_by = []
        for flow_id in node["attrs"].get("messageFlowRefs", []):
            flow = next((edge for edge in edges_by_type(bpmn_tag, "bpmn:messageFlow") if edge["id"] == flow_id), None)
            if flow and flow["attrs"].get("message") in dsl_nodes:
                represented_by.append(flow["attrs"]["message"])
        trace["represented_sources"].append(
            {
                "source_id": node["id"],
                "source_type": "bpmn:choreographyTask",
                "represented_by": represented_by,
                "rule_name": "ChoreographyTaskExpansion",
                "status": "matched" if represented_by else "unmatched",
            }
        )

    for derived in bpmn_tag.get("derived", []):
        target_id = derived.get("target")
        if target_id and target_id in dsl_nodes:
            matched_targets.add(target_id)
            trace["links"].append(
                {
                    "source_id": derived["id"],
                    "source_type": derived["type"],
                    "target_id": target_id,
                    "target_type": dsl_nodes[target_id]["type"],
                    "rule_name": derived["rule"],
                    "status": "matched",
                    "match_method": "derived_target",
                    "source_refs": derived.get("sources", []),
                }
            )

    critical_target_types = {
        "dsl:participant",
        "dsl:message",
        "dsl:gateway",
        "dsl:event",
        "dsl:businessrule",
        "dsl:oracletask",
    }
    for node in dsl_tag["nodes"]:
        if node["type"] in critical_target_types and node["id"] not in matched_targets:
            trace["unmatched_targets"].append(
                {
                    "target_id": node["id"],
                    "target_type": node["type"],
                    "reason": "no BPMN source link",
                }
            )
    return trace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpmn-tag", type=Path, required=True)
    parser.add_argument("--dsl-tag", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out-file", type=Path, required=True)
    args = parser.parse_args()

    trace = build_trace(read_json(args.bpmn_tag), read_json(args.dsl_tag), read_json(args.contract))
    write_json(args.out_file, trace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
