# Semantic Fidelity Report: business_rule_contract_e

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_contract_e/business_rule_contract_e.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_contract_e/business_rule_contract_e.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/positive/business_rule_contract_e/business_rule_contract_e.sol`

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

- `A05_rule_mappings_reference_own_globals`: businessrule 映射必须引用本合约 globals (Contract::RuleMappingsReferenceOwnGlobals, src/newTranslator/MDAcheck/check.ocl)
- `A08_exactly_one_start_flow`: 合约必须且仅有一个 start flow (Contract::ExactlyOneStartFlow, src/newTranslator/MDAcheck/check.ocl)
- `A15_gateway_choose_only_for_exclusive`: choose 分支只能用于 exclusive gateway (GatewayFlow::ChooseImpliesExclusiveGateway, src/newTranslator/MDAcheck/check.ocl)
