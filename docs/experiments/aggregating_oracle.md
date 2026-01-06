# 聚合型 Oracle 实验指南

本实验验证新合约 `AggregatingOracle.sol` 与链下节点 `oracle_node/aggregator_node.py` 的可靠性：只有合格签名的 Oracle 才能提交数据，聚合模式（均值、加权均值、强一致）按预期产出结果。

## 1. 准备
- 部署合约：`src/oracle-node/contracts/solidity/legacy/AggregatingOracle.sol`，记录合约地址。
- 为至少 3 个账户调用 `registerOracle`，确保 `active=true`。
- Python 依赖：`pip install -r src/oracle-node/requirements.txt web3 eth-account pyyaml`
- 配置文件示例（`src/oracle-node/config.yml`）：
```yaml
oracle:
  id: oracle-1
  private_key: 0x...
  rpc_url: http://127.0.0.1:8545
  contract_address: 0x...
data_sources:
  price_feed:
    type: mock
    value: 1200
  file_feed:
    type: file
    path: ./data/value.txt
```

## 2. 实验 A：均值模式 (MEAN)
1. `registerTask(dataType="PRICE", mode=MEAN, allowedOracles=[O1,O2,O3], weights=[], threshold=0)` → 获得 `taskId`。
2. 分别用三个节点运行：`python oracle_node/aggregator_node.py --task-id <taskId> --source price_feed`（每个节点配置不同私钥/数据源值）。
3. 观察事件 `TaskFinalized`，`finalValue` 应为三者均值。
4. 负例：未注册节点或重复提交 → 期望 revert/拒绝。

## 3. 实验 B：加权均值模式 (WEIGHTED_MEAN)
1. 以 `weights=[3,1,1]` 注册任务，其他同上。
2. 三节点提交数据后，`finalValue = (v1*3 + v2 + v3) / 5`。
3. 负例：不齐全提交（少于 allowedOracles 数）→ 不应 finalize。

## 4. 实验 C：强一致模式 (STRONG_CONSISTENCY)
1. 注册任务 `mode=STRONG_CONSISTENCY, threshold=2`。
2. 三节点中有至少两个返回相同值：提交后应直接 finalize 为该值。
3. 若没有值达到阈值，则任务保持未完成。

## 5. 签名校验与安全性
- 签名格式：`keccak256(abi.encodePacked(taskId, value))`，链下用 `eth_account` 签名，链上 `ecrecover` 校验。  
- 检查点：错误签名、篡改 value、未授权 oracle 均应失败；已提交的 oracle 再次提交会被拒绝。

## 6. 观察指标
- 成功/失败交易日志、`TaskFinalized` 事件。
- 聚合值与预期公式一致；强一致模式下的阈值行为。
- 性能可选：记录单次 `submitData` gas 开销，比较不同模式。

## 7. 清理与扩展
- 可将 data source 类型扩展为 HTTP/API（在 `aggregator_node.py` 中增加 `http` 分支）。  
- 可将合约扩展为滑动窗口或中位数等聚合策略，方式类似。  
