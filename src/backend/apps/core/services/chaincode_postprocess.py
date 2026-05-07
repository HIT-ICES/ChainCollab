import re
from typing import Literal


MessageConfirmationMode = Literal["explicit", "implicit"]


_SEND_FUNC_RE = re.compile(
    r"func \(cc \*SmartContract\) (?P<message_id>Message_[A-Za-z0-9]+)_Send"
    r"\(ctx contractapi\.TransactionContextInterface, instanceID string, fireflyTranID string\) error \{\n"
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

    return updated_content
