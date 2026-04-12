# Negative Case Report: invalid_missing_start_event

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_start_event/invalid_missing_start_event.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_start_event.b2c:22:21: Unknown object "MissingStart" of class "Event"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A08_exactly_one_start_flow`: 合约必须且仅有一个 start flow (Contract::ExactlyOneStartFlow, src/newTranslator/MDAcheck/check.ocl)
- `A11_flow_refs_stay_in_same_contract`: 所有 flow 引用必须局限在本合约内 (Contract::FlowRefsStayInSameContract, src/newTranslator/MDAcheck/check.ocl)
