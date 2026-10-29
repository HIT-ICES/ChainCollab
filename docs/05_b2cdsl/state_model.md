# 4.2 State Model

## 1. DSL 中的状态枚举

`B2CDSL` grammar 在 `ElementState` 中只定义了 4 个显式状态：

- `INACTIVE`
- `READY`
- `PENDING_CONFIRMATION`
- `DONE`

语法来源见 [b2cdsl_grammar.tx](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_grammar.tx)。

## 2. 每个状态的含义

### `INACTIVE`

- 元素已声明，但当前不可执行。
- 典型场景：
  - 尚未到达的消息。
  - 尚未激活的网关。
  - 尚未执行的 BusinessRuleTask。
  - 尚未触发的结束事件。

### `READY`

- 元素已被启用，可以被当前参与方或系统动作触发。
- 典型场景：
  - 开始事件初始即 `READY`。
  - 某个前驱完成后，后继消息或规则被 `enable`。

### `PENDING_CONFIRMATION`

- 元素已发起，但还未完成最终确认。
- 主要用于双阶段消息交互。
- 在当前生成器里，这个状态更接近“已发送，待完成”的中间运行态。

### `DONE`

- 元素执行完成。
- 它是后续 flow 规则中的常见触发条件，例如：

```dsl
when message Message_1wswgqu completed
then enable Message_1ajdm9l;
```

## 3. “其他状态”说明

从 DSL 语法角度，当前没有第五种枚举状态。

但在代码生成阶段，Go 与 Solidity 会把 DSL 状态映射为各自内部状态别名：

- Fabric Go:
  - `INACTIVE -> DISABLED`
  - `READY -> ENABLED`
  - `PENDING_CONFIRMATION -> WAITINGFORCONFIRMATION`
  - `DONE -> COMPLETED`
- Solidity:
  - `INACTIVE -> DISABLED`
  - `READY -> ENABLED`
  - `PENDING_CONFIRMATION -> WAITING_FOR_CONFIRMATION`
  - `DONE -> COMPLETED`

因此，如果论文里提到“其他状态”，建议表述为：

- `B2CDSL` 只定义 4 个抽象状态；
- 代码生成器会将其投影到目标平台的运行时状态命名体系。

## 4. 状态作用范围

当前 DSL 中，下列元素都可以携带初始状态：

- `message`
- `gateway`
- `event`
- `businessrule`
- `oracletask`

`participant` 和 `global` 本身不是状态机节点，不携带 `initial state`。

## 5. 示例

来自 [b2cdsl_full_example.dsl](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_full_example.dsl)：

```dsl
event Event_06sexe6 {
    initial state READY
}

message Message_1wswgqu from Participant_0w6qkdf to Participant_19mgbdn {
    initial state INACTIVE
    schema "..."
}

businessrule Activity_0fbi09z {
    ...
    initial state INACTIVE
}
```

其含义是：

- 流程开始事件在实例初始化后即可触发；
- 第一条业务消息初始不可执行，要等开始事件触发后被启用；
- DMN 规则节点也必须等待前序消息完成后才进入可执行状态。
