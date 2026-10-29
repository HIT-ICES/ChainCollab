# 5.3 Geth-side DMN Invocation via Chainlink

## 1. 为什么需要 Chainlink

Geth / Solidity 合约不适合直接执行复杂 DMN 决策：

- 决策逻辑复杂，链上实现成本高；
- DMN XML 解析与规则执行不适合放进 Solidity；
- 决策结果往往需要来自链下服务。

因此，Geth 侧 BusinessRuleTask 需要链下扩展机制。

## 2. 本文中的定位

Chainlink 在本文中的定位是：

> Geth 侧 BusinessRuleTask / DMN 调用的运行时适配组件。

它不是本文的主贡献点，也不需要在主线中展开其共识安全细节。

## 3. 基本流程

```text
Solidity contract reaches BusinessRuleTask
        ↓
contract sends Chainlink request
        ↓
Chainlink job invokes DMN Service
        ↓
DMN Service returns decision result
        ↓
Chainlink callback writes result to contract
        ↓
contract emits completion event / updates state
        ↓
FireFly observes event and normalizes it
```

## 4. 仓库中的两条实现路径

### 4.1 主实现路径：single-node direct request

位置：

- `src/oracle-node/CHAINLINK/features/02-single-node-dmn`

特点：

- 直接请求链下 DMN 服务；
- 结果由 Chainlink 节点回调写回；
- 实现路径更直接，更适合作为章节主线描述。

### 4.2 扩展原型：OCR + DMN

位置：

- `src/oracle-node/CHAINLINK/features/04-dmn-ocr`

特点：

- 引入多节点 OCR 聚合；
- 同时保留 baseline raw/hash 与 OCR hash 校验路径；
- 更适合作为扩展性说明或 future work / prototype support。

因此第 5 章建议写法是：

- 主体按 direct request 讲；
- OCR 作为已探索的增强路径轻写。

## 5. 与生成 Solidity 合约的结合点

在本文生成的 Solidity 合约里，BusinessRule 被拆成两阶段：

1. `Activity_xxx(...)`
   - 发起 DMN 请求；
2. `Activity_xxx_Continue(...)`
   - 在回调完成后读取结果并推进流程。

这正符合链下调用的运行语义。

## 6. 与 FireFly 的关系

FireFly 不负责执行 DMN。  
FireFly 的职责是：

- 观测 BusinessRule 请求事件；
- 观测 Chainlink 回调完成后的业务事件；
- 将这些事件纳入统一 runtime record。

所以更准确的表述应为：

- `Chainlink` 负责“链下调用与回写”
- `FireFly` 负责“统一观测与记录”

## 7. 一句概括

> 在 Geth 侧，BusinessRuleTask 的决策执行被实现为“链上触发 + Chainlink 转发 + DMN Service 计算 + 链上回写 + FireFly 观测”的混合流程。
