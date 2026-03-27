import json
import logging
from typing import Any

from common.utils.http_client import post_json

LOG = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"key", "key_secret", "secret", "password", "private", "token"}


def _mask_payload(payload: dict) -> dict:
    masked = {}
    for k, v in payload.items():
        if k in _SENSITIVE_KEYS:
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


def _log_request(action: str, core_url: str, endpoint: str, payload: dict) -> None:
    LOG.info("[FF] action=%s core=%s endpoint=%s", action, core_url, endpoint)
    LOG.debug("[FF] action=%s payload=%s", action, json.dumps(_mask_payload(payload)))


def _log_response(action: str, status: int, body: dict) -> None:
    LOG.info("[FF] action=%s status=%s", action, status)
    LOG.debug("[FF] action=%s body=%s", action, json.dumps(body))


def _response_payload(response) -> dict:
    payload = response
    if isinstance(payload, list):
        return payload[0] if payload else {}
    if isinstance(payload, dict):
        return payload
    return {}


def abi_event_names(abi: list, ignore: set[str] | None = None) -> list[str]:
    ignore = ignore or {
        "OwnershipTransferRequested",
        "OwnershipTransferred",
    }
    event_names: list[str] = []
    for item in abi or []:
        if not isinstance(item, dict) or item.get("type") != "event":
            continue
        name = item.get("name")
        if not name or name in ignore:
            continue
        event_names.append(str(name))
    return event_names


def build_listener_payload(
    *,
    listener_name: str,
    interface_id: str,
    contract_address: str,
    event_name: str,
    first_event: str = "newest",
) -> dict:
    return {
        "name": listener_name,
        "interface": {"id": interface_id},
        "location": {"address": contract_address},
        "event": {"name": event_name},
        "options": {"firstEvent": first_event},
        "topic": listener_name,
    }


def normalize_ffi(ffi: dict, version_suffix: str | None = None) -> dict:
    methods = ffi.get("methods", [])
    for method in methods:
        params = method.get("params", [])
        for idx, param in enumerate(params):
            name = param.get("name", "")
            if name:
                continue
            if method.get("name") == "orgExists":
                param["name"] = "orgName"
            else:
                param["name"] = f"arg{idx}"
        returns = method.get("returns", [])
        for idx, output in enumerate(returns):
            if output.get("name", ""):
                continue
            output["name"] = f"ret{idx}"
    if version_suffix:
        current = ffi.get("version", "1.0")
        ffi["version"] = f"{current}.{version_suffix}"
    return ffi


def generate_ffi(
    core_url: str,
    abi: list,
    name: str,
    namespace: str = "default",
    version: str = "1.0",
    description: str = "",
) -> dict:
    payload = {
        "name": name,
        "namespace": namespace,
        "version": version,
        "description": description,
        "input": {"abi": abi},
    }
    endpoint = f"http://{core_url}/api/v1/namespaces/{namespace}/contracts/interfaces/generate"
    _log_request("generate_ffi", core_url, endpoint, {"name": name, "namespace": namespace, "version": version})
    status_code, body = post_json(
        endpoint,
        headers={"Content-Type": "application/json"},
        body=payload,
        timeout=60,
        expected_status=(200, 201, 202),
    )
    body_payload = _response_payload(body)
    _log_response("generate_ffi", status_code, body_payload)
    return body_payload


def register_interface(
    core_url: str,
    ffi: dict,
    namespace: str = "default",
    confirm: bool = True,
) -> tuple[int, dict]:
    suffix = "?confirm=true" if confirm else ""
    endpoint = f"http://{core_url}/api/v1/namespaces/{namespace}/contracts/interfaces{suffix}"
    _log_request("register_interface", core_url, endpoint, {"name": ffi.get("name"), "namespace": namespace})
    try:
        status_code, body = post_json(
            endpoint,
            headers={"Content-Type": "application/json"},
            body=ffi,
            timeout=60,
            expected_status=(200, 201, 202),
        )
    except RuntimeError as exc:
        LOG.warning("[FF] action=register_interface failed core=%s err=%s", core_url, exc)
        return 500, {"error": str(exc)}
    body_payload = _response_payload(body)
    _log_response("register_interface", status_code, body_payload)
    return status_code, body_payload


def register_api(
    core_url: str,
    api_name: str,
    interface_id: str,
    contract_address: str,
    namespace: str = "default",
    confirm: bool = True,
) -> tuple[int, dict]:
    payload = {
        "name": api_name,
        "interface": {"id": interface_id},
        "location": {"address": contract_address},
    }
    suffix = "?confirm=true" if confirm else ""
    endpoint = f"http://{core_url}/api/v1/namespaces/{namespace}/apis{suffix}"
    _log_request("register_api", core_url, endpoint, {"name": api_name, "namespace": namespace})
    try:
        status_code, body = post_json(
            endpoint,
            headers={"Content-Type": "application/json"},
            body=payload,
            timeout=60,
            expected_status=(200, 201, 202),
        )
    except RuntimeError as exc:
        LOG.warning("[FF] action=register_api failed core=%s err=%s", core_url, exc)
        return 500, {"error": str(exc)}
    body_payload = _response_payload(body)
    _log_response("register_api", status_code, body_payload)
    return status_code, body_payload


def register_listener(
    core_url: str,
    listener: dict,
    namespace: str = "default",
    confirm: bool = True,
) -> tuple[int, dict]:
    suffix = "?confirm=true" if confirm else ""
    endpoint = f"http://{core_url}/api/v1/namespaces/{namespace}/contracts/listeners{suffix}"
    _log_request(
        "register_listener",
        core_url,
        endpoint,
        {"name": listener.get("name"), "namespace": namespace},
    )
    try:
        status_code, body = post_json(
            endpoint,
            headers={"Content-Type": "application/json"},
            body=listener,
            timeout=60,
            expected_status=(200, 201, 202),
        )
    except RuntimeError as exc:
        LOG.warning("[FF] action=register_listener failed core=%s err=%s", core_url, exc)
        return 500, {"error": str(exc)}
    body_payload = _response_payload(body)
    _log_response("register_listener", status_code, body_payload)
    return status_code, body_payload


def deploy_contract(
    core_url: str,
    abi: list,
    bytecode: str,
    namespace: str = "default",
    constructor_args: list | None = None,
    confirm: bool = True,
    timeout: int = 120,
) -> dict:
    payload = {
        "contract": bytecode,
        "definition": abi,
        "input": constructor_args or [],
    }
    suffix = "?confirm=true" if confirm else ""
    endpoint = f"http://{core_url}/api/v1/namespaces/{namespace}/contracts/deploy{suffix}"
    _log_request("deploy_contract", core_url, endpoint, {"namespace": namespace})
    status_code, body = post_json(
        endpoint,
        headers={"Content-Type": "application/json"},
        body=payload,
        timeout=timeout,
        expected_status=(200, 201, 202),
    )
    body_payload = _response_payload(body)
    _log_response("deploy_contract", status_code, body_payload)
    return body_payload


def api_base(core_url: str, api_name: str, namespace: str = "default") -> str:
    return f"http://{core_url}/api/v1/namespaces/{namespace}/apis/{api_name}"
