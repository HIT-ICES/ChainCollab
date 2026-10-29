# newTranslator 真实代码转换映射规则说明

本文档基于对目录：

- [src/newTranslator](/root/code/ChainCollab/src/newTranslator)

的实际源码阅读，尤其是：

- [generator/translator.py](/root/code/ChainCollab/src/newTranslator/generator/translator.py)
- [generator/snippet/newSnippet/snippet.py](/root/code/ChainCollab/src/newTranslator/generator/snippet/newSnippet/snippet.py)
- [generator/snippet/newSnippet/snippets.json](/root/code/ChainCollab/src/newTranslator/generator/snippet/newSnippet/snippets.json)
- [generator/snippet/chaincode_snippet/snippet.json](/root/code/ChainCollab/src/newTranslator/generator/snippet/chaincode_snippet/snippet.json)
- [CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py)
- [CodeGenerator/b2cdsl-go/templates/contract.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja)
- [CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py)
- [CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja)

梳理得到。

这份文档回答的不是“实验二如何校验”，而是：

**当前 `newTranslator` 的真实生成器，最后到底把哪些 BPMN/DSL 语义映射成了哪些 Go / Solidity 代码结构。**

---

## 1. 先说结论

当前 `newTranslator` 的真实生成链路是：

1. `BPMN/DMN -> B2CDSL`
   - 由 [translator.py](/root/code/ChainCollab/src/newTranslator/generator/translator.py) 完成
   - DSL 文本模板主要来自 `generator/snippet/newSnippet`

2. `B2CDSL -> Go`
   - 由 `textx generate --target go`
   - 实际入口是 [b2cdsl_go/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py)
   - 最终模板是 `CodeGenerator/b2cdsl-go/templates/*.jinja`

3. `B2CDSL -> Solidity`
   - 由 `textx generate --target solidity`
   - 实际入口是 [b2cdsl_solidity/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py)
   - 最终模板是 [contract.sol.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja)

因此：

- `generator/snippet/chaincode_snippet` 不是当前 `nt-go-gen` 的最终生成入口
- 它主要是**旧版 Go 片段库/遗留 helper 来源**
- 当前真正的最终 Go / Solidity 链码，都是 **B2CDSL 驱动的 code generator** 产物

这点非常重要。

---

## 2. 真实链路总览

### 2.1 BPMN -> DSL

入口：

- [GoChaincodeTranslator.generate_chaincode()](/root/code/ChainCollab/src/newTranslator/generator/translator.py)

内部步骤：

1. `Choreography` 解析 BPMN
2. `ParameterExtractor` 提取：
   - 全局参数 `global_parameters`
   - 条件参数 `judge_parameters`
3. `DSLContractBuilder` 生成 DSL 各 section
4. `FlowPlanner` 生成 `flows`
5. 通过 `newSnippet/snippets.json` 拼出 `.b2c`

### 2.2 DSL -> Go

入口：

- `nt-go-gen`
- `textx generate <b2c> --target go`

最终调用：

- [b2c_generate_go()](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py)
- `generator_callback()`

内部步骤：

1. textX 解析 `.b2c`
2. `DSLContractAdapter` 按 section 收集元素
3. `GoChaincodeRenderer.build_context()` 生成模板上下文
4. `FlowRenderer` 把 DSL `flows` 渲染成 Go 函数体片段
5. `contract.go.jinja` 组装最终 Go 链码

### 2.3 DSL -> Solidity

入口：

- `nt-sol-gen`
- `textx generate <b2c> --target solidity`

最终调用：

- [b2c_generate_solidity()](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py)
- `generator_callback()`

内部步骤：

1. textX 解析 `.b2c`
2. `DSLContractAdapter` 按 section 收集元素
3. `SolidityRenderer.build_context()` 生成模板上下文
4. `SolidityFlowRenderer` 把 DSL `flows` 渲染成 Solidity 函数体片段
5. `contract.sol.jinja` 组装最终 Solidity 合约

---

## 3. `generator/snippet/chaincode_snippet` 的真实地位

这是你特别点名的目录，所以这里单独说明。

### 3.1 它是什么

目录：

- [generator/snippet/chaincode_snippet](/root/code/ChainCollab/src/newTranslator/generator/snippet/chaincode_snippet)

里面的：

- [snippet.json](/root/code/ChainCollab/src/newTranslator/generator/snippet/chaincode_snippet/snippet.json)
- [snippet.py](/root/code/ChainCollab/src/newTranslator/generator/snippet/chaincode_snippet/snippet.py)
- [ffiframe.json](/root/code/ChainCollab/src/newTranslator/generator/snippet/chaincode_snippet/ffiframe.json)

体现的是**旧版 Go 链码模板库**。

### 3.2 它现在还在用吗

结论：

- **不再作为 `nt-go-gen` 的最终代码生成器**
- 但其中部分固定结构被迁移或吸收到新的 Jinja 模板里
- `ffiframe.json` 仍被 [translator.py](/root/code/ChainCollab/src/newTranslator/generator/translator.py) 用于生成 FFI JSON

### 3.3 当前真正生效的 Go 模板在哪里

不是 `generator/snippet/chaincode_snippet/snippet.json`，而是：

- [CodeGenerator/b2cdsl-go/templates/contract.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja)
- [start_event.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/start_event.go.jinja)
- [message_send.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/message_send.go.jinja)
- [message_complete.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/message_complete.go.jinja)
- [gateway.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/gateway.go.jinja)
- [event.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/event.go.jinja)
- [set_global_variable.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/actions/set_global_variable.go.jinja)

### 3.4 为什么看起来很像旧 snippet

因为新的 `contract.go.jinja` 明确写了：

- `// Static helpers copied from the legacy snippet`

也就是说：

- 老 `snippet.json` 的很多固定 helper 结构被复制进了新模板
- 但真正的“流程逻辑渲染”已经迁到 `CodeGenerator/b2cdsl-go`

所以从“最终真实映射规则”角度，应以 **CodeGenerator** 为准，而不是以老 snippet 为准。

---

## 4. BPMN -> B2CDSL 的真实映射规则

这一段由 [translator.py](/root/code/ChainCollab/src/newTranslator/generator/translator.py) 决定。

### 4.1 participants

映射规则：

- BPMN `Participant` -> DSL `participant`

实际来源：

- `query_element_with_type(NodeType.PARTICIPANT)`
- `ParticipantMetadataResolver`

最终保留的字段：

- `participant.id` -> DSL participant 名称
- `bindings.json` 或默认规则 -> `msp`
- `bindings.json` 或默认规则 -> `x509`
- `attributes.role` 默认取参与者名称
- `isMulti / multiMin / multiMax`

最终真实结果：

- DSL 参与方标识主要采用 **BPMN participant id**
- 不是 BPMN 展示名

### 4.2 globals

映射规则：

DSL `globals` 不是直接来自某个单一 BPMN 元素，而是由 `ParameterExtractor` 聚合推断：

1. 消息 schema 里的 `properties`
2. business rule 的 `inputs`
3. business rule 的 `outputs`
4. oracle task 的 `outputs`
5. sequence flow 条件中出现的变量

也就是说：

**DSL globals 是一个“参数与状态槽位统一表”**

不是 BPMN 里显式存在的一个 section。

### 4.3 类型映射

来自：

- `BPMN_TYPE_TO_DSL`

当前实际映射是：

| BPMN/文档类型 | DSL 类型 |
| --- | --- |
| `string` | `string` |
| `number` | `int` |
| `integer` | `int` |
| `boolean` | `bool` |
| `float` | `float64` |
| `float64` | `float64` |

注意：

- 这里 `float` 被映射为 `float64`
- 但 DSL grammar 本身的标量类型只声明了 `float`
- 这说明实现和 grammar 在这里存在一个潜在不完全一致点

### 4.4 messages

映射规则：

- BPMN `MessageFlow.message.id` -> DSL `message.name`
- `flow.source.id` -> `from`
- `flow.target.id` -> `to`
- message documentation -> `schema`
- 初始状态固定映射为 `INACTIVE`

关键点：

- message 的真实 DSL 标识是 BPMN message id
- schema 会保留原始结构化 JSON，若 message documentation 是对象

### 4.5 gateways

映射规则：

- BPMN `ExclusiveGateway` -> DSL gateway type `exclusive`
- BPMN `ParallelGateway` -> DSL gateway type `parallel`
- BPMN `EventBasedGateway` -> DSL gateway type `event`

初始状态：

- 统一映射为 `INACTIVE`

### 4.6 events

映射规则：

- BPMN `StartEvent` -> DSL `event`
- BPMN `EndEvent` -> DSL `event`

初始状态：

- StartEvent -> `READY`
- EndEvent -> `INACTIVE`

这意味着：

- DSL 层并不区分 `start event` 和 `end event` 的类型标签
- 区分主要靠：
  - 初始状态
  - flow 中是否作为 `start event ... enables ...`

### 4.7 businessrules

映射规则：

- BPMN `BusinessRuleTask` -> DSL `businessrule`

其中：

- `dmn` 固定写成 `<rule_id>.dmn`
- `decision` 固定写成 `<rule_id>_DecisionID`
- `input mapping`
  - 来自 BPMN documentation 的 `inputs`
  - 当前直接把 `input.name -> PublicTheName(input.name)`
- `output mapping`
  - 来自 BPMN documentation 的 `outputs`
  - 当前直接把 `output.name -> PublicTheName(output.name)`

这意味着：

- 当前 `businessrule` 的 `dmn/decision` 并不是从 BPMN 原始 DMN 真实解析出来的最终外部标识
- 而是生成器按规则合成的占位/约定标识

### 4.8 oracle tasks

映射规则：

- BPMN `ReceiveTask` / `ScriptTask` -> DSL `oracletask`

task type：

- `ReceiveTask` 默认 -> `external-data`
- `ScriptTask` 默认 -> `compute-task`
- 也可由 documentation 中 `oracleTaskType` 覆盖

输出映射：

- 来自 `outputMappings / outputMapping / outputs`
- 若都没有，默认生成 `<task.id>_result`

### 4.9 flows

这是 `translator.py` 最关键的一部分，由 `FlowPlanner` 控制。

#### A. start event

映射：

- BPMN StartEvent 的后继 -> `start event X enables Y`

#### B. message flows

当前真实实现不是 `when message ... sent`，而是：

- [snippets.json](/root/code/ChainCollab/src/newTranslator/generator/snippet/newSnippet/snippets.json)
  中 `DSLWhenMessageSentEnable`
  实际文本是：
  - `when message {message} completed then enable ...`

也就是说：

- `translator.py` 逻辑名虽然叫 `WhenMessageSent...`
- 但最终 DSL 文本写成的是 **`completed`**

这是一个非常重要的真实实现细节。

#### C. event-based gateway 互斥分支

若 event-based gateway 有多个 message 分支：

- 某个分支消息触发时
- 会在 DSL 中生成：
  - `disable 其他分支`
  - `enable 当前分支后继`

#### D. gateway flows

若 gateway 出边带条件：

- 生成 `when gateway X completed choose { if ... then ... else ... }`

若无条件：

- 生成 `when gateway X completed then enable ...`

#### E. parallel join

若 parallel gateway 入边多于 1：

- 生成 `parallel gateway X await A, B then enable ...`

#### F. businessrule / oracletask

- `when businessrule X done then enable ...`
- `when oracletask X done then enable ...`

#### G. event completed -> set global

`newSnippet` 里存在 `DSL_WhenEventCompletedSetGlobal`

但 `translator.py` 当前没有在 BPMN -> DSL 阶段显式使用它。

这意味着：

- 这类 DSL flow 可能来自人工 DSL 或其他链路
- 不是当前 BPMN -> DSL 主链路稳定自动生成的主模式

---

## 5. DSL -> Go 的真实最终映射规则

这一段以：

- [b2cdsl_go/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py)
- [contract.go.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja)

为准。

### 5.1 contract / runtime skeleton

DSL `contract` 被映射成：

- `type SmartContract struct`
- `type ContractInstance struct`
- `Participant / Message / Gateway / ActionEvent / BusinessRule / StateMemory / InitParameters`

这部分来自固定模板，不是按 flow 单独生成。

### 5.2 globals -> StateMemory

DSL：

- `globals { Confirm: bool }`

Go：

- `type StateMemory struct { Confirm bool }`

类型映射：

- `string` -> `string`
- `int` -> `int`
- `bool` -> `bool`
- `float` -> `float64`

### 5.3 participants -> InitParameters + CreateParticipant

DSL participant 会映射成两处：

1. `InitParameters` 中的 participant 字段
2. `CreateInstance()` 中的 `CreateParticipant(...)`

也就是说：

- participant 不是只变成常量
- 而是变成实例化时需要注入的身份配置

### 5.4 messages -> Message struct + Send/Complete 双函数

每个 DSL `message` 最终映射成：

1. `CreateMessage(...)`
2. `Message_<id>_Send(...)`
3. `Message_<id>_Complete(...)`

真实行为：

- `_Send`
  - 校验发送方
  - 校验消息状态为 `ENABLED`
  - 写入 FireFly transaction id
  - 执行 state_change_block
  - 执行 DSL message flow hook

- `_Complete`
  - 校验接收方
  - 校验消息状态为 `WAITINGFORCONFIRMATION`
  - 然后置为 `COMPLETED`
  - 执行 DSL message completed flow hook

### 5.5 一个关键真实现象：Go 消息状态存在不一致

当前模板：

- `message_send.go.jinja` 中默认把消息状态直接改成 `COMPLETED`
- `message_complete.go.jinja` 却要求消息进入 `WAITINGFORCONFIRMATION`

这意味着在当前真实生成实现中：

- Go 的 `_Send` / `_Complete` 状态机并不完全一致
- `WAITINGFORCONFIRMATION` 在 message 主链路里没有稳定、统一地被设置

从“真实最终映射规则”角度，这不是推断，而是当前模板中的真实行为。

### 5.6 gateways -> 单独 gateway 函数

每个 DSL `gateway` 映射成：

- `func (cc *SmartContract) <GatewayName>(...)`

函数统一执行：

1. 读取 gateway
2. 校验 `GatewayState == ENABLED`
3. parallel gateway 若需要，则先校验 join guard
4. 置为 `COMPLETED`
5. 执行后续动作

#### exclusive gateway

若 DSL 中有 `choose` 分支：

- 渲染成 `if / else if / else`

条件来源：

- `instance.InstanceStateMemory.<Var> <relation> <literal>`

#### parallel gateway

若 DSL 中有 `parallel await`：

- 渲染成 `if !(A && B && ...) return error`

然后再执行后续动作。

#### event gateway

若 DSL 中只是普通 `when gateway completed then ...`

- 与普通 gateway 一样渲染

### 5.7 events -> 事件函数

每个 DSL `event` 映射成：

- `func (cc *SmartContract) <EventName>(...)`

其中：

- start event 使用 `start_event.go.jinja`
- 其他 event 使用 `event.go.jinja`

共同特点：

- 校验事件状态为 `ENABLED`
- 置为 `COMPLETED`
- 执行 flow action

### 5.8 businessrules -> BusinessRule struct + 两阶段函数

每个 DSL `businessrule` 最终映射成：

1. `CreateBusinessRule(...)`
2. `<RuleName>(...)`
3. `<RuleName>_Continue(...)`

真实行为：

- 第一阶段 `<RuleName>`
  - 调 Oracle / 外部链码获取 DMN 内容
  - 发出 `DMNContentRequired` 事件
  - 将状态置为 `WAITINGFORCONFIRMATION`

- 第二阶段 `<RuleName>_Continue`
  - 校验 hash
  - 从 `ParamMapping` 读取全局变量输入
  - 调 `DMNEngine:v1`
  - 将规则输出写回 `StateMemory`
  - 将状态置为 `COMPLETED`
  - 执行 rule done 后续动作

因此：

- Go 侧 businessrule 的真实语义是一个**两阶段异步确认式规则执行**
- 不是单函数同步求值

### 5.9 oracle tasks -> ActionEvent 复用

DSL `oracletask` 在 Go 中没有单独 OracleTask struct。

它被映射成：

- `ActionEvent` 状态槽
- 一个与 task 同名的函数

其行为是：

- 校验 event state
- 可将函数参数写入 `StateMemory`
- 置为 `COMPLETED`
- 执行后继动作

因此从真实运行时结构看：

- Go 侧 oracle task 更像“带输出赋值能力的特殊 event”

### 5.10 flow actions -> ChangeXState / SetGlobalVariable

DSL action 的真实映射如下：

- `enable Message`
  - `ChangeMsgState(..., ENABLED)`
- `disable Message`
  - `ChangeMsgState(..., DISABLED)`
- `enable Gateway`
  - `ChangeGtwState(..., ENABLED)`
- `disable Gateway`
  - `ChangeGtwState(..., DISABLED)`
- `enable Event`
  - `ChangeEventState(..., ENABLED)`
- `disable Event`
  - `ChangeEventState(..., DISABLED)`
- `enable BusinessRule`
  - `ChangeBusinessRuleState(..., ENABLED)`
- `set Global = value`
  - `ReadGlobalVariable`
  - 写 `globalMemory.<Field> = <literal>`
  - `SetGlobalVariable(...)`

---

## 6. DSL -> Solidity 的真实最终映射规则

这一段以：

- [b2cdsl_solidity/__init__.py](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py)
- [contract.sol.jinja](/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja)

为准。

### 6.1 contract skeleton

DSL `contract` 映射成 Solidity：

- 顶层 contract
- `ElementState`
- `ParticipantKey / MessageKey / GatewayKey / EventKey / BusinessRuleKey`
- `StateMemory`
- `Participant / Message / Gateway / ActionEvent / BusinessRule`
- `Instance`
- `InitParameters`

因此 Solidity 侧比 Go 更强烈地采用：

- enum key
- mapping
- typed storage

的方式管理运行态。

### 6.2 globals -> StateMemory

DSL globals 被映射成：

- `struct StateMemory`

类型映射：

| DSL 类型 | Solidity 类型 |
| --- | --- |
| `string` | `string` |
| `int` | `int256` |
| `integer` | `int256` |
| `number` | `int256` |
| `bool` | `bool` |
| `float` | `int256` |
| `float64` | `int256` |

这说明当前 Solidity 生成器对浮点值没有真正保留浮点类型，而是向 `int256` 折叠。

### 6.3 participants -> ParticipantKey + InitParameters + _checkParticipant

每个 DSL participant 映射成：

1. `ParticipantKey` 枚举值
2. `InitParameters` 中的：
   - `<participant>_account`
   - `<participant>_org`
3. `_createParticipant(...)`
4. `_checkParticipant(...)`

真实语义：

- 单人参与方：校验 `msg.sender == participant.account`
- 多人参与方：通过 `IIdentityRegistry` 比较组织

### 6.4 messages -> 单个 `_Send` 函数

这是 Solidity 与 Go 最大的实际差异之一。

每个 DSL `message` 只映射成：

- `function <Message>_Send(...)`

没有 `_Complete`。

真实行为：

1. 读取消息
2. `_checkParticipant(inst, m.sendParticipant)`
3. 校验消息状态为 `ENABLED`
4. 写入 `fireflyTranId`
5. 若 schema 中字段能映射到 `StateMemory`，则直接写入全局状态
6. `m.state = COMPLETED`
7. 立即执行 DSL flow 对应的 sent/completed 后续动作

### 6.5 一个关键真实现象：Solidity 将 sent/completed 合并

在 `SolidityFlowRenderer._message_transition_actions()` 中：

- 会把 `(message, "sent")`
- 和 `(message, "completed")`

两类动作合并进同一个 `_Send` 函数。

这意味着：

- Solidity 侧真实状态机里没有独立的 message complete phase
- `sent` 和 `completed` 在代码生成层被压缩成一次事务

这也是为什么 Solidity 侧最终只生成 `_Send` 函数。

### 6.6 gateways -> 单个 gateway 函数

每个 DSL gateway 映射成：

- `function <GatewayName>(uint256 instanceId)`

统一逻辑：

1. 读取 gateway
2. 校验 `state == ENABLED`
3. 置为 `COMPLETED`
4. 执行 branch / action block

#### exclusive gateway

有 `choose` 时：

- 渲染为 `if / else if / else`

字符串型比较特殊处理：

- 使用 `keccak256(bytes(...))`

#### parallel gateway

有 `parallel await` 时：

- 渲染出联合条件检查
- 条件不满足时 `revert`

#### event gateway

并没有额外单独 runtime 类型

- 仍然按 gateway 函数处理

### 6.7 events -> 事件函数

每个 DSL event 映射成：

- `function <EventName>(uint256 instanceId)`

逻辑：

1. 校验 event 状态
2. 置为 `COMPLETED`
3. 触发 `ActionEventDone`
4. 执行 flow action

### 6.8 businessrules -> 原生链上异步 DMN 请求

Solidity 侧 `businessrule` 映射方式与 Go 明显不同。

每个 DSL businessrule 生成：

- `<RuleName>(instanceId)`
- `<RuleName>_Continue(instanceId)`

但它不是调用 Fabric 外部链码，而是：

#### 第一阶段 `<RuleName>`

1. 读取 `inst.stateMemory` 中的输入字段
2. 拼接成 JSON
3. 调 `IDmnLite.requestDMNDecision(...)`
4. 保存 `requestId`
5. 置状态为 `WAITING_FOR_CONFIRMATION`

#### 第二阶段 `<RuleName>_Continue`

1. 调 `getRequestStatus`
2. 确认 `DMN_REQUEST_FULFILLED`
3. 取原始结果 `getRawByRequestId`
4. 从 JSON 中抽取 output
5. 写回 `inst.stateMemory`
6. 置状态为 `COMPLETED`
7. 执行 rule done 动作

因此：

- Solidity 侧 businessrule 的真实实现是**链上异步请求-回填模型**
- 不是简单的 Oracle getDataItem

### 6.9 oracle tasks -> ActionEvent + IOracle

DSL `oracletask` 映射成：

- `EventKey` 中的一个 event-like key
- `ActionEvent` 状态槽
- 一个与 task 同名的函数

若类型为：

- `external-data`
  - 调 `oracle.getExternalData(...)`
- `compute-task`
  - 调 `oracle.runComputeTask(...)`

然后把返回值写入 `inst.stateMemory`。

所以从真实结构看：

- Solidity oracle task 也是被当作一种特殊 event 来落地
- 但它具有明确的 Oracle 调用逻辑

### 6.10 flow actions -> 直接状态赋值

DSL action 在 Solidity 中的真实映射非常直接：

- `enable Message`
  - `inst.messages[MessageKey.X].state = ElementState.ENABLED`
- `disable Message`
  - `... = ElementState.DISABLED`
- `enable Gateway`
  - `inst.gateways[GatewayKey.X].state = ElementState.ENABLED`
- `enable Event`
  - `inst.events[EventKey.X].state = ElementState.ENABLED`
- `enable BusinessRule`
  - `inst.businessRules[BusinessRuleKey.X].state = ElementState.ENABLED`
- `set Global = value`
  - `inst.stateMemory.<Field> = <literal>`

也就是说：

- Solidity 侧 flow 动作是**显式赋值式**
- Go 侧 flow 动作是**helper 调用式**

---

## 7. Go 与 Solidity 的真实差异

这里总结几个会直接影响“映射规则判断”的关键差异。

### 7.1 消息阶段

Go：

- 生成 `_Send`
- 生成 `_Complete`
- 但当前状态机模板存在不一致

Solidity：

- 只生成 `_Send`
- 将 sent/completed 语义合并

### 7.2 businessrule 执行模型

Go：

- 通过 `Invoke_Other_chaincode`
- 依赖 Oracle / DMNEngine 两个外部链码

Solidity：

- 通过 `IDmnLite`
- 原生链上保存 requestId / raw result

### 7.3 oracle task 表示

Go：

- 复用 `ActionEvent`
- 作为特殊 event 函数

Solidity：

- 同样复用 `ActionEvent`
- 但内嵌 Oracle 调用和输出写回

### 7.4 flow 动作落地方式

Go：

- helper 调用式
- `ChangeMsgState` / `ChangeGtwState` / `SetGlobalVariable`

Solidity：

- 直接 storage 赋值式
- `inst.xxx.state = ...`

---

## 8. 对实验二“最终实际映射规则”的影响

如果实验二要根据真实生成器来定义“最终实际映射规则”，那么应当采用以下原则。

### 8.1 Go 侧应以 `CodeGenerator/b2cdsl-go` 为准

不能再把：

- `generator/snippet/chaincode_snippet/snippet.json`

当作最终有效的 Go 映射规则来源。

真正应依据的是：

- `b2cdsl_go/__init__.py`
- `templates/*.jinja`

### 8.2 Solidity 侧应以 `b2cdsl_solidity` 为准

尤其是：

- 消息只有 `_Send`
- businessrule 是异步 DMN request/continue
- oracle task 用 `IOracle`

这些都必须在实验规则里体现。

### 8.3 message 语义不能简单对称化

真实实现中：

- Go 与 Solidity 对 message 生命周期并不对称
- 因此实验规则不能机械要求两边都必须有 `_Complete`

更合理的实际规则应当是：

- Go：允许 `_Send/_Complete`
- Solidity：允许 `_Send` 内完成 sent + completed 的合并语义

### 8.4 businessrule 规则必须按两边不同运行模型定义

Go 的真实证据应看：

- `Invoke_Other_chaincode`
- `DMNEngine:v1`
- `Oracle:v1`
- `ParamMapping`
- `reflect + StateMemory`

Solidity 的真实证据应看：

- `IDmnLite.requestDMNDecision`
- `getRequestStatus`
- `getRawByRequestId`
- 输出 JSON 抽取函数
- `inst.stateMemory.<slot> = ...`

---

## 9. 可以直接用于实验二的“真实最终映射规则”

如果把当前真实生成器抽象成一句话，那么可以表述为：

### 9.1 BPMN -> DSL

- BPMN participant -> DSL participant
- BPMN message -> DSL message
- BPMN gateway -> DSL gateway
- BPMN event -> DSL event
- BPMN business rule / oracle task -> DSL businessrule / oracletask
- BPMN 消息字段、规则输入输出、条件变量 -> DSL globals
- BPMN 控制流 -> DSL flows

### 9.2 DSL -> Go

- DSL globals -> `StateMemory`
- DSL participants -> `Participant` + `InitParameters` + ACL helper
- DSL messages -> `Message` + `_Send/_Complete`
- DSL gateways -> gateway 函数 + `if/else if` / join guard
- DSL events -> event 函数
- DSL businessrules -> 两阶段 Oracle/DMNEngine 调用函数
- DSL oracletasks -> event-like 函数 + 输出写回
- DSL flows -> `ChangeXState` / `SetGlobalVariable` / 条件控制

### 9.3 DSL -> Solidity

- DSL globals -> `StateMemory`
- DSL participants -> enum + participant storage + `_checkParticipant`
- DSL messages -> 单个 `_Send`，内部合并 sent/completed
- DSL gateways -> gateway 函数 + `if` / `revert` / state assignment
- DSL events -> event 函数
- DSL businessrules -> `requestDMNDecision` + `_Continue`
- DSL oracletasks -> `IOracle` 调用 + state writeback
- DSL flows -> 直接 storage 状态赋值和条件块

---

## 10. 一句话总结

当前 `newTranslator` 的真实最终映射规则不是“BPMN 直接生成 Go/Solidity”，而是：

**先由 `translator.py` 将 BPMN/DMN 归约为 B2CDSL，再由 `b2cdsl-go` 与 `b2cdsl-solidity` 两套独立代码生成器将 DSL 落地为 Go 链码和 Solidity 合约。**

其中：

- `generator/snippet/newSnippet` 决定 DSL 长什么样
- `CodeGenerator/b2cdsl-go` 决定 Go 最终怎么长
- `CodeGenerator/b2cdsl-solidity` 决定 Solidity 最终怎么长
- `generator/snippet/chaincode_snippet` 只是旧版 Go 模板遗留，不是当前最终生成规则的唯一依据
