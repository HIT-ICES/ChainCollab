#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from tag_utils import (
    edges_by_type,
    find_edge,
    find_node,
    node_index,
    nodes_by_type,
    public_the_name,
    read_json,
    summarize_message_schema,
    write_json,
)


DIRECT_TYPES = {
    "bpmn:participant": "dsl:participant",
    "bpmn:message": "dsl:message",
    "bpmn:startEvent": "dsl:event",
    "bpmn:endEvent": "dsl:event",
    "bpmn:exclusiveGateway": "dsl:gateway",
    "bpmn:parallelGateway": "dsl:gateway",
    "bpmn:eventBasedGateway": "dsl:gateway",
    "bpmn:businessRuleTask": "dsl:businessrule",
    "bpmn:receiveTask": "dsl:oracletask",
    "bpmn:scriptTask": "dsl:oracletask",
    "bpmn:dataTask": "dsl:oracletask",
}


def activation_target(bpmn_tag: Dict[str, Any], element_id: str) -> Optional[str]:
    node = find_node(bpmn_tag, element_id)
    if not node:
        return element_id
    if node["type"] != "bpmn:choreographyTask":
        return element_id
    initiating = node["attrs"].get("initiatingParticipantRef")
    flows = {edge["id"]: edge for edge in edges_by_type(bpmn_tag, "bpmn:messageFlow")}
    init_message = None
    return_message = None
    for flow_id in node["attrs"].get("messageFlowRefs", []):
        flow = flows.get(flow_id)
        if not flow:
            continue
        if flow["source"] == initiating:
            init_message = flow["attrs"].get("message")
        if flow["target"] == initiating:
            return_message = flow["attrs"].get("message")
    return init_message or return_message


def sequence_by_id(bpmn_tag: Dict[str, Any], seq_id: str) -> Optional[Dict[str, Any]]:
    return next((edge for edge in edges_by_type(bpmn_tag, "bpmn:sequenceFlow") if edge["id"] == seq_id), None)


def outgoing_target(bpmn_tag: Dict[str, Any], node: Dict[str, Any]) -> Optional[str]:
    outgoing = node.get("attrs", {}).get("outgoing")
    if isinstance(outgoing, list):
        outgoing = outgoing[0] if outgoing else ""
    seq = sequence_by_id(bpmn_tag, outgoing or "")
    return activation_target(bpmn_tag, seq["target"]) if seq else None


def check_element_coverage(bpmn_tag: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    direct_sources = [node for node in bpmn_tag["nodes"] if node["type"] in DIRECT_TYPES]
    matched = {(link["source_id"], link["rule_name"]) for link in trace.get("links", []) if link.get("status") == "matched"}
    missing = []
    for node in direct_sources:
        if not any(source_id == node["id"] for source_id, _ in matched):
            missing.append({"source_id": node["id"], "source_type": node["type"]})
    represented_failures = [
        item for item in trace.get("represented_sources", [])
        if item.get("source_type") == "bpmn:choreographyTask" and not item.get("represented_by")
    ]
    total = len(direct_sources) + len([n for n in nodes_by_type(bpmn_tag, "bpmn:choreographyTask")])
    mapped = len(direct_sources) - len(missing) + len([n for n in nodes_by_type(bpmn_tag, "bpmn:choreographyTask")]) - len(represented_failures)
    return {
        "convertible_source_elements": total,
        "mapped_source_elements": mapped,
        "missing_elements": missing,
        "represented_failures": represented_failures,
        "element_coverage": mapped / total if total else 1.0,
    }


def check_type_consistency(trace: Dict[str, Any]) -> Dict[str, Any]:
    mismatches = []
    total = 0
    matched = 0
    for link in trace.get("links", []):
        source_type = link.get("source_type")
        if source_type not in DIRECT_TYPES:
            continue
        total += 1
        expected = DIRECT_TYPES[source_type]
        if link.get("target_type") == expected:
            matched += 1
        else:
            mismatches.append({**link, "expected_target_type": expected})
    return {
        "total_trace_links": total,
        "type_matched_links": matched,
        "type_mismatches": mismatches,
        "type_consistency": matched / total if total else 1.0,
    }


def check_attributes(bpmn_tag: Dict[str, Any], dsl_tag: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    bpmn_nodes = node_index(bpmn_tag)
    dsl_nodes = node_index(dsl_tag)
    failures = []
    checks = 0

    def expect(source_id: str, target_id: str, attr: str, source_value: Any, target_value: Any) -> None:
        nonlocal checks
        checks += 1
        if source_value != target_value:
            failures.append(
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "attribute": attr,
                    "source_value": source_value,
                    "target_value": target_value,
                    "failure_type": "AttributeMismatch",
                }
            )

    for link in trace.get("links", []):
        source = bpmn_nodes.get(link.get("source_id"))
        target = dsl_nodes.get(link.get("target_id"))
        if not source or not target:
            continue
        stype = source["type"]
        sid = source["id"]
        tid = target["id"]
        expect(sid, tid, "id", sid, tid)
        if stype in DIRECT_TYPES:
            expect(sid, tid, "dsl_name_from_source_id", sid, target["name"])
        if stype == "bpmn:participant":
            expect(sid, tid, "isMulti", source["attrs"].get("is_multi"), target["attrs"].get("isMulti"))
            expect(sid, tid, "multiMin", source["attrs"].get("multi_minimum"), target["attrs"].get("multiMin"))
            expect(sid, tid, "multiMax", source["attrs"].get("multi_maximum"), target["attrs"].get("multiMax"))
        if stype == "bpmn:message":
            expect(sid, tid, "schema", summarize_message_schema(source["attrs"].get("documentation", "")), target["attrs"].get("schema", ""))
        if stype == "bpmn:startEvent":
            expect(sid, tid, "initialState", "READY", target["attrs"].get("initialState"))
        if stype == "bpmn:endEvent":
            expect(sid, tid, "initialState", "INACTIVE", target["attrs"].get("initialState"))
        if stype == "bpmn:exclusiveGateway":
            expect(sid, tid, "gatewayType", "exclusive", target["attrs"].get("gatewayType"))
        if stype == "bpmn:parallelGateway":
            expect(sid, tid, "gatewayType", "parallel", target["attrs"].get("gatewayType"))
        if stype == "bpmn:eventBasedGateway":
            expect(sid, tid, "gatewayType", "event", target["attrs"].get("gatewayType"))
        if stype == "bpmn:businessRuleTask":
            expect(sid, tid, "dmnResource", f"{sid}.dmn", target["attrs"].get("dmnResource"))
            expect(sid, tid, "decisionID", f"{sid}_DecisionID", target["attrs"].get("decisionID"))
    return {
        "total_attribute_checks": checks,
        "passed_attribute_checks": checks - len(failures),
        "failed_attribute_checks": len(failures),
        "attribute_preservation": (checks - len(failures)) / checks if checks else 1.0,
        "failures": failures,
    }


def check_relations(bpmn_tag: Dict[str, Any], dsl_tag: Dict[str, Any]) -> Dict[str, Any]:
    failures = []
    checks = 0

    def require(ok: bool, failure: Dict[str, Any]) -> None:
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(failure)

    for flow in edges_by_type(bpmn_tag, "bpmn:messageFlow"):
        message = flow["attrs"].get("message")
        sender_edge = find_edge(dsl_tag, "dsl:message_sender", message, flow["source"])
        receiver_edge = find_edge(dsl_tag, "dsl:message_receiver", message, flow["target"])
        require(sender_edge is not None, {"failure_type": "RelationMissing", "rule": "MessageFlowSender", "source_relation": flow})
        require(receiver_edge is not None, {"failure_type": "RelationMissing", "rule": "MessageFlowReceiver", "source_relation": flow})

    for start in nodes_by_type(bpmn_tag, "bpmn:startEvent"):
        target = outgoing_target(bpmn_tag, start)
        if target:
            require(
                find_edge(dsl_tag, "dsl:start_enables", start["id"], target) is not None,
                {"failure_type": "RelationMissing", "rule": "StartEventSequence2StartFlow", "source": start["id"], "target": target},
            )

    for task in nodes_by_type(bpmn_tag, "bpmn:choreographyTask"):
        initiating = task["attrs"].get("initiatingParticipantRef")
        init_message = None
        return_message = None
        flows = {edge["id"]: edge for edge in edges_by_type(bpmn_tag, "bpmn:messageFlow")}
        for flow_id in task["attrs"].get("messageFlowRefs", []):
            flow = flows.get(flow_id)
            if not flow:
                continue
            if flow["source"] == initiating:
                init_message = flow["attrs"].get("message")
            if flow["target"] == initiating:
                return_message = flow["attrs"].get("message")
        successor = outgoing_target(bpmn_tag, task)
        if init_message and return_message:
            require(find_edge(dsl_tag, "dsl:enable", init_message, return_message) is not None, {"failure_type": "RelationMissing", "rule": "ChoreographyInitReturn", "source": init_message, "target": return_message})
            if successor:
                require(find_edge(dsl_tag, "dsl:enable", return_message, successor) is not None, {"failure_type": "RelationMissing", "rule": "ChoreographyReturnSuccessor", "source": return_message, "target": successor})
        elif init_message and successor:
            require(find_edge(dsl_tag, "dsl:enable", init_message, successor) is not None, {"failure_type": "RelationMissing", "rule": "ChoreographyInitSuccessor", "source": init_message, "target": successor})
        elif return_message and successor:
            require(find_edge(dsl_tag, "dsl:enable", return_message, successor) is not None, {"failure_type": "RelationMissing", "rule": "ChoreographyReturnSuccessor", "source": return_message, "target": successor})

    for gateway in nodes_by_type(bpmn_tag, "bpmn:parallelGateway"):
        incoming = gateway["attrs"].get("incoming", [])
        outgoing = gateway["attrs"].get("outgoing", [])
        if len(incoming) > 1:
            for seq_id in incoming:
                seq = sequence_by_id(bpmn_tag, seq_id)
                if not seq:
                    continue
                source = activation_target(bpmn_tag, seq["source"])
                require(find_edge(dsl_tag, "dsl:parallel_join_source", source, gateway["id"]) is not None, {"failure_type": "RelationMissing", "rule": "ParallelJoinSource", "source": source, "target": gateway["id"]})
            for seq_id in outgoing:
                seq = sequence_by_id(bpmn_tag, seq_id)
                if not seq:
                    continue
                target = activation_target(bpmn_tag, seq["target"])
                require(find_edge(dsl_tag, "dsl:enable", gateway["id"], target) is not None, {"failure_type": "RelationMissing", "rule": "ParallelJoinEnable", "source": gateway["id"], "target": target})
        else:
            for seq_id in outgoing:
                seq = sequence_by_id(bpmn_tag, seq_id)
                if seq:
                    target = activation_target(bpmn_tag, seq["target"])
                    require(find_edge(dsl_tag, "dsl:enable", gateway["id"], target) is not None, {"failure_type": "RelationMissing", "rule": "GatewayEnable", "source": gateway["id"], "target": target})

    return {
        "total_source_relations": checks,
        "preserved_relations": checks - len(failures),
        "missing_relations": failures,
        "direction_mismatches": [],
        "relation_preservation": (checks - len(failures)) / checks if checks else 1.0,
    }


def check_spurious_targets(dsl_tag: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    critical = {"dsl:participant", "dsl:message", "dsl:gateway", "dsl:event", "dsl:businessrule", "dsl:oracletask"}
    traceable = {link["target_id"] for link in trace.get("links", []) if link.get("status") == "matched"}
    traceable |= {link["target_id"] for link in trace.get("relation_links", []) if link.get("status") == "matched"}
    critical_nodes = [node for node in dsl_tag["nodes"] if node["type"] in critical]
    spurious = [node for node in critical_nodes if node["id"] not in traceable]
    return {
        "critical_target_elements": len(critical_nodes),
        "traceable_target_elements": len(critical_nodes) - len(spurious),
        "allowed_synthetic_elements": [],
        "spurious_targets": spurious,
        "target_traceability": (len(critical_nodes) - len(spurious)) / len(critical_nodes) if critical_nodes else 1.0,
    }


def run_checks(bpmn_tag: Dict[str, Any], dsl_tag: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    reports = {
        "element_coverage_report": check_element_coverage(bpmn_tag, trace),
        "type_consistency_report": check_type_consistency(trace),
        "attribute_preservation_report": check_attributes(bpmn_tag, dsl_tag, trace),
        "relation_preservation_report": check_relations(bpmn_tag, dsl_tag),
        "spurious_target_report": check_spurious_targets(dsl_tag, trace),
    }
    metrics = {
        "element_coverage": reports["element_coverage_report"]["element_coverage"],
        "type_consistency": reports["type_consistency_report"]["type_consistency"],
        "attribute_preservation": reports["attribute_preservation_report"]["attribute_preservation"],
        "relation_preservation": reports["relation_preservation_report"]["relation_preservation"],
        "target_traceability": reports["spurious_target_report"]["target_traceability"],
    }
    failures = []
    for name, report in reports.items():
        for key in ("missing_elements", "represented_failures", "type_mismatches", "failures", "missing_relations", "spurious_targets"):
            for item in report.get(key, []):
                failures.append({"report": name, **item})
    return {
        "reports": reports,
        "summary": {
            "case_name": bpmn_tag["case_name"],
            "structural_status": "PASS" if all(value == 1.0 for value in metrics.values()) else "FAIL",
            "metrics": metrics,
            "counts": {
                "bpmn_nodes": len(bpmn_tag["nodes"]),
                "bpmn_edges": len(bpmn_tag["edges"]),
                "dsl_nodes": len(dsl_tag["nodes"]),
                "dsl_edges": len(dsl_tag["edges"]),
            },
            "failures": failures,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpmn-tag", type=Path, required=True)
    parser.add_argument("--dsl-tag", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()

    result = run_checks(read_json(args.bpmn_tag), read_json(args.dsl_tag), read_json(args.trace))
    args.report_dir.mkdir(parents=True, exist_ok=True)
    for name, report in result["reports"].items():
        write_json(args.report_dir / f"{name}.json", report)
    write_json(args.report_dir / "structure_summary.json", result["summary"])
    lines = [
        "# 1B Structure Consistency Summary",
        "",
        f"Case: {result['summary']['case_name']}",
        f"Status: {result['summary']['structural_status']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in result["summary"]["metrics"].items():
        lines.append(f"| {key} | {value:.4f} |")
    lines.extend(["", f"Failures: {len(result['summary']['failures'])}", ""])
    for failure in result["summary"]["failures"][:50]:
        lines.append(f"- {failure}")
    (args.report_dir / "structure_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if result["summary"]["structural_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
