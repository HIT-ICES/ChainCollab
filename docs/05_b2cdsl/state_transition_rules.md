# 4.2 State Transition Rules

## 1. 基本规则

`B2CDSL` 不把状态迁移写成单独的状态图文件，而是把迁移规则内嵌在 `flows` 中。

核心思想是：

- 元素先声明结构和初始状态；
- 再由 `flows` 指定何时 `enable`、何时 `disable`、何时 `complete`。

## 2. 起始规则

开始事件通常具有如下模式：

```dsl
start event Event_06sexe6 enables Message_1wswgqu;
```

语义：

1. `Event_06sexe6` 初始状态为 `READY`。
2. 开始事件触发后视为完成。
3. 后继 `Message_1wswgqu` 从 `INACTIVE` 迁移到 `READY`。

## 3. 消息状态迁移

消息在当前系统中通常经历以下抽象阶段：

1. `INACTIVE`
2. `READY`
3. `PENDING_CONFIRMATION`
4. `DONE`

可概括为：

```text
INACTIVE --enable--> READY --send--> PENDING_CONFIRMATION --complete--> DONE
```

其中：

- `enable` 来自前驱 flow；
- `send` / `complete` 在生成代码中拆成具体交易函数；
- `DONE` 会进一步触发下游 flow。

## 4. Gateway 状态迁移

### Exclusive Gateway

典型规则：

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

1. 网关先被前驱元素启用。
2. 网关完成时读取 `globals` 中的条件变量。
3. 仅有一个满足条件的后继被启用。

### Parallel Gateway

分为两类：

- 并行分发：

```dsl
when gateway Gateway_0onpe6x completed
then enable Message_0cba4t6, enable Message_0pm90nx;
```

- 并行汇聚：

```dsl
parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
then enable Message_0rwz1km;
```

语义：

- 分发时多个后继同时从 `INACTIVE -> READY`。
- 汇聚时必须等待所有前驱都达到完成条件，再启用后继。

## 5. BusinessRule 状态迁移

典型规则：

```dsl
when message Message_0ps2yzo completed
then enable Activity_0fbi09z;

when businessrule Activity_0fbi09z done
then enable Gateway_11hmo2k;
```

语义：

1. 前驱消息完成后，规则节点进入 `READY`。
2. 规则执行时读取 `input mapping` 对应的全局变量。
3. DMN 输出写回 `output mapping` 对应的全局变量。
4. 规则节点完成后进入 `DONE`。
5. 下游网关再根据更新后的全局变量决定路径。

## 6. Event 状态迁移

结束事件通常遵循：

```text
INACTIVE --enable--> READY --complete--> DONE
```

虽然 DSL 里常见写法是 “消息完成后 enable end event”，但在目标代码中会继续落实为事件完成与实例结束逻辑。

## 7. 约束

- 不应出现没有前驱就直接 `READY` 的普通消息、网关或规则节点。
- Exclusive gateway 的分支条件应能映射到 `globals` 中的显式变量。
- Parallel join 的 `await` 源列表必须完整，否则无法正确生成同步条件。
- BusinessRule 的 `input/output mapping` 应与 `globals` 对齐，否则状态推进虽可生成，但决策结果无法稳定影响后续路径。
