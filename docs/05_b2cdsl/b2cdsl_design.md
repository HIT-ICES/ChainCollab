# B2CDSL 设计文档

## 1. 设计目标

B2CDSL（Business-to-Chain DSL）是 `newTranslator` 中用于连接：

- BPMN 协作流程模型
- DMN 决策模型
- 区块链目标代码生成

的**稳定中间表示**。

它的核心设计目标不是“再造一种流程语言”，而是解决三个问题：

1. 如何把 BPMN/DMN 的业务语义收敛成统一结构
2. 如何把这种结构同时喂给 Fabric Go 链码生成器与 Solidity 生成器
3. 如何在代码生成前对模型做验证、检查与约束分析

## 2. 为什么需要 B2CDSL

如果系统直接做：

- BPMN -> Fabric
- BPMN -> Solidity

那么每增加一个目标平台，就要重写一遍映射逻辑，问题会包括：

- 平台耦合严重
- 规则复用困难
- 校验链路不统一
- DMN 绑定方式难以抽象

因此系统选择先构造一个平台无关但执行导向明确的中间层，即 B2CDSL。

## 3. B2CDSL 的设计原则

### 3.1 平台无关，但不脱离执行

B2CDSL 不直接写：

- Fabric 特有运行时 API
- Solidity 语法细节

但它也不是纯概念模型，而是明确描述：

- 参与方
- 消息
- 事件
- 网关
- 业务规则
- Oracle 任务
- 流程状态推进

这样它既能保持跨平台抽象，又足够支撑代码生成。

### 3.2 结构化，而不是图形化

BPMN/DMN 都是图形导向建模语言，而代码生成更需要结构化语义。

因此 B2CDSL 的重点不在布局信息，而在：

- 元素集合
- 元素关系
- 状态
- 流转规则
- 输入输出映射

### 3.3 显式表达状态机语义

区块链智能合约本质上是状态机。

所以 B2CDSL 明确抽象了：

- `INACTIVE`
- `READY`
- `PENDING_CONFIRMATION`
- `DONE`

并通过 `flows` 描述状态推进逻辑。

### 3.4 决策与流程分离，但可绑定

系统不把 DMN 规则直接揉进 BPMN 控制流，而是：

- 用 `businessrule` 单独表达规则节点
- 用 `input mapping` / `output mapping` 与全局状态绑定
- 再让流程分支读取规则结果

这是 B2CDSL 设计里很关键的一点。

## 4. 为什么设计这些语法块

### 4.1 `contract`

作用：

- 作为一个完整业务协作应用的封装边界

为什么需要：

- 后续代码生成器需要一个明确的顶层输出单元
- 同时便于多合约场景扩展

### 4.2 `participants`

作用：

- 显式表示多企业参与方

为什么需要：

- BPMN 里的协作语义必须被保留下来
- Fabric / Solidity 都需要明确身份边界

### 4.3 `globals`

作用：

- 统一承载消息字段、决策输入输出和流程共享变量

为什么需要：

- 规则结果、消息内容和分支判断都需要可持久化状态槽位

### 4.4 `messages`

作用：

- 表达跨参与方业务消息

为什么需要：

- 区块链协作流程的核心就是多主体消息驱动
- 后续需要生成交易调用接口

### 4.5 `gateways`

作用：

- 表达条件分支、事件分支和并行分支

为什么需要：

- BPMN 控制流必须被翻译成可执行状态转移

### 4.6 `events`

作用：

- 表达开始/结束及可被流程引用的事件节点

为什么需要：

- 代码生成时必须明确生命周期入口和终点

### 4.7 `businessrules`

作用：

- 表达流程中的 DMN 决策节点

为什么需要：

- 决策逻辑不能只留在 BPMN 图里，必须被提升为可生成结构

### 4.8 `oracletasks`

作用：

- 表达外部数据获取或计算任务

为什么需要：

- 区块链运行时经常需要链外数据或链外计算
- 这类能力不能硬塞进普通消息或规则节点

### 4.9 `flows`

作用：

- 统一表达流程推进逻辑

为什么需要：

- 仅有结构元素不足以生成状态机
- 还需要显式说明“何时启用谁、何时关闭谁、何时设置变量”

## 5. B2CDSL 在系统中的位置

见图：

- [b2cdsl_position_in_pipeline.png](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_position_in_pipeline.png)

它位于整条链路的中间：

`BPMN / DMN -> parser / translator -> B2CDSL -> textX model -> Go / Solidity generator`

也就是说，B2CDSL 不是最终产物，而是整个系统最关键的**中间枢纽**。

## 6. 设计收益

B2CDSL 的设计带来几个直接收益：

- 解耦 BPMN/DMN 解析与目标代码生成
- 让 Fabric 与 Solidity 共享同一中间语义层
- 便于使用 textX 做元模型管理
- 便于导出 Ecore/XMI 进行 OCL 校验
- 便于后续扩展新的目标平台或新任务类型

## 7. 对当前实现的一个准确判断

当前 B2CDSL 不是纯理论 DSL，而是已经被系统实际使用：

- `generator/translator.py` 会产出 B2CDSL 文本
- `service/api.py` 会加载 B2CDSL 元模型并编译
- `CodeGenerator/b2cdsl-go` / `b2cdsl-solidity` 会消费它生成目标代码
- `MDAcheck` 会把它接入 Ecore/OCL 校验链

所以它在系统里是一个**真正运行中的元模型层**，而不是只存在于论文里的抽象设计。

