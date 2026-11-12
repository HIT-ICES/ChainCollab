#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tag_utils import add_edge, add_node, extract_named_block, iter_named_blocks, make_tag, write_json
from tag_utils import find_matching_brace


def strip_quotes(value: str) -> str:
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1].replace('\\"', '"')
    return value


def section_body(contract_body: str, section_name: str) -> str:
    block = extract_named_block(contract_body, section_name)
    return block["body"] if block else ""


def parse_actions(action_text: str) -> list[tuple[str, str]]:
    actions: list[tuple[str, str]] = []
    for part in [item.strip().rstrip(";") for item in action_text.split(",") if item.strip()]:
        if part.startswith("enable "):
            actions.append(("enable", part.split(None, 1)[1].strip()))
        elif part.startswith("disable "):
            actions.append(("disable", part.split(None, 1)[1].strip()))
        elif part.startswith("set "):
            actions.append(("set", part[4:].strip()))
    return actions


def add_flow_action_edges(tag: dict, source: str, action_text: str, prefix: str, attrs: dict) -> None:
    for index, (action, target_expr) in enumerate(parse_actions(action_text)):
        if action == "set":
            if "=" not in target_expr:
                continue
            target, value = [part.strip() for part in target_expr.split("=", 1)]
            add_edge(tag, f"{prefix}__set__{index}__{target}", "dsl:set_global", source, target, {**attrs, "value": strip_quotes(value)})
            continue
        edge_type = "dsl:enable" if action == "enable" else "dsl:disable"
        add_edge(tag, f"{prefix}__{action}__{index}__{target_expr}", edge_type, source, target_expr, {**attrs, "action": action})


def iter_message_blocks(messages_body: str) -> list[dict]:
    blocks: list[dict] = []
    pattern = re.compile(
        r"\bmessage\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{",
        re.M,
    )
    for match in pattern.finditer(messages_body):
        open_index = messages_body.find("{", match.start())
        close_index = find_matching_brace(messages_body, open_index)
        blocks.append(
            {
                "name": match.group(1),
                "sender": match.group(2),
                "receiver": match.group(3),
                "body": messages_body[open_index + 1:close_index],
                "start": match.start(),
                "open": open_index,
                "close": close_index,
            }
        )
    return blocks


def extract(dsl_file: Path, case_name: str) -> dict:
    text = dsl_file.read_text(encoding="utf-8")
    contract = extract_named_block(text, "contract")
    if not contract:
        raise ValueError("No contract block found in DSL")
    contract_name = contract["name"]
    body = contract["body"]
    tag = make_tag(
        case_name,
        "dsl",
        dsl_file,
        "extract_dsl_structure",
        [
            "src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx",
            "src/newTranslator/MDAcheck/b2c.ecore",
        ],
    )
    add_node(tag, contract_name, "dsl:contract", contract_name, {})

    for block in iter_named_blocks(section_body(body, "participants"), "participant"):
        pid = block["name"]
        b = block["body"]
        attrs = {
            "msp": strip_quotes(re.search(r'\bmsp\s+(".*?")', b, re.S).group(1)) if re.search(r'\bmsp\s+(".*?")', b, re.S) else "",
            "x509": strip_quotes(re.search(r'\bx509\s+(".*?")', b, re.S).group(1)) if re.search(r'\bx509\s+(".*?")', b, re.S) else "",
            "isMulti": (re.search(r"\bisMulti\s+(true|false)", b) or ["", "false"])[1] == "true",
            "multiMin": int((re.search(r"\bmultiMin\s+(-?\d+)", b) or ["", "0"])[1]),
            "multiMax": int((re.search(r"\bmultiMax\s+(-?\d+)", b) or ["", "0"])[1]),
            "attributes": {},
        }
        attrs_block = extract_named_block(b, "attributes")
        if attrs_block:
            for key, value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\".*?\")", attrs_block["body"], re.S):
                attrs["attributes"][key] = strip_quotes(value)
                attr_id = f"{pid}__attr__{key}"
                add_node(tag, attr_id, "dsl:attribute", key, {"key": key, "value": attrs["attributes"][key]})
                add_edge(tag, f"{pid}__participant_attribute__{key}", "dsl:participant_attribute", pid, attr_id, {})
        add_node(tag, pid, "dsl:participant", pid, attrs)
        add_edge(tag, f"{contract_name}__contains__{pid}", "dsl:contains", contract_name, pid, {"section": "participants"})

    globals_body = section_body(body, "globals")
    for name, type_name in re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_]+)", globals_body, re.M):
        add_node(tag, name, "dsl:global", name, {"type": type_name})
        add_edge(tag, f"{contract_name}__contains__{name}", "dsl:contains", contract_name, name, {"section": "globals"})

    messages_body = section_body(body, "messages")
    for block in iter_message_blocks(messages_body):
        message_id = block["name"]
        sender = block["sender"]
        receiver = block["receiver"]
        state_match = re.search(r"\binitial\s+state\s+([A-Z_]+)", block["body"])
        schema_match = re.search(r'\bschema\s+("(?:\\"|[^"])*")', block["body"], re.S)
        add_node(tag, message_id, "dsl:message", message_id, {
            "sender": sender,
            "receiver": receiver,
            "initialState": state_match.group(1) if state_match else "",
            "schema": strip_quotes(schema_match.group(1)) if schema_match else "",
        })
        add_edge(tag, f"{message_id}__sender", "dsl:message_sender", message_id, sender, {})
        add_edge(tag, f"{message_id}__receiver", "dsl:message_receiver", message_id, receiver, {})
        add_edge(tag, f"{contract_name}__contains__{message_id}", "dsl:contains", contract_name, message_id, {"section": "messages"})

    for block in iter_named_blocks(section_body(body, "gateways"), "gateway"):
        gid = block["name"]
        type_match = re.search(r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)", block["body"])
        state_match = re.search(r"\binitial\s+state\s+([A-Z_]+)", block["body"])
        add_node(tag, gid, "dsl:gateway", gid, {
            "gatewayType": type_match.group(1) if type_match else "",
            "initialState": state_match.group(1) if state_match else "",
        })
        add_edge(tag, f"{contract_name}__contains__{gid}", "dsl:contains", contract_name, gid, {"section": "gateways"})

    for block in iter_named_blocks(section_body(body, "events"), "event"):
        eid = block["name"]
        state_match = re.search(r"\binitial\s+state\s+([A-Z_]+)", block["body"])
        add_node(tag, eid, "dsl:event", eid, {"initialState": state_match.group(1) if state_match else ""})
        add_edge(tag, f"{contract_name}__contains__{eid}", "dsl:contains", contract_name, eid, {"section": "events"})

    for block in iter_named_blocks(section_body(body, "businessrules"), "businessrule"):
        rid = block["name"]
        dmn = strip_quotes((re.search(r'\bdmn\s+(".*?")', block["body"], re.S) or ["", '""'])[1])
        decision = strip_quotes((re.search(r'\bdecision\s+(".*?")', block["body"], re.S) or ["", '""'])[1])
        state_match = re.search(r"\binitial\s+state\s+([A-Z_]+)", block["body"])
        add_node(tag, rid, "dsl:businessrule", rid, {"dmnResource": dmn, "decisionID": decision, "initialState": state_match.group(1) if state_match else ""})
        for direction, edge_type in (("input", "dsl:businessrule_input"), ("output", "dsl:businessrule_output")):
            mapping_block = re.search(rf"\b{direction}\s+mapping\s*\{{(.*?)\}}", block["body"], re.S)
            if not mapping_block:
                continue
            for param, global_ref in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)", mapping_block.group(1)):
                mapping_id = f"{rid}__{direction}__{param}"
                add_node(tag, mapping_id, "dsl:paramMapping", param, {"dmnParam": param, "globalRef": global_ref, "direction": direction})
                add_edge(tag, mapping_id, edge_type, rid, global_ref, {"dmnParam": param})
                add_edge(tag, f"{mapping_id}__globalRef", "dsl:param_global_ref", mapping_id, global_ref, {})

    for block in iter_named_blocks(section_body(body, "oracletasks"), "oracletask"):
        oid = block["name"]
        type_match = re.search(r"\btype\s+([A-Za-z0-9_-]+)", block["body"])
        data_source = strip_quotes((re.search(r'\bdataSource\s+("(?:\\"|[^"])*")', block["body"], re.S) or ["", '""'])[1])
        compute_script = strip_quotes((re.search(r'\bcomputeScript\s+("(?:\\"|[^"])*")', block["body"], re.S) or ["", '""'])[1])
        state_match = re.search(r"\binitial\s+state\s+([A-Z_]+)", block["body"])
        add_node(tag, oid, "dsl:oracletask", oid, {
            "oracleType": type_match.group(1) if type_match else "",
            "dataSource": data_source,
            "computeScript": compute_script,
            "initialState": state_match.group(1) if state_match else "",
        })
        add_edge(tag, f"{oid}__oracle_data_source", "dsl:oracle_data_source", oid, oid, {"value": data_source})
        add_edge(tag, f"{oid}__oracle_compute_script", "dsl:oracle_compute_script", oid, oid, {"value": compute_script})
        mapping_block = re.search(r"\boutput\s+mapping\s*\{(.*?)\}", block["body"], re.S)
        if mapping_block:
            for param, global_ref in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)", mapping_block.group(1)):
                mapping_id = f"{oid}__output__{param}"
                add_node(tag, mapping_id, "dsl:paramMapping", param, {"dmnParam": param, "globalRef": global_ref, "direction": "output"})
                add_edge(tag, mapping_id, "dsl:oracletask_output", oid, global_ref, {"dmnParam": param})
                add_edge(tag, f"{mapping_id}__globalRef", "dsl:param_global_ref", mapping_id, global_ref, {})

    flows_body = section_body(body, "flows")
    for match in re.finditer(r"start\s+event\s+([A-Za-z_][A-Za-z0-9_]*)\s+enables\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", flows_body):
        source, target = match.groups()
        flow_id = f"start__{source}__{target}"
        add_node(tag, flow_id, "dsl:startFlow", flow_id, {"start": source, "target": target})
        add_edge(tag, flow_id, "dsl:start_enables", source, target, {"flow_item": "StartFlow"})

    for match in re.finditer(r"when\s+message\s+([A-Za-z_][A-Za-z0-9_]*)\s+(sent|completed)\s+then\s+(.*?);", flows_body, re.S):
        source, cond, actions = match.groups()
        flow_id = f"messageFlow__{source}__{match.start()}"
        add_node(tag, flow_id, "dsl:messageFlow", flow_id, {"message": source, "msgCond": cond})
        add_edge(tag, f"{flow_id}__trigger", "dsl:flow_trigger", flow_id, source, {"trigger_type": "message", "trigger_condition": cond})
        add_flow_action_edges(tag, source, actions, flow_id, {"trigger_type": "message", "trigger_condition": cond, "flow_item": "MessageFlow"})

    for match in re.finditer(r"when\s+businessrule\s+([A-Za-z_][A-Za-z0-9_]*)\s+(ready|waiting|done)\s+then\s+(.*?);", flows_body, re.S):
        source, cond, actions = match.groups()
        flow_id = f"ruleFlow__{source}__{match.start()}"
        add_node(tag, flow_id, "dsl:ruleFlow", flow_id, {"businessrule": source, "ruleCond": cond})
        add_flow_action_edges(tag, source, actions, flow_id, {"trigger_type": "businessrule", "trigger_condition": cond, "flow_item": "RuleFlow"})

    for match in re.finditer(r"when\s+oracletask\s+([A-Za-z_][A-Za-z0-9_]*)\s+done\s+then\s+(.*?);", flows_body, re.S):
        source, actions = match.groups()
        flow_id = f"oracleTaskFlow__{source}__{match.start()}"
        add_node(tag, flow_id, "dsl:oracleTaskFlow", flow_id, {"oracletask": source, "condition": "done"})
        add_flow_action_edges(tag, source, actions, flow_id, {"trigger_type": "oracletask", "trigger_condition": "done", "flow_item": "OracleTaskFlow"})

    for match in re.finditer(r"when\s+gateway\s+([A-Za-z_][A-Za-z0-9_]*)\s+completed\s+then\s+(.*?);", flows_body, re.S):
        source, actions = match.groups()
        flow_id = f"gatewayFlow__{source}__{match.start()}"
        add_node(tag, flow_id, "dsl:gatewayFlow", flow_id, {"gateway": source, "condition": "completed"})
        add_flow_action_edges(tag, source, actions, flow_id, {"trigger_type": "gateway", "trigger_condition": "completed", "flow_item": "GatewayFlow"})

    for match in re.finditer(r"when\s+gateway\s+([A-Za-z_][A-Za-z0-9_]*)\s+completed\s+choose\s*\{(.*?)\}", flows_body, re.S):
        gateway, branches = match.groups()
        flow_id = f"gatewayChoose__{gateway}__{match.start()}"
        add_node(tag, flow_id, "dsl:gatewayFlow", flow_id, {"gateway": gateway, "condition": "completed", "mode": "choose"})
        for branch_index, branch in enumerate(re.finditer(r"(if\s+(.+?)|else)\s+then\s+(.*?);", branches, re.S)):
            kind = "else" if branch.group(1).strip() == "else" else "if"
            condition = "" if kind == "else" else " ".join((branch.group(2) or "").split())
            actions = branch.group(3)
            branch_id = f"{flow_id}__branch__{branch_index}"
            branch_type = "dsl:gatewayElseBranch" if kind == "else" else "dsl:gatewayCompareBranch"
            add_node(tag, branch_id, branch_type, branch_id, {"branch_kind": kind, "condition": condition})
            for action_index, (action, target) in enumerate(parse_actions(actions)):
                if action == "enable":
                    add_edge(tag, f"{branch_id}__gateway_branch__{action_index}__{target}", "dsl:gateway_branch", gateway, target, {"branch_kind": kind, "condition": condition, "action": action})

    for match in re.finditer(r"parallel\s+gateway\s+([A-Za-z_][A-Za-z0-9_]*)\s+await\s+(.*?)\s+then\s+(.*?);", flows_body, re.S):
        gateway, sources_text, actions = match.groups()
        flow_id = f"parallelJoin__{gateway}__{match.start()}"
        sources = [item.strip() for item in sources_text.split(",") if item.strip()]
        add_node(tag, flow_id, "dsl:parallelJoin", flow_id, {"gateway": gateway, "sources": sources})
        for source in sources:
            add_edge(tag, f"{flow_id}__source__{source}", "dsl:parallel_join_source", source, gateway, {"flow_item": "ParallelJoin"})
        add_flow_action_edges(tag, gateway, actions, flow_id, {"trigger_type": "parallelGateway", "flow_item": "ParallelJoin"})

    return tag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsl-file", type=Path, required=True)
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    tag = extract(args.dsl_file, args.case_name)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "dsl_tag.json", tag)
    write_json(args.out_dir / "dsl_elements.json", tag["nodes"])
    write_json(args.out_dir / "dsl_relations.json", tag["edges"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
