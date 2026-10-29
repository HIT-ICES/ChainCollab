# Semantic Fidelity Report: multi_message_contract_c

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/multi_message_contract_c/multi_message_contract_c.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/multi_message_contract_c/multi_message_contract_c.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/multi_message_contract_c/multi_message_contract_c.sol`

## DSL Statistics

- participants: 3
- globals: 1
- messages: 3
- events: 2
- gateways: 0
- businessrules: 0
- flows: 4

## Go

- verdict: PASS
- flow matched: 4 / 4
- flow coverage: 1.0
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=[]

### Unmatched Rules

- none

## Solidity

- verdict: PASS
- flow matched: 4 / 4
- flow coverage: 1.0
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=['PlaceholderGateway']
- businessrules: missing=[] extra=['PlaceholderBusinessRule']

### Unmatched Rules

- none

## Conclusion

- final verdict: PASS

## 覆盖断言

- `A03_message_sender_receiver_in_contract`: message 的发送方和接收方必须属于本合约 (Contract::MessageParticipantsInContract, src/newTranslator/MDAcheck/check.ocl)
- `A04_message_sender_not_receiver`: message 的发送方与接收方不能相同 (Message::SenderNotReceiver, src/newTranslator/MDAcheck/check.ocl)
- `A08_exactly_one_start_flow`: 合约必须且仅有一个 start flow (Contract::ExactlyOneStartFlow, src/newTranslator/MDAcheck/check.ocl)
- `A10_start_flow_target_in_contract`: start flow target 必须属于本合约 (Contract::StartFlowTargetInContract, src/newTranslator/MDAcheck/check.ocl)
