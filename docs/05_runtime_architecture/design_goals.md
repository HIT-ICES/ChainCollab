# 5.1 Design Goals

## 1. 支持多链运行

同一 BPMN/DMN 模型经过 `B2CDSL` 转换后，会生成：

- Fabric Go chaincode
- Solidity contract

因此运行架构必须允许：

- 在 Fabric 上部署并执行 Go chaincode；
- 在 Geth/EVM 上部署并执行 Solidity contract；
- 用统一方式驱动两类实现。

## 2. 屏蔽平台调用差异

Fabric 与 Geth 的调用机制并不一致：

- Fabric 偏向 `chaincode invoke/query`
- Geth 偏向 `contract transaction/call`

上层实验驱动、运行验证和前端执行视图，不应直接依赖这两套差异化接口。  
因此系统需要一个统一接入层，把“业务操作”稳定映射到不同链平台的调用方式。

仓库中的直接证据包括：

- `src/front/src/api/executionAPI.ts`
  - 无论消息、网关、事件还是 BusinessRule，前端都走统一的 FireFly API 形式：
  - `/api/v1/namespaces/default/apis/<contract>/invoke/<method>`

## 3. 支撑事件观测与运行轨迹生成

第 6 章要比较三类轨迹：

- DSL reference trace
- Fabric runtime trace
- Geth runtime trace

因此运行层不仅要能“调用”，还必须能“观测”：

- 交易提交结果
- 事件日志
- 业务操作执行状态
- 可查询的运行态快照
- 决策请求和决策返回结果

仓库中的证据包括：

- `Experiment/NoiseExperiment` 中保存了 FireFly/Fabric 的调用与事件记录；
- Solidity 生成合约中保留了 `MessageSent`、`BusinessRuleRequested`、`BusinessRuleCompleted` 等事件；
- Solidity 合约还提供 `getExecutionSnapshot()` 这类面向状态观测的接口。

## 4. 支撑 Geth 侧链下 DMN 调用

Solidity 合约不适合直接承载复杂 DMN 规则执行。  
因此运行架构必须把 Geth 侧 BusinessRuleTask 的执行拆成：

1. 链上发起决策请求；
2. 链下 DMN Service 执行决策；
3. 通过 Chainlink 回写结果；
4. 合约继续推进后续流程。

仓库中的证据包括：

- `src/oracle-node/CHAINLINK/features/02-single-node-dmn`
- `src/oracle-node/CHAINLINK/features/04-dmn-ocr`
- `docs/06_code_generation/solidity/generated_contract_example.sol`

## 5. 统一可追踪

运行架构中的操作、事件、状态快照，必须还能追溯回 DSL 元素。  
这也是为什么生成代码里保留了稳定命名：

- `Message_...`
- `Gateway_...`
- `Event_...`
- `Activity_...`

这使 FireFly 层捕获的原始运行记录，能够被稳定映射回：

- DSL operation id
- participant
- message / gateway / event / businessrule

## 6. 设计目标总结

第 5 章只需要围绕以下四个目标展开即可：

1. 让 Fabric 与 Geth 都能执行同源流程生成结果。
2. 用 FireFly 统一业务调用入口。
3. 用 FireFly 提供事件观测与记录来源。
4. 用 Chainlink + DMN Service 补足 Geth 侧复杂决策执行能力。
