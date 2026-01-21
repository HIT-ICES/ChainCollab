from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any, List, Optional

from jinja2 import Environment, FileSystemLoader
from textx import generator
from textx.generators import gen_file, get_output_filename

SOLIDITY_TYPE = {
    "string": "string",
    "int": "int256",
    "bool": "bool",
    "float": "int256",
}

STATE_ALIAS = {
    None: "DISABLED",
    "INACTIVE": "DISABLED",
    "READY": "ENABLED",
    "PENDING_CONFIRMATION": "WAITING_FOR_CONFIRMATION",
    "DONE": "COMPLETED",
}


def _template_env() -> Environment:
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True)


TEMPLATE_ENV = _template_env()
CONTRACT_TEMPLATE = "contract.sol.jinja"


def public_the_name(name: str) -> str:
    return "".join(name[:1].upper() + name[1:]) if name else name


def sanitize_identifier(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)


class DSLContractAdapter:
    def __init__(self, contract: Any):
        self.contract = contract
        self.participants: List[Any] = []
        self.globals: List[Any] = []
        self.messages: List[Any] = []
        self.gateways: List[Any] = []
        self.events: List[Any] = []
        self.business_rules: List[Any] = []
        self.flow_items: List[Any] = []
        self._collect_sections()

    def _collect_sections(self):
        for section in getattr(self.contract, "sections", []):
            cls_name = section.__class__.__name__
            if cls_name == "ParticipantSection":
                self.participants.extend(getattr(section, "participants", []))
            elif cls_name == "GlobalSection":
                self.globals.extend(getattr(section, "globals", []))
            elif cls_name == "MessageSection":
                self.messages.extend(getattr(section, "messages", []))
            elif cls_name == "GatewaySection":
                self.gateways.extend(getattr(section, "gateways", []))
            elif cls_name == "EventSection":
                self.events.extend(getattr(section, "events", []))
            elif cls_name == "BusinessRuleSection":
                self.business_rules.extend(getattr(section, "rules", []))
            elif cls_name == "FlowSection":
                self.flow_items.extend(getattr(section, "flowItems", []))


class SolidityRenderer:
    def __init__(self, adapter: DSLContractAdapter):
        self.adapter = adapter

    def build_context(self) -> dict:
        enum_maps = self._enum_maps()
        flow_renderer = SolidityFlowRenderer(
            self.adapter,
            enum_maps,
            self._global_type_map(),
        )
        flow_functions = flow_renderer.render_blocks()
        rule_done_actions = flow_renderer.rule_done_actions()
        return {
            "participants": self._participant_payload(),
            "messages": self._message_payload(),
            "gateways": self._simple_payload(self.adapter.gateways),
            "events": self._simple_payload(self.adapter.events),
            "globals": self._global_variables(),
            "business_rules": self._business_rule_payload(rule_done_actions),
            "flow_functions": flow_functions,
        }

    def _enum_maps(self) -> dict[str, dict[str, str]]:
        return {
            "participant": {
                item.name: sanitize_identifier(item.name) for item in self.adapter.participants
            },
            "message": {
                item.name: sanitize_identifier(item.name) for item in self.adapter.messages
            },
            "gateway": {
                item.name: sanitize_identifier(item.name) for item in self.adapter.gateways
            },
            "event": {
                item.name: sanitize_identifier(item.name) for item in self.adapter.events
            },
            "rule": {
                item.name: sanitize_identifier(item.name) for item in self.adapter.business_rules
            },
        }

    def _global_type_map(self) -> dict[str, str]:
        return {getattr(g, "name", ""): getattr(g, "type", "string") for g in self.adapter.globals}

    def _participant_payload(self) -> List[dict]:
        payload: List[dict] = []
        for participant in self.adapter.participants:
            enum_name = sanitize_identifier(participant.name)
            payload.append(
                {
                    "name": participant.name,
                    "enum_name": enum_name,
                    "param_name": f"{enum_name}_account",
                    "org_param": f"{enum_name}_org",
                    "is_multi": "true" if getattr(participant, "isMulti", False) else "false",
                    "multi_maximum": getattr(participant, "multiMax", 0) or 0,
                    "multi_minimum": getattr(participant, "multiMin", 0) or 0,
                }
            )
        return payload

    def _message_payload(self) -> List[dict]:
        payload: List[dict] = []
        for message in self.adapter.messages:
            enum_name = sanitize_identifier(message.name)
            payload.append(
                {
                    "enum_name": enum_name,
                    "sender": sanitize_identifier(message.sender.name),
                    "receiver": sanitize_identifier(message.receiver.name),
                    "initial_state": STATE_ALIAS.get(getattr(message, "initialState", None), "DISABLED"),
                    "schema": json.dumps(getattr(message, "schema", "") or ""),
                }
            )
        return payload

    def _simple_payload(self, items: List[Any]) -> List[dict]:
        payload: List[dict] = []
        for item in items:
            payload.append(
                {
                    "enum_name": sanitize_identifier(item.name),
                    "initial_state": STATE_ALIAS.get(getattr(item, "initialState", None), "DISABLED"),
                }
            )
        return payload

    def _global_variables(self) -> List[dict]:
        return [
            {
                "name": sanitize_identifier(public_the_name(global_var.name)),
                "type": SOLIDITY_TYPE.get(global_var.type, "string"),
            }
            for global_var in self.adapter.globals
        ]

    def _business_rule_payload(self, rule_done_actions: dict[str, str]) -> List[dict]:
        payload: List[dict] = []
        for rule in self.adapter.business_rules:
            enum_name = sanitize_identifier(rule.name)
            payload.append(
                {
                    "name": rule.name,
                    "enum_name": enum_name,
                    "address_param": f"{enum_name}_contract",
                    "content_param": f"{enum_name}_content",
                    "decision_param": f"{enum_name}_decision",
                    "done_actions": rule_done_actions.get(rule.name, ""),
                }
            )
        return payload


class SolidityFlowRenderer:
    def __init__(
        self,
        adapter: DSLContractAdapter,
        enum_maps: dict[str, dict[str, str]],
        global_type_map: dict[str, str],
    ):
        self.adapter = adapter
        self.enum_maps = enum_maps
        self.global_type_map = global_type_map
        self.start_event_actions: dict[str, List[str]] = {}
        self.message_actions: dict[tuple[str, str], List[str]] = {}
        self.gateway_actions: dict[str, List[str]] = {}
        self.gateway_branch_blocks: dict[str, str] = {}
        self.parallel_requirements: dict[str, dict[str, Any]] = {}
        self.event_actions: dict[str, List[str]] = {}
        self.rule_actions: dict[tuple[str, str], List[str]] = {}
        self._collect_flow_actions()

    def render_blocks(self) -> List[str]:
        blocks: List[str] = []
        blocks.extend(self._render_start_events())
        blocks.extend(self._render_messages())
        blocks.extend(self._render_gateways())
        blocks.extend(self._render_events())
        return [block for block in blocks if block.strip()]

    def rule_done_actions(self) -> dict[str, str]:
        done_actions: dict[str, str] = {}
        for (rule_name, condition), actions in self.rule_actions.items():
            if condition == "done":
                done_actions[rule_name] = self._indent("".join(actions), 2)
        return done_actions

    def _collect_flow_actions(self):
        for flow in self.adapter.flow_items:
            cls_name = flow.__class__.__name__
            if cls_name == "StartFlow":
                target_element = self._resolve_target(getattr(flow, "target", None))
                if not target_element:
                    continue
                change_code = self._change_state_code(target_element, "ENABLED")
                self._append_action(self.start_event_actions, flow.start.name, change_code)
            elif cls_name == "MessageFlow":
                actions = self._join_actions(getattr(flow, "actions", []))
                condition = getattr(flow, "msgCond", "sent")
                self._append_action(self.message_actions, (flow.msg.name, condition), actions)
            elif cls_name == "GatewayFlow":
                branches = getattr(flow, "branches", None)
                if branches:
                    branch_block = self._render_gateway_branches(flow.gtw.name, branches)
                    if branch_block:
                        self.gateway_branch_blocks[flow.gtw.name] = branch_block
                else:
                    actions = self._join_actions(getattr(flow, "actions", []))
                    self._append_action(self.gateway_actions, flow.gtw.name, actions)
            elif cls_name == "ParallelJoin":
                actions = self._join_actions(getattr(flow, "actions", []))
                sources = getattr(flow, "sources", [])
                self.parallel_requirements[flow.gtw.name] = {
                    "sources": sources,
                    "actions": actions,
                }
            elif cls_name == "RuleFlow":
                actions = self._join_actions(getattr(flow, "actions", []))
                condition = getattr(flow, "ruleCond", "done")
                self._append_action(self.rule_actions, (flow.rule.name, condition), actions)
            elif cls_name == "EventFlow":
                actions = self._join_actions(getattr(flow, "actions", []))
                self._append_action(self.event_actions, flow.ev.name, actions)

    def _render_start_events(self) -> List[str]:
        functions: List[str] = []
        for event_name, actions in self.start_event_actions.items():
            enum_name = self.enum_maps["event"].get(event_name, sanitize_identifier(event_name))
            body = f"""function {enum_name}(uint256 instanceId) external onlyInitialized {{
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.{enum_name}];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.{enum_name});
{self._indent("".join(actions), 2)}
    }}"""
            functions.append(body)
        return functions

    def _render_messages(self) -> List[str]:
        functions: List[str] = []
        for message in self.adapter.messages:
            enum_name = self.enum_maps["message"].get(message.name, sanitize_identifier(message.name))
            send_actions = self._indent("".join(self.message_actions.get((message.name, "sent"), [])), 2)
            body = f"""function {enum_name}_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {{
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.{enum_name}];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.{enum_name}, fireflyTranId);
{send_actions}
    }}"""
            functions.append(body)
        return functions

    def _render_gateways(self) -> List[str]:
        functions: List[str] = []
        for gateway in self.adapter.gateways:
            enum_name = self.enum_maps["gateway"].get(gateway.name, sanitize_identifier(gateway.name))
            raw_actions = "".join(self.gateway_actions.get(gateway.name, []))
            join_info = self.parallel_requirements.get(gateway.name)
            guard_block = ""
            if join_info:
                guard_block = self._indent(self._parallel_guard_block(join_info.get("sources", [])), 2)
                raw_actions = join_info.get("actions", "") + raw_actions
            normal_actions = self._indent(raw_actions, 2)
            conditional_raw = self.gateway_branch_blocks.get(gateway.name, "")
            conditional_block = self._indent(conditional_raw, 2) if conditional_raw else ""
            action_block = guard_block + (conditional_block or normal_actions)
            body = f"""function {enum_name}(uint256 instanceId) external onlyInitialized {{
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.{enum_name}];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.{enum_name});
{action_block}
    }}"""
            functions.append(body)
        return functions

    def _render_events(self) -> List[str]:
        functions: List[str] = []
        start_events = set(self.start_event_actions.keys())
        for event in self.adapter.events:
            if event.name in start_events:
                continue
            enum_name = self.enum_maps["event"].get(event.name, sanitize_identifier(event.name))
            actions = self._indent("".join(self.event_actions.get(event.name, [])), 2)
            body = f"""function {enum_name}(uint256 instanceId) external onlyInitialized {{
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.{enum_name}];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.{enum_name});
{actions}
    }}"""
            functions.append(body)
        return functions

    def _append_action(self, store: dict, key: Any, action: str):
        if not action:
            return
        store.setdefault(key, []).append(action)

    def _resolve_target(self, flow_target: Any) -> Optional[Any]:
        if flow_target is None:
            return None
        return getattr(flow_target, "target", flow_target)

    def _join_actions(self, actions: List[Any]) -> str:
        rendered = [self._render_action(action) for action in actions]
        return "".join(code for code in rendered if code)

    def _render_action(self, action: Any) -> Optional[str]:
        cls_name = action.__class__.__name__
        if cls_name == "EnableAction":
            return self._change_state_code(action.target, "ENABLED")
        if cls_name == "DisableAction":
            return self._change_state_code(action.target, "DISABLED")
        if cls_name == "SetGlobalAction":
            literal = self._literal_value(
                action.expr, self.global_type_map.get(getattr(action.var, "name", ""), "string")
            )
            field = sanitize_identifier(public_the_name(action.var.name))
            return f"inst.stateMemory.{field} = {literal};\n"
        return None

    def _literal_value(self, expr: Any, target_type: str) -> str:
        normalized_type = (target_type or "").lower()

        def bool_literal() -> Optional[str]:
            if getattr(expr, "boolValue", None) is not None:
                return "true" if expr.boolValue else "false"
            value = getattr(expr, "value", None)
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, str):
                lowered = value.lower()
                if lowered in ("true", "false"):
                    return lowered
            return None

        def int_literal() -> Optional[str]:
            if getattr(expr, "intValue", None) is not None:
                return str(expr.intValue)
            value = getattr(expr, "value", None)
            if isinstance(value, (int, float)):
                return str(value)
            if isinstance(value, str):
                return value or "0"
            return None

        def string_literal() -> Optional[str]:
            if getattr(expr, "stringValue", None) is not None:
                return json.dumps(expr.stringValue)
            value = getattr(expr, "value", None)
            if isinstance(value, str):
                return json.dumps(value)
            return None

        if normalized_type == "bool":
            literal = bool_literal()
            if literal is not None:
                return literal

        if normalized_type in ("int", "float"):
            literal = int_literal()
            if literal is not None:
                return literal

        value = getattr(expr, "value", None)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            lowered = value.lower()
            if normalized_type == "bool" and lowered in ("true", "false"):
                return lowered
            if normalized_type in ("int", "float"):
                return value
            return json.dumps(value)

        literal = bool_literal()
        if literal is not None:
            return literal

        literal = int_literal()
        if literal is not None:
            return literal

        literal = string_literal()
        if literal is not None:
            return literal

        if normalized_type == "bool":
            return "false"
        if normalized_type in ("int", "float"):
            return "0"
        return json.dumps("")

    def _render_gateway_branches(self, gateway_name: str, branches: List[Any]) -> str:
        blocks: List[str] = []
        branch_index = 0
        for branch in branches:
            actions = self._join_actions(getattr(branch, "actions", []))
            if not actions.strip():
                continue
            condition, is_else = self._gateway_branch_condition(branch)
            if condition is None and not is_else:
                continue
            if branch_index == 0:
                prefix = "if" if not is_else else "if (true)"
            else:
                prefix = "else" if is_else else "else if"
            clause = ""
            if condition and prefix != "else":
                clause = f" ({condition})"
            block = f"{prefix}{clause} {{\n"
            block += self._indent(actions, 1)
            block += "}\n"
            blocks.append(block)
            branch_index += 1
        return "".join(blocks)

    def _gateway_branch_condition(self, branch: Any) -> tuple[Optional[str], bool]:
        cls_name = branch.__class__.__name__
        if cls_name == "GatewayCompareBranch":
            var_name = getattr(branch.var, "name", "")
            field = sanitize_identifier(public_the_name(var_name))
            literal = self._literal_value(branch.value, self.global_type_map.get(var_name, "string"))
            return f"inst.stateMemory.{field} {branch.relation} {literal}", False
        if cls_name == "GatewayElseBranch":
            return None, True
        return None, False

    def _parallel_guard_block(self, sources: List[Any]) -> str:
        checks = [self._element_ready_check(source) for source in sources]
        checks = [check for check in checks if check]
        if not checks:
            return ""
        condition = " && ".join(checks)
        return f"if (!({condition})) {{\n            revert(\"Parallel gateway prerequisites not met\");\n        }}\n"

    def _element_ready_check(self, element: Any) -> Optional[str]:
        cls_name = element.__class__.__name__
        name = getattr(element, "name", "")
        if not name:
            return None
        if cls_name == "Message":
            enum_name = self.enum_maps["message"].get(name, sanitize_identifier(name))
            return f"inst.messages[MessageKey.{enum_name}].state == ElementState.COMPLETED"
        if cls_name == "Gateway":
            enum_name = self.enum_maps["gateway"].get(name, sanitize_identifier(name))
            return f"inst.gateways[GatewayKey.{enum_name}].state == ElementState.COMPLETED"
        if cls_name == "Event":
            enum_name = self.enum_maps["event"].get(name, sanitize_identifier(name))
            return f"inst.events[EventKey.{enum_name}].state == ElementState.COMPLETED"
        if cls_name == "BusinessRule":
            enum_name = self.enum_maps["rule"].get(name, sanitize_identifier(name))
            return f"inst.businessRules[BusinessRuleKey.{enum_name}].state == ElementState.COMPLETED"
        return None

    def _change_state_code(self, element: Any, state: str) -> str:
        cls_name = element.__class__.__name__
        if cls_name == "Message":
            enum_name = self.enum_maps["message"].get(element.name, sanitize_identifier(element.name))
            return f"inst.messages[MessageKey.{enum_name}].state = ElementState.{state};\n"
        if cls_name == "Gateway":
            enum_name = self.enum_maps["gateway"].get(element.name, sanitize_identifier(element.name))
            return f"inst.gateways[GatewayKey.{enum_name}].state = ElementState.{state};\n"
        if cls_name == "Event":
            enum_name = self.enum_maps["event"].get(element.name, sanitize_identifier(element.name))
            return f"inst.events[EventKey.{enum_name}].state = ElementState.{state};\n"
        if cls_name == "BusinessRule":
            enum_name = self.enum_maps["rule"].get(element.name, sanitize_identifier(element.name))
            return f"inst.businessRules[BusinessRuleKey.{enum_name}].state = ElementState.{state};\n"
        return ""

    def _indent(self, text: str, level: int = 1) -> str:
        if not text.strip():
            return ""
        indent = "    " * level
        lines = [indent + line if line else "" for line in text.rstrip().splitlines()]
        return "\n".join(lines) + "\n"


@generator("b2c", "solidity")
def b2c_generate_solidity(metamodel, model, output_path, overwrite, debug, **custom_args):
    output_file = get_output_filename(model._tx_filename, output_path, "sol")
    gen_file(
        model._tx_filename,
        output_file,
        partial(generator_callback, model, output_file),
        overwrite,
    )


def generator_callback(model, output_file):
    if not getattr(model, "contracts", None):
        raise ValueError("No contracts defined in the provided B2C DSL model.")
    contract = model.contracts[0]
    adapter = DSLContractAdapter(contract)
    renderer = SolidityRenderer(adapter)
    context = renderer.build_context()
    template = TEMPLATE_ENV.get_template(CONTRACT_TEMPLATE)
    rendered = template.render(**context).strip()
    Path(output_file).write_text(rendered + "\n", encoding="utf8")
