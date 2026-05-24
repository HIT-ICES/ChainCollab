#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


TAG_VERSION = "0.1.0"
NS_BPMN = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def node_index(tag: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in tag.get("nodes", [])}


def edge_index(tag: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {edge["id"]: edge for edge in tag.get("edges", [])}


def edges_by_type(tag: Dict[str, Any], edge_type: str) -> List[Dict[str, Any]]:
    return [edge for edge in tag.get("edges", []) if edge.get("type") == edge_type]


def nodes_by_type(tag: Dict[str, Any], node_type: str) -> List[Dict[str, Any]]:
    return [node for node in tag.get("nodes", []) if node.get("type") == node_type]


def find_node(tag: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    return node_index(tag).get(node_id)


def find_edge(
    tag: Dict[str, Any],
    edge_type: str,
    source: Optional[str] = None,
    target: Optional[str] = None,
    attr_filters: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    for edge in edges_by_type(tag, edge_type):
        if source is not None and edge.get("source") != source:
            continue
        if target is not None and edge.get("target") != target:
            continue
        attrs = edge.get("attrs", {})
        if attr_filters and any(attrs.get(k) != v for k, v in attr_filters.items()):
            continue
        return edge
    return None


def make_tag(case_name: str, model_type: str, source_file: Path, extractor_name: str, basis: Iterable[str]) -> Dict[str, Any]:
    return {
        "tag_version": TAG_VERSION,
        "case_name": case_name,
        "model_type": model_type,
        "source_file": str(source_file),
        "extractor": {
            "name": extractor_name,
            "version": TAG_VERSION,
            "implementation_basis": list(basis),
        },
        "nodes": [],
        "edges": [],
        "derived": [],
        "warnings": [],
    }


def add_node(tag: Dict[str, Any], node_id: str, node_type: str, name: str = "", attrs: Optional[Dict[str, Any]] = None) -> None:
    if not node_id:
        return
    if find_node(tag, node_id):
        return
    tag["nodes"].append(
        {
            "id": node_id,
            "type": node_type,
            "name": name or "",
            "attrs": attrs or {},
        }
    )


def add_edge(
    tag: Dict[str, Any],
    edge_id: str,
    edge_type: str,
    source: str,
    target: str,
    attrs: Optional[Dict[str, Any]] = None,
) -> None:
    if not edge_id or not source or not target:
        return
    if edge_id in edge_index(tag):
        return
    tag["edges"].append(
        {
            "id": edge_id,
            "type": edge_type,
            "source": source,
            "target": target,
            "attrs": attrs or {},
        }
    )


def public_the_name(name: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in (name or "").strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    return normalized[:1].upper() + normalized[1:] if normalized else normalized


def map_bpmn_type(origin_type: str) -> str:
    return {
        "string": "string",
        "number": "int",
        "integer": "int",
        "boolean": "bool",
        "float": "float64",
        "float64": "float64",
    }.get(origin_type or "string", origin_type or "string")


def parse_json_documentation(documentation: str) -> Dict[str, Any]:
    if not documentation:
        return {}
    try:
        payload = json.loads(documentation)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def summarize_message_schema(documentation: str) -> str:
    doc = parse_json_documentation(documentation)
    if doc and (doc.get("properties") or doc.get("files")):
        return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return documentation or ""


def parse_condition(raw_condition: str) -> Optional[Dict[str, str]]:
    if not raw_condition:
        return None
    for relation in ("==", "!=", ">=", "<=", ">", "<"):
        if relation in raw_condition:
            name, value = raw_condition.split(relation, 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return {
                "name": name.strip(),
                "relation": relation,
                "value": value,
            }
    return None


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escape = False
    for idx in range(open_index, len(text)):
        ch = text[idx]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx
    raise ValueError(f"No matching brace for index {open_index}")


def extract_named_block(text: str, keyword: str, start: int = 0) -> Optional[Dict[str, Any]]:
    match = re.search(rf"\b{re.escape(keyword)}\b\s*(?:([A-Za-z_][A-Za-z0-9_]*)\s*)?\{{", text[start:])
    if not match:
        return None
    abs_start = start + match.start()
    open_index = text.find("{", abs_start)
    close_index = find_matching_brace(text, open_index)
    return {
        "name": match.group(1) or "",
        "start": abs_start,
        "open": open_index,
        "close": close_index,
        "body": text[open_index + 1:close_index],
    }


def iter_named_blocks(text: str, keyword: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    pos = 0
    while True:
        block = extract_named_block(text, keyword, pos)
        if block is None:
            break
        blocks.append(block)
        pos = block["close"] + 1
    return blocks

