# 5.2.3 FireFly to Trace Mapping

## 1. 目标

FireFly 输出的是平台级运行事件；第 6 章需要的是可比较的统一 trace。  
因此中间需要一层规范化映射。

## 2. 映射原则

### 原则 1：保留 DSL 元素标识

优先使用稳定命名恢复：

- `Message_...`
- `Gateway_...`
- `Event_...`
- `Activity_...`

### 原则 2：平台差异收束成统一字段

- Fabric transaction id
- Ethereum tx hash

统一映射到：

- `transaction_id`

### 原则 3：状态快照按“可获得程度”补足

如果运行事件里没有完整状态变化，则补充：

- queried state snapshots
- contract snapshot APIs

例如：

- Fabric：`GetAllMessages / GetAllGateways / GetAllBusinessRules`
- Solidity：`getExecutionSnapshot()`

## 3. 映射表

| Runtime record field | Fabric / FireFly source | Geth / FireFly source | Normalization rule |
| --- | --- | --- | --- |
| `transaction_id` | FireFly operation `tx` / blockchain event tx id | Ethereum tx hash | 统一为字符串型交易标识 |
| `platform` | `fabric` | `ethereum` / `geth` | 统一枚举平台来源 |
| `operation_id` | method name / event name | function name / event name | 优先映射回 DSL 元素名 |
| `participant` | MSP / FireFly key / client identity | sender address / configured signer | 再映射回业务参与方 |
| `event_name` | chaincode event name | contract event name | 保留原名 |
| `event_payload` | `blockchainEvent.output` | decoded log output | 统一转 JSON |
| `decision_result` | DMNEngine response / event payload | Chainlink callback / BusinessRuleCompleted path | 若存在则提取 |
| `state_snapshot` | query result | `getExecutionSnapshot()` or equivalent | 可选补充字段 |
| `timestamp` | FireFly event timestamp | block/log timestamp | 统一标准时间 |
| `success` | operation status | tx receipt / operation status | 映射成布尔或 success/failure |

## 4. 一个典型转换过程

### FireFly 原始事件

```text
blockchain_event_received
```

### 规范化后

```json
{
  "operation_id": "Message_1wswgqu",
  "platform": "fabric",
  "participant": "Bulk buyer",
  "transaction_id": "25903c...",
  "event_name": "Message_1wswgqu",
  "event_payload": {
    "InstanceID": "31"
  },
  "success": true,
  "timestamp": "2024-10-11T03:55:50.3865853Z"
}
```

## 5. BusinessRule 的特殊处理

BusinessRule 相关 trace 需要额外关注：

- 请求发起
- 回调完成
- 结果写回后的后继推进

因此通常至少要拆成两条记录：

1. `BusinessRuleRequested`
2. `BusinessRuleCompleted`

如果需要更细粒度，也可以加入：

- DMN service request
- Chainlink callback accepted

## 6. 论文中建议表述

可以写成：

> FireFly 提供跨平台统一的事件采集入口，但其输出仍属于平台级原始记录。本文进一步根据 DSL 命名约定和查询快照接口，将这些原始记录规范化为统一 runtime record，并作为后续语义一致性验证的输入。
