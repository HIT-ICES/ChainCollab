# B2CDSL 元模型说明

## 1. 是否有 textX 元模型文件

有。

当前 `newTranslator` 使用的 textX 元模型文件就是：

- [b2cdsl_grammar.tx](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_grammar.tx)

它的源码位置是：

- `src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`

## 2. textX 装配方式

### 2.1 语言注册入口

`src/newTranslator/DSL/B2CDSL/b2cdsl/__init__.py` 中定义了：

- `@language('b2c', '*.b2c')`

并在 `b2c_language()` 中调用：

- `metamodel_from_file(os.path.join(current_dir, 'b2c.tx'))`

这说明：

- `.b2c` 是该 DSL 的注册扩展名
- `b2c.tx` 是真正的元模型来源

### 2.2 运行时加载

系统运行时还会直接加载该 grammar：

- `generator/translator.py`
- `service/api.py`
- `generator/b2c_to_solidity.py`
- `nt.sh`

都通过 `metamodel_from_file()` 加载 `b2c.tx`。

这意味着：

- 这不是“开发样例 grammar”
- 而是系统生产链路真正使用的元模型文件

## 3. 元模型由哪些核心概念组成

### 3.1 顶层结构

- `Model`
- `Contract`
- `ContractSection`

含义：

- 一个模型可包含多个合约
- 每个合约由若干 section 组成

### 3.2 结构性 section

元模型中定义了以下 section：

- `ParticipantSection`
- `GlobalSection`
- `MessageSection`
- `GatewaySection`
- `EventSection`
- `BusinessRuleSection`
- `OracleTaskSection`
- `FlowSection`

含义：

- 把协作流程拆成结构块，便于生成器按类别处理

### 3.3 业务元素

元模型中定义的核心元素包括：

- `Participant`
- `GlobalVar`
- `Message`
- `Gateway`
- `Event`
- `BusinessRule`
- `OracleTask`

这些元素共同构成“静态结构”。

### 3.4 行为元素

元模型中定义的动态行为包括：

- `StartFlow`
- `MessageFlow`
- `GatewayFlow`
- `RuleFlow`
- `OracleTaskFlow`
- `EventFlow`
- `ParallelJoin`

以及动作：

- `EnableAction`
- `DisableAction`
- `SetGlobalAction`

这些元素共同构成“状态机推进逻辑”。

## 4. 为什么说它是“元模型”

因为 `b2c.tx` 不是单个实例，而是定义了：

- 哪些概念存在
- 概念之间如何引用
- 哪些字段是标量
- 哪些字段是集合
- 哪些字段是可选

例如：

- `Message.sender=[Participant]`
- `BusinessRule.inputMappings+=ParamMapping*`
- `ParallelJoin.sources+=[FlowElement][',']`

这些规则决定了：

- DSL 实例文本如何被解析成对象图
- 代码生成器如何遍历这些对象图

## 5. 元模型在系统中的三个作用

### 5.1 语法约束

它决定：

- 合法的 B2CDSL 文本长什么样

### 5.2 解析模型

它决定：

- textX 如何把 DSL 文本变成 Python 对象模型

### 5.3 代码生成与校验基础

它决定：

- Go / Solidity 生成器如何读取结构
- Ecore / XMI / OCL 校验链如何导出和验证

## 6. 与 Ecore/OCL 的关系

`MDAcheck` 目录已经把这套 textX 元模型接到了 EMF/Ecore 链路：

- `export_b2c_ecore.py`
- `b2c_to_xmi.py`

因此 B2CDSL 元模型不仅用于：

- 解析 DSL

还用于：

- 导出 `b2c.ecore`
- 导出实例 XMI
- 做 OCL 约束校验

这说明它不仅是生成器输入层，也是模型验证层的基础。

## 7. 当前实现的一个重要特点

这套元模型不是“直接照搬 BPMN/DMN 标准”。

它是一个**面向区块链协作流程代码生成的工程化元模型**，特点包括：

- 把流程元素与执行状态统一抽象
- 把规则节点和 Oracle 节点纳入统一流转框架
- 把 BPMN 控制流转成可编译的 flow 规则
- 把 DMN 输入输出映射成全局变量引用

## 8. 一句话总结

`b2c.tx` 就是 `newTranslator` 中 B2CDSL 的 textX 元模型文件，它定义了整个系统从 DSL 解析、代码生成到 OCL 校验所依赖的核心抽象结构。

