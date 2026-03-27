import json
import logging
import os
import shutil
import time

import requests

from apps.api.config import ETHEREUM_CONTRACT_STORE
from common.lib.ethereum.convert_contract import extract_contract_info
from common.lib.ethereum.firefly_contracts import (
    api_base as firefly_api_base,
    deploy_contract as firefly_deploy_contract,
    generate_ffi as firefly_generate_ffi,
    normalize_ffi as firefly_normalize_ffi,
    register_api as firefly_register_api,
    register_interface as firefly_register_interface,
)
from common.lib.ethereum.solc_compiler import SolidityCompiler
from apps.infra.models import Firefly
from apps.environment.models import EthEnvironment
from apps.ethereum.models import EthereumIdentity, IdentityDeployment
from apps.fabric.models import ResourceSet


class IdentityContractFlow:
    def __init__(self, logger: logging.Logger | None = None):
        self.log = logger or logging.getLogger(__name__)

    def _mask_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {}
        masked = {}
        for key, value in payload.items():
            if key in {"key", "key_secret", "secret", "password", "private", "token"}:
                masked[key] = "***"
            else:
                masked[key] = value
        return masked

    def _log_action(self, level: str, action: str, **fields) -> None:
        parts = [f"action={action}"] + [f"{k}=%s" for k in fields.keys()]
        msg = "IdentityFlow " + " ".join(parts)
        args = [fields[k] for k in fields.keys()]
        if level == "debug":
            self.log.debug(msg, *args)
        elif level == "warning":
            self.log.warning(msg, *args)
        else:
            self.log.info(msg, *args)

    def resolve_identity_artifacts(self):
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../..")
        )
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        abi_path = os.path.join(contract_dir, "IdentityRegistry.abi")
        bin_path = os.path.join(contract_dir, "IdentityRegistry.bin")
        sol_copy_path = os.path.join(contract_dir, "IdentityRegistry.sol")
        meta_path = os.path.join(contract_dir, "IdentityRegistry.solc.meta.json")

        if not os.path.exists(sol_copy_path):
            candidate_paths = [
                os.path.join(
                    repo_root,
                    "src",
                    "backend",
                    "src",
                    "presetContract",
                    "IdentityRegistry.sol",
                ),
                os.path.join(
                    ETHEREUM_CONTRACT_STORE,
                    "identity-contract",
                    "IdentityRegistry.sol",
                ),
                os.path.join(
                    repo_root,
                    "src",
                    "geth_identity_contract",
                    "contracts",
                    "IdentityRegistry.sol",
                ),
            ]
            source_path = next(
                (path for path in candidate_paths if os.path.exists(path)),
                None,
            )
            if not source_path:
                raise FileNotFoundError(
                    "IdentityRegistry.sol not found under opt/ethereum-contracts or geth_identity_contract/contracts"
                )
            shutil.copyfile(source_path, sol_copy_path)

        compiler = SolidityCompiler()
        expected_meta = {
            "compiler_version": compiler.version,
            "evm_version": compiler.evm_version,
        }
        existing_meta = None
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as meta_file:
                    existing_meta = json.load(meta_file)
            except Exception:
                existing_meta = None

        if (
            not os.path.exists(abi_path)
            or not os.path.exists(bin_path)
            or existing_meta != expected_meta
        ):
            is_installed, version_or_error = compiler.check_installation()
            if not is_installed:
                raise Exception(
                    f"Solidity compiler not available: {version_or_error}"
                )
            output_json_path = os.path.join(contract_dir, "IdentityRegistry.json")
            return_code, compiled_data, error_msg = compiler.compile_contract(
                sol_copy_path, output_json_path
            )
            if return_code != 0:
                raise Exception(f"Compilation failed: {error_msg}")
            contract_info = extract_contract_info(
                compiled_data, contract_name="IdentityRegistry"
            )
            with open(abi_path, "w") as abi_file:
                json.dump(contract_info["definition"], abi_file, indent=2)
            with open(bin_path, "w") as bin_file:
                bin_file.write(contract_info["contract"])
            with open(meta_path, "w") as meta_file:
                json.dump(expected_meta, meta_file, indent=2)
        with open(abi_path, "r") as abi_file:
            abi = json.load(abi_file)
        with open(bin_path, "r") as bin_file:
            bytecode = bin_file.read().strip()
        if not bytecode:
            raise ValueError("IdentityRegistry bytecode is empty")
        return abi, bytecode

    def build_identity_ffi(self, abi: list) -> dict:
        methods = []
        for entry in abi:
            if entry.get("type") != "function":
                continue
            params = [
                {
                    "name": param.get("name") or f"arg{idx}",
                    "schema": self._abi_type_to_schema(param.get("type", "string")),
                }
                for idx, param in enumerate(entry.get("inputs", []))
            ]
            returns = [
                {
                    "name": output.get("name") or f"ret{idx}",
                    "schema": self._abi_type_to_schema(output.get("type", "string")),
                }
                for idx, output in enumerate(entry.get("outputs", []))
            ]
            methods.append(
                {
                    "name": entry.get("name"),
                    "pathname": "",
                    "description": "",
                    "params": params,
                    "returns": returns,
                }
            )
        return {
            "namespace": "default",
            "name": "IdentityRegistry",
            "description": "Identity registry contract interface",
            "version": "1.0",
            "methods": methods,
        }

    def _abi_type_to_schema(self, abi_type: str) -> dict:
        if abi_type.endswith("]"):
            base = abi_type[: abi_type.index("[")]
            return {
                "type": "array",
                "details": {"type": abi_type},
                "items": self._abi_type_to_schema(base),
            }
        if abi_type.startswith("uint") or abi_type.startswith("int"):
            return {
                "type": "integer",
                "details": {"type": abi_type},
            }
        if abi_type == "bool":
            return {"type": "boolean", "details": {"type": abi_type}}
        if abi_type == "address":
            return {"type": "string", "details": {"type": abi_type}}
        if abi_type.startswith("bytes"):
            return {"type": "string", "details": {"type": abi_type}}
        if abi_type == "string":
            return {"type": "string", "details": {"type": abi_type}}
        return {"type": "string", "details": {"type": abi_type}}

    def normalize_identity_ffi(self, ffi: dict, version_suffix: str | None = None) -> dict:
        return firefly_normalize_ffi(ffi, version_suffix=version_suffix)

    def write_identity_ffi(self, ffi: dict) -> str:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        ffi_path = os.path.join(contract_dir, "identityFFI.json")
        with open(ffi_path, "w") as handle:
            json.dump(ffi, handle, indent=2)
        return ffi_path

    def _actions_path(self) -> str:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        return os.path.join(contract_dir, "identityActions.json")

    def _load_identity_ffi(self) -> dict | None:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        ffi_path = os.path.join(contract_dir, "identityFFI.json")
        if not os.path.exists(ffi_path):
            return None
        with open(ffi_path, "r") as handle:
            return json.load(handle)

    def _generate_actions_from_ffi(self, ffi: dict) -> dict:
        actions = {}
        for method in ffi.get("methods", []):
            name = method.get("name")
            if not name:
                continue
            params = method.get("params") or []
            input_map = {param.get("name"): param.get("name") for param in params if param.get("name")}
            actions[name] = {
                "method": name,
                "mode": "invoke",
                "key_strategy": "system",
                "input_map": input_map,
            }
        return {"version": 1, "actions": actions}

    def load_identity_actions(self, ffi: dict | None = None) -> dict:
        actions_path = self._actions_path()
        if os.path.exists(actions_path):
            with open(actions_path, "r") as handle:
                return json.load(handle)
        if ffi is None:
            ffi = self._load_identity_ffi()
        if not ffi:
            return {"version": 1, "actions": {}}
        actions = self._generate_actions_from_ffi(ffi)
        with open(actions_path, "w") as handle:
            json.dump(actions, handle, indent=2)
        return actions

    def _resolve_context_value(self, context: dict, path: str):
        current = context
        for chunk in path.split("."):
            if isinstance(current, dict) and chunk in current:
                current = current[chunk]
            else:
                return None
        return current

    def invoke_contract_action(
        self,
        firefly_core_url: str,
        api_name: str,
        action_name: str,
        context: dict,
        default_params: dict | None = None,
        mode_override: str | None = None,
    ) -> dict:
        actions = self.load_identity_actions()
        action = (actions.get("actions") or {}).get(action_name)
        if action:
            input_map = action.get("input_map") or {}
            params = {}
            for key, path in input_map.items():
                value = self._resolve_context_value(context, path)
                if value is None:
                    raise Exception(f"missing input mapping for {key} via {path}")
                params[key] = value
            method = action.get("method") or action_name
            mode = mode_override or action.get("mode") or "invoke"
            return self.invoke_identity_api(
                firefly_core_url,
                method,
                params,
                mode=mode,
                api_name=api_name,
            )
        if default_params is None:
            raise Exception(f"action '{action_name}' not found and no default params provided")
        return self.invoke_identity_api(
            firefly_core_url,
            action_name,
            default_params,
            mode=mode_override or "invoke",
            api_name=api_name,
        )

    def generate_identity_ffi(self, firefly_core_url: str, abi: list) -> dict:
        return firefly_generate_ffi(
            firefly_core_url,
            abi,
            name="IdentityRegistry",
            namespace="default",
            version="1.0",
            description="Identity registry contract interface",
        )

    def register_identity_ffi(self, firefly_core_url: str, abi: list) -> dict:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        existing = self.find_identity_interface_id(firefly_core_url)
        if existing:
            self._log_action(
                "info",
                "ffi_exists",
                core=firefly_core_url,
                interface=existing,
            )
            try:
                detail = requests.get(
                    f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces/{existing}",
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if detail.status_code in [200, 202]:
                    payload = detail.json()
                    methods = payload.get("methods", [])
                    has_empty = any(
                        (not p.get("name"))
                        for m in methods
                        for p in (m.get("params") or [])
                    )
                    if not has_empty:
                        return {"id": existing, "existing": True}
                else:
                    return {"id": existing, "existing": True}
            except Exception:
                return {"id": existing, "existing": True}
        try:
            self._log_action("info", "ffi_generate_start", core=firefly_core_url)
            ffi = self.generate_identity_ffi(firefly_core_url, abi)
            ffi = self.normalize_identity_ffi(ffi, version_suffix="1")
            self.write_identity_ffi(ffi)
            self.load_identity_actions(ffi)
        except Exception as exc:
            fallback_ffi = self.build_identity_ffi(abi)
            fallback_ffi = self.normalize_identity_ffi(fallback_ffi, version_suffix="1")
            with open(os.path.join(contract_dir, "identityFFI.generate_error.log"), "w") as handle:
                handle.write(str(exc))
            self.write_identity_ffi(fallback_ffi)
            self.load_identity_actions(fallback_ffi)
            ffi = fallback_ffi
            self._log_action(
                "warning",
                "ffi_generate_failed",
                core=firefly_core_url,
                error=exc,
            )
        status_code, payload = firefly_register_interface(
            firefly_core_url, ffi, namespace="default", confirm=True
        )
        self._log_action(
            "info",
            "ffi_register",
            core=firefly_core_url,
            status=status_code,
        )
        self._log_action(
            "debug",
            "ffi_register_body",
            body=json.dumps(payload)[:500],
        )
        if status_code not in [200, 201, 202]:
            if isinstance(payload, dict) and payload.get("error", "").startswith("FF10127"):
                existing = self.find_identity_interface_id(firefly_core_url)
                if existing:
                    return {"id": existing, "existing": True}
            raise Exception(
                f"FireFly FFI registration failed with status {status_code}: "
                f"{str(payload)[:500]}"
            )
        return payload

    def find_identity_interface_id(self, firefly_core_url: str) -> str | None:
        response = requests.get(
            f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces",
            params={"name": "IdentityRegistry"},
            timeout=30,
        )
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except Exception:
            return None
        if isinstance(payload, dict):
            payload = payload.get("interfaces") or payload.get("items") or []
        if not isinstance(payload, list) or not payload:
            return None
        return payload[0].get("id")

    def register_identity_api(
        self,
        firefly_core_url: str,
        interface_id: str,
        contract_address: str,
        api_name: str,
    ) -> dict:
        self._log_action(
            "info",
            "api_register_request",
            core=firefly_core_url,
            api=api_name,
            interface=interface_id,
            address=contract_address,
        )
        existing_api_id = None
        existing_interface_id = None
        existing_location = None
        try:
            api_list = requests.get(
                f"http://{firefly_core_url}/api/v1/namespaces/default/apis",
                params={"name": api_name},
                timeout=30,
            )
            if api_list.status_code == 200:
                api_payload = api_list.json()
                items = api_payload.get("apis") or api_payload.get("items") or []
                if isinstance(items, list) and items:
                    existing_api = items[0]
                    existing_api_id = existing_api.get("id")
                    existing_interface = existing_api.get("interface") or {}
                    existing_interface_id = existing_interface.get("id")
                    existing_location = (existing_api.get("location") or {}).get(
                        "address"
                    )
                    self._log_action(
                        "info",
                        "api_existing",
                        core=firefly_core_url,
                        api=api_name,
                        api_id=existing_api_id,
                        interface=existing_interface_id,
                        address=existing_location,
                    )
                else:
                    self._log_action(
                        "info",
                        "api_existing_none",
                        core=firefly_core_url,
                        api=api_name,
                    )
            else:
                self._log_action(
                    "warning",
                    "api_list_failed",
                    core=firefly_core_url,
                    api=api_name,
                    status=api_list.status_code,
                    body=api_list.text[:300],
                )
        except Exception:
            existing_api_id = None
        last_error = None
        for attempt in range(1, 4):
            if attempt > 1:
                time.sleep(2)
            if existing_api_id:
                try:
                    requests.delete(
                        f"http://{firefly_core_url}/api/v1/namespaces/default/apis/{existing_api_id}",
                        timeout=30,
                    )
                    self._log_action(
                        "info",
                        "api_deleted",
                        core=firefly_core_url,
                        api_id=existing_api_id,
                    )
                    existing_api_id = None
                except Exception:
                    self._log_action(
                        "warning",
                        "api_delete_failed",
                        core=firefly_core_url,
                        api_id=existing_api_id,
                    )
            status_code, payload = firefly_register_api(
                firefly_core_url,
                api_name=api_name,
                interface_id=interface_id,
                contract_address=contract_address,
                namespace="default",
                confirm=True,
            )
            self._log_action(
                "info",
                "api_register_attempt",
                attempt=attempt,
                status=status_code,
                core=firefly_core_url,
                api=api_name,
            )
            self._log_action(
                "debug",
                "api_register_body",
                body=json.dumps(payload)[:500],
            )
            if status_code in [200, 201, 202]:
                return payload
            if isinstance(payload, dict) and payload.get("error", "").startswith("FF10127"):
                if existing_api_id and (
                    existing_interface_id != interface_id
                    or (existing_location and existing_location != contract_address)
                ):
                    try:
                        requests.delete(
                            f"http://{firefly_core_url}/api/v1/namespaces/default/apis/{existing_api_id}",
                            timeout=30,
                        )
                    except Exception:
                        return payload
                    continue
                return payload
            last_error = f"status {status_code}: {str(payload)[:500]}"
        raise Exception(f"FireFly API registration failed after retries: {last_error}")

    def invoke_identity_api(
        self,
        firefly_core_url: str,
        method: str,
        params: dict,
        mode: str = "invoke",
        api_name: str = "IdentityRegistry",
        key: str | None = None,
    ) -> dict:
        payload = {"input": params}
        if key:
            payload["key"] = key
        suffix = "?confirm=true" if mode == "invoke" else ""
        url = (
            f"http://{firefly_core_url}/api/v1/namespaces/default/apis/"
            f"{api_name}/{mode}/{method}{suffix}"
        )
        self._log_action(
            "info",
            "api_call",
            core=firefly_core_url,
            api=api_name,
            mode=mode,
            method=method,
        )
        self._log_action(
            "debug",
            "api_call_payload",
            payload=json.dumps(self._mask_payload(payload))[:500],
        )
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60,
        )
        self._log_action(
            "info",
            "api_call_response",
            status=response.status_code,
            core=firefly_core_url,
            api=api_name,
            method=method,
        )
        if response.status_code not in [200, 201, 202]:
            raise Exception(
                f"FireFly API call failed with status {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return payload

    def ensure_org_registered(
        self,
        firefly_core_url: str,
        org_name: str,
        org_admin_address: str,
        api_name: str = "IdentityRegistry",
    ) -> None:
        if not org_admin_address:
            raise Exception("org_admin_address is required")
        self._log_action(
            "info",
            "org_register_start",
            core=firefly_core_url,
            api=api_name,
            org=org_name,
            admin=org_admin_address,
        )
        try:
            context = {
                "orgName": org_name,
                "orgAdmin": org_admin_address,
                "org": {"name": org_name, "admin": org_admin_address},
            }
            self.invoke_contract_action(
                firefly_core_url,
                api_name,
                "createOrganization",
                context,
                default_params={"orgName": org_name, "orgAdmin": org_admin_address},
            )
        except Exception as exc:
            error_text = str(exc)
            if "already exists" in error_text.lower():
                self._log_action(
                    "info",
                    "org_register_exists",
                    core=firefly_core_url,
                    api=api_name,
                    org=org_name,
                )
                return
            raise
        self._log_action(
            "info",
            "org_register_done",
            core=firefly_core_url,
            api=api_name,
            org=org_name,
        )

    def fetch_firefly_org_admin_address(self, firefly: Firefly) -> str | None:
        try:
            response = requests.get(
                f"http://{firefly.core_url}/api/v1/identities",
                params={"fetchverifiers": "true"},
                timeout=30,
            )
            self._log_action(
                "info",
                "identities_fetch",
                org=firefly.org_name,
                status=response.status_code,
            )
            if response.status_code not in [200, 202]:
                self._log_action(
                    "warning",
                    "identities_fetch_failed",
                    org=firefly.org_name,
                    status=response.status_code,
                )
                return None
            payload = response.json()
            identity_dump_path = os.path.join(
                ETHEREUM_CONTRACT_STORE,
                "identity-contract",
                f"firefly-identities-{firefly.org_name}.json",
            )
            os.makedirs(os.path.dirname(identity_dump_path), exist_ok=True)
            with open(identity_dump_path, "w") as handle:
                json.dump(payload, handle, indent=2)
            self._log_action(
                "info",
                "identities_dumped",
                org=firefly.org_name,
                path=identity_dump_path,
            )
        except Exception as exc:
            self._log_action(
                "warning",
                "identities_fetch_error",
                org=firefly.org_name,
                error=exc,
            )
            return None
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("identities") or payload.get("items") or []
        else:
            items = []
        if not isinstance(items, list):
            return None
        org_identities = [item for item in items if item.get("type") == "org"]
        self._log_action(
            "info",
            "identities_fetched",
            org=firefly.org_name,
            total=len(items),
            org_total=len(org_identities),
        )
        for identity in items:
            if identity.get("type") != "org":
                continue
            if identity.get("name") != firefly.org_name:
                continue
            verifiers = identity.get("verifiers") or []
            for verifier in verifiers:
                if verifier.get("type") == "ethereum_address":
                    value = verifier.get("value")
                    if self._looks_like_eth_address(value):
                        return value
        return None

    def register_memberships_for_env(self, env: EthEnvironment) -> dict:
        memberships = [rs.membership for rs in env.resource_sets.all() if rs.membership]
        memberships = list({m.id: m for m in memberships}.values())
        if not memberships:
            return {"total": 0, "success": 0, "failed": 0, "results": []}
        results = []
        success = 0
        failed = 0
        system_resource_set = env.resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        ).first()
        system_firefly = (
            Firefly.objects.filter(resource_set=system_resource_set).first()
            if system_resource_set
            else None
        )
        if not system_firefly:
            return {
                "total": len(memberships),
                "success": 0,
                "failed": len(memberships),
                "results": [
                    {"membership": m.name, "status": "failed", "error": "system firefly not found"}
                    for m in memberships
                ],
            }
        api_name = self.get_identity_api_name(env)
        self._log_action(
            "info",
            "org_registration_start",
            env=env.id,
            memberships=len(memberships),
        )
        self._log_action(
            "debug",
            "org_registration_memberships",
            names=[m.name for m in memberships],
        )
        system_membership = (
            system_resource_set.membership if system_resource_set else None
        )
        default_admin_address = None
        if system_membership:
            system_identity = (
                EthereumIdentity.objects.filter(
                    eth_environment=env, membership=system_membership
                )
                .order_by("create_at")
                .first()
            )
            if system_identity and system_identity.address:
                default_admin_address = system_identity.address
        if not default_admin_address:
            fallback_identity = (
                EthereumIdentity.objects.filter(eth_environment=env)
                .order_by("create_at")
                .first()
            )
            if fallback_identity and fallback_identity.address:
                default_admin_address = fallback_identity.address
        for membership in memberships:
            try:
                identity = (
                    EthereumIdentity.objects.filter(
                        eth_environment=env, membership=membership
                    )
                    .order_by("create_at")
                    .first()
                )
                org_admin_address = None
                if identity and identity.address:
                    org_admin_address = identity.address
                if not org_admin_address:
                    rs = env.resource_sets.filter(membership=membership).first()
                    firefly = rs.firefly.first() if rs else None
                    if firefly:
                        org_admin_address = self.fetch_firefly_org_admin_address(firefly)
                if not org_admin_address:
                    org_admin_address = default_admin_address
                if not org_admin_address:
                    raise Exception("no org admin address available")
                self._log_action(
                    "info",
                    "org_register_resolved",
                    env=env.id,
                    membership=membership.name,
                    admin=org_admin_address,
                )
                self._log_action(
                    "info",
                    "org_register_call",
                    env=env.id,
                    membership=membership.name,
                    core=system_firefly.core_url,
                    api=api_name,
                    method="createOrganization",
                )
                self.ensure_org_registered(
                    system_firefly.core_url,
                    membership.name,
                    org_admin_address,
                    api_name=api_name,
                )
                results.append({"membership": membership.name, "status": "ok"})
                success += 1
            except Exception as exc:
                self._log_action(
                    "warning",
                    "org_register_failed",
                    env=env.id,
                    membership=membership.name,
                    error=exc,
                )
                results.append(
                    {"membership": membership.name, "status": "failed", "error": str(exc)}
                )
                failed += 1
        self._log_action(
            "info",
            "org_registration_done",
            env=env.id,
            success=success,
            failed=failed,
        )
        return {
            "total": len(memberships),
            "success": success,
            "failed": failed,
            "results": results,
        }

    def sync_all_identities_for_env(self, env: EthEnvironment) -> dict:
        identities = EthereumIdentity.objects.filter(eth_environment=env)
        results = []
        success = 0
        failed = 0
        self._log_action(
            "info",
            "sync_all_start",
            env=env.id,
            identities=identities.count(),
        )
        firefly_core_url = self.get_firefly_core_url(env)
        api_name = self.get_identity_api_name(env)
        for identity in identities:
            try:
                self.ensure_org_registered(
                    firefly_core_url,
                    identity.membership.name,
                    identity.address,
                    api_name=api_name,
                )
                context = {
                    "identityAddress": identity.address,
                    "fireflyIdentityId": identity.firefly_identity_id or "",
                    "orgName": identity.membership.name,
                    "customKey": identity.membership.name,
                    "identity": {
                        "address": identity.address,
                        "firefly_id": identity.firefly_identity_id or "",
                    },
                    "membership": {"name": identity.membership.name},
                }
                self.invoke_contract_action(
                    firefly_core_url,
                    api_name,
                    "registerIdentity",
                    context,
                    default_params={
                        "identityAddress": identity.address,
                        "fireflyIdentityId": identity.firefly_identity_id or "",
                        "orgName": identity.membership.name,
                        "customKey": identity.membership.name,
                    },
                )
                results.append({"id": str(identity.id), "status": "ok"})
                success += 1
            except Exception as exc:
                results.append(
                    {"id": str(identity.id), "status": "failed", "error": str(exc)}
                )
                failed += 1
        self._log_action(
            "info",
            "sync_all_done",
            env=env.id,
            success=success,
            failed=failed,
        )
        return {
            "total": len(results),
            "success": success,
            "failed": failed,
            "results": results,
        }

    def load_identity_abi(self):
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        abi_path = os.path.join(contract_dir, "IdentityRegistry.abi")
        if not os.path.exists(abi_path):
            return None
        with open(abi_path, "r") as abi_file:
            return json.load(abi_file)

    def get_firefly_core_url(self, env: EthEnvironment) -> str:
        resource_sets = env.resource_sets.all()
        system_resource_sets = resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        )
        if not system_resource_sets.exists():
            raise Exception("System resource set not found")
        system_resource_set = system_resource_sets.first()
        firefly = Firefly.objects.filter(resource_set=system_resource_set).first()
        if not firefly:
            raise Exception("Firefly instance not found for system resource set")
        return firefly.core_url

    def get_identity_api_name(self, env: EthEnvironment) -> str:
        deployment = IdentityDeployment.objects.filter(eth_environment=env).first()
        if deployment and deployment.api_name:
            return deployment.api_name
        return "IdentityRegistry"

    def deploy_identity_contract(self, env_id):
        env = EthEnvironment.objects.get(id=env_id)
        self._log_action("info", "deploy_start", env=env.id)
        deployment, _ = IdentityDeployment.objects.get_or_create(
            eth_environment=env
        )
        deployment.status = "SETTINGUP"
        deployment.error = None
        deployment.save(update_fields=["status", "error", "updated_at"])
        env.identity_contract_status = "SETTINGUP"
        env.save(update_fields=["identity_contract_status"])

        abi, bytecode = self.resolve_identity_artifacts()
        firefly_core_url = self.get_firefly_core_url(env)
        self._log_action("info", "deploy_core", env=env.id, core=firefly_core_url)

        deployment_result = firefly_deploy_contract(
            firefly_core_url,
            abi,
            bytecode,
            namespace="default",
            constructor_args=[],
            confirm=True,
            timeout=120,
        )
        self._log_action("info", "deploy_response_ok", env=env.id)

        deployment_status = deployment_result.get("status", "Unknown")
        output_data = deployment_result.get("output", {})
        contract_location = output_data.get("contractLocation", {})
        contract_address = contract_location.get("address") or output_data.get("address")
        tx_hash = output_data.get("transactionHash") or deployment_result.get("tx")
        deployment_id = deployment_result.get("id")

        if str(deployment_status).lower() in ["succeeded", "success", "started"]:
            mapped_status = "STARTED"
        elif str(deployment_status).lower() in ["pending", "running"]:
            mapped_status = "SETTINGUP"
        else:
            mapped_status = "FAILED"

        deployment.contract_address = contract_address
        deployment.deployment_tx_hash = tx_hash
        deployment.deployment_id = deployment_id
        deployment.status = mapped_status
        deployment.save(
            update_fields=[
                "contract_address",
                "deployment_tx_hash",
                "deployment_id",
                "status",
                "updated_at",
            ]
        )
        env.identity_contract_status = mapped_status
        env.save(update_fields=["identity_contract_status"])
        self._log_action(
            "info",
            "deploy_status",
            env=env.id,
            status=mapped_status,
            address=contract_address,
            tx=tx_hash,
        )

        if mapped_status in ["STARTED", "SETTINGUP"]:
            try:
                api_name = None
                if contract_address:
                    api_name = f"IdentityRegistry-{contract_address[-6:]}"
                else:
                    api_name = f"IdentityRegistry-{int(time.time())}"
                system_rs = env.resource_sets.filter(
                    ethereum_sub_resource_set__org_type=1
                ).first()
                if not system_rs:
                    raise Exception("System resource set not found for identity deploy")
                firefly = Firefly.objects.filter(resource_set=system_rs).first()
                if not firefly:
                    raise Exception("System firefly not found for identity deploy")
                self._log_action(
                    "info",
                    "deploy_register_start",
                    env=env.id,
                    resource_set=system_rs.id,
                    core=firefly.core_url,
                )
                ffi_response = self.register_identity_ffi(firefly.core_url, abi)
                interface_id = (
                    ffi_response.get("id")
                    or ffi_response.get("interface", {}).get("id")
                )
                self._log_action(
                    "info",
                    "deploy_register_interface",
                    core=firefly.core_url,
                    interface=interface_id,
                )
                if interface_id and contract_address:
                    try:
                        api_response = self.register_identity_api(
                            firefly.core_url,
                            interface_id,
                            contract_address,
                            api_name,
                        )
                    except Exception as exc:
                        error_text = str(exc)
                        if "FF10303" in error_text or "interface" in error_text.lower():
                            self._log_action(
                                "warning",
                                "deploy_api_retry_interface_missing",
                                core=firefly.core_url,
                                interface=interface_id,
                            )
                            ffi_response = self.register_identity_ffi(
                                firefly.core_url, abi
                            )
                            interface_id = (
                                ffi_response.get("id")
                                or ffi_response.get("interface", {}).get("id")
                            )
                            api_response = self.register_identity_api(
                                firefly.core_url,
                                interface_id,
                                contract_address,
                                api_name,
                            )
                        else:
                            raise
                    self._log_action(
                        "info",
                        "deploy_register_api",
                        core=firefly.core_url,
                        api_id=api_response.get("id"),
                        api_name=api_name,
                    )
                    deployment.interface_id = interface_id
                    deployment.api_id = api_response.get("id")
                    deployment.api_name = api_name
                    deployment.api_address = firefly_api_base(
                        firefly.core_url, api_name, namespace="default"
                    )
                    deployment.save(
                        update_fields=[
                            "interface_id",
                            "api_id",
                            "api_name",
                            "api_address",
                            "updated_at",
                        ]
                    )
                self._log_action("info", "deploy_register_done", env=env.id)
                org_result = self.register_memberships_for_env(env)
                self._log_action(
                    "info",
                    "deploy_org_registration",
                    env=env.id,
                    success=org_result.get("success"),
                    failed=org_result.get("failed"),
                )
            except Exception as exc:
                deployment.error = f"FFI registration failed: {exc}"
                deployment.save(update_fields=["error", "updated_at"])
                self._log_action(
                    "warning",
                    "deploy_register_failed",
                    env=env.id,
                    error=exc,
                )

        self._log_action(
            "info",
            "deploy_done",
            env=env.id,
            status=mapped_status,
        )
        return {
            "status": mapped_status,
            "contract_address": contract_address,
            "transaction_hash": tx_hash,
            "deployment_id": deployment_id,
        }

    def redeploy_and_sync(self, env_id):
        self._log_action("info", "redeploy_sync_start", env=env_id)
        deploy_result = self.deploy_identity_contract(env_id)
        env = EthEnvironment.objects.get(id=env_id)
        sync_result = self.sync_all_identities_for_env(env)
        self._log_action(
            "info",
            "redeploy_sync_done",
            env=env_id,
            deploy_status=deploy_result.get("status"),
            sync_success=sync_result.get("success"),
            sync_failed=sync_result.get("failed"),
        )
        return {"deploy": deploy_result, "sync": sync_result}

    def _looks_like_eth_address(self, value: str | None) -> bool:
        if not value or not isinstance(value, str):
            return False
        return value.startswith("0x") and len(value) == 42
