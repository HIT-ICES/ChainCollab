# Negative Case Report: invalid_missing_set_variable

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_set_variable/invalid_missing_set_variable.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_set_variable.b2c:24:47: Unknown object "MissingCounter" of class "GlobalVar"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A12_actions_reference_own_elements_and_globals`: action 引用的元素与变量必须存在 (Contract::ActionsReferenceOwnElementsAndGlobals, src/newTranslator/MDAcheck/check.ocl)
