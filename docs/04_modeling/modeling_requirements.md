# 模型必须表达哪些内容

## 1. 结论

为了把协作业务流程自动生成到 Fabric 链码或 Solidity 合约，模型至少需要表达以下内容：

- 多企业参与方
- 消息
- 开始 / 结束
- 分支
- 状态
- 决策
- 决策输入输出

这些内容在 `newTranslator` 中并不是全部都直接来自同一个 BPMN 元素，而是分别落在：

- BPMN Choreography
- BPMN `documentation`
- B2CDSL 中间层
- 代码生成器运行时结构

## 2. 需求与系统实现对应关系

### 2.1 多企业参与方

模型必须表达：

- 有哪些企业/组织参与
- 谁在流程中扮演什么角色
- 哪些消息由谁发、发给谁

系统中的对应实现：

- BPMN：`participant`
- 解析器对象：`Participant`
- DSL：`participants { participant ... }`
- Fabric 侧：`msp` / `x509` / `attributes`
- Solidity 侧：参与者枚举、地址/组织权限元数据

为什么必须有：

- 没有参与方，就无法生成跨企业协作合约
- 也无法生成消息收发权限控制

### 2.2 消息

模型必须表达：

- 交换的业务消息是什么
- 谁发送、谁接收
- 消息包含哪些数据字段

系统中的对应实现：

- BPMN：`message` + `messageFlow`
- 消息 schema 来源：`message.documentation`
- 解析器对象：`Message`、`MessageFlow`
- DSL：`messages { message ... from ... to ... schema ... }`
- 代码生成：消息发送方法、完成方法、格式校验/载荷处理

为什么必须有：

- 多方协作流程的核心就是消息驱动
- 没有消息定义，代码生成器无法知道要暴露哪些交互接口

### 2.3 开始 / 结束

模型必须表达：

- 流程从哪里启动
- 流程在哪些条件下结束

系统中的对应实现：

- BPMN：`startEvent`、`endEvent`
- 解析器对象：`StartEvent`、`EndEvent`
- DSL：`events { ... }` + `start event ... enables ...`
- 代码生成：实例初始化与终止状态管理

为什么必须有：

- 区块链上的流程实例需要明确生命周期
- 否则无法生成可执行的状态机入口和终止逻辑

### 2.4 分支

模型必须表达：

- 流程何时并行
- 流程何时按条件分支
- 汇聚条件是什么

系统中的对应实现：

- BPMN：`exclusiveGateway`、`parallelGateway`
- 分支条件来源：`sequenceFlow.name` 或 `conditionExpression`
- DSL：`gateway` + `choose` + `parallel gateway ... await ...`
- 代码生成：条件路由、并行等待、后继节点启用逻辑

为什么必须有：

- 真实业务流程几乎不会是纯线性
- 代码生成器需要知道状态机如何分叉和汇聚

### 2.5 状态

模型必须表达：

- 哪些元素可执行
- 哪些已完成
- 哪些尚未激活
- 在多步协作中当前流程走到哪里

系统中的对应实现：

- BPMN 中并没有完整显式状态枚举
- 状态语义主要在 DSL 中统一抽象为：
  - `INACTIVE`
  - `READY`
  - `PENDING_CONFIRMATION`
  - `DONE`
- 代码生成器再把它映射到：
  - Fabric runtime state
  - Solidity contract state

为什么必须有：

- 自动生成的链上程序本质是状态机
- 不抽象状态，就无法生成稳定的执行逻辑

### 2.6 决策

模型必须表达：

- 哪些流程节点需要业务规则判断
- 这些判断属于普通条件还是外部决策表

系统中的对应实现：

- BPMN：`businessRuleTask`
- 解析器对象：`BusinessRuleTask`
- DSL：`businessrules { businessrule ... }`
- 代码生成：规则调用点、继续执行点、结果写回逻辑

为什么必须有：

- 复杂业务流程里，分支不只是固定判断，还会依赖决策表
- 没有决策节点，就无法把 DMN 纳入自动生成

### 2.7 决策输入输出

模型必须表达：

- 决策读取哪些业务变量
- 决策输出哪些结果
- 输出结果写回哪里

系统中的对应实现：

- 当前 BPMN 主要通过 `businessRuleTask.documentation` 的 JSON 表达
- DSL：`input mapping` / `output mapping`
- DMN：`input` / `output`
- 代码生成：规则调用参数准备、结果落状态、后继网关判断

为什么必须有：

- 决策如果没有输入输出绑定，就只是一个“空节点”
- 无法与流程状态和后续分支真正连接

## 3. 这些需求在系统中的层次分布

可以把这些建模需求分成三层：

### 3.1 BPMN 直接表达的

- 多企业参与方
- 消息
- 开始 / 结束
- 分支
- 决策节点

### 3.2 BPMN 扩展字段表达的

- 消息数据字段
- 决策输入输出

当前主要通过 `documentation` JSON 携带。

### 3.3 DSL / 运行时补充表达的

- 统一状态模型
- 全局变量
- 输入输出映射
- 可执行的流程动作语义

## 4. 一句话总结

如果要生成可执行区块链协作程序，模型至少必须把：

- 参与方
- 消息
- 生命周期
- 控制分支
- 状态
- 决策节点
- 决策数据绑定

这七类信息表达完整；否则生成器无法把业务流程还原成可执行状态机。

