from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from .evm_client import EVMAdapterClient, EVMIdentity
from .fabric_client import FabricGatewayClient, FabricIdentity
from .storage import Storage


DEFAULT_EVENT_NAME = "XCallRequested"
DEFAULT_RESULT_SIGNATURE = "onXCallResult(bytes32,bool,bytes)"


class RelayerManager:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_run: Dict[str, float] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            routes = self.storage.list_routes()
            for route in routes:
                if not route.enabled:
                    continue
                try:
                    if route.source_chain_type == "evm":
                        last_run = self._last_run.get(route.id, 0.0)
                        if time.time() - last_run < max(route.poll_interval, 1):
                            continue
                        self._poll_evm_route(route)
                        self._last_run[route.id] = time.time()
                    else:
                        self.storage.add_log(
                            route.id,
                            "n/a",
                            "source",
                            "error",
                            {"error": f"source chain {route.source_chain_type} not supported"},
                        )
                except Exception as exc:
                    self.storage.add_log(
                        route.id,
                        "n/a",
                        "source",
                        "error",
                        {"error": str(exc)},
                    )
                if self._stop_event.is_set():
                    break
            time.sleep(2)

    def _poll_evm_route(self, route) -> None:
        identity = self.storage.get_identity(route.source_identity_id)
        if not identity or not identity.rpc_url:
            raise RuntimeError("source identity missing rpc_url")
        source_client = EVMAdapterClient(
            EVMIdentity(identity.rpc_url, identity.private_key, identity.address),
            route.source_adapter,
        )
        latest_block = source_client.w3.eth.block_number
        start_block = route.last_block or route.source_start_block or latest_block
        if start_block > latest_block:
            return
        event_name = route.metadata.get("source_event_name", DEFAULT_EVENT_NAME)
        logs = source_client.get_event_logs(event_name, start_block, latest_block)
        if not logs:
            self.storage.update_route_last_block(route.id, latest_block)
            return

        for entry in logs:
            args = entry["args"]
            payload = {
                "src_chain_id": int(args.get("srcChainId")),
                "dst_chain_id": int(args.get("dstChainId")),
                "nonce": int(args.get("nonce")),
                "target": args.get("target"),
                "value": int(args.get("value")),
                "call_data": args.get("callData").hex(),
            }
            self._forward_message(route, payload)

        self.storage.update_route_last_block(route.id, latest_block)

    def _forward_message(self, route, payload: Dict[str, Any]) -> None:
        if route.dest_chain_type == "evm":
            self._forward_to_evm(route, payload)
        elif route.dest_chain_type == "fabric":
            self._forward_to_fabric(route, payload)
        else:
            self.storage.add_log(
                route.id,
                "n/a",
                "forward",
                "error",
                {"error": f"dest chain {route.dest_chain_type} not supported"},
            )

    def _forward_to_evm(self, route, payload: Dict[str, Any]) -> None:
        identity = self.storage.get_identity(route.dest_identity_id)
        if not identity or not identity.rpc_url:
            raise RuntimeError("dest identity missing rpc_url")
        dest_client = EVMAdapterClient(
            EVMIdentity(identity.rpc_url, identity.private_key, identity.address),
            route.dest_adapter,
        )
        signer_keys = self._resolve_signer_keys(identity.private_key, route.metadata)
        call_data = bytes.fromhex(payload["call_data"].replace("0x", ""))
        tx_hash, result = dest_client.send_receive_call(
            payload["src_chain_id"],
            payload["dst_chain_id"],
            payload["nonce"],
            payload["target"],
            payload["value"],
            call_data,
            signer_keys,
        )
        message_id = dest_client.compute_message_id(
            payload["src_chain_id"],
            payload["dst_chain_id"],
            payload["nonce"],
            payload["target"],
            payload["value"],
            call_data,
        ).hex()
        self.storage.add_log(
            route.id,
            message_id,
            "forward",
            "success",
            {"tx_hash": tx_hash, "result": self._format_result(result)},
        )
        if result:
            self._send_result_back(route, payload, message_id, result)

    def _forward_to_fabric(self, route, payload: Dict[str, Any]) -> None:
        identity = self.storage.get_identity(route.dest_identity_id)
        if not identity:
            raise RuntimeError("dest identity not found")
        gateway_url = identity.metadata.get("gateway_url", "")
        channel = identity.metadata.get("channel_name", "")
        chaincode = identity.metadata.get("chaincode_name", "")
        if not gateway_url or not channel or not chaincode:
            raise RuntimeError("fabric metadata missing gateway_url/channel_name/chaincode_name")
        client = FabricGatewayClient(FabricIdentity(gateway_url, channel, chaincode))
        if "fabric_payload" not in payload:
            raise RuntimeError("fabric relay requires fabric_payload in event data")
        fabric_payload = payload["fabric_payload"]
        args = [
            str(fabric_payload.get("src_chain_id")),
            str(fabric_payload.get("dst_chain_id")),
            str(fabric_payload.get("nonce")),
            fabric_payload.get("target_chaincode"),
            fabric_payload.get("channel"),
            fabric_payload.get("function"),
            fabric_payload.get("args_json"),
            fabric_payload.get("signatures_json"),
        ]
        result = client.invoke("ReceiveCrossChainCall", args)
        self.storage.add_log(route.id, "n/a", "forward", "success", {"fabric_result": result})

    def _send_result_back(
        self,
        route,
        payload: Dict[str, Any],
        message_id_hex: str,
        result: Any,
    ) -> None:
        callback = route.metadata.get("result_callback") or {}
        target = callback.get("target")
        if not target:
            return
        signature = callback.get("method", DEFAULT_RESULT_SIGNATURE)
        src_identity = self.storage.get_identity(route.source_identity_id)
        if not src_identity or not src_identity.rpc_url:
            return
        src_client = EVMAdapterClient(
            EVMIdentity(src_identity.rpc_url, src_identity.private_key, src_identity.address),
            route.source_adapter,
        )
        message_id = bytes.fromhex(message_id_hex.replace("0x", ""))
        call_data = src_client.build_result_call_data(signature, message_id, result[0], result[1])
        signer_keys = self._resolve_signer_keys(src_identity.private_key, route.metadata)
        tx_hash, _ = src_client.send_receive_call(
            payload["dst_chain_id"],
            payload["src_chain_id"],
            payload["nonce"],
            target,
            0,
            call_data,
            signer_keys,
        )
        self.storage.add_log(
            route.id,
            message_id_hex,
            "result",
            "success",
            {"tx_hash": tx_hash},
        )

    def _resolve_signer_keys(self, identity_key: Optional[str], metadata: Dict[str, Any]) -> List[str]:
        keys = []
        if identity_key:
            keys.append(identity_key)
        for item in metadata.get("relay_signers", []):
            if item and item not in keys:
                keys.append(item)
        return keys

    @staticmethod
    def _format_result(result: Any) -> Dict[str, Any]:
        if not result:
            return {}
        success, data = result
        return {"success": bool(success), "return_data": data.hex() if data else ""}
