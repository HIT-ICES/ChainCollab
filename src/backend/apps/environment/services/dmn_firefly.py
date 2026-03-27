from __future__ import annotations

import logging

from apps.environment.models import EthEnvironment


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
    log = logger or logging.getLogger("api")
    try:
        firefly_core_url = identity_flow.get_firefly_core_url(env)
    except Exception as exc:
        log.warning("DMN action=firefly_core_not_found env=%s err=%s", env.id, exc)
        return None

    contract_address = dmn_deployment.get("contractAddress")
    if not contract_address:
        log.warning("DMN action=firefly_missing_address env=%s", env.id)
        return None

    contract_key = f"contracts/{contract_name}.sol:{contract_name}"
    abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")
    if not abi:
        log.warning("DMN action=firefly_missing_abi env=%s key=%s", env.id, contract_key)
        return None

    ffi = firefly_manager.generate_ffi(
        firefly_core_url,
        abi,
        name=contract_name,
        namespace="default",
        version="1.0",
        description=f"{contract_name} contract interface",
        version_suffix=str(env.id)[:8],
    )
    interface_payload = firefly_manager.register_interface(
        firefly_core_url, ffi, namespace="default", confirm=True
    )
    interface_id = interface_payload.get("id") or interface_payload.get("interface", {}).get("id")
    if not interface_id:
        log.warning("DMN action=firefly_interface_missing env=%s", env.id)
        return None

    api_payload = firefly_manager.register_api(
        firefly_core_url,
        api_name,
        interface_id,
        contract_address,
        namespace="default",
        confirm=True,
    )
    return {
        "firefly_core_url": firefly_core_url,
        "firefly_interface_id": interface_id,
        "firefly_api_name": api_name,
        "firefly_api_payload": api_payload,
    }
