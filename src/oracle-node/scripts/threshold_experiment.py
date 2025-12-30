"""
Threshold 签名实验脚本：
1. 读取多份私钥，生成与合约保持一致的签名（keccak(taskId||result) + 以太坊签名前缀）
2. 可选：调用 submitThresholdResult 将批量签名一次性提交链上

运行示例：
python scripts/threshold_experiment.py \\
  --rpc-url http://127.0.0.1:8545 \\
  --contract 0xOracleContract \\
  --abi-file ../contracts/solidity/legacy/SimpleMultiOracle.abi.json \\
  --task-id 0 \\
  --result-text "demo-result" \\
  --private-keys pk1,pk2,pk3 \\
  --submit
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence

from eth_account import Account
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from web3 import Web3


def _load_abi(path: Path) -> list:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _compute_digest(task_id: int, result_bytes: bytes) -> bytes:
    return Web3.solidity_keccak(["uint256", "bytes"], [task_id, result_bytes])


def _signers_from_keys(private_keys: Sequence[str]) -> List[Account]:
    return [Account.from_key(pk) for pk in private_keys]


def _build_signatures(
    accounts: Sequence[Account], digest: bytes
) -> tuple[List[str], List[bytes]]:
    message = encode_defunct(hexstr=digest.hex())
    signers: List[str] = []
    signatures: List[bytes] = []
    for acc in accounts:
        signed = Account.sign_message(message, private_key=acc.key)
        signers.append(acc.address)
        signatures.append(signed.signature)
    return signers, signatures


def _submit(
    rpc_url: str,
    contract_address: str,
    abi_file: Path,
    submitter_key: str,
    task_id: int,
    result_bytes: bytes,
    signatures: Sequence[bytes],
    signers: Sequence[str],
) -> str:
    abi = _load_abi(abi_file)
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = Account.from_key(submitter_key)
    contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi)
    tx = contract.functions.submitThresholdResult(
        task_id,
        result_bytes,
        signatures,
        signers,
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 1_000_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()


def main() -> None:
    parser = argparse.ArgumentParser(description="阈值签名实验工具")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--result-text", type=str, help="直接传入字符串结果")
    parser.add_argument("--result-hex", type=str, help="0x 开头的十六进制结果数据")
    parser.add_argument("--result-file", type=Path, help="从文件读取字节结果")
    parser.add_argument("--private-keys", type=str, required=True, help="逗号分隔的私钥列表")
    parser.add_argument("--rpc-url", type=str, help="提交链上所需的 RPC")
    parser.add_argument("--contract", type=str, help="合约地址")
    parser.add_argument(
        "--abi-file",
        type=Path,
        default=Path("../contracts/solidity/legacy/SimpleMultiOracle.abi.json"),
        help="ABI 文件路径",
    )
    parser.add_argument("--submit", action="store_true", help="是否直接提交链上")
    parser.add_argument(
        "--submitter-key",
        type=str,
        help="用于发送交易的私钥（默认第一个 oracle 私钥）",
    )

    args = parser.parse_args()

    if args.result_text:
        result_bytes = args.result_text.encode("utf-8")
    elif args.result_hex:
        result_bytes = HexBytes(args.result_hex)
    elif args.result_file:
        result_bytes = args.result_file.read_bytes()
    else:
        raise SystemExit("必须提供 result-text/result-hex/result-file 之一")

    private_keys = [pk.strip() for pk in args.private_keys.split(",") if pk.strip()]
    if not private_keys:
        raise SystemExit("未提供有效私钥")

    accounts = _signers_from_keys(private_keys)
    digest = _compute_digest(args.task_id, result_bytes)
    signers, signatures = _build_signatures(accounts, digest)

    print("=== 签名结果 ===")
    print(f"digest = {digest.hex()}")
    for addr, sig in zip(signers, signatures):
        print(f"Signer {addr}: {sig.hex()}")

    if args.submit:
        if not args.rpc_url or not args.contract:
            raise SystemExit("submit 模式需要同时提供 --rpc-url 与 --contract")
        submitter = args.submitter_key or private_keys[0]
        tx_hash = _submit(
            rpc_url=args.rpc_url,
            contract_address=args.contract,
            abi_file=args.abi_file,
            submitter_key=submitter,
            task_id=args.task_id,
            result_bytes=result_bytes,
            signatures=signatures,
            signers=signers,
        )
        print(f"提交完成，交易哈希: {tx_hash}")


if __name__ == "__main__":
    main()
