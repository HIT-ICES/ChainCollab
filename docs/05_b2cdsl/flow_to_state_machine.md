# 4.4 Flow to State Machine

## 1. 转换目标

`B2CDSL` 的 `flows` 可以等价理解为一组“带条件的状态迁移规则”。  
若要做运行轨迹验证，可把 DSL 转换成状态机：

- 状态机节点：流程实例在某一时刻的全局状态快照。
- 状态机边：某条 `flow` 被触发并执行后的迁移。

## 2. 状态机状态的组成

一个 DSL 执行状态至少应包含两部分：

### 元素状态

记录每个可执行元素当前处于：

- `INACTIVE`
- `READY`
- `PENDING_CONFIRMATION`
- `DONE`

### 全局变量状态

记录 `globals` 中每个变量当前值，例如：

- `Amount = 300`
- `Self_pickup = false`
- `Deliver = true`

## 3. 基本转换规则

### 规则 1：`enable X`

将目标元素 `X` 的状态迁移为 `READY`。

### 规则 2：消息发送

消息从 `READY` 进入 `PENDING_CONFIRMATION`。

### 规则 3：消息完成

消息从 `PENDING_CONFIRMATION` 进入 `DONE`，随后触发以 `when message ... completed` 为 trigger 的 flow。

### 规则 4：业务规则完成

业务规则执行时：

1. 读取 `input mapping` 指向的全局变量。
2. 调用 DMN 或决策逻辑。
3. 将 `output mapping` 写回 `globals`。
4. 将规则节点置为 `DONE`。
5. 继续触发 `when businessrule ... done` 的后继 flow。

### 规则 5：Exclusive gateway

当网关被触发时：

1. 读取 guard 对应的全局变量；
2. 选择满足条件的唯一分支；
3. 对该分支 effect 执行状态更新。

### 规则 6：Parallel join

只有当 `await` 中所有源元素都处于完成态时，join 对应的 flow 才可触发。

## 4. 形式化理解

可把单条 flow 抽象为：

```text
(Trigger, Guard, Effect) : State_i -> State_j
```

其中：

- `Trigger` 决定何时可检查该 flow；
- `Guard` 决定该 flow 是否可执行；
- `Effect` 决定执行后如何更新状态。

## 5. SupplyChain 示例

以如下片段为例：

```dsl
when businessrule Activity_0fbi09z done
then enable Gateway_11hmo2k;

when gateway Gateway_11hmo2k completed
choose {
    if Deliver == true
    then enable Message_196q1fj;
    if Deliver == false
    then enable Event_0eoqvir;
}
```

可转成如下状态机语义：

1. `Activity_0fbi09z` 完成后，`Gateway_11hmo2k := READY`。
2. 检查 `Deliver` 的值。
3. 若 `Deliver == true`，则 `Message_196q1fj := READY`。
4. 若 `Deliver == false`，则 `Event_0eoqvir := READY`。

## 6. 为什么这种转换有用

- 可以对 DSL 做可达性分析。
- 可以验证某些消息是否必然最终执行。
- 可以验证 DMN 结果是否真正影响后续路径。
- 可以对 Go/Solidity 生成结果做静态一致性检查。
