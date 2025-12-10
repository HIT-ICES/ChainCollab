# onchain/fabric_adapter.py
import json
from typing import Any
from compute import compute_deterministic

class FabricOracleClient:
    """
    这里只给一个接口骨架，具体实现需根据你选择的 Python Fabric SDK 来填。
    一般步骤：
    1. 通过 Gateway/SDK 连接 Fabric 网络
    2. 调用链码函数 CreateTask / SubmitResult / ReadTask
    """

    def __init__(self, connection_profile: str, wallet_path: str,
                 identity: str, channel_name: str, chaincode_name: str, oracle_id: str):
        self.connection_profile = connection_profile
        self.wallet_path = wallet_path
        self.identity = identity
        self.channel_name = channel_name
        self.chaincode_name = chaincode_name
        self.oracle_id = oracle_id

        # TOD: 初始化 Fabric 网关 / 网络 / 合约对象

    def get_task_ids(self) -> list[str]:
        """
        你可以设计一个链码函数列出所有 taskId，或者在客户端自己维护列表。
        这里先留个接口。
        """
        raise NotImplementedError

    def read_task(self, task_id: str) -> dict[str, Any]:
        """
        调用链码 ReadTask 返回 JSON 字符串，再转为 dict。
        """
        raise NotImplementedError

    def submit_result(self, task_id: str, result_bytes: bytes) -> Any:
        """
        调用链码 SubmitResult(taskId, oracleId, resultString)。
        """
        result_str = result_bytes.decode("utf-8")
        # TOD: 实际调用 Fabric 合约
        raise NotImplementedError

    def process_task(self, task_id: str):
        task = self.read_task(task_id)
        if task["Finished"]:
            print(f"[Fabric] Task {task_id} already finished, skip")
            return

        params_str = task["Params"]
        params_bytes = params_str.encode("utf-8")

        result_bytes = compute_deterministic(params_bytes)
        self.submit_result(task_id, result_bytes)

    def loop_poll_tasks(self, poll_interval: int = 5):
        import time
        processed = set()
        while True:
            try:
                task_ids = self.get_task_ids()
                for tid in task_ids:
                    if tid in processed:
                        continue
                    self.process_task(tid)
                    processed.add(tid)
            except Exception as e:
                print(f"[Fabric] Error while polling tasks: {e}")
            time.sleep(poll_interval)
