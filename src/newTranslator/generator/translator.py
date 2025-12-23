from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

if not __package__:
    CURRENT_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = CURRENT_DIR.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))

from generator.parser.choreography_parser.elements import (
    Element,
    Message,
    MessageFlow,
    NodeType,
    EdgeType,
    Participant,
    SequenceFlow,
)
from generator.parser.choreography_parser.parser import Choreography
from generator.snippet.newSnippet import snippet as dsl_snippet


BPMN_TYPE_TO_DSL = {
    "string": "string",
    "number": "int",
    "integer": "int",
    "boolean": "bool",
    "float": "float64",
    "float64": "float64",
}


def map_bpmn_type(origin_type: str) -> str:
    """Translate BPMN primitive types into DSL compatible ones."""
    return BPMN_TYPE_TO_DSL.get(origin_type, origin_type)


def public_the_name(name: str) -> str:
    """Uppercase the first character to build exported-style identifiers."""
    return "".join(name[:1].upper() + name[1:]) if name else name


def summarize_message_schema(message: Message) -> str:
    """Produce a short schema summary string from message documentation."""
    documentation = message.documentation or ""
    try:
        doc = json.loads(documentation)
    except (TypeError, json.JSONDecodeError):
        return documentation or ""
    properties = doc.get("properties", {})
    if not properties:
        return documentation or ""
    return " + ".join(properties.keys())


def escape_quotes(value: str) -> str:
    """Escape double quotes so schema strings can live inside DSL literals."""
    return value.replace("\"", "\\\"")


@dataclass
class ParticipantMetadata:
    msp: str
    x509: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class MessageDefinition:
    id: str
    sender: str
    receiver: str
    schema: str


class ParticipantMetadataResolver:
    def __init__(self, bindings_path: Optional[Path] = None):
        """Load participant metadata from bindings.json for DSL emission."""
        self._bindings_path = bindings_path or Path(__file__).with_name("bindings.json")
        self._bindings = self._load_bindings()

    def _load_bindings(self) -> Dict[str, Dict[str, object]]:
        """Return the JSON mapping describing participant MSP/X509 info."""
        if not self._bindings_path.exists():
            return {}
        try:
            with self._bindings_path.open("r", encoding="utf8") as handler:
                return json.load(handler)
        except json.JSONDecodeError:
            return {}

    def resolve(self, participant: Participant) -> ParticipantMetadata:
        """Produce metadata for a participant, falling back to sensible defaults."""
        entry = self._bindings.get(participant.id, {})
        name_hint = participant.name or participant.id
        msp = entry.get("msp") or f"{public_the_name(name_hint)}MSP"
        x509 = entry.get("x509") or ""
        attributes = entry.get("attributes") or {}
        if not attributes:
            attributes = {"role": name_hint}
        return ParticipantMetadata(msp=msp, x509=x509, attributes=attributes)


class MessageCatalog:
    def __init__(self, choreography: Choreography):
        """Index BPMN messages and flows for later DSL rendering."""
        self._choreography = choreography
        self._message_flows: Dict[str, MessageFlow] = {}
        for flow in choreography.query_element_with_type(EdgeType.MESSAGE_FLOW):
            if flow.message is None:
                continue
            self._message_flows[flow.message.id] = flow
        self._messages: Dict[str, Message] = {
            message.id: message
            for message in choreography.query_element_with_type(NodeType.MESSAGE)
        }

    def definitions(self) -> List[MessageDefinition]:
        """Return all message definitions with sender/receiver/schema info."""
        definitions: List[MessageDefinition] = []
        for message_id, flow in self._message_flows.items():
            message = self._messages.get(message_id)
            if message is None:
                continue
            definitions.append(
                MessageDefinition(
                    id=message_id,
                    sender=flow.source.id,
                    receiver=flow.target.id,
                    schema=summarize_message_schema(message),
                )
            )
        return definitions


class FlowPlanner:
    def __init__(self, choreography: Choreography, judge_parameters: Dict[str, dict]):
        """Pre-compute successor relationships so flows can be emitted declaratively."""
        self._choreography = choreography
        self._judge_parameters = judge_parameters
        self._message_successors = self._build_message_successors()
        self._event_branch_blocks = self._build_event_branch_map()

    def build(self) -> List[str]:
        """Assemble every DSL flow statement in the canonical order."""
        flows: List[str] = []
        flows.extend(self._start_event_flows())
        message_flows = self._message_flows()
        if flows and message_flows:
            flows.append(dsl_snippet.DSL_EmptyLine())
        flows.extend(message_flows)
        gateway_flows = self._gateway_flows()
        parallel_flows = self._parallel_join_flows()
        if flows and gateway_flows:
            flows.append(dsl_snippet.DSL_EmptyLine())
        flows.extend(gateway_flows)
        if flows and parallel_flows:
            flows.append(dsl_snippet.DSL_EmptyLine())
        flows.extend(parallel_flows)
        business_flows = self._business_rule_flows()
        if flows and business_flows:
            flows.append(dsl_snippet.DSL_EmptyLine())
        flows.extend(business_flows)
        return flows

    def _start_event_flows(self) -> List[str]:
        """Describe how start events enable their first target."""
        flows = []
        for start_event in self._choreography.query_element_with_type(NodeType.START_EVENT):
            target = self._activation_target(start_event.outgoing.target)
            if target:
                flows.append(dsl_snippet.DSL_StartEventEnables(start_event.id, target))
        return flows

    def _message_flows(self) -> List[str]:
        """Describe how messages unlock downstream nodes (and disable rivals)."""
        flows = []
        for message_id, targets in self._message_successors.items():
            if not targets:
                continue
            target_str = self._format_action_chain("enable", targets)
            disabled = self._event_branch_blocks.get(message_id)
            if disabled:
                flows.append(
                    dsl_snippet.DSL_WhenMessageSentDisableEnable(
                        message=message_id,
                        disabled=self._format_action_chain("disable", disabled),
                        enabled=target_str,
                    )
                )
            else:
                flows.append(
                    dsl_snippet.DSL_WhenMessageSentEnable(
                        message=message_id,
                        targets=target_str,
                    )
                )
        return flows

    def _gateway_flows(self) -> List[str]:
        """Emit generic gateway completion flows that enable downstream nodes."""
        flows = []
        gateway_iterable = (
            self._choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
            + self._choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
            + self._choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
        )
        for gateway in gateway_iterable:
            if gateway.type == NodeType.PARALLEL_GATEWAY and len(gateway.incomings or []) > 1:
                continue
            targets = self._successor_targets(gateway)
            if not targets:
                continue
            conditional_branches = self._gateway_condition_branches(gateway)
            if conditional_branches:
                flows.append(
                    dsl_snippet.DSL_WhenGatewayConditional(
                        gateway=gateway.id,
                        branches="".join(conditional_branches),
                    )
                )
                continue
            flows.append(
                dsl_snippet.DSL_WhenGatewayCompletedEnable(
                    gateway=gateway.id,
                    targets=self._format_action_chain("enable", targets),
                )
            )
        return flows

    def _business_rule_flows(self) -> List[str]:
        """Express that business rule completion enables the next step."""
        flows = []
        for rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            target = self._activation_target(rule.outgoing.target)
            targets = self._successor_targets(rule)
            if targets:
                flows.append(
                    dsl_snippet.DSL_WhenBusinessRuleDoneEnable(
                        rule=rule.id,
                        targets=self._format_action_chain("enable", targets),
                    )
                )
        return flows

    def _parallel_join_flows(self) -> List[str]:
        """Emit parallel gateway join semantics requiring multiple prerequisites."""
        flows: List[str] = []
        for gateway in self._choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY):
            incomings = gateway.incomings or []
            if len(incomings) <= 1:
                continue
            sources = []
            for incoming in incomings:
                source_name = self._activation_target(incoming.source)
                if source_name:
                    sources.append(source_name)
            sources = [source for source in sources if source]
            if len(sources) <= 1:
                continue
            targets = self._successor_targets(gateway)
            if not targets:
                continue
            flows.append(
                dsl_snippet.DSL_ParallelGatewayAwait(
                    gateway=gateway.id,
                    sources=", ".join(sources),
                    actions=self._format_prefixed_actions("enable", targets),
                )
            )
        return flows

    def _gateway_condition_branches(self, gateway: Element) -> List[str]:
        """Render conditional branches for gateways with sequence conditions."""
        branches: List[str] = []
        conditional_found = False
        fallback_targets: List[str] = []
        for outgoing in gateway.outgoings or []:
            target = self._activation_target(outgoing.target)
            if not target:
                continue
            branch = self._build_condition_branch(outgoing, target)
            if branch:
                conditional_found = True
                branches.append(branch)
            else:
                fallback_targets.append(target)
        if conditional_found and fallback_targets:
            branches.append(
                dsl_snippet.DSL_GatewayBranchElse(
                    actions=self._format_prefixed_actions("enable", fallback_targets)
                )
            )
        return branches

    def _build_condition_branch(self, sequence_flow: SequenceFlow, target: str) -> Optional[str]:
        """Build a conditional DSL clause for a sequence flow if judge metadata exists."""
        judge = self._judge_parameters.get(sequence_flow.id)
        if not judge:
            return None
        literal = self._format_condition_literal(judge)
        condition = f"{public_the_name(judge['name'])} {judge['relation']} {literal}"
        return dsl_snippet.DSL_GatewayBranchIf(
            condition=condition,
            actions=self._format_prefixed_actions("enable", [target]),
        )

    def _format_condition_literal(self, judge: dict) -> str:
        """Return the DSL literal for a conditional comparison."""
        value = judge.get("value", "")
        value_type = map_bpmn_type(judge.get("type", "string"))
        if value_type == "bool":
            lowered = value.lower()
            return "true" if lowered == "true" else "false"
        if value_type in ("int", "float64", "float"):
            return value
        escaped = escape_quotes(value)
        return f'"{escaped}"'

    def _activation_target(self, element: Optional[Element]) -> Optional[str]:
        """Map any BPMN element to the DSL identifier that becomes active."""
        if element is None:
            return None
        if element.type == NodeType.CHOREOGRAPHY_TASK:
            init_flow = element.init_message_flow
            if init_flow:
                return init_flow.message.id
            return None
        return element.id

    def _successor_targets(self, element: Element) -> List[str]:
        """Return all DSL identifiers that follow the given element."""
        raw_targets: List[Optional[Element]] = []
        outgoings = getattr(element, "outgoings", None)
        if outgoings:
            raw_targets.extend(outgoing.target for outgoing in outgoings)
        outgoing = getattr(element, "outgoing", None)
        if outgoing:
            raw_targets.append(outgoing.target)
        targets: List[str] = []
        for raw in raw_targets:
            target = self._activation_target(raw)
            if target:
                targets.append(target)
        return targets

    def _build_message_successors(self) -> Dict[str, List[str]]:
        """Create adjacency lists for messages to their follow-up elements."""
        mapping: Dict[str, List[str]] = {}
        for task in self._choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK):
            init_flow = task.init_message_flow
            if not init_flow:
                continue
            init_message = init_flow.message.id
            if task.return_message_flow:
                mapping[init_message] = [task.return_message_flow.message.id]
                mapping[task.return_message_flow.message.id] = self._targets_from_element(task.outgoing.target)
            else:
                mapping[init_message] = self._targets_from_element(task.outgoing.target)
        return mapping

    @staticmethod
    def _format_action_chain(prefix: str, targets: List[str]) -> str:
        """Format a list like `MessageA, prefix MessageB` for DSL action grammar."""
        if not targets:
            return ""
        head, *tail = targets
        suffix = "".join(f", {prefix} {target}" for target in tail)
        return f"{head}{suffix}"

    @staticmethod
    def _format_prefixed_actions(prefix: str, targets: List[str]) -> str:
        """Return all targets with the prefix applied, separated by commas."""
        items = [target for target in targets if target]
        return ", ".join(f"{prefix} {target}" for target in items)

    def _targets_from_element(self, element: Optional[Element]) -> List[str]:
        """Return a list wrapper around _activation_target for uniform consumers."""
        target = self._activation_target(element)
        return [target] if target else []

    def _build_event_branch_map(self) -> Dict[str, List[str]]:
        """Track mutually-exclusive event branches to emit disable statements."""
        mapping: Dict[str, List[str]] = {}
        for gateway in self._choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY):
            branch_messages = []
            for outgoing in gateway.outgoings:
                target = self._activation_target(outgoing.target)
                if target:
                    branch_messages.append(target)
            for message_id in branch_messages:
                others = [branch for branch in branch_messages if branch != message_id]
                if others:
                    mapping[message_id] = others
        return mapping


class DSLContractBuilder:
    def __init__(
        self,
        choreography: Choreography,
        global_parameters: Dict[str, dict],
        judge_parameters: Optional[Dict[str, dict]] = None,
    ):
        """Bundle together helpers that transform BPMN metadata into DSL sections."""
        self._choreography = choreography
        self._global_parameters = global_parameters
        self._participant_metadata = ParticipantMetadataResolver()
        self._message_catalog = MessageCatalog(choreography)
        self._flow_planner = FlowPlanner(choreography, judge_parameters or {})

    def build(self, contract_name: str) -> str:
        """Render the full DSL contract with all sections filled."""
        participants = self._build_participants_section()
        globals_section = self._build_globals_section()
        messages = self._build_messages_section()
        gateways = self._build_gateways_section()
        events = self._build_events_section()
        businessrules = self._build_business_rules_section()
        flows_section = self._build_flows_section()
        return dsl_snippet.DSL_ContractFrame(
            contract_name=contract_name,
            participants=participants,
            globals_=globals_section,
            messages=messages,
            gateways=gateways,
            events=events,
            businessrules=businessrules,
            flows=flows_section,
        )

    def _build_participants_section(self) -> str:
        """Render the participants block using resolved metadata."""
        items = []
        for participant in self._choreography.query_element_with_type(NodeType.PARTICIPANT):
            metadata = self._participant_metadata.resolve(participant)
            attributes_block = "".join(
                dsl_snippet.DSL_ParticipantAttributeItem(key=key, value=value)
                for key, value in metadata.attributes.items()
            )
            items.append(
                dsl_snippet.DSL_ParticipantItem(
                    pid=participant.id,
                    msp=metadata.msp,
                    x509=metadata.x509,
                    is_multi=participant.is_multi,
                    multi_min=participant.multi_minimum,
                    multi_max=participant.multi_maximum,
                    attributes=attributes_block,
                )
            )
        return dsl_snippet.DSL_ParticipantsFrame("".join(items))

    def _build_globals_section(self) -> str:
        """List every inferred global variable and its DSL type."""
        items = []
        for name, definition in sorted(self._global_parameters.items()):
            type_name = definition["definition"].get("type", "string")
            items.append(
                dsl_snippet.DSL_GlobalItem(
                    name=public_the_name(name),
                    type_=map_bpmn_type(type_name),
                )
            )
        return dsl_snippet.DSL_GlobalsFrame("".join(items))

    def _build_messages_section(self) -> str:
        """Render message declarations with initial state and schema summary."""
        items = []
        for definition in sorted(self._message_catalog.definitions(), key=lambda item: item.id):
            items.append(
                dsl_snippet.DSL_MessageItem(
                    id=definition.id,
                    sender=definition.sender,
                    receiver=definition.receiver,
                    state=dsl_snippet.MapElementState("DISABLED"),
                    schema=escape_quotes(definition.schema),
                )
            )
        return dsl_snippet.DSL_MessagesFrame("".join(items))

    def _build_gateways_section(self) -> str:
        """Render each gateway with its type label and initial state."""
        items = []
        for gateway in self._choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY) + self._choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY) + self._choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY):
            items.append(
                dsl_snippet.DSL_GatewayItem(
                    id=gateway.id,
                    type_=self._gateway_type_label(gateway),
                    state=dsl_snippet.MapElementState("DISABLED"),
                )
            )
        return dsl_snippet.DSL_GatewaysFrame("".join(items))

    def _gateway_type_label(self, gateway: Element) -> str:
        """Return the textual DSL label for a gateway type."""
        match gateway.type:
            case NodeType.EXCLUSIVE_GATEWAY:
                return "exclusive"
            case NodeType.PARALLEL_GATEWAY:
                return "parallel"
            case NodeType.EVENT_BASED_GATEWAY:
                return "event"
            case _:
                return "gateway"

    def _build_events_section(self) -> str:
        """Emit both start/end event blocks with their initial state."""
        items = []
        for event in self._choreography.query_element_with_type(NodeType.START_EVENT):
            items.append(
                dsl_snippet.DSL_EventItem(
                    id=event.id,
                    state=dsl_snippet.MapElementState("ENABLED"),
                )
            )
        for event in self._choreography.query_element_with_type(NodeType.END_EVENT):
            items.append(
                dsl_snippet.DSL_EventItem(
                    id=event.id,
                    state=dsl_snippet.MapElementState("DISABLED"),
                )
            )
        return dsl_snippet.DSL_EventsFrame("".join(items))

    def _build_business_rules_section(self) -> str:
        """Render business rule declarations with DMN metadata and mappings."""
        items = []
        for rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            documentation = rule.documentation or "{}"
            try:
                doc = json.loads(documentation)
            except json.JSONDecodeError:
                doc = {}
            input_block = "".join(
                dsl_snippet.DSL_BusinessRuleInputMappingItem(
                    param=entry.get("name", ""),
                    global_var=public_the_name(entry.get("name", "")),
                )
                for entry in doc.get("inputs", [])
            )
            output_block = "".join(
                dsl_snippet.DSL_BusinessRuleOutputMappingItem(
                    param=entry.get("name", ""),
                    global_var=public_the_name(entry.get("name", "")),
                )
                for entry in doc.get("outputs", [])
            )
            items.append(
                dsl_snippet.DSL_BusinessRuleItem(
                    id=rule.id,
                    dmn=f"{rule.id}.dmn",
                    decision=f"{rule.id}_DecisionID",
                    input_map=input_block,
                    output_map=output_block,
                    state=dsl_snippet.MapElementState("DISABLED"),
                )
            )
        return dsl_snippet.DSL_BusinessRulesFrame("".join(items))

    def _build_flows_section(self) -> str:
        """Wrap planned flow statements inside the flows frame."""
        flow_lines = self._flow_planner.build()
        return dsl_snippet.DSL_FlowsFrame("".join(flow_lines))


class ParameterExtractor:
    def __init__(self, choreography: Choreography):
        """Hold onto the choreography so we can compute globals and judge params."""
        self._choreography = choreography

    def extract(self) -> tuple[dict, dict]:
        """
        Produce two artifacts used downstream by the translator:

        * global_parameters: canonical definition of every inferred global variable.
        * judge_parameters: structured metadata for exclusive-gateway conditions.

        The workflow follows the same order that will later appear in a Latex/algorithm
        description: (1) harvest message schemas, (2) inspect business rule I/O,
        (3) merge everything into a parameter catalogue, and (4) analyse sequence
        flow conditions.
        """

        message_properties = self._collect_message_properties()
        business_rule_docs = list(self._business_rule_docs())

        global_parameters = self._build_global_parameter_map(
            message_properties,
            business_rule_docs,
        )

        available_definitions = {
            name: data["definition"] for name, data in global_parameters.items()
        }
        judge_parameters = self._collect_sequence_flow_conditions(
            available_definitions,
            global_parameters,
        )
        return global_parameters, judge_parameters

    def _business_rule_docs(self):
        """Yield business rule documentation blobs in parsed JSON form."""
        for business_rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            if not business_rule.documentation:
                continue
            try:
                yield business_rule, json.loads(business_rule.documentation)
            except json.JSONDecodeError:
                continue

    def _build_global_parameter_map(
        self,
        message_properties: dict,
        business_rule_data: list,
    ) -> dict:
        """
        Merge all potential parameter sources into the global catalogue.

        Priority order:
            1. Message schemas (fields declared in BPMN documentation).
            2. Business rule inputs (may reuse message fields or introduce new ones).
            3. Business rule outputs (always registered as fresh globals).
        """

        global_parameters = {
            name: {"definition": definition}
            for name, definition in sorted(message_properties.items())
        }

        business_rule_inputs = self._collect_business_rule_inputs(
            message_properties,
            business_rule_data,
        )
        for name, definition in business_rule_inputs.items():
            self._ensure_global_definition(global_parameters, name, definition)

        business_rule_outputs = self._collect_business_rule_outputs(business_rule_data)
        for name, definition in business_rule_outputs.items():
            self._ensure_global_definition(global_parameters, name, definition)

        return global_parameters

    def _collect_message_properties(self) -> dict:
        """Collect message property definitions keyed by property name."""
        message_properties = {}
        for message in self._choreography.query_element_with_type(NodeType.MESSAGE):
            if message.documentation == "{}":
                continue
            document_dict = json.loads(message.documentation)
            for name, attri in document_dict.get("properties", {}).items():
                message_properties[name] = {
                    **attri,
                    "message_id": ([message.id] + message_properties[name]["message_id"]) if name in message_properties else [message.id],
                    "source_type": "message",
                }
        return message_properties

    def _collect_business_rule_inputs(self, message_properties: dict, business_rule_data: list) -> dict:
        """Determine which message or DMN-defined properties are consumed by business rules."""
        referenced_parameters = {}
        for business_rule, definition in business_rule_data:
            for input_def in definition.get("inputs", []):
                name = input_def.get("name")
                if not name:
                    continue
                prop_definition = message_properties.get(name)
                if prop_definition is None:
                    inferred_type = input_def.get("type", "string")
                    prop_definition = {
                        "type": inferred_type,
                        "description": input_def.get("description"),
                        "source_type": "business_rule_input",
                        "business_rule_id": [business_rule.id],
                    }
                referenced_parameters[name] = {
                    "definition": prop_definition,
                }
        return referenced_parameters

    def _collect_business_rule_outputs(self, business_rule_data: list) -> dict:
        """Identify business rule outputs and expose them as globals."""
        outputs = {}
        for business_rule, definition in business_rule_data:
            for output_def in definition.get("outputs", []):
                outputs[output_def["name"]] = {
                    "type": output_def.get("type"),
                    "business_rule_id": [business_rule.id],
                    "description": output_def.get("description"),
                    "source_type": "business_rule",
                }
        return outputs

    def _collect_sequence_flow_conditions(self, available_definitions: dict, global_parameters: dict) -> dict:
        """Parse exclusive-gateway conditions into structured judge metadata."""
        judge_parameters = {}
        for sequence_flow in self._choreography.query_element_with_type(EdgeType.SEQUENCE_FLOW):
            raw_expression = sequence_flow.condition_expression or sequence_flow.name
            condition = self._parse_sequence_condition(raw_expression)
            if condition is None:
                continue
            prop, relation, value = condition
            prop_definition = available_definitions.get(prop)
            if prop_definition is None:
                inferred_definition = {
                    "type": self._infer_literal_type(value),
                    "source_type": "condition",
                    "condition_sequence_ids": [sequence_flow.id],
                }
                available_definitions[prop] = inferred_definition
                self._ensure_global_definition(global_parameters, prop, inferred_definition)
                prop_definition = inferred_definition
            else:
                self._ensure_global_definition(global_parameters, prop, prop_definition)
            judge_parameters[sequence_flow.id] = {
                "name": prop,
                "value": value,
                "type": prop_definition["type"],
                "relation": relation,
            }
        return judge_parameters

    @staticmethod
    def _parse_sequence_condition(raw_condition: str) -> Optional[tuple[str, str, str]]:
        """Split a textual condition like `foo>=3` into its components."""
        if not raw_condition:
            return None
        for relation in ("==", "!=", ">=", "<=", ">", "<"):
            if relation in raw_condition:
                prop, value = raw_condition.split(relation, 1)
                return prop.strip(), relation, value.strip()
        return None

    @staticmethod
    def _infer_literal_type(value: str) -> str:
        """Guess a DSL type from a literal string in a condition expression."""
        candidate = value.strip().strip('"').strip("'")
        lowered = candidate.lower()
        if lowered in {"true", "false"}:
            return "bool"
        try:
            int(candidate)
            return "int"
        except ValueError:
            pass
        try:
            float(candidate)
            return "float"
        except ValueError:
            pass
        return "string"

    @staticmethod
    def _ensure_global_definition(target: dict, name: str, definition: dict) -> None:
        """Populate the global_parameters map if the variable is not already declared."""
        target.setdefault(name, {"definition": definition})


class GoChaincodeTranslator:
    def __init__(self, bpmnContent: Optional[str] = None, bpmn_file: Optional[str] = None, config: Optional[dict] = None):
        """Parse BPMN input immediately so subsequent helpers can query it."""
        self._config = config or {}
        choreography = Choreography()
        if bpmnContent:
            choreography.load_diagram_from_string(bpmnContent)
        elif bpmn_file:
            choreography.load_diagram_from_xml_file(bpmn_file)
        else:
            # keep the choreography empty so helper APIs still respond
            pass
        self._choreography = choreography
        extractor = ParameterExtractor(self._choreography)
        self._global_parameters, self._judge_parameters = extractor.extract()

    def _default_contract_name(self) -> str:
        """Derive a contract name from the BPMN start event when possible."""
        start_events = self._choreography.query_element_with_type(NodeType.START_EVENT)
        if start_events and start_events[0].name:
            return public_the_name(start_events[0].name.replace(" ", ""))
        return "GeneratedContract"

    def generate_chaincode(self, output_path: str = "resource/contract.b2c", is_output: bool = False, contract_name: Optional[str] = None) -> str:
        """Render the DSL contract and optionally persist it to disk."""
        builder = DSLContractBuilder(self._choreography, self._global_parameters, self._judge_parameters)
        dsl_code = builder.build(contract_name or self._default_contract_name())
        if is_output:
            Path(output_path).write_text(dsl_code, encoding="utf8")
        return dsl_code

    def generate_ffi(self, *_, **__):
        """Placeholder for legacy API compatibility until DSL FFI is defined."""
        return json.dumps({})

    def get_participants(self):
        """Expose participant IDs and names for API consumers."""
        return {
            participant.id: participant.name
            for participant in self._choreography.query_element_with_type(NodeType.PARTICIPANT)
        }

    def get_messages(self):
        """Return message IDs along with their display metadata."""
        return {
            message.id: {
                "name": message.name,
                "documentation": message.documentation,
            }
            for message in self._choreography.query_element_with_type(NodeType.MESSAGE)
        }

    def get_businessrules(self):
        """Expose business rule documentation for UI/editor clients."""
        return {
            business_rule.id: {
                "name": business_rule.name,
                "documentation": business_rule.documentation,
            }
            for business_rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
        }


if __name__ == "__main__":
    demo_file = Path(__file__).with_name("resource").joinpath("bpmn", "BokeRental.bpmn")
    if demo_file.exists():
        translator = GoChaincodeTranslator(bpmn_file=str(demo_file))
        print(translator.generate_chaincode())
