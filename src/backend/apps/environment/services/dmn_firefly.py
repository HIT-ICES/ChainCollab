from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from apps.environment.models import EthEnvironment
from common.lib.ethereum.firefly_contracts import (
    api_base as firefly_api_base,
    build_listener_payload,
)


def _load_operator_abi() -> list | None:
    operator_abi_path = (
        Path(__file__).resolve().parents[4]
        / "oracle"
        / "CHAINLINK"
        / "deployment"
        / "operator-abi.json"
    )
    if not operator_abi_path.exists():
        return None
    try:
        with operator_abi_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, list) else None
    except Exception:
        return None


def resolve_contract_abi(compiled: dict, contract_name: str) -> list | None:
    contract_key = f"contracts/{contract_name}.sol:{contract_name}"
    abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")
    if abi:
        return abi
    if contract_name == "Operator":
        return _load_operator_abi()
    return None


def dmn_abi_fingerprint(compiled: dict, contract_name: str) -> tuple[list | None, str | None]:
    abi = resolve_contract_abi(compiled, contract_name)
    if not abi:
        return None, None
    abi_json = json.dumps(abi, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return abi, hashlib.sha256(abi_json.encode("utf-8")).hexdigest()


def contract_event_names(abi: list) -> list[str]:
    ignore = {
        "OwnershipTransferRequested",
        "OwnershipTransferred",
    }
    event_names: list[str] = []
    for item in abi:
        if item.get("type") != "event":
            continue
        name = item.get("name")
        if not name or name in ignore:
            continue
        event_names.append(str(name))
    return event_names


def _register_contract_bundle_to_firefly(
    *,
    env: EthEnvironment,
    compiled: dict,
    contract_name: str,
    contract_address: str,
    api_name: str,
    identity_flow,
    firefly_manager,
    logger: logging.Logger | None = None,
) -> dict | None:
    log = logger or logging.getLogger("api")
    if not contract_address:
        log.warning("FireFly action=missing_contract_address env=%s contract=%s", env.id, contract_name)
        return None

    try:
        firefly_core_url = identity_flow.get_firefly_core_url(env)
    except Exception as exc:
        log.warning("FireFly action=core_not_found env=%s contract=%s err=%s", env.id, contract_name, exc)
        return None

    abi, abi_hash = dmn_abi_fingerprint(compiled, contract_name)
    if not abi:
        contract_key = f"contracts/{contract_name}.sol:{contract_name}"
        log.warning("FireFly action=missing_abi env=%s contract=%s key=%s", env.id, contract_name, contract_key)
        return None

    interface_name = f"{contract_name}-{abi_hash[:8]}-{str(env.id)[:8]}"
    ffi = firefly_manager.generate_ffi(
        firefly_core_url,
        abi,
        name=interface_name,
        namespace="default",
        version="1.0",
        description=f"{contract_name} contract interface ({abi_hash[:12]})",
        version_suffix=str(env.id)[:8],
    )
    interface_payload = firefly_manager.register_interface(
        firefly_core_url, ffi, namespace="default", confirm=True
    )
    interface_id = interface_payload.get("id") or interface_payload.get("interface", {}).get("id")
    if not interface_id:
        log.warning("FireFly action=interface_missing env=%s contract=%s", env.id, contract_name)
        return None

    api_payload = firefly_manager.register_api(
        firefly_core_url,
        api_name,
        interface_id,
        contract_address,
        namespace="default",
        confirm=True,
    )

    listeners: list[dict] = []
    for event_name in contract_event_names(abi):
        listener_name = f"{api_name}-{event_name}"
        listener_payload = build_listener_payload(
            listener_name=listener_name,
            interface_id=interface_id,
            contract_address=contract_address,
            event_name=event_name,
            first_event="newest",
        )
        registered_listener = firefly_manager.register_listener(
            firefly_core_url,
            listener_payload,
            namespace="default",
            confirm=True,
        )
        listeners.append(
            {
                "name": listener_name,
                "event_path": event_name,
                "payload": registered_listener,
            }
        )

    return {
        "firefly_core_url": firefly_core_url,
        "firefly_interface_id": interface_id,
        "firefly_interface_name": interface_name,
        "firefly_api_name": api_name,
        "firefly_api_base": firefly_api_base(firefly_core_url, api_name, namespace="default"),
        "firefly_abi_hash": abi_hash,
        "firefly_api_payload": api_payload,
        "firefly_listeners": listeners,
    }


def register_dmn_contract_to_firefly(
    *,
    env: EthEnvironment,
    dmn_deployment: dict,
    compiled: dict,
    contract_name: str,
    api_name: str,
    identity_flow,
    firefly_manager,
    logger: logging.Logger | None = None,
) -> dict | None:
    return _register_contract_bundle_to_firefly(
        env=env,
        compiled=compiled,
        contract_name=contract_name,
        contract_address=dmn_deployment.get("contractAddress"),
        api_name=api_name,
        identity_flow=identity_flow,
        firefly_manager=firefly_manager,
        logger=logger,
    )


def register_related_chainlink_contracts_to_firefly(
    *,
    env: EthEnvironment,
    chainlink_detail: dict,
    compiled: dict,
    identity_flow,
    firefly_manager,
    logger: logging.Logger | None = None,
) -> dict:
    log = logger or logging.getLogger("api")
    result: dict = {
        "firefly": {
            "firefly_related_contracts": {},
        },
    }

    contract_specs: list[tuple[str, str, str | None]] = []
    operator_address = chainlink_detail.get("operator")
    if operator_address:
        contract_specs.append(("Operator", str(operator_address), f"ChainlinkOperator-{str(operator_address)[-6:]}"))

    link_token_address = chainlink_detail.get("linkToken")
    if link_token_address:
        contract_specs.append(("LinkToken", str(link_token_address), f"LinkToken-{str(link_token_address)[-6:]}"))

    ocr_contract_address = chainlink_detail.get("ocrContract") or chainlink_detail.get("ocr_contract")
    if ocr_contract_address:
        contract_specs.append((
            "AccessControlledOffchainAggregator",
            str(ocr_contract_address),
            f"OCRAggregator-{str(ocr_contract_address)[-6:]}",
        ))

    for contract_name, contract_address, api_prefix in contract_specs:
        api_name = api_prefix
        registered = _register_contract_bundle_to_firefly(
            env=env,
            compiled=compiled,
            contract_name=contract_name,
            contract_address=contract_address,
            api_name=api_name,
            identity_flow=identity_flow,
            firefly_manager=firefly_manager,
            logger=log,
        )
        if registered:
            result["firefly"]["firefly_related_contracts"][contract_name] = registered

    return result
