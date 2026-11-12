# Negative Case Report: invalid_missing_flow_target

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_flow_target/invalid_missing_flow_target.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_flow_target.b2c:23:42: Unknown object "MissingMessage" of class "FlowElement"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A10_start_flow_target_in_contract`: start flow target 必须属于本合约 (Contract::StartFlowTargetInContract, src/newTranslator/MDAcheck/check.ocl)
- `A11_flow_refs_stay_in_same_contract`: 所有 flow 引用必须局限在本合约内 (Contract::FlowRefsStayInSameContract, src/newTranslator/MDAcheck/check.ocl)
