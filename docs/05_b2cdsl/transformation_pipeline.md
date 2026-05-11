# 4.3 BPMN/DMN to B2CDSL Transformation

## 1. 转换在系统中的位置

源模型到 DSL 的转换位于 `newTranslator` 的前半段：

1. 读取 BPMN Choreography XML。
2. 解析参与方、消息、任务、网关、事件和顺序流。
3. 从 BPMN `documentation` 中提取消息 schema、BusinessRule 输入输出映射、Oracle 扩展信息。
4. 推导全局变量集合与分支条件变量。
5. 组装 B2CDSL 各 section。
6. 输出 DSL，供 Fabric/Go 或 Solidity 生成器继续处理。

核心代码见 [transformer_core_code](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/transformer_core_code)。

## 2. 核心组件

- `parser/choreography_parser/parser.py`
  - 负责 BPMN XML 结构解析。
- `translator.py`
  - `ParameterExtractor`：提取全局变量与网关判断参数。
  - `MessageCatalog`：整理消息定义与消息流元数据。
  - `FlowPlanner`：把前驱后继关系转成 DSL `flows`。
  - `DSLContractBuilder`：生成完整 DSL 文本。
- `parser/dmn_parser/parser.py`
  - 负责 DMN 决策结构解析，用于决策说明与后续绑定相关处理。

## 2.1 转换流程图

```text
BPMN XML + documentation JSON + DMN XML
                |
                v
      Choreography Parser / DMN Parser
                |
                v
    ParameterExtractor + MessageCatalog
                |
                v
           FlowPlanner
                |
                v
       DSLContractBuilder
                |
                v
             B2CDSL
                |
       +--------+--------+
       |                 |
       v                 v
   Go generator     Solidity generator
```

## 3. 转换步骤

### 3.1 BPMN 解析

解析器首先把 BPMN XML 装配成内部 choreography 图结构，识别：

- participants
- messages
- choreography tasks
- business rule tasks
- receive/script tasks
- gateways
- start/end events
- sequence flows
- message flows

### 3.2 参数抽取

`ParameterExtractor.extract()` 负责推导 `globals`：

- 从消息 `documentation.properties` 提取业务字段。
- 从 BusinessRule `documentation.inputs/outputs` 提取决策输入输出。
- 从 Oracle task 输出映射提取新变量。
- 从 sequence flow 条件中推断缺失的判断变量。

### 3.3 结构 section 构建

`DSLContractBuilder` 依次构建：

- `participants`
- `globals`
- `messages`
- `gateways`
- `events`
- `businessrules`
- `oracletasks`
- `flows`

### 3.4 控制流规划

`FlowPlanner` 将 BPMN 中的前驱后继关系转成 DSL 声明式 flow：

- 开始事件 -> `StartFlow`
- 消息完成 -> `MessageFlow`
- 网关完成 -> `GatewayFlow`
- 并行汇聚 -> `ParallelJoin`
- 规则完成 -> `RuleFlow`
- 事件完成 -> `EventFlow`

## 4. BPMN 与 DMN 的结合方式

当前实现里，DMN 与 BPMN 的结合是“流程侧推导优先”：

- BPMN `BusinessRuleTask.documentation` 提供输入输出参数。
- DSL 中的 `dmn` 资源名与 `decision` 标识由 `translator.py` 约定式生成。
- 独立 DMN 文件主要在后续业务规则执行或说明文档里使用。

这意味着：

- 当前系统已经支持 “流程中有决策节点” 的代码生成；
- 但 BPMN XML 中并没有采用标准化的显式字段去绑定真实 DMN 文件路径。

## 5. 转换前后完整示例

已整理到 [before_after_example](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/before_after_example)：

- `input.bpmn`
- `input.dmn`
- `output.dsl`

## 6. 建议在正文中表达的重点

- BPMN 负责多参与方交互结构与控制流。
- DMN 负责决策输入输出的结构化表达。
- B2CDSL 是两者之间的统一执行中间层。
- 该中间层显式保留了身份、状态、消息、规则和 flow 语义，因此适合后续多目标链码生成。
