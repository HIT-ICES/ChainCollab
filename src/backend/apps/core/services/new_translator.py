import os
from typing import Any, Dict, Literal, Optional

import requests

from apps.api.config import CURRENT_IP


TranslatorTarget = Literal["go", "solidity"]


class NewTranslatorError(RuntimeError):
    pass


class NewTranslatorClient:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 60):
        configured = base_url or os.environ.get("NEW_TRANSLATOR_API_BASE")
        self.base_url = (configured or f"http://{CURRENT_IP}:9999/api/v1").rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NewTranslatorError(f"newTranslator request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400:
            message = data.get("message") or data.get("detail") or response.text
            raise NewTranslatorError(message)

        return data

    def generate_artifacts(
        self,
        bpmn_content: str,
        target: TranslatorTarget,
        artifact_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if target == "solidity":
            result = self._post(
                "/chaincode/generate-eth",
                {
                    "bpmnContent": bpmn_content,
                    "artifactName": artifact_name,
                },
            )
            return {
                "target": "solidity",
                "dslContent": result.get("dslContent", ""),
                "chaincodeContent": result.get("contractContent", ""),
                "ffiContent": result.get("ffiContent", "{}"),
                "executionLayout": result.get("executionLayout", {}),
            }

        dsl_result = self._post(
            "/chaincode/generate",
            {
                "bpmnContent": bpmn_content,
                "artifactName": artifact_name,
            },
        )
        dsl_content = dsl_result.get("bpmnContent", "")
        compile_result = self._post(
            "/chaincode/compile",
            {
                "dslContent": dsl_content,
                "target": "go",
            },
        )
        ffi_content = compile_result.get("ffiContent")
        if not ffi_content or ffi_content == "{}":
            ffi_content = dsl_result.get("ffiContent", "{}")
        return {
            "target": "go",
            "dslContent": dsl_content,
            "chaincodeContent": compile_result.get("chaincodeContent", ""),
            "ffiContent": ffi_content,
            "executionLayout": {},
        }

    def get_participants(self, bpmn_content: str) -> Any:
        return self._post("/chaincode/getPartByBpmnC", {"bpmnContent": bpmn_content})

    def get_messages(self, bpmn_content: str) -> Any:
        return self._post("/chaincode/getMessagesByBpmnC", {"bpmnContent": bpmn_content})

    def get_business_rules(self, bpmn_content: str) -> Any:
        return self._post(
            "/chaincode/getBusinessRulesByBpmnC",
            {"bpmnContent": bpmn_content},
        )

    def get_decisions(self, dmn_content: str) -> Any:
        return self._post("/chaincode/getDecisions", {"dmnContent": dmn_content})
