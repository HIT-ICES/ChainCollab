# Semantic Fidelity Report: basic_linear_case

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/basic_linear_case/basic_linear_case.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/basic_linear_case/basic_linear_case.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/basic_linear_case/basic_linear_case.sol`

## DSL Statistics

- participants: 2
- globals: 1
- messages: 2
- events: 2
- gateways: 1
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
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=['PlaceholderBusinessRule']

### Unmatched Rules

- none

## Conclusion

- final verdict: PASS

## 覆盖断言

- `A01_model_has_contract`: 模型至少包含一个 contract (Model::AtLeastOneContract, src/newTranslator/MDAcheck/check.ocl)
- `A02_unique_names_per_kind`: 同类元素名称唯一 (Contract::UniqueNamesPerKind, src/newTranslator/MDAcheck/check.ocl)
- `A08_exactly_one_start_flow`: 合约必须且仅有一个 start flow (Contract::ExactlyOneStartFlow, src/newTranslator/MDAcheck/check.ocl)
- `A09_start_event_ready`: start event 必须 READY (Contract::StartEventMustBeReady, src/newTranslator/MDAcheck/check.ocl)
- `A10_start_flow_target_in_contract`: start flow target 必须属于本合约 (Contract::StartFlowTargetInContract, src/newTranslator/MDAcheck/check.ocl)
- `A15_gateway_choose_only_for_exclusive`: choose 分支只能用于 exclusive gateway (GatewayFlow::ChooseImpliesExclusiveGateway, src/newTranslator/MDAcheck/check.ocl)
- `A16_gateway_flow_mode_unique`: gateway flow 只能二选一使用 then 或 choose (GatewayFlow::ExactlyOneGatewayFlowMode, src/newTranslator/MDAcheck/check.ocl)
