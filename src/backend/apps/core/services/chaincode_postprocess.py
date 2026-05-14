import re
import json
from typing import Literal


MessageConfirmationMode = Literal["explicit", "implicit"]


_SEND_FUNC_RE = re.compile(
    r"func \(cc \*SmartContract\) (?P<message_id>Message_[A-Za-z0-9]+)_Send"
    r"\(ctx contractapi\.TransactionContextInterface, instanceID string, fireflyTranID string[^)]*\) error \{\n"
    r"(?P<body>.*?)\n\}",
    re.DOTALL,
)

_COMPLETE_FUNC_RE = re.compile(
    r"func \(cc \*SmartContract\) (?P<message_id>Message_[A-Za-z0-9]+)_Complete"
    r"\(ctx contractapi\.TransactionContextInterface, instanceID string\) error \{\n"
    r"(?P<body>.*?)\n\}",
    re.DOTALL,
)


def _extract_complete_transition_block(complete_body: str) -> str:
    match = re.search(
        r'cc\.ChangeMsgState\(ctx, instance, msg\.MessageID, COMPLETED\)\n'
        r'.*?stub\.SetEvent\([^\n]+\)\n'
        r'.*?cc\.SetInstance\(ctx, instance\)\n'
        r'(?P<block>.*?)\n'
        r'\s*cc\.SetInstance\(ctx, instance\)\n'
        r'\s*return nil',
        complete_body,
        re.DOTALL,
    )
    if not match:
        return ""
    return match.group("block").rstrip()


def _transform_send_to_explicit(message_id: str, send_body: str) -> str:
    return send_body.replace(
        f'cc.ChangeMsgState(ctx, instance, "{message_id}", COMPLETED)',
        f'cc.ChangeMsgState(ctx, instance, "{message_id}", WAITINGFORCONFIRMATION)',
        1,
    )


def _transform_send_to_implicit(message_id: str, send_body: str, transition_block: str) -> str:
    updated = send_body.replace(
        f'cc.ChangeMsgState(ctx, instance, "{message_id}", WAITINGFORCONFIRMATION)',
        f'cc.ChangeMsgState(ctx, instance, "{message_id}", COMPLETED)',
        1,
    )
    updated = updated.replace(
        'stub.SetEvent("%s", []byte("Message is waiting for confirmation"))' % message_id,
        'stub.SetEvent("%s", []byte("Message has been done"))' % message_id,
        1,
    )
    tail_pattern = re.compile(
        r"\tcc\.SetInstance\(ctx, instance\)\n\tcc\.SetInstance\(ctx, instance\)\n\treturn nil"
    )
    replacement = "\tcc.SetInstance(ctx, instance)\n"
    if transition_block:
        replacement += transition_block + "\n"
    replacement += "\tcc.SetInstance(ctx, instance)\n\treturn nil"
    return tail_pattern.sub(replacement, updated, count=1)


def transform_go_message_confirmation(
    chaincode_content: str,
    mode: MessageConfirmationMode = "explicit",
    ffi_content=None,
) -> str:
    if mode not in {"explicit", "implicit"}:
        return chaincode_content

    send_funcs = {m.group("message_id"): m for m in _SEND_FUNC_RE.finditer(chaincode_content)}
    complete_funcs = {
        m.group("message_id"): m for m in _COMPLETE_FUNC_RE.finditer(chaincode_content)
    }
    if not send_funcs or not complete_funcs:
        return chaincode_content

    updated_content = chaincode_content
    for message_id, send_match in send_funcs.items():
        complete_match = complete_funcs.get(message_id)
        if not complete_match:
            continue
        original_send = send_match.group(0)
        send_body = send_match.group("body")
        complete_body = complete_match.group("body")
        transition_block = _extract_complete_transition_block(complete_body)

        if mode == "explicit":
            transformed_body = _transform_send_to_explicit(message_id, send_body)
        else:
            transformed_body = _transform_send_to_implicit(
                message_id,
                send_body,
                transition_block,
            )

        transformed_send = original_send.replace(send_body, transformed_body, 1)
        updated_content = updated_content.replace(original_send, transformed_send, 1)

    return inject_message_payload_bindings(updated_content, ffi_content)


def _load_ffi_methods(ffi_content) -> list[dict]:
    if not ffi_content:
        return []
    if isinstance(ffi_content, str):
        try:
            ffi_content = json.loads(ffi_content)
        except Exception:
            return []
    if not isinstance(ffi_content, dict):
        return []
    methods = ffi_content.get("methods") or []
    return methods if isinstance(methods, list) else []


def _go_type(schema: dict) -> str:
    raw_type = str((schema or {}).get("type") or "").lower()
    if raw_type in {"number", "integer", "int"}:
        return "int"
    if raw_type in {"boolean", "bool"}:
        return "bool"
    if raw_type in {"float", "double"}:
        return "float64"
    return "string"


def _public_name(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _message_payload_params_from_ffi(ffi_content) -> dict[str, list[dict]]:
    payload_params: dict[str, list[dict]] = {}
    for method in _load_ffi_methods(ffi_content):
        method_name = str(method.get("name") or "")
        if not method_name.startswith("Message_") or not method_name.endswith("_Send"):
            continue
        message_id = method_name[:-5]
        params = []
        for param in method.get("params") or []:
            name = str(param.get("name") or "")
            if name in {"InstanceID", "instanceID", "instanceId", "FireFlyTran", "fireflyTranID"}:
                continue
            params.append({"name": name, "type": _go_type(param.get("schema") or {})})
        if params:
            payload_params[message_id] = params
    return payload_params


def inject_message_payload_bindings(chaincode_content: str, ffi_content=None) -> str:
    payload_params = _message_payload_params_from_ffi(ffi_content)
    if not payload_params:
        return chaincode_content

    updated_content = chaincode_content
    for message_id, params in payload_params.items():
        signature = (
            f"func (cc *SmartContract) {message_id}_Send"
            "(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string)"
        )
        if signature not in updated_content:
            continue
        param_suffix = "".join(f", {param['name']} {param['type']}" for param in params)
        updated_signature = signature[:-1] + param_suffix + ")"
        updated_content = updated_content.replace(signature, updated_signature, 1)

        state_change_pattern = re.compile(
            rf'(?P<line>\tcc\.ChangeMsgState\(ctx, instance, "{re.escape(message_id)}", (?:COMPLETED|WAITINGFORCONFIRMATION)\)\n)'
        )
        assignments = "\n".join(
            f"\tglobalMemory.{_public_name(param['name'])} = {param['name']}"
            for param in params
        )
        binding_block = (
            "\n\tglobalMemory, readGlobalError := cc.ReadGlobalVariable(ctx, instanceID)\n"
            "\tif readGlobalError != nil {\n"
            "\t\tfmt.Println(readGlobalError.Error())\n"
            "\t\treturn readGlobalError\n"
            "\t}\n"
            f"{assignments}\n"
            "\tsetGlobalError := cc.SetGlobalVariable(ctx, instance, globalMemory)\n"
            "\tif setGlobalError != nil {\n"
            "\t\tfmt.Println(setGlobalError.Error())\n"
            "\t\treturn setGlobalError\n"
            "\t}\n"
        )

        def replace_state_change(match: re.Match) -> str:
            following = updated_content[match.end() : match.end() + 120]
            if "ReadGlobalVariable" in following:
                return match.group("line")
            return match.group("line") + binding_block

        updated_content = state_change_pattern.sub(replace_state_change, updated_content, count=1)
    return updated_content
