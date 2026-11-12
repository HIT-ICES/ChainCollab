# Negative Case Report: invalid_missing_message_trigger

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_message_trigger/invalid_missing_message_trigger.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_message_trigger.b2c:24:22: Unknown object "MissingMsg" of class "Message"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A11_flow_refs_stay_in_same_contract`: 所有 flow 引用必须局限在本合约内 (Contract::FlowRefsStayInSameContract, src/newTranslator/MDAcheck/check.ocl)
