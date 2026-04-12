# 实验二断言表

这份文档是 `config/assertion_table.yaml` 的可读版说明，用于集中展示实验二的断言设计。

如果你想看机器可读配置，请看：

- [assertion_table.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/assertion_table.yaml:1)
- [case_assertion_matrix.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/case_assertion_matrix.yaml:1)

## 1. 断言表来源

本断言表不是手工随意编的，而是基于 `newTranslator` 的真实定义整理而来，主要来源包括：

- grammar：`src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`
- 约束：`src/newTranslator/MDAcheck/check.ocl`

因此，这张表的作用是把：

1. `newTranslator` 中已有的 grammar / OCL 规则
2. 实验二中的正例 / 负例
3. 最终验证报告

统一到同一套语义口径下。

## 2. 字段说明

每条断言包含以下字段：

- `id`
  断言编号，便于在报告中引用
- `title`
  断言标题
- `dimension`
  断言维度，例如 `structural`、`reference`、`syntax`、`semantic`
- `mode`
  适用场景，`positive` 表示主要由正例覆盖，`both` 表示正负例都可涉及，`negative` 表示主要作为不支持项或拒绝项
- `source.file`
  规则来源文件
- `source.rule`
  规则来源名
- `description`
  断言语义说明

## 3. 断言分类总览

### 3.1 结构类断言

| 编号 | 标题 | 来源 |
| --- | --- | --- |
| A01 | 模型至少包含一个 contract | `Model::AtLeastOneContract` |
| A02 | 同类元素名称唯一 | `Contract::UniqueNamesPerKind` |
| A07 | 合约必须且仅有一个 flow section | `Contract::HasExactlyOneFlowSection` |

### 3.2 引用合法性断言

| 编号 | 标题 | 来源 |
| --- | --- | --- |
| A03 | message 的发送方和接收方必须属于本合约 | `Contract::MessageParticipantsInContract` |
| A05 | businessrule 映射必须引用本合约 globals | `Contract::RuleMappingsReferenceOwnGlobals` |
| A06 | oracletask 输出映射必须引用本合约 globals | `Contract::OracleTaskMappingsReferenceOwnGlobals` |
| A10 | start flow target 必须属于本合约 | `Contract::StartFlowTargetInContract` |
| A11 | 所有 flow 引用必须局限在本合约内 | `Contract::FlowRefsStayInSameContract` |
| A12 | action 引用的元素与变量必须存在 | `Contract::ActionsReferenceOwnElementsAndGlobals` |
| A14 | parallel await 源元素至少两个、互异且存在 | `ParallelJoin::SourcesAtLeastTwoAndDistinct` |

### 3.3 语法类断言

| 编号 | 标题 | 来源 |
| --- | --- | --- |
| A16 | gateway flow 只能二选一使用 then 或 choose | `GatewayFlow::ExactlyOneGatewayFlowMode` |
| A17 | gateway type 必须取 grammar 允许值 | `GatewayType` |

### 3.4 语义类断言

| 编号 | 标题 | 来源 |
| --- | --- | --- |
| A04 | message 的发送方与接收方不能相同 | `Message::SenderNotReceiver` |
| A08 | 合约必须且仅有一个 start flow | `Contract::ExactlyOneStartFlow` |
| A09 | start event 必须 READY | `Contract::StartEventMustBeReady` |
| A13 | parallel join 必须绑定 parallel gateway | `ParallelJoin::ParallelGatewayTypeRequired` |
| A15 | choose 分支只能用于 exclusive gateway | `GatewayFlow::ChooseImpliesExclusiveGateway` |
| A18 | set 字面量类型必须匹配目标全局变量类型 | `SetGlobalAction::SetLiteralTypeMatchesGlobalType` |
| A19 | gateway compare 分支字面量类型必须匹配变量类型 | `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType` |

### 3.5 当前代码生成限制

| 编号 | 标题 | 来源 |
| --- | --- | --- |
| A20 | GatewayExpressionBranch 当前代码生成器不支持 | `GatewayExpressionBranch::NotSupportedByCurrentCodeGen` |

## 4. 全量断言明细

| 编号 | 标题 | 维度 | 模式 | 来源文件 | 来源规则 |
| --- | --- | --- | --- | --- | --- |
| A01 | 模型至少包含一个 contract | structural | positive | `check.ocl` | `Model::AtLeastOneContract` |
| A02 | 同类元素名称唯一 | structural | positive | `check.ocl` | `Contract::UniqueNamesPerKind` |
| A03 | message 的发送方和接收方必须属于本合约 | reference | both | `check.ocl` | `Contract::MessageParticipantsInContract` |
| A04 | message 的发送方与接收方不能相同 | semantic | positive | `check.ocl` | `Message::SenderNotReceiver` |
| A05 | businessrule 映射必须引用本合约 globals | reference | both | `check.ocl` | `Contract::RuleMappingsReferenceOwnGlobals` |
| A06 | oracletask 输出映射必须引用本合约 globals | reference | positive | `check.ocl` | `Contract::OracleTaskMappingsReferenceOwnGlobals` |
| A07 | 合约必须且仅有一个 flow section | structural | positive | `check.ocl` | `Contract::HasExactlyOneFlowSection` |
| A08 | 合约必须且仅有一个 start flow | semantic | positive | `check.ocl` | `Contract::ExactlyOneStartFlow` |
| A09 | start event 必须 READY | semantic | positive | `check.ocl` | `Contract::StartEventMustBeReady` |
| A10 | start flow target 必须属于本合约 | reference | both | `check.ocl` | `Contract::StartFlowTargetInContract` |
| A11 | 所有 flow 引用必须局限在本合约内 | reference | both | `check.ocl` | `Contract::FlowRefsStayInSameContract` |
| A12 | action 引用的元素与变量必须存在 | reference | both | `check.ocl` | `Contract::ActionsReferenceOwnElementsAndGlobals` |
| A13 | parallel join 必须绑定 parallel gateway | semantic | positive | `check.ocl` | `ParallelJoin::ParallelGatewayTypeRequired` |
| A14 | parallel await 源元素至少两个、互异且存在 | reference | both | `check.ocl` | `ParallelJoin::SourcesAtLeastTwoAndDistinct` |
| A15 | choose 分支只能用于 exclusive gateway | semantic | positive | `check.ocl` | `GatewayFlow::ChooseImpliesExclusiveGateway` |
| A16 | gateway flow 只能二选一使用 then 或 choose | syntax | positive | `check.ocl` | `GatewayFlow::ExactlyOneGatewayFlowMode` |
| A17 | gateway type 必须取 grammar 允许值 | syntax | both | `b2c.tx` | `GatewayType` |
| A18 | set 字面量类型必须匹配目标全局变量类型 | semantic | positive | `check.ocl` | `SetGlobalAction::SetLiteralTypeMatchesGlobalType` |
| A19 | gateway compare 分支字面量类型必须匹配变量类型 | semantic | positive | `check.ocl` | `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType` |
| A20 | GatewayExpressionBranch 当前代码生成器不支持 | codegen_limit | negative | `check.ocl` | `GatewayExpressionBranch::NotSupportedByCurrentCodeGen` |

## 5. 正例与负例如何使用断言表

实验二里，断言表不是孤立存在的，而是和案例矩阵绑定：

- 正例：
  使用 `case_assertion_matrix.yaml` 中的 `positive_cases.<case>.covers`
  表示该样例主要覆盖哪些断言
- 负例：
  使用 `case_assertion_matrix.yaml` 中的 `negative_cases.<case>.targets`
  表示该样例主要用来触发哪些断言失败

这意味着：

- 正例保留现有 case，不需要重写
- 负例也不是随意举例，而是有明确断言目标
- `outputs/summary.md` 和各 case 的 `report.md` 都可以回溯到断言编号

## 6. 当前负例生成器与断言映射

当前 `tools/generate_negative_cases.py` 已经根据统一断言表中的 `negative_generators` 生成负例，映射关系如下：

| 负例生成器 | 对应断言 |
| --- | --- |
| `missing_flow_target` | A10, A11 |
| `missing_set_variable` | A12 |
| `invalid_gateway_type` | A17 |
| `missing_message_trigger` | A11 |
| `missing_message_sender` | A03 |
| `missing_rule_mapping_global` | A05 |
| `missing_parallel_source` | A11, A14 |
| `missing_start_event` | A08, A11 |

## 7. 当前使用建议

如果你是从实验设计角度看这个项目，建议按这个顺序阅读：

1. 看本文件，先掌握断言体系
2. 看 [case_assertion_matrix.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/case_assertion_matrix.yaml:1)，理解案例和断言的关系
3. 看 [README.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/README.md:1)，理解工具链怎么运行
4. 看 [outputs/summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/summary.md:1)，理解当前实验结果

如果你是从实现角度继续开发，建议优先看：

1. [run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/run_exp2.py:1)
2. [tools/generate_negative_cases.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/generate_negative_cases.py:1)
3. [config/assertion_table.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/assertion_table.yaml:1)
4. [config/case_assertion_matrix.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/case_assertion_matrix.yaml:1)
