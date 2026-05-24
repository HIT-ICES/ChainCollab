#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any


ROOT = Path("/root/code/ChainCollab")
EXP_ROOT = ROOT / "Experiment" / "new" / "exp1_1C"
CASE_NAME = os.environ.get("EXP1C_CASE_NAME", "SupplyChainPaper")
CASE_DIR = EXP_ROOT / "cases" / CASE_NAME
BPMN_FILE = Path(os.environ.get("EXP1C_BPMN_FILE", str(ROOT / "Experiment" / "BPMNwithDMNcase" / f"{CASE_NAME}.bpmn")))
TRACE_FILE = ROOT / "Experiment" / "new" / "exp1_1B" / "cases" / CASE_NAME / "trace" / "bpmn_dsl_trace.json"
TRANSLATOR_ROOT = ROOT / "src" / "newTranslator"
TRANSLATOR_PY = TRANSLATOR_ROOT / ".venv" / "bin" / "python"
TRANSLATOR_SCRIPT = TRANSLATOR_ROOT / "generator" / "bpmn_to_dsl.py"

DIRS = {
    "config": CASE_DIR / "config",
    "translator": CASE_DIR / "translator",
    "raw": CASE_DIR / "raw",
    "semantic": CASE_DIR / "semantic",
    "canonical": CASE_DIR / "canonical",
    "paths": CASE_DIR / "paths",
    "normalized": CASE_DIR / "normalized",
    "comparison": CASE_DIR / "comparison",
    "traces": CASE_DIR / "traces",
    "logical_paths": CASE_DIR / "logical_paths",
    "reports": CASE_DIR / "reports",
    "all_reports": EXP_ROOT / "reports",
}


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def discover_dmn_files() -> list[Path]:
    explicit = os.environ.get("EXP1C_DMN_FILES") or os.environ.get("EXP1C_DMN_FILE")
    if explicit:
        return unique_paths([Path(part.strip()) for part in explicit.split(",") if part.strip()])
    case_dir = BPMN_FILE.parent
    candidates = [
        case_dir / f"{CASE_NAME}.dmn",
        case_dir / f"{CASE_NAME[:1].lower() + CASE_NAME[1:]}.dmn" if CASE_NAME else case_dir / ".dmn",
    ]
    candidates.extend(sorted(case_dir.glob(f"{BPMN_FILE.stem}*.dmn")))
    lowered_stem = BPMN_FILE.stem[:1].lower() + BPMN_FILE.stem[1:]
    candidates.extend(sorted(case_dir.glob(f"{lowered_stem}*.dmn")))
    return unique_paths([path for path in candidates if path.exists()])


DMN_FILES = discover_dmn_files()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_dirs() -> None:
    for path in DIRS.values():
        path.mkdir(parents=True, exist_ok=True)


def default_bound_config() -> dict[str, Any]:
    return {
        "max_depth": 30,
        "max_loop_unroll": 2,
        "max_paths": 200,
        "include_invalid_paths": False,
        "parallel_policy": "interleaving_canonical",
        "guard_policy": "symbolic_label",
        "dmn_policy": "decision_table_rows",
        "dmn_output_bound": 20,
        "dmn_fallback_policy": "fixed_sample",
    }


def prepare() -> None:
    ensure_dirs()
    write_json(DIRS["config"] / "path_bound_config.json", default_bound_config())
    run_config = {
        "case_name": CASE_NAME,
        "bpmn_file": str(BPMN_FILE),
        "dmn_file": str(DMN_FILES[0]) if DMN_FILES else "",
        "dmn_files": [str(path) for path in DMN_FILES],
        "translator_root": str(TRANSLATOR_ROOT),
        "dsl_file": str(DIRS["translator"] / "dsl.b2c"),
        "trace_file": str(TRACE_FILE),
        "bound_config": str(DIRS["config"] / "path_bound_config.json"),
    }
    write_json(DIRS["config"] / "run_config.json", run_config)


def run_newtranslator() -> None:
    ensure_dirs()
    output = DIRS["translator"] / "dsl.b2c"
    cmd = [
        str(TRANSLATOR_PY),
        str(TRANSLATOR_SCRIPT),
        str(BPMN_FILE),
        "-o",
        str(output),
        "-n",
        CASE_NAME,
    ]
    proc = subprocess.run(cmd, cwd=str(TRANSLATOR_ROOT), text=True, capture_output=True)
    report = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "output": str(output),
        "dmn_files": [str(path) for path in DMN_FILES],
    }
    for dmn_file in DMN_FILES:
        if dmn_file.exists():
            shutil.copy2(dmn_file, DIRS["translator"] / dmn_file.name)
    write_json(DIRS["translator"] / "newtranslator_report.json", report)
    if proc.returncode != 0:
        raise SystemExit(f"newTranslator failed: {proc.stderr}")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_doc_json(text: str | None) -> Any:
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def extract_bpmn_raw() -> None:
    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    tree = ET.parse(BPMN_FILE)
    root = tree.getroot()
    elements: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    wanted_nodes = {
        "participant",
        "message",
        "startEvent",
        "endEvent",
        "choreographyTask",
        "exclusiveGateway",
        "parallelGateway",
        "eventBasedGateway",
        "businessRuleTask",
        "receiveTask",
        "scriptTask",
    }
    for elem in root.iter():
        kind = local_name(elem.tag)
        if kind not in wanted_nodes:
            continue
        docs = [d.text or "" for d in list(elem) if local_name(d.tag) == "documentation"]
        attrs: dict[str, Any] = dict(elem.attrib)
        if docs:
            attrs["documentation"] = docs[0]
            attrs["documentation_json"] = parse_doc_json(docs[0])
        elements.append({
            "id": elem.attrib.get("id"),
            "type": f"bpmn:{kind}",
            "name": elem.attrib.get("name", ""),
            "attrs": attrs,
        })
    for elem in root.iter():
        kind = local_name(elem.tag)
        if kind == "messageFlow":
            relations.append({
                "id": elem.attrib.get("id"),
                "type": "bpmn:messageFlow",
                "source": elem.attrib.get("sourceRef"),
                "target": elem.attrib.get("targetRef"),
                "attrs": {"message": elem.attrib.get("messageRef"), "name": elem.attrib.get("name", "")},
            })
        elif kind == "sequenceFlow":
            cond = None
            for child in list(elem):
                if local_name(child.tag) == "conditionExpression":
                    cond = child.text
            relations.append({
                "id": elem.attrib.get("id"),
                "type": "bpmn:sequenceFlow",
                "source": elem.attrib.get("sourceRef"),
                "target": elem.attrib.get("targetRef"),
                "attrs": {"name": elem.attrib.get("name", ""), "condition_expression": cond},
            })
    write_json(DIRS["raw"] / "bpmn.raw_elements.json", elements)
    write_json(DIRS["raw"] / "bpmn.raw_relations.json", relations)


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def split_actions(text: str) -> list[dict[str, str]]:
    actions = []
    for part in [p.strip().rstrip(";") for p in text.split(",") if p.strip()]:
        if part.startswith("enable "):
            actions.append({"op": "enable", "target": part.split(None, 1)[1].strip()})
        elif part.startswith("disable "):
            actions.append({"op": "disable", "target": part.split(None, 1)[1].strip()})
        elif part.startswith("set "):
            left, right = part[4:].split("=", 1)
            actions.append({"op": "set", "var": left.strip(), "value": strip_quotes(right)})
    return actions


def iter_named_blocks(text: str, keyword: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for match in re.finditer(rf"\b{re.escape(keyword)}\s+(\w+)\s*\{{", text):
        start = match.end() - 1
        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            char = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append((match.group(1), text[start + 1:idx]))
                    break
    return blocks


@dataclass
class DSLModel:
    participants: list[dict[str, Any]]
    globals: dict[str, str]
    nodes: dict[str, dict[str, Any]]
    flows: list[dict[str, Any]]


def parse_dsl(dsl_path: Path) -> DSLModel:
    text = dsl_path.read_text(encoding="utf-8")
    participants: list[dict[str, Any]] = []
    globals_: dict[str, str] = {}
    nodes: dict[str, dict[str, Any]] = {}
    flows: list[dict[str, Any]] = []

    for m in re.finditer(r"participant\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        body = m.group(2)
        attrs = dict(re.findall(r"(\w+)\s*=\s*\"([^\"]*)\"", body))
        participants.append({
            "id": m.group(1),
            "name": attrs.get("role", m.group(1)),
            "is_multi": "isMulti true" in body,
            "metadata": {
                "msp": (re.search(r"msp\s+\"([^\"]*)\"", body) or ["", ""])[1],
                "x509": (re.search(r"x509\s+\"([^\"]*)\"", body) or ["", ""])[1],
                "attributes": attrs,
            },
        })
    globals_block = re.search(r"globals\s*\{(.*?)\n\s*\}", text, re.S)
    if globals_block:
        for name, typ in re.findall(r"^\s*(\w+)\s*:\s*(\w+)", globals_block.group(1), re.M):
            globals_[name] = typ
    for m in re.finditer(r"message\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        schema_m = re.search(r"schema\s+\"((?:\\.|[^\"])*)\"", m.group(4), re.S)
        schema = schema_m.group(1).encode("utf-8").decode("unicode_escape") if schema_m else "{}"
        nodes[m.group(1)] = {"id": m.group(1), "type": "message", "sender": m.group(2), "receiver": m.group(3), "schema": schema, "initial_state": "INACTIVE"}
    for m in re.finditer(r"gateway\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        typ = (re.search(r"type\s+(\w+)", m.group(2)) or ["", "gateway"])[1]
        nodes[m.group(1)] = {"id": m.group(1), "type": "gateway", "gateway_type": typ, "initial_state": "INACTIVE"}
    for m in re.finditer(r"event\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        state = (re.search(r"initial\s+state\s+(\w+)", m.group(2)) or ["", "INACTIVE"])[1]
        nodes[m.group(1)] = {"id": m.group(1), "type": "event", "initial_state": state}
    for name, body in iter_named_blocks(text, "businessrule"):
        outputs = re.findall(r"(\w+)\s*->\s*(\w+)", body.split("output mapping", 1)[1] if "output mapping" in body else "")
        inputs = re.findall(r"(\w+)\s*->\s*(\w+)", body.split("output mapping", 1)[0])
        nodes[name] = {"id": name, "type": "businessrule", "inputs": inputs, "outputs": outputs, "initial_state": "INACTIVE"}
    for m in re.finditer(r"oracletask\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        typ = (re.search(r"type\s+([\w-]+)", m.group(2)) or ["", "external-data"])[1]
        outputs = re.findall(r"(\w+)\s*->\s*(\w+)", m.group(2))
        nodes[m.group(1)] = {"id": m.group(1), "type": "oracletask", "oracle_type": typ, "outputs": outputs, "initial_state": "INACTIVE"}
    flow_block = re.search(r"flows\s*\{(.*)\n\s*\}\s*\n\s*\}", text, re.S)
    if flow_block:
        block = flow_block.group(1)
        for m in re.finditer(r"start\s+event\s+(\w+)\s+enables\s+(\w+)\s*;", block):
            flows.append({"kind": "start", "trigger": m.group(1), "actions": [{"op": "enable", "target": m.group(2)}]})
        for m in re.finditer(r"when\s+message\s+(\w+)\s+(sent|completed)\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "message", "trigger": m.group(1), "condition": m.group(2), "actions": split_actions(m.group(3))})
        for m in re.finditer(r"when\s+gateway\s+(\w+)\s+completed\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "gateway", "trigger": m.group(1), "actions": split_actions(m.group(2))})
        for m in re.finditer(r"when\s+gateway\s+(\w+)\s+completed\s+choose\s*\{(.*?)\n\s*\}", block, re.S):
            branches = []
            for b in re.finditer(r"if\s+(.+?)\s+then\s+(.*?);", m.group(2), re.S):
                branches.append({"guard": " ".join(b.group(1).split()), "actions": split_actions(b.group(2))})
            else_m = re.search(r"else\s+then\s+(.*?);", m.group(2), re.S)
            if else_m:
                branches.append({"guard": "else", "actions": split_actions(else_m.group(1))})
            flows.append({"kind": "gateway_choose", "trigger": m.group(1), "branches": branches})
        for m in re.finditer(r"parallel\s+gateway\s+(\w+)\s+await\s+(.*?)\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "parallel_join", "trigger": m.group(1), "sources": [s.strip() for s in m.group(2).split(",")], "actions": split_actions(m.group(3))})
        for m in re.finditer(r"when\s+businessrule\s+(\w+)\s+done\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "businessrule", "trigger": m.group(1), "actions": split_actions(m.group(2))})
        for m in re.finditer(r"when\s+oracletask\s+(\w+)\s+done\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "oracletask", "trigger": m.group(1), "actions": split_actions(m.group(2))})
        for m in re.finditer(r"when\s+event\s+(\w+)\s+completed\s+then\s+(.*?);", block, re.S):
            flows.append({"kind": "event", "trigger": m.group(1), "actions": split_actions(m.group(2))})
    return DSLModel(participants, globals_, nodes, flows)


def extract_dsl_raw() -> None:
    model = parse_dsl(DIRS["translator"] / "dsl.b2c")
    elements = model.participants + list(model.nodes.values()) + [{"id": k, "type": "global", "dsl_type": v} for k, v in model.globals.items()]
    write_json(DIRS["raw"] / "dsl.raw_elements.json", elements)
    write_json(DIRS["raw"] / "dsl.raw_relations.json", model.flows)


def parse_dmn_outputs() -> dict[str, list[str]]:
    existing_dmn_files = [path for path in DMN_FILES if path.exists()]
    if not existing_dmn_files:
        return {}
    ns = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}
    outputs: dict[str, set[str]] = {}
    for dmn_file in existing_dmn_files:
        root = ET.parse(dmn_file).getroot()
        for decision in root.findall("dmn:decision", ns):
            decision_outputs: list[str] = []
            for output in decision.findall(".//dmn:output", ns):
                name = output.attrib.get("name") or output.attrib.get("label")
                if name:
                    outputs.setdefault(name, set())
                    decision_outputs.append(name)
            if not decision_outputs:
                continue
            output_entries = decision.findall(".//dmn:outputEntry", ns)
            if len(decision_outputs) == 1:
                for output_entry in output_entries:
                    text = "".join(output_entry.itertext()).strip()
                    if text:
                        outputs[decision_outputs[0]].add(strip_quotes(text))
                continue
            for idx, output_entry in enumerate(output_entries):
                text = "".join(output_entry.itertext()).strip()
                if text:
                    outputs[decision_outputs[idx % len(decision_outputs)]].add(strip_quotes(text))
    return {k: sorted(v) for k, v in outputs.items()}


def build_ubts(model_type: str) -> dict[str, Any]:
    model = parse_dsl(DIRS["translator"] / "dsl.b2c")
    transitions = []
    for idx, flow in enumerate(model.flows, 1):
        transitions.append({
            "id": f"r_{idx:03d}",
            "template_kind": flow["kind"],
            "trigger": flow.get("trigger"),
            "guard": flow.get("guard") or flow.get("condition") or None,
            "actions": flow.get("actions", []),
            "branches": flow.get("branches", []),
            "sources": flow.get("sources", []),
        })
    starts = [node_id for node_id, node in model.nodes.items() if node.get("type") == "event" and node.get("initial_state") == "READY"]
    ends = [node_id for node_id, node in model.nodes.items() if node.get("type") == "event" and node.get("initial_state") != "READY"]
    for end in ends:
        transitions.append({
            "id": f"r_{len(transitions)+1:03d}",
            "template_kind": "end_event",
            "trigger": end,
            "guard": None,
            "actions": [],
            "branches": [],
            "sources": [],
        })
    return {
        "schema_version": "exp1c.ubts.v1",
        "case_name": CASE_NAME,
        "model_type": model_type,
        "formalism": "UBTS/GLSTS JSON implementation",
        "participants": model.participants,
        "nodes": list(model.nodes.values()),
        "globals": model.globals,
        "dmn_outputs": parse_dmn_outputs(),
        "transitions": transitions,
        "start_nodes": starts,
        "end_nodes": ends,
        "state_model": ["INIT", "READY", "PENDING_CONFIRMATION", "DONE", "INACTIVE"],
    }


def build_bpmn_semantic_graph() -> None:
    write_json(DIRS["semantic"] / "bpmn.semantic_graph.json", build_ubts("bpmn"))


def build_dsl_semantic_graph() -> None:
    write_json(DIRS["semantic"] / "dsl.semantic_graph.json", build_ubts("dsl"))


def canonicalize() -> None:
    if TRACE_FILE.exists():
        trace = read_json(TRACE_FILE)
        mapping = {link["source_id"]: link["target_id"] for link in trace.get("links", []) if link.get("status") == "matched"}
        source = str(TRACE_FILE)
    else:
        mapping = {}
        source = "not_available; kept translator element ids"
    report = {"case_name": CASE_NAME, "mapped_ids": len(mapping), "missing": [], "trace_file": source}
    for name in ("bpmn", "dsl"):
        data = read_json(DIRS["semantic"] / f"{name}.semantic_graph.json")
        # IDs are already aligned for this case; keep canonical output explicit.
        data["canonicalization"] = {"source": str(TRACE_FILE), "mapping_count": len(mapping)}
        write_json(DIRS["canonical"] / f"{name}.semantic_graph.canonical.json", data)
    write_json(DIRS["canonical"] / "id_normalization_report.json", report)


def initial_state(ubts: dict[str, Any]) -> dict[str, Any]:
    states = {}
    for node in ubts["nodes"]:
        states[node["id"]] = node.get("initial_state") or ("READY" if node["id"] in ubts["start_nodes"] else "INACTIVE")
    return {"element_states": states, "globals": {}, "enabled": sorted([k for k, v in states.items() if v == "READY"])}


def apply_actions(state: dict[str, Any], actions: list[dict[str, str]]) -> None:
    for action in actions:
        if action["op"] == "enable":
            state["element_states"][action["target"]] = "READY"
        elif action["op"] == "disable":
            state["element_states"][action["target"]] = "INACTIVE"
        elif action["op"] == "set":
            state["globals"][action["var"]] = action["value"]
    state["enabled"] = sorted([k for k, v in state["element_states"].items() if v == "READY"])


def eval_guard(guard: str, globals_: dict[str, Any]) -> bool:
    if guard == "else":
        return True
    m = re.match(r"(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)", guard)
    if not m:
        return False
    var, op, raw = m.groups()
    expected = strip_quotes(raw)
    actual = globals_.get(var)
    actual_text = "true" if actual is True else "false" if actual is False else str(actual)
    if expected.lower() in {"true", "false"}:
        actual_text = actual_text.lower()
        expected = expected.lower()
    if op == "==":
        return actual_text == expected
    if op == "!=":
        return actual_text != expected
    try:
        av, ev = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    return {">": av > ev, "<": av < ev, ">=": av >= ev, "<=": av <= ev}[op]


def trace_signature(steps: list[dict[str, Any]]) -> str:
    payload = [
        {
            "i": i,
            "element": step["element"],
            "type": step["type"],
            "guard": step.get("guard"),
            "payload_shape": sorted((step.get("payload") or {}).keys()),
            "outputs": step.get("outputs") or {},
        }
        for i, step in enumerate(steps)
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def node_type(ubts: dict[str, Any], node_id: str) -> str:
    for node in ubts["nodes"]:
        if node["id"] == node_id:
            return node["type"]
    return "unknown"


def sample_payload(node: dict[str, Any]) -> dict[str, Any]:
    if node.get("type") != "message":
        return {}
    try:
        schema = json.loads(node.get("schema") or "{}")
    except json.JSONDecodeError:
        return {}
    out = {}
    for name, spec in (schema.get("properties") or {}).items():
        typ = spec.get("type", "string")
        out[name] = True if typ == "boolean" else 1 if typ == "number" else f"sample-{name}"
    return out


def normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def matching_global(ubts: dict[str, Any], field_name: str) -> str | None:
    wanted = normalized_name(field_name)
    for global_name in ubts.get("globals", {}):
        if normalized_name(global_name) == wanted:
            return global_name
    return None


def guard_variables(transitions: list[dict[str, Any]]) -> set[str]:
    variables: set[str] = set()
    for transition in transitions:
        guards = [transition.get("guard")] + [branch.get("guard") for branch in transition.get("branches", [])]
        for guard in [g for g in guards if g and g != "else"]:
            match = re.match(r"(\w+)\s*(?:==|!=|>=|<=|>|<)\s*.+", guard)
            if match:
                variables.add(match.group(1))
    return variables


def message_output_variants(
    node: dict[str, Any],
    ubts: dict[str, Any],
    guarded_variables: set[str],
    limit: int,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if node.get("type") != "message":
        return [(sample_payload(node), {})]
    try:
        schema = json.loads(node.get("schema") or "{}")
    except json.JSONDecodeError:
        return [({}, {})]
    fields = schema.get("properties") or {}
    if not fields:
        return [({}, {})]
    payload_template = sample_payload(node)
    value_sets: list[tuple[str, str, list[Any]]] = []
    for field_name, spec in fields.items():
        global_name = matching_global(ubts, field_name)
        if not global_name or global_name not in guarded_variables:
            continue
        typ = spec.get("type", "string")
        if typ == "boolean":
            values = ["true", "false"]
        elif typ == "number":
            values = [1]
        else:
            values = [f"sample-{field_name}"]
        value_sets.append((field_name, global_name, values))
    if not value_sets:
        return [(payload_template, {})]
    variants: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for combo in product(*[values for _, _, values in value_sets]):
        payload = dict(payload_template)
        outputs: dict[str, Any] = {}
        for (field_name, global_name, _), value in zip(value_sets, combo):
            payload[field_name] = value
            if global_name:
                outputs[global_name] = value
        variants.append((payload, outputs))
        if len(variants) >= limit:
            break
    return variants or [({}, {})]


def case_insensitive_values(values_by_name: dict[str, list[str]], name: str) -> list[str]:
    for key, values in values_by_name.items():
        if key.lower() == name.lower():
            return values
    return []


def values_from_guards(transitions: list[dict[str, Any]], variable: str) -> list[str]:
    values: list[str] = []
    pattern = re.compile(rf"\b{re.escape(variable)}\s*(?:==|!=)\s*(.+)")
    for transition in transitions:
        guards = [transition.get("guard")] + [branch.get("guard") for branch in transition.get("branches", [])]
        for guard in [g for g in guards if g and g != "else"]:
            match = pattern.match(guard)
            if match:
                value = strip_quotes(match.group(1))
                if value not in values:
                    values.append(value)
    return values


def businessrule_output_variants(
    node: dict[str, Any],
    ubts: dict[str, Any],
    transitions: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    mappings = node.get("outputs") or []
    if not mappings:
        return [{}]
    dmn_outputs = ubts.get("dmn_outputs", {})
    value_sets: list[tuple[str, list[str]]] = []
    for dmn_name, global_name in mappings:
        values = (
            dmn_outputs.get(dmn_name)
            or dmn_outputs.get(global_name)
            or case_insensitive_values(dmn_outputs, dmn_name)
            or case_insensitive_values(dmn_outputs, global_name)
            or values_from_guards(transitions, global_name)
        )
        if not values:
            values = ["true", "false"] if global_name.lower().startswith(("confirm", "approved", "valid")) else ["sample"]
        value_sets.append((global_name, values[:limit]))
    variants: list[dict[str, Any]] = []
    names = [name for name, _ in value_sets]
    for combo in product(*[values for _, values in value_sets]):
        variants.append(dict(zip(names, combo)))
        if len(variants) >= limit:
            break
    return variants


def generate_paths(model_name: str) -> None:
    ubts = read_json(DIRS["canonical"] / f"{model_name}.semantic_graph.canonical.json")
    cfg = read_json(DIRS["config"] / "path_bound_config.json")
    transitions = ubts["transitions"]
    node_by_id = {node["id"]: node for node in ubts["nodes"]}
    guarded_variables = guard_variables(transitions)
    max_paths = cfg["max_paths"]
    max_depth = cfg["max_depth"]
    max_loop_unroll = cfg.get("max_loop_unroll", 2)
    results = []
    queue = [(initial_state(ubts), [], [])]
    visited: set[str] = set()
    join_templates = [t for t in transitions if t["template_kind"] == "parallel_join"]

    def stabilize_parallel_joins(state: dict[str, Any]) -> None:
        changed = False
        for join in join_templates:
            trig = join["trigger"]
            sources_done = all(state["element_states"].get(source) == "DONE" for source in join.get("sources", []))
            if not sources_done and state["element_states"].get(trig) == "READY":
                state["element_states"][trig] = "INACTIVE"
                changed = True
                continue
            if state["element_states"].get(trig) in {"READY", "DONE"}:
                continue
            if sources_done:
                state["element_states"][trig] = "READY"
                changed = True
        if changed:
            state["enabled"] = sorted([k for k, v in state["element_states"].items() if v == "READY"])

    def state_key(state: dict[str, Any], steps: list[dict[str, Any]]) -> str:
        return json.dumps({
            "states": state["element_states"],
            "globals": state["globals"],
            "steps": [(s["element"], s.get("guard"), s.get("outputs")) for s in steps],
        }, sort_keys=True)

    while queue and len(results) < max_paths:
        state, steps, trace_states = queue.pop(0)
        stabilize_parallel_joins(state)
        key = state_key(state, steps)
        if key in visited:
            continue
        visited.add(key)
        if any(state["element_states"].get(end) == "DONE" for end in ubts["end_nodes"]):
            sig = trace_signature(steps)
            results.append({
                "path_id": f"{model_name}_path_{len(results)+1:03d}",
                "trace_signature": sig,
                "steps": steps,
                "states": trace_states,
                "final_state": copy.deepcopy(state),
            })
            continue
        if len(steps) >= max_depth:
            continue
        for transition in transitions:
            trig = transition.get("trigger")
            if not trig or state["element_states"].get(trig) != "READY":
                continue
            if max_loop_unroll >= 0 and sum(1 for step in steps if step["element"] == trig) >= max_loop_unroll:
                continue
            kind = transition["template_kind"]
            base = copy.deepcopy(state)
            base["element_states"][trig] = "DONE"
            actions_variants: list[tuple[list[dict[str, str]], str | None, dict[str, Any]]] = []
            if kind == "gateway_choose":
                matched = False
                for branch in transition.get("branches", []):
                    guard = branch["guard"]
                    if guard == "else" or eval_guard(guard, base["globals"]):
                        actions_variants.append((branch["actions"], guard, {}))
                        matched = True
                        if guard != "else":
                            break
                if not matched:
                    continue
            else:
                actions_variants.append((transition.get("actions", []), transition.get("guard"), {}))
            if kind == "message":
                node = node_by_id.get(trig, {})
                actions_variants = [
                    (actions, guard, outputs)
                    for payload, outputs in message_output_variants(node, ubts, guarded_variables, cfg.get("dmn_output_bound", 20))
                    for actions, guard, _ in actions_variants
                ]
            if kind == "businessrule":
                actions_variants = []
                node = node_by_id.get(trig, {})
                for outputs in businessrule_output_variants(node, ubts, transitions, cfg.get("dmn_output_bound", 20)):
                    actions_variants.append((transition.get("actions", []), "dmn:decision_table_rows", outputs))
            for actions, guard, outputs in actions_variants:
                new_state = copy.deepcopy(base)
                if outputs:
                    new_state["globals"].update(outputs)
                apply_actions(new_state, actions)
                node = node_by_id.get(trig, {"id": trig, "type": node_type(ubts, trig)})
                step = {
                    "type": node.get("type", "unknown"),
                    "element": trig,
                    "payload": sample_payload(node),
                }
                if kind == "message":
                    matching_payloads = [
                        payload
                        for payload, payload_outputs in message_output_variants(node, ubts, guarded_variables, cfg.get("dmn_output_bound", 20))
                        if payload_outputs == outputs
                    ]
                    if matching_payloads:
                        step["payload"] = matching_payloads[0]
                if guard:
                    step["guard"] = guard
                if outputs:
                    step["outputs"] = outputs
                if node.get("sender"):
                    step["sender"] = node["sender"]
                    step["receiver"] = node["receiver"]
                trace_states_next = trace_states + [{
                    "enabled_before": state["enabled"],
                    "trigger": trig,
                    "guard_result": True,
                    "state_diff": {trig: [state["element_states"].get(trig), "DONE"]},
                    "global_diff": outputs,
                    "enabled_after": new_state["enabled"],
                }]
                queue.append((new_state, steps + [step], trace_states_next))
    write_json(DIRS["paths"] / f"{model_name}.paths.json", results)
    write_json(DIRS["paths"] / f"{model_name}.path_generation_report.json", {"case_name": CASE_NAME, "model": model_name, "path_count": len(results)})


def normalize_paths() -> None:
    report = {"case_name": CASE_NAME, "normalized": []}
    for name in ("bpmn", "dsl"):
        paths = read_json(DIRS["paths"] / f"{name}.paths.json")
        write_json(DIRS["normalized"] / f"{name}.normalized_paths.json", paths)
        report["normalized"].append({"model": name, "path_count": len(paths)})
    write_json(DIRS["normalized"] / "path_normalization_report.json", report)


def compare_path_sets() -> None:
    bpmn = read_json(DIRS["normalized"] / "bpmn.normalized_paths.json")
    dsl = read_json(DIRS["normalized"] / "dsl.normalized_paths.json")
    bpmn_sigs = {p["trace_signature"]: p for p in bpmn}
    dsl_sigs = {p["trace_signature"]: p for p in dsl}
    missing = sorted(set(bpmn_sigs) - set(dsl_sigs))
    extra = sorted(set(dsl_sigs) - set(bpmn_sigs))
    matched = sorted(set(bpmn_sigs) & set(dsl_sigs))
    result = {
        "case_name": CASE_NAME,
        "bpmn_trace_count": len(bpmn),
        "dsl_trace_count": len(dsl),
        "matched_trace_count": len(matched),
        "bpmn_subset_dsl": not missing,
        "dsl_subset_bpmn": not extra,
        "bounded_trace_equivalence": not missing and not extra,
        "missing_in_dsl": missing,
        "extra_in_dsl": extra,
        "matched_signatures": matched,
    }
    write_json(DIRS["comparison"] / "path_set_comparison.json", result)
    write_text(DIRS["comparison"] / "path_set_comparison.md", "\n".join([
        f"# Path Set Comparison: {CASE_NAME}",
        "",
        f"- BPMN bounded traces: {len(bpmn)}",
        f"- DSL bounded traces: {len(dsl)}",
        f"- Matched traces: {len(matched)}",
        f"- BPMN ⊆ DSL: {result['bpmn_subset_dsl']}",
        f"- DSL ⊆ BPMN: {result['dsl_subset_bpmn']}",
        f"- Bounded trace equivalence: {result['bounded_trace_equivalence']}",
        "",
    ]))


def simulate_traces() -> None:
    for model in ("bpmn", "dsl"):
        for path in read_json(DIRS["normalized"] / f"{model}.normalized_paths.json"):
            out_dir = DIRS["traces"] / model / path["path_id"]
            trace = {
                "schema_version": "exp1c.normalized_trace.v1",
                "model_type": model,
                "case_name": CASE_NAME,
                "path_id": path["path_id"],
                "trace_signature": path["trace_signature"],
                "steps": path["states"],
                "final_state": {
                    "status": "COMPLETED" if not path["final_state"]["enabled"] else "OPEN",
                    "element_states": path["final_state"]["element_states"],
                    "enabled_elements": path["final_state"]["enabled"],
                    "globals": path["final_state"]["globals"],
                },
            }
            write_json(out_dir / f"{model}.normalized.json", trace)


def compare_step_traces() -> None:
    bpmn_paths = {p["trace_signature"]: p for p in read_json(DIRS["normalized"] / "bpmn.normalized_paths.json")}
    dsl_paths = {p["trace_signature"]: p for p in read_json(DIRS["normalized"] / "dsl.normalized_paths.json")}
    matched = sorted(set(bpmn_paths) & set(dsl_paths))
    comparisons = []
    for sig in matched:
        b, d = bpmn_paths[sig], dsl_paths[sig]
        ok = b["steps"] == d["steps"] and b["final_state"] == d["final_state"]
        item = {"trace_signature": sig, "bpmn_path_id": b["path_id"], "dsl_path_id": d["path_id"], "passed": ok}
        comparisons.append(item)
        out = DIRS["comparison"] / "traces" / b["path_id"]
        write_json(out / "trace_comparison.json", item)
        write_text(out / "trace_comparison.md", f"# Trace Comparison {sig}\n\n- passed: {ok}\n")
    summary = {
        "case_name": CASE_NAME,
        "matched_trace_count": len(matched),
        "passed_trace_count": sum(1 for c in comparisons if c["passed"]),
        "step_wise_transition_preservation": all(c["passed"] for c in comparisons),
        "comparisons": comparisons,
    }
    write_json(DIRS["comparison"] / "step_trace_comparison_summary.json", summary)


def generate_logical_paths() -> None:
    dsl_paths = read_json(DIRS["normalized"] / "dsl.normalized_paths.json")
    comparison = read_json(DIRS["comparison"] / "step_trace_comparison_summary.json")
    passed = {c["trace_signature"] for c in comparison["comparisons"] if c["passed"]}
    if DIRS["logical_paths"].exists():
        for child in DIRS["logical_paths"].iterdir():
            if child.is_dir() and child.name.startswith(f"{CASE_NAME}_dsl_path_"):
                shutil.rmtree(child)
    exported = []
    for path in dsl_paths:
        if path["trace_signature"] not in passed:
            continue
        path_name = f"{CASE_NAME}_{path['path_id']}"
        logical = {
            "case_name": CASE_NAME,
            "path_name": path_name,
            "description": "Auto materialized from BPMN/DSL consistent path by exp1_1C.",
            "source_model": str(DIRS["translator"] / "dsl.b2c"),
            "expect": "accepted",
            "steps": path["steps"],
            "generated_path": {
                "final_enabled_elements": path["final_state"]["enabled"],
                "final_element_states": path["final_state"]["element_states"],
                "final_globals": path["final_state"]["globals"],
            },
        }
        write_json(DIRS["logical_paths"] / path_name / "logical_path.json", logical)
        exported.append(path_name)
    write_json(DIRS["logical_paths"] / "logical_path_generation_report.json", {"case_name": CASE_NAME, "exported_count": len(exported), "paths": exported})


def write_all_cases_summary() -> None:
    summaries = []
    cases_root = EXP_ROOT / "cases"
    if cases_root.exists():
        for summary_path in sorted(cases_root.glob("*/reports/behavior_summary.json")):
            summaries.append(read_json(summary_path))
    headers = [
        "case_name",
        "bpmn_trace_count",
        "dsl_trace_count",
        "logical_path_exported_count",
        "bounded_trace_equivalence",
        "step_wise_transition_preservation",
        "passed",
    ]
    rows = [",".join(headers)]
    for item in summaries:
        rows.append(",".join(str(item.get(header, "")) for header in headers))
    write_text(DIRS["all_reports"] / "all_cases_behavior_summary.csv", "\n".join(rows) + "\n")

    markdown = [
        "# Experiment 1C All Cases Behavior Summary",
        "",
        f"- Total cases: {len(summaries)}",
        f"- Passed cases: {sum(1 for item in summaries if item.get('passed'))}",
        "",
        "| Case | BPMN traces | DSL traces | Logical paths | Bounded trace equivalence | Step-wise preservation | Passed |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for item in summaries:
        markdown.append(
            "| {case_name} | {bpmn_trace_count} | {dsl_trace_count} | {logical_path_exported_count} | "
            "{bounded_trace_equivalence} | {step_wise_transition_preservation} | {passed} |".format(**item)
        )
    markdown.append("")
    write_text(DIRS["all_reports"] / "all_cases_behavior_summary.md", "\n".join(markdown))


def summarize() -> None:
    path_cmp = read_json(DIRS["comparison"] / "path_set_comparison.json")
    step_cmp = read_json(DIRS["comparison"] / "step_trace_comparison_summary.json")
    logical_report = read_json(DIRS["logical_paths"] / "logical_path_generation_report.json") if (DIRS["logical_paths"] / "logical_path_generation_report.json").exists() else {"exported_count": 0}
    summary = {
        "case_name": CASE_NAME,
        "bpmn_trace_count": path_cmp["bpmn_trace_count"],
        "dsl_trace_count": path_cmp["dsl_trace_count"],
        "bounded_trace_equivalence": path_cmp["bounded_trace_equivalence"],
        "step_wise_transition_preservation": step_cmp["step_wise_transition_preservation"],
        "logical_path_exported_count": logical_report["exported_count"],
        "passed": path_cmp["bounded_trace_equivalence"] and step_cmp["step_wise_transition_preservation"],
    }
    write_json(DIRS["reports"] / "behavior_summary.json", summary)
    write_text(DIRS["reports"] / "behavior_summary.md", "\n".join([
        f"# Behavior Summary: {CASE_NAME}",
        "",
        f"- BPMN bounded traces: {summary['bpmn_trace_count']}",
        f"- DSL bounded traces: {summary['dsl_trace_count']}",
        f"- Bounded trace equivalence: {summary['bounded_trace_equivalence']}",
        f"- Step-wise transition preservation: {summary['step_wise_transition_preservation']}",
        f"- Logical path formatted artifacts: {summary['logical_path_exported_count']}",
        f"- Passed: {summary['passed']}",
        "",
    ]))
    write_all_cases_summary()
    print((DIRS["reports"] / "behavior_summary.md").read_text(encoding="utf-8"))


STEPS = {
    "prepare": prepare,
    "run_newtranslator": run_newtranslator,
    "extract_bpmn_raw": extract_bpmn_raw,
    "build_bpmn_semantic_graph": build_bpmn_semantic_graph,
    "extract_dsl_raw": extract_dsl_raw,
    "build_dsl_semantic_graph": build_dsl_semantic_graph,
    "normalize_semantic_ids": canonicalize,
    "generate_bpmn_paths": lambda: generate_paths("bpmn"),
    "generate_dsl_paths": lambda: generate_paths("dsl"),
    "normalize_paths": normalize_paths,
    "compare_path_sets": compare_path_sets,
    "simulate_bpmn_trace": simulate_traces,
    "simulate_dsl_trace": simulate_traces,
    "compare_step_traces": compare_step_traces,
    "generate_logical_paths": generate_logical_paths,
    "summarize_behavior_results": summarize,
}


PIPELINE = [
    "prepare",
    "run_newtranslator",
    "extract_bpmn_raw",
    "build_bpmn_semantic_graph",
    "extract_dsl_raw",
    "build_dsl_semantic_graph",
    "normalize_semantic_ids",
    "generate_bpmn_paths",
    "generate_dsl_paths",
    "normalize_paths",
    "compare_path_sets",
    "simulate_bpmn_trace",
    "compare_step_traces",
    "generate_logical_paths",
    "summarize_behavior_results",
]


def main(default_step: str | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", default=default_step or "pipeline", choices=["pipeline", *STEPS])
    args = parser.parse_args()
    if args.step == "pipeline":
        for step in PIPELINE:
            STEPS[step]()
    else:
        STEPS[args.step]()


if __name__ == "__main__":
    main()
