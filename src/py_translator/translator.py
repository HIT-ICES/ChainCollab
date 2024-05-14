from typing import List, Optional, Tuple, Any, Protocol, Union
from choreography_parser.elements import (
    Participant,
    StartEvent,
    EndEvent,
    Message,
    NodeType,
    EdgeType,
    ChoreographyTask,
    ExclusiveGateway,
    ParallelGateway,
    EventBasedGateway,
    MessageFlow,
    SequenceFlow,
    Element,
)
from choreography_parser.parser import Choreography
from chaincode_snippet import snippet
import json


def type_change_from_bpmn_to_go(type: str) -> str:
    if type == "string":
        return "string"
    if type == "integer":
        return "int"
    if type == "boolean":
        return "bool"
    if type == "float":
        return "float64"
    return type


def public_the_name(name: str) -> str:
    return name.capitalize()


class GoChaincodeTranslator:
    def __init__(self):
        self._choreography: Choreography = None
        self._global_variabels: dict = None
        self._judge_parameters: dict = None
        self._hook_codes: dict = None

    def _extract_global_parameters(self) -> dict:
        choreography = self._choreography
        global_parameters = {}
        judge_parameters = (
            {}
        )  # {sequence_flow_id: {name: value, type: type, relation: relation}}
        message_properties = {}
        # Step 1: extract parameters from properties
        for message in choreography.query_element_with_type(NodeType.MESSAGE):
            if message.documentation == "{}":
                continue
            document_dict = json.loads(message.documentation)
            #   {
            #       "properties": {
            #           "<name>": {"type":"<type>","description":"<description>"},},
            #       "required": [],
            #       "files": {},
            #       "file required": {}
            # }
            for name, attri in document_dict["properties"].items():
                message_properties[name] = {
                    **{
                        "message_id": (
                            [message.id] + message_properties[name]["message_id"]
                            if name in message_properties
                            else [message.id]
                        )
                    },
                    **attri,
                }

        # Step 2: extract parameters from sequence flow
        # Step 3: match parameters from properties and sequence flow
        for sequence_flow in choreography.query_element_with_type(
            EdgeType.SEQUENCE_FLOW
        ):
            name = sequence_flow.name
            if name == "":
                continue
            # name possible value
            #   [A]==[B]
            #   [A]!=[B]
            #   [A]>[B]
            #   [A]<[B]
            #   [A]>=[B]
            #   [A]<=[B]
            #   [A] means the property of the message
            #   [B] means the value of the property
            match name:
                case x if "==" in x:
                    prop, value = x.split("==")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": "==",
                    }
                case x if "!=" in x:
                    prop, value = x.split("!=")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": "!=",
                    }
                case x if ">" in x:
                    prop, value = x.split(">")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": ">",
                    }
                case x if "<" in x:
                    prop, value = x.split("<")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": "<",
                    }
                case x if ">=" in x:
                    prop, value = x.split(">=")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": ">=",
                    }
                case x if "<=" in x:
                    prop, value = x.split("<=")
                    prop_defination = message_properties.get(prop)
                    if prop_defination is None:
                        continue
                    global_parameters[prop] = {
                        "definition": prop_defination,
                    }
                    judge_parameters[sequence_flow.id] = {
                        "name": prop,
                        "value": value,
                        "type": prop_defination["type"],
                        "relation": "<=",
                    }

        return global_parameters, judge_parameters

    def _generate_parameters_code(self) -> str:
        global_parameters = self._global_parameters
        temp_list = []
        for name, prop in global_parameters.items():
            type = prop["definition"]["type"]
            # type may need to be converted to golang type
            # boolean -> bool
            # integer -> int
            # string -> string
            # float -> float64
            temp_list.append(
                snippet.StateMemoryParameterDefinition_code(
                    public_the_name(name), type_change_from_bpmn_to_go(type)
                )
            )
        return "\n\t".join(temp_list)

    def _generate_InitLedger(self):
        choreography = self._choreography
        temp_list = []
        start_event: StartEvent = choreography.query_element_with_type(
            NodeType.START_EVENT
        )[0]
        end_events: EndEvent = choreography.query_element_with_type(NodeType.END_EVENT)
        message_flows: List[MessageFlow] = choreography.query_element_with_type(
            EdgeType.MESSAGE_FLOW
        )
        gateways: List[Union[ExclusiveGateway, ParallelGateway, EventBasedGateway]] = (
            choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
            + choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
            + choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
        )

        temp_list.append(
            snippet.InitLedger_code(
                start_event=start_event.id,
                end_events=[end_event.id for end_event in end_events],
                messages=[
                    {
                        "name": message_flow.message.id,
                        "sender": bindings.get(
                            message_flow.source.id, message_flow.source.id
                        ),
                        "receiver": bindings.get(
                            message_flow.target.id, message_flow.target.id
                        ),
                        "properties": message_flow.message.documentation,
                    }
                    for message_flow in message_flows
                ],
                gateways=[gateway.id for gateway in gateways],
            )
        )
        return temp_list

    def _generate_change_state_code(
        self, element: Element, state: str = "ENABLED"
    ) -> str:
        match element.type:
            case NodeType.CHOREOGRAPHY_TASK:
                return snippet.ChangeMsgState_code(
                    element.init_message_flow.message.id, state
                )
            case (
                NodeType.EXCLUSIVE_GATEWAY
                | NodeType.PARALLEL_GATEWAY
                | NodeType.EVENT_BASED_GATEWAY
            ):
                return snippet.ChangeGtwState_code(element.id, state)
            case NodeType.END_EVENT:
                return snippet.ChangeEventState_code(element.id, state)
            case NodeType.MESSAGE:
                return snippet.ChangeMsgState_code(element.id, state)

    def _generate_check_state_code(self, element: Element, state: str = "ENABLED"):
        match element.type:
            case NodeType.CHOREOGRAPHY_TASK:
                return snippet.CheckMsgState_code(
                    element.init_message_flow.message.id, state
                )
            case (
                NodeType.EXCLUSIVE_GATEWAY
                | NodeType.PARALLEL_GATEWAY
                | NodeType.EVENT_BASED_GATEWAY
            ):
                return snippet.CheckGatewayState_code(element.id, state)
            case NodeType.END_EVENT:
                return snippet.CheckEventState_code(element.id, state)

    def _generate_message_record_parameters_code(self, message: Message):
        global_parameters = self._global_parameters
        params_to_add = []
        for parameter in global_parameters:
            if message.id in global_parameters[parameter]["definition"]["message_id"]:
                params_to_add.append((parameter, global_parameters[parameter]))
        # generate parameters code
        more_params_code = ", " + ", ".join(
            [
                public_the_name(param[0])
                + " "
                + type_change_from_bpmn_to_go(param[1]["definition"]["type"])
                for param in params_to_add
            ]
        )
        # generate put state code
        put_more_params_code = "\n".join(
            [
                snippet.SetGlobalVariable_code(
                    name=public_the_name(param[0]), value=public_the_name(param[0])
                )
                for param in params_to_add
            ]
        )
        return more_params_code, put_more_params_code

    def _event_based_gateway_hook_code(
        self, event_based_gateway: EventBasedGateway, currentElement: Element
    ):
        # find all other branches
        other_elements = []
        for outgoing in event_based_gateway.outgoings:
            if outgoing.target != currentElement:
                other_elements.append(outgoing.target)
        temp_list = [
            self._generate_change_state_code(element, "DISABLED")
            for element in other_elements
        ]
        return "\n".join(temp_list)

    def _parallel_gateway_merge_hook_code(
        self, parallel_gateway: ParallelGateway, currentElement: Element
    ):
        # find all other branches
        other_elements = []
        for incoming in parallel_gateway.incomings:
            if incoming.source != currentElement:
                other_elements.append(incoming.source)
        # check if other branches are "COMPLETED"
        conditions = [
            self._generate_check_state_code(element, "COMPLETED")
            for element in other_elements
        ]
        combined_condition = snippet.CombineConditions_Any_False_code(conditions)
        return snippet.ConditionToHalt_code(combined_condition)

    def _generate_chaincode_for_choreography_task(
        self,
        choreography_task: ChoreographyTask,
    ):
        temp_list = []
        next_element = choreography_task.outgoing.target
        init_message_flow = choreography_task.init_message_flow
        return_message_flow = choreography_task.return_message_flow

        pre_activate_next_hook = self._hook_codes[choreography_task.id][
            "pre_activate_next"
        ]
        when_triggered_code = self._hook_codes[choreography_task.id]["when_triggered"]

        if not init_message_flow:
            return temp_list

        if not return_message_flow:
            more_parameters, put_more_parameters = (
                self._generate_message_record_parameters_code(init_message_flow.message)
            )
            # find parameters
            temp_list.append(
                # To Modify, may be need more parameters than default
                snippet.MessageSend_code(
                    message=init_message_flow.message.id,
                    after_all_hook="\n".join(when_triggered_code),
                    more_parameters=more_parameters,
                    put_more_parameters=put_more_parameters,
                )
            )
            temp_list.append(
                snippet.MessageComplete_code(
                    message=init_message_flow.message.id,
                    change_next_state_code=self._generate_change_state_code(
                        return_message_flow.message
                        if return_message_flow
                        else next_element
                    ),
                    pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                )
            )
            return temp_list

        more_parameters, put_more_parameters = (
            self._generate_message_record_parameters_code(init_message_flow.message)
        )
        temp_list.append(
            snippet.MessageSend_code(
                message=init_message_flow.message.id,
                after_all_hook="\n\t".join(when_triggered_code),
                more_parameters=more_parameters,
                put_more_parameters=put_more_parameters,
            )
        )
        temp_list.append(
            snippet.MessageComplete_code(
                message=init_message_flow.message.id,
                change_next_state_code=self._generate_change_state_code(
                    return_message_flow.message if return_message_flow else next_element
                ),
            )
        )
        more_parameters, put_more_parameters = (
            self._generate_message_record_parameters_code(return_message_flow.message)
        )
        temp_list.append(
            snippet.MessageSend_code(
                message=return_message_flow.message.id,
                more_parameters=more_parameters,
                put_more_parameters=put_more_parameters,
            )
        )
        temp_list.append(
            snippet.MessageComplete_code(
                message=return_message_flow.message.id,
                change_next_state_code=self._generate_change_state_code(next_element),
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
            )
        )
        return temp_list

    def _generate_fullfill_condition_code(self, sequence_flow: SequenceFlow):
        judge_parameters = self._judge_parameters
        if sequence_flow.id in judge_parameters:
            parameter = judge_parameters[sequence_flow.id]
            return (
                # snippet.ReadState_code(public_the_name(parameter["name"]))
                # + "\n"
                public_the_name(parameter["name"])
                + parameter["relation"]
                + parameter["value"]
            )
        return "true"

    def _generate_chaincode_for_exclusive_gateway(
        self,
        exclusive_gateway: ExclusiveGateway,
    ):
        judge_parameters = self._judge_parameters
        temp_list = []
        # judge type
        # type One : one come and multiple out, branch by condition
        # type Two : multiple come and one out, wait for any come
        pre_activate_next_hook = self._hook_codes[exclusive_gateway.id][
            "pre_activate_next"
        ]
        when_triggered_code = self._hook_codes[exclusive_gateway.id]["when_triggered"]

        if len(exclusive_gateway.incomings) == 1:
            # type One
            code = snippet.ExclusiveGateway_split_code(
                gateway=exclusive_gateway.id,
                change_next_state_code="\n".join(
                    [snippet.ReadGlobalMemory_code()]
                    + list(
                        set(
                            [
                                snippet.ReadState_code(
                                    public_the_name(
                                        judge_parameters[outgoing.id]["name"]
                                    )
                                )
                                for outgoing in exclusive_gateway.outgoings
                                if outgoing.id in judge_parameters
                            ]
                        )
                    )
                    + [
                        snippet.ConditionToDo_code(
                            self._generate_fullfill_condition_code(outgoing),
                            self._generate_change_state_code(outgoing.target),
                        )
                        for outgoing in exclusive_gateway.outgoings
                    ]
                ),
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                after_all_hook="\n\t".join(when_triggered_code),
            )
            temp_list.append(code)
        else:
            # type Two
            # outgoings should be only one, otherwise it is not a valid BPMN!!!!
            code = snippet.ExclusiveGateway_merge_code(
                gateway=exclusive_gateway.id,
                change_next_state_code=self._generate_change_state_code(
                    exclusive_gateway.outgoings[0].target
                ),
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                after_all_hook="\n\t".join(when_triggered_code),
            )
            temp_list.append(code)
        return temp_list

    def _generate_chaincode_for_parallel_gateway(
        self, parallel_gateway: ParallelGateway
    ):
        temp_list = []
        # judge type
        # type One : one come and multiple out, activate all out
        # type Two : multiple come and one out, wait for all come
        pre_activate_next_hook = self._hook_codes[parallel_gateway.id][
            "pre_activate_next"
        ]
        when_triggered_code = self._hook_codes[parallel_gateway.id]["when_triggered"]
        if len(parallel_gateway.incomings) == 1:
            # type One
            code = snippet.ParallelGateway_split_code(
                gateway=parallel_gateway.id,
                change_next_state_code="\n".join(
                    [
                        self._generate_change_state_code(outgoing.target)
                        for outgoing in parallel_gateway.outgoings
                    ]
                ),
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                after_all_hook="\n\t".join(when_triggered_code),
            )
            temp_list.append(code)
        else:
            # type Two
            # Nothing special to do, check logic implemented in the hook
            # outgoings should be only one, otherwise it is not a valid BPMN!!!!
            code = snippet.ParallelGateway_merge_code(
                gateway=parallel_gateway.id,
                change_next_state_code="\n".join(
                    [
                        self._generate_change_state_code(
                            parallel_gateway.outgoings[0].target
                        )
                    ]
                ),
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                after_all_hook="\n\t".join(when_triggered_code),
            )
            temp_list.append(code)

        return temp_list

    def _generate_chaincode_for_event_based_gateway(
        self,
        event_based_gateway: EventBasedGateway,
    ):
        temp_list = []
        # No other type
        pre_activate_next_hook = self._hook_codes[event_based_gateway.id][
            "pre_activate_next"
        ]
        when_triggered_code = self._hook_codes[event_based_gateway.id]["when_triggered"]
        code = snippet.EventBasedGateway_code(
            gateway=event_based_gateway.id,
            change_next_state_code="\n".join(
                [
                    self._generate_change_state_code(outgoing.target)
                    for outgoing in event_based_gateway.outgoings
                ]
            ),
            pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
            after_all_hook="\n\t".join(when_triggered_code),
        )
        temp_list.append(code)
        return temp_list

    def _generate_chaincode_for_start_event(self, start_event: StartEvent):
        temp_list = []
        # Assume no hook for start event
        temp_list.append(
            snippet.StartEvent_code(
                start_event.id,
                change_next_state_code=self._generate_change_state_code(
                    start_event.outgoing.target
                ),
            )
        )
        return temp_list

    def _generate_chaincode_for_end_event(self, end_event: EndEvent):
        temp_list = []
        when_triggered_code = self._hook_codes[end_event.id]["when_triggered"]

        temp_list.append(
            snippet.EndEvent_code(
                end_event.id,
                after_all_hook="\n\t".join(when_triggered_code),
            )
        )
        return temp_list

    def generate_chaincode(
        self,
        bpmn_file_path: str,
        bindings: dict[str, str],
        output_path: str = "resource/chaincode.go",
    ):
        ############
        # Init: Set general state
        ############
        choreography: Choreography = Choreography()
        choreography.load_diagram_from_xml_file(bpmn_file_path)
        # add choreography to self
        self._choreography = choreography
        # analyze parameter from properties and sequence flow
        self._global_parameters, self._judge_parameters = (
            self._extract_global_parameters()
        )
        # init Hook
        self._hook_codes = {
            key: {"pre_activate_next": [], "when_triggered": []}
            for key in [node.id for node in choreography.nodes]
        }

        chaincode_list = []

        ########
        # Generate Part: Add common code to chaincode
        ########
        chaincode_list.append(snippet.package_code())
        chaincode_list.append(snippet.import_code())
        chaincode_list.append(snippet.contract_definition_code())
        # global variable definition
        chaincode_list.append(
            snippet.StateMemoryDefinition_code(self._generate_parameters_code())
        )
        chaincode_list.append(snippet.fix_part_code())
        # chaincode_list.append(snippet.state_read_and_put_code())
        chaincode_list.append(snippet.globale_variable_read_and_set_code())

        # generate InitLedger

        chaincode_list.extend(self._generate_InitLedger())

        #########
        # Hook Generate: check structure caused hook code to be inserted into the chaincode, prepare code for real generation
        #########

        # find all event based gateways, and set after_all hook to turn off other branches
        for event_based_gateway in choreography.query_element_with_type(
            NodeType.EVENT_BASED_GATEWAY
        ):
            if len(event_based_gateway.outgoings) > 1:
                for outgoing in event_based_gateway.outgoings:
                    self._hook_codes[outgoing.target.id].setdefault(
                        "when_triggered", []
                    ).append(
                        # generate some code to turn off other branches
                        self._event_based_gateway_hook_code(
                            event_based_gateway, outgoing.target
                        )
                    )

        # find all parallel to parrallel gateways, and set pre_activate_next hook to check if other branch finished

        for parallel_gateway in choreography.query_element_with_type(
            NodeType.PARALLEL_GATEWAY
        ):
            if len(parallel_gateway.incomings) > 1:
                for incoming in parallel_gateway.incomings:
                    self._hook_codes[incoming.id].setdefault(
                        "pre_activate_next", []
                    ).append(
                        # generate some code to check if other branch finished
                        self._parallel_gateway_merge_hook_code(
                            parallel_gateway, incoming.source
                        )
                    )

        #####
        # Real Generate Code: from start event to end event to create the chaincode for every element
        #####

        for element in choreography.nodes:
            if element.type == NodeType.CHOREOGRAPHY_TASK:
                chaincode_list.extend(
                    self._generate_chaincode_for_choreography_task(element)
                )
            if element.type == NodeType.EXCLUSIVE_GATEWAY:
                chaincode_list.extend(
                    self._generate_chaincode_for_exclusive_gateway(element)
                )
            if element.type == NodeType.PARALLEL_GATEWAY:
                chaincode_list.extend(
                    self._generate_chaincode_for_parallel_gateway(element)
                )
            if element.type == NodeType.EVENT_BASED_GATEWAY:
                chaincode_list.extend(
                    self._generate_chaincode_for_event_based_gateway(element)
                )
            if element.type == NodeType.START_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_start_event(element))
            if element.type == NodeType.END_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_end_event(element))

        # OutPut the chaincode
        with open(output_path, "w") as f:
            f.write("\n\n".join(chaincode_list))

    def generate_ffi(self) -> str:
        pass


if __name__ == "__main__":
    go_chaincode_translator = GoChaincodeTranslator()
    bindings = {}
    go_chaincode_translator.generate_chaincode(
        "resource/bpmn/service provider running time example.bpmn", bindings=bindings
    )
