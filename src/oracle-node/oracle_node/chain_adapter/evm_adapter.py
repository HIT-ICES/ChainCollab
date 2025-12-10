# onchain/evm_adapter.py
import json
from typing import Callable, Any

from web3 import Web3
from web3.middleware import geth_poa_middleware

from compute import compute_deterministic

class EVMOracleClient:
    def __init__(self, rpc_url: str, private_key: str, contract_address: str, abi: list):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.account = self.w3.eth.account.from_key(private_key)
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(contract_address),
            abi=abi
        )

    def get_next_task_id(self) -> int:
        return self.contract.functions.nextTaskId().call()

    def get_task(self, task_id: int):
        # 对应 Solidity: getTask(taskId) returns (requester, params, finished, finalResult, deadline)
        return self.contract.functions.getTask(task_id).call()

    def submit_result(self, task_id: int, result_bytes: bytes) -> str:
        tx = self.contract.functions.submitResult(task_id, result_bytes).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 500000,
            "gasPrice": self.w3.eth.gas_price,
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def process_task(self, task_id: int):
        requester, params_bytes, finished, final_result_bytes, deadline = self.get_task(task_id)
        if finished:
            print(f"[EVM] Task {task_id} already finished, skip")
            return

        print(f"[EVM] Processing task {task_id}, params={params_bytes}")

        # 计算确定性结果
        result_bytes = compute_deterministic(params_bytes)

        # 提交结果
        tx_hash = self.submit_result(task_id, result_bytes)
        print(f"[EVM] Submitted result for task {task_id}, tx={tx_hash}")

    def loop_poll_tasks(self, poll_interval: int = 5):
        """
        简单轮询：假设任务 ID 从 0 到 nextTaskId-1 都是已创建任务，
        节点检查自己是否已经提交过（这部分可以通过合约接口增强，这里做简单示例）。
        实际可以通过事件订阅更优雅，这里用轮询便于演示。
        """
        import time
        processed = set()
        while True:
            try:
                current_next = self.get_next_task_id()
                for task_id in range(current_next):
                    if task_id in processed:
                        continue
                    # 这里简单假设本节点还没提交就处理一遍；真实情况应在合约中加“是否已响应”查询
                    self.process_task(task_id)
                    processed.add(task_id)
            except Exception as e:
                print(f"[EVM] Error while polling tasks: {e}")

            time.sleep(poll_interval)
