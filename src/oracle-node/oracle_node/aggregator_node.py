"""
轻量级 Oracle 节点示例：
- 支持注册数据源（本地配置），从数据源读取数值
- 为指定任务签名 (taskId, value) 并提交至 AggregatingOracle 合约

使用前请在 config.yml 中配置:
oracle:
  id: oracle-1
  private_key: 0x...
  rpc_url: http://127.0.0.1:8545
  contract_address: 0x...
data_sources:
  price_feed:
    type: mock
    value: 12345
  file_feed:
    type: file
    path: ./data/value.txt
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.middleware import geth_poa_middleware


@dataclass
class DataSource:
    name: str
    ds_type: str
    config: Dict[str, Any]

    def fetch(self) -> int:
        if self.ds_type == "mock":
            return int(self.config["value"])
        if self.ds_type == "file":
            path = Path(self.config["path"])
            return int(path.read_text().strip())
        raise ValueError(f"unsupported data source type: {self.ds_type}")


class OracleNode:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        oracle_cfg = cfg["oracle"]
        self.account = Account.from_key(oracle_cfg["private_key"])
        self.w3 = Web3(Web3.HTTPProvider(oracle_cfg["rpc_url"]))
        try:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except ValueError:
            pass

        # 聚合 Oracle 的最小 ABI，只保留 submitData 接口
        abi = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "taskId", "type": "uint256"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "name": "submitData",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(oracle_cfg["contract_address"]), abi=abi
        )
        self.sources = self._load_sources(cfg.get("data_sources", {}))

    def _load_sources(self, ds_cfg: dict) -> Dict[str, DataSource]:
        sources = {}
        for name, conf in ds_cfg.items():
            sources[name] = DataSource(name=name, ds_type=conf["type"], config=conf)
        return sources

    def sign_value(self, task_id: int, value: int) -> bytes:
        digest = Web3.solidity_keccak(["uint256", "uint256"], [task_id, value])
        msg = encode_defunct(hexstr=digest.hex())
        signed = self.account.sign_message(msg)
        return signed.signature

    def submit_value(self, task_id: int, value: int) -> str:
        signature = self.sign_value(task_id, value)
        tx = self.contract.functions.submitData(task_id, value, signature).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 500_000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def run_once(self, task_id: int, source_name: str):
        if source_name not in self.sources:
            raise KeyError(f"data source {source_name} not found")
        value = self.sources[source_name].fetch()
        tx_hash = self.submit_value(task_id, value)
        print(f"[oracle] task={task_id} value={value} tx={tx_hash}")


def load_config(path: str = "config.yml") -> dict:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="Aggregator Oracle Node")
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--source", required=True, help="data source name")
    args = parser.parse_args()

    cfg = load_config(args.config)
    node = OracleNode(cfg)
    node.run_once(args.task_id, args.source)
