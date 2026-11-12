# Semantic Fidelity Report: business_rule_case

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_case/business_rule_case.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_case/business_rule_case.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_case/business_rule_case.sol`

## DSL Statistics

- participants: 2
- globals: 2
- messages: 2
- events: 2
- gateways: 1
- businessrules: 1
- flows: 5

## Go

- verdict: PASS
- flow matched: 5 / 5
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
- flow matched: 5 / 5
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

## Conclusion

- final verdict: PASS

## 覆盖断言

- `A01_model_has_contract`: 模型至少包含一个 contract (Model::AtLeastOneContract, src/newTranslator/MDAcheck/check.ocl)
- `A02_unique_names_per_kind`: 同类元素名称唯一 (Contract::UniqueNamesPerKind, src/newTranslator/MDAcheck/check.ocl)
- `A05_rule_mappings_reference_own_globals`: businessrule 映射必须引用本合约 globals (Contract::RuleMappingsReferenceOwnGlobals, src/newTranslator/MDAcheck/check.ocl)
- `A08_exactly_one_start_flow`: 合约必须且仅有一个 start flow (Contract::ExactlyOneStartFlow, src/newTranslator/MDAcheck/check.ocl)
- `A09_start_event_ready`: start event 必须 READY (Contract::StartEventMustBeReady, src/newTranslator/MDAcheck/check.ocl)
- `A10_start_flow_target_in_contract`: start flow target 必须属于本合约 (Contract::StartFlowTargetInContract, src/newTranslator/MDAcheck/check.ocl)
