# Crosschain Relayer Experiment Design

## 1. 为什么有跨链需求（问题定义）

跨链不是“可选功能”，而是多链现实下的基础能力。典型刚需来自三类业务：

1. 资产跨链流转与流动性管理
- 代表场景：USDC 在多链之间原生流转、做市商/交易所跨链再平衡。
- 现实依据：Circle CCTP 将“跨链消息 + 铸销”作为标准流程，并明确用于 rebalancing、swap、支付编排等。

2. 跨链消息驱动的业务编排
- 代表场景：链 A 发起一条业务消息，在链 B 执行合约动作（不仅仅是转账）。
- 现实依据：LayerZero/CCIP 都强调通用消息（generic messaging）+ 目标链业务执行（programmable action）。

3. 多链应用的统一用户体验
- 代表场景：用户不关心“在哪条链执行”，系统自动完成跨链动作并反馈结果。
- 现实依据：Ethereum 基金会近期也将互操作性作为 UX 核心方向之一（跨 L2 感知“像一条链”）。

## 2. 研究目标（面向你的 relayer 体系）

本实验关注以下四个问题：

- RQ1 正确性：是否能保证“至多一次执行 + 最终可达”？
- RQ2 性能：跨链时延分布（avg/p95）与吞吐的关系？
- RQ3 成本：源链发送 + 目标链执行的 gas 成本构成？
- RQ4 鲁棒性：在重复事件、乱序、目标链失败、relayer 重启下是否稳定？

## 3. 现有系统映射（已实现）

当前 `crosschain-relay-lab` 已具备：

- 合约层：
  - `CrossChainEndpoint`（消息发起/执行、目标白名单、`executed[msgId]` 防重放）
  - `RelayTaskReceiver`（数据任务 + 计算任务）
  - `IndustrialIoTReceiver`（工业场景：遥测入链 + 维护决策回传）
- 链下层：
  - `relay-server/index.js`（监听、排队、重试、转发、状态接口）
- 实验层：
  - `experiments/run-experiment.js`（双向任务、gas/latency、重放防护验证）
  - `experiments/run-iiot-experiment.js`（工业物联网闭环实验）

因此你现在已经有“可跑的 baseline”，可直接扩展为论文级实验矩阵。

## 4. 实验案例矩阵（建议）

### Case A: Baseline 双向跨链业务（已实现）

目的：验证基本可用性与开销。

- 负载：`data` + `compute` 混合，A->B / B->A 交替。
- 指标：
  - `avgSendGas`, `avgExecuteGas`, `avgTotalGas`
  - `avgLatencyMs`, `p95LatencyMs`
  - 成功率（执行成功数/总消息数）
- 判据：
  - 成功率 100%
  - `replayProtectionWorks=true`

### Case B: 重复事件/重复提交鲁棒性

目的：验证“重复消息不会重复执行”。

- 方法：对同一 `msgId` 重放 `executeMessage`。
- 指标：
  - 重放拒绝率（应为 100%）
  - 非重复消息误拒率（应接近 0）
- 判据：
  - 所有重复提交均被拒绝

### Case C: 目标链业务失败恢复

目的：验证业务合约 revert 时 relayer 行为。

- 方法：构造非法 payload（如 `div` 且除数为 0）触发 `handleComputeTask` revert。
- 指标：
  - 失败任务占比
  - 平均重试次数
  - 最大重试延迟
- 判据：
  - 失败被记录，不影响后续队列继续处理

### Case D: Relayer 故障恢复（中断/重启）

目的：验证链下服务可恢复性。

- 方法：发送消息后停掉 relayer，积压一段时间后重启。
- 指标：
  - backlog 清空时间
  - 恢复后成功率
  - 重复执行数（应为 0）
- 判据：
  - 恢复后最终一致，且无重复执行

### Case E: 成本-负载曲线

目的：在不同负载下观察 gas 与时延变化。

- 方法：轮数从 `N=10/50/100/500`，任务类型比例从 `data:compute=9:1, 5:5, 1:9`。
- 指标：
  - 单消息 gas
  - 端到端延迟分位数
  - 每分钟处理量
- 判据：
  - 成本/延迟曲线可复现，能支持参数调优

### Case F: 工业物联网闭环（重点，已实现）

目的：模拟产线遥测跨链上报与维护决策跨链回传。

- 流程：
  - 链 A（Edge/Shopfloor）发送遥测消息到链 B（Ops/MES）。
  - 链 B 计算风险分数并形成维护决策。
  - 决策再由链 B 回传到链 A，形成闭环。
- 负载：
  - 遥测字段：`temperatureMilliC / vibrationUm / pressureKpa`
  - 设备字段：`deviceId / lineId / sampleTs`
  - 决策字段：`NORMAL / INSPECT / SCHEDULE_MAINTENANCE / EMERGENCY_STOP`
- 指标：
  - `avgTelemetryLatencyMs`, `p95TelemetryLatencyMs`
  - `avgDecisionLatencyMs`, `p95DecisionLatencyMs`
  - `avgCycleLatencyMs`, `p95CycleLatencyMs`
  - `avgTelemetryGas`, `avgDecisionGas`, `avgTotalGasPerCycle`
  - `decisionConsistency`, `replayProtectionWorks`
- 判据：
  - 决策一致性为真（回传决策与目标链决策一致）
  - 防重放有效
  - 端到端闭环时延可稳定复现

工程注意：
- 对 `executeMessage` 不能依赖默认 gas 估算。若目标调用失败但 `executeMessage` 本身不 revert，估算可能偏低并导致“交易成功但业务失败（ok=false）”。
- 解决：relayer 固定设置 `RELAYER_EXEC_GAS_LIMIT`，并强制校验 `RelayExecuted.ok`，失败则重试。

## 5. 工业物联网故事线（优先）

建议把论文/报告主线聚焦在“跨域制造协同”：

1. Shopfloor 与 Ops 分域
- 设备侧链（A）负责高频事件与原始遥测锚定；
- 运维侧链（B）负责策略计算与维护工单决策。

2. 遥测与决策分离
- 数据跨链：保证多方可验证且可追溯；
- 决策跨链：保证闭环执行可审计。

3. 故障注入验证工程可用性
- 链下 relayer 重启、消息重放、无效 payload、高负载压测。
- 观察是否“最终一致 + 不重复执行 + 可恢复”。

对应脚本：
- `npm run experiment:iiot`

## 6. 其他业务故事线（可选）

为避免实验“只测框架”，建议绑定业务语义：

1. 资金跨链再平衡（Data Task）
- 源链触发“库存不足”消息，目标链写入最新补仓数据（如库存阈值、补仓量）。

2. 风险计算跨链请求（Compute Task）
- 源链发送风险参数，目标链执行计算（`add/sub/mul/div/pow2sum`），再由目标链状态反哺上层流程。

3. 业务编排（Message + Action）
- 一笔跨链消息不仅传值，还触发目标链合约动作（你现在这套 payload 调用正是该模式）。

## 7. 结果记录模板

建议每次实验统一落地以下字段：

- 基本信息：
  - git commit
  - 时间戳
  - 链配置（chainId、RPC）
  - relayer 参数（poll/retry）
- 输入：
  - rounds
  - 任务比例
  - 注入故障类型
- 输出：
  - 成功率、失败率
  - avg/p95 latency
  - avg send/execute/total gas
  - replay 检查结果
  - 队列峰值、恢复时长

## 8. 下一步扩展（对接你的主项目）

- 增加 ack 回传通道（目标链执行后回执源链）
- 增加多 relayer 竞争与 leader/去重策略实验
- 增加最终性等待策略（按链类型动态确认块数）
- 将实验报告接入 backend task 体系，前端直接可视化比较实验组

## 9. 参考资料（官方/论文）

1. Circle CCTP Technical Guide
- https://developers.circle.com/cctp/technical-guide

2. Circle CCTP Overview
- https://developers.circle.com/cctp/v1

3. Cosmos IBC Transfer (ICS-20) Overview
- https://docs.cosmos.network/ibc/next/apps/transfer/overview

4. LayerZero: What is LayerZero / Architecture
- https://docs.layerzero.network/v2/concepts/getting-started/what-is-layerzero
- https://docs.layerzero.network/v2/concepts/layerzero-protocol-architecture

5. Ethereum Foundation (Interoperability UX direction)
- https://blog.ethereum.org/en/2025/11/18/eil

6. SoK: Communication Across Distributed Ledgers
- https://eprint.iacr.org/2019/1128

7. NIST SP 800-82 Rev.3 (Industrial Control Systems Security)
- https://csrc.nist.gov/pubs/sp/800/82/r3/final

8. Industrial Internet Consortium - IIRA
- https://www.iiconsortium.org/IIRA.htm

9. OPC Foundation - OPC UA
- https://opcfoundation.org/about/opc-technologies/opc-ua/
