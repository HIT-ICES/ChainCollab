# 5.2.2 Event Observability Through FireFly

## 1. 基本定位

FireFly 在本文中不是验证器，而是观测层。  
它提供的价值是：

- 监听链上事件；
- 关联到底层交易；
- 输出统一的事件消息流；
- 为后续 runtime record 规范化提供数据源。

## 2. Fabric 侧观测证据

仓库中 `Experiment/NoiseExperiment` 已实际使用 FireFly：

1. 创建 listener
2. 创建 websocket subscription
3. 监听 `blockchain_event_received`

相关代码：

- `Experiment/NoiseExperiment/main.py`
- `Experiment/NoiseExperiment/invoker.py`

其监听 API 形态为：

```http
POST /api/v1/namespaces/default/contracts/listeners
POST /api/v1/namespaces/default/subscriptions
```

收到的事件类型为：

```text
blockchain_event_received
```

## 3. Ethereum / Geth 侧观测证据

前端执行层已实现 Ethereum 监听注册逻辑：

- 当是 Fabric 时，listener `location = { channel, chaincode }`
- 当是 Ethereum 时，listener `location = { address }`

直接证据：

- `src/front/src/api/executionAPI.ts::invokeFireflyListeners`
- `src/front/src/views/BPMN/Translation/BpmnDetail/index.tsx`

因此 FireFly 的观测逻辑在两侧保持统一，只是底层 location 不同。

## 4. 订阅哪些事件

### Fabric 侧

从现有日志和链码模板可见，FireFly 可观测到这类事件：

- `InstanceCreated`
- 各消息完成/发送事件
- 网关完成事件
- 结束事件
- DMN 续执行完成事件，例如 `Avtivity_continueDone`

### Geth 侧

从生成合约和 Solidity 模板可见，适合被 FireFly 监听的事件包括：

- `MessageSent`
- `BusinessRuleRequested`
- `BusinessRuleCompleted`
- 其他 message/gateway/event 完成事件

## 5. FireFly 能提供什么，不提供什么

### 能提供

- operation 对应的底层 transaction id
- 链上事件名称
- 事件 payload
- 时间戳
- 来源平台
- 监听主题 / listener 元数据

### 不应过度承诺

- FireFly 本身不会自动完成 DSL 语义一致性判断
- FireFly 也不天然保证拿到完整 `state_before/state_after`

更准确的表述应为：

> FireFly 提供统一的运行观测数据源；状态相关信息可进一步通过链上查询接口或快照接口补足。

## 6. 与第 6 章的关系

第 6 章真正比较的是：

- DSL reference trace
- Fabric runtime records
- Geth runtime records

FireFly 在这里承担的是：

- 采集入口
- 事件统一输送入口

而不是：

- 语义一致性判定器
