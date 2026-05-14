# 5.3 Chainlink Callback and FireFly Observation

## 1. 关系定位

Chainlink 回调完成后，系统并不会停在“链上结果已写回”这一层。  
为了进入第 6 章的一致性验证链路，回调后的事件或状态变化还需要被 FireFly 观测。

## 2. 可被 FireFly 监听的对象

### 合约级事件

FireFly 可以监听 Geth/Ethereum 合约事件。  
仓库中直接证据：

- `src/front/src/api/executionAPI.ts::invokeFireflyListeners`
  - Ethereum listener 使用 `location: { address: contractAddress }`

因此，以下事件都适合作为观测源：

- `BusinessRuleRequested`
- `BusinessRuleCompleted`
- `DecisionFulfilled`
- `Finalized`
- `MessageSent`

## 3. 为什么回调后还要观测

仅仅知道 Chainlink 成功回写还不够。  
验证层更关心的是：

- 回写是否对应正确的 `requestId`
- 业务规则状态是否由 waiting 变为 completed
- 决策结果是否真正写回流程全局状态
- 后续 gateway 或 message 是否因此被启用

因此 FireFly 侧至少需要捕获：

- request id
- event name
- transaction id
- instance id
- rule id / businessrule key

## 4. 当前仓库中的可观测路径

### 已有明确实现证据

- FireFly Ethereum listener registration
- Solidity 生成合约保留业务事件
- `getExecutionSnapshot()` 用于补充状态查询

### 当前保存原始日志的情况

- Fabric/FireFly 原始日志在仓库中保存得更完整；
- Geth/FireFly 的原始回调事件日志保留较少；
- 但从监听注册代码和 Solidity 事件设计看，观测链路是成立的。

## 5. 如何进入 runtime record

建议规范化步骤如下：

1. FireFly 捕获 `BusinessRuleCompleted` 或 `Finalized`
2. 解析 `instanceId`、`requestId`、`ruleKey`
3. 结合状态查询接口补一个 `state_snapshot`
4. 输出统一记录：
   - `operation_id = ruleKey`
   - `decision_result = ...`
   - `platform = geth`
   - `transaction_id = tx hash`

## 6. 对 OCR 的处理建议

如果 OCR 只是当前仓库中的增强原型，而不是主实验路径，那么正文最好写成：

> Chainlink callback results are still observed through the same FireFly event pipeline. The repository additionally contains an OCR-based prototype, but the main runtime narrative only requires that callback events and post-callback state updates remain observable and traceable.
