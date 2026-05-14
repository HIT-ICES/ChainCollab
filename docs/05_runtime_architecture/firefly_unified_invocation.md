# 5.2.1 Unified Invocation Through FireFly

## 1. 统一入口

上层实验和执行界面并不直接区分：

- Fabric chaincode invoke/query
- Geth contract transaction/call

而是统一调用 FireFly 暴露出的业务 API：

```text
B2CDSL operation
      ↓
FireFly API / wrapper
      ↓
Fabric invoke  or  Geth transaction
```

## 2. 统一调用在仓库中的实现证据

### 统一 invoke 形式

`src/front/src/api/executionAPI.ts` 中，消息、事件、网关、业务规则都通过统一 URL 形式调用：

```text
/api/v1/namespaces/default/apis/<contractName>/invoke/<methodName>
```

例如：

- `invokeMessageAction(...)`
- `invokeEventAction(...)`
- `invokeGatewayAction(...)`
- `invokeBusinessRuleAction(...)`

这说明上层调用心智是：

- “调用某个流程操作”

而不是：

- “手写 Fabric SDK 调某个 chaincode”
- “手写 Web3/Ethers 调某个 Solidity function”

## 3. FireFly 如何区分 Fabric 与 Geth

差异被压到 FireFly API 注册阶段。

### Fabric

注册 API 时使用：

```json
{
  "location": {
    "channel": "default",
    "chaincode": "<contractName>"
  }
}
```

### Ethereum / Geth

注册 API 时使用：

```json
{
  "location": {
    "address": "<contractAddress>"
  }
}
```

这个逻辑直接出现在：

- `src/front/src/views/BPMN/Translation/BpmnDetail/index.tsx`
- `src/front/src/api/executionAPI.ts`

因此，上层只看到统一 API 名，而 FireFly 根据 `location` 决定底层把调用路由到 Fabric 还是 Ethereum。

## 4. 为什么这对本文重要

这带来三个直接收益：

1. 实验驱动代码不需要分别写两套调用器。
2. 业务操作可以稳定回溯到 DSL 元素。
3. 第 6 章的一致性验证可以把“平台调用差异”尽量排除出比较主线。

## 5. 与 DSL 的映射关系

FireFly 层的业务操作，与 DSL 元素之间存在稳定映射：

- `message X` -> `X_Send` / `X_Complete`
- `event X` -> `X`
- `gateway X` -> `X`
- `businessrule X` -> `X` / `X_Continue`

这意味着：

- FireFly-level operation 不是任意自定义命名；
- 它本质上继承了 B2CDSL 的命名体系。

## 6. 当前实现的边界

仓库中保存的 FireFly 原始调用日志以 Fabric 侧最完整。  
Ethereum/Geth 侧的统一调用路径，在前端注册逻辑、接口形式和生成合约事件设计中都有实现依据，但仓库中保留的原始 FireFly/Geth 调用日志少于 Fabric。

因此第 5 章建议写法是：

- FireFly 作为统一接入层的机制已经明确；
- Fabric 侧有现成日志证据；
- Geth 侧通过 API 注册代码与合约事件接口得到支撑。
