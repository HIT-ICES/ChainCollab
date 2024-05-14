import json

with open("chaincode_snippet/snippet.json", "r") as f:
    content = json.load(f)


def import_code():
    return content["import"]


def contract_definition_code():
    return content["contract_definition"]


def fix_part_code():
    return content["fix_part"]


def package_code():
    return content["package"]


def state_read_and_put_code():
    return content["StateReadAndSetFunc"]

def globale_variable_read_and_set_code():
    return content["ReadAndSetGloablVariable"]


def InitLedger_code(
    start_event: str, end_event: str, messages: list[dict[str, str]], gateways: list
):
    def InitStartEvent(event: str) -> str:
        return content["InitStart"].format(event)

    def InitEndEvent(event: str) -> str:
        return content["InitEnd"].format(event)

    def InitMessage(message: str, sender: str, receiver: str, properties) -> str:
        return content["InitMessage"].format(message, sender, receiver, properties)

    def InitGateway(gateway: str) -> str:
        return content["InitGateway"].format(gateway)

    return content["InitFuncFrame"].format(
        "\n".join(
            [InitStartEvent(start_event), InitEndEvent(end_event)]
            + [
                InitMessage(
                    message=message["name"],
                    sender=message["sender"],
                    receiver=message["receiver"],
                    properties=message["properties"],
                )
                for message in messages
            ]
            + [InitGateway(gateway) for gateway in gateways]
        ),
    )


def ChangeEventState_code(event, state: str):
    return content["ChangeEventState"].format(event=event, state=state)


def ChangeMsgState_code(msg, state: str):
    return content["ChangeMsgState"].format(message=msg, state=state)


def ChangeGtwState_code(gtw, state: str):
    return content["ChangeGtwState"].format(gateway=gtw, state=state)


def StartEvent_code(
    event,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["StartEventFuncFrame"].format(
        event=event,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


def EndEvent_code(event, after_all_hook: str = ""):
    return content["EndEventFuncFrame"].format(
        event=event,
        after_all_hook=after_all_hook,
    )


def MessageSend_code(
    message,
    after_all_hook: str = "",
    more_parameters: str = "",
    put_more_parameters: str = "",
):
    return content["MessageSendFuncFrame"].format(
        message=message,
        after_all_hook=after_all_hook,
        more_parameters=more_parameters,
        put_more_parameters=put_more_parameters,
    )


def MessageComplete_code(
    message,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["MessageCompleteFuncFrame"].format(
        message=message,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


# TODO
def ExclusiveGateway_split_code(
    gateway,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["ExclusiveGatewaySplitFuncFrame"].format(
        exclusive_gateway=gateway,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


def ExclusiveGateway_merge_code(
    gateway,
    change_next_state_code,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["ExclusiveGatewayMergeFuncFrame"].format(
        exclusive_gateway=gateway,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


def ParallelGateway_split_code(
    gateway,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["ParallelGatewaySplitFuncFrame"].format(
        parallel_gateway=gateway,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


def ParallelGateway_merge_code(
    gateway,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["ParallelGatewayMergeFuncFrame"].format(
        parallel_gateway=gateway,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


def EventBasedGateway_code(
    gateway,
    change_next_state_code: str,
    pre_activate_next_hook: str = "",
    after_all_hook: str = "",
):
    return content["EventBasedGatewayFuncFrame"].format(
        event_based_gateway=gateway,
        change_next_state_code=change_next_state_code,
        pre_activate_next_hook=pre_activate_next_hook,
        after_all_hook=after_all_hook,
    )


## Conditions
##----------------


def CheckMessageState_code(message, state: str):
    return content["CheckMessageState"].format(state=state, message=message)


def CheckGatewayState_code(gateway, state: str):
    return content["CheckGtwState"].format(state=state, gateway=gateway)


def CheckEventState_code(event, state: str):
    return content["CheckEventState"].format(state=state, event=event)


##----------------


## Combine Conditions
##----------------
def CombineConditions_All_True_code(conditions: list[str]):
    return "&&".join(conditions)


def CombineConditions_Any_False_code(conditions: list[str]):
    return "||".join([f"!({condition})" for condition in conditions])


def CombineConditions_Any_True_code(conditions: list[str]):
    return "||".join(conditions)


def CombineConditions_All_False_code(conditions: list[str]):
    return "&&".join([f"!({condition})" for condition in conditions])


##----------------

## Condition Behaviour
##----------------


def ConditionToDo_code(condition: str, todo: str):
    return content["ConditionToDo"].format(condition=condition, todo=todo)


def ConditionToHalt_code(condition: str):
    return ConditionToDo_code(condition, "return nil")


##----------------


def StateMemoryDefinition_code(fields: str):
    return content["StateMemoryDefinitionFrame"].format(fields)


def StateMemoryParameterDefinition_code(name: str, type: str):
    # <name> bool `json:"<name>"`
    return '{name} {type} `json:"{name}"`'.format(name=name, type=type)


# deprecated
def PutState_code(name: str, value: str):
    return content["PutStateFuncFrame"].format(name=name, value=value)


def SetGlobalVariable_code(name: str, value: str):
    return content["SetGlobalVariableFuncFrame"].format(name=name, value=value)


def ReadState_code(name: str):
    return content["ReadStateFuncFrame"].format(stateName=name)


def ReadCurrentMemory_code():
    return content["ReadCurrentMemoryCode"]
