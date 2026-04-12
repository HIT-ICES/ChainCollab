# Negative Case Report: invalid_missing_rule_mapping_global

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_rule_mapping_global/invalid_missing_rule_mapping_global.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_rule_mapping_global.b2c:24:26: Unknown object "MissingScore" of class "GlobalVar"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A05_rule_mappings_reference_own_globals`: businessrule 映射必须引用本合约 globals (Contract::RuleMappingsReferenceOwnGlobals, src/newTranslator/MDAcheck/check.ocl)
