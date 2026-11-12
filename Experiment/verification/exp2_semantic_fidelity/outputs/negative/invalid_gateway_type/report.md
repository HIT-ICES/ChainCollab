# Negative Case Report: invalid_gateway_type

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_gateway_type/invalid_gateway_type.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_gateway_type.b2c:13:35: Expected 'exclusive' or 'event' or 'parallel' => 'ay { type *xor initia'

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A17_gateway_type_enum_legal`: gateway type 必须取 grammar 允许值 (GatewayType, src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx)
