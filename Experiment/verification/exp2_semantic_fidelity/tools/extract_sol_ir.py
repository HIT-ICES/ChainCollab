#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.common import command_exists, dump_json, run_command
from tools.normalize_ir import normalize_solidity_ir


def parse_src(src: str) -> tuple[int, int]:
    start_text, length_text, *_rest = src.split(":")
    start = int(start_text)
    length = int(length_text)
    return start, length


def text_from_src(source: str, src: str | None) -> str:
    if not src:
        return ""
    start, length = parse_src(src)
    return source[start : start + length]


def walk(node: Any, visit) -> None:
    if isinstance(node, dict):
        if "nodeType" in node:
            visit(node)
        for value in node.values():
            walk(value, visit)
    elif isinstance(node, list):
        for item in node:
            walk(item, visit)


def load_ast(sol_path: Path) -> tuple[dict[str, Any], str]:
    if not command_exists("solc"):
        raise RuntimeError("solc was not found in PATH. Install solc, then rerun extract_sol_ir.py.")
    payload = {
        "language": "Solidity",
        "sources": {sol_path.name: {"content": sol_path.read_text(encoding="utf-8")}},
        "settings": {"outputSelection": {"*": {"": ["ast"]}}},
    }
    proc = run_command(
        ["solc", "--standard-json"],
        cwd=sol_path.parent,
        context="solc ast export",
        check=True,
        input_text=json.dumps(payload),
    )
    cleaned = proc.stdout.replace(
        ">>> Cannot retry compilation with SMT because there are no SMT solvers available.\n",
        "",
    )
    parsed = json.loads(cleaned)
    source_name = next(iter(parsed.get("sources", {})), None)
    if not source_name:
        raise RuntimeError("solc did not return any source AST.")
    source_ast = parsed["sources"][source_name].get("ast")
    if not source_ast:
        raise RuntimeError("solc output did not include an AST.")
    return source_ast, sol_path.read_text(encoding="utf-8")


def collect_ir(ast_root: dict[str, Any], source: str, sol_path: Path) -> dict[str, Any]:
    output: dict[str, Any] = {
        "contract": "",
        "state_fields": [],
        "functions": [],
        "event_defs": [],
        "message_keys": [],
        "gateway_keys": [],
        "event_keys": [],
        "businessrule_keys": [],
        "unsupported": [],
        "source_file": str(sol_path),
    }
    state: dict[str, Any] = {"contract": "", "function": None}

    def visit(node: dict[str, Any]) -> None:
        node_type = node.get("nodeType")
        if node_type == "ContractDefinition":
            if not output["contract"]:
                output["contract"] = node.get("name", "")
            state["contract"] = node.get("name", "")
        elif node_type == "StructDefinition" and node.get("name") == "StateMemory":
            for member in node.get("members", []):
                output["state_fields"].append({"name": member.get("name", ""), "type": member.get("typeDescriptions", {}).get("typeString", "")})
        elif node_type == "EnumDefinition":
            name = node.get("name", "")
            values = [{"name": member.get("name", "")} for member in node.get("members", [])]
            if name == "MessageKey":
                output["message_keys"].extend(values)
            elif name == "GatewayKey":
                output["gateway_keys"].extend(values)
            elif name == "EventKey":
                output["event_keys"].extend(values)
            elif name == "BusinessRuleKey":
                output["businessrule_keys"].extend(values)
        elif node_type == "EventDefinition":
            output["event_defs"].append({"name": node.get("name", "")})
        elif node_type == "FunctionDefinition":
            name = node.get("name") or node.get("kind") or ""
            fn_ir = {
                "name": name,
                "kind": node.get("kind", ""),
                "visibility": node.get("visibility", ""),
                "body": text_from_src(source, node.get("body", {}).get("src") if node.get("body") else node.get("src")),
                "ifs": [],
                "requires": [],
            }
            body = node.get("body") or {}
            for stmt in body.get("statements", []):
                if stmt.get("nodeType") == "IfStatement":
                    fn_ir["ifs"].append(
                        {
                            "condition": text_from_src(source, stmt.get("condition", {}).get("src")),
                            "then": text_from_src(source, stmt.get("trueBody", {}).get("src")),
                            "else": text_from_src(source, stmt.get("falseBody", {}).get("src")) if stmt.get("falseBody") else "",
                        }
                    )
                if stmt.get("nodeType") == "ExpressionStatement":
                    expr = stmt.get("expression", {})
                    if expr.get("nodeType") == "FunctionCall":
                        callee = text_from_src(source, expr.get("expression", {}).get("src"))
                        if callee in {"require", "assert"}:
                            fn_ir["requires"].append({"text": text_from_src(source, expr.get("src"))})
            output["functions"].append(fn_ir)

    walk(ast_root, visit)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract normalized Solidity IR via solc official AST.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    ast_root, source = load_ast(input_path)
    raw = collect_ir(ast_root, source, input_path)
    dump_json(output_path, normalize_solidity_ir(raw, input_path))


if __name__ == "__main__":
    main()
