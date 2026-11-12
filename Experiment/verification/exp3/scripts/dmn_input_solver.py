from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from common import normalize_name


@dataclass
class DmnRule:
    inputs: Dict[str, str]
    outputs: Dict[str, Any]


@dataclass
class DmnDecision:
    decision_id: str
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    rules: List[DmnRule]


def normalize_literal(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    previous = None
    while text and text != previous:
        previous = text
        try:
            parsed = json.loads(text)
            if isinstance(parsed, str):
                text = parsed.strip()
                continue
        except Exception:
            pass
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()
            continue
        if text.startswith('\\"') and text.endswith('\\"'):
            text = text[2:-2].strip()
    return text


def parse_output_value(text: str, type_ref: str) -> Any:
    value = normalize_literal(text)
    kind = str(type_ref or "").lower()
    if kind in {"number", "integer", "int", "long", "double"}:
        try:
            return int(value) if float(value).is_integer() else float(value)
        except Exception:
            return value
    if kind in {"boolean", "bool"}:
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return value


def values_equal(left: Any, right: Any) -> bool:
    return normalize_literal(left) == normalize_literal(right)


def namespace(root: ET.Element) -> str:
    return root.tag.split("}", 1)[0][1:] if root.tag.startswith("{") else ""


def child_text(parent: ET.Element, ns: str, path: str) -> str:
    item = parent.find(path.format(ns=ns))
    return (item.text or "").strip() if item is not None and item.text else ""


def parse_dmn(path: Path) -> Dict[str, DmnDecision]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    ns = namespace(root)
    decisions: Dict[str, DmnDecision] = {}
    for decision in root.findall(f".//{{{ns}}}decision"):
        decision_id = str(decision.get("id") or "")
        table = decision.find(f".//{{{ns}}}decisionTable")
        if not decision_id or table is None:
            continue

        inputs = []
        for clause in table.findall(f"./{{{ns}}}input"):
            name = child_text(clause, ns, ".//{{{ns}}}inputExpression/{{{ns}}}text")
            if name:
                inputs.append(name)

        output_types: Dict[str, str] = {}
        outputs = []
        for clause in table.findall(f"./{{{ns}}}output"):
            name = str(clause.get("name") or clause.get("label") or clause.get("id") or "")
            if not name:
                continue
            outputs.append(name)
            output_types[name] = str(clause.get("typeRef") or "string")

        dependencies = []
        for req in decision.findall(f"./{{{ns}}}informationRequirement"):
            required = req.find(f"./{{{ns}}}requiredDecision")
            href = str(required.get("href") or "") if required is not None else ""
            if href.startswith("#"):
                dependencies.append(href[1:])

        rules = []
        for rule in table.findall(f"./{{{ns}}}rule"):
            input_entries = rule.findall(f"./{{{ns}}}inputEntry")
            output_entries = rule.findall(f"./{{{ns}}}outputEntry")
            rule_inputs = {}
            for index, input_name in enumerate(inputs):
                if index >= len(input_entries):
                    continue
                text = child_text(input_entries[index], ns, "./{{{ns}}}text")
                if text:
                    rule_inputs[input_name] = text
            rule_outputs = {}
            for index, output_name in enumerate(outputs):
                if index >= len(output_entries):
                    continue
                text = child_text(output_entries[index], ns, "./{{{ns}}}text")
                if text:
                    rule_outputs[output_name] = parse_output_value(text, output_types.get(output_name, "string"))
            rules.append(DmnRule(rule_inputs, rule_outputs))

        decisions[decision_id] = DmnDecision(decision_id, inputs, outputs, dependencies, rules)
    return decisions


def expression_exact_value(expression: str) -> Optional[Any]:
    text = expression.strip()
    if not text:
        return None
    if any(text.startswith(prefix) for prefix in (">=", "<=", ">", "<")) or ".." in text:
        return None
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(text) if float(text).is_integer() else float(text)
    except Exception:
        return normalize_literal(text)


def sample_for_expression(expression: str) -> Optional[Any]:
    text = expression.strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if ".." in text:
        match = re.match(r"^\s*([\[(])?\s*(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)\s*([\])])?\s*$", text)
        if match:
            left_inclusive = match.group(1) != "("
            right_inclusive = match.group(4) != ")"
            low = float(match.group(2))
            high = float(match.group(3))
            candidate = (low + high) / 2
            if candidate == low and not left_inclusive:
                candidate += 1
            if candidate == high and not right_inclusive:
                candidate -= 1
            return int(candidate) if candidate.is_integer() else candidate
    for op, delta in ((">=", 0), (">", 1), ("<=", 0), ("<", -1)):
        if text.startswith(op):
            try:
                bound = float(text[len(op):].strip())
            except Exception:
                return None
            value = bound + delta
            return int(value) if value.is_integer() else value
    exact = expression_exact_value(text)
    return exact


def output_producers(decisions: Dict[str, DmnDecision]) -> Dict[str, List[str]]:
    producers: Dict[str, List[str]] = {}
    for decision in decisions.values():
        for output in decision.outputs:
            producers.setdefault(normalize_name(output), []).append(decision.decision_id)
    return producers


def solve_decision(
    decisions: Dict[str, DmnDecision],
    decision_id: str,
    desired_outputs: Dict[str, Any],
    *,
    seen: Optional[set[str]] = None,
) -> Optional[Dict[str, Any]]:
    if seen is None:
        seen = set()
    if decision_id in seen:
        return None
    decision = decisions.get(decision_id)
    if decision is None:
        return None
    producers = output_producers(decisions)
    desired_by_norm = {normalize_name(key): value for key, value in desired_outputs.items()}

    for rule in decision.rules:
        if any(
            normalize_name(output) in desired_by_norm
            and not values_equal(value, desired_by_norm[normalize_name(output)])
            for output, value in rule.outputs.items()
        ):
            continue
        if not all(name in {normalize_name(key) for key in rule.outputs} for name in desired_by_norm):
            continue

        assignments: Dict[str, Any] = {}
        failed = False
        for input_name, expression in rule.inputs.items():
            dep_ids = [
                item
                for item in producers.get(normalize_name(input_name), [])
                if item in decision.dependencies
            ]
            exact = expression_exact_value(expression)
            if dep_ids and exact is not None:
                dep_assignments = solve_decision(
                    decisions,
                    dep_ids[0],
                    {input_name: exact},
                    seen=seen | {decision_id},
                )
                if dep_assignments is None:
                    failed = True
                    break
                assignments.update(dep_assignments)
                continue

            sample = sample_for_expression(expression)
            if sample is not None:
                assignments[input_name] = sample
        if not failed:
            return assignments
    return None


def find_decision_for_outputs(decisions: Dict[str, DmnDecision], desired_outputs: Dict[str, Any]) -> Optional[str]:
    desired = {normalize_name(key) for key in desired_outputs}
    for decision in decisions.values():
        if desired.issubset({normalize_name(item) for item in decision.outputs}):
            return decision.decision_id
    return None


def synthesize_dmn_inputs(dmn_file: Path, desired_outputs: Dict[str, Any], decision_id: str = "") -> Dict[str, Any]:
    decisions = parse_dmn(dmn_file)
    target_decision = decision_id if decision_id in decisions else ""
    if not target_decision:
        target_decision = find_decision_for_outputs(decisions, desired_outputs) or ""
    if not target_decision:
        return {}
    return solve_decision(decisions, target_decision, desired_outputs) or {}
