#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from common import EXP3_ROOT, dump_json, dump_text, load_json


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = "0x" + ("0" * 64)
DEFAULT_DMN_EVAL_URL = "http://cdmn-node1:5000/api/dmn/evaluate"


@dataclass
class StepRecord:
    element_type: str
    element_id: str
    method: str
    signer: str
    payload: Dict[str, Any]
    response: Dict[str, Any]
    snapshot_after: Dict[str, Any]


class ReplayError(RuntimeError):
    pass


class ChainCollabClient:
    def __init__(self, backend_base: str, token: str, timeout: int = 120) -> None:
        self.backend_base = backend_base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.backend_base}{path}"

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self.session.get(self._url(path), params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path: str, payload: Dict[str, Any]) -> Any:
        resp = self.session.post(self._url(path), data=json.dumps(payload), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def put_json(self, path: str, payload: Dict[str, Any]) -> Any:
        resp = self.session.put(self._url(path), data=json.dumps(payload), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def patch_json(self, path: str, payload: Dict[str, Any]) -> Any:
        resp = self.session.patch(self._url(path), data=json.dumps(payload), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


class FireFlyClient:
    def __init__(self, timeout: int = 180) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def post_json(self, url: str, payload: Dict[str, Any]) -> Any:
        resp = self.session.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_json(self, url: str) -> Any:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, url: str, filename: str, content: str, content_type: str = "application/xml") -> Any:
        resp = self.session.post(
            url,
            files={"file": (filename, content.encode("utf-8"), content_type)},
            data={"autometa": "true"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


def local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_bpmn_execution_meta(bpmn_content: str) -> Dict[str, Any]:
    ns = {"bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    root = ET.fromstring(bpmn_content)
    meta = {
        "messages": {},
        "gateways": {},
        "events": {},
        "businessRules": {},
    }
    for node in root.iter():
        node_id = node.attrib.get("id", "")
        if not node_id:
            continue
        name = node.attrib.get("name", node_id)
        doc_text = ""
        for child in list(node):
            if local_name(child.tag) == "documentation":
                doc_text = (child.text or "").strip()
                break
        parsed_doc = None
        if doc_text:
            try:
                parsed_doc = json.loads(doc_text)
            except Exception:
                parsed_doc = None
        entry = {
            "id": node_id,
            "name": name,
            "documentation": doc_text,
            "parsedDoc": parsed_doc,
            "type": local_name(node.tag),
        }
        if node_id.startswith("Message_"):
            entry["format"] = parsed_doc
            meta["messages"][node_id] = entry
        elif node_id.startswith("Gateway_") or node_id.startswith("ExclusiveGateway_") or node_id.startswith("EventBasedGateway_"):
            meta["gateways"][node_id] = entry
        elif node_id.startswith("Event_") or node_id.startswith("StartEvent_") or node_id.startswith("EndEvent_") or node_id.startswith("Intermediate"):
            meta["events"][node_id] = entry
        elif node_id.startswith("Activity_") and local_name(node.tag) == "businessRuleTask":
            entry["inputs"] = parsed_doc.get("inputs", []) if isinstance(parsed_doc, dict) else []
            entry["outputs"] = parsed_doc.get("outputs", []) if isinstance(parsed_doc, dict) else []
            meta["businessRules"][node_id] = entry
    return meta


def get_enum_ids(abi: List[Dict[str, Any]], execution_layout: Dict[str, Any]) -> Dict[str, List[str]]:
    def layout_ids(key: str) -> List[str]:
        raw = execution_layout.get(key) or []
        ids = []
        for item in raw:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return ids

    message_ids = layout_ids("messages")
    gateway_ids = layout_ids("gateways")
    event_ids = layout_ids("events")
    business_rule_ids = layout_ids("businessRules")

    if not message_ids:
        message_ids = [item["name"][:-5] for item in abi if item.get("name", "").startswith("Message_") and item.get("name", "").endswith("_Send")]
    if not gateway_ids:
        gateway_ids = [item["name"] for item in abi if item.get("name", "").startswith("Gateway_") or item.get("name", "").startswith("ExclusiveGateway_") or item.get("name", "").startswith("EventBasedGateway_")]
    if not event_ids:
        event_ids = [item["name"] for item in abi if item.get("name", "").startswith("Event_") or item.get("name", "").startswith("StartEvent_") or item.get("name", "").startswith("EndEvent_")]
    if not business_rule_ids:
        business_rule_ids = [item["name"] for item in abi if item.get("name", "").startswith("Activity_") and not item.get("name", "").endswith("_Continue")]

    return {
        "messageIds": message_ids,
        "gatewayIds": gateway_ids,
        "eventIds": event_ids,
        "businessRuleIds": business_rule_ids,
    }


def extract_snapshot_output(payload: Dict[str, Any]) -> Dict[str, List[Any]]:
    output = payload.get("output") or payload.get("data", {}).get("output") or payload.get("data") or payload
    return {
        "messageStates": list(output.get("messageStates") or output.get("MessageStates") or output.get("ret0") or []),
        "messageFireflyTranIds": list(output.get("messageFireflyTranIds") or output.get("MessageFireflyTranIds") or output.get("ret1") or []),
        "gatewayStates": list(output.get("gatewayStates") or output.get("GatewayStates") or output.get("ret2") or []),
        "eventStates": list(output.get("eventStates") or output.get("EventStates") or output.get("ret3") or []),
        "businessRuleStates": list(output.get("businessRuleStates") or output.get("BusinessRuleStates") or output.get("ret4") or []),
        "businessRuleRequestIds": list(output.get("businessRuleRequestIds") or output.get("BusinessRuleRequestIds") or output.get("ret5") or []),
    }


def to_state(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        try:
            return int(value)
        except Exception:
            return 0
    return 0


def build_execution_elements(
    abi: List[Dict[str, Any]],
    snapshot: Dict[str, List[Any]],
    meta: Dict[str, Any],
    execution_layout: Dict[str, Any],
) -> List[Dict[str, Any]]:
    enum_ids = get_enum_ids(abi, execution_layout)
    elements: List[Dict[str, Any]] = []
    for idx, item_id in enumerate(enum_ids["messageIds"]):
        elements.append(
            {
                "type": "message",
                "MessageID": item_id,
                "DisplayName": meta["messages"].get(item_id, {}).get("name", item_id),
                "Format": meta["messages"].get(item_id, {}).get("format"),
                "state": to_state(snapshot["messageStates"][idx] if idx < len(snapshot["messageStates"]) else 0),
                "FireflyTranID": str(snapshot["messageFireflyTranIds"][idx] if idx < len(snapshot["messageFireflyTranIds"]) else ""),
            }
        )
    for idx, item_id in enumerate(enum_ids["eventIds"]):
        elements.append(
            {
                "type": "event",
                "EventID": item_id,
                "DisplayName": meta["events"].get(item_id, {}).get("name", item_id),
                "state": to_state(snapshot["eventStates"][idx] if idx < len(snapshot["eventStates"]) else 0),
            }
        )
    for idx, item_id in enumerate(enum_ids["gatewayIds"]):
        elements.append(
            {
                "type": "gateway",
                "GatewayID": item_id,
                "DisplayName": meta["gateways"].get(item_id, {}).get("name", item_id),
                "state": to_state(snapshot["gatewayStates"][idx] if idx < len(snapshot["gatewayStates"]) else 0),
            }
        )
    for idx, item_id in enumerate(enum_ids["businessRuleIds"]):
        elements.append(
            {
                "type": "businessRule",
                "BusinessRuleID": item_id,
                "DisplayName": meta["businessRules"].get(item_id, {}).get("name", item_id),
                "state": to_state(snapshot["businessRuleStates"][idx] if idx < len(snapshot["businessRuleStates"]) else 0),
                "RequestID": str(snapshot["businessRuleRequestIds"][idx] if idx < len(snapshot["businessRuleRequestIds"]) else ""),
            }
        )
    return elements


def find_actionable(
    abi: List[Dict[str, Any]],
    snapshot: Dict[str, List[Any]],
    meta: Dict[str, Any],
    execution_layout: Dict[str, Any],
    methods_by_name: Dict[str, Dict[str, Any]],
    action_overrides: Dict[str, Dict[str, Any]],
    instance_id: int,
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    elements = build_execution_elements(abi, snapshot, meta, execution_layout)
    actionable: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for element in elements:
        config_item = get_action_config(element, instance_id, methods_by_name, action_overrides)
        if not config_item:
            continue
        method_def = config_item["methodDef"] or {}
        defaults = build_action_defaults(method_def, instance_id, element)
        merged_payload = {**defaults, **config_item["payload"]}
        config_item["payload"] = merged_payload
        actionable.append((element, config_item))
    return actionable


def canonical_step_type(raw: str) -> str:
    lowered = str(raw or "").strip().lower()
    mapping = {
        "message": "message",
        "gateway": "gateway",
        "event": "event",
        "businessrule": "businessRule",
        "business_rule": "businessRule",
    }
    if lowered not in mapping:
        raise ReplayError(f"Unsupported execution step type: {raw}")
    return mapping[lowered]


def element_matches_step(element: Dict[str, Any], step_type: str, step_element: str) -> bool:
    canonical = canonical_step_type(step_type)
    if element.get("type") != canonical:
        return False
    return get_element_id(element) == str(step_element)


def merge_payload_overrides(
    element_id: str,
    base_payload: Dict[str, Any],
    step_payload: Optional[Dict[str, Any]],
    action_overrides: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    merged = dict(base_payload)
    merged.update(action_overrides.get(element_id, {}))
    if step_payload:
        merged.update(step_payload)
    return merged


def find_target_action(
    abi: List[Dict[str, Any]],
    snapshot: Dict[str, List[Any]],
    meta: Dict[str, Any],
    execution_layout: Dict[str, Any],
    methods_by_name: Dict[str, Dict[str, Any]],
    action_overrides: Dict[str, Dict[str, Any]],
    instance_id: int,
    step_type: str,
    step_element: str,
    step_payload: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    elements = build_execution_elements(abi, snapshot, meta, execution_layout)
    for element in elements:
        if not element_matches_step(element, step_type, step_element):
            continue
        config_item = get_action_config(element, instance_id, methods_by_name, action_overrides)
        if not config_item:
            return None
        method_def = config_item["methodDef"] or {}
        defaults = build_action_defaults(method_def, instance_id, element)
        config_item["payload"] = merge_payload_overrides(
            get_element_id(element),
            {**defaults, **config_item["payload"]},
            step_payload,
            action_overrides,
        )
        return element, config_item
    return None


def wait_for_target_action(
    firefly: FireFlyClient,
    contract_base_url: str,
    abi: List[Dict[str, Any]],
    meta: Dict[str, Any],
    execution_layout: Dict[str, Any],
    methods_by_name: Dict[str, Dict[str, Any]],
    action_overrides: Dict[str, Dict[str, Any]],
    instance_id: int,
    step_type: str,
    step_element: str,
    step_payload: Optional[Dict[str, Any]],
    attempts: int,
    interval_sec: float,
) -> Tuple[Optional[Tuple[Dict[str, Any], Dict[str, Any]]], Dict[str, List[Any]], List[Dict[str, Any]]]:
    history: List[Dict[str, Any]] = []
    for _ in range(attempts):
        snapshot = extract_snapshot_output(
            firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": instance_id}},
            )
        )
        history.append(snapshot)
        action = find_target_action(
            abi,
            snapshot,
            meta,
            execution_layout,
            methods_by_name,
            action_overrides,
            instance_id,
            step_type,
            step_element,
            step_payload,
        )
        if action:
            return action, snapshot, history
        if is_final_success(snapshot):
            return None, snapshot, history
        time.sleep(interval_sec)
    return None, history[-1] if history else {}, history


def wait_for_business_rule_continue(
    firefly: FireFlyClient,
    contract_base_url: str,
    abi: List[Dict[str, Any]],
    meta: Dict[str, Any],
    execution_layout: Dict[str, Any],
    methods_by_name: Dict[str, Dict[str, Any]],
    action_overrides: Dict[str, Dict[str, Any]],
    instance_id: int,
    step_element: str,
    continue_payload: Optional[Dict[str, Any]],
    attempts: int,
    interval_sec: float,
) -> Tuple[Optional[Tuple[Dict[str, Any], Dict[str, Any]]], Dict[str, List[Any]], List[Dict[str, Any]]]:
    history: List[Dict[str, Any]] = []
    for _ in range(attempts):
        snapshot = extract_snapshot_output(
            firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": instance_id}},
            )
        )
        history.append(snapshot)
        action = find_target_action(
            abi,
            snapshot,
            meta,
            execution_layout,
            methods_by_name,
            action_overrides,
            instance_id,
            "businessrule",
            step_element,
            continue_payload,
        )
        if action and str(action[1]["method"]).endswith("_Continue"):
            return action, snapshot, history
        if is_final_success(snapshot):
            return None, snapshot, history
        time.sleep(interval_sec)
    return None, history[-1] if history else {}, history


def infer_param_type(param: Dict[str, Any]) -> str:
    raw = str(
        (((param.get("schema") or {}).get("details") or {}).get("type"))
        or (param.get("schema") or {}).get("type")
        or param.get("type")
        or param.get("internalType")
        or ""
    ).lower()
    if "bool" in raw:
        return "boolean"
    if "int" in raw:
        return "number"
    return "string"


def get_element_id(element: Dict[str, Any]) -> str:
    return str(
        element.get("EventID")
        or element.get("GatewayID")
        or element.get("MessageID")
        or element.get("BusinessRuleID")
        or ""
    )


def get_snapshot_element_state(
    snapshot: Dict[str, List[Any]],
    execution_layout: Dict[str, Any],
    abi: List[Dict[str, Any]],
    element_type: str,
    element_id: str,
) -> int:
    enum_ids = get_enum_ids(abi, execution_layout)
    state_key_by_type = {
        "message": ("messageIds", "messageStates"),
        "event": ("eventIds", "eventStates"),
        "gateway": ("gatewayIds", "gatewayStates"),
        "businessRule": ("businessRuleIds", "businessRuleStates"),
    }
    id_key, state_key = state_key_by_type[element_type]
    ids = enum_ids[id_key]
    if element_id not in ids:
        return 0
    idx = ids.index(element_id)
    states = snapshot.get(state_key) or []
    if idx >= len(states):
        return 0
    return to_state(states[idx])


def wait_for_element_completed_snapshot(
    firefly: FireFlyClient,
    contract_base_url: str,
    abi: List[Dict[str, Any]],
    execution_layout: Dict[str, Any],
    instance_id: int,
    element_type: str,
    element_id: str,
    attempts: int,
    interval_sec: float,
    target_state: int = 3,
) -> Tuple[Dict[str, List[Any]], List[Dict[str, Any]]]:
    history: List[Dict[str, Any]] = []
    latest: Dict[str, List[Any]] = {}
    for _ in range(max(1, attempts)):
        latest = extract_snapshot_output(
            firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": instance_id}},
            )
        )
        history.append(latest)
        if get_snapshot_element_state(latest, execution_layout, abi, element_type, element_id) == target_state:
            return latest, history
        time.sleep(interval_sec)
    return latest, history


def get_default_value(param: Dict[str, Any], instance_id: int, element: Optional[Dict[str, Any]] = None) -> Any:
    name = str(param.get("name") or "")
    lower_name = name.lower()
    if name in ("instanceId", "InstanceID"):
        return int(instance_id)
    if "fireflytran" in lower_name:
        return f"ff-{instance_id}-{get_element_id(element or {}) or 'action'}"
    kind = infer_param_type(param)
    if kind == "boolean":
        return False
    if kind == "number":
        return 1
    if lower_name.endswith("id") or "requestid" in lower_name:
        return f"{get_element_id(element or {}) or 'item'}-{instance_id}"
    return f"sample-{name or 'value'}"


def build_method_payload(method_def: Optional[Dict[str, Any]], instance_id: int, element: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for param in method_def.get("params", []) if method_def else []:
        name = param.get("name")
        if not name:
            continue
        payload[name] = get_default_value(param, instance_id, element)
    return payload


def build_action_defaults(method_def: Optional[Dict[str, Any]], instance_id: int, element: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {}
    for param in method_def.get("params", []) if method_def else []:
        name = param.get("name")
        if not name or name in ("instanceId", "InstanceID"):
            continue
        defaults[name] = get_default_value(param, instance_id, element)
    return defaults


def get_action_config(
    element: Dict[str, Any],
    instance_id: int,
    methods_by_name: Dict[str, Dict[str, Any]],
    overrides: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    has_request_id = (
        isinstance(element.get("RequestID"), str)
        and element["RequestID"] not in ("", "0x", ZERO_BYTES32)
    )
    if element["type"] == "message" and element["state"] == 1:
        method_name = f"{element['MessageID']}_Send"
        method_def = methods_by_name.get(method_name)
        payload = build_method_payload(method_def, instance_id, element)
        payload.update(overrides.get(element["MessageID"], {}))
        return {"method": method_name, "payload": payload, "label": "Send", "methodDef": method_def}
    if element["type"] == "gateway" and element["state"] == 1:
        method_name = element["GatewayID"]
        method_def = methods_by_name.get(method_name)
        payload = build_method_payload(method_def, instance_id, element)
        payload.update(overrides.get(element["GatewayID"], {}))
        return {"method": method_name, "payload": payload, "label": "Execute", "methodDef": method_def}
    if element["type"] == "event" and element["state"] == 1:
        method_name = element["EventID"]
        method_def = methods_by_name.get(method_name)
        payload = build_method_payload(method_def, instance_id, element)
        payload.update(overrides.get(element["EventID"], {}))
        return {"method": method_name, "payload": payload, "label": "Execute", "methodDef": method_def}
    if element["type"] == "businessRule" and element["state"] == 1:
        method_name = element["BusinessRuleID"]
        method_def = methods_by_name.get(method_name)
        payload = build_method_payload(method_def, instance_id, element)
        payload.update(overrides.get(element["BusinessRuleID"], {}))
        return {"method": method_name, "payload": payload, "label": "Request DMN", "methodDef": method_def}
    if element["type"] == "businessRule" and element["state"] == 2 and has_request_id:
        method_name = f"{element['BusinessRuleID']}_Continue"
        method_def = methods_by_name.get(method_name)
        payload = build_method_payload(method_def, instance_id, element)
        payload.update(overrides.get(element["BusinessRuleID"], {}))
        return {"method": method_name, "payload": payload, "label": "Continue", "methodDef": method_def}
    return None


def extract_cid(firefly_data: Dict[str, Any]) -> str:
    blob = firefly_data.get("blob") or {}
    public = str(blob.get("public") or blob.get("url") or blob.get("href") or "").strip()
    if not public:
        return ""
    if "/ipfs/" in public:
        return public.split("/ipfs/", 1)[1].split("?", 1)[0].split("#", 1)[0]
    return public


def find_first_firefly_core(client: ChainCollabClient, env_id: str) -> str:
    data = client.get_json(f"/api/v1/eth-environments/{env_id}/fireflys")
    items = data.get("data") or []
    if not items:
        raise ReplayError(f"No FireFly cores found for Ethereum environment {env_id}")
    return str(items[0]["core_url"]).rstrip("/")


def get_identity_contract_address(client: ChainCollabClient, env_id: str) -> str:
    data = client.get_json(f"/api/v1/eth-environments/{env_id}/identity-contract")
    return str((data.get("deployment") or {}).get("contract_address") or "")


def get_dmn_contract_address(client: ChainCollabClient, env_id: str) -> str:
    data = client.get_json(f"/api/v1/eth-environments/{env_id}/dmn-contract")
    return str((data.get("contract") or {}).get("address") or "")


def get_membership_detail(client: ChainCollabClient, consortium_id: str, membership_id: str) -> Dict[str, Any]:
    return client.get_json(f"/api/v1/consortium/{consortium_id}/memberships/{membership_id}")


def get_eth_identity_detail(client: ChainCollabClient, identity_id: str) -> Dict[str, Any]:
    return client.get_json(f"/api/v1/ethereum_identities/{identity_id}")


def ensure_dmn_stored_for_ethereum(
    backend: ChainCollabClient,
    firefly: FireFlyClient,
    consortium_id: str,
    env_id: str,
    dmn_id: str,
    dmn_content: str,
) -> Dict[str, str]:
    dmn = backend.get_json(f"/api/v1/consortiums/{consortium_id}/dmns/{dmn_id}")
    if dmn.get("cid"):
        return {
            "dmnCid": str(dmn["cid"]),
            "dmnHash": str(dmn.get("contentHash") or ZERO_BYTES32),
            "fireflyDataId": str(dmn.get("fireflyDataId") or ""),
        }

    core_url = find_first_firefly_core(backend, env_id)
    upload = firefly.upload_file(
        f"{core_url}/api/v1/namespaces/default/data",
        f"{dmn_id}.dmn",
        dmn_content,
    )
    data_id = str(upload.get("id") or upload.get("data", {}).get("id") or "")
    if not data_id:
        raise ReplayError(f"Failed to upload DMN {dmn_id} to FireFly")
    firefly.post_json(
        f"{core_url}/api/v1/namespaces/default/messages/broadcast",
        {"data": [{"id": data_id}]},
    )

    cid = ""
    for _ in range(10):
        time.sleep(1.5)
        firefly_data = firefly.get_json(f"{core_url}/api/v1/namespaces/default/data/{data_id}")
        cid = extract_cid(firefly_data)
        if cid:
            break
    if not cid:
        raise ReplayError(f"Failed to resolve CID for DMN {dmn_id}")

    updated = backend.put_json(
        f"/api/v1/consortiums/{consortium_id}/dmns/{dmn_id}",
        {
            "fireflyDataId": data_id,
            "cid": cid,
            "dmnContent": dmn_content,
        },
    )
    updated_data = updated.get("data") or updated
    return {
        "dmnCid": str(updated_data.get("cid") or cid),
        "dmnHash": str(updated_data.get("contentHash") or ZERO_BYTES32),
        "fireflyDataId": str(updated_data.get("fireflyDataId") or data_id),
    }


def wait_for_chain_instance(
    firefly: FireFlyClient,
    contract_base_url: str,
    starting_counter: Optional[int],
    attempts: int = 25,
    interval_sec: float = 2.0,
) -> int:
    last_error = None
    for _ in range(attempts):
        try:
            counter = firefly.post_json(f"{contract_base_url}/query/currentInstanceId", {"input": {}})
            numeric_counter = int((counter.get("ret0") or counter.get("output", {}).get("ret0") or 0))
            if starting_counter is not None and numeric_counter <= starting_counter:
                raise ReplayError("instance counter has not advanced yet")
            instance_id = numeric_counter - 1 if numeric_counter > 0 else 0
            firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": instance_id}},
            )
            return instance_id
        except Exception as exc:
            last_error = exc
            time.sleep(interval_sec)
    raise ReplayError(f"Failed to resolve on-chain instance id: {last_error}")


def choose_signer(
    default_signer: str,
) -> str:
    return default_signer


def is_final_success(snapshot: Dict[str, List[Any]]) -> bool:
    event_states = [to_state(x) for x in snapshot["eventStates"]]
    business_states = [to_state(x) for x in snapshot["businessRuleStates"]]
    gateway_states = [to_state(x) for x in snapshot["gatewayStates"]]
    end_done = any(state == 3 for idx, state in enumerate(event_states) if idx > 0)
    all_gateways_done_or_idle = all(state in (0, 3) for state in gateway_states)
    all_business_done_or_idle = all(state in (0, 3) for state in business_states)
    return end_done and all_gateways_done_or_idle and all_business_done_or_idle


def load_config(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_execution_sequence(config: Dict[str, Any], sequence_file: str) -> List[Dict[str, Any]]:
    explicit_file = sequence_file or str(config.get("execution_sequence_file") or "")
    if explicit_file:
        payload = load_json(Path(explicit_file))
        if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
            return list(payload.get("steps") or [])
        if isinstance(payload, dict) and isinstance(payload.get("execution_sequence"), list):
            return list(payload.get("execution_sequence") or [])
        raise ReplayError(
            f"Sequence file {explicit_file} must contain either 'steps' or 'execution_sequence'"
        )
    return list(config.get("execution_sequence") or [])


def normalize_execution_bindings_from_create_params(create_params: Dict[str, Any]) -> Dict[str, Any]:
    participants: Dict[str, Any] = {}
    business_rules: Dict[str, Any] = {}
    for key, value in create_params.items():
        if key.endswith("_account"):
            participant_id = key[: -len("_account")]
            participants.setdefault(participant_id, {})
            participants[participant_id]["address"] = value
            continue
        if key.endswith("_org"):
            participant_id = key[: -len("_org")]
            participants.setdefault(participant_id, {})
            participants[participant_id]["org_name"] = value
            continue
        if isinstance(value, dict) and {"dmnCid", "dmnHash", "decisionId"} & set(value.keys()):
            business_rules[key] = dict(value)
    return {"participants": participants, "business_rules": business_rules}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay the Ethereum Add New Instance + execution flow for a pre-deployed BPMN."
    )
    parser.add_argument("--config", required=True, help="Path to replay JSON config")
    parser.add_argument("--sequence-file", default="", help="Optional path JSON file that contains steps/execution_sequence")
    parser.add_argument("--token", default="", help="JWT token for backend API")
    parser.add_argument("--backend-base", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--output-dir", default="", help="Optional output directory")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    token = args.token or str(config.get("token") or "")
    if not token:
        raise SystemExit("JWT token is required. Pass --token or set config.token")

    consortium_id = str(config["consortium_id"])
    env_id = str(config["eth_environment_id"])
    bpmn_id = str(config["bpmn_id"])
    instance_name_prefix = str(config.get("instance_name_prefix") or "eth-replay-instance")
    backend = ChainCollabClient(args.backend_base, token)
    firefly = FireFlyClient()

    bpmn = backend.get_json(f"/api/v1/consortiums/{consortium_id}/bpmns/{bpmn_id}")
    contract_base_url = str(bpmn.get("firefly_url") or "")
    if not contract_base_url:
        raise ReplayError(f"BPMN {bpmn_id} is not registered to FireFly")
    bpmn_content = str(bpmn.get("bpmnContent") or "")
    execution_layout = dict(bpmn.get("execution_layout") or {})
    contract_info = bpmn.get("ethereum_contract") or {}
    abi = list(contract_info.get("abi") or [])
    methods_by_name = {
        str(item.get("name")): {
            "name": item.get("name"),
            "params": [
                {"name": p.get("name"), "schema": {"details": {"type": p.get("type")}}}
                for p in (item.get("inputs") or [])
            ],
        }
        for item in abi
        if item.get("type") == "function" and item.get("name")
    }
    meta = parse_bpmn_execution_meta(bpmn_content)

    participant_signers: Dict[str, str] = {}
    direct_create_params = config.get("create_instance_params")
    if direct_create_params:
        create_params = dict(direct_create_params)
        execution_bindings = normalize_execution_bindings_from_create_params(create_params)
        for participant_id, binding in execution_bindings["participants"].items():
            address = str(binding.get("address") or "")
            if address:
                participant_signers[participant_id] = address
    else:
        participant_bindings_cfg = dict(config.get("participant_bindings") or {})
        if not participant_bindings_cfg:
            raise ReplayError("config.participant_bindings is required when config.create_instance_params is absent")
        execution_bindings = {"participants": {}, "business_rules": {}}
        create_params = {
            "identityContractAddress": str(config.get("identity_contract_address") or get_identity_contract_address(backend, env_id)),
            "dmnLiteAddress": str(config.get("dmn_lite_address") or get_dmn_contract_address(backend, env_id)),
            "dmnEvalUrl": str(config.get("dmn_eval_url") or DEFAULT_DMN_EVAL_URL),
            "enforceBusinessRuleCaller": bool(config.get("enforce_business_rule_caller", False)),
        }

        for participant_id, binding in participant_bindings_cfg.items():
            membership_id = str(binding["membership_id"])
            eth_identity_id = str(binding["ethereum_identity_id"])
            membership = get_membership_detail(backend, consortium_id, membership_id)
            eth_identity = get_eth_identity_detail(backend, eth_identity_id)
            address = str(eth_identity["address"])
            org_name = str(membership.get("name") or membership.get("membershipName") or "")
            create_params[f"{participant_id}_account"] = address
            create_params[f"{participant_id}_org"] = org_name
            execution_bindings["participants"][participant_id] = {
                "membership_id": membership_id,
                "ethereum_identity_id": eth_identity_id,
                "address": address,
                "org_name": org_name,
            }
            participant_signers[participant_id] = address

        business_rule_bindings_cfg = dict(config.get("business_rule_bindings") or {})
        for rule_id, binding in business_rule_bindings_cfg.items():
            dmn_id = str(binding["dmn_id"])
            decision_id = str(binding["decision_id"])
            dmn = backend.get_json(f"/api/v1/consortiums/{consortium_id}/dmns/{dmn_id}")
            dmn_content = str(binding.get("dmn_content") or dmn.get("dmnContent") or "")
            storage = ensure_dmn_stored_for_ethereum(
                backend,
                firefly,
                consortium_id,
                env_id,
                dmn_id,
                dmn_content,
            )
            allowed_caller = str(binding.get("allowed_caller") or ZERO_ADDRESS)
            caller_restricted = bool(binding.get("caller_restricted", False))
            create_params[rule_id] = {
                "dmnCid": storage["dmnCid"],
                "dmnHash": storage["dmnHash"],
                "decisionId": decision_id,
                "callerRestricted": caller_restricted,
                "allowedCaller": allowed_caller,
            }
            execution_bindings["business_rules"][rule_id] = {
                "dmn_id": dmn_id,
                "dmn_cid": storage["dmnCid"],
                "dmn_hash": storage["dmnHash"],
                "firefly_data_id": storage["fireflyDataId"],
                "callerRestricted": caller_restricted,
                "allowedCaller": allowed_caller,
                "decisionId": decision_id,
            }

    default_signer = str(
        config.get("default_signer")
        or next(iter(participant_signers.values()), "")
    )
    if not default_signer:
        raise ReplayError("config.default_signer is required")

    pre_counter_payload = firefly.post_json(f"{contract_base_url}/query/currentInstanceId", {"input": {}})
    pre_counter = int(pre_counter_payload.get("ret0") or 0)

    create_response = firefly.post_json(
        f"{contract_base_url}/invoke/createInstance",
        {"input": {"params": create_params}},
    )
    on_chain_instance_id = wait_for_chain_instance(firefly, contract_base_url, pre_counter)

    created = backend.post_json(
        f"/api/v1/bpmns/{bpmn_id}/bpmn-instances",
        {
            "name": f"{instance_name_prefix}-{int(time.time())}",
            "env_id": env_id,
            "execution_bindings": execution_bindings,
        },
    )
    local_instance = (created.get("data") or created)
    local_instance_id = str(local_instance["id"])
    patched = backend.patch_json(
        f"/api/v1/bpmns/{bpmn_id}/bpmn-instances/{local_instance_id}",
        {
            "instance_chaincode_id": on_chain_instance_id,
            "name": f"{bpmn.get('name', 'BPMN').replace('.bpmn', '')}-{on_chain_instance_id}",
            "execution_bindings": execution_bindings,
        },
    )

    action_overrides = dict(config.get("action_overrides") or {})
    execution_sequence = load_execution_sequence(config, args.sequence_file)
    steps: List[StepRecord] = []
    snapshot_history: List[Dict[str, Any]] = []
    target_wait_retries = int(config.get("target_wait_retries", 120))
    target_wait_seconds = float(config.get("target_wait_seconds", 1.5))

    if execution_sequence:
        for seq_index, seq_step in enumerate(execution_sequence):
            step_type = str(seq_step.get("type") or "")
            step_element = str(seq_step.get("element") or "")
            step_payload = dict(seq_step.get("payload") or {})
            if not step_type or not step_element:
                raise ReplayError(f"execution_sequence[{seq_index}] must include type and element")

            action, latest_snapshot, wait_history = wait_for_target_action(
                firefly,
                contract_base_url,
                abi,
                meta,
                execution_layout,
                methods_by_name,
                action_overrides,
                on_chain_instance_id,
                step_type,
                step_element,
                step_payload,
                target_wait_retries,
                target_wait_seconds,
            )
            snapshot_history.extend(wait_history)
            if action is None:
                if is_final_success(latest_snapshot):
                    raise ReplayError(
                        f"execution_sequence[{seq_index}] target {step_element} never became actionable because the instance already finished"
                    )
                raise ReplayError(
                    f"execution_sequence[{seq_index}] target {step_element} did not become actionable within {target_wait_retries} polls"
                )

            element, config_item = action
            signer = choose_signer(default_signer)
            try:
                invoke_response = firefly.post_json(
                    f"{contract_base_url}/invoke/{config_item['method']}",
                    {
                        "input": config_item["payload"],
                        "key": signer,
                    },
                )
            except requests.HTTPError as exc:
                raise ReplayError(
                    f"Invoke failed for execution_sequence[{seq_index}] {config_item['method']}: {exc.response.text}"
                ) from exc

            snapshot_after, complete_history = wait_for_element_completed_snapshot(
                firefly,
                contract_base_url,
                abi,
                execution_layout,
                on_chain_instance_id,
                element["type"],
                get_element_id(element),
                target_wait_retries,
                target_wait_seconds,
                2 if element["type"] == "businessRule" and not str(config_item["method"]).endswith("_Continue") else 3,
            )
            snapshot_history.extend(complete_history)
            snapshot_history.append(snapshot_after)
            steps.append(
                StepRecord(
                    element_type=element["type"],
                    element_id=get_element_id(element),
                    method=str(config_item["method"]),
                    signer=signer,
                    payload=dict(config_item["payload"]),
                    response=invoke_response,
                    snapshot_after=snapshot_after,
                )
            )

            if canonical_step_type(step_type) == "businessRule":
                continue_payload = dict(seq_step.get("continue_payload") or {})
                continue_response = None
                continue_element = None
                continue_config = None
                continue_attempts = int(config.get("business_rule_wait_retries", 40))
                continue_delay_seconds = float(config.get("business_rule_continue_delay_seconds", 0))
                continue_delay_applied = False
                for continue_try in range(continue_attempts):
                    continue_action, continue_snapshot, continue_wait_history = wait_for_business_rule_continue(
                        firefly,
                        contract_base_url,
                        abi,
                        meta,
                        execution_layout,
                        methods_by_name,
                        action_overrides,
                        on_chain_instance_id,
                        step_element,
                        continue_payload,
                        int(config.get("business_rule_wait_retries", 40)),
                        float(config.get("business_rule_wait_seconds", 3)),
                    )
                    snapshot_history.extend(continue_wait_history)
                    if continue_action is None:
                        time.sleep(float(config.get("business_rule_wait_seconds", 3)))
                        continue
                    continue_element, continue_config = continue_action
                    try:
                        if continue_delay_seconds > 0 and not continue_delay_applied:
                            time.sleep(continue_delay_seconds)
                            continue_delay_applied = True
                        continue_response = firefly.post_json(
                            f"{contract_base_url}/invoke/{continue_config['method']}",
                            {
                                "input": continue_config["payload"],
                                "key": signer,
                            },
                        )
                        break
                    except requests.HTTPError as exc:
                        text = exc.response.text.lower()
                        if (
                            (
                                "dmn result not ready" in text
                                or "state not allowed" in text
                                or "json string not found" in text
                            )
                            and continue_try + 1 < continue_attempts
                        ):
                            time.sleep(float(config.get("business_rule_wait_seconds", 3)))
                            continue
                        raise ReplayError(
                            f"Invoke failed for business rule continue {continue_config['method']}: {exc.response.text}"
                        ) from exc
                if continue_response is None or continue_element is None or continue_config is None:
                    raise ReplayError(
                        f"Business rule continue for {step_element} never became executable after retries"
                    )
                continue_snapshot_after, continue_complete_history = wait_for_element_completed_snapshot(
                    firefly,
                    contract_base_url,
                    abi,
                    execution_layout,
                    on_chain_instance_id,
                    continue_element["type"],
                    get_element_id(continue_element),
                    target_wait_retries,
                    target_wait_seconds,
                    3,
                )
                snapshot_history.extend(continue_complete_history)
                snapshot_history.append(continue_snapshot_after)
                steps.append(
                    StepRecord(
                        element_type=continue_element["type"],
                        element_id=get_element_id(continue_element),
                        method=str(continue_config["method"]),
                        signer=signer,
                        payload=dict(continue_config["payload"]),
                        response=continue_response,
                        snapshot_after=continue_snapshot_after,
                    )
                )
        final_snapshot = extract_snapshot_output(
            firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": on_chain_instance_id}},
            )
        )
        snapshot_history.append(final_snapshot)
    else:
        business_rule_pending_retries = 0
        while True:
            raw_snapshot = firefly.post_json(
                f"{contract_base_url}/query/getExecutionSnapshot",
                {"input": {"instanceId": on_chain_instance_id}},
            )
            snapshot = extract_snapshot_output(raw_snapshot)
            snapshot_history.append(snapshot)
            if is_final_success(snapshot):
                break

            actionable = find_actionable(
                abi,
                snapshot,
                meta,
                execution_layout,
                methods_by_name,
                action_overrides,
                on_chain_instance_id,
            )

            if not actionable:
                raise ReplayError("No actionable element found before reaching a final state")

            element, config_item = actionable[0]

            latest_snapshot = extract_snapshot_output(
                firefly.post_json(
                    f"{contract_base_url}/query/getExecutionSnapshot",
                    {"input": {"instanceId": on_chain_instance_id}},
                )
            )
            snapshot_history.append(latest_snapshot)
            if is_final_success(latest_snapshot):
                break

            latest_actionable = find_actionable(
                abi,
                latest_snapshot,
                meta,
                execution_layout,
                methods_by_name,
                action_overrides,
                on_chain_instance_id,
            )
            latest_match = next(
                (
                    (latest_element, latest_config)
                    for latest_element, latest_config in latest_actionable
                    if get_element_id(latest_element) == get_element_id(element)
                    and str(latest_config["method"]) == str(config_item["method"])
                ),
                None,
            )
            if latest_match is None:
                time.sleep(0.5)
                continue

            element, config_item = latest_match
            signer = choose_signer(default_signer)
            try:
                invoke_response = firefly.post_json(
                    f"{contract_base_url}/invoke/{config_item['method']}",
                    {
                        "input": config_item["payload"],
                        "key": signer,
                    },
                )
                business_rule_pending_retries = 0
            except requests.HTTPError as exc:
                text = exc.response.text
                if "dmn result not ready" in text and config_item["method"].endswith("_Continue"):
                    business_rule_pending_retries += 1
                    if business_rule_pending_retries > int(config.get("business_rule_wait_retries", 40)):
                        raise ReplayError(f"Business rule result never became ready: {text}")
                    time.sleep(float(config.get("business_rule_wait_seconds", 3)))
                    continue
                if "state not allowed" in text.lower():
                    time.sleep(0.5)
                    continue
                raise ReplayError(f"Invoke failed for {config_item['method']}: {text}") from exc

            snapshot_after, complete_history = wait_for_element_completed_snapshot(
                firefly,
                contract_base_url,
                abi,
                execution_layout,
                on_chain_instance_id,
                element["type"],
                get_element_id(element),
                target_wait_retries,
                target_wait_seconds,
                2 if element["type"] == "businessRule" and not str(config_item["method"]).endswith("_Continue") else 3,
            )
            snapshot_history.extend(complete_history)
            steps.append(
                StepRecord(
                    element_type=element["type"],
                    element_id=get_element_id(element),
                    method=str(config_item["method"]),
                    signer=signer,
                    payload=dict(config_item["payload"]),
                    response=invoke_response,
                    snapshot_after=snapshot_after,
                )
            )

    result = {
        "config_path": str(Path(args.config).resolve()),
        "bpmn_id": bpmn_id,
        "bpmn_name": bpmn.get("name"),
        "contract_base_url": contract_base_url,
        "create_response": create_response,
        "local_instance_id": local_instance_id,
        "local_instance_patch": patched,
        "on_chain_instance_id": on_chain_instance_id,
        "default_signer": default_signer,
        "participant_signers": participant_signers,
        "steps": [
            {
                "element_type": item.element_type,
                "element_id": item.element_id,
                "method": item.method,
                "signer": item.signer,
                "payload": item.payload,
                "response": item.response,
                "snapshot_after": item.snapshot_after,
            }
            for item in steps
        ],
        "final_snapshot": snapshot_history[-1] if snapshot_history else {},
        "success": True,
    }

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        sequence_path = Path(str(args.sequence_file or config.get("execution_sequence_file") or ""))
        if sequence_path.is_absolute() and sequence_path.exists():
            output_dir = sequence_path.parent / "replays"
        else:
            output_dir = EXP3_ROOT / "outputs" / "eth_instance_replay"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"replay_{ts}.json"
    md_path = output_dir / f"replay_{ts}.md"
    dump_json(json_path, result)

    lines = [
        "# Ethereum Instance Replay",
        "",
        f"- BPMN: `{bpmn.get('name')}`",
        f"- BPMN id: `{bpmn_id}`",
        f"- Local instance id: `{local_instance_id}`",
        f"- On-chain instance id: `{on_chain_instance_id}`",
        f"- Contract API: `{contract_base_url}`",
        f"- Steps executed: `{len(steps)}`",
        "",
        "## Final Snapshot",
        "",
        "```json",
        json.dumps(result["final_snapshot"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Steps",
        "",
    ]
    for idx, item in enumerate(steps, start=1):
        lines.append(f"{idx}. `{item.method}` by `{item.signer}` on `{item.element_id}`")
    dump_text(md_path, "\n".join(lines) + "\n")

    print(f"Replay succeeded. JSON report: {json_path}")
    print(f"Replay succeeded. Markdown report: {md_path}")
    print(f"Local instance id: {local_instance_id}")
    print(f"On-chain instance id: {on_chain_instance_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
