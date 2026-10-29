# 面向区块链代码生成的建模约束

## 1. 这类约束的含义

有些约束是为了业务建模本身成立；
有些约束则更像是为了后续 **自动代码生成**、**状态机执行**、**链上安全** 而增加的。

`newTranslator` 中后者尤其重要，因为目标不是“只画图”，而是“把图稳定地生成成链码/合约”。

## 2. 哪些约束明显是为代码生成服务的

下面这些约束，不只是业务语义要求，更是为了保证生成器可以稳定输出可执行代码。

### 2.1 每个合约 section 最多一次

对应约束：

- `SectionAtMostOnceEachKind`
- `HasExactlyOneFlowSection`

原因：

- 代码生成器会把 `participants/globals/messages/gateways/events/businessrules/flows` 当成唯一结构块处理
- 如果同类 section 出现多次，容易造成拼接歧义、覆盖顺序问题或生成结果不确定

### 2.2 必须有且只有一个起点

对应约束：

- `ExactlyOneStartFlow`
- `StartEventMustBeReady`
- `ExactlyOneReadyEventAndMatchesStart`

原因：

- 自动生成的区块链流程实例需要唯一入口
- 否则实例初始化时无法确定第一步启用哪个节点

### 2.3 所有 flow 引用必须落在同一合约内部

对应约束：

- `FlowRefsStayInSameContract`
- `ActionsReferenceOwnElementsAndGlobals`

原因：

- 代码生成器默认生成的是一个闭合的本地状态机
- 如果一个 flow 引用到未定义元素或跨 contract 元素，生成代码就会出现悬空引用

### 2.4 消息的 sender / receiver 必须合法且不同

对应约束：

- `MessageParticipantsInContract`
- `SenderNotReceiver`
- `MessagesRequireAtLeastTwoParticipants`

原因：

- 代码生成器需要据此生成权限检查、消息发送接口和接收者约束
- 若发送方与接收方相同，消息协作语义会退化甚至与生成逻辑冲突

### 2.5 决策输入输出映射必须引用全局变量

对应约束：

- `RuleMappingsReferenceOwnGlobals`
- `InputMappingParamUnique`
- `OutputMappingParamUnique`
- `HasAtLeastOneInputMapping`

原因：

- 决策执行前，生成器需要从全局状态槽位取输入
- 决策执行后，生成器需要把结果写回全局状态槽位
- 如果没有映射或映射重复，代码生成就无法稳定落地

### 2.6 网关分支必须可判定、可生成

对应约束：

- `ChooseImpliesExclusiveGateway`
- `ExactlyOneGatewayFlowMode`
- `ElseBranchUniqueAndLast`
- `CompareBranchesNoDuplicateConditions`
- `RelationOperatorAllowed`
- `CompareLiteralTypeMatchesGlobalType`
- `NotSupportedByCurrentCodeGen`

原因：

- 生成器必须把分支逻辑编译成明确的 `if / else` 或等价状态机判断
- 表达式分支之所以被禁止，不是 BPMN 不允许，而是**当前代码生成器还没有实现**

这类约束是典型的“为了代码生成服务”的约束。

### 2.7 并行汇聚必须是可实现的并行等待

对应约束：

- `ParallelGatewayTypeRequired`
- `SourcesAtLeastTwoAndDistinct`
- `SourcesNotContainJoinGateway`

原因：

- 自动生成代码需要知道“等哪些前驱完成后再继续”
- 如果来源集合不清晰或不合法，就无法正确实现并行 join

### 2.8 字面量类型必须和全局变量类型匹配

对应约束：

- `SetLiteralTypeMatchesGlobalType`
- `CompareLiteralTypeMatchesGlobalType`
- `ExactlyOneLiteralKind`

原因：

- Fabric Go 与 Solidity 都是强类型运行时
- 如果 DSL 层允许类型随意漂移，代码生成后就会产生编译错误或运行时歧义

### 2.9 同一 flow 中不能同时 enable 和 disable 同一元素

对应约束：

- `NoEnableDisableConflict`

原因：

- 对同一元素同时启用又禁用，业务上含糊，代码生成时也无法定义唯一语义

## 3. 哪些约束既有业务意义，也有生成意义

有些约束同时服务于建模正确性和代码生成。

### 3.1 参与方身份约束

- `MspX509Paired`
- `MultiBoundsPaired`
- `MultiBoundsOrder`
- `MultiFlagConsistent`
- `AttributeKeysUnique`

业务意义：

- 保证参与方身份和多实例配置自洽

生成意义：

- Fabric 侧身份校验、组织绑定、多实例逻辑需要可执行的结构化配置

### 3.2 命名唯一性约束

- `UniqueContractNames`
- `UniqueNamesPerKind`

业务意义：

- 避免模型歧义

生成意义：

- 避免生成 DSL、Go、Solidity 标识符冲突

## 4. 从区块链自动生成角度看，最关键的约束

如果只从“后续代码生成”角度排序，最关键的是：

1. 唯一起点与闭合 flow 引用
2. 决策输入输出必须映射到全局变量
3. 分支条件必须可类型检查、可编译
4. 并行汇聚必须可枚举等待源
5. 所有动作不能存在语义冲突

这些约束决定了模型能否真正被编译成链上状态机。

## 5. 一个本质判断

面向区块链代码生成的建模，不是“BPMN 画得像就行”，而是模型必须满足：

- 可确定初始化
- 可确定状态推进
- 可确定权限边界
- 可确定数据类型
- 可确定条件分支
- 可确定结束条件

所以很多看起来“偏工程”的约束，本质上都是为了让业务模型变成 **可编译、可验证、可部署** 的链上程序。

## 6. 一句话总结

这些建模约束之所以存在，不只是为了让模型“规范”，更是为了让 `newTranslator` 能把流程图稳定地翻译成：

- Fabric 的 Go 链码状态机
- Geth/EVM 的 Solidity 合约状态机

换句话说，它们服务的是 **从模型到代码的可执行性**。
