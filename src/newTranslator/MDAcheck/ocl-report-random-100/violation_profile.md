# Violation Profile

- Total models: 100
- OK: 0
- Not OK: 100
- Total violations: 10333
- Distinct diagnostics/rules: 33

## OCL Invariants

| Rule | Violated models | Total violations | Avg/all models | Avg/violated model | Meaning |
|---|---:|---:|---:|---:|---|
| `LiteralExpr::ExactlyOneLiteralKind` | 95 | 2937 | 29.3700 | 30.9158 | LiteralExpr 是“互斥选择”，三个字段只能出现一个 |
| `GatewayExpressionBranch::NotSupportedByCurrentCodeGen` | 65 | 208 | 2.0800 | 3.2000 | 违反约束：GatewayExpressionBranch::NotSupportedByCurrentCodeGen |
| `GatewayCompareBranch::RelationOperatorAllowed` | 58 | 174 | 1.7400 | 3.0000 | relation 仅允许 6 种比较运算符 |
| `Message::SenderNotReceiver` | 48 | 268 | 2.6800 | 5.5833 | 违反约束：Message::SenderNotReceiver |
| `Participant::MultiBoundsOrder` | 41 | 253 | 2.5300 | 6.1707 | 违反约束：Participant::MultiBoundsOrder |
| `GatewayFlow::ExactlyOneGatewayFlowMode` | 41 | 60 | 0.6000 | 1.4634 | 语法是二选一：要么 then actions，要么 choose branches（不能两者都有/都没有） |
| `Contract::ExactlyOneReadyEventAndMatchesStart` | 35 | 145 | 1.4500 | 4.1429 | READY 的事件只能有一个，并且必须等于 start flow 的 start event |
| `Contract::SectionAtMostOnceEachKind` | 34 | 34 | 0.3400 | 1.0000 | 违反约束：Contract::SectionAtMostOnceEachKind |
| `Contract::ExactlyOneStartFlow` | 32 | 139 | 1.3900 | 4.3438 | 只允许 1 个起点；并要求 start event 显式 READY（与你示例/生成器取 start_event 的逻辑一致） |
| `Participant::MultiFlagConsistent` | 31 | 105 | 1.0500 | 3.3871 | 违反约束：Participant::MultiFlagConsistent |
| `RuleFlow::NoEnableDisableConflict` | 30 | 39 | 0.3900 | 1.3000 | 同一条 flow 里，不要对同一 target 同时 enable+disable（对生成代码/可读性更安全） |
| `MessageFlow::NoEnableDisableConflict` | 29 | 34 | 0.3400 | 1.1724 | 同一条 flow 里，不要对同一 target 同时 enable+disable（对生成代码/可读性更安全） |
| `Contract::FlowSectionNotEmpty` | 28 | 131 | 1.3100 | 4.6786 | 违反约束：Contract::FlowSectionNotEmpty |
| `GatewayFlow::ElseBranchUniqueAndLast` | 27 | 33 | 0.3300 | 1.2222 | 违反约束：GatewayFlow::ElseBranchUniqueAndLast |
| `Contract::HasExactlyOneFlowSection` | 26 | 131 | 1.3100 | 5.0385 | 对生成/执行更友好：要求合约包含且仅包含一个 flows 区块 |
| `EventFlow::NoEnableDisableConflict` | 23 | 29 | 0.2900 | 1.2609 | 同一条 flow 里，不要对同一 target 同时 enable+disable（对生成代码/可读性更安全） |
| `BusinessRule::HasAtLeastOneInputMapping` | 20 | 88 | 0.8800 | 4.4000 | 至少要有一个输入映射（否则业务规则无法从合约状态拿到参数） |
| `ParallelJoin::NoEnableDisableConflict` | 19 | 29 | 0.2900 | 1.5263 | 同一条 flow 里，不要对同一 target 同时 enable+disable（对生成代码/可读性更安全） |
| `ParallelJoin::ParallelGatewayTypeRequired` | 17 | 25 | 0.2500 | 1.4706 | 并行汇聚语义：parallel join 只能绑定 parallel gateway；sources 至少两个且不重复 |
| `OracleTaskFlow::NoEnableDisableConflict` | 17 | 20 | 0.2000 | 1.1765 | 同一条 flow 里，不要对同一 target 同时 enable+disable（对生成代码/可读性更安全） |
| `Contract::ActionsReferenceOwnElementsAndGlobals` | 15 | 15 | 0.1500 | 1.0000 | 所有 enable/disable 的目标必须在本合约内；所有 set 的 var 必须在本合约 globals 内 |
| `Contract::FlowRefsStayInSameContract` | 15 | 15 | 0.1500 | 1.0000 | textX 默认作用域可能跨 contract；这里强制“本合约内自洽” |
| `GatewayFlow::ChooseImpliesExclusiveGateway` | 12 | 13 | 0.1300 | 1.0833 | choose 分支：else 最多一个且必须放最后；并且（当前 Go/Sol 生成器）不支持 GatewayExpressionBranch |
| `ParallelJoin::SourcesNotContainJoinGateway` | 11 | 15 | 0.1500 | 1.3636 | 违反约束：ParallelJoin::SourcesNotContainJoinGateway |
| `Contract::OracleTaskMappingsReferenceOwnGlobals` | 8 | 8 | 0.0800 | 1.0000 | OracleTask 的输出映射也必须引用“本合约 globals”里的变量（避免跨 contract 串引用） |
| `Contract::MessageParticipantsInContract` | 6 | 6 | 0.0600 | 1.0000 | Message 的 sender/receiver 必须来自本合约 participants（避免跨 contract 串引用） |
| `Contract::MessagesRequireAtLeastTwoParticipants` | 6 | 6 | 0.0600 | 1.0000 | 如果定义了 message，则 participant 至少 2 个（否则必然出现 sender=receiver 或无法建模通信） |
| `Contract::RuleMappingsReferenceOwnGlobals` | 6 | 6 | 0.0600 | 1.0000 | 业务规则映射必须引用“本合约 globals”里的变量（避免跨 contract 串引用） |
| `Contract::StartFlowTargetInContract` | 6 | 6 | 0.0600 | 1.0000 | StartFlow 的 target 也必须是本合约内元素 |
| `Contract::StartEventMustBeReady` | 5 | 5 | 0.0500 | 1.0000 | 违反约束：Contract::StartEventMustBeReady |
| `ParallelJoin::SourcesAtLeastTwoAndDistinct` | 3 | 7 | 0.0700 | 2.3333 | 违反约束：ParallelJoin::SourcesAtLeastTwoAndDistinct |

## Non-OCL Diagnostics

| Rule | Kind | Violated models | Total violations | Avg/all models | Avg/violated model | Meaning |
|---|---|---:|---:|---:|---:|---|
| `EMF_REQUIRED_FEATURE` | EMF | 89 | 5252 | 52.5200 | 59.0112 | 必填字段未设置：var |
| `UNKNOWN` | UNKNOWN | 45 | 97 | 0.9700 | 2.1556 |  |
