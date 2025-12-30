from __future__ import annotations

import threading
import time
from typing import Dict

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.middleware import geth_poa_middleware

from .models import ComputeWatcher
from .storage import Storage


class ComputeWatcherManager:
    """拉取链上计算任务并执行的管理器。"""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self._watchers: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start(self, watcher_id: str) -> None:
        watcher = self.storage.get_compute_watcher(watcher_id)
        if not watcher:
            raise ValueError(f"watcher {watcher_id} not found")
        with self._lock:
            if watcher_id in self._watchers:
                return
            stop_event = threading.Event()
            self._watchers[watcher_id] = stop_event

        thread = threading.Thread(
            target=self._run_watcher,
            args=(watcher, stop_event),
            daemon=True,
        )
        thread.start()

    def stop(self, watcher_id: str) -> None:
        with self._lock:
            stop_event = self._watchers.pop(watcher_id, None)
        if stop_event:
            stop_event.set()

    def _run_watcher(self, watcher: ComputeWatcher, stop_event: threading.Event) -> None:
        identity = self.storage.get_identity(watcher.identity_id)
        if not identity:
            raise ValueError("identity not found")
        if identity.chain_type != "evm":
            raise ValueError("compute watcher requires evm identity")
        w3 = Web3(Web3.HTTPProvider(identity.rpc_url))
        try:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except ValueError:
            pass
        acct = Account.from_key(identity.private_key)
        contract = w3.eth.contract(
            address=w3.to_checksum_address(watcher.contract_address),
            abi=_unified_oracle_abi(),
        )

        processed = set()
        while not stop_event.is_set():
            try:
                next_id = contract.functions.nextComputeTaskId().call()
                for task_id in range(next_id):
                    if task_id in processed:
                        continue
                    task = contract.functions.getComputeTask(task_id).call()
                    requester, compute_type, payload_hash, threshold, finished, final_result = task
                    if finished:
                        processed.add(task_id)
                        continue
                    allowed = contract.functions.isComputeOracleAllowed(
                        task_id, acct.address
                    ).call()
                    if not allowed:
                        continue

                    result = _compute_result(
                        compute_type, payload_hash, watcher.compute_profiles
                    )
                    tx_hash = _submit_compute(
                        w3,
                        contract,
                        acct,
                        task_id,
                        payload_hash,
                        result,
                    )
                    processed.add(task_id)
                    self.storage.append_compute_log(
                        {
                            "watcher_id": watcher.id,
                            "task_id": int(task_id),
                            "compute_type": _as_hex(compute_type),
                            "payload_hash": _as_hex(payload_hash),
                            "result": _as_hex(result),
                            "tx_hash": tx_hash,
                            "status": "submitted",
                        }
                    )
            except Exception as exc:
                self.storage.append_compute_log(
                    {
                        "watcher_id": watcher.id,
                        "task_id": -1,
                        "compute_type": "",
                        "payload_hash": "",
                        "result": "",
                        "status": "error",
                        "error": str(exc),
                    }
                )
                time.sleep(watcher.poll_interval)
            time.sleep(watcher.poll_interval)


def _compute_result(
    compute_type: bytes, payload_hash: bytes, profiles: dict
) -> bytes:
    # compute_type/payload_hash 是 bytes32
    compute_key = _as_hex(compute_type)
    profile = profiles.get(compute_key) or profiles.get("default") or {}
    mode = profile.get("mode", "hash_payload")
    value = profile.get("value", "")

    if mode == "static":
        if isinstance(value, str) and value.startswith("0x") and len(value) == 66:
            return bytes.fromhex(value[2:])
        return Web3.keccak(text=str(value))
    if mode == "hash_payload":
        return Web3.keccak(payload_hash)
    # 默认：对 compute_type 与 payload_hash 做一次哈希
    return Web3.solidity_keccak(["bytes32", "bytes32"], [compute_type, payload_hash])


def _submit_compute(
    w3: Web3,
    contract,
    acct,
    task_id: int,
    payload_hash: bytes,
    result: bytes,
) -> str:
    digest = Web3.solidity_keccak(
        ["uint256", "bytes32", "bytes32"],
        [task_id, payload_hash, result],
    )
    msg = encode_defunct(hexstr=digest.hex())
    signed = acct.sign_message(msg)
    tx = contract.functions.submitComputeResult(
        task_id, result, signed.signature
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 800_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed_tx = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()


def _unified_oracle_abi() -> list:
    return [
        {
            "inputs": [],
            "name": "nextComputeTaskId",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "taskId", "type": "uint256"}],
            "name": "getComputeTask",
            "outputs": [
                {"internalType": "address", "name": "requester", "type": "address"},
                {"internalType": "bytes32", "name": "computeType", "type": "bytes32"},
                {"internalType": "bytes32", "name": "payloadHash", "type": "bytes32"},
                {"internalType": "uint256", "name": "threshold", "type": "uint256"},
                {"internalType": "bool", "name": "finished", "type": "bool"},
                {"internalType": "bytes32", "name": "finalResult", "type": "bytes32"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "taskId", "type": "uint256"},
                {"internalType": "address", "name": "oracle", "type": "address"},
            ],
            "name": "isComputeOracleAllowed",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "taskId", "type": "uint256"},
                {"internalType": "bytes32", "name": "result", "type": "bytes32"},
                {"internalType": "bytes", "name": "signature", "type": "bytes"},
            ],
            "name": "submitComputeResult",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]


def _as_hex(value: bytes) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    return str(value)
