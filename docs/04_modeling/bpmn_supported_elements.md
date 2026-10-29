# BPMN 示例与支持元素

## 1. 示例文件

- BPMN XML： [bpmn_example.bpmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_example.bpmn)
- BPMN 图： [bpmn_diagram.png](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_diagram.png)

说明：

- 本示例来自 `Experiment/BPMNwithDMNcase/SupplyChain.bpmn`。
- `bpmn_diagram.png` 是根据 XML 结构导出的简化 Choreography 图，用于文档展示，不是 BPMN 建模器的原始截图。

## 2. 该示例实际使用的 BPMN 元素

这份 `SupplyChain.bpmn` 中实际出现并进入 `newTranslator` 主解析链路的元素如下：

| BPMN 元素 | 数量 | 在该示例中的作用 |
|---|---:|---|
| `bpmn2:choreography` | 1 | 顶层协作流程容器 |
| `bpmn2:participant` | 5 | 定义参与方：Bulk buyer、Manufacturer、Middleman、Supplier、Special carrier |
| `bpmn2:message` | 11 | 定义跨参与方交换的业务消息及其 schema |
| `bpmn2:messageFlow` | 11 | 连接消息与发送方/接收方 |
| `bpmn2:startEvent` | 1 | 流程入口 |
| `bpmn2:endEvent` | 2 | 流程结束点，其中一个是正常结束，一个是条件分支结束 |
| `bpmn2:choreographyTask` | 11 | 表示两个参与方之间的协作任务 |
| `bpmn2:parallelGateway` | 2 | 表示并行分支与并行汇聚 |
| `bpmn2:exclusiveGateway` | 1 | 表示条件判断分支 |
| `bpmn2:businessRuleTask` | 1 | 表示与 DMN 规则关联的业务规则节点 |
| `bpmn2:sequenceFlow` | 18 | 表示控制流顺序和条件流转 |
| `bpmn2:documentation` | 多处 | 用于消息 schema 和业务规则输入输出映射描述 |

该示例中**没有使用**但解析器已预留支持的元素：

- `bpmn2:eventBasedGateway`
- `bpmn2:receiveTask`
- `bpmn2:scriptTask`
- 自定义 `DataTask`

## 3. 每个元素在系统中的含义

### 3.1 `bpmn2:choreography`

- 在系统中表示一个可被转换的 **协作流程根模型**。
- `Choreography.load_from_root()` 只会选择 `choreography` 根节点进行主解析。
- 后续 DSL/Go/Solidity 全部从这个根对象展开。

### 3.2 `bpmn2:participant`

- 在系统中表示 **流程参与方**。
- 会被翻译到 B2CDSL 的 `participants` 区块。
- 后续进一步映射为：
  - Fabric：`MSP/X.509/attributes`
  - Solidity：参与者枚举、地址/组织权限元数据

### 3.3 `bpmn2:message`

- 在系统中表示 **业务消息定义**。
- `documentation` 中的 JSON 会被当作消息 schema，用于抽取全局变量和生成消息格式信息。
- 只有被 `messageFlow` 引用的消息才会进入解析结果。

### 3.4 `bpmn2:messageFlow`

- 在系统中表示 **消息的发送方与接收方关系**。
- 它把 `participant` 与 `message` 绑定起来。
- 对 `choreographyTask` 来说，哪条消息是“发起消息”、哪条是“返回消息”，就是由 `messageFlow.source/target` 与 `initiatingParticipantRef` 的关系决定的。

### 3.5 `bpmn2:startEvent`

- 在系统中表示 **流程起点**。
- 会被翻译成 DSL 里的 `event`，且初始状态为 `READY`。
- 同时在 `flows` 中生成 `start event ... enables ...`。

### 3.6 `bpmn2:endEvent`

- 在系统中表示 **流程终点**。
- 会被翻译成 DSL 里的结束事件。
- 通常由前一个消息、网关或业务规则节点驱动进入完成态。

### 3.7 `bpmn2:choreographyTask`

- 在系统中表示 **两个参与方之间的一次协作交互**。
- 这是 BPMN Choreography 到 DSL 转换里最核心的业务节点。
- 系统会从中抽取：
  - 哪个参与方发起
  - 哪些参与方参与
  - 关联了哪条消息流
  - 前驱/后继控制流
- 然后翻译成 DSL 中的消息定义和消息驱动流程语句。

### 3.8 `bpmn2:parallelGateway`

- 在系统中表示 **并行分支 / 并行汇聚**。
- 解析器只从结构上区分“多出边”和“多入边”。
- 在 DSL 中会转成 `gateway type parallel`，以及 `parallel gateway ... await ... then ...` 这样的 flow 语句。

### 3.9 `bpmn2:exclusiveGateway`

- 在系统中表示 **条件判断网关**。
- 分支条件来自 `sequenceFlow.name` 或 `conditionExpression`。
- 在 DSL 中会转成 `gateway type exclusive` 和 `choose { if ... then ... }`。

### 3.10 `bpmn2:businessRuleTask`

- 在系统中表示 **与 DMN 决策相关的规则节点**。
- 当前实现主要从 `documentation` 中读取输入输出字段，而不是直接从 BPMN 里挂接一个真实 DMN 文件路径。
- 在 DSL 中会转成 `businessrule` 块，并映射输入输出参数。

### 3.11 `bpmn2:sequenceFlow`

- 在系统中表示 **控制流边**。
- 普通顺序流用于定义先后关系。
- 带条件的顺序流用于 exclusive gateway 分支判断。

### 3.12 `bpmn2:documentation`

- 在系统中是一个很重要的扩展承载位。
- 主要用于两类语义：
  - `message.documentation`：消息 payload/schema
  - `businessRuleTask.documentation`：规则输入输出元数据

## 4. 这份示例能说明什么

`SupplyChain.bpmn` 适合作为示例，是因为它同时覆盖了 `newTranslator` 当前主链路最关键的 BPMN 语义：

- 参与方建模
- 消息建模
- 协作任务建模
- 顺序控制流
- 并行控制流
- 条件网关
- 业务规则任务
- 基于 `documentation` 的数据语义扩展

因此，这个例子足以说明系统如何把 BPMN Choreography 翻译成 B2CDSL，再进一步翻译成 Fabric Go 链码或 Solidity 合约。

