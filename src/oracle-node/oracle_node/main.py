# main.py
import yaml
import json

from onchain.evm_adapter import EVMOracleClient
from onchain.fabric_adapter import FabricOracleClient  # 如暂时不用，可以先不导入

ORACLE_CONTRACT_ABI = [
    # ... 填入 SimpleMultiOracle 的 ABI ...
]

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_config()

    # 启动 EVM Oracle 节点
    evm_cfg = cfg.get("evm", {})
    evm_client = EVMOracleClient(
        rpc_url=evm_cfg["rpc_url"],
        private_key=evm_cfg["private_key"],
        contract_address=evm_cfg["oracle_contract_address"],
        abi=ORACLE_CONTRACT_ABI,
    )

    # 如果要同时支持 Fabric，可以再启一个线程/进程跑 FabricOracleClient.loop_poll_tasks
    fabric_cfg = cfg.get("fabric", {})
    fabric_enabled = fabric_cfg.get("enabled", False)

    if fabric_enabled:
        # TODO: 初始化 Fabric 客户端
        fabric_client = FabricOracleClient(
            connection_profile=fabric_cfg["connection_profile"],
            wallet_path=fabric_cfg["wallet_path"],
            identity=fabric_cfg["identity"],
            channel_name=fabric_cfg["channel_name"],
            chaincode_name=fabric_cfg["chaincode_name"],
            oracle_id=cfg["oracle"]["id"],
        )
        # 简单用多线程并行处理
        import threading
        t_fabric = threading.Thread(
            target=fabric_client.loop_poll_tasks,
            kwargs={"poll_interval": cfg["oracle"]["poll_interval_seconds"]},
            daemon=True,
        )
        t_fabric.start()

    # 主线程跑 EVM 轮询
    evm_client.loop_poll_tasks(poll_interval=cfg["oracle"]["poll_interval_seconds"])


if __name__ == "__main__":
    main()
