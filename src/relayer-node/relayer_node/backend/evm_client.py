from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode as abi_encode
from web3 import Web3


ADAPTER_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"indexed": True, "internalType": "uint64", "name": "srcChainId", "type": "uint64"},
            {"indexed": True, "internalType": "uint64", "name": "dstChainId", "type": "uint64"},
            {"indexed": False, "internalType": "address", "name": "target", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "success", "type": "bool"},
            {"indexed": False, "internalType": "bytes", "name": "returnData", "type": "bytes"},
        ],
        "name": "CrossChainCallReceived",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint64", "name": "srcChainId", "type": "uint64"},
            {"indexed": True, "internalType": "uint64", "name": "dstChainId", "type": "uint64"},
            {"indexed": False, "internalType": "uint64", "name": "nonce", "type": "uint64"},
            {"indexed": False, "internalType": "address", "name": "target", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"},
            {"indexed": False, "internalType": "bytes", "name": "callData", "type": "bytes"},
        ],
        "name": "XCallRequested",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "uint64", "name": "srcChainId", "type": "uint64"},
            {"internalType": "uint64", "name": "dstChainId", "type": "uint64"},
            {"internalType": "uint64", "name": "nonce", "type": "uint64"},
            {"internalType": "address", "name": "target", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "bytes", "name": "callData", "type": "bytes"},
            {"internalType": "bytes[]", "name": "signatures", "type": "bytes[]"},
        ],
        "name": "receiveCrossChainCall",
        "outputs": [
            {"internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"internalType": "bool", "name": "success", "type": "bool"},
            {"internalType": "bytes", "name": "returnData", "type": "bytes"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "messageId", "type": "bytes32"}],
        "name": "getResult",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"},
            {"internalType": "bytes", "name": "", "type": "bytes"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class EVMIdentity:
    rpc_url: str
    private_key: Optional[str] = None
    address: Optional[str] = None


class EVMAdapterClient:
    def __init__(self, identity: EVMIdentity, adapter_address: str) -> None:
        self.identity = identity
        self.w3 = Web3(Web3.HTTPProvider(identity.rpc_url))
        self.adapter_address = Web3.to_checksum_address(adapter_address)
        self.contract = self.w3.eth.contract(address=self.adapter_address, abi=ADAPTER_ABI)
        if self.identity.private_key and not self.identity.address:
            self.identity.address = Account.from_key(identity.private_key).address

    def compute_message_id(
        self,
        src_chain_id: int,
        dst_chain_id: int,
        nonce: int,
        target: str,
        value: int,
        call_data: bytes,
    ) -> bytes:
        call_hash = Web3.keccak(call_data)
        return Web3.solidity_keccak(
            ["string", "address", "uint64", "uint64", "uint64", "address", "uint256", "bytes32"],
            [
                "XCALL",
                self.adapter_address,
                src_chain_id,
                dst_chain_id,
                nonce,
                Web3.to_checksum_address(target),
                value,
                call_hash,
            ],
        )

    def sign_message(self, message_id: bytes, signer_keys: List[str]) -> List[bytes]:
        signatures: List[bytes] = []
        for key in signer_keys:
            signed = Account.sign_message(encode_defunct(message_id), private_key=key)
            signatures.append(signed.signature)
        return signatures

    def send_receive_call(
        self,
        src_chain_id: int,
        dst_chain_id: int,
        nonce: int,
        target: str,
        value: int,
        call_data: bytes,
        signer_keys: List[str],
    ) -> Tuple[str, Optional[Tuple[bool, bytes]]]:
        if not self.identity.private_key or not self.identity.address:
            raise RuntimeError("evm identity missing private_key or address")
        message_id = self.compute_message_id(
            src_chain_id, dst_chain_id, nonce, target, value, call_data
        )
        signatures = self.sign_message(message_id, signer_keys)
        tx = self.contract.functions.receiveCrossChainCall(
            src_chain_id,
            dst_chain_id,
            nonce,
            Web3.to_checksum_address(target),
            value,
            call_data,
            signatures,
        ).build_transaction(
            {
                "from": self.identity.address,
                "nonce": self.w3.eth.get_transaction_count(self.identity.address),
            }
        )
        if "gas" not in tx:
            try:
                tx["gas"] = self.w3.eth.estimate_gas(tx)
            except Exception:
                tx["gas"] = 600000
        if "gasPrice" not in tx:
            tx["gasPrice"] = self.w3.eth.gas_price
        signed = Account.sign_transaction(tx, self.identity.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        result = None
        if receipt.status == 1:
            try:
                result = self.contract.functions.getResult(message_id).call()
            except Exception:
                result = None
        return tx_hash.hex(), result

    def build_result_call_data(self, signature: str, message_id: bytes, success: bool, return_data: bytes) -> bytes:
        fn_name = signature.split("(")[0]
        types = signature[signature.find("(") + 1 : signature.find(")")]
        arg_types = [t.strip() for t in types.split(",") if t.strip()] if types else []
        selector = Web3.keccak(text=signature)[:4]
        encoded = abi_encode(arg_types, [message_id, success, return_data]) if arg_types else b""
        return selector + encoded

    def get_event_logs(
        self,
        event_name: str,
        from_block: int,
        to_block: int,
    ) -> List[Dict[str, Any]]:
        event = getattr(self.contract.events, event_name, None)
        if event is None:
            return []
        return event().get_logs(fromBlock=from_block, toBlock=to_block)
