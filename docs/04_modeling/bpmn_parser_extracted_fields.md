# BPMN 解析器提取字段说明

## 1. 解析器入口

当前 BPMN 主解析器位于：

- `src/newTranslator/generator/parser/choreography_parser/parser.py`
- `src/newTranslator/generator/parser/choreography_parser/elements.py`

入口类是 `Choreography`，主要流程是：

1. 从 BPMN XML 中定位 `bpmn2:choreography`
2. 递归解析节点与边
3. 根据 ID 建立元素引用关系
4. 只把被 `messageFlow` 使用到的 `message` 补充进图模型

## 2. 当前示例中，解析器实际提取哪些字段

下面的说明分两层：

- 第一层：按 BPMN 元素说明“从 XML 抽取什么”
- 第二层：说明这些字段在系统里的用途

## 3. 节点类元素

### 3.1 `bpmn2:participant`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 参与方唯一标识 |
| `@name` | `name` | 参与方显示名 |
| `participantMultiplicity/@minimum` | `multi_minimum` | 多实例下界 |
| `participantMultiplicity/@maximum` | `multi_maximum` | 多实例上界 |
| `participantMultiplicity` 是否存在 | `is_multi` | 是否多实例参与者 |

用途：

- 生成 DSL `participant`
- 绑定参与方元数据
- 作为 `messageFlow.source/target` 的引用目标

### 3.2 `bpmn2:message`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 消息唯一标识 |
| `@name` | `name` | 消息名称 |
| `documentation` 文本 | `documentation` | 消息 schema 的 JSON 文本 |

用途：

- 生成 DSL `message`
- 从 `documentation` 中抽取消息字段，进而推导 DSL `globals`

注意：

- 不是所有 `message` 都自动进入图模型。
- 只有被 `messageFlow.messageRef` 引用到的 `message` 才会在 `_parse_messages()` 阶段被补入。

### 3.3 `bpmn2:startEvent`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 事件 ID |
| `@name` | `name` | 事件名，可为空 |
| `outgoing` | `outgoing` | 指向下一个 `sequenceFlow` 的 ID |

用途：

- 定位流程起点
- 生成 DSL 起始事件与 start flow

### 3.4 `bpmn2:endEvent`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 事件 ID |
| `@name` | `name` | 事件名，可为空 |
| `incoming` | `incoming` | 指向前一个 `sequenceFlow` 的 ID |

用途：

- 生成 DSL 结束事件
- 用于构造流程终止路径

### 3.5 `bpmn2:choreographyTask`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 任务 ID |
| `@name` | `name` | 任务名称 |
| `incoming` | `incoming` | 前驱顺序流 ID |
| `outgoing` | `outgoing` | 后继顺序流 ID |
| `participantRef*` | `participants` | 参与方 ID 列表 |
| `@initiatingParticipantRef` | `init_participant` | 发起方 ID |
| `messageFlowRef*` | `message_flows` | 关联消息流 ID 列表 |

用途：

- 判断哪条消息是发起消息、哪条是返回消息
- 生成 DSL `message` 驱动流程
- 生成消息发送/完成后的后继控制逻辑

### 3.6 `bpmn2:businessRuleTask`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 规则任务 ID |
| `@name` | `name` | 规则任务名称 |
| `incoming` | `incoming` | 前驱顺序流 ID |
| `outgoing` | `outgoing` | 后继顺序流 ID |
| `documentation` 文本 | `documentation` | 输入输出描述 JSON |

用途：

- 生成 DSL `businessrule`
- 从 `documentation.inputs/outputs` 推导输入输出映射
- 驱动业务规则完成后的流程推进

### 3.7 `bpmn2:parallelGateway`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 网关 ID |
| `@name` | `name` | 网关名称，可为空 |
| `incoming*` | `incomings` | 所有入边 ID |
| `outgoing*` | `outgoings` | 所有出边 ID |

用途：

- 识别并行分叉或并行汇聚
- 生成 DSL 并行网关与 `parallel join` 逻辑

### 3.8 `bpmn2:exclusiveGateway`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 网关 ID |
| `@name` | `name` | 网关名称，可为空 |
| `incoming*` | `incomings` | 所有入边 ID |
| `outgoing*` | `outgoings` | 所有出边 ID |

用途：

- 识别条件分支节点
- 结合 `sequenceFlow` 条件生成 DSL `choose` 分支

### 3.9 `bpmn2:eventBasedGateway`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 网关 ID |
| `@name` | `name` | 网关名称 |
| `incoming*` | `incomings` | 所有入边 ID |
| `outgoing*` | `outgoings` | 所有出边 ID |

用途：

- 当前解析器支持建模对象创建。
- 该示例未使用。

### 3.10 `bpmn2:receiveTask` / `bpmn2:scriptTask` / `DataTask`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 任务 ID |
| `@name` | `name` | 任务名称 |
| `incoming` | `incoming` | 前驱顺序流 ID |
| `outgoing` | `outgoing` | 后继顺序流 ID |
| `documentation` | `documentation` | Oracle 任务元数据 |
| `script` | `computeScript` | 对 `scriptTask`，若无 documentation，则从 script 自动补文档 |
| `dataSource`/`extensionElements` | `dataSource` | 对自定义 `DataTask` 提取外部数据源信息 |

用途：

- 映射为系统里的 Oracle 任务
- 生成 DSL `oracletasks`

该示例未使用这些元素，但解析器已预留支持。

## 4. 边类元素

### 4.1 `bpmn2:messageFlow`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 消息流 ID |
| `@name` | `name` | 名称，可为空 |
| `@sourceRef` | `source` | 发送方 participant ID |
| `@targetRef` | `target` | 接收方 participant ID |
| `@messageRef` | `message` | 消息 ID |

用途：

- 建立消息、发送方、接收方三者之间的绑定
- 支撑 choreography task 的发起消息/返回消息判断

### 4.2 `bpmn2:sequenceFlow`

解析器提取：

| XML 来源 | 提取字段 | 说明 |
|---|---|---|
| `@id` | `id` | 顺序流 ID |
| `@name` | `name` | 名称，通常也可承载条件文本 |
| `@sourceRef` | `source` | 起点元素 ID |
| `@targetRef` | `target` | 终点元素 ID |
| `conditionExpression` 文本 | `condition_expression` | 显式条件表达式 |

补充规则：

- 如果 `conditionExpression` 存在，优先提取它。
- 如果没有 `conditionExpression`，但 `@name` 存在，则把 `@name` 当条件文本使用。

用途：

- 建立控制流图
- 为 exclusive gateway 的分支条件提供来源

## 5. 解析器还做了哪些二次处理

除了“按字段读取 XML”，解析器还做了几步结构化处理：

### 5.1 ID 到对象的引用绑定

- 初次解析时，很多字段先只是字符串 ID。
- `_init_element_properties()` 会把这些 ID 解析为真正的对象引用。

例如：

- `ChoreographyTask.participants`
- `ChoreographyTask.message_flows`
- `SequenceFlow.source/target`
- `MessageFlow.source/target/message`

最终都会变成对象级关联。

### 5.2 图模型构建

- `simple_graph` 会把节点和边放入 `networkx.DiGraph`
- `topology_graph_without_message` 会去掉 `message` 和 `participant` 节点，只保留流程控制图

这一步是后续路径计算、网关分析、SESE 分析和 DSL flow 生成的基础。

## 6. 当前不进入主解析链路的 BPMN 信息

下面这些 BPMN XML 信息在当前 `Choreography` 解析器里**不会进入主模型字段**：

- `bpmndi:BPMNDiagram`
- `bpmndi:BPMNPlane`
- `bpmndi:BPMNShape`
- `bpmndi:BPMNEdge`
- `dc:Bounds`
- `di:waypoint`
- 绝大多数图形布局信息

也就是说：

- 当前生成器主要消费 **语义层 BPMN**，不是图形层 BPMN DI。
- 图中坐标、尺寸、显示方式主要用于建模器展示，不参与主 DSL 翻译。

## 7. 对这份示例的结论

对于 `bpmn_example.bpmn`，解析器真正关心的是：

- 谁是参与者
- 哪些消息被交换
- 哪个任务由谁发起
- 流程按什么顺序推进
- 哪些节点并行
- 哪些节点按条件分支
- 哪些业务规则会读写哪些输入输出

这正是 `newTranslator` 从 BPMN Choreography 到 B2CDSL 的最小必要语义集合。

