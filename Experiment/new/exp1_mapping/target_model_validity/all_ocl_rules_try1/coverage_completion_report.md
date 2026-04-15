# OCL Negative Coverage Completion Report

## Summary

This dataset keeps the existing random negatives under [random_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/random_negative) and replaces the old mutation set with a new coverage-oriented mutation set under [targeted_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/targeted_negative).

Current directory contents:

- positives: [positive](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/positive), `11` files
- retained random negatives: [random_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/random_negative), `299` files
- rebuilt mutation negatives: [targeted_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/targeted_negative), `140` files

The rebuilt mutation corpus comes from [bpmn-mutations/xmi](/root/code/ChainCollab/src/newTranslator/MDAcheck/bpmn-mutations/xmi) and was validated with:

- mutation manifest: [manifest.json](/root/code/ChainCollab/src/newTranslator/MDAcheck/bpmn-mutations/manifest.json)
- mutation report: [report.json](/root/code/ChainCollab/src/newTranslator/MDAcheck/ocl-report-bpmn-mutations/report.json)
- mutation markdown report: [report.md](/root/code/ChainCollab/src/newTranslator/MDAcheck/ocl-report-bpmn-mutations/report.md)

## Mutation Set

The new mutation set contributes `10` negatives for each of these 14 rules:

- `Model::AtLeastOneContract`
- `Model::UniqueContractNames`
- `Contract::UniqueNamesPerKind`
- `Participant::MspX509Paired`
- `Participant::MultiBoundsPaired`
- `Participant::MultiBoundsOrder`
- `Participant::AttributeKeysUnique`
- `Message::SenderNotReceiver`
- `BusinessRule::InputMappingParamUnique`
- `BusinessRule::OutputMappingParamUnique`
- `Contract::StartDoesNotEnableItself`
- `GatewayFlow::CompareBranchesNoDuplicateConditions`
- `SetGlobalAction::SetLiteralTypeMatchesGlobalType`
- `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType`

Validation status for the rebuilt mutation set:

- all `140` mutation files are negative samples
- all 14 intended rules are hit `10/10`
- `Model::AtLeastOneContract` samples also carry `UNKNOWN`; this comes from evaluating an empty-contract model, but the intended OCL rule is still present in every such sample

## Combined Coverage

The table below uses:

- random count: files already kept in `random_negative`
- mutation count: files in the rebuilt `targeted_negative`
- total: random + mutation

Every OCL rule now has at least `10` negative samples in the combined dataset.

| OCL rule | Random | Mutation | Total |
| --- | ---: | ---: | ---: |
| `Model::AtLeastOneContract` | 0 | 10 | 10 |
| `Model::UniqueContractNames` | 0 | 10 | 10 |
| `Contract::SectionAtMostOnceEachKind` | 10 | 0 | 10 |
| `Contract::HasExactlyOneFlowSection` | 10 | 0 | 10 |
| `Contract::MessagesRequireAtLeastTwoParticipants` | 10 | 0 | 10 |
| `Contract::UniqueNamesPerKind` | 0 | 10 | 10 |
| `Contract::MessageParticipantsInContract` | 10 | 0 | 10 |
| `Participant::MspX509Paired` | 0 | 10 | 10 |
| `Participant::MultiBoundsPaired` | 0 | 10 | 10 |
| `Participant::MultiBoundsOrder` | 2 | 10 | 12 |
| `Participant::MultiFlagConsistent` | 10 | 0 | 10 |
| `Participant::AttributeKeysUnique` | 0 | 10 | 10 |
| `Message::SenderNotReceiver` | 2 | 10 | 12 |
| `BusinessRule::InputMappingParamUnique` | 0 | 10 | 10 |
| `BusinessRule::OutputMappingParamUnique` | 0 | 10 | 10 |
| `BusinessRule::HasAtLeastOneInputMapping` | 10 | 0 | 10 |
| `Contract::RuleMappingsReferenceOwnGlobals` | 10 | 0 | 10 |
| `Contract::OracleTaskMappingsReferenceOwnGlobals` | 10 | 0 | 10 |
| `Contract::FlowSectionNotEmpty` | 10 | 0 | 10 |
| `Contract::FlowRefsStayInSameContract` | 10 | 0 | 10 |
| `Contract::ExactlyOneStartFlow` | 10 | 0 | 10 |
| `Contract::StartEventMustBeReady` | 10 | 0 | 10 |
| `Contract::StartDoesNotEnableItself` | 5 | 10 | 15 |
| `Contract::ExactlyOneReadyEventAndMatchesStart` | 10 | 0 | 10 |
| `Contract::StartFlowTargetInContract` | 10 | 0 | 10 |
| `Contract::ActionsReferenceOwnElementsAndGlobals` | 10 | 0 | 10 |
| `ParallelJoin::ParallelGatewayTypeRequired` | 10 | 0 | 10 |
| `ParallelJoin::SourcesAtLeastTwoAndDistinct` | 10 | 0 | 10 |
| `ParallelJoin::SourcesNotContainJoinGateway` | 10 | 0 | 10 |
| `GatewayFlow::ChooseImpliesExclusiveGateway` | 10 | 0 | 10 |
| `GatewayFlow::ExactlyOneGatewayFlowMode` | 10 | 0 | 10 |
| `GatewayFlow::ElseBranchUniqueAndLast` | 10 | 0 | 10 |
| `GatewayFlow::CompareBranchesNoDuplicateConditions` | 0 | 10 | 10 |
| `GatewayExpressionBranch::NotSupportedByCurrentCodeGen` | 10 | 0 | 10 |
| `GatewayCompareBranch::RelationOperatorAllowed` | 10 | 0 | 10 |
| `SetGlobalAction::SetLiteralTypeMatchesGlobalType` | 0 | 10 | 10 |
| `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType` | 0 | 10 | 10 |
| `LiteralExpr::ExactlyOneLiteralKind` | 10 | 0 | 10 |
| `MessageFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `RuleFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `EventFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `OracleTaskFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `ParallelJoin::NoEnableDisableConflict` | 10 | 0 | 10 |

## Notes

- The retained random negatives were not regenerated; they are the samples already produced during the earlier `generate_balanced_dataset.py` run.
- The mutation set was rebuilt from the current positive pool and copied into this dataset's `targeted_negative` directory.
- This report is the authoritative summary for the completed coverage state of `all_ocl_rules_try1`.

---

# 中文版说明

## 总体情况

这个数据集保留了原有的随机负例目录 [random_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/random_negative)，并用新的“覆盖补齐型”变异集替换了旧的 mutation 集，新的变异样本放在 [targeted_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/targeted_negative)。

当前目录内容如下：

- 正例目录：[positive](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/positive)，共 `11` 个文件
- 保留下来的随机负例：[random_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/random_negative)，共 `299` 个文件
- 重新构造后的变异负例：[targeted_negative](/root/code/ChainCollab/src/newTranslator/MDAcheck/datasets/all_ocl_rules_try1/targeted_negative)，共 `140` 个文件

新的 mutation 语料来自：

- 变异 manifest：[manifest.json](/root/code/ChainCollab/src/newTranslator/MDAcheck/bpmn-mutations/manifest.json)
- 变异校验报告：[report.json](/root/code/ChainCollab/src/newTranslator/MDAcheck/ocl-report-bpmn-mutations/report.json)
- 变异 Markdown 报告：[report.md](/root/code/ChainCollab/src/newTranslator/MDAcheck/ocl-report-bpmn-mutations/report.md)

## 新 mutation 集覆盖了什么

新的 mutation 集为下面 `14` 条规则各补了 `10` 个负例：

- `Model::AtLeastOneContract`
- `Model::UniqueContractNames`
- `Contract::UniqueNamesPerKind`
- `Participant::MspX509Paired`
- `Participant::MultiBoundsPaired`
- `Participant::MultiBoundsOrder`
- `Participant::AttributeKeysUnique`
- `Message::SenderNotReceiver`
- `BusinessRule::InputMappingParamUnique`
- `BusinessRule::OutputMappingParamUnique`
- `Contract::StartDoesNotEnableItself`
- `GatewayFlow::CompareBranchesNoDuplicateConditions`
- `SetGlobalAction::SetLiteralTypeMatchesGlobalType`
- `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType`

这套新 mutation 集的校验结果是：

- `140` 个 mutation 文件全部都是负例
- 上面 14 条目标规则都实现了 `10/10` 命中
- 其中 `Model::AtLeastOneContract` 这 10 个样本会同时带有 `UNKNOWN`，这是空 contract 模型在校验时产生的附带现象，但目标规则本身仍然稳定命中

## 合并后的规则覆盖情况

下面这个表的含义是：

- Random：来自已经保留的 `random_negative`
- Mutation：来自重新构造的 `targeted_negative`
- Total：两者相加

现在合并后，`43` 条 OCL 规则都至少有 `10` 个负例。

| OCL规则 | 随机负例 | 变异负例 | 总数 |
| --- | ---: | ---: | ---: |
| `Model::AtLeastOneContract` | 0 | 10 | 10 |
| `Model::UniqueContractNames` | 0 | 10 | 10 |
| `Contract::SectionAtMostOnceEachKind` | 10 | 0 | 10 |
| `Contract::HasExactlyOneFlowSection` | 10 | 0 | 10 |
| `Contract::MessagesRequireAtLeastTwoParticipants` | 10 | 0 | 10 |
| `Contract::UniqueNamesPerKind` | 0 | 10 | 10 |
| `Contract::MessageParticipantsInContract` | 10 | 0 | 10 |
| `Participant::MspX509Paired` | 0 | 10 | 10 |
| `Participant::MultiBoundsPaired` | 0 | 10 | 10 |
| `Participant::MultiBoundsOrder` | 2 | 10 | 12 |
| `Participant::MultiFlagConsistent` | 10 | 0 | 10 |
| `Participant::AttributeKeysUnique` | 0 | 10 | 10 |
| `Message::SenderNotReceiver` | 2 | 10 | 12 |
| `BusinessRule::InputMappingParamUnique` | 0 | 10 | 10 |
| `BusinessRule::OutputMappingParamUnique` | 0 | 10 | 10 |
| `BusinessRule::HasAtLeastOneInputMapping` | 10 | 0 | 10 |
| `Contract::RuleMappingsReferenceOwnGlobals` | 10 | 0 | 10 |
| `Contract::OracleTaskMappingsReferenceOwnGlobals` | 10 | 0 | 10 |
| `Contract::FlowSectionNotEmpty` | 10 | 0 | 10 |
| `Contract::FlowRefsStayInSameContract` | 10 | 0 | 10 |
| `Contract::ExactlyOneStartFlow` | 10 | 0 | 10 |
| `Contract::StartEventMustBeReady` | 10 | 0 | 10 |
| `Contract::StartDoesNotEnableItself` | 5 | 10 | 15 |
| `Contract::ExactlyOneReadyEventAndMatchesStart` | 10 | 0 | 10 |
| `Contract::StartFlowTargetInContract` | 10 | 0 | 10 |
| `Contract::ActionsReferenceOwnElementsAndGlobals` | 10 | 0 | 10 |
| `ParallelJoin::ParallelGatewayTypeRequired` | 10 | 0 | 10 |
| `ParallelJoin::SourcesAtLeastTwoAndDistinct` | 10 | 0 | 10 |
| `ParallelJoin::SourcesNotContainJoinGateway` | 10 | 0 | 10 |
| `GatewayFlow::ChooseImpliesExclusiveGateway` | 10 | 0 | 10 |
| `GatewayFlow::ExactlyOneGatewayFlowMode` | 10 | 0 | 10 |
| `GatewayFlow::ElseBranchUniqueAndLast` | 10 | 0 | 10 |
| `GatewayFlow::CompareBranchesNoDuplicateConditions` | 0 | 10 | 10 |
| `GatewayExpressionBranch::NotSupportedByCurrentCodeGen` | 10 | 0 | 10 |
| `GatewayCompareBranch::RelationOperatorAllowed` | 10 | 0 | 10 |
| `SetGlobalAction::SetLiteralTypeMatchesGlobalType` | 0 | 10 | 10 |
| `GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType` | 0 | 10 | 10 |
| `LiteralExpr::ExactlyOneLiteralKind` | 10 | 0 | 10 |
| `MessageFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `RuleFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `EventFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `OracleTaskFlow::NoEnableDisableConflict` | 10 | 0 | 10 |
| `ParallelJoin::NoEnableDisableConflict` | 10 | 0 | 10 |

## 备注

- 保留下来的随机负例没有重新生成，它们来自前面那轮 `generate_balanced_dataset.py` 运行时已经筛出来的结果。
- 变异负例是基于当前正例池重新构造的，然后复制到了这个数据集目录下的 `targeted_negative` 中。
- 这份文档就是 `all_ocl_rules_try1` 当前覆盖状态的最终说明。
