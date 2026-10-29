# Negative Case Report: invalid_missing_message_sender

- 输入 DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/negative/invalid_missing_message_sender/invalid_missing_message_sender.b2c`
- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败
- 实际结果: 已按预期拒绝非法输入

## 失败原因

- /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/cases/negative/invalid_missing_message_sender.b2c:9:27: Unknown object "UnknownSender" of class "Participant"

## 结论

- verdict: EXPECTED_REJECT

## 对应断言

- `A03_message_sender_receiver_in_contract`: message 的发送方和接收方必须属于本合约 (Contract::MessageParticipantsInContract, src/newTranslator/MDAcheck/check.ocl)
