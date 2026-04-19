from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TYPE_ALIASES = {
    "string": {"string", "string memory"},
    "int": {"int", "int256", "int64", "int32"},
    "bool": {"bool"},
    "float": {"float", "float64", "float32"},
}


@dataclass
class MatchResult:
    matched: bool
    evidence: List[str]
    missing_reason: str = ""
    severity: str = "medium"


def normalize_name(value: Optional[str]) -> str:
    raw = (value or "").strip()
    chars = []
    for ch in raw:
        chars.append(ch.lower() if ch.isalnum() else "_")
    normalized = "".join(chars)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def compatible_type(dsl_type: Optional[str], code_type: Optional[str]) -> bool:
    if not dsl_type or not code_type:
        return False
    dsl = normalize_name(dsl_type)
    code = normalize_name(code_type)
    return code in TYPE_ALIASES.get(dsl, {dsl})


def has_name_match(name: str, candidates: Iterable[str]) -> bool:
    expected = normalize_name(name)
    for item in candidates:
        if expected and expected == normalize_name(item):
            return True
    return False


def find_field(fields: Sequence[Dict[str, Any]], target_name: str) -> Optional[Dict[str, Any]]:
    expected = normalize_name(target_name)
    for field in fields:
        if normalize_name(field.get("name")) == expected:
            return field
    return None


def find_functions(functions: Sequence[Dict[str, Any]], prefix: str) -> List[Dict[str, Any]]:
    expected = normalize_name(prefix)
    return [
        function
        for function in functions
        if normalize_name(function.get("name", "")).startswith(expected)
    ]


def find_exact_function(functions: Sequence[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    expected = normalize_name(name)
    for function in functions:
        if normalize_name(function.get("name")) == expected:
            return function
    return None


def select_calls(calls: Sequence[Dict[str, Any]], function_names: Sequence[str]) -> List[Dict[str, Any]]:
    names = {normalize_name(name) for name in function_names}
    return [call for call in calls if normalize_name(call.get("function")) in names]


def select_assignments(assignments: Sequence[Dict[str, Any]], function_names: Sequence[str]) -> List[Dict[str, Any]]:
    names = {normalize_name(name) for name in function_names}
    return [item for item in assignments if normalize_name(item.get("function")) in names]


def select_conditions(entries: Sequence[Dict[str, Any]], function_names: Sequence[str]) -> List[Dict[str, Any]]:
    entries = entries or []
    names = {normalize_name(name) for name in function_names}
    return [item for item in entries if normalize_name(item.get("function")) in names]


def flow_trigger_candidates(flow: Dict[str, Any], target: str) -> List[str]:
    trigger = flow.get("trigger", {})
    trigger_type = trigger.get("type")
    trigger_name = trigger.get("name")
    if not trigger_name:
        return []
    if trigger_type in {"event", "gateway", "parallel"}:
        return [trigger_name]
    if trigger_type == "message":
        if target == "go":
            if trigger.get("state") == "completed":
                return [f"{trigger_name}_Complete", trigger_name]
            return [f"{trigger_name}_Send", trigger_name]
        return [f"{trigger_name}_Send", trigger_name]
    if trigger_type == "businessrule":
        return [trigger_name, f"{trigger_name}_Continue"]
    if trigger_type == "oracletask":
        return [trigger_name]
    if trigger_type == "start":
        return [trigger_name]
    return [trigger_name]


def iter_flow_actions(flow: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions = list(flow.get("actions", []))
    for condition in flow.get("conditions", []):
        actions.extend(condition.get("actions", []))
    return actions


def action_state_value(action_kind: str) -> Optional[str]:
    if action_kind == "enable":
        return "enabled"
    if action_kind == "disable":
        return "disabled"
    return None


def summarize_evidence(lines: List[str], fallback: str, *, matched: bool, severity: str = "medium") -> MatchResult:
    return MatchResult(
        matched=matched,
        evidence=lines,
        missing_reason="" if matched else fallback,
        severity=severity,
    )


def verify_global_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    field = find_field(go_ast.get("state_fields", []), item["name"])
    if not field:
        return summarize_evidence([], "No matching field found in Go StateMemory.", matched=False)
    evidence = [f"StateMemory.{field['name']} : {field.get('type', '')}"]
    if compatible_type(item.get("type"), field.get("type")):
        return summarize_evidence(evidence, "", matched=True, severity="low")
    return summarize_evidence(evidence, "Field exists but type is not aligned.", matched=False)


def verify_global_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    field = find_field(sol_ast.get("state_variables", []), item["name"])
    if not field:
        return summarize_evidence([], "No matching Solidity state variable found.", matched=False)
    evidence = [f"{field.get('container', 'contract')}.{field['name']} : {field.get('type', '')}"]
    if compatible_type(item.get("type"), field.get("type")):
        return summarize_evidence(evidence, "", matched=True, severity="low")
    return summarize_evidence(evidence, "State variable exists but type is not aligned.", matched=False)


def verify_participant_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    functions = {entry.get("name", "") for entry in go_ast.get("functions", [])}
    literals = go_ast.get("string_literals", [])
    evidence = []
    if has_name_match(item["name"], literals):
        evidence.append(f"participant literal `{item['name']}` appears in generated Go")
    if {"check_participant", "check_msp"} & {normalize_name(name) for name in functions}:
        evidence.append("Go participant guard helpers exist: check_participant/check_msp")
    if evidence:
        return summarize_evidence(evidence, "", matched=True, severity="low")
    return summarize_evidence([], "No participant identifier or access-control helper found in Go.", matched=False)


def verify_participant_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    enum_values = []
    for enum in sol_ast.get("enums", []):
        enum_values.extend(enum.get("values", []))
    calls = sol_ast.get("calls", [])
    evidence = []
    if has_name_match(item["name"], enum_values):
        evidence.append(f"ParticipantKey enum contains `{item['name']}`")
    if any(call.get("callee") == "_checkParticipant" for call in calls):
        evidence.append("Solidity uses _checkParticipant(msg.sender/identity registry)")
    if evidence:
        return summarize_evidence(evidence, "", matched=True, severity="low")
    return summarize_evidence([], "No participant enum or sender check found in Solidity.", matched=False)


def verify_message_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(go_ast.get("functions", []), item["name"])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:3]]
    calls = select_calls(go_ast.get("calls", []), [entry["name"] for entry in matched_functions])
    literals = go_ast.get("string_literals", [])
    if item.get("from") and has_name_match(item["from"], literals):
        evidence.append(f"sender participant `{item['from']}` preserved in Go literals")
    if item.get("to") and has_name_match(item["to"], literals):
        evidence.append(f"receiver participant `{item['to']}` preserved in Go literals")
    if any("check_participant" in call.get("callee", "") for call in calls):
        evidence.append("participant guard in message handler")
    if any("ChangeMsgState" in call.get("callee", "") for call in calls):
        evidence.append("message state transition via ChangeMsgState")
    matched = bool(matched_functions) and any("ChangeMsgState" in call.get("callee", "") for call in calls)
    return summarize_evidence(evidence, "Missing Go message handler or message state transition.", matched=matched)


def verify_message_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(sol_ast.get("functions", []), item["name"])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:3]]
    assignments = select_assignments(sol_ast.get("assignments", []), [entry["name"] for entry in matched_functions])
    calls = select_calls(sol_ast.get("calls", []), [entry["name"] for entry in matched_functions])
    enum_values = []
    for enum in sol_ast.get("enums", []):
        enum_values.extend(enum.get("values", []))
    if item.get("from") and has_name_match(item["from"], enum_values):
        evidence.append(f"sender participant `{item['from']}` preserved in ParticipantKey")
    if item.get("to") and has_name_match(item["to"], enum_values):
        evidence.append(f"receiver participant `{item['to']}` preserved in ParticipantKey")
    if any(call.get("callee") == "_checkParticipant" for call in calls):
        evidence.append("participant guard via _checkParticipant")
    if any("state" in normalize_name(assignment.get("lhs")) for assignment in assignments):
        evidence.append("message state assignment in handler")
    matched = bool(matched_functions) and any("state" in normalize_name(assignment.get("lhs")) for assignment in assignments)
    return summarize_evidence(evidence, "Missing Solidity message function or state assignment.", matched=matched)


def verify_gateway_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(go_ast.get("functions", []), item["name"])
    function_names = [entry["name"] for entry in matched_functions]
    evidence = [f"function {entry['name']}" for entry in matched_functions[:2]]
    if_conditions = select_conditions(go_ast.get("if_conditions", []), function_names)
    switches = select_conditions(go_ast.get("switches", []), function_names)
    calls = select_calls(go_ast.get("calls", []), function_names)
    if item.get("type") == "exclusive" and (if_conditions or switches):
        evidence.append("exclusive gateway backed by conditional branch")
    if item.get("type") == "parallel" and any("&&" in entry.get("condition", "") for entry in if_conditions):
        evidence.append("parallel join waits for multiple completed predecessors")
    if item.get("type") == "event" and any("ChangeMsgState" in call.get("callee", "") for call in calls):
        evidence.append("event gateway advances alternative message branches")
    matched = bool(matched_functions) and (bool(if_conditions or switches or calls))
    return summarize_evidence(evidence, "Missing Go gateway logic evidence.", matched=matched)


def verify_gateway_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(sol_ast.get("functions", []), item["name"])
    function_names = [entry["name"] for entry in matched_functions]
    evidence = [f"function {entry['name']}" for entry in matched_functions[:2]]
    if_conditions = select_conditions(sol_ast.get("if_conditions", []), function_names)
    requires = select_calls(sol_ast.get("requires", []), function_names)
    if item.get("type") == "exclusive" and if_conditions:
        evidence.append("exclusive gateway backed by if branch")
    if item.get("type") == "parallel" and any("&&" in entry.get("condition", "") for entry in if_conditions + requires):
        evidence.append("parallel gateway requires multi-predecessor condition")
    if item.get("type") == "event" and any("gateway state not allowed" in " ".join(call.get("arguments", [])) for call in requires):
        evidence.append("gateway guarded by runtime state check")
    matched = bool(matched_functions) and bool(if_conditions or requires)
    return summarize_evidence(evidence, "Missing Solidity gateway branch evidence.", matched=matched)


def verify_event_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(go_ast.get("functions", []), item["name"])
    calls = select_calls(go_ast.get("calls", []), [entry["name"] for entry in matched_functions])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:2]]
    if any("ChangeEventState" in call.get("callee", "") for call in calls):
        evidence.append("event completion updates event state")
    if any("ChangeMsgState" in call.get("callee", "") or "ChangeGtwState" in call.get("callee", "") for call in calls):
        evidence.append("event triggers downstream state transition")
    matched = bool(matched_functions) and bool(calls)
    return summarize_evidence(evidence, "Missing Go event handler evidence.", matched=matched)


def verify_event_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(sol_ast.get("functions", []), item["name"])
    assignments = select_assignments(sol_ast.get("assignments", []), [entry["name"] for entry in matched_functions])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:2]]
    if any("events" in normalize_name(assignment.get("lhs")) and "completed" in normalize_name(assignment.get("rhs")) for assignment in assignments):
        evidence.append("event state changes to COMPLETED")
    if any("messages" in normalize_name(assignment.get("lhs")) or "gateways" in normalize_name(assignment.get("lhs")) for assignment in assignments):
        evidence.append("event enables downstream message/gateway")
    matched = bool(matched_functions) and bool(assignments)
    return summarize_evidence(evidence, "Missing Solidity event transition evidence.", matched=matched)


def verify_businessrule_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(go_ast.get("functions", []), item["name"])
    calls = select_calls(go_ast.get("calls", []), [entry["name"] for entry in matched_functions])
    literals = go_ast.get("string_literals", [])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:3]]
    if any("Invoke_Other_chaincode" in call.get("callee", "") for call in calls):
        evidence.append("business rule invokes external chaincode")
    if any("oracle." in call.get("callee", "") for call in calls):
        evidence.append("oracle helper call found in business rule")
    if any("ChangeBusinessRuleState" in call.get("callee", "") for call in calls):
        evidence.append("business rule state transition found")
    if item.get("decision") and has_name_match(item["decision"], literals):
        evidence.append("decision id preserved in Go string literal")
    if item.get("dmn") and has_name_match(item["dmn"], literals):
        evidence.append("dmn resource literal preserved in Go string literal")
    for mapping in item.get("input_mapping", []) + item.get("output_mapping", []):
        if has_name_match(mapping.get("global"), literals):
            evidence.append(f"mapping literal preserved for global `{mapping.get('global')}`")
            break
    matched = bool(matched_functions) and (
        any("Invoke_Other_chaincode" in call.get("callee", "") for call in calls)
        or any("oracle." in call.get("callee", "") for call in calls)
    )
    return summarize_evidence(evidence, "Missing Go business-rule execution evidence.", matched=matched)


def verify_businessrule_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    matched_functions = find_functions(sol_ast.get("functions", []), item["name"])
    function_names = [entry["name"] for entry in matched_functions]
    calls = select_calls(sol_ast.get("calls", []), function_names)
    assignments = select_assignments(sol_ast.get("assignments", []), function_names)
    literals = sol_ast.get("string_literals", [])
    evidence = [f"function {entry['name']}" for entry in matched_functions[:3]]
    if any("requestDMNDecision" in call.get("callee", "") for call in calls):
        evidence.append("DMN request call found")
    if any("getRequestStatus" in call.get("callee", "") for call in calls):
        evidence.append("DMN request status polling found")
    if any("getRawByRequestId" in call.get("callee", "") for call in calls):
        evidence.append("DMN result fetch found")
    if any("businessrules" in normalize_name(assignment.get("lhs")) and "waiting_for_confirmation" in normalize_name(assignment.get("rhs")) for assignment in assignments):
        evidence.append("business rule enters WAITING_FOR_CONFIRMATION")
    if any("statememory" in normalize_name(assignment.get("lhs")) for assignment in assignments):
        evidence.append("business rule writes outputs into StateMemory")
    if any("businessrules" in normalize_name(assignment.get("lhs")) and "completed" in normalize_name(assignment.get("rhs")) for assignment in assignments):
        evidence.append("business rule continuation marks rule as COMPLETED")
    if item.get("decision") and has_name_match(item["decision"], literals):
        evidence.append("decision id preserved in Solidity literal")
    if item.get("dmn") and has_name_match(item["dmn"], literals):
        evidence.append("dmn resource literal preserved in Solidity literal")
    matched = bool(matched_functions) and (
        any("requestDMNDecision" in call.get("callee", "") for call in calls)
        or any("getRequestStatus" in call.get("callee", "") for call in calls)
        or any("getRawByRequestId" in call.get("callee", "") for call in calls)
        or any("statememory" in normalize_name(assignment.get("lhs")) for assignment in assignments)
    )
    return summarize_evidence(evidence, "Missing Solidity business-rule call evidence.", matched=matched)


def verify_oracletask_go(item: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    function = find_exact_function(go_ast.get("functions", []), item["name"])
    if not function:
        return summarize_evidence([], "Missing Go oracle-task handler.", matched=False)
    calls = select_calls(go_ast.get("calls", []), [function["name"]])
    evidence = [f"function {function['name']}"]
    if any("ReadEvent" in call.get("callee", "") for call in calls):
        evidence.append("oracle task reuses ActionEvent state slot")
    if any("ChangeEventState" in call.get("callee", "") for call in calls):
        evidence.append("oracle task completion updates event state")
    if any("SetGlobalVariable" in call.get("callee", "") for call in calls):
        evidence.append("oracle task writes outputs into global state")
    matched = any("ChangeEventState" in call.get("callee", "") for call in calls)
    return summarize_evidence(evidence, "Missing Go oracle-task state transition evidence.", matched=matched)


def verify_oracletask_sol(item: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    function = find_exact_function(sol_ast.get("functions", []), item["name"])
    if not function:
        return summarize_evidence([], "Missing Solidity oracle-task handler.", matched=False)
    calls = select_calls(sol_ast.get("calls", []), [function["name"]])
    assignments = select_assignments(sol_ast.get("assignments", []), [function["name"]])
    evidence = [f"function {function['name']}"]
    if any("getExternalData" in call.get("callee", "") for call in calls):
        evidence.append("external-data oracle call found")
    if any("runComputeTask" in call.get("callee", "") for call in calls):
        evidence.append("compute-task oracle call found")
    if any("statememory" in normalize_name(assignment.get("lhs")) for assignment in assignments):
        evidence.append("oracle task writes outputs into StateMemory")
    if any("events" in normalize_name(assignment.get("lhs")) and "completed" in normalize_name(assignment.get("rhs")) for assignment in assignments):
        evidence.append("oracle task completion updates event slot")
    matched = bool(calls) or any("statememory" in normalize_name(assignment.get("lhs")) for assignment in assignments)
    return summarize_evidence(evidence, "Missing Solidity oracle-task oracle-call or state-write evidence.", matched=matched)


def _go_action_match(action: Dict[str, Any], calls: Sequence[Dict[str, Any]], assignments: Sequence[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    target = action.get("target")
    if action.get("kind") in {"enable", "disable"}:
        desired_state = "ENABLED" if action.get("kind") == "enable" else "DISABLED"
        for call in calls:
            args = " ".join(call.get("args", []))
            callee = call.get("callee", "")
            if target and target in args and desired_state in args and ("ChangeMsgState" in callee or "ChangeEventState" in callee or "ChangeGtwState" in callee or "ChangeBusinessRuleState" in callee):
                return True, [f"{callee}({args})"]
        return False, []
    if action.get("kind") == "set":
        target_norm = normalize_name(target)
        value_norm = normalize_name(str(action.get("value")))
        for assignment in assignments:
            lhs = " ".join(assignment.get("lhs", []))
            rhs = " ".join(assignment.get("rhs", []))
            if target_norm in normalize_name(lhs) and (not value_norm or value_norm in normalize_name(rhs)):
                return True, [f"{lhs} = {rhs}"]
        for call in calls:
            args = " ".join(call.get("args", []))
            if "SetGlobalVariable" in call.get("callee", "") or ("FieldByName" in call.get("callee", "") and target and target in args):
                return True, [f"{call.get('callee')}({args})"]
        return False, []
    return False, []


def _sol_action_match(action: Dict[str, Any], assignments: Sequence[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    target = normalize_name(action.get("target"))
    if action.get("kind") in {"enable", "disable"}:
        desired = normalize_name("ElementState.ENABLED" if action.get("kind") == "enable" else "ElementState.DISABLED")
        for assignment in assignments:
            lhs = normalize_name(assignment.get("lhs"))
            rhs = normalize_name(assignment.get("rhs"))
            if target and target in lhs and desired in rhs:
                return True, [f"{assignment.get('lhs')} = {assignment.get('rhs')}"]
            if desired in rhs and lhs.endswith("_state") and target:
                return True, [f"{assignment.get('lhs')} = {assignment.get('rhs')}"]
        return False, []
    if action.get("kind") == "set":
        value = normalize_name(str(action.get("value")))
        for assignment in assignments:
            lhs = normalize_name(assignment.get("lhs"))
            rhs = normalize_name(assignment.get("rhs"))
            if target and target in lhs and (not value or value in rhs):
                return True, [f"{assignment.get('lhs')} = {assignment.get('rhs')}"]
        return False, []
    return False, []


def verify_flow_go(flow: Dict[str, Any], go_ast: Dict[str, Any]) -> MatchResult:
    function_names = flow_trigger_candidates(flow, "go")
    functions = []
    if function_names:
        functions = [
            entry
            for entry in go_ast.get("functions", [])
            if normalize_name(entry.get("name")) in {normalize_name(name) for name in function_names}
        ]
    calls = select_calls(go_ast.get("calls", []), [entry["name"] for entry in functions])
    assignments = select_assignments(go_ast.get("assignments", []), [entry["name"] for entry in functions])
    conditions = select_conditions(go_ast.get("if_conditions", []), [entry["name"] for entry in functions]) + select_conditions(go_ast.get("switches", []), [entry["name"] for entry in functions])

    evidence = [f"trigger handled by {entry['name']}" for entry in functions[:2]]
    matched_actions = 0
    flow_actions = iter_flow_actions(flow)
    for action in flow_actions:
        matched, action_evidence = _go_action_match(action, calls, assignments)
        if matched:
            matched_actions += 1
            evidence.extend(action_evidence[:1])
    for condition in flow.get("conditions", []):
        if condition.get("condition_kind") == "compare":
            for item in conditions:
                text = item.get("condition", "") or item.get("tag", "")
                if normalize_name(condition.get("var")) in normalize_name(text):
                    evidence.append(f"branch condition `{text}`")
                    break
            else:
                if condition.get("actions"):
                    evidence.append("gateway compare branch preserved via branch-specific state updates")
        if condition.get("condition_kind") == "await_all":
            for item in conditions:
                text = item.get("condition", "")
                if "&&" in text:
                    evidence.append(f"parallel await condition `{text}`")
                    break

    matched = bool(functions) and matched_actions == len(flow_actions)
    if flow.get("conditions"):
        matched = matched and len(evidence) > len(functions[:2])
    return summarize_evidence(evidence, "Go flow trigger/actions were not fully preserved.", matched=matched)


def verify_flow_sol(flow: Dict[str, Any], sol_ast: Dict[str, Any]) -> MatchResult:
    function_names = flow_trigger_candidates(flow, "solidity")
    functions = [entry for entry in sol_ast.get("functions", []) if normalize_name(entry.get("name")) in {normalize_name(name) for name in function_names}]
    assignments = select_assignments(sol_ast.get("assignments", []), [entry["name"] for entry in functions])
    conditions = select_conditions(sol_ast.get("if_conditions", []), [entry["name"] for entry in functions]) + select_conditions(sol_ast.get("requires", []), [entry["name"] for entry in functions])
    evidence = [f"trigger handled by {entry['name']}" for entry in functions[:2]]
    matched_actions = 0
    flow_actions = iter_flow_actions(flow)
    for action in flow_actions:
        matched, action_evidence = _sol_action_match(action, assignments)
        if matched:
            matched_actions += 1
            evidence.extend(action_evidence[:1])
    for condition in flow.get("conditions", []):
        if condition.get("condition_kind") == "compare":
            for item in conditions:
                text = item.get("condition", "") or " ".join(item.get("arguments", []))
                if normalize_name(condition.get("var")) in normalize_name(text):
                    evidence.append(f"branch condition `{text}`")
                    break
            else:
                if condition.get("actions"):
                    evidence.append("gateway compare branch preserved via branch-specific state updates")
        if condition.get("condition_kind") == "await_all":
            for item in conditions:
                text = item.get("condition", "") or " ".join(item.get("arguments", []))
                sources = [normalize_name(source) for source in condition.get("sources", [])]
                if "&&" in text and all(source in normalize_name(text) for source in sources):
                    evidence.append(f"parallel await condition `{text}`")
                    break
    matched = bool(functions) and matched_actions == len(flow_actions)
    if flow.get("conditions"):
        matched = matched and len(evidence) > len(functions[:2])
    return summarize_evidence(evidence, "Solidity flow trigger/actions were not fully preserved.", matched=matched)
