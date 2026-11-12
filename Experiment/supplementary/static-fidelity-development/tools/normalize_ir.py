from __future__ import annotations

import re
from pathlib import Path
from typing import Any


RE_MESSAGE_KEY = re.compile(r"Message(?:Key\.)?\.?([A-Za-z0-9_]+)|\"(Message_[A-Za-z0-9_]+)\"")
RE_GATEWAY_KEY = re.compile(r"Gateway(?:Key\.)?\.?([A-Za-z0-9_]+)|\"([A-Za-z0-9_]*Gateway_[A-Za-z0-9_]+|Gateway_[A-Za-z0-9_]+)\"")
RE_EVENT_KEY = re.compile(r"Event(?:Key\.)?\.?([A-Za-z0-9_]+)|\"([A-Za-z0-9_]*Event_[A-Za-z0-9_]+|Event_[A-Za-z0-9_]+)\"")
RE_RULE_KEY = re.compile(r"BusinessRule(?:Key\.)?\.?([A-Za-z0-9_]+)|\"([A-Za-z0-9_]+)\"")


def _pick(match: re.Match[str] | None) -> str | None:
    if not match:
        return None
    for idx in range(1, (match.lastindex or 0) + 1):
        value = match.group(idx)
        if value:
            return value
    return None


def canonical_trigger(kind: str, name: str, phase: str | None = None) -> dict[str, Any]:
    base = {"name": name}
    if kind == "event":
        if phase == "start":
            return {"kind": "start_event", **base}
        return {"kind": "event_completed", **base}
    if kind == "message":
        return {"kind": f"message_{phase or 'completed'}", **base}
    if kind == "gateway":
        return {"kind": "gateway_completed", **base}
    if kind == "businessrule":
        return {"kind": f"rule_{phase or 'done'}", **base}
    if kind == "oracletask":
        return {"kind": "oracle_done", **base}
    return {"kind": kind, **base}


def normalize_action(op: str, target: str | None = None, *, var: str | None = None, value: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"op": op}
    if target:
        payload["target"] = target
    if var:
        payload["var"] = var
    if value is not None:
        payload["value"] = value
    return payload


def infer_event_type(name: str) -> str:
    lowered = name.lower()
    if lowered.startswith("startevent") or lowered.startswith("start_event"):
        return "start"
    if lowered.startswith("endevent") or lowered.startswith("end_event"):
        return "end"
    return "event"


def _extract_actions_from_go_text(text: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for op_name, op in (
        ("ChangeMsgState", "message"),
        ("ChangeGatewayState", "gateway"),
        ("ChangeGtwState", "gateway"),
        ("ChangeEventState", "event"),
        ("ChangeBusinessRuleState", "businessrule"),
    ):
        for target, state in re.findall(rf'{op_name}\([^)]*,\s*"([^"]+)"\s*,\s*([A-Z]+)\)', text):
            mapped_op = {"ENABLED": "enable", "DISABLED": "disable", "COMPLETED": "complete"}.get(state, state.lower())
            actions.append(normalize_action(mapped_op, target))
    for var, value in re.findall(r"InstanceStateMemory\.([A-Za-z0-9_]+)\s*=\s*([^\n;]+)", text):
        actions.append(normalize_action("set", var=var, value=value.strip()))
    return actions


def _extract_branch_actions_from_go_if(branch: dict[str, Any]) -> list[dict[str, Any]]:
    body = branch.get("then", "")
    return _extract_actions_from_go_text(body)


def normalize_go_ir(raw: dict[str, Any], source_path: Path | None = None) -> dict[str, Any]:
    globals_ir = raw.get("state_fields", [])
    handlers: list[dict[str, Any]] = []
    coverage = {"messages": [], "gateways": [], "events": [], "businessrules": []}

    for fn in raw.get("functions", []):
        name = fn["name"]
        trigger: dict[str, Any] | None = None
        element_kind: str | None = None
        element_name: str | None = None
        body_text = fn.get("body", "")
        if name.endswith("_Send"):
            element_kind = "message"
            element_name = name[: -len("_Send")]
            trigger = canonical_trigger("message", element_name, "sent")
        elif name.endswith("_Complete"):
            element_kind = "message"
            element_name = name[: -len("_Complete")]
            trigger = canonical_trigger("message", element_name, "completed")
        elif name.startswith("StartEvent_"):
            element_kind = "event"
            element_name = name
            trigger = canonical_trigger("event", element_name, "start")
        elif name.startswith("EndEvent_"):
            element_kind = "event"
            element_name = name
            trigger = canonical_trigger("event", element_name, "completed")
        elif "_Continue" in name:
            element_kind = "businessrule"
            element_name = name[: name.index("_Continue")]
            trigger = canonical_trigger("businessrule", element_name, "done")
        elif "Gateway_" in name or name.startswith("ExclusiveGateway_") or name.startswith("ParallelGateway_") or name.startswith("EventBasedGateway_"):
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif name.startswith("Activity_"):
            element_kind = "businessrule"
            element_name = name
            trigger = canonical_trigger("businessrule", element_name, "ready")
        elif f'ChangeGatewayState(ctx, instance, "{name}", COMPLETED)' in body_text or f'ChangeGtwState(ctx, instance, "{name}", COMPLETED)' in body_text:
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif f'ReadGtw(ctx, instanceID, "{name}")' in body_text:
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif f'ChangeBusinessRuleState(ctx, instance, "{name}", COMPLETED)' in body_text:
            element_kind = "businessrule"
            element_name = name
            trigger = canonical_trigger("businessrule", element_name, "done")

        if not trigger or not element_kind or not element_name:
            continue

        coverage[f"{element_kind}s" if element_kind != "businessrule" else "businessrules"].append(element_name)
        actions = _extract_actions_from_go_text(body_text)
        branches: list[dict[str, Any]] = []
        for branch in fn.get("ifs") or []:
            branches.append(
                {
                    "condition": branch.get("condition", ""),
                    "actions": _extract_branch_actions_from_go_if(branch),
                    "else_actions": _extract_actions_from_go_text(branch.get("else", "")),
                }
            )
        handlers.append(
            {
                "name": name,
                "language": "go",
                "element_kind": element_kind,
                "element_name": element_name,
                "trigger": trigger,
                "guards": [item.get("condition", "") for item in (fn.get("ifs") or [])],
                "actions": actions,
                "branches": branches,
                "body": body_text,
            }
        )

    return {
        "contract": raw.get("contract", ""),
        "source_file": str(source_path) if source_path else raw.get("source_file", ""),
        "globals": globals_ir,
        "handlers": handlers,
        "elements": {key: sorted(set(values)) for key, values in coverage.items()},
        "unsupported": [],
        "raw_summary": {
            "function_count": len(raw.get("functions", [])),
            "struct_count": len(raw.get("structs", [])),
        },
    }


def _extract_actions_from_solidity_text(text: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for target in re.findall(r"inst\.messages\[MessageKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.ENABLED", text):
        actions.append(normalize_action("enable", target))
    for target in re.findall(r"inst\.messages\[MessageKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.DISABLED", text):
        actions.append(normalize_action("disable", target))
    for target in re.findall(r"inst\.messages\[MessageKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.COMPLETED", text):
        actions.append(normalize_action("complete", target))
    for target in re.findall(r"inst\.gateways\[GatewayKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.ENABLED", text):
        actions.append(normalize_action("enable", target))
    for target in re.findall(r"inst\.gateways\[GatewayKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.DISABLED", text):
        actions.append(normalize_action("disable", target))
    for target in re.findall(r"inst\.gateways\[GatewayKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.COMPLETED", text):
        actions.append(normalize_action("complete", target))
    for target in re.findall(r"inst\.events\[EventKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.ENABLED", text):
        actions.append(normalize_action("enable", target))
    for target in re.findall(r"inst\.events\[EventKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.COMPLETED", text):
        actions.append(normalize_action("complete", target))
    for target in re.findall(r"inst\.businessRules\[BusinessRuleKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.ENABLED", text):
        actions.append(normalize_action("enable", target))
    for target in re.findall(r"inst\.businessRules\[BusinessRuleKey\.([A-Za-z0-9_]+)\]\.state\s*=\s*ElementState\.COMPLETED", text):
        actions.append(normalize_action("complete", target))
    for var, value in re.findall(r"inst\.stateMemory\.([A-Za-z0-9_]+)\s*=\s*([^;]+);", text):
        actions.append(normalize_action("set", var=var, value=value.strip()))
    return actions


def normalize_solidity_ir(raw: dict[str, Any], source_path: Path | None = None) -> dict[str, Any]:
    handlers: list[dict[str, Any]] = []
    coverage = {
        "messages": sorted({item["name"] for item in raw.get("message_keys", [])}),
        "gateways": sorted({item["name"] for item in raw.get("gateway_keys", [])}),
        "events": sorted({item["name"] for item in raw.get("event_keys", [])}),
        "businessrules": sorted({item["name"] for item in raw.get("businessrule_keys", [])}),
    }

    for fn in raw.get("functions", []):
        name = fn["name"]
        trigger: dict[str, Any] | None = None
        element_kind: str | None = None
        element_name: str | None = None
        if name.startswith("Message_") and name.endswith("_Send"):
            element_kind = "message"
            element_name = name[: -len("_Send")]
            trigger = canonical_trigger("message", element_name, "sent")
        elif name.endswith("_Send"):
            element_kind = "message"
            element_name = name[: -len("_Send")]
            trigger = canonical_trigger("message", element_name, "sent")
        elif name.startswith("StartEvent_"):
            element_kind = "event"
            element_name = name
            trigger = canonical_trigger("event", element_name, "start")
        elif name.startswith("EndEvent_"):
            element_kind = "event"
            element_name = name
            trigger = canonical_trigger("event", element_name, "completed")
        elif "_Continue" in name:
            element_kind = "businessrule"
            element_name = name[: name.index("_Continue")]
            trigger = canonical_trigger("businessrule", element_name, "done")
        elif "Gateway_" in name or name.startswith("ExclusiveGateway_") or name.startswith("ParallelGateway_") or name.startswith("EventBasedGateway_"):
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif name.startswith("Activity_"):
            element_kind = "businessrule"
            element_name = name
            trigger = canonical_trigger("businessrule", element_name, "ready")
        elif name in coverage["gateways"]:
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif name in coverage["businessrules"]:
            element_kind = "businessrule"
            element_name = name
            trigger = canonical_trigger("businessrule", element_name, "ready")
        elif re.search(rf"inst\.gateways\[GatewayKey\.{re.escape(name)}\]\.state\s*=\s*ElementState\.COMPLETED", fn.get("body", "")):
            element_kind = "gateway"
            element_name = name
            trigger = canonical_trigger("gateway", element_name)
        elif re.search(rf"inst\.businessRules\[BusinessRuleKey\.{re.escape(name)}\]\.state\s*=\s*ElementState\.COMPLETED", fn.get("body", "")):
            element_kind = "businessrule"
            element_name = name
            trigger = canonical_trigger("businessrule", element_name, "done")

        if not trigger or not element_kind or not element_name:
            continue

        handlers.append(
            {
                "name": name,
                "language": "solidity",
                "element_kind": element_kind,
                "element_name": element_name,
                "trigger": trigger,
                "guards": [item.get("condition", "") for item in (fn.get("ifs") or [])]
                + [item.get("text", "") for item in (fn.get("requires") or [])],
                "actions": _extract_actions_from_solidity_text(fn.get("body", "")),
                "branches": [
                    {
                        "condition": item.get("condition", ""),
                        "actions": _extract_actions_from_solidity_text(item.get("then", "")),
                        "else_actions": _extract_actions_from_solidity_text(item.get("else", "")),
                    }
                    for item in (fn.get("ifs") or [])
                ],
                "body": fn.get("body", ""),
            }
        )

    return {
        "contract": raw.get("contract", ""),
        "source_file": str(source_path) if source_path else raw.get("source_file", ""),
        "globals": raw.get("state_fields", []),
        "handlers": handlers,
        "elements": coverage,
        "unsupported": raw.get("unsupported", []),
        "raw_summary": {
            "function_count": len(raw.get("functions", [])),
            "event_count": len(raw.get("event_defs", [])),
        },
    }
