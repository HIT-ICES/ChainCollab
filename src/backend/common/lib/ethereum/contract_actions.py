import json
import logging
import os

from common.lib.ethereum.firefly_contracts import (
    generate_ffi as firefly_generate_ffi,
    normalize_ffi as firefly_normalize_ffi,
)


def _ffi_path(contract_dir: str) -> str:
    return os.path.join(contract_dir, "contractFFI.json")


def _actions_path(contract_dir: str) -> str:
    return os.path.join(contract_dir, "contractActions.json")


def _generate_actions_from_ffi(ffi: dict) -> dict:
    actions = {}
    for method in ffi.get("methods", []):
        name = method.get("name")
        if not name:
            continue
        params = method.get("params") or []
        input_map = {
            param.get("name"): param.get("name")
            for param in params
            if param.get("name")
        }
        actions[name] = {
            "method": name,
            "mode": "invoke",
            "key_strategy": "system",
            "input_map": input_map,
        }
    return {"version": 1, "actions": actions}


def _generate_actions_from_abi(abi: list) -> dict:
    actions = {}
    for entry in abi or []:
        if entry.get("type") != "function":
            continue
        name = entry.get("name")
        if not name:
            continue
        params = entry.get("inputs") or []
        input_map = {
            param.get("name"): param.get("name")
            for param in params
            if param.get("name")
        }
        actions[name] = {
            "method": name,
            "mode": "invoke",
            "key_strategy": "system",
            "input_map": input_map,
        }
    return {"version": 1, "actions": actions}


def ensure_contract_actions(
    firefly_core_url: str,
    abi: list,
    contract_name: str,
    contract_dir: str,
    namespace: str = "default",
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    os.makedirs(contract_dir, exist_ok=True)

    try:
        ffi = firefly_generate_ffi(
            firefly_core_url,
            abi,
            name=contract_name,
            namespace=namespace,
            version="1.0",
            description=f"{contract_name} contract interface",
        )
        ffi = firefly_normalize_ffi(ffi, version_suffix="1")
        with open(_ffi_path(contract_dir), "w") as handle:
            json.dump(ffi, handle, indent=2)
        actions = _generate_actions_from_ffi(ffi)
        log.info(
            "Contract FFI generated for %s core=%s",
            contract_name,
            firefly_core_url,
        )
    except Exception as exc:
        log.warning(
            "Contract FFI generate failed for %s core=%s err=%s",
            contract_name,
            firefly_core_url,
            exc,
        )
        actions = _generate_actions_from_abi(abi)

    actions_path = _actions_path(contract_dir)
    with open(actions_path, "w") as handle:
        json.dump(actions, handle, indent=2)
    return actions_path
