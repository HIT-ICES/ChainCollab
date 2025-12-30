from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class FabricIdentity:
    gateway_url: str
    channel_name: str
    chaincode_name: str


class FabricGatewayClient:
    def __init__(self, identity: FabricIdentity) -> None:
        self.identity = identity

    def invoke(self, function_name: str, args: List[str]) -> Dict[str, Any]:
        if not self.identity.gateway_url:
            raise RuntimeError("fabric gateway_url not configured")
        payload = {
            "channel": self.identity.channel_name,
            "chaincode": self.identity.chaincode_name,
            "function": function_name,
            "args": args,
        }
        resp = requests.post(f"{self.identity.gateway_url.rstrip('/')}/invoke", json=payload, timeout=30)
        if resp.status_code >= 300:
            raise RuntimeError(f"fabric invoke failed: {resp.text}")
        return resp.json() if resp.content else {"status": "ok"}
