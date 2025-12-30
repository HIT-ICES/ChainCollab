from __future__ import annotations

import threading
import time
from typing import Dict, Optional

import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware

from .models import EventSpec
from .storage import Storage


class EventManager:
    """负责根据注册信息启动/停止链上事件监听，并可触发回调。"""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self._listeners: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start_listener(self, event_id: str) -> None:
        event = self.storage.get_event(event_id)
        if not event:
            raise ValueError(f"event {event_id} not found")
        with self._lock:
            if event_id in self._listeners:
                return
            stop_event = threading.Event()
            self._listeners[event_id] = stop_event

        thread = threading.Thread(
            target=self._run_listener,
            args=(event, stop_event),
            daemon=True,
        )
        thread.start()

    def stop_listener(self, event_id: str) -> None:
        with self._lock:
            stop_event = self._listeners.pop(event_id, None)
        if stop_event:
            stop_event.set()

    # ==== 内部实现 ====
    def _run_listener(self, event: EventSpec, stop_event: threading.Event) -> None:
        if event.chain_type == "evm":
            self._run_evm_listener(event, stop_event)
        else:
            # Fabric 监听需要 SDK 支持，这里留出钩子
            while not stop_event.is_set():
                time.sleep(5)

    def _run_evm_listener(self, event: EventSpec, stop_event: threading.Event) -> None:
        contract_iface = self.storage.get_contract(event.contract_interface_id)
        if not contract_iface or not contract_iface.abi or not contract_iface.address:
            raise ValueError("contract interface missing ABI/address")
        if not event.rpc_url:
            raise ValueError("rpc_url required for evm listener")

        w3 = Web3(Web3.HTTPProvider(event.rpc_url))
        # 允许兼容 PoA 链
        try:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except ValueError:
            pass

        contract = w3.eth.contract(
            address=w3.to_checksum_address(contract_iface.address), abi=contract_iface.abi
        )
        evm_event = getattr(contract.events, event.event_name, None)
        if evm_event is None:
            raise ValueError(f"event {event.event_name} not found in ABI")

        from_block = event.start_block or w3.eth.block_number

        while not stop_event.is_set():
            latest = w3.eth.block_number
            target_block = latest - event.confirmations
            if target_block < from_block:
                time.sleep(event.poll_interval)
                continue
            try:
                logs = evm_event().get_logs(
                    fromBlock=from_block,
                    toBlock=target_block,
                    argument_filters=event.filter_args or None,
                )
                for log in logs:
                    payload = {
                        "args": dict(log["args"]),
                        "blockNumber": log["blockNumber"],
                        "transactionHash": log["transactionHash"].hex(),
                    }
                    self.storage.append_event_log(
                        {"event_id": event.id, "payload": payload}
                    )
                    self._maybe_callback(event, payload)
                from_block = target_block + 1
            except Exception as exc:  # pragma: no cover - 监控中容忍异常
                self.storage.append_event_log(
                    {
                        "event_id": event.id,
                        "payload": {"error": str(exc), "stage": "evm_listener"},
                    }
                )
                time.sleep(event.poll_interval)
            time.sleep(event.poll_interval)

    def _maybe_callback(self, event: EventSpec, payload: dict) -> None:
        if not event.callback_url:
            return
        try:
            requests.post(event.callback_url, json={"event_id": event.id, "payload": payload}, timeout=5)
        except requests.RequestException as exc:
            self.storage.append_event_log(
                {
                    "event_id": event.id,
                    "payload": {"error": f"callback failed: {exc}", "stage": "callback"},
                }
            )

