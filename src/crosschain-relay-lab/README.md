# Crosschain Relay Lab

这个实验工程用于验证两类能力：
- 跨链中继合约（每条链部署一个 `CrossChainEndpoint`）
- 链下中继节点（监听源链事件，在目标链执行消息）

并提供可复现实验：
- 双向消息转发（A->B / B->A）
- 两类任务负载（`data` 与 `compute`）
- 工业物联网闭环（遥测跨链 + 维护决策跨链回传）
- 指标采集（延迟、send gas、execute gas、总 gas）
- 幂等性验证（重复执行应被拒绝）

## 目录结构

- `contracts/CrossChainEndpoint.sol`
  - 跨链入口合约
  - 发送端：`sendMessage()` 发事件
  - 执行端：`executeMessage()` 由 relayer 调用
  - 内置 `executed[msgId]` 防重放
- `contracts/RelayTaskReceiver.sol`
  - 示例业务合约
  - `handleDataTask(...)`
  - `handleComputeTask(...)`
- `relay-server/index.js`
  - 链下中继服务
  - 监听两条链的 `RelayRequested`
  - 自动投递到目标链 `executeMessage`
  - 带重试与状态接口
- `experiments/run-experiment.js`
  - 自动发送多轮跨链任务并输出报告
- `experiments/run-iiot-experiment.js`
  - 工业物联网实验：设备遥测从链 A 到链 B，链 B 形成维护决策回传链 A

## 依赖

- Node.js >= 18
- Foundry `anvil`

## 快速开始

```bash
cd /home/logres/system/src/crosschain-relay-lab
npm install
npm run anvil:up
npm run deploy
```

启动中继服务：

```bash
npm run relay
```

查看状态：

```bash
curl http://127.0.0.1:18888/health
curl http://127.0.0.1:18888/metrics
curl http://127.0.0.1:18888/queue
```

## 一键实验

实验脚本会自动拉起中继进程并执行多轮任务：

```bash
cd /home/logres/system/src/crosschain-relay-lab
npm run experiment
```

输出：

- `deployments/relay-experiment-report.json`

工业物联网实验：

```bash
cd /home/logres/system/src/crosschain-relay-lab
npm run experiment:iiot
```

输出：

- `deployments/iiot-relay-experiment-report.json`

报告包括：
- `avgSendGas`
- `avgExecuteGas`
- `avgTotalGas`
- `avgLatencyMs`
- `p95LatencyMs`
- `replayProtectionWorks`
- `decisionConsistency`（工业物联网闭环的一致性）

架构图见：`ARCHITECTURE.md`
实验设计见：`EXPERIMENT_DESIGN.md`

## 环境变量

- `CHAIN_A_RPC` 默认 `http://127.0.0.1:8545`
- `CHAIN_B_RPC` 默认 `http://127.0.0.1:9545`
- `RELAYER_PORT` 默认 `18888`
- `RELAYER_POLL_MS` 默认 `1500`
- `RELAYER_MAX_RETRIES` 默认 `8`
- `RELAYER_EXEC_GAS_LIMIT` 默认 `1500000`
- `RELAY_EXPERIMENT_ROUNDS` 默认 `10`

## 清理

```bash
npm run anvil:down
```
