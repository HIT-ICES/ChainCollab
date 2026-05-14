# 5. Multi-Chain Runtime Architecture

本章关注的是运行支撑层，而不是模型转换或环境部署细节。  
目标是说明：同一份 `B2CDSL` 生成的 Fabric Go 链码和 Solidity 合约，如何在多链环境中被统一调用、统一观测，并进一步为第 6 章的一致性验证提供输入。

## 1. 总体思路

运行架构由五类核心组件组成：

- `Fabric Runtime`
  - 执行生成的 Go chaincode。
- `Geth Runtime`
  - 执行生成的 Solidity contract。
- `FireFly Integration Layer`
  - 为上层提供统一业务调用入口，并汇聚链上事件。
- `Chainlink Adapter`
  - 为 Geth 侧 BusinessRuleTask 提供链下 DMN 调用能力。
- `DMN Service`
  - 实际执行 DMN 决策逻辑。

统一后的运行记录进入：

- `Normalized Runtime Records`
- `Semantic Consistency Verification`

## 2. 与前面章节的关系

- 第 4 章说明如何把 BPMN/DMN 转成 `B2CDSL`。
- 第 5 章说明 `B2CDSL` 生成结果如何落地到多链运行环境。
- 第 6 章再基于这里产出的运行记录，做 DSL/Fabric/Geth 三方语义一致性比较。

## 3. 实际仓库中的对应实现

### Fabric 侧

- 生成链码与模板：
  - [generated_chaincode_example.go](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/fabric/generated_chaincode_example.go)
- FireFly 统一调用与监听样例：
  - `Experiment/NoiseExperiment`
  - `src/front/src/api/executionAPI.ts`

### Geth 侧

- 生成合约与模板：
  - [generated_contract_example.sol](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/solidity/generated_contract_example.sol)
- FireFly Ethereum 注册与监听代码：
  - `src/front/src/api/executionAPI.ts`
  - `src/front/src/views/BPMN/Translation/BpmnDetail/index.tsx`

### Chainlink + DMN 侧

- 单节点 direct request：
  - `src/oracle-node/CHAINLINK/features/02-single-node-dmn`
- OCR 扩展原型：
  - `src/oracle-node/CHAINLINK/features/04-dmn-ocr`

## 4. 组件边界

本章需特别区分两类内容：

### 本文实现或整理的内容

- B2CDSL 到 Fabric/Geth 的生成结果。
- FireFly 上层统一调用与事件监听接入方式。
- Solidity 侧为 FireFly/Chainlink 保留的统一事件与 `fireflyTranId` 设计。
- Geth 侧 BusinessRuleTask 的链下 DMN 适配路径。

### 集成使用的开源组件

- Hyperledger Fabric
- Geth / EVM runtime
- Hyperledger FireFly
- Chainlink node / OCR
- Camunda DMN engine based service

因此，第 5 章的贡献表述应当是：

- 本文提出并实现了面向多链流程执行的运行时整合方式；
- 但 Fabric、Geth、FireFly、Chainlink 本身属于被集成的基础设施，而不是本文重新实现的系统。

## 5. 一句概括

这一章最核心的结论是：

> `B2CDSL` 在运行时并不直接面对 Fabric 与 Geth 的异构差异，而是通过 FireFly 形成统一调用与观测入口；对于 Geth 上无法原生执行的 DMN 决策，再通过 Chainlink + DMN Service 形成链下扩展路径。
