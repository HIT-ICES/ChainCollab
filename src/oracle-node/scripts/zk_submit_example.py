"""
ZK 结果提交流程示例：

依赖：
  pip install -r src/oracle-node/requirements.txt

示例运行：
  python scripts/zk_submit_example.py \\
    --rpc-url http://127.0.0.1:8545 \\
    --oracle-contract 0xOracleContract \\
    --verifier-contract 0xVerifierContract \\
    --task-id 0 \\
    --private-key 0xabc...

脚本会读取 scripts/zk_sample/proof.json & public.json（由 snarkjs 生成的示例），
并调用合约的 submitZKResult。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

ABI_PATH = Path(__file__).resolve().parents[1] / "contracts" / "solidity" / "legacy" / "SimpleMultiOracle.abi.json"
PROOF_PATH = Path(__file__).resolve().parent / "zk_sample" / "proof.json"
PUBLIC_PATH = Path(__file__).resolve().parent / "zk_sample" / "public.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_proof(raw: dict):
    a = [int(raw["pi_a"][0]), int(raw["pi_a"][1])]
    b = [
        [int(raw["pi_b"][0][0]), int(raw["pi_b"][0][1])],
        [int(raw["pi_b"][1][0]), int(raw["pi_b"][1][1])],
    ]
    c = [int(raw["pi_c"][0]), int(raw["pi_c"][1])]
    return a, b, c


def main() -> None:
    parser = argparse.ArgumentParser(description="提交 Groth16 ZK 结果示例")
    parser.add_argument("--rpc-url", required=True)
    parser.add_argument("--oracle-contract", required=True)
    parser.add_argument("--verifier-contract", required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--private-key", required=True, help="Oracle 节点私钥")
    args = parser.parse_args()

    proof = load_json(PROOF_PATH)
    public_signals: List[int] = [int(x) for x in load_json(PUBLIC_PATH)]
    proofA, proofB, proofC = parse_proof(proof)

    w3 = Web3(Web3.HTTPProvider(args.rpc_url))
    acct: LocalAccount = Account.from_key(args.private_key)

    abi = load_json(ABI_PATH)
    contract = w3.eth.contract(address=w3.to_checksum_address(args.oracle_contract), abi=abi)

    # 将公开信号中的输出转换成 bytes (uint256 -> bytes32)
    output_bytes = public_signals[0].to_bytes(32, "big")

    tx = contract.functions.submitZKResult(
        args.task_id,
        output_bytes,
        proofA,
        proofB,
        proofC,
        public_signals,
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 1_200_000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"submitted tx: {tx_hash.hex()}")


if __name__ == "__main__":
    main()
