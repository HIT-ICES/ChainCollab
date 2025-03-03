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
    BusinessRuleTask,
    TaskLoopType,
)
from choreography_parser.parser import Choreography
from new_chaincode_snippet import snippet as snippet
import json


def tidy_chaincode(chaincode):
    import subprocess

    try:
        process = subprocess.run(["goimports"], input=chaincode, text=True, capture_output=True, check=True)
        go_code = process.stdout
        return go_code
    except subprocess.CalledProcessError as e:
        print(f"Error during formatting: {e.stderr}")
    return chaincode


def type_change_from_bpmn_to_go(type: str) -> str:
    if type == "string":
        return "string"
    if type == "number":
        return "int"
    if type == "integer":
        return "int"
    if type == "boolean":
        return "bool"
    if type == "float":
        return "float64"
    return type


def public_the_name(name: str) -> str:
    return "".join(name[:1].upper() + name[1:])
    # return name.capitalize()


def bool_handle(origin: bool) -> str:
    return "true" if origin else "false"


default_config = {
    "NeedConfirm": True,
    "NeedIdentityAuth": True,
    "NeedStateCheck": True,
}


class GoChaincodeTranslator:
    def __init__(self, bpmnContent: str, bpmn_file: str = None, config: dict = default_config):
        self._config = config
        self._choreography: Optional[Choreography] = None
        self._global_variabels: Optional[dict] = None
        self._judge_parameters: Optional[dict] = None
        self._hook_codes: Optional[dict] = None
        choreography: Choreography = Choreography()
        if bpmnContent:
            choreography.load_diagram_from_string(bpmnContent)
        elif bpmn_file:
            choreography.load_diagram_from_xml_file(bpmn_file)
        else:
            pass
        self._choreography = choreography
        self._global_parameters, self._judge_parameters = self._extract_global_parameters()
        self._instance_initparameters = self._extract_instance_initparameters()

    def _extract_global_parameters(self) -> dict:
        # We can split the element related with global param into two type: producer and consumer
        # Message with properties is producer
        # BusinessRule and SequenceFlow with condition is consumer

        # so, extract all parameters from properties, and check if it is in consumer's param, to decide whether it is global param or not
        # and there is a consequence problem, now let it go TODO

        choreography = self._choreography
        global_parameters = (
            {}
        )  # {'is_available': {'definition': {'message_id': ['Message_0r9lypd'], 'type': 'boolean', 'description': 'Is the service available?'}}
        judge_parameters = {}  # {sequence_flow_id: {name: value, type: type, relation: relation}}
        message_properties = (
            {}
        )  # {'product Id': {'message_id': ['Message_1qbk325'], 'type': 'string', 'description': 'Delivered product id'}, 'payment amount': {'message_id': ['Message_0o8eyir', 'Message_1q05nnw'], 'type': 'number', 'description': 'payment amount'}
        business_rule_outputs = {}  # {"name":{type:"","business_rule_id":[]}}

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
                    "source_type": "message",
                }
        # Step 2: extract parameters from sequence flow and business rule
        # Step 3: match parameters from properties to that from sequence flow and business rule

        for business_rule in choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            input_and_output_def_of_business_rule = json.loads(business_rule.documentation)
            # {"input":[{{"name":"","type":""}}],"output":{"name":"","type":""}}
            for input_def in input_and_output_def_of_business_rule.get("inputs", []):
                prop_defination = message_properties.get(input_def["name"])
                if prop_defination is None:
                    # Parse Error!
                    continue
                global_parameters[input_def["name"]] = {
                    "definition": prop_defination,
                }
            for output_def in input_and_output_def_of_business_rule.get("outputs", []):
                business_rule_outputs[output_def["name"]] = {
                    "type": output_def["type"],
                    "business_rule_id": [business_rule.id],
                    "description": output_def["description"],
                    "source_type": "business_rule",
                }

        # Logic Change, output always show in Global Variables, for Testing
        for output_name, output_def in business_rule_outputs.items():
            global_parameters[output_name] = {
                "definition": output_def,
            }

        message_properties_plus_business_rule_outputs = {
            **message_properties,
            **business_rule_outputs,
        }

        for sequence_flow in choreography.query_element_with_type(EdgeType.SEQUENCE_FLOW):
            name = sequence_flow.name
            if name == "":
                continue
            {
                # name possible value
                #   [A]==[B]
                #   [A]!=[B]
                #   [A]>[B]
                #   [A]<[B]
                #   [A]>=[B]
                #   [A]<=[B]
                #   [A] means the property of the message
                #   [B] means the value of the property
            }
            match name:
                case x if "==" in x:
                    prop, value = x.split("==")
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
                    prop_defination = message_properties_plus_business_rule_outputs.get(prop)
                    if prop_defination is None:
                        # Parse Error!
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
            _type = prop["definition"]["type"]
            # type may need to be converted to golang type
            # boolean -> bool
            # integer -> int
            # number -> int
            # string -> string
            # float -> float64
            temp_list.append(
                snippet.StructParameterDefinition_code(public_the_name(name), type_change_from_bpmn_to_go(_type))
            )
        return "\n\t".join(temp_list)

    def _extract_instance_initparameters(self) -> dict:
        # How to extract instance parameters?
        # Get all participant elements
        instance_initparameters = {}
        participants = self._choreography.query_element_with_type(NodeType.PARTICIPANT)
        instance_initparameters["Participant"] = {}
        for participant in participants:
            instance_initparameters["Participant"][participant.id] = {
                "is_multi": participant.is_multi,
                "multi_minimum": participant.multi_minimum,
                "multi_maximum": participant.multi_maximum,
            }
        # DMN ELEMENTS: TODO
        business_rules = self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
        instance_initparameters["BusinessRuleTask"] = {}
        for business_rule in business_rules:
            instance_initparameters["BusinessRuleTask"][business_rule.id] = {}
        return instance_initparameters

    def _generate_instance_initparameters_code(self) -> str:
        instance_initparameters = self._instance_initparameters
        temp_list = []
        for name, prop in instance_initparameters["Participant"].items():
            temp_list.append(snippet.StructParameterDefinition_code(public_the_name(name), "ParticipantForInit"))
        for name, prop in instance_initparameters["BusinessRuleTask"].items():
            # temp_list.append(
            #     snippet.StructParameterDefinition_code(
            #         public_the_name(name), "BusinessRule"
            #     )
            # )
            # only Content、DecisionID、ParamMapping
            # content field of DMN
            temp_list.append(snippet.StructParameterDefinition_code(public_the_name(name) + "_DecisionID", "string"))
            temp_list.append(
                snippet.StructParameterDefinition_code(public_the_name(name) + "_ParamMapping", "map[string]string")
            )
            temp_list.append(snippet.StructParameterDefinition_code(public_the_name(name) + "_Content", "string"))
        return "\n\t".join(temp_list)

    def _generate_create_instance_code(self):
        choreography = self._choreography
        temp_list = []
        start_event: StartEvent = choreography.query_element_with_type(NodeType.START_EVENT)[0]
        end_events: EndEvent = choreography.query_element_with_type(NodeType.END_EVENT)
        gateways: List[Union[ExclusiveGateway, ParallelGateway, EventBasedGateway]] = (
            choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
            + choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
            + choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
        )

        participants_exist = [element.id for element in choreography.query_element_with_type(NodeType.PARTICIPANT)]

        participant_to_be_added = [
            {
                "id": participant,
                "is_multi": bool_handle(self._instance_initparameters["Participant"][participant]["is_multi"]),
                "multi_maximum": self._instance_initparameters["Participant"][participant]["multi_maximum"],
                "multi_minimum": self._instance_initparameters["Participant"][participant]["multi_minimum"],
                "loop_type": self._instance_initparameters["Participant"][participant].get("loop_type", "Standard"),
                "loop_cardinality": self._instance_initparameters["Participant"][participant].get(
                    "loop_cardinality", 1
                ),
            }
            for participant in participants_exist
        ]
        business_rules = [business_rule for business_rule in self._instance_initparameters["BusinessRuleTask"]]



        def get_message_properties(message_flow: MessageFlow, choreography_task: ChoreographyTask) -> List[dict]:
            message_id = message_flow.message.id
            sender_id = message_flow.source.id
            receiver_id = message_flow.target.id
            choreography_task_id = choreography_task.id

            # any of the participants is multi
            is_multi = any([participant.is_multi for participant in choreography_task.participants])

            loop_type = choreography_task.loop_type

            messages = []
            messages.append(
                    {
                        "id": message_id,
                        "sender": sender_id,
                        "receiver": receiver_id,
                        "choreography_task": choreography_task_id,
                        "properties": message_flow.message.documentation,
                        "is_multi": bool_handle(is_multi),
                    }
                )
            if loop_type in [TaskLoopType.MULTI_INSTANCE_PARALLEL, TaskLoopType.MULTI_INSTANCE_SEQUENTIAL] and choreography_task.loop_cardinality > 1:
                for i in range(1, choreography_task.loop_cardinality):
                    messages.append(
                        {
                            "id": f"{message_id}_{i}",
                            "sender": sender_id,
                            "receiver": receiver_id,
                            "choreography_task": choreography_task_id,
                            "properties": message_flow.message.documentation,
                            "is_multi": bool_handle(is_multi),
                        }
                    )

            return messages

        # Generate messages with multi-instance support
        messages = []
        choreography_tasks = choreography.query_element_with_type(
            NodeType.CHOREOGRAPHY_TASK
        )  # Get all ChoreographyTasks
        for choreography_task in choreography_tasks:
            for message_flow in choreography_task.message_flows:  # Get MessageFlow from each ChoreographyTask
                messages.extend(get_message_properties(message_flow, choreography_task))


        def get_list_item(target_list, index: int, default):
            return target_list[index] if len(target_list) > index else default

        choreography_tasks = [
            {
                "id": choreography_task.id,
                "is_multi": bool_handle(choreography_task.is_multi),
                "multi_type": choreography_task.loop_type,
                "init_message": get_list_item(
                    [
                        message_flow.message.id
                        for message_flow in choreography_task.message_flows
                        if message_flow.source.id == choreography_task.init_participant.id
                    ],
                    0,
                    "",
                ),
                "response_message": get_list_item(
                    [
                        message_flow.message.id
                        for message_flow in choreography_task.message_flows
                        if message_flow.target.id == choreography_task.init_participant.id
                    ],
                    0,
                    "",
                ),
            }
            for choreography_task in choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)
        ]


        temp_list.append(
            snippet.CreateInstance_code(
                start_event=start_event.id,
                end_events=[end_event.id for end_event in end_events],
                choreography_tasks=choreography_tasks,
                messages=messages,
                gateways=[gateway.id for gateway in gateways],
                participants=participant_to_be_added,
                business_rules=business_rules,
            )
        )

        return temp_list

    def _generate_change_state_code(self, element: Element, state: str = "ENABLED") -> str:
        match element.type:
            case NodeType.CHOREOGRAPHY_TASK:
                return snippet.ChangeMsgState_code(element.init_message_flow.message.id, state)
            case NodeType.EXCLUSIVE_GATEWAY | NodeType.PARALLEL_GATEWAY | NodeType.EVENT_BASED_GATEWAY:
                return snippet.ChangeGtwState_code(element.id, state)
            case NodeType.END_EVENT:
                return snippet.ChangeEventState_code(element.id, state)
            case NodeType.MESSAGE:
                return snippet.ChangeMsgState_code(element.id, state)
            case NodeType.BUSINESS_RULE_TASK:
                return snippet.ChangeBusinessRuleState_code(element.id, state)

    def _generate_check_state_code(self, element: Element, state: str = "ENABLED"):
        match element.type:
            case NodeType.CHOREOGRAPHY_TASK:
                return snippet.CheckMessageState_code(element.init_message_flow.message.id, state)
            case NodeType.EXCLUSIVE_GATEWAY | NodeType.PARALLEL_GATEWAY | NodeType.EVENT_BASED_GATEWAY:
                return snippet.CheckGatewayState_code(element.id, state)
            case NodeType.END_EVENT:
                return snippet.CheckEventState_code(element.id, state)

    def _get_message_params(self, message: Message):
        global_parameters = self._global_parameters
        message_global_parameters = {
            param: global_parameters[param]
            for param in global_parameters
            if global_parameters[param]["definition"]["source_type"] == "message"
        }
        params_to_add = []
        for parameter in message_global_parameters:
            if message.id in message_global_parameters[parameter]["definition"]["message_id"]:
                params_to_add.append(
                    (
                        parameter,
                        message_global_parameters[parameter]["definition"]["type"],
                    )
                )
        return params_to_add

    def _generate_message_record_parameters_code(self, message: Message) -> Tuple[str, str]:
        params_to_add = self._get_message_params(message)
        # generate parameters code
        more_params_code = (
            ", "
            + ", ".join(
                [public_the_name(param[0]) + " " + type_change_from_bpmn_to_go(param[1]) for param in params_to_add]
            )
            if params_to_add
            else ""
        )
        # generate put state code
        put_more_params_code = (
            "\n".join(
                [
                    snippet.SetGlobalVariable_code(
                        "\n".join(
                            [
                                snippet.SetGlobalVaribaleItem_code(
                                    name=public_the_name(param[0]),
                                    value=public_the_name(param[0]),
                                )
                                for param in params_to_add
                            ]
                        )
                    )
                ]
            )
            if params_to_add
            else ""
        )

        # generate event send state code
        put_more_event_parameter_code = (
            "\n".join(
                [
                    f'"{public_the_name(param[0])}": {public_the_name(param[0])},' for param in params_to_add
                ]
            )
        )

        return more_params_code, put_more_params_code, put_more_event_parameter_code


    def _event_based_gateway_hook_code(self, event_based_gateway: EventBasedGateway, currentElement: Element):
        # find all other branches
        other_elements = []
        for outgoing in event_based_gateway.outgoings:
            if outgoing.target != currentElement:
                other_elements.append(outgoing.target)
        temp_list = [self._generate_change_state_code(element, "DISABLED") for element in other_elements]
        return "\n".join(temp_list)

    def _parallel_gateway_merge_hook_code(self, parallel_gateway: ParallelGateway, currentElement: Element):
        # find all other branches
        other_elements = [
            incoming.source for incoming in parallel_gateway.incomings if incoming.source != currentElement
        ]
        # check if other branches are "COMPLETED"
        conditions = [self._generate_check_state_code(element, "COMPLETED") for element in other_elements]
        combined_condition = snippet.CombineConditions_Any_False_code(conditions)
        return snippet.ConditionToHalt_code(combined_condition)

    def _generate_chaincode_for_choreography_task(
        self,
        choreography_task: ChoreographyTask,
    ) -> list:
        def generate_chaincode_for_message(
            message_id,
            more_params_code,
            put_more_params_code,
            put_more_event_parameters,
            need_confirm=True,
        ):
            code_list = []
            code_list.append(
                snippet.MessageSend_code(
                    message=message_id,
                    more_parameters=more_params_code,
                    put_more_parameters=put_more_params_code,
                    put_more_event_parameters=put_more_event_parameters,
                )
            )
            if need_confirm:
                code_list.append(snippet.MessageComplete_code(message=message_id))
            code_list.append(snippet.MessageAdvance_code(message=message_id))
            return code_list

        temp_list = []
        init_message_flow = choreography_task.init_message_flow
        return_message_flow = choreography_task.return_message_flow

        if not init_message_flow:
            return temp_list
        # print(choreography_task.id)
        # print(choreography_task._is_multi)
        # print(choreography_task.loop_type)

        # Handle single instance or standard multi-instance
        more_parameters, put_more_parameters, put_more_event_parameters = self._generate_message_record_parameters_code(init_message_flow.message)
        temp_list.extend(
            generate_chaincode_for_message(
                message_id=init_message_flow.message.id,
                more_params_code=more_parameters,
                put_more_params_code=put_more_parameters,
                put_more_event_parameters=put_more_event_parameters,
                need_confirm=self._config["NeedConfirm"],
            )
        )

        if return_message_flow:
            more_parameters, put_more_parameters,put_more_event_parameters = self._generate_message_record_parameters_code(
                return_message_flow.message
            )
            temp_list.extend(
                generate_chaincode_for_message(
                    message_id=return_message_flow.message.id,
                    more_params_code=more_parameters,
                    put_more_params_code=put_more_parameters,
                    put_more_event_parameters=put_more_event_parameters,
                    need_confirm=self._config["NeedConfirm"],
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
        return [snippet.Gateway_code(gateway=exclusive_gateway.id)]

    def _generate_chaincode_for_parallel_gateway(self, parallel_gateway: ParallelGateway):
        return [snippet.Gateway_code(gateway=parallel_gateway.id)]

    def _generate_chaincode_for_event_based_gateway(
        self,
        event_based_gateway: EventBasedGateway,
    ):
        return [snippet.Gateway_code(gateway=event_based_gateway.id)]

    def _generate_chaincode_for_start_event(self, start_event: StartEvent):
        return [snippet.Event_code(start_event.id)]

    def _generate_chaincode_for_end_event(self, end_event: EndEvent):
        return [snippet.Event_code(end_event.id)]

    def _generate_chaincode_for_business_rule(self, business_rule: BusinessRuleTask):
        temp_list = []
        pre_activate_next_hook = []
        when_triggered_code = []

        temp_list.append(
            snippet.BusinessRuleFuncFrame_code(
                business_rule.id,
                pre_activate_next_hook="\n\t".join(pre_activate_next_hook),
                after_all_hook="",
                change_next_state_code="",
            )
        )
        temp_list.append(
            snippet.BusinessRuleContinueFuncFrame_code(
                business_rule.id,
                pre_activate_next_hook="",
                after_all_hook="\n\t".join(when_triggered_code),
                change_next_state_code=self._generate_change_state_code(business_rule.outgoing.target),
            )
        )

        return temp_list

    def generate_new_chaincode(self, output_path: str = "result/chaincode.go", is_output: bool = False):

        chaincode_list = []

        ########
        # Generate Part: Add common code to chaincode
        ########

        chaincode_list.append(snippet.package_code())
        chaincode_list.append(
            snippet.import_code(
                if_oracle=len(self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)) > 0,
                if_stateCharts=True,
            )
        )
        chaincode_list.append(snippet.contract_definition_code())
        # global variable definition
        chaincode_list.append(snippet.StateMemoryDefinition_code(self._generate_parameters_code()))
        # initParams definition
        chaincode_list.append(snippet.InitParametersTypeDefFrame_code(self._generate_instance_initparameters_code()))
        chaincode_list.append(snippet.fix_part_code())
        # chaincode_list.append(snippet.CheckRegisterFunc_code())
        # chaincode_list.append(snippet.RegisterFunc_code())
        chaincode_list.append(snippet.InvokeChaincodeFunc_code())
        # generate InitLedger
        chaincode_list.extend(self._generate_create_instance_code())

        #####
        # Real Generate Code: from start event to end event to create the chaincode for every element
        #####

        for element in self._choreography.nodes:
            if element.type == NodeType.CHOREOGRAPHY_TASK:
                chaincode_list.extend(self._generate_chaincode_for_choreography_task(element))
            if element.type == NodeType.EXCLUSIVE_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_exclusive_gateway(element))
            if element.type == NodeType.PARALLEL_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_parallel_gateway(element))
            if element.type == NodeType.EVENT_BASED_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_event_based_gateway(element))
            if element.type == NodeType.START_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_start_event(element))
            if element.type == NodeType.END_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_end_event(element))
            if element.type == NodeType.BUSINESS_RULE_TASK:
                chaincode_list.extend(self._generate_chaincode_for_business_rule(element))
        go_code = "\n\n".join(chaincode_list)

        go_code = tidy_chaincode(go_code)

        if is_output:
            with open(output_path, "w") as f:
                f.write(go_code)

        return go_code

    def generate_chaincode(self, output_path: str = "result/chaincode.go", is_output: bool = False):
        ############
        # Init: Set general state
        ############
        # init Hook
        self._hook_codes = {
            key: {"pre_activate_next": [], "when_triggered": []}
            for key in [node.id for node in self._choreography.nodes]
        }

        chaincode_list = []
        ########
        # Generate Part: Add common code to chaincode
        ########
        chaincode_list.append(snippet.package_code())
        chaincode_list.append(
            snippet.import_code(
                if_oracle=len(self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)) > 0
            )
        )
        chaincode_list.append(snippet.contract_definition_code())
        # global variable definition
        chaincode_list.append(snippet.StateMemoryDefinition_code(self._generate_parameters_code()))
        # initParams definition
        chaincode_list.append(snippet.InitParametersTypeDefFrame_code(self._generate_instance_initparameters_code()))
        chaincode_list.append(snippet.fix_part_code())
        # chaincode_list.append(snippet.CheckRegisterFunc_code())
        # chaincode_list.append(snippet.RegisterFunc_code())
        chaincode_list.append(snippet.InvokeChaincodeFunc_code())

        # generate InitLedger

        chaincode_list.extend(self._generate_create_instance_code())

        #########
        # Hook Generate: check structure caused hook code to be inserted into the chaincode, prepare code for real generation
        #########

        # find all event based gateways, and set after_all hook to turn off other branches
        for event_based_gateway in self._choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY):
            if len(event_based_gateway.outgoings) > 1:
                for outgoing in event_based_gateway.outgoings:
                    self._hook_codes[outgoing.target.id].setdefault("when_triggered", []).append(
                        # generate some code to turn off other branches
                        self._event_based_gateway_hook_code(event_based_gateway, outgoing.target)
                    )

        # find all parallel to parrallel gateways, and set pre_activate_next hook to check if other branch finished
        for parallel_gateway in self._choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY):
            if len(parallel_gateway.incomings) > 1:
                for incoming in parallel_gateway.incomings:
                    self._hook_codes[incoming.source.id].setdefault("pre_activate_next", []).append(
                        # generate some code to check if other branch finished
                        self._parallel_gateway_merge_hook_code(parallel_gateway, incoming.source)
                    )

        #####
        # Real Generate Code: from start event to end event to create the chaincode for every element
        #####

        for element in self._choreography.nodes:
            if element.type == NodeType.CHOREOGRAPHY_TASK:
                chaincode_list.extend(self._generate_chaincode_for_choreography_task(element))
            if element.type == NodeType.EXCLUSIVE_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_exclusive_gateway(element))
            if element.type == NodeType.PARALLEL_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_parallel_gateway(element))
            if element.type == NodeType.EVENT_BASED_GATEWAY:
                chaincode_list.extend(self._generate_chaincode_for_event_based_gateway(element))
            if element.type == NodeType.START_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_start_event(element))
            if element.type == NodeType.END_EVENT:
                chaincode_list.extend(self._generate_chaincode_for_end_event(element))
            if element.type == NodeType.BUSINESS_RULE_TASK:
                chaincode_list.extend(self._generate_chaincode_for_business_rule(element))
        go_code = "\n\n".join(chaincode_list)

        go_code = tidy_chaincode(go_code)

        if is_output:
            with open(output_path, "w") as f:
                f.write(go_code)

        return go_code

    def _fireflytran_ffi_param(self):
        return {
            "name": "fireFlyTran",
            "schema": {"type": "string"},
        }

    def _instance_id_param(self):
        return {
            "name": "instanceID",
            "schema": {"type": "string"},
        }
    
    def _target_task_id_param(self):
        return {
            "name": "targetTaskID",
            "schema": {"type": "int"},
        }

    def _confirm_target_x509_param(self):
        return {
            "name": "confirmTargetX509",
            "schema": {"type": "string"},
        }

    def _generate_ffi_item(
        self,
        name: str,
        pathname: str = "",
        description: str = "",
        params: list[tuple[str, str]] = [],
        returns: list[str] = None,
    ):
        params = params if params else []
        returns = returns if returns else []
        item = {
            "name": name,
            "pathname": pathname,
            "description": description,
            "params": params,
            "returns": returns,
        }
        return item
    


    def generate_ffi_items_for_choreography_task(self, choreography_task: ChoreographyTask):
        def generate_ffi_for_message(message_flow):
            """为消息流生成 Send 和 Complete 的 FFI 项"""
            items = []
            params = self._get_message_params(message_flow.message)
            params = [{"name": param[0], "schema": {"type": param[1]}} for param in params]

            items.append(
                self._generate_ffi_item(
                    name=message_flow.message.id + "_Send",
                    params=[
                        self._instance_id_param(),
                        self._target_task_id_param(),
                        self._fireflytran_ffi_param(),
                        *params,
                    ],
                )
            )
            items.append(
                self._generate_ffi_item(
                    name=message_flow.message.id + "_Complete",
                    params=[self._instance_id_param(),
                            self._target_task_id_param(),
                            self._confirm_target_x509_param(),
                            ],
                )
            )
            items.append(
                self._generate_ffi_item(
                    name=message_flow.message.id + "_Advance",
                    params=[
                        self._instance_id_param(),
                        self._target_task_id_param(),
                    ]
                )
            )

            return items

        items = []
        init_message_flow = choreography_task.init_message_flow
        return_message_flow = choreography_task.return_message_flow

        if not init_message_flow:
            return items

        items.extend(generate_ffi_for_message(init_message_flow))

        if return_message_flow:
            items.extend(generate_ffi_for_message(return_message_flow))

        return items
    

    def _generate_ffi_items_for_business_rule_task(self, business_rule_task: NodeType.BUSINESS_RULE_TASK) -> list:
        first_name = business_rule_task.id
        continue_method = business_rule_task.id + "_Continue"
        return [
            self._generate_ffi_item(
                name=first_name,
                pathname=first_name,
                description="",
                params=[
                    {
                        "name": "InstanceID",
                        "schema": {"type": "string"},
                    }
                ],
            ),
            self._generate_ffi_item(
                name=continue_method,
                pathname=continue_method,
                description="",
                params=[
                    {
                        "name": "InstanceID",
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "ContentOfDmn",
                        "schema": {"type": "string"},
                    },
                ],
            ),
        ]

    def _generate_ffi_events(self) -> list:
        return [{"name": "DMNContentRequired"}, {"name": "InstanceCreated"}]

    # TODO: Generate FFI For New Type of Chaincode
    def generate_ffi(self, is_output: bool = False, output_path: str = "resource/ffi.json") -> str:
        ffi_items = []

        # Init
        ffi_items.append(
            self._generate_ffi_item(
                name="InitLedger",
                pathname="",
                description="Init the chaincode",
                params=[],
            )
        )
        # Create Instance
        ffi_items.append(
            self._generate_ffi_item(
                name="CreateInstance",
                pathname="",
                description="Create a new instance",
                params=[{"name": "initParametersBytes", "schema": {"type": "string"}}],
            )
        )

        for element in self._choreography.nodes:
            match element.type:
                case NodeType.CHOREOGRAPHY_TASK:
                    ffi_items.extend(self.generate_ffi_items_for_choreography_task(element))
                case NodeType.BUSINESS_RULE_TASK:
                    ffi_items.extend(self._generate_ffi_items_for_business_rule_task(element))
                    pass
                case (
                    NodeType.EXCLUSIVE_GATEWAY
                    | NodeType.PARALLEL_GATEWAY
                    | NodeType.EVENT_BASED_GATEWAY
                    | NodeType.START_EVENT
                    | NodeType.END_EVENT
                ):
                    ffi_items.append(
                        self._generate_ffi_item(
                            name=element.id,
                            params=[
                                self._instance_id_param(),
                            ],
                        )
                    )

        ffi_events = []
        ffi_events.extend(self._generate_ffi_events())

        with open("new_chaincode_snippet/ffiframe.json", "r") as f:
            frame = json.load(f)
        frame["methods"].extend(ffi_items)
        frame["events"].extend(ffi_events)
        if is_output:
            with open(output_path, "w") as f:
                json.dump(frame, f)
        return json.dumps(frame)

    def get_participants(self):
        return {
            participant.id: participant.name
            for participant in self._choreography.query_element_with_type(NodeType.PARTICIPANT)
        }

    def get_messages(self):
        return {
            message.id: {
                "name": message.name,
                "documentation": message.documentation,
            }
            for message in self._choreography.query_element_with_type(NodeType.MESSAGE)
        }

    def get_businessrules(self):
        # return the businessrules and its related properties
        return {
            business_rule.id: {
                "name": business_rule.name,
                "documentation": business_rule.documentation,
            }
            for business_rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
        }


if __name__ == "__main__":
    go_chaincode_translator = GoChaincodeTranslator(
        None,
        bpmn_file="/home/logres/system/muti/bpmn_muti/supplypaper_test2.bpmn",
    )
    # go_chaincode_translator.generate_chaincode(is_output=False)
    go_chaincode_translator.generate_new_chaincode(is_output=True)
    go_chaincode_translator.generate_ffi(is_output=True, output_path="./result/ffi.json")
