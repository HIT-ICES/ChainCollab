"""Prepare off-chain message data without changing or invoking the contract."""
import json
from xml.etree import ElementTree as ET

import requests


def read_message_schema(node):
    schema_node = next((n for n in node.iter() if n.tag.split("}")[-1] == "MessageSchema"), None)
    if schema_node is not None:
        files, required = {}, []
        for field in schema_node:
            if field.tag.split("}")[-1] == "File" and field.get("name"):
                name = field.get("name")
                files[name] = dict(field.attrib)
                if field.get("required", "false").lower() in ("true", "1", "yes"):
                    required.append(name)
        return {"files": files, "file required": required}
    documentation = next((n.text for n in node if n.tag.split("}")[-1] == "documentation"), "{}")
    schema = json.loads(documentation or "{}")
    schema = schema.get("schema", schema)
    return json.loads(schema) if isinstance(schema, str) else schema


def prepare_ethereum_message(instance, message_id, values, uploads, identity_lookup):
    bpmn = instance.bpmn
    if not bpmn.eth_environment_id or not bpmn.firefly_url:
        raise ValueError("Ethereum execution API is not configured")
    root = ET.fromstring(bpmn.bpmnContent)
    node = next((n for n in root.iter() if n.get("id") == message_id and n.tag.split("}")[-1] == "message"), None)
    if node is None:
        raise ValueError("Unknown BPMN message")
    schema = read_message_schema(node)
    file_fields = schema.get("files") or {}
    if not file_fields:
        raise ValueError("Message has no file fields")
    if set(uploads) - set(file_fields):
        raise ValueError("Unknown message file field")
    for name in schema.get("file required") or []:
        if name not in uploads:
            raise ValueError(f"File {name} is required")
    flow = next((n for n in root.iter() if n.tag.split("}")[-1] == "messageFlow" and n.get("messageRef") == message_id), None)
    if flow is None:
        raise ValueError("Message receiver is not configured")
    binding = (instance.execution_bindings or {}).get("participants", {}).get(flow.get("targetRef"), {})
    identity = identity_lookup(binding, bpmn.eth_environment_id)
    if not identity or not identity.firefly_identity_id:
        raise ValueError("Receiver has no bound FireFly identity")
    # Use the registered API's node and namespace; never accept a URL from the request.
    namespace_url = bpmn.firefly_url.split("/apis/", 1)[0].rstrip("/")

    def request(method, path, **kwargs):
        response = requests.request(method, f"{namespace_url}/{path}", timeout=120, **kwargs)
        if not response.ok:
            raise ValueError(f"FireFly request failed ({response.status_code}): {response.text[:300]}")
        return response.json()

    receiver = request("GET", f"identities/{identity.firefly_identity_id}")
    if not receiver.get("did"):
        raise ValueError("Receiver FireFly DID is unavailable")
    file_ids = {}
    for name, upload in uploads.items():
        data = request("POST", "data", data={"autometa": "true"},
                       files={"file": (upload.name, upload, upload.content_type or "application/octet-stream")})
        if not data.get("id"):
            raise ValueError("FireFly upload did not return a data ID")
        file_ids[name] = data["id"]
    file_names = {name.lower() for name in file_fields}
    business_values = {key: value for key, value in values.items()
                       if key.lower() != "instanceid" and "fireflytran" not in key.lower() and key.lower() not in file_names}
    business_values.update(file_ids)
    message = request("POST", "messages/private", json={
        "data": [{"value": business_values}] + [{"id": data_id} for data_id in file_ids.values()],
        "group": {"members": [{"identity": receiver["did"]}]},
        "header": {"tag": "private", "topics": [f"{bpmn.name}_{message_id}"]},
    })
    message_id = message.get("header", {}).get("id")
    if not message_id:
        raise ValueError("FireFly did not return a message ID")
    return {"messageId": message_id, "fileIds": file_ids}
