# 5.2.3 Normalized Runtime Record Schema

建议将统一运行记录定义为“最小充分字段集合”，避免过度承诺自动可得信息。

## 1. 核心字段

| Field | Meaning |
| --- | --- |
| `operation_id` | 映射回 DSL 的操作标识，如 `Message_1wswgqu` |
| `platform` | `dsl` / `fabric` / `geth` |
| `participant` | 业务参与方标识 |
| `transaction_id` | Fabric tx id 或 Ethereum tx hash |
| `event_name` | 运行时事件名 |
| `event_payload` | 事件携带的结构化数据 |
| `input_parameters` | 本次调用输入参数 |
| `decision_result` | 若涉及 DMN，则记录决策结果或其摘要 |
| `state_snapshot` | 状态相关输出或查询快照 |
| `success` | 调用或事件是否对应成功执行 |
| `timestamp` | 记录时间 |

## 2. 可选增强字段

| Field | Meaning |
| --- | --- |
| `state_before` | 若可获得，则记录执行前状态 |
| `state_after` | 若可获得，则记录执行后状态 |
| `request_id` | Chainlink / BusinessRule request id |
| `firefly_operation_id` | FireFly operation id |
| `raw_event` | 未规范化的原始 FireFly 事件 |

## 3. JSON 示例

```json
{
  "operation_id": "Activity_0fbi09z",
  "platform": "geth",
  "participant": "Manufacturer",
  "transaction_id": "0xabc123...",
  "event_name": "BusinessRuleCompleted",
  "event_payload": {
    "instanceId": 1,
    "ruleKey": "Activity_0fbi09z",
    "requestId": "0x9988..."
  },
  "input_parameters": {
    "Amount": 320,
    "Self_pickup": false
  },
  "decision_result": {
    "Deliver": true
  },
  "state_snapshot": {
    "gatewayStates": [3, 1, 0]
  },
  "success": true,
  "timestamp": "2026-05-11T10:00:00Z"
}
```

## 4. 字段设计原则

- `operation_id` 必须能回溯到 DSL 元素。
- `platform` 必须能区分 DSL、Fabric、Geth。
- `event_payload` 与 `state_snapshot` 应保留原始信息，不要过早丢失细节。
- `state_before/state_after` 如果当前系统拿不到，就不要在正文里声称一定完整可得。

## 5. 论文中建议表述

建议使用：

> normalized runtime records contain operation-level identifiers, platform origin, participant identity, transaction metadata, event payloads, and state-related outputs or queried state snapshots.

这个表述既准确，也避免对 `state_before/state_after` 的完整自动采集做过度承诺。
