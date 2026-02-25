import json
import logging
import time
from typing import Any

from common.lib.ethereum.firefly_contracts import (
    api_base,
    generate_ffi as firefly_generate_ffi,
    normalize_ffi as firefly_normalize_ffi,
    register_api as firefly_register_api,
    register_interface as firefly_register_interface,
)
from common.utils.http_client import get_json, request_json


class FireflyContractManager:
    def __init__(self, logger: logging.Logger | None = None):
        self.log = logger or logging.getLogger(__name__)

    def _log(self, level: str, action: str, **fields):
        parts = [f"action={action}"] + [f"{k}=%s" for k in fields.keys()]
        msg = "FireflyContractManager " + " ".join(parts)
        args = [fields[k] for k in fields.keys()]
        if level == "warning":
            self.log.warning(msg, *args)
        elif level == "debug":
            self.log.debug(msg, *args)
        else:
            self.log.info(msg, *args)

    def generate_ffi(
        self,
        core_url: str,
        abi: list,
        name: str,
        namespace: str = "default",
        version: str = "1.0",
        description: str = "",
        version_suffix: str | None = None,
    ) -> dict:
        ffi = firefly_generate_ffi(
            core_url,
            abi,
            name=name,
            namespace=namespace,
            version=version,
            description=description,
        )
        return firefly_normalize_ffi(ffi, version_suffix=version_suffix)

    def find_interface_id(
        self, core_url: str, name: str, namespace: str = "default"
    ) -> str | None:
        try:
            _, payload = get_json(
                f"http://{core_url}/api/v1/namespaces/{namespace}/contracts/interfaces",
                timeout=30,
                expected_status=(200,),
                params={"name": name},
            )
        except Exception as exc:
            self._log("warning", "interface_lookup_failed", core=core_url, name=name, error=str(exc))
            return None
        if isinstance(payload, dict):
            payload = payload.get("interfaces") or payload.get("items") or []
        if not isinstance(payload, list) or not payload:
            return None
        return payload[0].get("id")

    def register_interface(
        self,
        core_url: str,
        ffi: dict,
        namespace: str = "default",
        confirm: bool = True,
    ) -> dict:
        status, payload = firefly_register_interface(
            core_url, ffi, namespace=namespace, confirm=confirm
        )
        if status in [200, 201, 202]:
            return payload
        existing = self.find_interface_id(
            core_url, ffi.get("name", ""), namespace=namespace
        )
        if existing:
            return {"id": existing, "existing": True}
        raise Exception(
            f"FireFly interface registration failed (status {status}): {str(payload)[:500]}"
        )

    def _find_api(
        self, core_url: str, api_name: str, namespace: str = "default"
    ) -> dict | None:
        try:
            _, payload = get_json(
                f"http://{core_url}/api/v1/namespaces/{namespace}/apis",
                timeout=30,
                expected_status=(200,),
                params={"name": api_name},
            )
        except Exception as exc:
            self._log("warning", "api_lookup_failed", core=core_url, api=api_name, error=str(exc))
            return None
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("apis") or payload.get("items") or []
        else:
            items = []
        if not items:
            return None
        first = items[0]
        return first if isinstance(first, dict) else None

    def register_api(
        self,
        core_url: str,
        api_name: str,
        interface_id: str,
        contract_address: str,
        namespace: str = "default",
        confirm: bool = True,
    ) -> dict:
        existing = self._find_api(core_url, api_name, namespace=namespace)
        if existing:
            existing_id = existing.get("id")
            existing_interface_id = (existing.get("interface") or {}).get("id")
            existing_address = (existing.get("location") or {}).get("address")
            if (
                existing_interface_id == interface_id
                and existing_address == contract_address
            ):
                return {"id": existing_id, "existing": True}
            if existing_id:
                self._log(
                    "info",
                    "api_delete",
                    core=core_url,
                    api=api_name,
                    api_id=existing_id,
                )
                try:
                    request_json(
                        "DELETE",
                        f"http://{core_url}/api/v1/namespaces/{namespace}/apis/{existing_id}",
                        timeout=30,
                        expected_status=(200, 202, 204),
                    )
                except Exception as exc:
                    self._log(
                        "warning",
                        "api_delete_failed",
                        core=core_url,
                        api=api_name,
                        api_id=existing_id,
                        error=str(exc),
                    )

        last_error = None
        for attempt in range(1, 4):
            if attempt > 1:
                time.sleep(2)
            status, payload = firefly_register_api(
                core_url,
                api_name,
                interface_id,
                contract_address,
                namespace=namespace,
                confirm=confirm,
            )
            if status in [200, 201, 202]:
                return payload
            last_error = payload
        raise Exception(
            f"FireFly api registration failed: {str(last_error)[:500]}"
        )

    def invoke_api(
        self,
        core_url: str,
        api_name: str,
        method: str,
        params: dict,
        mode: str = "invoke",
        namespace: str = "default",
        confirm: bool = True,
    ) -> dict:
        payload = {"input": params}
        suffix = "?confirm=true" if confirm and mode == "invoke" else ""
        endpoint = (
            f"{api_base(core_url, api_name, namespace=namespace)}"
            f"/{mode}/{method}{suffix}"
        )
        try:
            _, body = request_json(
                "POST",
                endpoint,
                headers={"Content-Type": "application/json"},
                data_body=json.dumps(payload),
                timeout=60,
                expected_status=(200, 201, 202),
            )
        except Exception as exc:
            raise Exception(f"FireFly api call network error: {exc}") from exc
        return body if isinstance(body, dict) else {"raw": str(body)}
