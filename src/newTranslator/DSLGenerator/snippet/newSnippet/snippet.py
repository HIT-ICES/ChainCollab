from pathlib import Path
import json


# 载入 DSL 模板库
SNIPPET_JSON = Path(__file__).resolve().with_name("snippet.json")
with SNIPPET_JSON.open("r", encoding="utf8") as f:
    DSL = json.load(f)


def _render(template: str, **params) -> str:
    keys = sorted(params.keys(), key=len, reverse=True)
    tokens = {}
    result = template
    for key in keys:
        placeholder = f"{{{key}}}"
        token = f"__DSL_TOKEN_{key.upper()}__"
        tokens[key] = token
        result = result.replace(placeholder, token)
    result = result.replace("{", "{{").replace("}", "}}")
    for key in keys:
        result = result.replace(tokens[key], f"{{{key}}}")
    return result.format(**params)


def DSL_ContractFrame(contract_name: str, participants: str, globals_: str,
                       messages: str, gateways: str, events: str,
                       businessrules: str, flows: str) -> str:
    return _render(
        DSL["DSLContractFrame"],
        contract_name=contract_name,
        participants=participants,
        globals=globals_,
        messages=messages,
        gateways=gateways,
        events=events,
        businessrules=businessrules,
        flows=flows,
    )


# ========== Participants ==========

def DSL_ParticipantsFrame(items: str) -> str:
    return _render(DSL["DSLParticipantsFrame"], items=items)


def DSL_ParticipantItem(pid: str, msp: str, x509: str, is_multi: bool,
                         multi_min: int, multi_max: int, attributes: str) -> str:
    return _render(
        DSL["DSLParticipantItem"],
        id=pid,
        msp=msp,
        x509=x509,
        is_multi=str(is_multi).lower(),
        multi_min=multi_min,
        multi_max=multi_max,
        attributes=attributes,
    )


def DSL_ParticipantAttributeItem(key: str, value: str) -> str:
    return _render(DSL["DSLParticipantAttributeItem"], key=key, value=value)


# ========== Globals ==========

def DSL_GlobalsFrame(items: str) -> str:
    return _render(DSL["DSLGlobalsFrame"], items=items)


def DSL_GlobalItem(name: str, type_: str) -> str:
    return _render(DSL["DSLGlobalItem"], name=name, type=type_)


# ========== Messages ==========

def DSL_MessagesFrame(items: str) -> str:
    return _render(DSL["DSLMessagesFrame"], items=items)


def DSL_MessageItem(id: str, sender: str, receiver: str, state: str, schema: str) -> str:
    return _render(
        DSL["DSLMessageItem"],
        id=id,
        sender=sender,
        receiver=receiver,
        state=state,
        schema=schema,
    )


# ========== Gateways ==========

def DSL_GatewaysFrame(items: str) -> str:
    return _render(DSL["DSLGatewaysFrame"], items=items)


def DSL_GatewayItem(id: str, type_: str, state: str) -> str:
    return _render(DSL["DSLGatewayItem"], id=id, type=type_, state=state)


# ========== Events ==========

def DSL_EventsFrame(items: str) -> str:
    return _render(DSL["DSLEventsFrame"], items=items)


def DSL_EventItem(id: str, state: str) -> str:
    return _render(DSL["DSLEventItem"], id=id, state=state)


# ========== Business Rules ==========

def DSL_BusinessRulesFrame(items: str) -> str:
    return _render(DSL["DSLBusinessRulesFrame"], items=items)


def DSL_BusinessRuleItem(id: str, dmn: str, decision: str,
                         input_map: str, output_map: str, state: str) -> str:

    # output block optional
    output_block = ""
    if output_map.strip():
        output_block = _render(
            DSL["DSLBusinessRuleOutputBlockFrame"],
            output_mappings=output_map,
        )

    return _render(
        DSL["DSLBusinessRuleItem"],
        id=id,
        dmn=dmn,
        decision=decision,
        input_mappings=input_map,
        output_block=output_block,
        state=state,
    )


def DSL_BusinessRuleInputMappingItem(param: str, global_var: str) -> str:
    return _render(
        DSL["DSLBusinessRuleInputMappingItem"],
        dmn_param=param,
        global_name=global_var,
    )


def DSL_BusinessRuleOutputMappingItem(param: str, global_var: str) -> str:
    return _render(
        DSL["DSLBusinessRuleOutputMappingItem"],
        dmn_param=param,
        global_name=global_var,
    )


# ========== Flows ==========

def DSL_FlowsFrame(items: str) -> str:
    return _render(DSL["DSLFlowsFrame"], items=items)


def DSL_StartEventEnables(event: str, target: str) -> str:
    return _render(DSL["DSLStartEventEnables"], event=event, target=target)


def DSL_WhenMessageSentEnable(message: str, targets: str) -> str:
    return _render(
        DSL["DSLWhenMessageSentEnable"],
        message=message,
        targets=targets,
    )


def DSL_WhenMessageSentDisableEnable(message: str, disabled: str, enabled: str) -> str:
    return _render(
        DSL["DSLWhenMessageSentDisableEnable"],
        message=message,
        disabled=disabled,
        enabled=enabled,
    )


def DSL_WhenGatewayCompletedEnable(gateway: str, targets: str) -> str:
    return _render(
        DSL["DSLWhenGatewayCompletedEnable"],
        gateway=gateway,
        targets=targets,
    )


def DSL_WhenBusinessRuleDoneEnable(rule: str, targets: str) -> str:
    return _render(
        DSL["DSLWhenBusinessRuleDoneEnable"],
        rule=rule,
        targets=targets,
    )


def DSL_WhenEventCompletedSetGlobal(event: str, global_name: str, value: str) -> str:
    return _render(
        DSL["DSLWhenEventCompletedSetGlobal"],
        event=event,
        global_name=global_name,
        value=value,
    )


# ========== Utilities ==========

def DSL_EmptyLine() -> str:
    return DSL["DSLEmptyLine"]


def MapElementState(old_state: str) -> str:
    """
    将链码的状态映射为 DSL 状态：
    DISABLED -> INACTIVE
    ENABLED -> READY
    WAITINGFORCONFIRMATION -> PENDING_CONFIRMATION
    COMPLETED -> DONE
    """
    mapping = DSL["ElementStateMapping"]
    return mapping[old_state]
