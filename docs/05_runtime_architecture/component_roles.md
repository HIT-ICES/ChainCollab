# 5.1 Component Roles

## 1. Fabric Runtime

角色：

- 执行由 `B2CDSL` 生成的 Go chaincode。
- 保存流程实例状态、消息状态、网关状态和业务规则状态。
- 通过 chaincode event 暴露运行事件。

本文实现关系：

- Go 代码由本文生成器产生。
- Fabric 平台本身是外部基础设施。

仓库证据：

- [generated_chaincode_example.go](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/fabric/generated_chaincode_example.go)
- `stub.SetEvent(...)`
- `ctx.GetStub().GetState(...)`
- `ctx.GetStub().PutState(...)`

## 2. Geth Runtime

角色：

- 执行由 `B2CDSL` 生成的 Solidity contract。
- 保存合约实例状态、消息状态和 BusinessRule 请求状态。
- 通过 Solidity event 暴露执行行为。

本文实现关系：

- Solidity 代码由本文生成器产生。
- Geth/EVM runtime 本身是外部基础设施。

仓库证据：

- [generated_contract_example.sol](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/solidity/generated_contract_example.sol)
- `event MessageSent(...)`
- `event BusinessRuleRequested(...)`
- `event BusinessRuleCompleted(...)`
- `function getExecutionSnapshot(...)`

## 3. FireFly Integration Layer

角色：

- 向上层暴露统一业务调用 API。
- 注册合约/链码接口。
- 订阅 Fabric 或 Ethereum 侧事件。
- 将底层平台差异收束成统一的调用与事件流。

本文实现关系：

- FireFly 本身是开源中间件。
- 本文工作体现在：
  - 生成可注册的 FFI / contract interface；
  - 统一方法命名；
  - 前端和实验脚本使用 FireFly API 调用与监听；
  - 事件可映射回 DSL 元素。

仓库证据：

- `src/front/src/api/executionAPI.ts`
- `src/front/src/views/BPMN/Translation/BpmnDetail/index.tsx`
- `Experiment/NoiseExperiment/main.py`
- `Experiment/NoiseExperiment/invoker.py`

## 4. Chainlink Adapter

角色：

- 作为 Geth 侧链下服务适配器。
- 把合约中的 DMN 决策请求转发给外部 DMN Service。
- 将结果回写到链上。
- 在扩展模式下还可支持 OCR 聚合。

本文实现关系：

- Chainlink 节点与 OCR 能力是开源组件。
- 本文贡献在于把其接入 BusinessRuleTask 运行链路。

仓库证据：

- `src/oracle-node/CHAINLINK/contracts/MyChainlinkRequesterDMN.sol`
- `src/oracle-node/CHAINLINK/features/02-single-node-dmn`
- `src/oracle-node/CHAINLINK/features/04-dmn-ocr`

## 5. DMN Service

角色：

- 解析 DMN XML。
- 根据 `decisionId` 和 `inputData` 执行决策。
- 返回 JSON 结果。
- 在 OCR 扩展模式中还承担缓存与按 hash 查询功能。

本文实现关系：

- 本文使用并封装了独立 DMN 决策服务。
- 其重点是为多链 BusinessRuleTask 提供可调用决策执行能力。

仓库证据：

- `src/oracle-node/CHAINLINK/features/02-single-node-dmn/dmn-server-java`
- `DMN_SERVICES_GUIDE.md`

## 6. Verification Component

角色：

- 不直接参与链上执行。
- 消费 FireFly 观测数据、链上事件和状态快照。
- 规范化为统一 runtime record。
- 与 DSL reference trace 做一致性比对。

本文实现关系：

- 这是第 6 章的核心消费者，而不是第 5 章的调用者。

## 7. 哪些是实现的，哪些是集成的

### 本文实现或主导整理

- B2CDSL 生成结果与命名约定
- 统一 FireFly 调用模型
- FireFly 监听注册逻辑
- Solidity 侧 `fireflyTranId` 和事件保留
- Geth 侧 BusinessRuleTask -> Chainlink -> DMN 的接入路径

### 开源组件配置集成

- Hyperledger Fabric
- Geth
- Hyperledger FireFly
- Chainlink
- Camunda DMN engine based service
