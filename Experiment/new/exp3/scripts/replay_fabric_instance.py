#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from common import EXP3_ROOT, dump_json, dump_text, load_json


STATE_DONE = 3
STATE_READY = 1
STATE_WAITING = 2


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


class FireFlyClient:
    def __init__(self, base_url: str, timeout: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def get_json(self, path_or_url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path_or_url: str, payload: Dict[str, Any]) -> Any:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        resp = self.session.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


def canonical_base(url: str) -> str:
    return url.rstrip("/")


def api_base_from_core(core_base: str, api_name: str, namespace: str = "default") -> str:
    return f"{canonical_base(core_base)}/api/v1/namespaces/{namespace}/apis/{api_name}"


def discover_contract_api(core_base: str, api_name: str = "", chaincode: str = "", namespace: str = "default") -> Dict[str, Any]:
    client = FireFlyClient(core_base)
    apis = client.get_json(f"/api/v1/namespaces/{namespace}/apis")
    if not isinstance(apis, list):
        raise ReplayError(f"Unexpected FireFly API list response: {apis}")
    matches = []
    for item in apis:
        item_name = str(item.get("name") or "")
        item_chaincode = str((item.get("location") or {}).get("chaincode") or "")
        if api_name and item_name != api_name:
            continue
        if chaincode and item_chaincode != chaincode:
            continue
        matches.append(item)
    if not matches:
        raise ReplayError(f"No Fabric contract API matched api_name={api_name!r}, chaincode={chaincode!r}")
    if len(matches) > 1 and not api_name and not chaincode:
        names = ", ".join(str(item.get("name")) for item in matches)
        raise ReplayError(f"Multiple Fabric APIs found; set config.api_name or config.chaincode: {names}")
    return matches[0]


def load_config(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_frontend_param(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("param="):
        text = text.split("=", 1)[1].strip()
    try:
        value = ast.literal_eval(text)
    except Exception as exc:
        raise ReplayError(f"Failed to parse frontend param file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"Frontend param file {path} must evaluate to an object")
    return value


def load_execution_sequence(config: Dict[str, Any], sequence_file: str) -> List[Dict[str, Any]]:
    explicit_file = sequence_file or str(config.get("execution_sequence_file") or "")
    if explicit_file:
        payload = load_json(Path(explicit_file))
        if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
            return list(payload.get("steps") or [])
        if isinstance(payload, dict) and isinstance(payload.get("execution_sequence"), list):
            return list(payload.get("execution_sequence") or [])
        raise ReplayError(f"Sequence file {explicit_file} must contain 'steps' or 'execution_sequence'")
    return list(config.get("execution_sequence") or [])


def infer_param_type(param: Dict[str, Any]) -> str:
    raw = str(((param.get("schema") or {}).get("type")) or param.get("type") or "").lower()
    if "bool" in raw:
        return "boolean"
    if "int" in raw or "number" in raw:
        return "number"
    return "string"


def default_value(param: Dict[str, Any], instance_id: str, element_id: str) -> Any:
    name = str(param.get("name") or "")
    lower = name.lower()
    if name in ("InstanceID", "instanceID", "instanceId"):
        return str(instance_id)
    if "fireflytran" in lower:
        return str(uuid.uuid4())
    if lower == "contentofdmn":
        return ""
    kind = infer_param_type(param)
    if kind == "boolean":
        return False
    if kind == "number":
        return 1
    if lower.endswith("id"):
        return f"{element_id}-{instance_id}"
    return f"sample-{name or 'value'}"


def build_payload(method: Dict[str, Any], instance_id: str, element_id: str) -> Dict[str, Any]:
    return {
        str(param["name"]): default_value(param, instance_id, element_id)
        for param in method.get("params", []) or []
        if param.get("name")
    }


def method_map(interface: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("name")): item for item in interface.get("methods", []) if item.get("name")}


def state_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def id_list(items: List[Dict[str, Any]], key: str) -> List[str]:
    return [str(item.get(key) or "") for item in items]


def query_snapshot(client: FireFlyClient, api_base: str, instance_id: str) -> Dict[str, Any]:
    input_payload = {"input": {"InstanceID": str(instance_id)}}
    messages = client.post_json(f"{api_base}/query/GetAllMessages", input_payload)
    gateways = client.post_json(f"{api_base}/query/GetAllGateways", input_payload)
    events = client.post_json(f"{api_base}/query/GetAllActionEvents", input_payload)
    business_rules = client.post_json(f"{api_base}/query/GetAllBusinessRules", input_payload)
    return {
        "messageIds": id_list(messages, "MessageID"),
        "messageStates": [state_int(item.get("MsgState")) for item in messages],
        "messageFireflyTranIds": [str(item.get("FireflyTranID") or "") for item in messages],
        "gatewayIds": id_list(gateways, "GatewayID"),
        "gatewayStates": [state_int(item.get("GatewayState")) for item in gateways],
        "eventIds": id_list(events, "EventID"),
        "eventStates": [state_int(item.get("EventState")) for item in events],
        "businessRuleIds": id_list(business_rules, "BusinessRuleID"),
        "businessRuleStates": [state_int(item.get("State")) for item in business_rules],
        "businessRuleRequestIds": [str(item.get("RequestID") or "") for item in business_rules],
        "raw": {
            "messages": messages,
            "gateways": gateways,
            "events": events,
            "businessRules": business_rules,
        },
    }


def element_state(snapshot: Dict[str, Any], element_type: str, element_id: str) -> int:
    keys = {
        "message": ("messageIds", "messageStates"),
        "gateway": ("gatewayIds", "gatewayStates"),
        "event": ("eventIds", "eventStates"),
        "businessRule": ("businessRuleIds", "businessRuleStates"),
    }
    ids_key, states_key = keys[element_type]
    ids = snapshot.get(ids_key) or []
    if element_id not in ids:
        return 0
    index = ids.index(element_id)
    states = snapshot.get(states_key) or []
    return state_int(states[index] if index < len(states) else 0)


def is_final_success(snapshot: Dict[str, Any]) -> bool:
    end_done = any(state_int(value) == STATE_DONE for idx, value in enumerate(snapshot.get("eventStates") or []) if idx > 0)
    gateways_ok = all(state_int(value) in (0, STATE_DONE) for value in snapshot.get("gatewayStates") or [])
    rules_ok = all(state_int(value) in (0, STATE_DONE) for value in snapshot.get("businessRuleStates") or [])
    return end_done and gateways_ok and rules_ok


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


def method_for_step(step_type: str, element_id: str, business_continue: bool = False) -> str:
    canonical = canonical_step_type(step_type)
    if canonical == "message":
        return f"{element_id}_Send"
    if canonical == "businessRule" and business_continue:
        return f"{element_id}_Continue"
    return element_id


def merge_payload(
    method: Dict[str, Any],
    instance_id: str,
    element_id: str,
    overrides: Dict[str, Any],
    dmn_content: str = "",
) -> Dict[str, Any]:
    payload = build_payload(method, instance_id, element_id)
    payload.update(overrides)
    if dmn_content:
        payload["ContentOfDmn"] = dmn_content
    return payload


def wait_for_state(
    client: FireFlyClient,
    api_base: str,
    instance_id: str,
    element_type: str,
    element_id: str,
    target_states: Tuple[int, ...],
    attempts: int,
    interval_sec: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    history: List[Dict[str, Any]] = []
    latest: Dict[str, Any] = {}
    for _ in range(max(1, attempts)):
        latest = query_snapshot(client, api_base, instance_id)
        history.append(latest)
        if element_state(latest, element_type, element_id) in target_states:
            return latest, history
        if is_final_success(latest):
            return latest, history
        time.sleep(interval_sec)
    return latest, history


def wait_for_instance_created_event(
    event_clients: List[FireFlyClient],
    tx_id: str,
    created_after_sequences: Dict[str, int],
    attempts: int,
    interval_sec: float,
) -> Tuple[str, Dict[str, Any]]:
    last_event: Dict[str, Any] = {}
    for _ in range(max(1, attempts)):
        for event_client in event_clients:
            events = event_client.get_json("/api/v1/namespaces/default/events", params={"limit": 100})
            threshold = created_after_sequences.get(event_client.base_url, 0)
            for event in events if isinstance(events, list) else []:
                if int(event.get("sequence") or 0) <= threshold:
                    continue
                if event.get("type") != "blockchain_event_received" or event.get("topic") != "InstanceCreated":
                    continue
                ref = str(event.get("reference") or "")
                if not ref:
                    continue
                chain_event = event_client.get_json(f"/api/v1/namespaces/default/blockchainevents/{ref}")
                output = chain_event.get("output") or {}
                instance_id = str(output.get("InstanceID") or output.get("instanceID") or "")
                if instance_id:
                    return instance_id, chain_event
                last_event = chain_event
        time.sleep(interval_sec)
    raise ReplayError(f"Timed out waiting for InstanceCreated event after tx {tx_id}; last_event={last_event}")


def latest_event_sequence(client: FireFlyClient) -> int:
    events = client.get_json("/api/v1/namespaces/default/events", params={"limit": 1})
    if isinstance(events, list) and events:
        return int(events[0].get("sequence") or 0)
    return 0


def default_output_dir_for_sequence(sequence_file: str) -> Path:
    sequence_path = Path(sequence_file)
    if sequence_path.is_absolute() and "paths" in sequence_path.parts:
        parts = sequence_path.parts
        path_index = parts.index("paths")
        if path_index > 0 and path_index + 1 < len(parts):
            case_name = parts[path_index - 1]
            path_name = parts[path_index + 1]
            return EXP3_ROOT / "fabric" / case_name / "paths" / path_name / "replays"
    return EXP3_ROOT / "fabric" / "instance_replays"


def invoke(client: FireFlyClient, api_base: str, method: str, payload: Dict[str, Any], signer: str) -> Dict[str, Any]:
    body: Dict[str, Any] = {"input": payload}
    if signer:
        body["key"] = signer
    return client.post_json(f"{api_base}/invoke/{method}", body)


def wait_for_operation(
    client: FireFlyClient,
    response: Dict[str, Any],
    attempts: int,
    interval_sec: float,
) -> Dict[str, Any]:
    operation_id = str(response.get("id") or "")
    if not operation_id:
        return response
    latest = response
    for _ in range(max(1, attempts)):
        latest = client.get_json(f"/api/v1/namespaces/default/operations/{operation_id}", params={"fetchstatus": "true"})
        status = str(latest.get("status") or "")
        if status == "Succeeded":
            return latest
        if status == "Failed":
            raise ReplayError(f"Fabric operation {operation_id} failed: {latest.get('error') or latest.get('output')}")
        time.sleep(interval_sec)
    raise ReplayError(f"Fabric operation {operation_id} did not finish; latest status={latest.get('status')}")


def dmn_content_for_rule(config: Dict[str, Any], rule_id: str, instance_created_event: Dict[str, Any]) -> str:
    contents = dict(config.get("dmn_contents") or {})
    if rule_id in contents:
        return str(contents[rule_id])
    output = instance_created_event.get("output") or {}
    return str(output.get(rule_id) or "")


def derive_signer_from_create_params(config: Dict[str, Any], participant_id: str) -> str:
    participant = (config.get("create_instance_params") or {}).get(participant_id) or {}
    msp = str(participant.get("msp") or "")
    x509 = str(participant.get("x509") or "")
    if not msp or "@" not in x509:
        return ""
    encoded, x509_msp = x509.rsplit("@", 1)
    try:
        verifier = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return ""
    return f"{x509_msp or msp}::{verifier}"


def snapshot_element(snapshot: Dict[str, Any], element_type: str, element_id: str) -> Dict[str, Any]:
    raw_key = {
        "message": "messages",
        "gateway": "gateways",
        "event": "events",
        "businessRule": "businessRules",
    }[element_type]
    id_key = {
        "message": "MessageID",
        "gateway": "GatewayID",
        "event": "EventID",
        "businessRule": "BusinessRuleID",
    }[element_type]
    for item in ((snapshot.get("raw") or {}).get(raw_key) or []):
        if str(item.get(id_key) or "") == element_id:
            return dict(item)
    return {}


def choose_signer(
    *,
    config: Dict[str, Any],
    snapshot: Dict[str, Any],
    element_type: str,
    element_id: str,
    seq_step: Dict[str, Any],
    default_signer: str,
) -> str:
    if seq_step.get("signer"):
        return str(seq_step["signer"])
    signer_overrides = dict(config.get("signer_overrides") or {})
    if element_id in signer_overrides:
        return str(signer_overrides[element_id])
    if element_type != "message":
        return ""
    element = snapshot_element(snapshot, element_type, element_id)
    participant_id = str(element.get("SendMspID") or "")
    participant_signers = dict(config.get("participant_signers") or {})
    if participant_id and participant_id in participant_signers and participant_signers[participant_id]:
        return str(participant_signers[participant_id])
    if participant_id:
        derived = derive_signer_from_create_params(config, participant_id)
        if derived:
            return derived
    return default_signer


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a Fabric/FireFly BPMN instance from an exp3 execution sequence.")
    parser.add_argument("--config", required=True, help="Path to Fabric replay config JSON")
    parser.add_argument("--sequence-file", default="", help="Optional execution_sequence.json")
    parser.add_argument("--output-dir", default="", help="Optional output directory")
    parser.add_argument("--frontend-param-file", default="", help="Optional text file copied from frontend 'Get CreateInstance Param'")
    parser.add_argument("--no-compare", action="store_true", help="Skip automatic Fabric-vs-DSL/Solidity comparison after replay")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    namespace = str(config.get("namespace") or "default")
    core_base = canonical_base(str(config.get("firefly_core_url") or "http://127.0.0.1:5000"))
    api_base = str(config.get("contract_api_url") or "").rstrip("/")
    api_info: Dict[str, Any] = {}
    if not api_base:
        api_info = discover_contract_api(
            core_base,
            api_name=str(config.get("api_name") or ""),
            chaincode=str(config.get("chaincode") or ""),
            namespace=namespace,
        )
        api_base = api_base_from_core(core_base, str(api_info["name"]), namespace)

    client = FireFlyClient(core_base)
    event_core_urls = [
        canonical_base(str(item))
        for item in (config.get("event_core_urls") or [core_base])
        if str(item).strip()
    ]
    if core_base not in event_core_urls:
        event_core_urls.append(core_base)
    event_clients = [FireFlyClient(url) for url in event_core_urls]
    interface = client.get_json(f"{api_base}/interface")
    methods = method_map(interface)
    default_signer = str(config.get("default_signer") or "")
    if not default_signer:
        status_payload = client.get_json("/api/v1/status")
        verifiers = (((status_payload.get("org") or {}).get("verifiers")) or [])
        default_signer = str((verifiers[0] or {}).get("value") or "") if verifiers else ""

    existing_instance_id = str(config.get("existing_instance_id") or "")
    if existing_instance_id:
        create_response = {"skipped": True, "reason": "existing_instance_id configured"}
        instance_id = existing_instance_id
        instance_created_event = dict(config.get("instance_created_event") or {})
    else:
        frontend_param_file = args.frontend_param_file or str(config.get("frontend_param_file") or "")
        create_params = load_frontend_param(Path(frontend_param_file)) if frontend_param_file else config.get("create_instance_params")
        if create_params is None:
            create_params = config.get("init_parameters") or {}
        if isinstance(create_params, str):
            init_parameters_bytes = create_params
        else:
            init_parameters_bytes = json.dumps(create_params, ensure_ascii=False)

        pre_sequences = {
            event_client.base_url: latest_event_sequence(event_client)
            for event_client in event_clients
        }
        create_response = invoke(
            client,
            api_base,
            "CreateInstance",
            {"initParametersBytes": init_parameters_bytes},
            str(config.get("create_instance_signer") or ""),
        )
        create_response = wait_for_operation(
            client,
            create_response,
            int(config.get("operation_wait_retries", 80)),
            float(config.get("operation_wait_seconds", 1.0)),
        )
        tx_id = str(create_response.get("tx") or create_response.get("id") or "")
        instance_id, instance_created_event = wait_for_instance_created_event(
            event_clients,
            tx_id,
            pre_sequences,
            int(config.get("instance_wait_retries", 60)),
            float(config.get("instance_wait_seconds", 1.5)),
        )

    execution_sequence = load_execution_sequence(config, args.sequence_file)
    if not execution_sequence:
        raise ReplayError("Fabric replay currently requires an explicit execution_sequence")

    steps: List[StepRecord] = []
    snapshot_history: List[Dict[str, Any]] = []
    wait_retries = int(config.get("target_wait_retries", 80))
    wait_seconds = float(config.get("target_wait_seconds", 1.5))
    action_overrides = dict(config.get("action_overrides") or {})

    for index, seq_step in enumerate(execution_sequence):
        step_type = str(seq_step.get("type") or "")
        element_id = str(seq_step.get("element") or "")
        if not step_type or not element_id:
            raise ReplayError(f"execution_sequence[{index}] must include type and element")
        canonical = canonical_step_type(step_type)
        method_name = method_for_step(canonical, element_id)
        method = methods.get(method_name)
        if not method:
            raise ReplayError(f"Method not found in Fabric FFI: {method_name}")

        snapshot, waited = wait_for_state(
            client,
            api_base,
            instance_id,
            canonical,
            element_id,
            (STATE_READY,),
            wait_retries,
            wait_seconds,
        )
        snapshot_history.extend(waited)
        if element_state(snapshot, canonical, element_id) != STATE_READY:
            raise ReplayError(f"execution_sequence[{index}] target {element_id} did not become READY")

        payload = merge_payload(
            method,
            instance_id,
            element_id,
            {**action_overrides.get(element_id, {}), **dict(seq_step.get("payload") or {})},
        )
        signer = choose_signer(
            config=config,
            snapshot=snapshot,
            element_type=canonical,
            element_id=element_id,
            seq_step=seq_step,
            default_signer=default_signer,
        )
        try:
            response = invoke(client, api_base, method_name, payload, signer)
            response = wait_for_operation(
                client,
                response,
                int(config.get("operation_wait_retries", 80)),
                float(config.get("operation_wait_seconds", 1.0)),
            )
        except requests.HTTPError as exc:
            raise ReplayError(f"Invoke failed for {method_name}: {exc.response.text}") from exc
        target_states_after = (STATE_WAITING, STATE_DONE) if canonical == "businessRule" else (STATE_DONE,)
        snapshot_after, waited_after = wait_for_state(
            client,
            api_base,
            instance_id,
            canonical,
            element_id,
            target_states_after,
            wait_retries,
            wait_seconds,
        )
        snapshot_history.extend(waited_after)
        steps.append(StepRecord(canonical, element_id, method_name, signer, payload, response, snapshot_after))

        if canonical == "businessRule":
            auto_done_snapshot, auto_done_waited = wait_for_state(
                client,
                api_base,
                instance_id,
                canonical,
                element_id,
                (STATE_DONE,),
                int(config.get("business_rule_auto_continue_wait_retries", 10)),
                float(config.get("business_rule_auto_continue_wait_seconds", 1.5)),
            )
            snapshot_history.extend(auto_done_waited)
            if element_state(auto_done_snapshot, canonical, element_id) == STATE_DONE:
                steps[-1].snapshot_after = auto_done_snapshot
                continue

            continue_name = method_for_step(canonical, element_id, business_continue=True)
            continue_method = methods.get(continue_name)
            if not continue_method:
                raise ReplayError(f"Business rule continue method not found in Fabric FFI: {continue_name}")
            content = str(seq_step.get("continue_payload", {}).get("ContentOfDmn") or dmn_content_for_rule(config, element_id, instance_created_event))
            if not content:
                raise ReplayError(f"No DMN content available for business rule {element_id}")
            continue_payload = merge_payload(
                continue_method,
                instance_id,
                element_id,
                {**action_overrides.get(element_id, {}), **dict(seq_step.get("continue_payload") or {})},
                dmn_content=content,
            )
            try:
                continue_response = invoke(client, api_base, continue_name, continue_payload, signer)
                continue_response = wait_for_operation(
                    client,
                    continue_response,
                    int(config.get("operation_wait_retries", 80)),
                    float(config.get("operation_wait_seconds", 1.0)),
                )
            except requests.HTTPError as exc:
                raise ReplayError(f"Invoke failed for {continue_name}: {exc.response.text}") from exc
            continue_snapshot_after, continue_waited = wait_for_state(
                client,
                api_base,
                instance_id,
                canonical,
                element_id,
                (STATE_DONE,),
                wait_retries,
                wait_seconds,
            )
            snapshot_history.extend(continue_waited)
            steps.append(StepRecord(canonical, element_id, continue_name, signer, continue_payload, continue_response, continue_snapshot_after))

    final_snapshot = query_snapshot(client, api_base, instance_id)
    snapshot_history.append(final_snapshot)

    result = {
        "config_path": str(Path(args.config).resolve()),
        "platform": "fabric",
        "api_base": api_base,
        "api_info": api_info,
        "interface": {"id": interface.get("id"), "name": interface.get("name"), "version": interface.get("version")},
        "create_response": create_response,
        "instance_created_event": instance_created_event,
        "instance_id": instance_id,
        "default_signer": default_signer,
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
        "final_snapshot": final_snapshot,
        "success": True,
    }

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = default_output_dir_for_sequence(str(args.sequence_file or config.get("execution_sequence_file") or ""))
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"replay_{ts}.json"
    md_path = output_dir / f"replay_{ts}.md"
    dump_json(json_path, result)

    lines = [
        "# Fabric Instance Replay",
        "",
        f"- API: `{api_base}`",
        f"- Instance id: `{instance_id}`",
        f"- Steps executed: `{len(steps)}`",
        "",
        "## Final Snapshot",
        "",
        "```json",
        json.dumps(final_snapshot, ensure_ascii=False, indent=2),
        "```",
    ]
    dump_text(md_path, "\n".join(lines) + "\n")
    print(f"Replay succeeded. JSON report: {json_path}")
    print(f"Replay succeeded. Markdown report: {md_path}")
    print(f"Fabric instance id: {instance_id}")
    if not args.no_compare:
        try:
            from compare_fabric_replay import run_fabric_comparison

            comparison = run_fabric_comparison(
                fabric_replay=json_path,
                sequence_file=str(args.sequence_file or config.get("execution_sequence_file") or ""),
            )
            print(f"Fabric normalized trace: {comparison['fabric_normalized']}")
            for warning in comparison["warnings"]:
                print(f"Comparison warning: {warning}")
            for name, report in comparison["comparisons"].items():
                print(
                    f"{name}: consistent={report['consistent']} "
                    f"findings={report['finding_count']} "
                    f"steps={report['left_steps']}/{report['right_steps']}"
                )
        except Exception as exc:
            print(f"Comparison warning: automatic Fabric comparison failed: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
