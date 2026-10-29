# 4.4 B2CDSL Flow Semantics

## 1. 为什么 `flows` 是语义核心

在 `B2CDSL` 中：

- `participants`、`messages`、`gateways`、`events`、`businessrules` 负责描述“有哪些元素”；
- `flows` 负责描述“这些元素如何推进执行”。

因此，后续运行轨迹验证与代码生成，主要都依赖 `flows`。

## 2. flow 语法样例

### 起始 flow

```dsl
start event Event_06sexe6 enables Message_1wswgqu;
```

### 消息驱动 flow

```dsl
when message Message_1wswgqu completed
then enable Message_1ajdm9l;
```

### 网关分支 flow

```dsl
when gateway Gateway_11hmo2k completed
choose {
    if Deliver == true
    then enable Message_196q1fj;
    if Deliver == false
    then enable Event_0eoqvir;
}
```

### 业务规则 flow

```dsl
when businessrule Activity_0fbi09z done
then enable Gateway_11hmo2k;
```

### 并行汇聚 flow

```dsl
parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
then enable Message_0rwz1km;
```

## 3. trigger / guard / effect / successor

### Trigger

`trigger` 是触发 flow 的前置事件。

对应形式：

- `start event ...`
- `when message ... completed`
- `when gateway ... completed`
- `when businessrule ... done`
- `when event ... completed`
- `parallel gateway ... await ...`

### Guard

`guard` 是决定 flow 是否可走、走哪条分支的条件。

在当前 DSL 中，guard 主要出现在 exclusive gateway 的 `choose` 分支里：

```dsl
if Deliver == true
```

它依赖 `globals` 中的变量值。

### Effect

`effect` 是 flow 被触发后执行的状态更新动作。

当前 grammar 里支持：

- `enable target`
- `disable target`
- `set var = literal`

其中最常见的是 `enable`。

### Successor

`successor` 是 effect 指向的后继元素，也就是被状态推进的对象，例如：

- 后继消息
- 后继网关
- 后继事件
- 后继 businessrule

## 4. Gateway 对应 flow 的例子

### Exclusive gateway

```dsl
when gateway Gateway_11hmo2k completed
choose {
    if Deliver == true
    then enable Message_196q1fj;
    if Deliver == false
    then enable Event_0eoqvir;
}
```

语义：

- trigger：`Gateway_11hmo2k completed`
- guard：`Deliver == true` 或 `Deliver == false`
- effect：启用不同后继
- successor：`Message_196q1fj` 或 `Event_0eoqvir`

### Parallel gateway

```dsl
when gateway Gateway_0onpe6x completed
then enable Message_0cba4t6, enable Message_0pm90nx;
```

语义：

- 一个 trigger
- 多个并行 effect
- 多个 successor 同时进入可执行状态

## 5. BusinessRule 对应 flow 的例子

```dsl
when message Message_0ps2yzo completed
then enable Activity_0fbi09z;

when businessrule Activity_0fbi09z done
then enable Gateway_11hmo2k;
```

语义：

- 第一条 flow 把规则节点纳入执行路径；
- 第二条 flow 把决策完成事件继续传播给后继网关。

中间虽然规则执行会读写 `globals`，但从 `flows` 视角，它仍然是一个“有前驱、有后继”的可执行节点。

## 6. 语义上的关键约束

- `flows` 不直接携带参与方身份，身份约束由消息或函数生成逻辑承担。
- `flows` 不直接保存消息载荷，载荷通过 `globals` 与消息 schema 联系。
- 决策的语义影响不是“修改控制边”，而是“先写全局状态，再由后续网关读状态完成分支选择”。

## 7. 与轨迹验证的关系

如果把每条 flow 看作一条状态迁移规则，就可以从 DSL 构建：

- 可达状态集合；
- 执行路径；
- 分支条件覆盖；
- 并行汇聚等待关系；
- 端到端 trace 验证。

因此，`flows` 是 DSL 行为语义和验证语义的共同基础。
