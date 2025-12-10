from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any, List, Optional
import shutil

from jinja2 import Environment, FileSystemLoader
from textx import generator
from textx.generators import gen_file, get_output_filename

__version__ = "0.1.0.dev"


def _template_env() -> Environment:
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True)


TEMPLATE_ENV = _template_env()
RESOURCE_ROOT = Path(__file__).resolve().parents[3] / "DSLGenerator" / "resource"
CONTRACT_TEMPLATE = "contract.go.jinja"
START_EVENT_TEMPLATE = "flows/start_event.go.jinja"
MESSAGE_SEND_TEMPLATE = "flows/message_send.go.jinja"
MESSAGE_COMPLETE_TEMPLATE = "flows/message_complete.go.jinja"
SET_GLOBAL_TEMPLATE = "actions/set_global_variable.go.jinja"

B2C_TO_GO_TYPE = {
    "string": "string",
    "int": "int",
    "bool": "bool",
    "float": "float64",
}

STATE_ALIAS = {
    None: "DISABLED",
    "INACTIVE": "DISABLED",
    "READY": "ENABLED",
    "PENDING_CONFIRMATION": "WAITINGFORCONFIRMATION",
    "DONE": "COMPLETED",
}

BASE_IMPORTS = [
    "encoding/json",
    "errors",
    "fmt",
    "strconv",
    "reflect",
    "crypto/sha256",
    "strings",
    "encoding/hex",
    "github.com/hyperledger/fabric-chaincode-go/shim",
    "github.com/hyperledger/fabric-contract-api-go/contractapi",
]
ORACLE_IMPORT = "IBC/Oracle/oracle"


def public_the_name(name: str) -> str:
    return "".join(name[:1].upper() + name[1:]) if name else name


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

    @property
    def start_event_id(self) -> Optional[str]:
        ready_events = [event for event in self.events if STATE_ALIAS.get(getattr(event, "initialState", None)) == "ENABLED"]
        if ready_events:
            return ready_events[0].name
        start_flows = [flow for flow in self.flow_items if flow.__class__.__name__ == "StartFlow"]
        if start_flows:
            return start_flows[0].start.name
        if self.events:
            return self.events[0].name
        return None

    @property
    def end_event_ids(self) -> List[str]:
        start_id = self.start_event_id
        return [event.name for event in self.events if event.name != start_id]


class FlowRenderer:
    def __init__(
        self,
        adapter: DSLContractAdapter,
        template_env: Environment,
        global_type_map: dict[str, str],
    ):
        self.adapter = adapter
        self.template_env = template_env
        self.global_type_map = global_type_map
        self.start_event_actions: dict[str, List[str]] = {}
        self.message_actions: dict[tuple[str, str], List[str]] = {}
        self.gateway_actions: dict[str, List[str]] = {}
        self.event_actions: dict[str, List[str]] = {}
        self.rule_actions: dict[tuple[str, str], List[str]] = {}
        self._collect_flow_actions()

    def render_blocks(self) -> List[str]:
        codes: List[str] = []
        codes.extend(self._render_start_events())
        codes.extend(self._render_messages())
        codes.extend(self._render_gateways())
        codes.extend(self._render_events())
        return [code.strip() for code in codes if code.strip()]

    def rule_done_actions(self) -> dict[str, str]:
        done_actions: dict[str, str] = {}
        for (rule_name, condition), actions in self.rule_actions.items():
            if condition == "done":
                done_actions[rule_name] = "".join(actions)
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
                actions = self._join_actions(getattr(flow, "actions", []))
                self._append_action(self.gateway_actions, flow.gtw.name, actions)
            elif cls_name == "RuleFlow":
                actions = self._join_actions(getattr(flow, "actions", []))
                condition = getattr(flow, "ruleCond", "done")
                self._append_action(self.rule_actions, (flow.rule.name, condition), actions)
            elif cls_name == "EventFlow":
                actions = self._join_actions(getattr(flow, "actions", []))
                self._append_action(self.event_actions, flow.ev.name, actions)

    def _render_start_events(self) -> List[str]:
        blocks: List[str] = []
        for event_name, actions in self.start_event_actions.items():
            blocks.append(
                self._render_template(
                    START_EVENT_TEMPLATE,
                    event_name=event_name,
                    next_state_block="".join(actions),
                    pre_activate_hooks="",
                    after_hooks="",
                )
            )
        return blocks

    def _render_messages(self) -> List[str]:
        blocks: List[str] = []
        for message in self.adapter.messages:
            msg_name = message.name
            send_actions = "".join(self.message_actions.get((msg_name, "sent"), []))
            complete_actions = "".join(self.message_actions.get((msg_name, "completed"), []))
            blocks.append(
                self._render_template(
                    MESSAGE_SEND_TEMPLATE,
                    message_name=msg_name,
                    after_hooks=send_actions,
                    state_change_block=self._change_state_code(message, "COMPLETED"),
                    more_parameters="",
                    parameter_assignments="",
                )
            )
            blocks.append(
                self._render_template(
                    MESSAGE_COMPLETE_TEMPLATE,
                    message_name=msg_name,
                    next_state_block=complete_actions,
                    pre_activate_hooks="",
                    after_hooks="",
                )
            )
        return blocks

    def _render_gateways(self) -> List[str]:
        blocks: List[str] = []
        for gateway in self.adapter.gateways:
            actions = "".join(self.gateway_actions.get(gateway.name, []))
            blocks.append(
                self._render_template(
                    "flows/gateway.go.jinja",
                    gateway_name=gateway.name,
                    action_block=actions,
                )
            )
        return blocks

    def _render_events(self) -> List[str]:
        blocks: List[str] = []
        start_event_names = set(self.start_event_actions.keys())
        for event in self.adapter.events:
            if event.name in start_event_names:
                continue
            actions = "".join(self.event_actions.get(event.name, []))
            blocks.append(
                self._render_template(
                    "flows/event.go.jinja",
                    event_name=event.name,
                    action_block=actions,
                )
            )
        return blocks

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
        rendered = [code for code in rendered if code]
        return "".join(rendered)

    def _render_action(self, action: Any) -> Optional[str]:
        cls_name = action.__class__.__name__
        if cls_name == "EnableAction":
            return self._change_state_code(action.target, "ENABLED")
        if cls_name == "DisableAction":
            return self._change_state_code(action.target, "DISABLED")
        if cls_name == "SetGlobalAction":
            var_name = getattr(action.var, "name", "")
            literal = self._literal_value(
                action.expr, self.global_type_map.get(var_name)
            )
            assignment = {
                "name": public_the_name(action.var.name),
                "value": literal,
            }
            return self._render_template(SET_GLOBAL_TEMPLATE, assignments=[assignment])
        return None

    def _literal_value(self, expr: Any, target_type: Optional[str] = None) -> str:
        def pick_attr(names: List[str]) -> Any:
            for name in names:
                value = getattr(expr, name, None)
                if value is not None:
                    return value
            return None

        string_value = pick_attr(["stringValue", "stringvalue"])
        if string_value is not None:
            return json.dumps(string_value)

        int_value = pick_attr(["intValue", "intvalue"])
        if int_value is not None:
            return str(int_value)

        bool_value = pick_attr(["boolValue", "boolvalue"])
        if bool_value is not None:
            if isinstance(bool_value, str):
                lowered = bool_value.lower()
                if lowered in ("true", "false"):
                    return lowered
            return "true" if bool_value else "false"

        generic_value = pick_attr(["value"])
        if generic_value is not None:
            if isinstance(generic_value, bool):
                return "true" if generic_value else "false"
            if isinstance(generic_value, (int, float)):
                return str(generic_value)
            if isinstance(generic_value, str):
                lowered = generic_value.lower()
                if target_type and target_type.lower() == "bool" and lowered in ("true", "false"):
                    return lowered
                if target_type and target_type.lower() in ("int", "float"):
                    return generic_value
                return json.dumps(generic_value)

        if target_type and target_type.lower() == "bool":
            return "false"
        if target_type and target_type.lower() in ("int", "float"):
            return "0"
        return json.dumps("")

    def _change_state_code(self, element: Any, state: str) -> str:
        cls_name = element.__class__.__name__
        if cls_name == "Message":
            return f"\tcc.ChangeMsgState(ctx, instance, \"{element.name}\", {state})\n"
        if cls_name == "Gateway":
            return f"\tcc.ChangeGtwState(ctx, instance, \"{element.name}\", {state})\n"
        if cls_name == "Event":
            return f"\tcc.ChangeEventState(ctx, instance, \"{element.name}\", {state})\n"
        if cls_name == "BusinessRule":
            return f"\tcc.ChangeBusinessRuleState(ctx, instance, \"{element.name}\", {state})\n"
        return ""

    def _render_template(self, template_name: str, **context: Any) -> str:
        template = self.template_env.get_template(template_name)
        rendered = template.render(**context).strip()
        return rendered + ("\n" if rendered else "")


class GoChaincodeRenderer:
    def __init__(self, adapter: DSLContractAdapter, template_env: Environment):
        self.adapter = adapter
        self.template_env = template_env
        self.flow_renderer = FlowRenderer(
            adapter, template_env, self._global_type_map()
        )

    def build_context(self) -> dict:
        flow_functions = self.flow_renderer.render_blocks()
        rule_done_actions = self.flow_renderer.rule_done_actions()
        return {
            "package_name": "chaincode",
            "imports": self._imports(),
            "globals": self._state_memory_fields(),
            "init_params": self._init_parameter_fields(),
            "create_instance": self._create_instance_payload(),
            "business_rules": self._business_rule_payload(rule_done_actions),
            "flow_functions": flow_functions,
        }

    def _imports(self) -> List[str]:
        imports = list(BASE_IMPORTS)
        if self.adapter.business_rules:
            imports.append(ORACLE_IMPORT)
        return imports

    def _global_type_map(self) -> dict[str, str]:
        return {
            getattr(global_var, "name", ""): getattr(global_var, "type", "string")
            for global_var in self.adapter.globals
        }

    def _state_memory_fields(self) -> List[dict]:
        return [
            {
                "name": public_the_name(global_var.name),
                "type": B2C_TO_GO_TYPE.get(global_var.type, "string"),
            }
            for global_var in self.adapter.globals
        ]

    def _init_parameter_fields(self) -> List[dict]:
        payload: List[dict] = []
        for participant in self.adapter.participants:
            payload.append({"name": public_the_name(participant.name), "type": "Participant"})
        for rule in self.adapter.business_rules:
            capital = public_the_name(rule.name)
            payload.extend(
                [
                    {"name": f"{capital}_DecisionID", "type": "string"},
                    {"name": f"{capital}_ParamMapping", "type": "map[string]string"},
                    {"name": f"{capital}_Content", "type": "string"},
                ]
            )
        return payload

    def _create_instance_payload(self) -> dict:
        start_event = self.adapter.start_event_id or "StartEvent"
        end_events = self.adapter.end_event_ids
        return {
            "start_event": start_event,
            "end_events": end_events,
            "messages": [
                {
                    "name": message.name,
                    "sender": message.sender.name,
                    "receiver": message.receiver.name,
                    "properties": json.dumps({"schema": getattr(message, "schema", "") or ""}),
                }
                for message in self.adapter.messages
            ],
            "gateways": [gateway.name for gateway in self.adapter.gateways],
            "participants": [
                {
                    "id": participant.name,
                    "field_name": public_the_name(participant.name),
                    "multi_maximum": getattr(participant, "multiMax", 0) or 0,
                    "multi_minimum": getattr(participant, "multiMin", 0) or 0,
                }
                for participant in self.adapter.participants
            ],
            "business_rules": [
                {
                    "name": rule.name,
                    "field_name": public_the_name(rule.name),
                }
                for rule in self.adapter.business_rules
            ],
        }

    def _business_rule_payload(self, rule_done_actions: dict[str, str]) -> List[dict]:
        payload: List[dict] = []
        for rule in self.adapter.business_rules:
            payload.append(
                {
                    "name": rule.name,
                    "done_actions": rule_done_actions.get(rule.name, ""),
                }
            )
        return payload


@generator("b2c", "go")
def b2c_generate_go(metamodel, model, output_path, overwrite, debug, **custom_args):
    output_file = get_output_filename(model._tx_filename, output_path, "go")
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
    renderer = GoChaincodeRenderer(adapter, TEMPLATE_ENV)
    context = renderer.build_context()
    template = TEMPLATE_ENV.get_template(CONTRACT_TEMPLATE)
    rendered = template.render(**context).strip()
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf8")
    _ensure_go_scaffold(output_path.parent)


def _ensure_go_scaffold(target_dir: Path) -> None:
    """Copy go.mod/go.sum and oracle dependency into the output directory."""
    if not RESOURCE_ROOT.exists():
        return
    for filename in ("go.mod", "go.sum"):
        src = RESOURCE_ROOT / filename
        if src.exists():
            shutil.copy2(src, target_dir / filename)
    contracts_src = RESOURCE_ROOT / "contracts" / "oracle-go"
    if contracts_src.exists():
        contracts_dest = target_dir / "contracts" / "Oracle"
        contracts_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(contracts_src, contracts_dest, dirs_exist_ok=True)

    
